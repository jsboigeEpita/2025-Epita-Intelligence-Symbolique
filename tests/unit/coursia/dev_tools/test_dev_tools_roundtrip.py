# -*- coding: utf-8 -*-
"""Round-trip guard for the #1961 Phase 1 CoursIA asset on dev_tools.

Replays every case of docs/coursia_contrib/dev_tools_examples.json against the real
argumentation_analysis.utils.dev_tools modules and pins the structural claims the
notebook teaches. Corpus-free, zero LLM, zero JVM — external commands are stubbed.
"""

import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
EXAMPLES_PATH = REPO / "docs" / "coursia_contrib" / "dev_tools_examples.json"
NOTEBOOK_PATH = REPO / "docs" / "coursia_contrib" / "dev_tools.ipynb"
DEV_TOOLS_DIR = REPO / "argumentation_analysis" / "utils" / "dev_tools"

from argumentation_analysis.utils.dev_tools import (
    code_formatting_utils,
    code_validation,
    coverage_utils,
    encoding_utils,
    env_checks,
    format_utils,
    import_testing_utils,
    project_structure_utils,
)


@pytest.fixture(scope="module")
def examples():
    data = json.loads(EXAMPLES_PATH.read_text(encoding="utf-8"))
    assert data["asset"] == "dev_tools"
    return data


def case(sections, name):
    match = [c for c in sections if c["name"] == name]
    assert len(match) == 1, f"case {name!r} not found exactly once"
    return match[0]


# ------------------------------------------------------------------ inventory


def test_inventory_matches_head(examples):
    inv = examples["inventory"]
    mods = sorted(p.name for p in DEV_TOOLS_DIR.glob("*.py") if p.name != "__init__.py")
    assert len(mods) == inv["total_modules"] == 12
    assert set(inv["module_lines"]) == set(mods)
    for m in mods:
        lines = len((DEV_TOOLS_DIR / m).read_text(encoding="utf-8").splitlines())
        assert lines == inv["module_lines"][m], f"line count drifted for {m}"
    assert len(inv["core_eight"]) == 8
    assert set(inv["core_eight"]) <= set(mods)
    assert set(inv["untargeted"]) == set(mods) - set(inv["core_eight"])


def test_notebook_ships_executed_outputs():
    nb = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
    code_cells = [c for c in nb["cells"] if c["cell_type"] == "code"]
    assert len(code_cells) >= 12
    counts = []
    for cell in code_cells:
        assert cell.get("execution_count"), "code cell without execution_count"
        assert cell.get("outputs"), "code cell without committed outputs"
        counts.append(cell["execution_count"])
    assert counts == sorted(counts), "execution_count must be sequential"


# ------------------------------------------------------------------ encoding


def test_fix_file_encoding_replays(examples, tmp_path):
    cases = {c["name"]: c for c in examples["encoding_cases"]}

    p = tmp_path / "utf8_ok.txt"
    p.write_text("café déjà vu\n", encoding="utf-8")
    assert encoding_utils.fix_file_encoding(str(p)) is True
    assert (
        p.read_text(encoding="utf-8")
        == cases["utf8_file_passes_through"]["content_after"]
    )

    p = tmp_path / "cp1252_src.txt"
    p.write_bytes("café".encode("cp1252"))
    assert encoding_utils.fix_file_encoding(str(p)) is True
    assert (
        p.read_text(encoding="utf-8")
        == cases["cp1252_recovered_as_utf8"]["content_after"]
    )

    p = tmp_path / "weird_bytes.txt"
    p.write_bytes(b"\x81\x8d\x8f\x90\x9d")
    assert encoding_utils.fix_file_encoding(str(p)) is True
    assert (
        p.read_text(encoding="utf-8") == cases["latin1_always_decodes"]["content_after"]
    )

    assert (
        encoding_utils.fix_file_encoding(str(tmp_path / "nope.txt"))
        is cases["missing_file_is_false"]["returns"]
        is False
    )


