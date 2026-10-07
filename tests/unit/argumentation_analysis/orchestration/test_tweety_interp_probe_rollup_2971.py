"""#2971 — three witnesses for the phases that could not produce, and the
rollup that hid them.

Measured on the authorized paid pass of 06/10 (doc_A): all 39 phases
COMPLETED, ``degraded_phases = []`` — yet ``tweety_interpretation`` produced
no extract (its ``await`` on the plugin's SYNCHRONOUS methods raised
``TypeError``, swallowed by ``except Exception: pass``; the state was read
through a phantom key; the plugin was fed the raw text), ``modal_solver``
probed SPASS on PATH while the registry held the vendored binary, and no
self-declared ``degraded: True`` output ever reached the run-level rollup.

All synthetic — no JVM verdict is trusted for the red assertions (the
fallback lane is stubbed where main would otherwise consult it), no paid
pass, opaque ids only.
"""

import asyncio
from types import SimpleNamespace
from unittest import mock


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class TestTweetyInterpretationRuns:
    """#2971 part 1 — the phase produces an extract from a real state leaf."""

    @staticmethod
    def _dung_state():
        extracts = []

        def add_extract(name, text):
            extracts.append((name, text))

        return (
            SimpleNamespace(
                dung_frameworks={
                    "d1": {
                        "name": "verification_grounded",
                        "arguments": ["a1", "a2"],
                        "extensions": {"grounded": ["a1"], "preferred": ["a1", "a2"]},
                    }
                },
                fol_analysis_results=[],
                add_extract=add_extract,
            ),
            extracts,
        )

    def test_one_dung_framework_yields_the_extract(self):
        """The issue's witness: on main, no extract; after the fix, one.

        Also the sync-contract guard: an ``await`` regression hands the
        join a coroutine repr, not an interpretation.
        """
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_tweety_interpretation,
        )
        from argumentation_analysis.orchestration.state_writers import (
            _write_tweety_interpretation_to_state,
        )

        state, extracts = self._dung_state()
        ctx = {"_state_object": state}
        out = _run(_invoke_tweety_interpretation("texte du document", ctx))

        assert out.get("interpretation"), "the phase produced nothing"
        assert "coroutine" not in out["interpretation"].lower()
        assert "a1" in out["interpretation"], "the Dung verdict is interpreted"

        _write_tweety_interpretation_to_state(out, state, ctx)
        names = [n for n, _t in extracts]
        assert "formal_interpretation" in names, "no extract ever written"

    def test_no_state_object_is_honest_unavailable(self):
        """Control: without ``_state_object`` the phase says so — and that
        reason is now TRUE (nothing was read), not a false blame."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_tweety_interpretation,
        )

        out = _run(_invoke_tweety_interpretation("texte", {}))
        assert out.get("status") == "unavailable"
        assert out.get("reason") == "insufficient_upstream_formal_data"
        assert not out.get("interpretation")

    def test_fol_consistency_entry_is_not_a_query_verdict(self):
        """The state's FOL leaf carries KB-consistency entries — feeding
        them to the plugin's query interpreter would fabricate an
        entailment verdict. The interpretation speaks Dung, never
        « requête », for those entries."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_tweety_interpretation,
        )

        state, _ = self._dung_state()
        state.fol_analysis_results = [
            {"consistent": True, "message": "coherent", "formulas": ["P(a)"]},
        ]
        out = _run(_invoke_tweety_interpretation("texte", {"_state_object": state}))
        assert "a1" in out.get("interpretation", ""), "Dung still interpreted"
        assert (
            "requête" not in out["interpretation"]
        ), "a consistency entry was read as a query verdict"

    def test_fol_entry_with_the_query_shape_is_interpreted(self):
        """Positive control: an entry that DOES carry the query contract
        (``accepted``/``query``) is interpreted through it."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_tweety_interpretation,
        )

        state = SimpleNamespace(
            dung_frameworks={},
            fol_analysis_results=[
                {"accepted": True, "query": "q1", "message": "deduit"}
            ],
        )
        out = _run(_invoke_tweety_interpretation("texte", {"_state_object": state}))
        assert "q1" in out.get(
            "interpretation", ""
        ), "a real query result is not interpreted"


class TestModalSolverProbeRegistry:
    """#2971 part 2 — one availability probe per tool: the registry."""

    @staticmethod
    def _stub_both_lanes(fake_handler_reply=(True, "ok")):
        """Stub the SPASS handler lane AND the TweetyBridge fallback so the
        chosen LANE (not a JVM verdict) is the measured signal."""
        handler_cls = mock.MagicMock()
        handler_cls.return_value.is_modal_kb_consistent = mock.MagicMock(
            return_value=fake_handler_reply
        )
        bridge_cls = mock.MagicMock()
        bridge_cls.return_value.execute_modal_query = mock.MagicMock(
            return_value=(None, "stub fallback")
        )
        import argumentation_analysis.agents.core.logic.tweety_bridge as tb_mod
        import argumentation_analysis.agents.core.logic.modal_handler as mh_mod

        return (
            mock.patch.object(mh_mod, "ModalHandler", handler_cls),
            mock.patch.object(tb_mod, "TweetyBridge", bridge_cls),
            handler_cls,
        )

    def test_registered_spass_off_path_takes_the_spass_lane(self):
        """The issue's witness: SPASS registered (vendored shape) but absent
        from PATH → on main, unavailable; after the fix, the SPASS lane."""
        import argumentation_analysis.core.jvm_setup as jvm_setup
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_external_modal_solver,
        )
        from argumentation_analysis.agents.core.logic import tweety_initializer

        spass_lane, tweety_lane, handler_cls = self._stub_both_lanes()
        with mock.patch.object(
            jvm_setup, "EXTERNAL_TOOL_PATHS", {"spass": "X:/fake/SPASS.exe"}
        ), mock.patch.object(
            tweety_initializer, "ready_initializer", mock.MagicMock()
        ), spass_lane, tweety_lane:
            out = _run(
                _invoke_external_modal_solver(
                    "[](p)", {"phase_modal_output": {"formulas": ["[](p)"]}}
                )
            )
        assert (
            out["solver"] == "spass"
        ), "a registered binary was declared unavailable (PATH-only probe)"
        assert handler_cls.return_value.is_modal_kb_consistent.called

    def test_unregistered_spass_is_honestly_unavailable(self):
        """Positive control: neither registered nor on PATH → not the SPASS
        lane — the fallback decides."""
        import argumentation_analysis.core.jvm_setup as jvm_setup
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_external_modal_solver,
        )

        spass_lane, tweety_lane, _handler = self._stub_both_lanes()
        with mock.patch.object(
            jvm_setup, "EXTERNAL_TOOL_PATHS", {}
        ), spass_lane, tweety_lane:
            out = _run(
                _invoke_external_modal_solver(
                    "[](p)", {"phase_modal_output": {"formulas": ["[](p)"]}}
                )
            )
        assert out["solver"] != "spass"


