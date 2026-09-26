"""Keep recursive test-tree walks named, so a new probe race cannot hide (#2607)."""

import ast
from pathlib import Path

import pytest

from tests.support.tree_walk import iter_files

TESTS_ROOT = Path(__file__).resolve().parents[1]

# Each permitted recursive walk and its root, followed through any parameters
# to its callers. The stable subtrees here cannot contain tests/_probe_*.
# A removed walk makes this table stale and reddens too.
ROOTS_BY_WALK = {
    "e2e/runners/playwright_js_runner.py": ["screenshots_path (artifacts)"] * 3,
    "e2e/web_api/test_interfaces_integration.py": [
        "simple_templates (web UI)",
        "react_src (web UI)",
        "self.react_interface_dir/src (web UI)",
    ],
    "support/withdrawn_modules.py": [
        "spec.submodule_search_locations (module or tmp_path)"
    ],
    "unit/argumentation_analysis/agents/core/logic/test_modal_atom_names_2471.py": [
        "REPO/root (argumentation_analysis, scripts)"
    ],
    "unit/argumentation_analysis/agents/test_encryption_island_retirement_2120.py": [
        "island (retired production package or tmp_path)"
    ],
    "unit/argumentation_analysis/config/test_settings_attribute_drift_2115.py": [
        "PROD_ROOT (argumentation_analysis)"
    ],
    "unit/argumentation_analysis/core/communication/test_no_naked_middleware_in_production_1574.py": [
        "PKG_ROOT (production package)"
    ],
    "unit/argumentation_analysis/core/test_one_openai_client_constructor_2391.py": [
        "REPO_ROOT/root (production roots)"
    ],
    "unit/argumentation_analysis/orchestration/test_one_capability_surface_1842.py": [
        "root (PROD_ROOT or synthetic)"
    ]
    * 3,
    "unit/argumentation_analysis/test_cross_text_parallels_status_2344.py": [
        "REPO_ROOT/root (argumentation_analysis, scripts)"
    ],
    "unit/argumentation_analysis/test_no_duplicate_method_definitions_2357.py": [
        "PKG_ROOT (argumentation_analysis)"
    ],
    "unit/argumentation_analysis/test_raw_sdk_sampling_params_1936.py": [
        "SWEEP_ROOTS (production)"
    ],
    "unit/argumentation_analysis/test_utils_real.py": [
        "self.temp_dir (temporary test data)"
    ],
    "unit/argumentation_analysis/utils/test_no_exit_at_import_2459.py": [
        "PACKAGE (argumentation_analysis)"
    ],
    "unit/docs/test_report_anchors_2258.py": ["DOCS (docs/)"],
    "unit/mocks/test_no_sysmodules_hijack_1891.py": ["MOCKS_DIR (tests/mocks/)"],
    "unit/scripts/test_extract_promising_versions_3827.py": ["out (tmp_path output)"],
    "unit/test_fixture_modules_resolve_2416.py": [
        "FIXTURES (tests/fixtures/)",
        "ROOT/docs (docs/)",
    ],
    "unit/test_probe_walk_race_2607.py": ["tmp_path (stable synthetic tree)"],
}


def _recursive_walks(root):
    found = {}
    for path in iter_files(root):
        if "_archived" in path.parts:
            continue  # not collected: archived tests are outside this gate
        rel = path.relative_to(root).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        calls = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(
                node.func, ast.Attribute
            ):
                continue
            func = node.func
            if func.attr == "rglob":
                calls.append(node.lineno)
            elif (
                func.attr == "walk"
                and isinstance(func.value, ast.Name)
                and func.value.id == "os"
            ):
                calls.append(node.lineno)
            elif func.attr == "glob" and (
                isinstance(func.value, ast.Name)
                and func.value.id == "glob"
                or any(
                    kw.arg == "recursive"
                    and isinstance(kw.value, ast.Constant)
                    and kw.value.value
                    for kw in node.keywords
                )
                or bool(
                    node.args
                    and isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, str)
                    and "**" in node.args[0].value
                )
            ):
                calls.append(node.lineno)
        if calls:
            found[rel] = calls
    return found


def _assert_named_roots(observed):
    expected = {path: len(roots) for path, roots in ROOTS_BY_WALK.items()}
    actual = {path: len(lines) for path, lines in observed.items()}
    assert actual == expected, (
        f"unlisted walks: {actual.items() - expected.items()}; "
        f"stale roots: {expected.items() - actual.items()}. "
        "Trace every root parameter to its callers; use iter_files if tests/ "
        "can be reached, otherwise name its stable root here."
    )


def test_recursive_walks_have_named_roots():
    _assert_named_roots(_recursive_walks(TESTS_ROOT))


def test_an_unlisted_tests_root_walk_turns_the_guard_red(tmp_path):
    carrier = tmp_path / "test_new_walker.py"
    carrier.write_text(
        "from pathlib import Path\nTESTS_ROOT = Path('tests')\n"
        "def scan(): return list(TESTS_ROOT.rglob('*.py'))\n",
        encoding="utf-8",
    )
    observed = _recursive_walks(TESTS_ROOT)
    observed[carrier.name] = _recursive_walks(tmp_path)[carrier.name]
    with pytest.raises(AssertionError, match="unlisted walks"):
        _assert_named_roots(observed)


def test_a_removed_walk_leaves_a_stale_root():
    observed = _recursive_walks(TESTS_ROOT)
    observed.pop("unit/test_fixture_modules_resolve_2416.py")
    with pytest.raises(AssertionError, match="stale roots"):
        _assert_named_roots(observed)