def test_project_encoding_scan_replays(examples, tmp_path):
    (tmp_path / "good.py").write_text("print('éàç')\n", encoding="utf-8")
    (tmp_path / "bad.py").write_bytes("print('éàç')\n".encode("cp1252"))
    (tmp_path / "venv").mkdir()
    (tmp_path / "venv" / "ignored.py").write_bytes("print('éàç')\n".encode("cp1252"))
    (tmp_path / "notes.txt").write_bytes("print('éàç')\n".encode("cp1252"))
    flagged = encoding_utils.check_project_python_files_encoding(str(tmp_path))
    stored = case(examples["encoding_cases"], "project_scan_flags_only_utf8_broken_py")
    assert (
        sorted(Path(f).name for f in flagged)
        == stored["flagged_basenames"]
        == ["bad.py"]
    )


# ------------------------------------------------------------------ java env

JAVA_OK_STUB = lambda cmd, cwd=None: (0, "", 'openjdk version "11.0.25"')  # noqa: E731
JAVA_MISSING_STUB = lambda cmd, cwd=None: (
    -1,
    "",
    "FileNotFoundError: java",
)  # noqa: E731


@pytest.mark.parametrize(
    "name,stub,home_kind,expected",
    [
        ("path_only_no_home", "ok", None, False),
        ("home_and_path", "ok", "valid", True),
        ("home_without_bin_exe", "ok", "empty_dir", False),
        ("java_not_found_valid_home", "missing", "valid", False),
    ],
)
def test_java_environment_quadrants(
    examples, tmp_path, monkeypatch, name, stub, home_kind, expected
):
    stored = case(examples["java_env_cases"], name)
    assert stored["verdict"] is expected

    monkeypatch.setattr(
        env_checks, "_run_command", JAVA_OK_STUB if stub == "ok" else JAVA_MISSING_STUB
    )
    if home_kind is None:
        monkeypatch.delenv("JAVA_HOME", raising=False)
    elif home_kind == "valid":
        jdk = tmp_path / "jdk"
        (jdk / "bin").mkdir(parents=True)
        (jdk / "bin" / ("java.exe" if sys.platform == "win32" else "java")).write_text(
            "", encoding="utf-8"
        )
        monkeypatch.setenv("JAVA_HOME", str(jdk))
    else:
        monkeypatch.setenv("JAVA_HOME", str(tmp_path))

    assert env_checks.check_java_environment() is expected


def test_java_rule_is_a_conjunction(examples):
    assert "AND" in examples["java_env_rule"]


# ------------------------------------------------------------------ deps


def test_check_python_dependencies_replays(examples, tmp_path):
    stored = {c["name"]: c for c in examples["deps_cases"]}
    assert stored["all_installed"]["verdict"] is True
    assert stored["missing_package"]["verdict"] is False
    assert stored["vcs_and_include_lines_skipped"]["verdict"] is True
    assert stored["comments_only_is_true"]["verdict"] is True
    assert stored["file_missing_is_false"]["verdict"] is False
    assert stored["constraint_loss_marks_false"]["verdict"] is False

    p = tmp_path / "ok.txt"
    p.write_text("pytest\npackaging>=20\n", encoding="utf-8")
    assert env_checks.check_python_dependencies(str(p)) is True

    p = tmp_path / "miss.txt"
    p.write_text("pytest\nno-such-package-xyz-42\n", encoding="utf-8")
    assert env_checks.check_python_dependencies(str(p)) is False

    p = tmp_path / "vcs.txt"
    p.write_text(
        "-e .\ngit+https://example.invalid/repo.git\n-r other.txt\npytest\n",
        encoding="utf-8",
    )
    assert env_checks.check_python_dependencies(str(p)) is True

    p = tmp_path / "empty.txt"
    p.write_text("# rien ici\n\n", encoding="utf-8")
    assert env_checks.check_python_dependencies(str(p)) is True

    assert env_checks.check_python_dependencies(str(tmp_path / "absent.txt")) is False

    p = tmp_path / "heur.txt"
    p.write_text("pytest == =9.9\n", encoding="utf-8")
    assert env_checks.check_python_dependencies(str(p)) is False


