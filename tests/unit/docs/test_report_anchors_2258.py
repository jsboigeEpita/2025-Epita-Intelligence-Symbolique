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

import re
import subprocess
from collections import defaultdict
from functools import lru_cache
from pathlib import Path, PurePosixPath

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
DOCS = REPO_ROOT / "docs" / "reports"

# `chemin/fichier.py:123` ou `chemin/fichier.py:123-145`
ANCHOR = re.compile(r"`([A-Za-z0-9_./\-]+\.py):(\d+)(?:-(\d+))?`")

# Repertoires qui ne font pas partie du depot utilisable (filtre applique aux lignes
# de `git ls-files` : libs/ porte 7 .py suivis, et le depot peut en gagner d'autres).
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
    """Index basename -> chemins, sur les .py du DEPOT (git), pas de la machine.

    Deux mesures R1007 rendent ce choix obligatoire :

    1. Un parcours filesystem (`rglob`) suit l'auto-lien npm
       `services/web_api/interface-web-argumentative/node_modules/<pkg>` (self-link
       `exports`) jusqu'a la limite de chemin de Windows -> `OSError [WinError 1921]`
       (run CI 34960002692). Un filtre d'apres-coup ne peut rien : la marche meurt
       avant de rendre un seul chemin de ce sous-arbre. Piege mesure au passage :
       `os.path.islink()` et `DirEntry.is_symlink()` rendent `False` sur une jonction
       Windows, donc `followlinks=False` ne l'arrete pas non plus.
    2. Un parcours de l'arbre de travail mesure la MACHINE, pas le depot : 5775 .py
       vus localement (dont 2427 sous `.claude/` et 848 sous `venvs/` -- locaux, non
       suivis) contre 2429 en CI pour le meme arbre. Un plancher calibre sur l'arbre
       local faux-positif en CI (run 34962541758).

    `git ls-files --cached --others --exclude-standard` rend le meme ensemble
    partout : les fichiers committes plus ceux sur le point de l'etre, hors installes
    et locaux ignores. C'est la reponse a la question que la garde pose vraiment --
    « l'ancre se resout-elle quelque part dans le depot ? ».
    """
    out = subprocess.run(
        [
            "git",
            "-C",
            str(REPO_ROOT),
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "--",
            "*.py",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    idx: dict[str, list[Path]] = defaultdict(list)
    for line in out.stdout.splitlines():
        if not line or any(part in SKIP_DIRS for part in PurePosixPath(line).parts):
            continue
        idx[Path(line).name].append(REPO_ROOT / line)
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
    """Controle de non-vacuite de l'index lui-meme (mesure 2026-09-15 : 2429 chemins,
    identique local et CI depuis que l'index porte sur `git ls-files`).

    Si l'index ne rend plus rien, toutes les ancres citees par basename deviennent
    MISSING-FILE : le garde rougirait pour la mauvaise raison, ou — si la resolution
    tombait sur le chemin direct — passerait sur un index vide. Un plancher explicite
    distingue « aucun fichier » de « plus rien a scanner »."""
    total = sum(len(paths) for paths in _basename_index().values())
    assert total >= 1500, (
        f"index de basename reduit a {total} chemins .py — le parcours ne voit plus le "
        f"depot (git ls-files a change de comportement ? repertoire entierement depublie ?). "
        f"Re-mesurer AVANT de faire confiance au verdict des ancres."
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
