"""#3062 — nothing re-loads a ``.env`` over the caller: no ``override=True``.

Measured on ``main`` (R1094, seat ai-01): collecting ``tests/e2e/python``
imported ``scripts.apps.webapp.unified_web_orchestrator``, whose import-time
``load_dotenv(override=True)`` reloaded the root ``.env`` over the caller's
neutralised keys for the whole pytest session — 12 705 paid calls from a
neutralised run (#2472 broken at import). The one loader is
``argumentation_analysis.config.env_loader`` (``EnvironmentManager`` /
``load_env_file``): a value the caller set wins, even ``""`` (#2472), while a
value set in-process before it is replaced (#1295).

This guard pins the mechanism, not one file: any tracked module calling
``load_dotenv(..., override=...)`` — ``True``, another truthy constant, or an
opaque expression — re-opens the hole. ``override=False`` is the library
default spelled out and stays allowed. Archive trees are dead code by policy
and unreachable from collection.
"""

import ast
from pathlib import Path

import pytest

from tests.support.tree_walk import iter_tracked_files

ROOT = Path(__file__).resolve().parents[4]

# Tracked vendored/dead trees the census does not count: probes are transient,
# ``_archives``/``_archived`` are dead by policy, the rest is vendored.
SKIP_DIR_PREFIXES = (
    "_probe_",
    "_archives",
    "_archived",
    "node_modules",
    "libs",
    "portable_jdk",
)


def _override_sites(path: Path):
    """``(line, override expression)`` for every ``load_dotenv(override=...)``
    that is not the constant ``False``."""
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
        if name != "load_dotenv":
            continue
        for keyword in node.keywords:
            if keyword.arg != "override":
                continue
            if isinstance(keyword.value, ast.Constant) and keyword.value.value is False:
                continue  # the library default spelled out
            yield node.lineno, ast.unparse(keyword.value)


def test_no_tracked_module_reloads_dotenv_over_the_caller():
    offenders = []
    for path in iter_tracked_files(ROOT, skip_prefixes=SKIP_DIR_PREFIXES):
        for line, expr in _override_sites(path):
            offenders.append(f"{path.relative_to(ROOT)}:{line}: override={expr}")
    assert not offenders, (
        "load_dotenv(override=...) re-opens #3062 — route through "
        "argumentation_analysis.config.env_loader (the caller wins, #2472):\n"
        + "\n".join(sorted(offenders))
    )


@pytest.mark.parametrize(
    ("call", "banned"),
    [
        ("load_dotenv(p, override=True)", True),
        ("dotenv.load_dotenv(p, override=True)", True),
        ("load_dotenv(p, override=1)", True),
        ("load_dotenv(p, override=USE_ENV)", True),
        ("load_dotenv(p)", False),
        ("load_dotenv(dotenv_path=p)", False),
        ("load_dotenv(p, override=False)", False),
        ("os.environ.update(d)", False),
    ],
)
def test_guard_classifies_an_override_loader(tmp_path, call, banned):
    path = tmp_path / "loader.py"
    path.write_text(call, encoding="utf-8")
    assert bool(list(_override_sites(path))) is banned
