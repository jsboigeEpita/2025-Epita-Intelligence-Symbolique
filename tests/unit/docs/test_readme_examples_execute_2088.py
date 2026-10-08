"""#2088 DoD item 6 — the python examples the READMEs cite RESOLVE.

Item 6 asks the command and import examples of the documentation to be
*executed or verified by tests*. Executing the paid modes is the residual
(carried to its gated issue, #2936 / #2932); everything else is verifiable
for free, and this guard does it: from the fenced blocks of every tracked
README under ``argumentation_analysis/`` it reads

- ``python -m <module>`` invocations → the module must resolve in the tree;
- ``from``/``import argumentation_analysis…`` lines → same.

This is a NAME question, not a link question — which is why the item-3
instrument (``test_argumentation_readmes_cover_dirs_2088``) could not see
the defect this guard was born against: ``argumentation_analysis/scripts/
README.md`` had every link resolving and documented two modules
(``…scripts.repair_extract_markers``, ``…scripts.verify_extracts``) that no
longer exist (measured on ``f79a7c089``, 2026-10-08).

Hermetic: ``importlib.util.find_spec`` (never an import of the target, no
side effects) plus tree probes; no network, no API key, no cost.
"""

import importlib.util
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SUBTREE = "argumentation_analysis"

_FENCE = re.compile(r"^```[^\n]*\n(.*?)^```", re.MULTILINE | re.DOTALL)
# ``python [-3] -m <module>`` — ``python -c`` runs inline code, out of scope.
_PY_MODULE = re.compile(r"^\s*python(?:3)?\s+-m\s+(?P<module>[\w.]+)", re.MULTILINE)
_AA_IMPORT = re.compile(
    r"^\s*(?:from\s+(?P<from>[A-Za-z_][\w.]*)\s+import"
    r"|import\s+(?P<direct>[A-Za-z_][\w.]*))",
    re.MULTILINE,
)

# Population floor, measured 2026-10-08 on f79a7c089 — re-measure after a
# change of convention (a floor, not a frozen count).
_MIN_MODULE_EXAMPLES = 3
_MIN_IMPORT_EXAMPLES = 15


def _tracked_files(pattern: str) -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "--", pattern],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return [line for line in out.stdout.splitlines() if line.strip()]


def _readmes() -> list[str]:
    return sorted(
        set(
            _tracked_files(f"{SUBTREE}/**/README.md")
            + _tracked_files(f"{SUBTREE}/README.md")
        )
    )


def _fenced_blocks(text: str) -> list[str]:
    return _FENCE.findall(text)


def _cited_modules(text: str) -> list[tuple[str, str]]:
    """``(kind, module)`` for every ``python -m`` / ``argumentation_analysis``
    import inside a fenced block. Non-package imports are read too, but the
    gate only asks the package's own names to resolve in the tree."""
    found: list[tuple[str, str]] = []
    for block in _fenced_blocks(text):
        for m in _PY_MODULE.finditer(block):
            found.append(("module", m.group("module")))
        for m in _AA_IMPORT.finditer(block):
            target = (m.group("from") or m.group("direct") or "").rstrip(".")
            if target:
                found.append(("import", target))
    return found


def _resolves(target: str, root: Path = REPO_ROOT) -> bool:
    """Does ``target`` name a module that exists — in the tree, else installed?

    A module file, a package (``__init__.py``) or a runnable package
    (``__main__.py``) resolves. When the target's top segment is a directory
    of the repo but the module is not under it, the module is DEAD — a repo
    package must carry its own module, never fall through to the installed
    search path (the ``argumentation_analysis`` name is what catches a
    README citing a module the tree no longer has).
    """
    as_path = root / Path(*target.split("."))
    if as_path.with_suffix(".py").is_file():
        return True
    if (as_path / "__init__.py").is_file() or (as_path / "__main__.py").is_file():
        return True
    if (root / target.split(".")[0]).exists():
        return False
    return importlib.util.find_spec(target) is not None


