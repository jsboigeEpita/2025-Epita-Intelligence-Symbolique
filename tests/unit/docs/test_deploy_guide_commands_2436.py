"""Born-red guards for #2436: the deployment guides' commands exist.

``docs/guides/GUIDE_DEPLOIEMENT_PRODUCTION.md`` made
``python scripts/sprint3_final_validation.py`` its "Validation système" step
(4 occurrences), with "Résultat attendu : 100% de succès". Measured on
``main`` ``31fb6821``:

- the path was wrong: the script lived under ``scripts/validation/``;
- at its real path it exited 1, for reasons unrelated to the system:
  - it imported a module that never existed (``fol_logic_agent_adapter``);
  - it ran pytest through a conda env name absent from the fleet;
  - one of its two test paths had moved;
- every run wrote ``docs/SPRINT_3_RAPPORT_FINAL.md`` into the repository.

The same guide also called ``scripts/fix_unicode_conda.py`` and
``scripts/fix_critical_imports.py`` (deleted in 2025) and
``python -m argumentation_analysis.app`` (no such module). ``DEPLOYMENT.md``
had superseded the page since #991, but the page did not say so.

The script is retired (``config/webapp_config.yml`` already listed it as
replaced), and both guides now run the same verification: the registry, then
the unit suite under CI's marker filter.

Scope: the two deployment guides. Other guides are not covered here.
"""

import importlib.util
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
GUIDES = (
    "docs/guides/DEPLOYMENT.md",
    "docs/guides/GUIDE_DEPLOIEMENT_PRODUCTION.md",
)
RETIRED_SCRIPT = "scripts/validation/sprint3_final_validation.py"
SNAPSHOT_DIRS = ("docs/reports/", "docs/archives/")

_FENCE = re.compile(r"^```[^\n]*\n(.*?)^```", re.MULTILINE | re.DOTALL)
# ``python <path>.py`` or ``python -m <module>``; ``python -c`` runs inline code.
_PYTHON_COMMAND = re.compile(
    r"^\s*python\s+(?:-m\s+(?P<module>[\w.]+)|(?P<path>[\w./\\-]+\.py))",
    re.MULTILINE,
)


def _tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return [line for line in out.stdout.splitlines() if line.strip()]


def _python_commands(markdown: str) -> list[tuple[str, str]]:
    """``(kind, target)`` for every python invocation inside a fenced block."""
    commands = []
    for block in _FENCE.findall(markdown):
        for match in _PYTHON_COMMAND.finditer(block):
            if match.group("module"):
                commands.append(("module", match.group("module")))
            else:
                commands.append(("path", match.group("path").replace("\\", "/")))
    return commands


def _resolves(kind: str, target: str, root: Path = REPO_ROOT) -> bool:
    if kind == "path":
        return (root / target).is_file()
    as_path = root / Path(*target.split("."))
    if as_path.with_suffix(".py").is_file() or (as_path / "__main__.py").is_file():
        return True
    if (root / target.split(".")[0]).exists():
        return False  # a repo package: the module must be in the tree
    return importlib.util.find_spec(target) is not None  # an installed tool


def test_every_python_command_of_the_deployment_guides_exists():
    dead, seen = [], 0
    for guide in GUIDES:
        text = (REPO_ROOT / guide).read_text(encoding="utf-8-sig")
        commands = _python_commands(text)
        seen += len(commands)
        dead += [
            f"{guide}: python {'-m ' if kind == 'module' else ''}{target}"
            for kind, target in commands
            if not _resolves(kind, target)
        ]
    assert seen, "the reader found no python command in either guide"
    assert not dead, f"commands that point nowhere: {dead}"


def test_the_command_reader_can_fail(tmp_path: Path):
    """Non-vacuity: a dead path and a dead repo module redden; ``-c`` is not
    read as a path; an installed module resolves."""
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "real.py").write_text("", encoding="utf-8")
    guide = (
        "```bash\n"
        "python scripts/gone.py\n"
        "python -m pkg.real\n"
        "python -m pkg.gone\n"
        'python -c "print(1)"\n'
        "python -m pytest tests/\n"
        "```\n"
        "python outside/a/fence.py\n"
    )
    commands = _python_commands(guide)
    assert commands == [
        ("path", "scripts/gone.py"),
        ("module", "pkg.real"),
        ("module", "pkg.gone"),
        ("module", "pytest"),
    ]
    verdicts = {target: _resolves(kind, target, tmp_path) for kind, target in commands}
    assert verdicts == {
        "scripts/gone.py": False,
        "pkg.real": True,
        "pkg.gone": False,
        "pytest": True,
    }


def test_the_sprint3_script_is_retired_and_no_living_doc_runs_it():
    tracked = _tracked_files()
    assert RETIRED_SCRIPT not in tracked
    runners = [
        rel
        for rel in tracked
        if rel.endswith(".md")
        and not rel.startswith(SNAPSHOT_DIRS)
        and re.search(
            r"python\s+\S*sprint3_final_validation\.py",
            (REPO_ROOT / rel).read_text(encoding="utf-8-sig", errors="replace"),
        )
    ]
    assert not runners, f"living docs still run the retired script: {runners}"


def test_both_guides_verify_with_the_same_command():
    """One verification, written once in each guide: the registry, then the
    unit suite under CI's marker filter, which keeps ``requires_api`` tests
    out (unmarked tests that still reach the LLM are #2444)."""
    expected = 'pytest tests/unit/ -m "not slow and not requires_api"'
    for guide in GUIDES:
        text = (REPO_ROOT / guide).read_text(encoding="utf-8-sig")
        assert "setup_registry(); print('OK')" in text, guide
        assert expected in text, guide
