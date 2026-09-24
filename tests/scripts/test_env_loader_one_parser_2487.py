# -*- coding: utf-8 -*-
"""#2487: every .env loader parses quotes, and a value the caller set wins.

Measured on ``main``: 21 files carried the same hand-rolled loop, and 20 more
a variant of it. ``val.strip()`` kept the quotes, so a ``.env`` line
``KEY="value"`` put ``"value"``, quotes included, into the environment.
``scripts/run_real_analysis.py`` could not start on a seat whose ``.env``
quotes a URL: ``OpenAISettings.base_url`` refused ``'"https://..."'`` at
import. The loaders now call python-dotenv, which the environment ships.

Each loader runs for real, in a fresh interpreter, on a copy placed in a
temporary tree whose ``.env`` quotes its values, so no test reads the
repository's own ``.env``.
"""

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

# The one hand-rolled loop the census allows, and why.
_NAMED_FALLBACKS = {
    "project_core/core_from_scripts/load_dotenv.py": (
        "load_dotenv_simple: the fallback load_dotenv_advanced uses when "
        "python-dotenv cannot be imported. It strips quotes and lets the "
        "caller win."
    ),
}

_DOTENV = (
    'QUOTED_2487="https://example.invalid/v1"\n'
    "SINGLE_2487='single quoted'\n"
    'CALLER_2487="from the file"\n'
)
_EXPECTED = "'https://example.invalid/v1' 'single quoted' 'from the caller'"
_PRINT = (
    "import os as _os_2487\n"
    "print(repr(_os_2487.environ.get('QUOTED_2487')),"
    " repr(_os_2487.environ.get('SINGLE_2487')),"
    " repr(_os_2487.environ.get('CALLER_2487')))\n"
)

_BOUND = 300


def _is_environ(node):
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "environ"
        and isinstance(node.value, ast.Name)
        and node.value.id == "os"
    )


def _writes_environ(node):
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in ("setdefault", "update")
        and _is_environ(node.func.value)
    ):
        return True
    if isinstance(node, ast.Assign):
        return any(
            isinstance(t, ast.Subscript) and _is_environ(t.value) for t in node.targets
        )
    return False


def _splits_on_equals(node):
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in ("partition", "split")
        and bool(node.args)
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value == "="
    )


def _hand_rolled_loops(tree):
    """Loops that split ``KEY=VALUE`` and write ``os.environ``."""
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.For, ast.While))
        and any(_writes_environ(n) for n in ast.walk(node))
        and any(_splits_on_equals(n) for n in ast.walk(node))
    ]


def _tracked(pattern):
    out = subprocess.run(
        ["git", "ls-files", pattern],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return out.split()


def _parse(rel):
    return ast.parse((ROOT / rel).read_text(encoding="utf-8-sig"))


def _module_level_loaders():
    """``(path, last line of the loader)`` for every module-level .env loader
    under ``scripts/``: a ``load_dotenv(...)`` call or a hand-rolled loop."""
    found = []
    for rel in _tracked("scripts/*.py"):
        text = (ROOT / rel).read_text(encoding="utf-8-sig")
        if "load_dotenv(" not in text and "os.environ" not in text:
            continue
        tree = ast.parse(text)
        for stmt in tree.body:
            # A loader inside a function runs when the function is called:
            # those are in _FUNCTION_LOADERS.
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            call = isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)
            if (call and getattr(stmt.value.func, "id", None) == "load_dotenv") or (
                _hand_rolled_loops(stmt)
            ):
                found.append((rel, stmt.end_lineno))
                break
    return found


def _child_env():
    env = dict(os.environ)
    for name in ("QUOTED_2487", "SINGLE_2487"):
        env.pop(name, None)
    env["CALLER_2487"] = "from the caller"
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT), env.get("PYTHONPATH", "")])
    return env


