"""Tests for FOL handler solver fallback (#949).

Verifies that when the configured external solver (eprover/prover9) is absent,
FOLHandler gracefully falls back to the in-JVM Tweety reasoner — mirroring
the modal pattern.  A ``solver_fallback`` flag is returned so callers can
track degradation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestFOLSolverFallback:
    """Test graceful solver downgrade when external binary is absent."""

    @pytest.fixture
    def handler(self):
        """Create a FOLHandler with a mock initializer."""
        from argumentation_analysis.agents.core.logic.fol_handler import FOLHandler
        from argumentation_analysis.agents.core.logic.tweety_initializer import (
            TweetyInitializer,
        )

        mock_initializer = MagicMock(spec=TweetyInitializer)
        mock_initializer.get_fol_parser.return_value = MagicMock()

        with patch(
            "argumentation_analysis.agents.core.logic.fol_handler.settings"
        ) as mock_settings:
            mock_settings.solver = MagicMock()
            mock_settings.solver.value = "eprover"
            # Force tweety path for constructor
            from argumentation_analysis.core.config import SolverChoice

            mock_settings.solver = SolverChoice.TWEETY
            handler = FOLHandler(initializer_instance=mock_initializer)
            # Now override to eprover for test
            mock_settings.solver = SolverChoice.EPROVER

        handler._initializer_instance = mock_initializer
        return handler

    @pytest.mark.asyncio
    async def test_eprover_absent_falls_back_to_tweety_consistency(self, handler):
        """When eprover binary is absent, consistency check uses Tweety fallback."""
        from argumentation_analysis.core.config import SolverChoice

        with patch(
            "argumentation_analysis.agents.core.logic.fol_handler.settings"
        ) as mock_settings:
            mock_settings.solver = SolverChoice.EPROVER

            # Mock eprover to raise RuntimeError (binary absent)
            with patch.object(
                handler,
                "_fol_check_consistency_with_eprover",
                new_callable=AsyncMock,
                side_effect=RuntimeError("EProver binary not found"),
            ):
                # Mock tweety fallback to succeed
                with patch.object(
                    handler,
                    "_fol_check_consistency_with_tweety",
                    new_callable=AsyncMock,
                    return_value=(True, "Tweety-based consistency check result: True"),
                ):
                    belief_set = MagicMock()
                    belief_set.size.return_value = 2
                    result = await handler.fol_check_consistency(belief_set)

        # Result should be (is_consistent, msg, solver_fallback=True)
        assert len(result) == 3
        is_consistent, msg, solver_fallback = result
        assert is_consistent is True
        assert (
            solver_fallback is True
        ), "solver_fallback flag must be True when degraded"
        assert "Tweety" in msg

    @pytest.mark.asyncio
    async def test_eprover_present_no_fallback(self, handler):
        """When eprover is available, no fallback occurs."""
        from argumentation_analysis.core.config import SolverChoice

        with patch(
            "argumentation_analysis.agents.core.logic.fol_handler.settings"
        ) as mock_settings:
            mock_settings.solver = SolverChoice.EPROVER

            with patch.object(
                handler,
                "_fol_check_consistency_with_eprover",
                new_callable=AsyncMock,
                return_value=(False, "EProver-based consistency check result: False"),
            ):
                belief_set = MagicMock()
                belief_set.size.return_value = 2
                result = await handler.fol_check_consistency(belief_set)

        # No fallback — result is (is_consistent, msg) from eprover directly
        assert len(result) == 2
        is_consistent, msg = result
        assert is_consistent is False
        assert "EProver" in msg

    @pytest.mark.asyncio
    async def test_tweety_path_no_fallback(self, handler):
        """When solver is Tweety directly, no fallback mechanism is needed."""
        from argumentation_analysis.core.config import SolverChoice

        with patch(
            "argumentation_analysis.agents.core.logic.fol_handler.settings"
        ) as mock_settings:
            mock_settings.solver = SolverChoice.TWEETY

            with patch.object(
                handler,
                "_fol_check_consistency_with_tweety",
                new_callable=AsyncMock,
                return_value=(True, "Tweety-based consistency check result: True"),
            ):
                belief_set = MagicMock()
                belief_set.size.return_value = 1
                result = await handler.fol_check_consistency(belief_set)

        # Direct Tweety path — 2-tuple, no fallback flag
        assert len(result) == 2
        is_consistent, msg = result
        assert is_consistent is True

    def test_eprover_absent_falls_back_to_tweety_query(self, handler):
        """When eprover binary is absent, FOL query uses Tweety fallback."""
        from argumentation_analysis.core.config import SolverChoice

        with patch(
            "argumentation_analysis.agents.core.logic.fol_handler.settings"
        ) as mock_settings:
            mock_settings.solver = SolverChoice.EPROVER

            with patch.object(
                handler,
                "_fol_query_with_eprover",
                side_effect=RuntimeError("EProver binary not found"),
            ):
                with patch.object(
                    handler,
                    "_fol_query_with_tweety",
                    return_value=True,
                ):
                    belief_set = MagicMock()
                    result = handler.fol_query(belief_set, "mortal(socrates)")

        # Result is (entailed, solver_fallback)
        entailed, solver_fallback = result
        assert entailed is True
        assert (
            solver_fallback is True
        ), "solver_fallback must be True on query degradation"

    def test_eprover_present_no_query_fallback(self, handler):
        """When eprover is available, query returns (entailed, False)."""
        from argumentation_analysis.core.config import SolverChoice

        with patch(
            "argumentation_analysis.agents.core.logic.fol_handler.settings"
        ) as mock_settings:
            mock_settings.solver = SolverChoice.EPROVER

            with patch.object(
                handler,
                "_fol_query_with_eprover",
                return_value=True,
            ):
                belief_set = MagicMock()
                result = handler.fol_query(belief_set, "mortal(socrates)")

        entailed, solver_fallback = result
        assert entailed is True
        assert (
            solver_fallback is False
        ), "solver_fallback must be False when eprover works"

    @pytest.mark.asyncio
    async def test_both_solvers_absent_raises(self, handler):
        """When both external and Tweety solvers fail, RuntimeError is raised."""
        from argumentation_analysis.core.config import SolverChoice

        with patch(
            "argumentation_analysis.agents.core.logic.fol_handler.settings"
        ) as mock_settings:
            mock_settings.solver = SolverChoice.EPROVER

            with patch.object(
                handler,
                "_fol_check_consistency_with_eprover",
                new_callable=AsyncMock,
                side_effect=RuntimeError("EProver binary not found"),
            ):
                with patch.object(
                    handler,
                    "_fol_check_consistency_with_tweety",
                    new_callable=AsyncMock,
                    side_effect=NotImplementedError("Tweety also failed"),
                ):
                    belief_set = MagicMock()
                    belief_set.size.return_value = 2
                    with pytest.raises(
                        RuntimeError, match="FOL consistency check failed"
                    ):
                        await handler.fol_check_consistency(belief_set)


# ──── FP-3 #1192 DoD: fail-loud sync consistency ────


class TestFOLCheckConsistencyFailLoud:
    """#1192: ``FOLHandler.check_consistency`` (sync path) must NEVER fabricate
    a ``consistent=True`` verdict when no reasoning happened (anti-theater
    #1019). Previously it returned ``(True, "Parsed successfully...")`` on a
    reasoner exception or a missing initializer — a false-positive consistency
    claim. It now returns ``(None, ...)`` (degraded/unknown)."""

    @pytest.fixture
    def handler(self):
        from argumentation_analysis.agents.core.logic.fol_handler import FOLHandler
        from argumentation_analysis.agents.core.logic.tweety_initializer import (
            TweetyInitializer,
        )

        mock_initializer = MagicMock(spec=TweetyInitializer)
        mock_initializer.get_fol_parser.return_value = MagicMock()
        with patch(
            "argumentation_analysis.agents.core.logic.fol_handler.settings"
        ) as mock_settings:
            from argumentation_analysis.core.config import SolverChoice

            mock_settings.solver = SolverChoice.TWEETY
            h = FOLHandler(initializer_instance=mock_initializer)
        return h

    def test_reasoner_exception_returns_degraded_not_true(self, handler):
        """When the reasoner raises, consistency is unknown (None), not True."""
        java_bs = MagicMock()
        java_bs.size.return_value = 2

        # initializer present but get_reasoner raises (simulates a Tweety
        # internal failure on the contradiction query).
        handler._initializer_instance = MagicMock()
        handler._initializer_instance.get_reasoner.side_effect = RuntimeError("boom")

        with patch.object(
            handler, "create_belief_set_from_string", return_value=java_bs
        ):
            result = handler.check_consistency(java_bs)

        is_consistent, msg = result
        assert (
            is_consistent is None
        ), "Degraded check must return None, not fabricate a True verdict"
        assert "degraded" in msg.lower() or "no consistency verdict" in msg.lower()

    def test_no_initializer_returns_degraded_not_true(self, handler):
        """Without a Tweety initializer, consistency is unknown (None), not True."""
        handler._initializer_instance = None
        java_bs = MagicMock()
        java_bs.size.return_value = 3

        with patch.object(
            handler, "create_belief_set_from_string", return_value=java_bs
        ):
            result = handler.check_consistency(java_bs)

        is_consistent, msg = result
        assert is_consistent is None
        assert "degraded" in msg.lower() or "no consistency verdict" in msg.lower()

    def test_empty_belief_set_still_consistent(self, handler):
        """An empty belief set remains trivially consistent (degraded only
        applies to non-empty KBs that cannot be reasoned about)."""
        java_bs = MagicMock()
        java_bs.size.return_value = 0
        result = handler.check_consistency(java_bs)
        is_consistent, _ = result
        assert is_consistent is True


# ──── FP-3 #1192 DoD: modal signature fix ────


class TestTweetyBridgeModalDispatch:
    """#1192: ``TweetyBridge.execute_modal_query`` previously passed 3 args to
    ``ModalHandler.execute_modal_query`` (2-arg) → TypeError on every modal
    query; and ``check_consistency`` called a non-existent
    ``modal_handler.check_consistency`` → AttributeError for K/T/S4/S5. Both
    now route to the correct handler methods."""

    def test_execute_modal_query_2arg_handler(self):
        """ModalHandler.execute_modal_query accepts exactly (self, belief_set, query)
        — no logic_type (reasoner is global). The bridge must NOT pass a 3rd arg."""
        import inspect

        from argumentation_analysis.agents.core.logic.modal_handler import (
            ModalHandler,
        )

        sig = inspect.signature(ModalHandler.execute_modal_query)
        # self + belief_set_content + query_string = 3 params
        assert len(sig.parameters) == 3, (
            "execute_modal_query must take 3 params incl. self (belief_set, query), "
            "not logic_type (reasoner is global)"
        )

    def test_modal_handler_has_no_check_consistency(self):
        """ModalHandler exposes is_modal_kb_consistent, not check_consistency."""
        from argumentation_analysis.agents.core.logic.modal_handler import (
            ModalHandler,
        )

        assert not hasattr(ModalHandler, "check_consistency"), (
            "ModalHandler must NOT expose check_consistency; "
            "TweetyBridge routes to is_modal_kb_consistent"
        )
        assert hasattr(ModalHandler, "is_modal_kb_consistent")

    def test_bridge_execute_modal_query_returns_tuple(self):
        """Bridge wrapper returns (bool, str), calling the 2-arg handler."""
        from argumentation_analysis.agents.core.logic.tweety_bridge import (
            TweetyBridge,
        )

        mock_modal = MagicMock()
        mock_modal.execute_modal_query.return_value = (
            "Tweety Result (SimpleMlReasoner): Modal Query 'p' is ACCEPTED (True)."
        )
        with patch.object(
            TweetyBridge,
            "modal_handler",
            new_callable=lambda: property(lambda self: mock_modal),
        ):
            bridge = TweetyBridge.__new__(TweetyBridge)  # bypass JVM __init__
            accepted, msg = bridge.execute_modal_query("kb", "p", logic_type="K")
        mock_modal.execute_modal_query.assert_called_once_with("kb", "p")
        assert accepted is True
        assert "ACCEPTED" in msg

    def test_bridge_check_consistency_routes_modal_to_is_consistent(self):
        """Bridge check_consistency('K') calls is_modal_kb_consistent."""
        from argumentation_analysis.agents.core.logic.tweety_bridge import (
            TweetyBridge,
        )

        mock_modal = MagicMock()
        mock_modal.is_modal_kb_consistent.return_value = (True, "ok")
        with patch.object(
            TweetyBridge,
            "modal_handler",
            new_callable=lambda: property(lambda self: mock_modal),
        ):
            bridge = TweetyBridge.__new__(TweetyBridge)
            result = bridge.check_consistency("kb", "S5")
        mock_modal.is_modal_kb_consistent.assert_called_once_with("kb")
        assert result == (True, "ok")


# ──── #1204 anti-théâtre: EProver delivery-contract sentinel guard ────


class TestEProverDeliverySentinelGuard:
    """#1204 / #1019: Tweety's ``EFOLReasoner`` ships the problem to the binary
    via ``Runtime.exec(String)`` — on some platform/E-version combos (Linux,
    E 3.x) the file never reaches the solver, E proves the *empty* theory
    ``Satisfiable`` and a genuinely **inconsistent** KB is reported *consistent*
    (a fabricated verdict, #1019). ``_eprover_delivery_is_reliable`` runs a
    known-inconsistent sentinel ``{P(a),!P(a)}`` through the SAME reasoner and
    refuses to trust eprover when the contradiction is not detected, so the
    caller falls back to the in-JVM reasoner instead of fabricating."""

    def _clear_cache(self):
        from argumentation_analysis.agents.core.logic import fol_handler

        fol_handler._EPROVER_DELIVERY_RELIABLE.clear()

    def test_reliable_when_sentinel_reported_inconsistent(self):
        """Sentinel correctly detected inconsistent (query truthy) → reliable."""
        from argumentation_analysis.agents.core.logic import fol_handler

        self._clear_cache()
        reasoner = MagicMock()
        reasoner.query.return_value = True  # contradiction entailed = inconsistent
        with patch.object(fol_handler.jpype, "JClass", return_value=MagicMock()):
            assert (
                fol_handler._eprover_delivery_is_reliable(reasoner, "/path/eprover")
                is True
            )

    def test_unreliable_when_sentinel_not_inconsistent(self):
        """Broken delivery: sentinel reported consistent (query falsy) → unreliable.
        This is the exact Linux/E-3.x fabrication the guard must catch."""
        from argumentation_analysis.agents.core.logic import fol_handler

        self._clear_cache()
        reasoner = MagicMock()
        reasoner.query.return_value = (
            False  # contradiction NOT entailed = fabricated "consistent"
        )
        with patch.object(fol_handler.jpype, "JClass", return_value=MagicMock()):
            assert (
                fol_handler._eprover_delivery_is_reliable(reasoner, "/path/eprover")
                is False
            )

    def test_unreliable_when_sentinel_raises(self):
        """A parser/JVM hiccup during the self-check → fail-loud unreliable, never trust."""
        from argumentation_analysis.agents.core.logic import fol_handler

        self._clear_cache()
        reasoner = MagicMock()
        reasoner.query.side_effect = RuntimeError("JVM boom")
        with patch.object(fol_handler.jpype, "JClass", return_value=MagicMock()):
            assert (
                fol_handler._eprover_delivery_is_reliable(reasoner, "/path/eprover")
                is False
            )

    def test_result_is_cached_per_path(self):
        """The sentinel is a one-off per binary path; the verdict is cached so the
        reasoner is probed only once (not per query)."""
        from argumentation_analysis.agents.core.logic import fol_handler

        self._clear_cache()
        reasoner = MagicMock()
        reasoner.query.return_value = True
        with patch.object(fol_handler.jpype, "JClass", return_value=MagicMock()):
            fol_handler._eprover_delivery_is_reliable(reasoner, "/path/eprover")
            # second call must NOT re-probe (cache hit)
            fol_handler._eprover_delivery_is_reliable(reasoner, "/path/eprover")
        assert reasoner.query.call_count == 1
        assert fol_handler._EPROVER_DELIVERY_RELIABLE["/path/eprover"] is True
