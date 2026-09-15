# -*- coding: utf-8 -*-
"""#2258: les ancres `fichier.py:NNN` des rapports de docs/reports/ doivent exister.

Une ancre de ligne dans un rapport est une affirmation datee : rien n'empechait d'en
ecrire une, et rien ne rougissait quand elle pourrissait. #2239 a retire 7 ancres
derivees d'un seul rapport ; la mesure de #2258 en a trouve 8 autres, prouvablement
mortes, dans 3 autres rapports (5 au-dela de l'EOF, 3 vers des fichiers disparus).

Perimetre volontairement etroit — **le verdict ne repose sur aucune heuristique** :
  - le fichier cible se resout-il quelque part dans le depot ? (chemin puis basename)
  - la ligne (ou la fin de plage) tient-elle dans le fichier ?

Le garde ne pretend PAS juger si l'ancre pointe le BON symbole : une heuristique
« le symbole nomme dans la phrase est-il proche de la ligne ? » a ete mesuree a
~50% de faux positifs (un vrai positif, un faux positif sur deux echantillons), donc
elle n'est pas utilisee ici. Seuls EOF et fichier-absent sont jugees.

Limite assumee : les references `chemin.py` SANS numero de ligne ne sont pas couvertes
(une ancre sans ligne n'est pas une affirmation de position), ni les `.ipynb`.
"""

import os
import re
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
DOCS = REPO_ROOT / "docs" / "reports"

# `chemin/fichier.py:123` ou `chemin/fichier.py:123-145`
ANCHOR = re.compile(r"`([A-Za-z0-9_./\-]+\.py):(\d+)(?:-(\d+))?`")

# Repertoires qui ne font pas partie du depot utilisable (ou trop gros pour un scan).
SKIP_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    "libs",
    "portable_jdk",
}

# Prefixes essayes avant de retomber sur l'index de basename.
PATH_PREFIXES = ("", "argumentation_analysis", "scripts")


@lru_cache(maxsize=1)
def _basename_index() -> dict[str, tuple[Path, ...]]:
    """Index basename -> chemins, en parcourant le depot SANS suivre les liens.

    `rglob` ne convient pas ici : il suit les liens de repertoire et ne permet pas
    d'elaguer avant la descente. npm cree un auto-lien dans `node_modules`
    (`<paquet>/node_modules/<nom-du-paquet>` -> racine du paquet) pour les
    auto-references `exports` ; `rglob` le suit, la recursion ne s'arrete qu'a la limite
    de chemin de Windows et leve `OSError [WinError 1921]`. C'est ce qui a rougi la CI
    (#2258, run 34960002692) alors que l'arbre de dev local ne porte pas ce lien.

    Ce qui compte est l'elagage de `SKIP_DIRS` AVANT la descente, ce que `os.walk`
    autorise et `rglob` non. Piege mesure : sur une jonction Windows, `os.path.islink()`
    et `DirEntry.is_symlink()` rendent tous deux `False`, donc `followlinks=False` ne
    l'arrete PAS — sans elagage par nom la marche termine, mais en comptant 128 fichiers
    au lieu de 2 (silencieusement faux, donc pire qu'un rouge).
    """
    idx: dict[str, list[Path]] = defaultdict(list)
    for dirpath, dirnames, filenames in os.walk(REPO_ROOT, followlinks=False):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for filename in filenames:
            if filename.endswith(".py"):
                idx[filename].append(Path(dirpath) / filename)
    return {name: tuple(paths) for name, paths in idx.items()}


def anchors_in(text: str) -> list[tuple[str, int, int | None]]:
    """(chemin, ligne, fin de plage) pour chaque ancre citee dans `text`."""
    return [
        (m.group(1), int(m.group(2)), int(m.group(3)) if m.group(3) else None)
        for m in ANCHOR.finditer(text)
    ]


def _candidates(rel: str) -> list[Path]:
    found = [
        REPO_ROOT / prefix / rel
        for prefix in PATH_PREFIXES
        if (REPO_ROOT / prefix / rel).is_file()
    ]
    if found:
        return found
    return list(_basename_index().get(Path(rel).name, ()))


