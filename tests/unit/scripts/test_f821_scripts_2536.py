"""Sondes né-rouge pour la tranche scripts/ de #2536 (F821 : noms indéfinis).

Chaque sonde atteint un site qui référençait un nom indéfini avant la
réparation : sur l'arbre pré-fix, la sonde échoue avec le NameError /
AttributeError documenté dans le test ; sur l'arbre réparé, elle passe.
Mesure de référence (2026-09-24) : `git stash` → rouge en valeurs →
`git stash pop` → vert.

Les scripts purement module-level (sans garde `__main__`) sont exécutés via
runpy dans un répertoire temporaire, jamais importés nus ; les scripts qui
écrivent dans de vrais fichiers du dépôt (update_coverage_in_report,
update_main_report_file) ne sont jamais exécutés — seule leur référence à
l'utilitaire restauré est vérifiée statiquement.
"""

import asyncio
import importlib.util
import json
import os
import runpy
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"


def _load_script(script_relpath, module_name):
    """Charge un script gardé par ``if __name__ == "__main__"`` sans l'exécuter.

    Enregistrement dans ``sys.modules`` obligatoire : sans lui, les ``@dataclass``
    du script échouent dans ``dataclasses._is_type`` (résolution d'annotations
    via ``sys.modules[cls.__module__]`` -> None)."""
    spec = importlib.util.spec_from_file_location(
        module_name, REPO_ROOT / script_relpath
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(module_name, None)
        raise
    return module


# --- scripts/extract_belief_trajectories.py :769 ---------------------------


def test_belief_trajectories_error_branch_names_the_real_exception():
    """Pré-fix : la branche except référençait ``trajectures_holder`` (typo) et
    écrasait l'exception réelle par un NameError."""
    mod = _load_script("scripts/extract_belief_trajectories.py", "ebp_probe_2536")
    # Import paresseux dans _run_one : on patche le module source, pas le script.
    with mock.patch(
        "argumentation_analysis.workflows.democratech.build_democratech_workflow",
        side_effect=RuntimeError("boom-p2536"),
    ):
        traj = asyncio.run(
            mod._run_one(
                "corpus_x", "Corpus X", "texte", object(), {}, max_wall_seconds=5.0
            )
        )
    assert traj.error == "RuntimeError: boom-p2536"


# --- scripts/maintenance/test_imports_after_reorg.py :37 --------------------


def test_imports_after_reorg_binds_path_and_path_helper(tmp_path):
    """Pré-fix : ``Path`` et ``test_module_import_by_path`` n'étaient pas importés."""
    mod = _load_script(
        "scripts/maintenance/test_imports_after_reorg.py", "tio_probe_2536"
    )
    assert hasattr(mod, "Path")
    tiny = tmp_path / "tiny_probe_module.py"
    tiny.write_text("VALUE = 1\n", encoding="utf-8")
    success, _message = mod.test_module_import_by_path(tiny)
    assert success is True


# --- scripts/maintenance/tools/check_imports.py :67,84 ----------------------


def test_check_imports_script_completes_without_undefined_name():
    """Script entièrement module-level (sys.exit final) : sonde par sous-processus.
    Pré-fix : NameError ``test_module_import_by_name`` dans la boucle."""
    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT)}
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "maintenance" / "tools" / "check_imports.py"),
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env=env,
        timeout=300,
    )
    assert "NameError" not in result.stderr
    assert "Traceback (most recent call last)" not in result.stderr


# --- scripts/maintenance/tools/fix_project_structure.py :151,170,179,188,198


def test_fix_project_structure_binds_run_shell_command():
    """Pré-fix : ``run_shell_command`` n'était pas importé (AttributeError)."""
    mod = _load_script(
        "scripts/maintenance/tools/fix_project_structure.py", "fps_probe_2536"
    )
    return_code, stdout, _stderr = mod.run_shell_command(
        [sys.executable, "-c", "print('probe-p2536')"], description="sonde 2536"
    )
    assert return_code == 0
    assert "probe-p2536" in stdout


# --- scripts/maintenance/tools/verify_files.py :26,27 -----------------------


def test_verify_files_runs_through_centralized_existence_check(capsys):
    """Pré-fix : ``Path`` et ``check_files_existence`` n'étaient pas importés."""
    mod = _load_script("scripts/maintenance/tools/verify_files.py", "vf_probe_2536")
    assert hasattr(mod, "check_files_existence")
    assert mod.verify_files() is None
    assert "Vérification des fichiers réorganisés" in capsys.readouterr().out


# --- scripts/maintenance/tools/verify_content_integrity.py :77 --------------


def test_verify_content_integrity_binds_path(tmp_path):
    """Pré-fix : ``Path`` n'était pas importé dans ce module."""
    mod = _load_script(
        "scripts/maintenance/tools/verify_content_integrity.py", "vci_probe_2536"
    )
    assert hasattr(mod, "Path")
    doc = tmp_path / "doc.md"
    doc.write_text("# Titre\n\n- element\n", encoding="utf-8")
    success, _message = mod.check_markdown_file(mod.Path(doc))
    assert success is True


