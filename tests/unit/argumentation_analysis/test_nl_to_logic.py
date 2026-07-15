"""
Tests for NL-to-formal-logic translation service (#173).

Tests the translate-validate-retry pipeline, heuristic fallback,
Python validation, and pipeline integration.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# ── Service unit tests ───────────────────────────────────────────────────


class TestNLToLogicTranslator:
    """Tests for NLToLogicTranslator service."""

    def _make_translator(self, **kwargs):
        from argumentation_analysis.services.nl_to_logic import NLToLogicTranslator

        return NLToLogicTranslator(**kwargs)

    # ── Heuristic fallback tests ─────────────────────────────────────

    def test_heuristic_pl_translation(self):
        """Heuristic produces valid PL formula from multi-sentence text."""
        translator = self._make_translator(logic_type="propositional")
        result = translator._translate_heuristic(
            "Rain causes wet ground. Wet ground leads to slippery roads. "
            "Slippery roads are dangerous for drivers.",
            "propositional",
        )
        assert result.is_valid is True
        assert result.logic_type == "propositional"
        assert result.confidence == 0.3
        assert "=>" in result.formula
        assert len(result.variables) >= 2

    def test_heuristic_fol_translation(self):
        """Heuristic produces FOL predicates from text."""
        translator = self._make_translator(logic_type="fol")
        result = translator._translate_heuristic(
            "Socrates is a human being. All humans are mortal creatures.",
            "fol",
        )
        assert result.is_valid is True
        assert result.logic_type == "fol"
        assert result.confidence == 0.2
        assert "(" in result.formula  # has predicates

    def test_heuristic_single_sentence(self):
        """Heuristic handles single sentence gracefully."""
        translator = self._make_translator()
        result = translator._translate_heuristic(
            "This argument is about climate change and rising temperatures.",
            "propositional",
        )
        assert result.is_valid is True
        assert result.formula  # Non-empty

    # ── Python validation tests ──────────────────────────────────────

    def test_validate_pl_valid(self):
        """Valid PL formula passes Python validation."""
        translator = self._make_translator()
        is_valid, msg = translator._validate_pl_python("p && (p => q)")
        assert is_valid is True

    def test_validate_pl_unmatched_parens(self):
        """Unmatched parentheses are detected."""
        translator = self._make_translator()
        is_valid, msg = translator._validate_pl_python("p && (q => r")
        assert is_valid is False
        assert "parenthes" in msg.lower()

    def test_validate_pl_invalid_token(self):
        """Invalid tokens in PL formula are detected."""
        translator = self._make_translator()
        is_valid, msg = translator._validate_pl_python("p && 123abc")
        assert is_valid is False
        assert "Invalid token" in msg

    def test_validate_pl_empty(self):
        """Empty formula is invalid."""
        translator = self._make_translator()
        is_valid, msg = translator._validate_pl_python("")
        assert is_valid is False

    def test_validate_fol_valid(self):
        """Valid FOL formula passes Python validation."""
        translator = self._make_translator()
        is_valid, msg = translator._validate_fol_python(
            "forall X: (Human(X) => Mortal(X)); Human(socrates)"
        )
        assert is_valid is True

    def test_validate_fol_no_predicates(self):
        """FOL formula without predicates is invalid."""
        translator = self._make_translator()
        is_valid, msg = translator._validate_fol_python("x && y")
        assert is_valid is False
        assert "predicate" in msg.lower()

    def test_validate_fol_unmatched_parens(self):
        """FOL with unmatched parentheses is invalid."""
        translator = self._make_translator()
        is_valid, msg = translator._validate_fol_python("Human(socrates")
        assert is_valid is False

    # ── Consistency checking (Python fallback) ───────────────────────

    def test_consistency_no_contradiction(self):
        """No contradictions → consistent."""
        translator = self._make_translator()
        is_consistent, msg = translator._check_consistency_python(
            ["p", "q", "r"], "propositional"
        )
        assert is_consistent is True

    def test_consistency_with_contradiction(self):
        """Direct contradiction detected."""
        translator = self._make_translator()
        is_consistent, msg = translator._check_consistency_python(
            ["p", "!p"], "propositional"
        )
        assert is_consistent is False
        assert "contradiction" in msg.lower()

    # ── Operator normalization ───────────────────────────────────────

    def test_normalize_operators(self):
        """Unicode operators are replaced with ASCII."""
        from argumentation_analysis.services.nl_to_logic import normalize_operators

        result = normalize_operators("∀X: (Human(X) → Mortal(X)) ∧ ¬Dead(X)")
        assert "forall" in result
        assert "=>" in result
        assert "&&" in result
        assert "!" in result

    # ── Async translate (with mock LLM) ──────────────────────────────

    @pytest.mark.asyncio
    async def test_translate_no_api_key_uses_heuristic(self):
        """Without API key, translate falls back to heuristic."""
        translator = self._make_translator()
        # ATT-1 #1336: collection-order pollution — patching os.environ is not
        # enough in the full suite (a prior test leaks a mock/state that re-
        # exposes an api_key, routing to the LLM path). Make this robust by
        # patching the AsyncOpenAI constructor to raise (option B, approved
        # coord R558): translate() catches and falls back to heuristic, so this
        # tests the "LLM unavailable → heuristic" intent hermetically,
        # independent of ambient env / leaked mocks.
        with patch("openai.AsyncOpenAI", side_effect=RuntimeError("no key")):
            result = await translator.translate(
                "All men are mortal. Socrates is a man. Therefore Socrates is mortal.",
                logic_type="propositional",
            )
        assert result.is_valid is True
        # Heuristic markers (#1019 anti-théâtre): the heuristic path sets
        # confidence=0.3 and a "Heuristic translation (no LLM)" message. Assert
        # both so a silent LLM-path leak (confidence=0.7+, LLM message) fails
        # loud rather than passing on the wrong branch.
        assert result.confidence == 0.3
        assert "Heuristic" in result.validation_message

    @pytest.mark.asyncio
    async def test_translate_with_mock_llm(self):
        """LLM translation produces valid result when API succeeds."""
        translator = self._make_translator()

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = (
            '{"formula": "mortal && human", '
            '"variables": {"mortal": "all men are mortal", "human": "Socrates is human"}, '
            '"confidence": 0.85}'
        )

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        async def mock_validate(formula, logic_type, **kwargs):
            return (True, "Valid (mocked)")

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=False):
            with patch("openai.AsyncOpenAI", return_value=mock_client):
                with patch.object(translator, "_validate_formula", mock_validate):
                    result = await translator.translate(
                        "All men are mortal. Socrates is a man.",
                        logic_type="propositional",
                    )

        assert result.is_valid is True
        assert result.formula == "mortal && human"
        assert result.confidence == 0.85
        assert result.attempts == 1

    @pytest.mark.asyncio
    async def test_translate_retry_on_invalid(self):
        """LLM retries when first attempt produces invalid formula."""
        translator = self._make_translator(max_retries=2)

        # First response: invalid (unmatched parens)
        bad_response = MagicMock()
        bad_response.choices = [MagicMock()]
        bad_response.choices[0].message.content = (
            '{"formula": "p && (q", "variables": {"p": "x"}, "confidence": 0.5}'
        )

        # Second response: valid
        good_response = MagicMock()
        good_response.choices = [MagicMock()]
        good_response.choices[0].message.content = (
            '{"formula": "p && q && r", "variables": {"p": "x", "q": "y", "r": "z"}, "confidence": 0.8}'
        )

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=[bad_response, good_response]
        )

        # Use Python validation (not Tweety) for predictable behavior
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=False):
            with patch("openai.AsyncOpenAI", return_value=mock_client):
                with patch.object(
                    translator,
                    "_validate_formula",
                    side_effect=[
                        (False, "Unmatched parentheses"),  # first call: invalid
                        (True, "Valid (mocked)"),  # second call: valid
                    ],
                ):
                    result = await translator.translate(
                        "Some argument text here that is long enough.",
                        logic_type="propositional",
                    )

        assert result.is_valid is True
        assert result.attempts == 2

    # ── Batch translation ────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_translate_batch_heuristic(self):
        """Batch translation works with heuristic fallback."""
        translator = self._make_translator()
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}, clear=False):
            batch = await translator.translate_batch(
                [
                    "Rain causes wet ground and slippery conditions.",
                    "Climate change increases extreme weather events significantly.",
                ],
                logic_type="propositional",
            )
        assert len(batch.translations) == 2
        assert all(t.is_valid for t in batch.translations)

    @pytest.mark.asyncio
    async def test_translate_batch_skips_short(self):
        """Batch skips arguments shorter than 10 chars."""
        translator = self._make_translator()
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}, clear=False):
            batch = await translator.translate_batch(
                ["short", "This is a sufficiently long argument about something."],
                logic_type="propositional",
            )
        assert len(batch.translations) == 1

    # ── #1457: NL→modal silent collapse guard ────────────────────────

    @pytest.mark.asyncio
    async def test_modal_formula_without_box_or_diamond_is_honest_absent_1457(self):
        """#1457 — probe `check_consistency("K", "p => q")` returns
        ``(True, "consistent")`` (Tweety accepts any syntactically valid
        K-modal formula, including material implications and bare atoms).
        The LLM sometimes emits ``"p => q"`` / ``"p"`` for ``logic_type=modal``
        when the source text has modal *flavor* but no genuine necessity /
        possibility — that is honest-absent (the validator below would
        false-green it as a valid modal belief set). The guard at
        ``_translate_with_llm`` must catch this BEFORE retrying and return
        the same honest-absent sentinel as the EMPTY-formulas branch:
        ``is_valid=True`` + ``validation_message="No modal operator in
        formulas (honest absent)"`` + ``formula=""`` + ``confidence=0.0``.
        Critically: NOT a fabricated modal verdict (anti-théâtre #1019).
        """
        translator = self._make_translator()

        # LLM emits ONLY material implications / bare atoms — no [] / <>.
        # Both are precisely the cases the empirical probe confirmed Tweety
        # silently accepts (verdict=VALID, msg="Knowledge base is
        # consistent (spass)" for both ``p => q`` and ``p``).
        bad_modal_response = MagicMock()
        bad_modal_response.choices = [MagicMock()]
        bad_modal_response.choices[0].message.content = (
            '{"logic_type": "modal", '
            '"constants": ["p", "q"], '
            '"formulas": ["p => q"], '
            '"confidence": 0.7}'
        )

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=bad_modal_response)

        # The guard fires BEFORE ``_validate_formula`` — the mock below would
        # false-green any input if it were reached. Asserting it is NEVER
        # called proves the guard short-circuits at the source.
        validate_call_count = 0

        async def fail_validate(*args, **kwargs):
            nonlocal validate_call_count
            validate_call_count += 1
            return (True, "THIS MUST NEVER RUN — guard should short-circuit")

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=False):
            with patch("openai.AsyncOpenAI", return_value=mock_client):
                with patch.object(translator, "_validate_formula", fail_validate):
                    result = await translator.translate(
                        "If it rains, the ground gets wet — this is a necessary consequence.",
                        logic_type="modal",
                    )

        # Honest-absent sentinel — NOT a false-green modal verdict.
        assert result.is_valid is True, (
            "Without modal operator, the LLM response is honest-absent "
            "(is_valid=True with empty formula + 0.0 confidence), NOT invalid."
        )
        assert result.formula == "", (
            f"#1457 REGRESSION: silent modal collapse — formula {result.formula!r} "
            f"without []/<> was accepted as a modal belief set (anti-théâtre #1019)."
        )
        assert result.confidence == 0.0
        assert "honest absent" in result.validation_message.lower()
        # The validator MUST NOT have been reached — the guard short-circuits
        # before retrying, so no JVM call, no fabricated Tweety verdict.
        assert validate_call_count == 0, (
            f"#1457 REGRESSION: _validate_formula called {validate_call_count} "
            f"time(s); guard must short-circuit BEFORE validation (no retry loop)."
        )

    @pytest.mark.asyncio
    async def test_modal_formula_with_box_or_diamond_passes_guard_1457(self):
        """#1457 — companion control: the new guard must NOT reject genuine
        modal formulas carrying ``[]`` or ``<>``. We mock ``_validate_formula``
        to a no-op (True, ...) and assert that (a) the guard lets them
        through, (b) the resulting TranslationResult has the formula from
        ``_build_modal_belief_set`` (NOT empty), (c) confidence is preserved
        (NOT zeroed — that's the honest-absent signal from the guard)."""
        translator = self._make_translator()

        good_modal_response = MagicMock()
        good_modal_response.choices = [MagicMock()]
        good_modal_response.choices[0].message.content = (
            '{"logic_type": "modal", '
            '"constants": ["p", "q"], '
            '"formulas": ["[](p => q)", "<>(p)"], '
            '"confidence": 0.8}'
        )

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=good_modal_response
        )

        async def passthrough_validate(formula, logic_type, **kwargs):
            # Mimic the real Tweety happy path: VALID modal belief set.
            return (True, "Valid modal belief set (mocked)")

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=False):
            with patch("openai.AsyncOpenAI", return_value=mock_client):
                with patch.object(
                    translator, "_validate_formula", passthrough_validate
                ):
                    result = await translator.translate(
                        "It is necessarily true that p implies q, and p is possible.",
                        logic_type="modal",
                    )

        # Guard did NOT trigger — formula carried [] / <>, so the genuine
        # modal path ran end-to-end.
        assert result.is_valid is True
        assert result.formula, (
            "#1457 REGRESSION: genuine modal formulas ([] / <>) were rejected "
            "by the guard — formula is unexpectedly empty."
        )
        # No "honest absent" message — the guard did not short-circuit.
        assert "honest absent" not in result.validation_message.lower()
        # Confidence preserved (NOT the honest-absent zeroing).
        assert result.confidence == 0.8
        # _build_modal_belief_set prefix: type(...) declarations + formulas.
        assert "type(" in result.formula
        assert "[](p => q)" in result.formula or "[]( p => q )" in result.formula
        assert "<>(p)" in result.formula or "<>( p )" in result.formula