class TestDegradedRollupSeesSelfDeclared:
    """#2971 part 3 — a COMPLETED phase that declares itself degraded in its
    output is visible at run level."""

    @staticmethod
    def _executor():
        from argumentation_analysis.orchestration.workflow_dsl import (
            PhaseResult,
            PhaseStatus,
            WorkflowExecutor,
        )

        return WorkflowExecutor(registry=object()), PhaseResult, PhaseStatus

    def test_completed_self_declared_degraded_is_listed(self):
        exec_, PhaseResult, PhaseStatus = self._executor()
        results = {
            "modal_solver": PhaseResult(
                "modal_solver",
                PhaseStatus.COMPLETED,
                "external_modal_solving",
                output={"valid": None, "degraded": True},
            )
        }
        degraded, degraded_phases, _caps = exec_._compute_workflow_degraded(
            results, None
        )
        assert degraded is True
        assert "modal_solver" in degraded_phases

    def test_completed_clean_output_is_not_listed(self):
        """Control: a decided output (``degraded`` absent or False) never
        lands in the list — a healthy phase is not degraded."""
        exec_, PhaseResult, PhaseStatus = self._executor()
        results = {
            "p": PhaseResult("p", PhaseStatus.COMPLETED, "cap", output={"valid": True}),
            "q": PhaseResult(
                "q",
                PhaseStatus.COMPLETED,
                "cap",
                output={"degraded": False},
            ),
        }
        degraded, degraded_phases, _caps = exec_._compute_workflow_degraded(
            results, None
        )
        assert degraded is False
        assert degraded_phases == []


class TestPreflightReadsTheRegistry:
    """#2971 part 2b — the preflight warns from the registry, not PATH."""

    def test_registered_tools_warn_nothing(self, monkeypatch, caplog):
        """A run whose registry holds the tools must not be told they are
        missing — the false warning is the defect (measured: preflight
        warned, the run then used SPASS through its registered path)."""
        import argumentation_analysis.core.jvm_setup as jvm_setup
        import logging

        from argumentation_analysis.orchestration import invoke_callables

        monkeypatch.setattr(invoke_callables, "_SOLVER_PREFLIGHT_CHECKED", False)
        with mock.patch.object(
            jvm_setup,
            "EXTERNAL_TOOL_PATHS",
            {"eprover": "X:/e", "spass": "X:/s"},
        ):
            with caplog.at_level(logging.WARNING, logger="UnifiedPipeline"):
                invoke_callables._preflight_solver_check()
        assert not [
            r for r in caplog.records if "External solvers" in r.message
        ], "the preflight warned about solvers the registry holds"

    def test_empty_registry_warns_naming_the_tools(self, monkeypatch, caplog):
        import argumentation_analysis.core.jvm_setup as jvm_setup
        import logging

        from argumentation_analysis.orchestration import invoke_callables

        monkeypatch.setattr(invoke_callables, "_SOLVER_PREFLIGHT_CHECKED", False)
        with mock.patch.object(jvm_setup, "EXTERNAL_TOOL_PATHS", {}):
            with caplog.at_level(logging.WARNING, logger="UnifiedPipeline"):
                invoke_callables._preflight_solver_check()
        warnings = [r for r in caplog.records if "External solvers" in r.message]
        assert warnings, "an empty registry must warn"
        assert "SPASS (modal)" in warnings[0].message
        assert "eprover (FOL)" in warnings[0].message