# ------------------------------------------------------------------ package map


def test_map_package_to_module_replays(examples):
    for c in examples["map_module_cases"]:
        got = project_structure_utils.map_package_to_module(
            c["package"], c.get("custom")
        )
        assert got == c["expected"] == c["returns"], c["name"]


def test_map_boundary_and_catch_all(examples):
    cases = {c["name"]: c for c in examples["map_module_cases"]}
    assert (
        project_structure_utils.map_package_to_module("tests.unit_legacy")
        == cases["prefix_has_no_dotted_boundary"]["returns"]
        == "Tests - Unit"
    )
    # startswith("") is always True, so the documented 'Autre' fallback is unreachable
    assert (
        project_structure_utils.map_package_to_module("unknown.top.pkg")
        == cases["unmapped_never_reaches_autre"]["returns"]
        == "Global/Non-Specific"
    )
    assert "Autre" not in {
        project_structure_utils.map_package_to_module(p)
        for p in ("unknown.top.pkg", "zzz", "not.in.map.at")
    }


# ------------------------------------------------------------------ imports


def test_import_by_name_and_path_replays(examples, tmp_path):
    stored = {c["name"]: c for c in examples["import_cases"]}

    ok, msg = import_testing_utils.test_module_import_by_name("json")
    assert ok is stored["by_name_stdlib"]["success"] is True
    assert msg.startswith(stored["by_name_stdlib"]["msg_prefix"])

    ok, msg = import_testing_utils.test_module_import_by_name("module_inexistant_zz_42")
    assert ok is stored["by_name_missing"]["success"] is False
    assert msg.startswith(stored["by_name_missing"]["msg_prefix"])

    (tmp_path / "ok_module.py").write_text("VALUE = 42\n", encoding="utf-8")
    ok, msg = import_testing_utils.test_module_import_by_path(tmp_path / "ok_module.py")
    sys.modules.pop("ok_module", None)
    assert ok is stored["by_path_ok"]["success"] is True
    assert msg.startswith(stored["by_path_ok"]["msg_prefix"])
    assert str(tmp_path.resolve()) not in sys.path  # restored
    assert stored["by_path_ok"]["sys_path_restored"] is True


def test_init_py_inserts_package_dir_not_parent(examples, tmp_path):
    stored = case(examples["import_cases"], "init_py_inserts_package_dir_not_parent")
    pkg = tmp_path / "fake_pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("PKG = 1\n", encoding="utf-8")
    ok, msg = import_testing_utils.test_module_import_by_path(pkg / "__init__.py")
    sys.modules.pop("fake_pkg", None)
    assert ok is stored["success"] is False
    assert msg.startswith(stored["msg_prefix"])


def test_import_error_taxonomy_and_alias(examples, tmp_path):
    stored = {c["name"]: c for c in examples["import_cases"]}

    broken = tmp_path / "broken_module.py"
    broken.write_text("def f(:\n    pass\n", encoding="utf-8")
    ok, msg = import_testing_utils.test_module_import_by_path(broken)
    sys.modules.pop("broken_module", None)
    assert ok is stored["by_path_syntax_error_is_not_importerror"]["success"] is False
    assert msg.startswith(
        stored["by_path_syntax_error_is_not_importerror"]["msg_prefix"]
    )

    txt = tmp_path / "notes.txt"
    txt.write_text("no\n", encoding="utf-8")
    ok, msg = import_testing_utils.test_module_import_by_path(txt)
    assert ok is stored["non_py_path_rejected"]["success"] is False
    assert msg.startswith(stored["non_py_path_rejected"]["msg_prefix"])

    assert (
        import_testing_utils.test_import
        is import_testing_utils.test_module_import_by_name
    )