class TestReadmeExamplesResolve:
    def test_every_cited_python_module_resolves(self):
        dead: list[str] = []
        n_modules = n_imports = 0
        for readme in _readmes():
            text = (REPO_ROOT / readme).read_text(
                encoding="utf-8-sig", errors="replace"
            )
            for kind, target in _cited_modules(text):
                if kind == "module":
                    n_modules += 1
                elif target.startswith(f"{SUBTREE}."):
                    n_imports += 1
                else:
                    continue  # a third-party import: not the tree's business
                if not _resolves(target):
                    dead.append(f"{readme}: {kind} {target}")
        assert n_modules >= _MIN_MODULE_EXAMPLES, (
            f"population inattendue : {n_modules} exemple(s) ``python -m`` "
            f"(plancher {_MIN_MODULE_EXAMPLES}) — le lecteur ne voit plus les "
            "blocs de code, son vert ne prouverait rien"
        )
        assert n_imports >= _MIN_IMPORT_EXAMPLES, (
            f"population inattendue : {n_imports} import(s) du paquet cités "
            f"(plancher {_MIN_IMPORT_EXAMPLES})"
        )
        assert dead == [], (
            "#2088 item 6 : exemples de code des READMEs de "
            f"argumentation_analysis/ pointant un module inexistant : {dead}"
        )


class TestTheReaderCanFail:
    """Non-vacuity: the reader finds a planted dead module and resolves the
    living forms — a 0 with no such control is indistinguishable from a
    reader that reads nothing."""

    def test_planted_dead_module_reddens_and_living_forms_pass(self, tmp_path: Path):
        (tmp_path / "pkg").mkdir()
        (tmp_path / "pkg" / "__init__.py").write_text("", encoding="utf-8")
        (tmp_path / "pkg" / "real.py").write_text("", encoding="utf-8")
        (tmp_path / "pkg" / "runnable").mkdir()
        (tmp_path / "pkg" / "runnable" / "__main__.py").write_text("", encoding="utf-8")
        text = (
            "```bash\n"
            "python -m pkg.real\n"
            "python -m pkg.runnable\n"
            "python -m pkg.gone\n"
            "python -m pytest tests/\n"
            'python -c "print(1)"\n'
            "```\n"
            "```python\n"
            "from pkg.real import thing\n"
            "import pkg.missing\n"
            "```\n"
        )
        found = _cited_modules(text)
        assert ("module", "pkg.real") in found
        assert ("module", "pkg.runnable") in found
        assert ("module", "pkg.gone") in found
        assert not any(
            t == "print" or t.startswith("print") for _, t in found
        ), "``python -c`` runs inline code, not a module"
        verdicts = {t: _resolves(t, tmp_path) for _, t in found}
        assert verdicts["pkg.real"] is True
        assert verdicts["pkg.runnable"] is True
        assert verdicts["pkg.gone"] is False
        assert verdicts["pkg.missing"] is False
        assert verdicts["pytest"] is True

    def test_fenced_only(self):
        """A command outside a fenced block is prose, not an example."""
        assert _cited_modules("python -m pkg.gone\n") == []


class TestRetiredScriptModulesAreNotCited:
    """The two modules the item-6 guard was born against — held retired.

    Scoped to the subtree's READMEs (the surface item 6 covers); the dated
    architecture audits that still name the old files are not rewritten
    (#2057)."""

    RETIRED = (
        f"{SUBTREE}.scripts.repair_extract_markers",
        f"{SUBTREE}.scripts.verify_extracts",
    )

    def test_no_readme_cites_a_retired_scripts_module(self):
        hits: list[str] = []
        for readme in _readmes():
            text = (REPO_ROOT / readme).read_text(
                encoding="utf-8-sig", errors="replace"
            )
            for kind, target in _cited_modules(text):
                if target in self.RETIRED:
                    hits.append(f"{readme}: {kind} {target}")
        assert hits == [], f"module(s) retiré(s) encore cité(s) : {hits}"
