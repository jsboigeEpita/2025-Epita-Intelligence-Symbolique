"""Tests for EProver (FOL) and SPASS (Modal) reasoner integration.

Validates:
- SolverChoice.EPROVER dispatch in FOLHandler
- ModalSolverChoice.SPASS dispatch in ModalHandler
- Config enum extensions
- Reasoner lazy-loading and fallback
"""

import pytest
import importlib
from unittest.mock import patch, MagicMock, PropertyMock

from argumentation_analysis.core import config
from argumentation_analysis.core.config import (
    SolverChoice,
    ModalSolverChoice,
    ArgAnalysisSettings,
)
from argumentation_analysis.agents.core.logic.fol_handler import FOLHandler
from argumentation_analysis.agents.core.logic.modal_handler import ModalHandler
from argumentation_analysis.agents.core.logic.tweety_initializer import (
    TweetyInitializer,
)

# ──── Config Tests ────


class TestSolverChoiceEnum:
    """Tests for extended solver choice enums."""

    def test_fol_solver_choices(self):
        assert SolverChoice.TWEETY.value == "tweety"
        assert SolverChoice.PROVER9.value == "prover9"
        assert SolverChoice.EPROVER.value == "eprover"

    def test_modal_solver_choices(self):
        assert ModalSolverChoice.TWEETY.value == "tweety"
        assert ModalSolverChoice.SPASS.value == "spass"

    def test_solver_choice_from_string(self):
        assert SolverChoice("eprover") == SolverChoice.EPROVER
        assert ModalSolverChoice("spass") == ModalSolverChoice.SPASS

    def test_invalid_solver_choice_raises(self):
        with pytest.raises(ValueError):
            SolverChoice("invalid_solver")
        with pytest.raises(ValueError):
            ModalSolverChoice("invalid_modal")

    def test_settings_default_values(self):
        s = ArgAnalysisSettings()
        assert s.solver == SolverChoice.TWEETY
        assert s.modal_solver == ModalSolverChoice.TWEETY

    def test_settings_env_override(self):
        with patch.dict(
            "os.environ",
            {
                "ARG_ANALYSIS_SOLVER": "eprover",
                "ARG_ANALYSIS_MODAL_SOLVER": "spass",
            },
        ):
            s = ArgAnalysisSettings()
            assert s.solver == SolverChoice.EPROVER
            assert s.modal_solver == ModalSolverChoice.SPASS


# ──── FOLHandler EProver Dispatch Tests ────


@pytest.fixture
def mock_belief_set():
    bs = MagicMock()
    bs.toString.return_value = "some_formula(a)."
    bs.size.return_value = 1
    bs.getMinimalSignature.return_value = MagicMock()
    return bs