def _run(script, cwd, *args, env=None):
    try:
        return subprocess.run(
            [sys.executable, str(script), *args],
            cwd=cwd,
            env=env or _child_env(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=_BOUND,
        )
    except subprocess.TimeoutExpired:
        pytest.fail(f"{script} did not end within {_BOUND}s")


def test_no_hand_rolled_env_loop_outside_the_named_fallback():
    """DoD 2 and 3. Root: every tracked ``*.py`` file (``git ls-files``).
    ``main`` had 41 files with such a loop."""
    found, unread = {}, []
    for rel in _tracked("*.py"):
        try:
            loops = _hand_rolled_loops(_parse(rel))
        except (SyntaxError, UnicodeDecodeError, ValueError) as exc:
            unread.append(f"{rel} ({type(exc).__name__})")
            continue
        if loops:
            found[rel] = [loop.lineno for loop in loops]

    assert not unread, f"the census could not read: {unread}"
    unnamed = sorted(set(found) - set(_NAMED_FALLBACKS))
    assert (
        not unnamed
    ), "hand-rolled .env loops (call dotenv.load_dotenv instead): " + ", ".join(
        f"{rel}:{found[rel]}" for rel in unnamed
    )
    stale = sorted(set(_NAMED_FALLBACKS) - set(found))
    assert not stale, f"named fallbacks that no longer carry a loop: {stale}"


_LOADERS = _module_level_loaders()


def test_the_census_of_module_level_loaders_is_not_empty():
    """Control: the parametrization below measures something."""
    assert len(_LOADERS) >= 33, _LOADERS


@pytest.mark.parametrize("rel,last_line", _LOADERS, ids=[r for r, _ in _LOADERS])
def test_a_script_loads_quoted_values_unquoted_and_the_caller_wins(
    tmp_path, rel, last_line
):
    """DoD 1. The script runs up to its loader, from a copy at the same depth
    in a temporary tree, so its ``Path(__file__)`` arithmetic reaches the
    temporary ``.env``."""
    lines = (ROOT / rel).read_text(encoding="utf-8-sig").splitlines()
    copy = tmp_path / rel
    copy.parent.mkdir(parents=True, exist_ok=True)
    copy.write_text("\n".join(lines[:last_line]) + "\n" + _PRINT, encoding="utf-8")
    (tmp_path / ".env").write_text(_DOTENV, encoding="utf-8")

    done = _run(copy, tmp_path)

    assert done.returncode == 0, done.stderr[-3000:]
    assert done.stdout.strip().splitlines()[-1] == _EXPECTED, done.stdout[-3000:]


_FUNCTION_LOADERS = {
    # the .env path is relative to the working directory
    "capability_eval": (
        "from argumentation_analysis.evaluation import capability_eval as m\n"
        "m._load_dotenv()\n"
    ),
    "run_agentic_eval": (
        "from argumentation_analysis.evaluation import run_agentic_eval as m\n"
        "m._load_dotenv()\n"
    ),
    "run_iteration": (
        "from argumentation_analysis.evaluation import run_iteration as m\n"
        "m._load_dotenv()\n"
    ),
    "run_llm_judge": (
        "from argumentation_analysis.evaluation import run_llm_judge as m\n"
        "m._load_dotenv()\n"
    ),
    "validation_point2_llm_authentique": (
        "import runpy\n"
        "runpy.run_path(r'{root}/scripts/validation/"
        "validation_point2_llm_authentique.py')\n"
    ),
    # the .env path is an argument
    "scan_virtuous_corpus": (
        "import runpy\n"
        "from pathlib import Path\n"
        "ns = runpy.run_path(r'{root}/scripts/scan_virtuous_corpus.py')\n"
        "ns['_load_dotenv'](Path('.env').resolve())\n"
    ),
    # the .env path comes from the file's own location
    "soutenance _shared": (
        "import runpy, shutil\n"
        "from pathlib import Path\n"
        "copy = Path('examples/soutenance/_shared.py')\n"
        "copy.parent.mkdir(parents=True)\n"
        "shutil.copy(r'{root}/examples/soutenance/_shared.py', copy)\n"
        "runpy.run_path(str(copy))['bootstrap_env']()\n"
    ),
}


@pytest.mark.parametrize("name", list(_FUNCTION_LOADERS))
def test_a_function_loader_loads_quoted_values_unquoted_and_the_caller_wins(
    tmp_path, name
):
    """DoD 1 for the loaders that live in a function. ``main``:
    ``validation_point2_llm_authentique`` overwrote the caller's value, and
    ``soutenance _shared`` kept the quotes."""
    (tmp_path / ".env").write_text(_DOTENV, encoding="utf-8")
    driver = tmp_path / "driver_2487.py"
    driver.write_text(
        _FUNCTION_LOADERS[name].format(root=ROOT.as_posix()) + _PRINT,
        encoding="utf-8",
    )

    done = _run(driver, tmp_path)

    assert done.returncode == 0, done.stderr[-3000:]
    assert done.stdout.strip().splitlines()[-1] == _EXPECTED, done.stdout[-3000:]


def test_run_real_analysis_starts_on_a_dotenv_that_quotes_its_url(tmp_path):
    """DoD 4, the measured case: ``main`` raised ``ValidationError`` on
    ``OpenAISettings.base_url`` at import, before ``argparse``."""
    copy = tmp_path / "scripts" / "run_real_analysis.py"
    copy.parent.mkdir()
    copy.write_text(
        (ROOT / "scripts" / "run_real_analysis.py").read_text(encoding="utf-8-sig"),
        encoding="utf-8",
    )
    (tmp_path / ".env").write_text(
        'OPENAI_BASE_URL="https://api.openai.com/v1"\n', encoding="utf-8"
    )
    env = _child_env()
    env.pop("OPENAI_BASE_URL", None)

    done = _run(copy, tmp_path, "--help", env=env)

    assert done.returncode == 0, done.stderr[-3000:]
    assert "usage:" in done.stdout, done.stdout[-3000:]
