"""#1845 — the SPASS loan on ``settings.modal_solver`` must be repaid.

``_invoke_external_modal_solver`` forced ``settings.modal_solver`` to SPASS on
binary presence and NEVER restored it. ``settings`` is a module singleton, so
the override leaked process-wide: every later caller inherited a solver it did
not choose — including callers that had explicitly pinned TWEETY with both
settings (the #1339 recipe, which this site does not read at all).

Witness design: the test screens ``argumentation_analysis.core.config.settings``
with a delegating object. Reads fall through to the real singleton; the
function's ``object.__setattr__`` writes (which bypass every hook) land in the
screen's ``__dict__`` — exactly what the production site will see and restore.
The loan-repayment is asserted through the same path: after return, the value
seen through ``settings`` must be back to the pinned TWEETY.

``shutil.which("SPASS")`` is made to genuinely answer by placing a stub
executable on the test PATH (the real detection runs — no module-level mock
of shutil). The initializer fails ON PURPOSE so the repayment must survive
the exception path, which is the path main leaks through.

Born-red on main (measured): the screen's dict holds the forced SPASS after
return; the assert fails.
"""

import asyncio
import os
from unittest import mock

from argumentation_analysis.core.config import ModalSolverChoice
import argumentation_analysis.core.config as cfg
from argumentation_analysis.orchestration import invoke_callables


def _put_stub_spass_on_path(monkeypatch, tmp_path):
    """Make shutil.which("SPASS") genuinely answer, without mocking shutil."""
    stub = tmp_path / "SPASS.exe"
    stub.write_bytes(b"")  # never executed — only detected
    monkeypatch.setenv("PATH", str(tmp_path) + ";" + os.environ["PATH"])
    assert invoke_callables.shutil.which("SPASS") is not None


class _SettingsScreen:
    """Delegating screen over the real singleton.

    The production site reads ``settings.modal_solver`` (delegated to the
    real object) and writes via ``object.__setattr__`` (lands in this
    screen's __dict__, bypassing __getattr__). The fix's finally-restore
    writes back through the same channel — so what this screen's dict holds
    after the call is exactly what the production site leaves behind.
    """

    def __init__(self, real):
        object.__setattr__(self, "_real", real)

    def __getattr__(self, name):
        return getattr(object.__getattribute__(self, "_real"), name)


class TestExternalModalSolverRestoresTheSetting:
    """#1845: the force is a loan; the singleton must get it back."""

    async def test_pinned_tweety_survives_the_spass_branch(self, monkeypatch, tmp_path):
        _put_stub_spass_on_path(monkeypatch, tmp_path)

        screen = _SettingsScreen(cfg.settings)
        object.__setattr__(screen, "modal_solver", ModalSolverChoice.TWEETY)

        # The handler lane fails on purpose: the finally-restore must hold on
        # the EXCEPTION path too (that is the path main leaks through).
        fake_initializer = mock.MagicMock(
            side_effect=RuntimeError("synthetic initializer failure")
        )
        fake_bridge_cls = mock.MagicMock()
        # to_thread calls it as a SYNC function in a worker thread.
        fake_bridge_cls.return_value.execute_modal_query = mock.MagicMock(
            return_value=(None, "stub fallback verdict")
        )

        with mock.patch.object(cfg, "settings", screen), mock.patch(
            "argumentation_analysis.agents.core.logic.tweety_initializer.ready_initializer",
            fake_initializer,
        ), mock.patch(
            "argumentation_analysis.agents.core.logic.tweety_bridge.TweetyBridge",
            fake_bridge_cls,
        ):
            result = await invoke_callables._invoke_external_modal_solver(
                "[](p => q)", {}
            )

        # The call completed via the Tweety fallback — the witness is not
        # about the verdict but about what the call leaves behind.
        assert result["solver"] == "tweety"
        # #1845 né-rouge: main leaves the forced SPASS here, process-wide.
        assert screen.__dict__["modal_solver"] == ModalSolverChoice.TWEETY

    async def test_no_loan_when_solver_already_spass(self, monkeypatch, tmp_path):
        """When the setting already says SPASS there is nothing to borrow: the
        call must leave the value untouched (no force, no spurious restore)."""
        _put_stub_spass_on_path(monkeypatch, tmp_path)

        screen = _SettingsScreen(cfg.settings)
        object.__setattr__(screen, "modal_solver", ModalSolverChoice.SPASS)

        fake_initializer_mod = mock.MagicMock()
        fake_handler = mock.MagicMock()
        fake_handler.is_modal_kb_consistent = lambda kb: (True, "ok")

        with mock.patch.object(cfg, "settings", screen), mock.patch(
            "argumentation_analysis.agents.core.logic.tweety_initializer.ready_initializer",
            return_value=fake_initializer_mod,
        ), mock.patch(
            "argumentation_analysis.agents.core.logic.modal_handler.ModalHandler",
            return_value=fake_handler,
        ):
            result = await invoke_callables._invoke_external_modal_solver(
                "[](p => q)", {}
            )

        assert result["solver"] == "spass"
        assert screen.__dict__["modal_solver"] == ModalSolverChoice.SPASS