# ── Pipeline integration tests ───────────────────────────────────────


class TestNLToLogicPipelineIntegration:
    """Tests for NL-to-logic integration in unified pipeline."""

    def test_capability_registered(self):
        """nl_to_logic_translation capability is registered in setup_registry."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            setup_registry,
        )

        registry = setup_registry(include_optional=False)
        # Check capability exists
        found = registry.find_agents_for_capability("nl_to_logic_translation")
        assert found or "nl_to_logic_service" in str(registry._registrations.keys())

    def test_state_writer_in_dict(self):
        """nl_to_logic_translation has a state writer."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            CAPABILITY_STATE_WRITERS,
        )

        assert "nl_to_logic_translation" in CAPABILITY_STATE_WRITERS

    def test_workflow_in_catalog(self):
        """nl_to_logic workflow appears in the catalog."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            get_workflow_catalog,
        )

        catalog = get_workflow_catalog()
        assert "nl_to_logic" in catalog

    def test_state_has_nl_to_logic_field(self):
        """UnifiedAnalysisState has nl_to_logic_translations field."""
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        state = UnifiedAnalysisState("test text")
        assert hasattr(state, "nl_to_logic_translations")
        assert isinstance(state.nl_to_logic_translations, list)

    def test_state_add_translation(self):
        """State correctly stores NL-to-logic translations."""
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        state = UnifiedAnalysisState("test text")
        tr_id = state.add_nl_to_logic_translation(
            original_text="All men are mortal",
            formula="forall X: (Man(X) => Mortal(X))",
            logic_type="fol",
            is_valid=True,
            variables={"Man": "is a man", "Mortal": "is mortal"},
            confidence=0.85,
        )
        assert tr_id.startswith("nll")
        assert len(state.nl_to_logic_translations) == 1
        assert state.nl_to_logic_translations[0]["is_valid"] is True

    def test_state_writer_function(self):
        """State writer correctly populates state from pipeline output."""
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_nl_to_logic_to_state,
        )

        state = UnifiedAnalysisState("test text")
        output = {
            "translations": [
                {
                    "original_text": "Rain implies wet ground",
                    "formula": "rain => wet",
                    "logic_type": "propositional",
                    "is_valid": True,
                    "variables": {"rain": "it rains", "wet": "ground is wet"},
                    "confidence": 0.8,
                },
                {
                    "original_text": "All humans are mortal",
                    "formula": "forall X: (Human(X) => Mortal(X))",
                    "logic_type": "fol",
                    "is_valid": True,
                    "variables": {},
                    "confidence": 0.9,
                },
            ],
            "total": 2,
            "valid_count": 2,
        }
        _write_nl_to_logic_to_state(output, state, {})
        assert len(state.nl_to_logic_translations) == 2

    @pytest.mark.asyncio
    async def test_invoke_nl_to_logic_heuristic(self):
        """_invoke_nl_to_logic produces structured output."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_nl_to_logic,
        )

        context = {
            "phase_extract_output": {
                "arguments": [
                    {"text": "Rain causes wet ground and dangerous conditions."},
                    {
                        "text": "Climate change accelerates extreme weather events globally."
                    },
                ],
            },
        }
        # ATT-1 #1336: collection-order pollution — patching os.environ is not
        # enough in the full suite (see test_translate_no_api_key_uses_heuristic).
        # Patch the AsyncOpenAI constructor (option B, coord R558) so the LLM
        # path fails hermetically → translate() catches → heuristic.
        with patch("openai.AsyncOpenAI", side_effect=RuntimeError("no key")):
            result = await _invoke_nl_to_logic("test input text", context)

        assert "translations" in result
        assert "valid_count" in result
        assert "total" in result
        assert result["total"] >= 1
        assert result["method"] == "heuristic"


# ── TranslationResult dataclass tests ────────────────────────────────


class TestTranslationDataclasses:
    """Tests for data structures."""

    def test_translation_result_defaults(self):
        from argumentation_analysis.services.nl_to_logic import TranslationResult

        result = TranslationResult(
            original_text="test",
            formula="p => q",
            logic_type="propositional",
            is_valid=True,
        )
        assert result.attempts == 1
        assert result.variables == {}
        assert result.confidence == 0.0

    def test_batch_result_defaults(self):
        from argumentation_analysis.services.nl_to_logic import TranslationBatchResult

        batch = TranslationBatchResult()
        assert batch.translations == []
        assert batch.overall_consistency is None
        assert batch.method == "llm"