# --- scripts/reporting/generate_coverage_report.py :228 ---------------------


def test_generate_coverage_report_main_writes_evolution_report(tmp_path, monkeypatch):
    """Pré-fix : ``generate_coverage_evolution_text_report`` n'était pas importé.
    main() utilise des chemins relatifs codés en dur -> chdir vers tmp."""
    history = [
        {
            "timestamp": "2026-01-01",
            "packages": {"pkg_a": {"line_rate": 40.0, "branch_rate": 30.0}},
        },
        {
            "timestamp": "2026-02-01",
            "packages": {"pkg_a": {"line_rate": 60.0, "branch_rate": 50.0}},
        },
    ]
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    (results_dir / "coverage_history.json").write_text(
        json.dumps(history), encoding="utf-8"
    )
    mod = _load_script(
        "scripts/reporting/generate_coverage_report.py", "gcr_probe_2536"
    )
    monkeypatch.chdir(tmp_path)
    mod.main()
    assert (results_dir / "rapport_evolution_couverture.md").exists()


# --- scripts/reporting/initialize_coverage_history.py :91 -------------------


def test_initialize_coverage_history_binds_and_creates_initial_history(tmp_path):
    """Pré-fix : ``create_initial_coverage_history`` n'était pas importé."""
    mod = _load_script(
        "scripts/reporting/initialize_coverage_history.py", "ich_probe_2536"
    )
    assert hasattr(mod, "create_initial_coverage_history")
    coverage_data = {
        "global_line_rate": 50.0,
        "lines_covered": 10,
        "packages": {"pkg_a": {"line_rate": 40.0, "branch_rate": 20.0}},
    }
    history_file = tmp_path / "coverage_history.json"
    assert mod.create_initial_coverage_history(coverage_data, history_file) is True
    entries = json.loads(history_file.read_text(encoding="utf-8"))
    assert len(entries) == 2


# --- scripts/reporting/visualize_test_coverage.py :111,192,295,389 ----------

_COVERAGE_XML = """<?xml version="1.0" ?>
<coverage version="7.6.1" timestamp="1760000000000" line-rate="0.5" branches-rate="0.25">
    <sources>
        <source>D:/dev/repo</source>
    </sources>
    <packages>
        <package name="argumentation_analysis.core" line-rate="0.6" branch-rate="0.3" complexity="10">
            <classes>
                <class name="mod_a" filename="argumentation_analysis/core/mod_a.py" complexity="5" line-rate="0.6" branch-rate="0.3">
                    <methods/>
                    <lines>
                        <line number="1" hits="1"/>
                        <line number="2" hits="0"/>
                    </lines>
                </class>
            </classes>
        </package>
    </packages>
</coverage>
"""


def test_visualize_test_coverage_binds_helpers_and_draws_chart(tmp_path, monkeypatch):
    """Pré-fix : ``map_package_to_module`` et ``parse_coverage_xml`` n'étaient
    pas importés (les copies locales sont commentées « déplacée »)."""
    monkeypatch.setenv("MPLBACKEND", "Agg")
    mod = _load_script("scripts/reporting/visualize_test_coverage.py", "vtc_probe_2536")
    assert hasattr(mod, "map_package_to_module")
    assert hasattr(mod, "parse_coverage_xml")

    xml_file = tmp_path / "coverage.xml"
    xml_file.write_text(_COVERAGE_XML, encoding="utf-8")
    parsed = mod.parse_coverage_xml(xml_file)
    assert parsed is not None and "packages" in parsed

    history = [
        {"timestamp": "2026-01-01", "global": 40, "packages": {"pkg_a": 40}},
        {"timestamp": "2026-02-01", "global": 60, "packages": {"pkg_a": 60}},
    ]
    history_file = tmp_path / "coverage_history.json"
    history_file.write_text(json.dumps(history), encoding="utf-8")
    output_dir = tmp_path / "charts"
    output_dir.mkdir()
    mod.generate_coverage_trend_chart(history_file, output_dir)
    assert any(output_dir.glob("*.png"))


# --- scripts/utils/analyze_directory_usage.py :95 ---------------------------


def test_analyze_directory_usage_main_produces_json_report(tmp_path):
    """Pré-fix : ``parse_colon_separated_string_to_regex_dict`` n'était pas importé."""
    target = tmp_path / "srcpkg"
    (target / "config").mkdir(parents=True)
    (target / "config" / "c.py").write_text('P = "config/x"\n', encoding="utf-8")
    output = tmp_path / "out" / "report.json"
    mod = _load_script("scripts/utils/analyze_directory_usage.py", "adu_probe_2536")
    argv = [
        "analyze_directory_usage.py",
        "--dir",
        str(target),
        "--output",
        str(output),
        "--patterns",
        "config/:data/",
    ]
    with mock.patch.object(sys, "argv", argv):
        mod.main()
    assert output.exists()


# --- scripts/utils/inspect_specific_sources.py :32 --------------------------