# ------------------------------------------------------------------ apostrophes


def test_fix_docstrings_apostrophes_replays(examples, tmp_path):
    stored = {c["name"]: c for c in examples["apostrophe_cases"]}

    p = tmp_path / "docstrings.py"
    p.write_text("C'est un test d'évaluation simple.\n", encoding="utf-8")
    assert (
        format_utils.fix_docstrings_apostrophes(str(p))
        is stored["basic_quoting"]["first_run"]
    )
    after1 = p.read_text(encoding="utf-8")
    assert after1 == stored["basic_quoting"]["content_after_first"]
    assert (
        format_utils.fix_docstrings_apostrophes(str(p))
        is stored["second_run_is_idempotent"]["second_run"]
    )
    assert (
        p.read_text(encoding="utf-8")
        == stored["second_run_is_idempotent"]["content_after_second"]
    )

    p = tmp_path / "longest.py"
    p.write_text("jusqu'au bout et jusqu'à la fin\n", encoding="utf-8")
    assert (
        format_utils.fix_docstrings_apostrophes(str(p))
        is stored["longest_alternative_first"]["returns"]
    )
    assert (
        p.read_text(encoding="utf-8")
        == stored["longest_alternative_first"]["content_after"]
    )

    p = tmp_path / "overmatch.py"
    p.write_text("jusqu'aubaine\n", encoding="utf-8")
    assert (
        format_utils.fix_docstrings_apostrophes(str(p))
        is stored["no_word_boundary_overmatch"]["returns"]
    )
    assert (
        p.read_text(encoding="utf-8")
        == stored["no_word_boundary_overmatch"]["content_after"]
    )

    assert (
        format_utils.fix_docstrings_apostrophes(str(tmp_path / "nope.py"))
        is stored["missing_file_is_false"]["returns"]
        is False
    )


# ------------------------------------------------------------------ syntax / tokens


def test_check_python_syntax_replays(examples, tmp_path):
    stored = {c["name"]: c for c in examples["syntax_cases"]}

    p = tmp_path / "ok.py"
    p.write_text("def hi():\n    print('hi')\n", encoding="utf-8")
    ok, msg, ctx = code_validation.check_python_syntax(str(p))
    assert ok is True and msg == stored["syntax_ok"]["message"] and ctx == []

    p = tmp_path / "broken.py"
    p.write_text("def hi():\n    print('oops)\n", encoding="utf-8")
    ok, msg, ctx = code_validation.check_python_syntax(str(p))
    assert ok is stored["syntax_error_context"]["ok"] is False
    assert stored["syntax_error_context"]["message_contains"] in msg
    assert ctx == stored["syntax_error_context"]["context"]
    assert stored["syntax_error_context"]["error_line_marked"] in ctx

    ok, msg, ctx = code_validation.check_python_syntax(str(tmp_path / "absent.py"))
    assert ok is stored["syntax_missing_file"]["ok"] is False
    assert stored["syntax_missing_file"]["message_contains"] in msg


def test_check_python_tokens_replays(examples, tmp_path):
    stored = {c["name"]: c for c in examples["syntax_cases"]}

    p = tmp_path / "dollars.py"
    p.write_text("x = 1\n$ = 2\n", encoding="utf-8")
    ok, msg, errs = code_validation.check_python_tokens(str(p))
    assert ok is stored["error_token_flagged"]["ok"] is False
    assert errs == stored["error_token_flagged"]["error_tokens"]
    assert errs[0]["line"] == 2 and errs[0]["col"] == 0

    p = tmp_path / "unterminated.py"
    p.write_text("s = '''abc\n", encoding="utf-8")
    ok, msg, errs = code_validation.check_python_tokens(str(p))
    assert ok is stored["token_error_unterminated_string"]["ok"] is False
    assert stored["token_error_unterminated_string"]["message_contains"] in msg
    assert errs == stored["token_error_unterminated_string"]["error_tokens"]


