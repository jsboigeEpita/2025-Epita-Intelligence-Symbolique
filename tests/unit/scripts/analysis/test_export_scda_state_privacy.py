# tests/unit/scripts/analysis/test_export_scda_state_privacy.py
"""L'export SCDA est sûr **par défaut** : destination gitignorée, contenu décontaminé.

Avant #2143, `--out` valait `"."` et rien ne décontaminait : lancé depuis la
racine sans `--out`, le script déposait `state.json|xml|md|html` et un bundle CSV
en clair dans le répertoire de travail suivi par git. Les deux dimensions
mesurées ici sont séparées — la destination et le contenu.

Les étiquettes de ce fichier sont inventées : aucune ne nomme une source.
"""

import json
import subprocess
from pathlib import Path

import pytest

import argumentation_analysis.evaluation.state_export_scrub as scrub
from argumentation_analysis.evaluation.corpus_instance_tokens import (
    derive_instance_tokens,
)
from scripts.analysis.export_scda_state import (
    DEFAULT_OUT_DIR,
    build_parser,
    export_state,
)

REPO = Path(__file__).resolve().parents[4]

# Census synthétique : aucune étiquette ne mappe sur un vrai document. Le but
# est un vocabulaire que le test connaît exactement, pour armer la dérivation
# sans qu'un seul label réel entre dans ce fichier suivi (#2411, #2187).
_SYNTHETIC_CENSUS = (
    {"source_name": "Clovermark Fennwick 03/04/2026"},
    {"source_name": "Bramblewood - Tinder Lattice 2026"},
)


@pytest.fixture(autouse=True)
def _synthetic_instance_census(monkeypatch):
    """Dérive le vocabulaire d'instance du census synthétique, pas du corpus.

    `_instance_pattern` est mémoïsé dans le module : le remettre à None autour
    de chaque test, sinon le vocabulaire du premier servirait aux suivants.
    Sans ce fixture, le scrub irait chercher le corpus chiffré réel (ce que
    fait la production — et ce dont un test unitaire ne doit pas dépendre).
    """
    monkeypatch.setattr(
        scrub,
        "_load_instance_tokens",
        lambda: derive_instance_tokens(_SYNTHETIC_CENSUS),
    )
    monkeypatch.setattr(scrub, "_INSTANCE_PATTERN", None)


def _git_check_ignore(path: str) -> bool:
    """True si git lui-même ignore `path`."""
    done = subprocess.run(
        ["git", "check-ignore", "-q", path],
        cwd=REPO,
        capture_output=True,
        check=False,
    )
    return done.returncode == 0


def test_git_check_ignore_is_not_blind():
    """Contrôle : l'instrument doit savoir rendre un « non ignoré ».

    Sans lui, un `check-ignore` cassé (mauvais cwd, git absent, sortie avalée)
    rendrait « gitignoré » pour n'importe quel chemin.
    """
    assert not _git_check_ignore(
        "CLAUDE.md"
    ), "git check-ignore déclare ignoré un fichier suivi -> instrument aveugle"
    assert _git_check_ignore(
        "outputs/"
    ), "contrôle positif échoué : outputs/ n'est pas ignoré"


def test_default_out_is_gitignored():
    default = build_parser().get_default("out")
    assert default == DEFAULT_OUT_DIR
    assert default not in (".", "", "./"), "le défaut est le répertoire courant suivi"
    assert _git_check_ignore(default), f"{default} n'est pas gitignoré"


def test_export_scrubs_before_writing(tmp_path):
    leak = "Verbatim integral d'un discours attribue a Nationrelay"
    state = {
        "raw_text": leak,
        "final_conclusion": leak,
        "identified_arguments": {"arg_1": {"premisses": leak, "confidence": 0.9}},
    }
    src = tmp_path / "state.json"
    src.write_text(json.dumps(state), encoding="utf-8")

    out = tmp_path / "out"
    written = export_state(str(src), "json", out)
    assert written, "aucun fichier écrit -> le test ne prouve rien"

    blob = (out / "state.json").read_text(encoding="utf-8")
    assert leak not in blob, "texte brut présent dans l'export"
    assert "raw_text" not in blob, "champ de texte brut conservé"
    assert "<scrubbed>" in blob, "aucune neutralisation -> le scrub n'a pas tourné"
    assert (
        "0.9" in blob
    ), "un agrégat a été perdu : le scrub doit préserver le structurel"


def test_both_exporters_share_one_scrub():
    """La consolidation : deux appelants, une seule implémentation."""
    import argumentation_analysis.evaluation.state_export_scrub as scrub
    import scripts.analysis.generate_spectacular_bundle as bundle

    assert bundle._scrub_state_for_export is scrub._scrub_state_for_export