def anchor_verdict(rel: str, start: int, end: int | None = None) -> str:
    """Verdict d'une ancre. 'OK' ou un motif de mort, jamais un jugement de symbole.

    Resolution GENEREUSE : si un seul candidat tient la ligne, l'ancre est valide. Un
    basename ambigu (plusieurs fichiers) n'est donc pas un defaut — seuls l'absence
    totale de fichier et le depassement d'EOF le sont.
    """
    candidates = _candidates(rel)
    if not candidates:
        return "MISSING-FILE"
    failures: list[str] = []
    for cand in candidates:
        try:
            total = len(cand.read_text(encoding="utf-8", errors="replace").splitlines())
        except OSError as exc:  # pragma: no cover - disque
            failures.append(f"UNREADABLE({exc.__class__.__name__})")
            continue
        if start > total:
            failures.append(f"BEYOND-EOF({total} lines)")
            continue
        if end is not None and end > total:
            failures.append(f"RANGE-BEYOND-EOF({total} lines)")
            continue
        return "OK"
    return failures[0] if failures else "OK"


def _report_files() -> list[Path]:
    return sorted(DOCS.rglob("*.md"))


def test_the_guard_actually_finds_anchors():
    """Controle de non-vacuite : sans ancres lues, un vert ne prouverait rien."""
    total = sum(len(anchors_in(f.read_text(encoding="utf-8"))) for f in _report_files())
    assert total >= 300, (
        f"seulement {total} ancres trouvees dans docs/reports/ — le motif a probablement "
        f"cesse de correspondre, ou les rapports ont ete deplaces. Re-mesurer avant de "
        f"conclure que le garde est vert."
    )


def test_no_report_anchor_points_past_the_end_of_its_file():
    """Le defaut mesure par #2258 : 5 ancres au-dela de l'EOF, 3 vers un fichier absent."""
    dead: list[str] = []
    for doc in _report_files():
        text = doc.read_text(encoding="utf-8")
        for rel, start, end in anchors_in(text):
            v = anchor_verdict(rel, start, end)
            if v != "OK":
                dead.append(
                    f"{doc.relative_to(REPO_ROOT).as_posix()} -> {rel}:{start} [{v}]"
                )
    assert not dead, (
        "ancre(s) morte(s) dans docs/reports/ — reparer vers une poignee mesuree, ou "
        "marquer la reference comme fossile si sa cible a disparu :\n  "
        + "\n  ".join(dead)
    )


def test_the_basename_index_is_not_silently_empty():
    """Controle de non-vacuite de l'index lui-meme (mesure 2026-09-15 : 5773 chemins).

    Si le parcours ne rend plus rien, toutes les ancres citees par basename deviennent
    MISSING-FILE : le garde rougirait pour la mauvaise raison, ou — si la resolution
    tombait sur le chemin direct — passerait sur un index vide. Un plancher explicite
    distingue « aucun fichier » de « plus rien a scanner »."""
    total = sum(len(paths) for paths in _basename_index().values())
    assert total >= 3000, (
        f"index de basename reduit a {total} chemins .py — le parcours ne voit plus le "
        f"depot (elagage trop large ? arbre monte differemment ?). Re-mesurer AVANT de "
        f"faire confiance au verdict des ancres."
    )


def test_the_verdict_flags_a_fabricated_anchor():
    """Controle POSITIF : sans lui, le zero du test precedent ne prouve rien.

    Un instrument qui ne sait pas rendre non-zero rend zero pour toujours. On verifie donc
    qu'une ancre fabriquee est bien rapportee morte, sur les deux motifs.
    """
    beyond = anchor_verdict("argumentation_analysis/core/jvm_setup.py", 99_999)
    assert beyond.startswith(
        "BEYOND-EOF"
    ), f"ancre au-dela de l'EOF non signalee : {beyond}"

    missing = anchor_verdict(
        "argumentation_analysis/agents/no_such_dir/no_such_file_xyz.py", 1
    )
    assert missing == "MISSING-FILE", f"fichier absent non signale : {missing}"

    # et l'instrument doit rester capable de dire OK sur une ancre saine
    assert anchor_verdict("argumentation_analysis/core/jvm_setup.py", 1) == "OK"


@pytest.mark.parametrize(
    "rel,line",
    [
        ("core/jvm_setup.py", 70),
        ("orchestration/workflows.py", 149),
        ("agents/core/logic/fol_handler.py", 22),
    ],
)
def test_known_good_anchors_stay_resolvable(rel: str, line: int):
    """Epingles : ces formes de resolution (chemin partiel, sous argumentation_analysis/)
    sont celles dont dependent les 240 ancres saines du depot. Si la resolution se
    resserre, ce test tombe avant que le garde ne devienne bruyant."""
    assert anchor_verdict(rel, line) == "OK", f"{rel}:{line} ne se resout plus"
