# -*- coding: utf-8 -*-
"""#2472 — a value the caller set wins over the root ``.env``, even ``""``.

Measured on ``main``: every pytest process loaded the root ``.env`` with
``override=True`` in ``pytest_configure`` (``ensure_env`` ->
``EnvironmentManager``), so ``OPENAI_API_KEY= pytest ...`` ran with the key of
the ``.env`` file. A keyless run on a keyed checkout was impossible without
moving the file aside.

The contract kept from #1295: the root ``.env`` still replaces a value set
in-process before it (a sub-``.env`` loaded first by a module-level
``load_dotenv()``, ``test_dotenv_loading.py``). What changes: it no longer
replaces a value the process was started with.

The probes run in child processes, because the caller's environment is what a
process is started with. They point ``_find_repo_root`` at a temporary root, so
they need no ``.env`` on the seat and run the same in CI.
"""

import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

import project_core.managers.environment_manager as em

REPO = Path(__file__).resolve().parents[4]

EMPTIED = "ISSUE_2472_EMPTIED"  # the caller sets it to ""
CALLER = "ISSUE_2472_CALLER"  # the caller sets it to "from-caller"
ONLY_IN_DOTENV = "ISSUE_2472_ONLY_IN_DOTENV"  # the caller does not set it
ONLY_IN_DOTENV_TEST = "ISSUE_2472_ONLY_IN_DOTENV_TEST"
# The caller sets it, then a sub-.env replaces it in-process (#1295).
REPLACED = "ISSUE_2472_REPLACED_IN_PROCESS"
NAMES = (EMPTIED, CALLER, ONLY_IN_DOTENV)
EXPECTED = {EMPTIED: "", CALLER: "from-caller", ONLY_IN_DOTENV: "from-dotenv"}


def _root(tmp_path: Path) -> Path:
    root = tmp_path / "root"
    root.mkdir()
    (root / ".env").write_text(
        "".join(f"{name}=from-dotenv\n" for name in NAMES), encoding="utf-8"
    )
    return root


def _caller_env(**extra: str) -> dict:
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in NAMES + (ONLY_IN_DOTENV_TEST, REPLACED)
    }
    env[EMPTIED] = ""
    env[CALLER] = "from-caller"
    env["PYTHONIOENCODING"] = "utf-8"
    env.update(extra)
    return env


_PROBE = r"""
import json, os, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
names = sys.argv[3].split(",")
before = {k: os.environ.get(k) for k in names}
import project_core.managers.environment_manager as em
em._find_repo_root = lambda: Path(sys.argv[2])
os.environ[sys.argv[4]] = "from-sub-env"  # a sub-.env loaded before the root one
em.EnvironmentManager()
after = {k: os.environ.get(k) for k in names}
print("PROBE=" + json.dumps({"before": before, "after": after}))
"""


def test_the_environment_manager_keeps_what_the_caller_set(tmp_path):
    """The root ``.env`` fills what the caller left unset and replaces what a
    sub-``.env`` set in-process (#1295), but not what the caller set."""
    root = _root(tmp_path)
    with (root / ".env").open("a", encoding="utf-8") as fh:
        fh.write(f"{REPLACED}=from-dotenv\n")
    names = NAMES + (REPLACED,)
    proc = subprocess.run(
        [sys.executable, "-c", _PROBE, str(REPO), str(root), ",".join(names), REPLACED],
        capture_output=True,
        text=True,
        env=_caller_env(**{REPLACED: "from-caller"}),
        cwd=str(REPO),
        timeout=300,
    )
    lines = [l for l in proc.stdout.splitlines() if l.startswith("PROBE=")]
    assert lines, f"no probe output — stderr tail: {proc.stderr[-600:]!r}"
    probe = json.loads(lines[-1][len("PROBE=") :])
    # Control: the child did receive the caller's values, "" included.
    assert probe["before"] == {
        EMPTIED: "",
        CALLER: "from-caller",
        ONLY_IN_DOTENV: None,
        REPLACED: "from-caller",
    }
    assert probe["after"] == {**EXPECTED, REPLACED: "from-dotenv"}


_PLUGIN = r"""
import json, os
from pathlib import Path

import project_core.managers.environment_manager as em

em._find_repo_root = lambda: Path(os.environ["ISSUE_2472_ROOT"])


def pytest_sessionstart(session):
    role = os.environ.get("PYTEST_XDIST_WORKER", "controller")
    names = ("ISSUE_2472_EMPTIED", "ISSUE_2472_CALLER", "ISSUE_2472_ONLY_IN_DOTENV",
             "ISSUE_2472_ONLY_IN_DOTENV_TEST")
    out = Path(os.environ["ISSUE_2472_OUT"]) / f"{role}.json"
    out.write_text(json.dumps({k: os.environ.get(k) for k in names}), encoding="utf-8")
"""