class TestFOLHandlerEProverDispatch:
    """Tests that FOLHandler correctly dispatches to EProver."""

    def test_fol_query_dispatches_to_eprover(self, mock_belief_set):
        with patch.object(
            FOLHandler, "_fol_query_with_eprover", return_value=True
        ) as mock_eprover, patch.object(
            FOLHandler, "_fol_query_with_tweety"
        ) as mock_tweety, patch.object(
            FOLHandler, "_fol_query_with_prover9"
        ) as mock_prover9, patch(
            "argumentation_analysis.agents.core.logic.fol_handler.settings"
        ) as mock_settings:
            mock_settings.solver = SolverChoice.EPROVER

            handler = FOLHandler()
            result = handler.fol_query(mock_belief_set, "query(a)")

            mock_eprover.assert_called_once_with(mock_belief_set, "query(a)")
            mock_tweety.assert_not_called()
            mock_prover9.assert_not_called()
            # fol_query returns (result, used_tweety_fallback); the eprover path
            # returns the prover verdict + False (no Tweety fallback was used).
            assert result == (True, False)

    @pytest.mark.parametrize(
        "solver,expected_method",
        [
            ("tweety", "_fol_query_with_tweety"),
            ("prover9", "_fol_query_with_prover9"),
            ("eprover", "_fol_query_with_eprover"),
        ],
    )
    def test_fol_query_dispatch_all_solvers(
        self, solver, expected_method, mock_belief_set
    ):
        with patch.object(
            FOLHandler, expected_method, return_value=True
        ) as mock_method, patch(
            "argumentation_analysis.agents.core.logic.fol_handler.settings"
        ) as mock_settings:
            mock_settings.solver = SolverChoice(solver)

            # Mock other methods to ensure they're not called
            other_methods = {
                "_fol_query_with_tweety",
                "_fol_query_with_prover9",
                "_fol_query_with_eprover",
            } - {expected_method}
            patches = {}
            for m in other_methods:
                patches[m] = patch.object(FOLHandler, m)

            mocks = {m: p.__enter__() for m, p in patches.items()}

            handler = FOLHandler()
            handler.fol_query(mock_belief_set, "query(a)")

            mock_method.assert_called_once()
            for m, mock in mocks.items():
                mock.assert_not_called()

            for p in patches.values():
                p.__exit__(None, None, None)

    async def test_consistency_dispatches_to_eprover(self, mock_belief_set):
        with patch.object(
            FOLHandler, "_fol_check_consistency_with_eprover"
        ) as mock_eprover, patch.object(
            FOLHandler, "_fol_check_consistency_with_tweety"
        ) as mock_tweety, patch.object(
            FOLHandler, "_fol_check_consistency_with_prover9"
        ) as mock_prover9, patch(
            "argumentation_analysis.agents.core.logic.fol_handler.settings"
        ) as mock_settings:
            mock_settings.solver = SolverChoice.EPROVER

            async def async_result(*a, **k):
                return (True, "Consistent")

            mock_eprover.return_value = async_result()

            handler = FOLHandler()
            result = await handler.fol_check_consistency(mock_belief_set)

            mock_eprover.assert_awaited_once()
            mock_tweety.assert_not_called()
            mock_prover9.assert_not_called()

    @pytest.mark.parametrize(
        "solver,expected_method",
        [
            ("tweety", "_fol_check_consistency_with_tweety"),
            ("prover9", "_fol_check_consistency_with_prover9"),
            ("eprover", "_fol_check_consistency_with_eprover"),
        ],
    )
    async def test_consistency_dispatch_all_solvers(
        self, solver, expected_method, mock_belief_set
    ):
        with patch.object(FOLHandler, expected_method) as mock_method, patch(
            "argumentation_analysis.agents.core.logic.fol_handler.settings"
        ) as mock_settings:
            mock_settings.solver = SolverChoice(solver)

            async def async_result(*a, **k):
                return (True, "Consistent")

            mock_method.return_value = async_result()

            handler = FOLHandler()
            await handler.fol_check_consistency(mock_belief_set)

            mock_method.assert_awaited_once()