# ------------------------------------------------------------------ directory references


def test_analyze_directory_references_replays(examples, tmp_path):
    stored = case(examples["dir_reference_cases"], "counts_and_exclusions")

    (tmp_path / "subdir").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / "file1.py").write_text(
        "a = 'config/settings.json'\nb = 'config/other.yaml'\nc = 'data/input.csv'\n",
        encoding="utf-8",
    )
    (tmp_path / "subdir" / "file2.py").write_text("d = 'data/x'\n", encoding="utf-8")
    (tmp_path / "file3.txt").write_text("config/ignored\n", encoding="utf-8")
    (tmp_path / "docs" / "ignored.py").write_text(
        "z = 'config/still-ignored'\n", encoding="utf-8"
    )

    res = code_validation.analyze_directory_references(
        str(tmp_path),
        {"config_refs": re.compile(r"config/"), "data_refs": re.compile(r"data/")},
    )
    assert {k: v["count"] for k, v in res.items()} == stored["expected_counts"]
    assert {
        k: {Path(f).name: n for f, n in v["files"].items()} for k, v in res.items()
    } == stored["expected_files"]


def test_reference_examples_capped_at_five(examples, tmp_path):
    stored = case(examples["dir_reference_cases"], "examples_capped_at_five")
    (tmp_path / "many.py").write_text(
        "".join(f"line{i} = 'config/f{i}'\n" for i in range(1, 8)), encoding="utf-8"
    )
    res = code_validation.analyze_directory_references(
        str(tmp_path), {"c": re.compile(r"config/")}
    )
    assert res["c"]["count"] == stored["expected_count"] == 7
    assert len(res["c"]["examples"]) == stored["expected_n_examples"] == 5


# ------------------------------------------------------------------ coverage

COVERAGE_XML = (
    "<coverage line-rate='0.735' branch-rate='0.5' lines-valid='200' "
    "lines-covered='147' branches-valid='40' branches-covered='20'>"
    "<packages><package name='alpha' line-rate='0.8' branch-rate='0.4'/>"
    "<package name='beta' line-rate='0.612345' branch-rate='0.2'/></packages></coverage>"
)

FIXED_INPUT = {
    "global_line_rate": 73.5,
    "global_branch_rate": 50.0,
    "lines_valid": 200,
    "lines_covered": 57,
    "branches_valid": 10,
    "branches_covered": 4,
    "packages": {
        "alpha": {"line_rate": 80.0, "branch_rate": 40.0},
        "beta": {"line_rate": 61.2, "branch_rate": 20.0},
    },
    "timestamp": "2026-01-01 12:00:00",
}


def test_parse_coverage_xml_replays(examples, tmp_path):
    stored = {c["name"]: c for c in examples["coverage_cases"]}

    xml = tmp_path / "coverage.xml"
    xml.write_text(COVERAGE_XML, encoding="utf-8")
    data = coverage_utils.parse_coverage_xml(xml)
    data.pop("timestamp")
    assert data == stored["parse_ok"]["data"]
    assert data["global_line_rate"] == 73.5

    assert (
        coverage_utils.parse_coverage_xml(tmp_path / "absent.xml")
        is stored["parse_missing_file"]["returns"]
        is None
    )
    bad = tmp_path / "bad.xml"
    bad.write_text("<coverage><packages>", encoding="utf-8")
    assert (
        coverage_utils.parse_coverage_xml(bad)
        is stored["parse_malformed_xml"]["returns"]
        is None
    )