def _run_child_pytest(tmp_path: Path, root: Path, *args: str) -> dict:
    """Start a child pytest session on this file that loads the real conftests,
    and return what each process of that session sees after ``pytest_configure``.
    It deselects every test: the probe is the session start, not a test."""
    plugin_dir = tmp_path / "plugin"
    plugin_dir.mkdir()
    (plugin_dir / "issue_2472_probe_plugin.py").write_text(_PLUGIN, encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    env = _caller_env(
        ISSUE_2472_ROOT=str(root),
        ISSUE_2472_OUT=str(out),
        PYTHONPATH=os.pathsep.join([str(plugin_dir), str(REPO)]),
    )
    env.pop("PYTEST_XDIST_WORKER", None)
    env.pop("PYTEST_ADDOPTS", None)
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(Path(__file__).relative_to(REPO)),
            "-q",
            "-k",
            "issue_2472_selects_nothing",
            "-p",
            "issue_2472_probe_plugin",
            "-p",
            "no:cacheprovider",
            "--disable-jvm-session",
            *args,
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(REPO),
        timeout=600,
    )
    seen = {
        p.stem: json.loads(p.read_text(encoding="utf-8")) for p in out.glob("*.json")
    }
    assert seen, (
        f"the child session reported nothing (rc={proc.returncode}) — "
        f"stdout tail: {proc.stdout[-600:]!r}, stderr tail: {proc.stderr[-600:]!r}"
    )
    return seen


def test_a_pytest_session_and_its_worker_keep_what_the_caller_set(tmp_path):
    """The real harness: ``tests/conftest.py``'s ``pytest_configure`` loads the
    root ``.env`` through ``ensure_env``. ``OPENAI_API_KEY= pytest ...`` now
    runs keyless, and the keys the caller did not set still come from ``.env``.

    An xdist worker is started with the controller's environment, after the
    controller's ``pytest_configure``: it must see the caller's values too."""
    seen = _run_child_pytest(tmp_path, _root(tmp_path), "-n", "1")
    assert set(seen) == {"controller", "gw0"}
    for role, values in seen.items():
        got = {k: v for k, v in values.items() if k in NAMES}
        assert got == EXPECTED, role


def test_allow_dotenv_layers_env_test_but_the_caller_still_wins(tmp_path):
    """``--allow-dotenv`` layers ``.env.test`` over the root ``.env``; a value
    the caller set wins over both."""
    root = _root(tmp_path)
    (root / ".env.test").write_text(
        f"{EMPTIED}=from-dotenv-test\n{CALLER}=from-dotenv-test\n"
        f"{ONLY_IN_DOTENV_TEST}=from-dotenv-test\n",
        encoding="utf-8",
    )
    seen = _run_child_pytest(tmp_path, root, "--allow-dotenv")
    assert seen["controller"] == {**EXPECTED, ONLY_IN_DOTENV_TEST: "from-dotenv-test"}


@pytest.mark.parametrize(
    "caller_value, warned",
    [("sk-caller-OLD-1234", True), ("", False), ("sk-root-NEW-5678", False)],
    ids=["a-different-key", "keyless", "the-same-key"],
)
def test_a_caller_key_that_shadows_the_root_env_is_reported(
    tmp_path, caplog, caller_value, warned
):
    """A stale key exported in the shell now beats the root ``.env``, as a
    sub-``.env`` did before #1295: the divergence is reported, masked."""
    root = tmp_path / "root"
    root.mkdir()
    (root / ".env").write_text("OPENAI_API_KEY=sk-root-NEW-5678\n", encoding="utf-8")
    env = {"OPENAI_API_KEY": caller_value}
    with patch.dict("os.environ", env, clear=True), patch.object(
        em, "_CALLER_ENVIRONMENT", {em._env_key(k): v for k, v in env.items()}
    ), patch.object(em, "_find_repo_root", return_value=root), patch.object(
        em, "_SECONDARY_ENV_RELPATHS", []
    ):
        with caplog.at_level(logging.WARNING, logger=em.__name__):
            em.EnvironmentManager()
        assert os.environ["OPENAI_API_KEY"] == caller_value

    messages = [
        m for m in (r.getMessage() for r in caplog.records) if "set by the caller" in m
    ]
    assert bool(messages) is warned, messages
    for message in messages:
        assert "OLD-1234" not in message and "NEW-5678" not in message
