"""Garde du recensement des écrivains en mode texte (#3723).

En mode texte, ``"\\n"`` devient le saut de ligne de la plateforme **à
l'écriture**. Un écrivain qui ne dit pas quel séparateur il veut commite donc
le saut de ligne du siège : mesuré sur ``origin/main``, 306 blobs suivis
portent un CR, dont ``docs/reports/discourse_patterns.md`` (102 lignes CRLF),
produit par ``scripts/dataset/build_pattern_report.py``.

Le contrôle qui compte est le NÉGATIF : un écrivain qui écrit un fichier suivi
sans ``newline="\\n"`` doit être **signalé**. Sans ce contrôle, le garde-fou
peut rendre un verdict vert sans avoir rien regardé.

Les témoins synthétiques écrivent dans ``tmp_path`` : le dépôt n'est jamais
touché, et le classement (suivi / ignoré / hors dépôt) reste réel parce que
la cible est résolue depuis la racine du dépôt.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
TOOL = REPO_ROOT / "scripts/security/verify_text_writer_line_endings.py"

SPEC = importlib.util.spec_from_file_location("verify_text_writer_line_endings", TOOL)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def census_in(tmp_path: Path, source: str, monkeypatch) -> tuple[list, dict]:
    """The census of a synthetic scripts/ tree holding one file."""
    script = tmp_path / "synthetic_script.py"
    script.write_text(source, encoding="utf-8")
    monkeypatch.setattr(mod, "script_files", lambda: [script])
    return mod.census()


def violations(sites: list) -> list:
    return [site for site in sites if site.in_population and not site.declares_newline]


# ---------------------------------------------------------------------------
# le dépôt, tel qu'il est
# ---------------------------------------------------------------------------
def test_every_writer_of_the_population_declares_the_lf():
    """Le contrôle négatif, sur l'arbre réel : aucune violation."""
    sites, _ = mod.census()
    assert violations(sites) == [], [
        f"{site.location}: {site.target_expr_src}" for site in violations(sites)
    ]


def test_the_census_sees_a_population_and_is_not_vacuous():
    """Le census doit voir la population : sinon le contrôle ne teste rien."""
    sites, _ = mod.census()
    tracked = [site for site in sites if site.classification == "tracked"]
    rewriters = [site for site in sites if site.classification.startswith("walk-")]
    assert (
        len(tracked) >= 30
    ), f"la résolution ne voit plus que {len(tracked)} fichiers suivis"
    assert (
        len(rewriters) >= 5
    ), f"la règle des réécriveurs ne voit plus que {len(rewriters)} sites"
    assert len(tracked) + len(rewriters) >= 40


def test_the_guard_runs_and_is_green():
    """Le garde-fou, exécuté comme en CI, sort vert."""
    proc = subprocess.run(
        [sys.executable, str(TOOL)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "violations: 0" in proc.stdout


# ---------------------------------------------------------------------------
# témoins synthétiques : le contrôle négatif doit mordre
# ---------------------------------------------------------------------------
def test_a_writer_of_a_tracked_file_without_newline_is_flagged(tmp_path, monkeypatch):
    """Contrôle négatif : un écrivain d'un fichier suivi sans newline= est vu."""
    sites, _ = census_in(
        tmp_path,
        "from pathlib import Path\n"
        'Path("README.md").write_text("x", encoding="utf-8")\n',
        monkeypatch,
    )
    flagged = violations(sites)
    assert len(flagged) == 1, [site.target_expr_src for site in sites]
    assert flagged[0].classification == "tracked"


def test_the_same_writer_with_the_lf_is_accepted(tmp_path, monkeypatch):
    """Contrôle positif : le même écrivain, conforme, ne sort pas."""
    sites, _ = census_in(
        tmp_path,
        "from pathlib import Path\n"
        'Path("README.md").write_text("x", encoding="utf-8", newline="\\n")\n',
        monkeypatch,
    )
    assert violations(sites) == []


def test_a_translated_separator_is_still_a_violation(tmp_path, monkeypatch):
    """``newline=os.linesep`` est le défaut lui-même : il doit être signalé."""
    sites, _ = census_in(
        tmp_path,
        "import os\n"
        "from pathlib import Path\n"
        'Path("README.md").write_text("x", encoding="utf-8", newline=os.linesep)\n',
        monkeypatch,
    )
    assert len(violations(sites)) == 1


def test_a_rewriter_is_flagged_even_when_its_root_is_unknown(tmp_path, monkeypatch):
    """Un réécriveur est dans la population, même si sa racine est illisible."""
    sites, _ = census_in(
        tmp_path,
        "from pathlib import Path\n"
        "def rewrite(directory):\n"
        '    for file_path in Path(directory).rglob("*.py"):\n'
        '        file_path.write_text(file_path.read_text(encoding="utf-8"), encoding="utf-8")\n',
        monkeypatch,
    )
    flagged = violations(sites)
    assert len(flagged) == 1, [site.classification for site in sites]
    assert flagged[0].classification.startswith("walk-")


def test_a_writer_into_an_ignored_directory_is_not_flagged(tmp_path, monkeypatch):
    """Contrôle négatif de la contre-épreuve : ``outputs/`` est ignoré par git."""
    sites, _ = census_in(
        tmp_path,
        "from pathlib import Path\n"
        'Path("outputs/result.json").write_text("x", encoding="utf-8")\n',
        monkeypatch,
    )
    assert violations(sites) == []
    assert [site.classification for site in sites] == ["ignored"]


def test_a_writer_in_bytes_has_no_separator_to_declare(tmp_path, monkeypatch):
    """Un écrivain en mode octets n'a pas de séparateur à posséder."""
    sites, _ = census_in(
        tmp_path,
        "from pathlib import Path\n" 'Path("README.md").write_bytes(b"x")\n',
        monkeypatch,
    )
    assert sites == []
    assert violations(sites) == []


def test_a_writer_outside_the_repository_is_not_flagged(tmp_path, monkeypatch):
    """Un fichier hors du dépôt n'est jamais commité."""
    elsewhere = (tmp_path.resolve().parent / "elsewhere-3723.md").as_posix()
    sites, _ = census_in(
        tmp_path,
        "from pathlib import Path\n"
        f'Path({elsewhere!r}).write_text("x", encoding="utf-8")\n',
        monkeypatch,
    )
    assert violations(sites) == []
    assert [site.classification for site in sites] == ["outside"]