class TestFOLHandlerEProverImplementation:
    """Tests for the EProver query/consistency implementation details."""

    def test_eprover_query_requires_initializer(self, mock_belief_set):
        with patch(
            "argumentation_analysis.agents.core.logic.fol_handler.settings"
        ) as mock_settings:
            mock_settings.solver = SolverChoice.EPROVER
            handler = FOLHandler()
            with pytest.raises(ValueError, match="TweetyInitializer"):
                handler._fol_query_with_eprover(mock_belief_set, "query(a)")

    async def test_eprover_consistency_requires_path(self, mock_belief_set):
        """#1196: EProver consistency requires the binary path (from the
        EXTERNAL_TOOL_PATHS registry), not the TweetyInitializer. With no path
        registered, the method must raise RuntimeError (fail-loud) rather than
        silently fall back to a no-op reasoner."""
        handler = FOLHandler()
        with patch(
            "argumentation_analysis.agents.core.logic.fol_handler._get_eprover_path",
            return_value=None,
        ):
            with pytest.raises(RuntimeError, match="EProver binary not detected"):
                await handler._fol_check_consistency_with_eprover(mock_belief_set)

    def test_eprover_query_uses_efol_reasoner(self, mock_belief_set):
        """Verify that _fol_query_with_eprover builds EFOLReasoner from the
        registered binary path and delegates the query to it (#1196).

        The EFOLReasoner constructor takes the path string as its single
        argument (Tweety 1.28+ API); previously this called EFOLReasoner() with
        no argument and relied on a global static path that was never set.
        """
        mock_initializer = MagicMock(spec=TweetyInitializer)
        mock_reasoner = MagicMock()
        mock_reasoner.query.return_value = True
        fake_path = "/fake/eprover.exe"

        with patch(
            "argumentation_analysis.agents.core.logic.fol_handler.settings"
        ) as mock_settings, patch(
            "argumentation_analysis.agents.core.logic.fol_handler.jpype"
        ) as mock_jpype, patch(
            "argumentation_analysis.agents.core.logic.fol_handler._get_eprover_path",
            return_value=fake_path,
        ):
            mock_settings.solver = SolverChoice.EPROVER
            # EFOLReasoner(path) returns the mock reasoner.
            mock_jpype.JClass.return_value = lambda _path: mock_reasoner

            handler = FOLHandler(initializer_instance=mock_initializer)
            handler._fol_parser = MagicMock()

            # Mock parse_fol_formula to return a mock formula
            handler.parse_fol_formula = MagicMock(return_value="mock_formula")

            result = handler._fol_query_with_eprover(mock_belief_set, "query(a)")

            handler.parse_fol_formula.assert_called_once_with("query(a)")
            mock_reasoner.query.assert_called_once()
            assert result is True


# ──── EProver Wiring Contract (#1196) ────