def test_inspect_specific_sources_runpy_completes(tmp_path, monkeypatch):
    """Script module-level : runpy dans un cwd temporaire avec la config qu'il
    lit. Pré-fix : NameError ``find_sources_in_config_by_ids``."""
    temp_dir = tmp_path / "_temp"
    temp_dir.mkdir()
    config = {"sources": [{"id": "x1", "source_name": "s1"}, {"id": "x2"}]}
    (temp_dir / "config_paths_corrected_v3.json").write_text(
        json.dumps(config), encoding="utf-8"
    )
    script_path = str(SCRIPTS_DIR / "utils" / "inspect_specific_sources.py")
    monkeypatch.chdir(tmp_path)
    with mock.patch.object(sys, "argv", [script_path]):
        try:
            runpy.run_path(script_path, run_name="__main__")
        except SystemExit as exc:
            assert exc.code in (0, None)


# --- scripts/maintenance/tools/remove_source_from_config.py :26,42,52,60 ----


def test_remove_source_from_config_filters_and_saves(tmp_path, monkeypatch):
    """Pré-fix : ``load_json_from_file`` / ``save_json_to_file`` /
    ``filter_list_in_json_data`` = vieux noms supprimés de project_core."""
    temp_dir = tmp_path / "_temp"
    temp_dir.mkdir()
    config = {"sources": [{"source_name": "s1"}, {"source_name": "s2"}]}
    (temp_dir / "config_fr_corrected.json").write_text(
        json.dumps(config), encoding="utf-8"
    )
    script_path = str(
        SCRIPTS_DIR / "maintenance" / "tools" / "remove_source_from_config.py"
    )
    monkeypatch.chdir(tmp_path)
    with mock.patch.object(sys, "argv", [script_path, "s1"]):
        try:
            runpy.run_path(script_path, run_name="__main__")
        except SystemExit as exc:
            assert exc.code in (0, None)
    output = temp_dir / "config_source_removed.json"
    updated = json.loads(output.read_text(encoding="utf-8"))
    assert updated == {"sources": [{"source_name": "s2"}]}


# --- argumentation_analysis/core/utils/markdown_utils.py (fonction restaurée)
# --- consommée par scripts/reporting/update_coverage_in_report.py :126
# --- et scripts/reporting/update_main_report_file.py :125 --------------------


def test_update_markdown_section_restored_and_consumed_by_reporting_scripts(tmp_path):
    """Pré-fix : ``update_markdown_section`` avait été supprimée de
    markdown_utils par le refactor 9ddcbdd8a alors que deux scripts de
    scripts/reporting/ l'appellent (ImportError). Ces deux scripts écrivent
    dans de vrais fichiers du dépôt : ils ne sont jamais exécutés ici, seule
    leur référence à l'utilitaire est vérifiée."""
    from argumentation_analysis.core.utils.markdown_utils import (
        update_markdown_section,
    )

    doc = tmp_path / "rapport.md"
    doc.write_text(
        "# Rapport\n\n## Couverture\n\nancien\n\n## Autre\n\ncontenu intouchable\n",
        encoding="utf-8",
    )
    assert update_markdown_section(doc, "## Couverture", "nouveau contenu") is True
    text = doc.read_text(encoding="utf-8")
    assert "nouveau contenu" in text
    assert "ancien" not in text
    assert "contenu intouchable" in text

    for script_name in (
        "scripts/reporting/update_coverage_in_report.py",
        "scripts/reporting/update_main_report_file.py",
    ):
        source = (REPO_ROOT / script_name).read_text(encoding="utf-8")
        assert "update_markdown_section" in source, script_name
        assert "markdown_utils" in source, script_name


# --- scripts/maintenance/tools/update_imports.py :210,214 -------------------
# --- scripts/maintenance/tools/update_paths.py :241,243 ---------------------


@pytest.fixture
def rewritable_pkg(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "m.py").write_text(
        "from core import thing\nP = 'config/foo'\n", encoding="utf-8"
    )
    return pkg


def test_update_imports_main_dry_run_lists_details(rewritable_pkg):
    """Pré-fix : main() référençait les noms nus ``modified_files_count`` /
    ``modified_files_details`` (ancienne forme du dict stats)."""
    mod = _load_script("scripts/maintenance/tools/update_imports.py", "ui_probe_2536")
    argv = [
        "update_imports.py",
        "--dir",
        str(rewritable_pkg),
        "--dry-run",
    ]
    with mock.patch.object(sys, "argv", argv):
        assert mod.main() == 0
    # dry-run : le fichier source reste intact.
    assert (rewritable_pkg / "m.py").read_text(encoding="utf-8") == (
        "from core import thing\nP = 'config/foo'\n"
    )


def test_update_paths_main_dry_run_lists_details(rewritable_pkg):
    """Pré-fix : main() référençait le nom nu ``changed_files_details``."""
    mod = _load_script("scripts/maintenance/tools/update_paths.py", "up_probe_2536")
    argv = [
        "update_paths.py",
        "--dir",
        str(rewritable_pkg),
        "--dry-run",
    ]
    with mock.patch.object(sys, "argv", argv):
        assert mod.main() == 0
    assert (rewritable_pkg / "m.py").read_text(encoding="utf-8") == (
        "from core import thing\nP = 'config/foo'\n"
    )
