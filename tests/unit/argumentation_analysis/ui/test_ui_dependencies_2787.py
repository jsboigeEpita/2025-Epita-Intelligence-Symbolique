"""The notebook UIs import in the gate env, and refuse outside a kernel (#2787).

``ui/app.py`` and ``ui/extract_editor/extract_marker_editor.py`` import
``ipywidgets`` (and ``app.py`` also ``jupyter_ui_poll``) at module level. No env
spec declared either package, so ``run_orchestration --ui``, ``main_orchestrator``
and the extract tooling died on ``ModuleNotFoundError`` in the env CI builds
from ``environment.yml``. #2076 counted these modules among the import-dead and
left them there.

The CLI cannot run the UI in any case: ``configure_analysis_task`` waits for
widget clicks through ``jupyter_ui_poll``, which reads the IPython kernel.
Outside one it died on ``'NoneType' object has no attribute 'kernel'`` after
loading the definitions and building the whole UI. The guard now refuses first,
with a message that names the requirement.

These tests import the real packages. No double stands in for ``ipywidgets``:
the gap was precisely that a double stood in for it (``test_ui_fetch_surface_2536``
does so on purpose, to test something else).
"""

import asyncio
import importlib
import importlib.metadata
import re
import sys
from pathlib import Path

import pytest

ENV_SPEC = Path(__file__).resolve().parents[4] / "environment.yml"
UI_DISTRIBUTIONS = ("ipywidgets", "jupyter-ui-poll")


@pytest.mark.parametrize("dist", UI_DISTRIBUTIONS)
def test_env_spec_declares_the_ui_distribution(dist):
    """The spec CI builds from names each package the UI modules import."""
    entry = re.compile(rf"^\s*-\s*{re.escape(dist)}\s*(?:[<>=!~]|#|$)")
    lines = ENV_SPEC.read_text(encoding="utf-8").splitlines()
    declared = [line for line in lines if entry.match(line)]
    assert declared, f"environment.yml does not declare {dist} (#2787)"


@pytest.mark.parametrize(
    "module",
    [
        "argumentation_analysis.ui.app",
        "argumentation_analysis.ui.extract_editor.extract_marker_editor",
    ],
)
def test_ui_module_imports_in_this_env(module):
    """The real import succeeds, on the real packages."""
    importlib.import_module(module)
    for dist in UI_DISTRIBUTIONS:
        assert importlib.metadata.version(dist)


def test_configure_analysis_task_refuses_outside_a_kernel(monkeypatch):
    """No kernel: a RuntimeError naming the requirement, before any work.

    Loading the definitions is the first piece of work the function does, so
    it must not be reached.
    """
    app = importlib.import_module("argumentation_analysis.ui.app")

    def reached(*args, **kwargs):
        raise AssertionError("the guard must refuse before loading definitions")

    monkeypatch.setattr(app, "load_extract_definitions", reached)
    with pytest.raises(RuntimeError, match="noyau Jupyter"):
        app.configure_analysis_task()


def test_cli_ui_flag_is_refused_before_setup(monkeypatch, capsys):
    """``run_orchestration --ui`` exits on a usage error before the env setup."""
    cli = importlib.import_module("argumentation_analysis.run_orchestration")

    async def reached():
        raise AssertionError("--ui must be refused before setup_environment")

    monkeypatch.setattr(cli, "setup_environment", reached)
    # setup_logging owns the process config (basicConfig(force=True)): run for
    # real it would leave a handler on pytest's closed capture stream.
    monkeypatch.setattr(cli, "setup_logging", lambda verbose=False: None)
    monkeypatch.setattr(sys, "argv", ["run_orchestration.py", "--ui"])
    with pytest.raises(SystemExit) as exit_info:
        asyncio.run(cli.main())
    assert exit_info.value.code == 2
    assert "noyau Jupyter" in capsys.readouterr().err