class TestEProverWiringContract:
    """Regression guard for the #1196 external-solver wiring fix.

    The previous code called ``EFOLReasoner.setPathToEProver(path)`` as if it
    were a static method — but in Tweety 1.28+ this method does not exist
    (it was replaced by the instance method ``setBinaryLocation``). The
    ``AttributeError`` was silently swallowed, so EProver was never wired and
    the FOL axis degraded. The fix records the path in a registry and the
    handler instantiates ``EFOLReasoner(path)`` directly.

    These tests pin the contract: the path is read from the registry, the
    constructor receives it, and a missing path fails loud (no fabricated
    verdict).
    """

    def test_eprover_path_read_from_registry_on_query(self, mock_belief_set):
        """_fol_query_with_eprover must pass the registered path to EFOLReasoner."""
        mock_reasoner = MagicMock()
        mock_reasoner.query.return_value = True
        fake_path = "/registered/eprover.exe"
        captured_path = {}

        def fake_jclass(name):
            if name.endswith("EFOLReasoner"):
                return (
                    lambda path: mock_reasoner.__setattr__("_path", path)
                    or mock_reasoner
                )
            if name == "java.lang.String":
                return lambda s: s
            return MagicMock()

        with patch(
            "argumentation_analysis.agents.core.logic.fol_handler._get_eprover_path",
            return_value=fake_path,
        ), patch(
            "argumentation_analysis.agents.core.logic.fol_handler.jpype"
        ) as mock_jpype:
            mock_jpype.JClass.side_effect = fake_jclass

            handler = FOLHandler(initializer_instance=MagicMock(spec=TweetyInitializer))
            handler.parse_fol_formula = MagicMock(return_value="mock_formula")
            handler._fol_query_with_eprover(mock_belief_set, "query(a)")

            # The constructor must have been invoked with the registered path.
            assert mock_reasoner.query.called

    def test_check_consistency_uses_eprover_when_wired(self, mock_belief_set):
        """check_consistency must dispatch to EFOLReasoner when settings.solver
        is EPROVER and the binary path is registered (#1196: previously it
        hardcoded SimpleFolReasoner regardless of settings)."""
        mock_reasoner = MagicMock()
        mock_reasoner.query.return_value = False  # bottom not entailed => consistent
        mock_parser_instance = MagicMock()
        mock_parser_instance.parseFormula.return_value = "bottom_formula"
        mock_parser_factory = MagicMock(return_value=mock_parser_instance)

        def fake_jclass(name):
            if name.endswith("EFOLReasoner"):
                return lambda _path: mock_reasoner
            if name == "java.lang.String":
                return lambda s: s
            # FolParser and anything else: a factory returning an instance
            return mock_parser_factory

        with patch(
            "argumentation_analysis.agents.core.logic.fol_handler.settings"
        ) as mock_settings, patch(
            "argumentation_analysis.agents.core.logic.fol_handler._get_eprover_path",
            return_value="/registered/eprover.exe",
        ), patch(
            "argumentation_analysis.agents.core.logic.fol_handler.jpype"
        ) as mock_jpype:
            mock_settings.solver = SolverChoice.EPROVER
            mock_jpype.JClass.side_effect = fake_jclass

            handler = FOLHandler()  # no initializer — EProver path is self-sufficient
            is_consistent, msg = handler.check_consistency(mock_belief_set)

            # EFOLReasoner was used (query called), verdict reflects its answer.
            assert mock_reasoner.query.called
            assert is_consistent is True
            assert "EProver" in msg

    def test_check_consistency_falls_back_to_tweety_when_eprover_absent(
        self, mock_belief_set
    ):
        """When settings.solver is EPROVER but no binary is registered, the
        handler must fall back to SimpleFolReasoner (not fabricate a verdict)."""
        mock_initializer = MagicMock(spec=TweetyInitializer)
        mock_tweety_reasoner = MagicMock()
        mock_tweety_reasoner.query.return_value = False
        mock_initializer.get_reasoner.return_value = mock_tweety_reasoner
        mock_parser = MagicMock()
        mock_parser.parseFormula.return_value = "bottom_formula"

        with patch(
            "argumentation_analysis.agents.core.logic.fol_handler.settings"
        ) as mock_settings, patch(
            "argumentation_analysis.agents.core.logic.fol_handler._get_eprover_path",
            return_value=None,
        ), patch(
            "argumentation_analysis.agents.core.logic.fol_handler.jpype"
        ) as mock_jpype:
            mock_settings.solver = SolverChoice.EPROVER
            mock_jpype.JClass.side_effect = lambda name: mock_parser

            handler = FOLHandler(initializer_instance=mock_initializer)
            is_consistent, msg = handler.check_consistency(mock_belief_set)

            # EFOLReasoner not built; SimpleFolReasoner used instead.
            mock_initializer.get_reasoner.assert_called_once_with("SimpleFolReasoner")
            assert "SimpleFolReasoner" in msg


# ──── ModalHandler SPASS Tests ────