def test_initial_coverage_history_replays(examples, tmp_path):
    stored = case(
        examples["coverage_cases"], "initial_history_fabricates_minus_5pct_30_days_ago"
    )

    hist = tmp_path / "hist" / "coverage_history.json"
    assert (
        coverage_utils.create_initial_coverage_history(dict(FIXED_INPUT), hist) is True
    )
    entries = json.loads(hist.read_text(encoding="utf-8"))
    assert len(entries) == stored["n_entries"] == 2
    assert entries[1] == FIXED_INPUT
    previous = dict(entries[0])
    assert isinstance(previous.pop("timestamp"), str)
    assert previous == stored["previous_entry"]
    assert previous["global_line_rate"] == 68.5  # -5 points
    assert previous["lines_covered"] == 51  # int(57 * 0.9)
    assert previous["packages"]["alpha"]["branch_rate"] == 40.0  # branch rate conserved
    assert stored["current_entry_equals_input"] is True


def test_save_coverage_history_appends_and_resets(examples, tmp_path):
    h2 = tmp_path / "h2.json"
    e1 = {"global_line_rate": 10.0, "timestamp": "2026-01-02 08:00:00"}
    e2 = {"global_line_rate": 12.0, "timestamp": "2026-01-03 08:00:00"}
    coverage_utils.save_coverage_history(dict(e1), h2)
    coverage_utils.save_coverage_history(dict(e2), h2)
    saved = json.loads(h2.read_text(encoding="utf-8"))
    assert saved == [e1, e2]

    h3 = tmp_path / "h3.json"
    h3.write_text("definitely-not-json{", encoding="utf-8")
    payload = {"global_line_rate": 5.0, "timestamp": "2026-01-04 08:00:00"}
    coverage_utils.save_coverage_history(dict(payload), h3)
    reset = json.loads(h3.read_text(encoding="utf-8"))
    stored = case(examples["coverage_cases"], "corrupted_history_is_reset_not_crashed")
    assert len(reset) == stored["n_entries"] == 1
    assert reset == [payload]


# ------------------------------------------------------------------ autopep8 wrapper


class _FakeProc:
    returncode = 0
    stdout = ""
    stderr = ""


def _format_with_stub(tmp_path, args=None):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        return _FakeProc()

    real_run = code_formatting_utils.subprocess.run
    code_formatting_utils.subprocess.run = fake_run
    try:
        target = tmp_path / "ugly.py"
        target.write_text("x=1\n", encoding="utf-8")
        ok = code_formatting_utils.format_python_file_with_autopep8(str(target), args)
    finally:
        code_formatting_utils.subprocess.run = real_run
    return ok, calls


def test_autopep8_default_command_replays(examples, tmp_path):
    stored = case(
        examples["format_tool_cases"], "default_args_are_in_place_double_aggressive"
    )
    ok, calls = _format_with_stub(tmp_path)
    assert ok is True
    assert len(calls) == stored["n_subprocess_calls"] == 2
    assert calls[0] == stored["version_probe"] == ["autopep8", "--version"]
    assert (
        calls[1][:4]
        == stored["format_command_head"]
        == [
            "autopep8",
            "--in-place",
            "--aggressive",
            "--aggressive",
        ]
    )
    assert calls[1][-1].endswith("ugly.py")


def test_autopep8_custom_args_replace_defaults(examples, tmp_path):
    stored = case(
        examples["format_tool_cases"], "custom_args_replace_defaults_entirely"
    )
    ok, calls = _format_with_stub(tmp_path, ["--diff"])
    assert ok is stored["returns"] is True
    assert calls[1] == ["autopep8", "--diff", calls[1][-1]]
    assert stored["format_command_head"] == ["autopep8", "--diff"]


def test_autopep8_missing_file_short_circuits(examples, tmp_path):
    stored = case(
        examples["format_tool_cases"], "missing_file_fails_before_any_subprocess"
    )
    calls = []
    real_run = code_formatting_utils.subprocess.run

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        return _FakeProc()

    code_formatting_utils.subprocess.run = fake_run
    try:
        ok = code_formatting_utils.format_python_file_with_autopep8(
            str(tmp_path / "absent.py")
        )
    finally:
        code_formatting_utils.subprocess.run = real_run
    assert ok is stored["returns"] is False
    assert len(calls) == stored["n_subprocess_calls"] == 0