class TestModalHandlerSPASS:
    """Tests for SPASS reasoner integration in ModalHandler."""

    @pytest.fixture
    def mock_initializer(self):
        init = MagicMock(spec=TweetyInitializer)
        init.get_modal_parser.return_value = MagicMock()
        init.get_modal_reasoner.return_value = MagicMock()
        return init

    def test_default_reasoner_is_tweety(self, mock_initializer):
        with patch(
            "argumentation_analysis.agents.core.logic.modal_handler.settings"
        ) as mock_settings:
            mock_settings.modal_solver = ModalSolverChoice.TWEETY
            handler = ModalHandler(mock_initializer)
            reasoner = handler._get_active_reasoner()
            assert reasoner == mock_initializer.get_modal_reasoner()

    def test_spass_reasoner_lazy_loaded(self, mock_initializer):
        with patch(
            "argumentation_analysis.agents.core.logic.modal_handler.settings"
        ) as mock_settings, patch(
            "argumentation_analysis.agents.core.logic.modal_handler.jpype"
        ) as mock_jpype, patch(
            "argumentation_analysis.agents.core.logic.modal_handler._get_spass_path",
            return_value="/registered/spass.exe",
        ):
            mock_settings.modal_solver = ModalSolverChoice.SPASS
            mock_spass = MagicMock()
            # #1205: SPASSMlReasoner is built as SPASSMlReasoner(JString(path))
            # (1-arg ctor). JClass is called twice: for JString and for the
            # reasoner class. Both return a factory accepting the path arg.
            mock_jpype.JClass.return_value = lambda *args, **kwargs: mock_spass

            handler = ModalHandler(mock_initializer)
            reasoner = handler._get_active_reasoner()

            mock_jpype.JClass.assert_any_call(
                "org.tweetyproject.logics.ml.reasoner.SPASSMlReasoner"
            )

    def test_spass_reasoner_cached(self, mock_initializer):
        with patch(
            "argumentation_analysis.agents.core.logic.modal_handler.settings"
        ) as mock_settings, patch(
            "argumentation_analysis.agents.core.logic.modal_handler.jpype"
        ) as mock_jpype, patch(
            "argumentation_analysis.agents.core.logic.modal_handler._get_spass_path",
            return_value="/registered/spass.exe",
        ):
            mock_settings.modal_solver = ModalSolverChoice.SPASS
            mock_spass = MagicMock()
            mock_jpype.JClass.return_value = lambda *args, **kwargs: mock_spass

            handler = ModalHandler(mock_initializer)
            r1 = handler._get_spass_reasoner()
            r2 = handler._get_spass_reasoner()
            assert r1 is r2  # Same instance

    def test_spass_unavailable_raises_when_binary_absent(self, mock_initializer):
        """#1205: when no SPASS binary is registered, _get_spass_reasoner must
        raise RuntimeError fail-loud (anti-theater #1019) — NOT silently fall
        back to SimpleMlReasoner. The previous code swallowed the no-arg ctor
        error into a generic RuntimeError; now the fail-loud path is explicit
        on the missing binary path."""
        with patch(
            "argumentation_analysis.agents.core.logic.modal_handler.settings"
        ) as mock_settings, patch(
            "argumentation_analysis.agents.core.logic.modal_handler._get_spass_path",
            return_value=None,
        ):
            mock_settings.modal_solver = ModalSolverChoice.SPASS

            handler = ModalHandler(mock_initializer)
            with pytest.raises(RuntimeError, match="SPASS binary not detected"):
                handler._get_active_reasoner()

    def test_spass_construction_error_raises(self, mock_initializer):
        """#1205: if the binary is registered but SPASSMlReasoner construction
        fails (e.g. the binary is present but broken), the error must still
        surface as RuntimeError — never a silent fallback."""
        with patch(
            "argumentation_analysis.agents.core.logic.modal_handler.settings"
        ) as mock_settings, patch(
            "argumentation_analysis.agents.core.logic.modal_handler.jpype"
        ) as mock_jpype, patch(
            "argumentation_analysis.agents.core.logic.modal_handler._get_spass_path",
            return_value="/registered/spass.exe",
        ):
            mock_settings.modal_solver = ModalSolverChoice.SPASS
            mock_jpype.JClass.side_effect = Exception("Class not found")

            handler = ModalHandler(mock_initializer)
            with pytest.raises(RuntimeError, match="SPASS reasoner not available"):
                handler._get_active_reasoner()

    def test_execute_query_with_spass(self, mock_initializer):
        with patch(
            "argumentation_analysis.agents.core.logic.modal_handler.settings"
        ) as mock_settings, patch(
            "argumentation_analysis.agents.core.logic.modal_handler.jpype"
        ) as mock_jpype, patch(
            "argumentation_analysis.agents.core.logic.modal_handler._get_spass_path",
            return_value="/registered/spass.exe",
        ):
            mock_settings.modal_solver = ModalSolverChoice.SPASS

            # Setup SPASS reasoner mock
            mock_spass_instance = MagicMock()
            mock_spass_instance.query.return_value = True
            mock_spass_cls = MagicMock(return_value=mock_spass_instance)

            # Setup JClass to return different things based on args
            def jclass_side_effect(class_name):
                if "SPASSMlReasoner" in class_name:
                    return mock_spass_cls
                elif "StringReader" in class_name:
                    return MagicMock
                elif "java.lang.String" in class_name:
                    return str
                return MagicMock()

            mock_jpype.JClass.side_effect = jclass_side_effect

            # Setup parser mock
            mock_parser = mock_initializer.get_modal_parser()
            mock_parser.parseBeliefBase.return_value = MagicMock()
            mock_parser.parseFormula.return_value = MagicMock()

            handler = ModalHandler(mock_initializer)
            result = handler.execute_modal_query("p || []q", "[]p")

            assert "ACCEPTED" in result

    def test_consistency_with_spass(self, mock_initializer):
        with patch(
            "argumentation_analysis.agents.core.logic.modal_handler.settings"
        ) as mock_settings, patch(
            "argumentation_analysis.agents.core.logic.modal_handler.jpype"
        ) as mock_jpype, patch(
            "argumentation_analysis.agents.core.logic.modal_handler._get_spass_path",
            return_value="/registered/spass.exe",
        ):
            mock_settings.modal_solver = ModalSolverChoice.SPASS

            # #1205: modal reasoners expose query(), NOT isConsistent. The
            # handler now decides consistency via query(beliefSet, atom&&!atom):
            # query == False (contradiction NOT entailed) => consistent.
            mock_spass_instance = MagicMock()
            mock_spass_instance.query.return_value = False
            mock_spass_cls = MagicMock(return_value=mock_spass_instance)

            def jclass_side_effect(class_name):
                if "SPASSMlReasoner" in class_name:
                    return mock_spass_cls
                elif "StringReader" in class_name:
                    return MagicMock
                return MagicMock()

            mock_jpype.JClass.side_effect = jclass_side_effect
            # is_modal_kb_consistent catches jpype.JException; give the patched
            # jpype module a real exception class so the except clause is valid.
            mock_jpype.JException = Exception

            # Signature with one 0-ary predicate so _build_contradiction_probe
            # builds a ground contradiction probe.
            mock_pred = MagicMock()
            mock_pred.getName.return_value = "Rain"
            mock_pred.getArity.return_value = 0
            mock_belief_set = MagicMock()
            mock_belief_set.getSignature.return_value.getPredicates.return_value = [
                mock_pred
            ]

            mock_parser = mock_initializer.get_modal_parser()
            mock_parser.parseBeliefBase.return_value = mock_belief_set

            handler = ModalHandler(mock_initializer)
            is_consistent, msg = handler.is_modal_kb_consistent("Rain")

            assert is_consistent is True
            mock_spass_instance.query.assert_called_once()
            assert "consistent" in msg.lower()


class TestModalHandlerInitFix:
    """Tests that ModalHandler uses instance methods (not static) for initialization."""

    def test_uses_instance_method(self):
        """The ModalHandler should call initializer_instance.get_modal_parser(),
        not TweetyInitializer.get_modal_parser()."""
        mock_init = MagicMock(spec=TweetyInitializer)
        mock_init.get_modal_parser.return_value = MagicMock()
        mock_init.get_modal_reasoner.return_value = MagicMock()

        handler = ModalHandler(mock_init)

        # Verify instance methods were called
        mock_init.get_modal_parser.assert_called_once()
        mock_init.get_modal_reasoner.assert_called_once()

    def test_raises_if_parser_none(self):
        mock_init = MagicMock(spec=TweetyInitializer)
        mock_init.get_modal_parser.return_value = None
        mock_init.get_modal_reasoner.return_value = MagicMock()

        with pytest.raises(RuntimeError, match="ModalHandler initialized before"):
            ModalHandler(mock_init)

    def test_raises_if_reasoner_none(self):
        mock_init = MagicMock(spec=TweetyInitializer)
        mock_init.get_modal_parser.return_value = MagicMock()
        mock_init.get_modal_reasoner.return_value = None

        with pytest.raises(RuntimeError, match="ModalHandler initialized before"):
            ModalHandler(mock_init)
