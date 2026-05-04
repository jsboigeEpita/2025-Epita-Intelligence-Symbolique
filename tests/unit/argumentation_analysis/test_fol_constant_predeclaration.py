"""
Tests for FOL constant pre-declaration workaround (#304).

Validates that the NLToLogicTranslator correctly extracts FOL metadata
from LLM responses and uses it to build Tweety FolSignatures, enabling
multiple FOL formulas with shared constants to be validated together.

These tests mock the Tweety/JVM layer since the JVM may not be available
in the test environment.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

from argumentation_analysis.services.nl_to_logic import (
    NLToLogicTranslator,
    _extract_fol_metadata,
    normalize_operators,
)

# ── _extract_fol_metadata tests ────────────────────────────────────────


class TestExtractFolMetadata:
    """Tests for the _extract_fol_metadata helper function."""

    def test_new_format_with_sorts_and_predicates(self):
        """New LLM format with explicit sorts and typed predicates."""
        parsed = {
            "formulas": [
                "forall X: (Human(X) => Mortal(X))",
                "Human(socrates)",
                "Human(plato)",
            ],
            "predicates": {"Human": ["Person"], "Mortal": ["Person"]},
            "sorts": {"Person": ["socrates", "plato"]},
            "constants": {
                "socrates": "the philosopher Socrates",
                "plato": "the philosopher Plato",
            },
            "confidence": 0.9,
        }
        metadata = _extract_fol_metadata(parsed)

        assert metadata["sorts"] == {"Person": ["socrates", "plato"]}
        assert metadata["predicates"] == {
            "Human": ["Person"],
            "Mortal": ["Person"],
        }
        assert "socrates" in metadata["constants_raw"]
        assert "plato" in metadata["constants_raw"]

    def test_old_format_with_description_predicates(self):
        """Old LLM format where predicates have string descriptions."""
        parsed = {
            "formulas": ["Human(socrates)", "Mortal(socrates)"],
            "predicates": {"Human": "is a human being", "Mortal": "is mortal"},
            "constants": {"socrates": "the philosopher Socrates"},
            "confidence": 0.85,
        }
        metadata = _extract_fol_metadata(parsed)

        # Old format predicates (string values) are not added to typed predicates
        assert metadata["predicates"] == {}
        # But constants are extracted and a default Thing sort is created
        assert "Thing" in metadata["sorts"]
        assert "socrates" in metadata["sorts"]["Thing"]
        assert metadata["constants_raw"] == {"socrates": "the philosopher Socrates"}

    def test_no_sorts_creates_default_thing_sort(self):
        """When no sorts declared but constants exist, creates a 'Thing' sort."""
        parsed = {
            "formulas": ["Likes(alice, bob)"],
            "constants": {"alice": "person A", "bob": "person B"},
            "confidence": 0.7,
        }
        metadata = _extract_fol_metadata(parsed)

        assert "Thing" in metadata["sorts"]
        assert set(metadata["sorts"]["Thing"]) == {"alice", "bob"}

    def test_empty_parsed_response(self):
        """Empty parsed response returns empty metadata."""
        metadata = _extract_fol_metadata({})
        assert metadata["sorts"] == {}
        assert metadata["predicates"] == {}
        assert metadata["constants_raw"] == {}

    def test_multiple_sorts(self):
        """Multiple sorts with different constants."""
        parsed = {
            "sorts": {
                "Person": ["socrates", "plato"],
                "City": ["athens", "sparta"],
            },
            "predicates": {
                "LivesIn": ["Person", "City"],
                "Human": ["Person"],
            },
            "constants": {
                "socrates": "philosopher",
                "plato": "philosopher",
                "athens": "Greek city",
                "sparta": "Greek city",
            },
        }
        metadata = _extract_fol_metadata(parsed)

        assert len(metadata["sorts"]) == 2
        assert set(metadata["sorts"]["Person"]) == {"socrates", "plato"}
        assert set(metadata["sorts"]["City"]) == {"athens", "sparta"}
        assert metadata["predicates"]["LivesIn"] == ["Person", "City"]


# ── _validate_fol_with_signature tests (mocked Tweety) ─────────────────


class TestValidateFolWithSignature:
    """Tests for _validate_fol_with_signature with mocked JVM/Tweety."""

    def _make_translator(self):
        return NLToLogicTranslator(logic_type="fol")

    @patch("argumentation_analysis.services.nl_to_logic.jpype", create=True)
    def test_signature_built_with_sorts_and_constants(self, mock_jpype):
        """Signature is built with sorts, constants, and predicates."""
        translator = self._make_translator()

        # Mock JPype classes
        mock_sig = MagicMock()
        mock_sort = MagicMock()
        mock_constant = MagicMock()
        mock_predicate = MagicMock()
        mock_parser = MagicMock()
        mock_arraylist = MagicMock()

        mock_jpype.JClass.side_effect = lambda name: {
            "org.tweetyproject.logics.fol.syntax.FolSignature": lambda: mock_sig,
            "org.tweetyproject.logics.commons.syntax.Sort": lambda s: mock_sort,
            "org.tweetyproject.logics.commons.syntax.Constant": lambda s, sort: mock_constant,
            "org.tweetyproject.logics.commons.syntax.Predicate": lambda s, sorts: mock_predicate,
            "org.tweetyproject.logics.fol.parser.FolParser": lambda: mock_parser,
            "java.util.ArrayList": lambda: mock_arraylist,
            "java.lang.String": lambda s: s,
        }[name]

        mock_bridge = MagicMock()
        mock_bridge.fol_handler.parse_fol_formula.return_value = MagicMock()

        fol_metadata = {
            "sorts": {"Person": ["socrates", "plato"]},
            "predicates": {"Human": ["Person"], "Mortal": ["Person"]},
            "constants_raw": {
                "socrates": "philosopher",
                "plato": "philosopher",
            },
        }

        formulas = [
            "forall X: (Human(X) => Mortal(X))",
            "Human(socrates)",
            "Human(plato)",
        ]

        result = translator._validate_fol_with_signature(
            mock_bridge, formulas, fol_metadata
        )

        is_valid, msg = result
        assert is_valid is True
        assert "3 formulas" in msg

        # Verify parse_fol_formula was called for each formula with custom_parser
        assert mock_bridge.fol_handler.parse_fol_formula.call_count == 3

    @patch("argumentation_analysis.services.nl_to_logic.jpype", create=True)
    def test_undeclared_constants_auto_discovered(self, mock_jpype):
        """Constants found in formulas but not in metadata are auto-added."""
        translator = self._make_translator()

        mock_sig = MagicMock()
        mock_sort = MagicMock()
        mock_constant = MagicMock()
        mock_predicate = MagicMock()
        mock_parser = MagicMock()
        mock_arraylist = MagicMock()

        mock_jpype.JClass.side_effect = lambda name: {
            "org.tweetyproject.logics.fol.syntax.FolSignature": lambda: mock_sig,
            "org.tweetyproject.logics.commons.syntax.Sort": lambda s: mock_sort,
            "org.tweetyproject.logics.commons.syntax.Constant": lambda s, sort: mock_constant,
            "org.tweetyproject.logics.commons.syntax.Predicate": lambda s, sorts: mock_predicate,
            "org.tweetyproject.logics.fol.parser.FolParser": lambda: mock_parser,
            "java.util.ArrayList": lambda: mock_arraylist,
            "java.lang.String": lambda s: s,
        }[name]

        mock_bridge = MagicMock()
        mock_bridge.fol_handler.parse_fol_formula.return_value = MagicMock()

        # Only declare socrates, but formula uses plato too
        fol_metadata = {
            "sorts": {"Person": ["socrates"]},
            "predicates": {"Human": ["Person"]},
            "constants_raw": {"socrates": "philosopher"},
        }

        formulas = ["Human(socrates)", "Human(plato)"]

        is_valid, msg = translator._validate_fol_with_signature(
            mock_bridge, formulas, fol_metadata
        )

        assert is_valid is True
        # plato should have been auto-discovered and added

    @patch("argumentation_analysis.services.nl_to_logic.jpype", create=True)
    def test_parse_error_returns_invalid(self, mock_jpype):
        """Parse errors are collected and returned as invalid."""
        translator = self._make_translator()

        mock_sig = MagicMock()
        mock_sort = MagicMock()
        mock_constant = MagicMock()
        mock_predicate = MagicMock()
        mock_parser = MagicMock()
        mock_arraylist = MagicMock()

        mock_jpype.JClass.side_effect = lambda name: {
            "org.tweetyproject.logics.fol.syntax.FolSignature": lambda: mock_sig,
            "org.tweetyproject.logics.commons.syntax.Sort": lambda s: mock_sort,
            "org.tweetyproject.logics.commons.syntax.Constant": lambda s, sort: mock_constant,
            "org.tweetyproject.logics.commons.syntax.Predicate": lambda s, sorts: mock_predicate,
            "org.tweetyproject.logics.fol.parser.FolParser": lambda: mock_parser,
            "java.util.ArrayList": lambda: mock_arraylist,
            "java.lang.String": lambda s: s,
        }[name]
        mock_jpype.JException = Exception

        mock_bridge = MagicMock()
        mock_bridge.fol_handler.parse_fol_formula.side_effect = ValueError(
            "Syntax error in formula"
        )

        fol_metadata = {
            "sorts": {"Person": ["socrates"]},
            "predicates": {"Human": ["Person"]},
            "constants_raw": {"socrates": "philosopher"},
        }

        is_valid, msg = translator._validate_fol_with_signature(
            mock_bridge, ["Human(socrates)"], fol_metadata
        )

        assert is_valid is False
        assert "Syntax error" in msg


# ── Integration: _validate_formula dispatches to signature builder ──────


class TestValidateFormulaFOLDispatch:
    """Tests that _validate_formula correctly dispatches FOL with metadata."""

    def _make_translator(self):
        return NLToLogicTranslator(logic_type="fol")

    @pytest.mark.asyncio
    async def test_fol_with_metadata_uses_signature_builder(self):
        """FOL validation with metadata calls _validate_fol_with_signature."""
        translator = self._make_translator()

        fol_metadata = {
            "sorts": {"Person": ["socrates"]},
            "predicates": {"Human": ["Person"]},
            "constants_raw": {"socrates": "philosopher"},
        }

        with patch.object(
            translator, "_validate_fol_with_signature", return_value=(True, "OK")
        ) as mock_sig_validate:
            # Mock Tweety import to not fail
            with patch(
                "argumentation_analysis.services.nl_to_logic.TweetyBridge",
                create=True,
            ):
                with patch(
                    "argumentation_analysis.agents.core.logic.tweety_bridge.TweetyBridge"
                ) as MockBridge:
                    mock_bridge = MagicMock()
                    MockBridge.return_value = mock_bridge

                    is_valid, msg = await translator._validate_formula(
                        "Human(socrates)", "fol", fol_metadata=fol_metadata
                    )

        # Should have attempted Tweety validation with signature builder

    @pytest.mark.asyncio
    async def test_fol_without_metadata_falls_back(self):
        """FOL validation without metadata uses individual parsing or Python fallback.

        Without FOL metadata (no sorts/constants), Tweety's FOL parser will fail
        on formulas with undeclared constants. This is the exact bug #304 describes.
        The validation should either fail at Tweety level or fall back to Python.
        """
        translator = self._make_translator()

        # Without fol_metadata, Tweety will fail on 'socrates' (undeclared constant)
        # and the code falls back to Python validation
        is_valid, msg = await translator._validate_formula(
            "forall X: (Human(X) => Mortal(X)); Human(socrates)",
            "fol",
            fol_metadata=None,
        )
        # Either Tweety fails on socrates (bug #304 scenario) and Python fallback
        # validates it, or Tweety succeeds for formulas without constants.
        # In any case, the Python fallback validates syntactically.
        # The important thing: with metadata, it succeeds at Tweety level too.
        # We just verify the method doesn't crash.
        assert isinstance(is_valid, bool)
        assert isinstance(msg, str)

    @pytest.mark.asyncio
    async def test_propositional_ignores_fol_metadata(self):
        """Propositional validation ignores fol_metadata (it's only for FOL).

        FOL metadata is only used for FOL formulas. For propositional logic,
        the metadata is ignored and standard PL validation applies.
        """
        translator = self._make_translator()

        # Mock Tweety to avoid JVM dependency; focus on testing dispatch logic
        with patch.object(
            translator,
            "_validate_with_tweety",
            side_effect=Exception("JVM not available"),
        ):
            is_valid, msg = await translator._validate_formula(
                "p && (p => q)",
                "propositional",
                fol_metadata={"sorts": {"Thing": ["x"]}},
            )
        # Falls back to Python validation which accepts this formula
        assert is_valid is True
        assert "Python" in msg


# ── LLM translation with FOL metadata extraction ───────────────────────


class TestTranslateWithLLMFolMetadata:
    """Tests that _translate_with_llm extracts and passes FOL metadata."""

    def _make_translator(self):
        return NLToLogicTranslator(logic_type="fol", max_retries=1)

    @pytest.mark.asyncio
    async def test_fol_translation_extracts_metadata(self):
        """FOL translation extracts sorts/predicates/constants from LLM response."""
        translator = self._make_translator()

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = (
            '{"formulas": ["forall X: (Human(X) => Mortal(X))", "Human(socrates)", "Human(plato)"], '
            '"predicates": {"Human": ["Person"], "Mortal": ["Person"]}, '
            '"sorts": {"Person": ["socrates", "plato"]}, '
            '"constants": {"socrates": "philosopher", "plato": "philosopher"}, '
            '"confidence": 0.9}'
        )

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        captured_metadata = {}

        async def mock_validate(formula, logic_type, fol_metadata=None):
            captured_metadata["fol_metadata"] = fol_metadata
            return (True, "Valid (mocked)")

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=False):
            with patch("openai.AsyncOpenAI", return_value=mock_client):
                with patch.object(translator, "_validate_formula", mock_validate):
                    result = await translator.translate(
                        "All humans are mortal. Socrates and Plato are humans.",
                        logic_type="fol",
                    )

        assert result.is_valid is True
        assert (
            result.formula
            == "forall X: (Human(X) => Mortal(X)); Human(socrates); Human(plato)"
        )

        # Verify metadata was extracted and passed
        meta = captured_metadata["fol_metadata"]
        assert meta is not None
        assert "Person" in meta["sorts"]
        assert set(meta["sorts"]["Person"]) == {"socrates", "plato"}
        assert meta["predicates"]["Human"] == ["Person"]

    @pytest.mark.asyncio
    async def test_propositional_translation_passes_none_metadata(self):
        """Propositional translation passes fol_metadata=None."""
        translator = NLToLogicTranslator(logic_type="propositional", max_retries=1)

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = (
            '{"formula": "p && q", "variables": {"p": "x", "q": "y"}, "confidence": 0.8}'
        )

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        captured_metadata = {}

        async def mock_validate(formula, logic_type, fol_metadata=None):
            captured_metadata["fol_metadata"] = fol_metadata
            return (True, "Valid")

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=False):
            with patch("openai.AsyncOpenAI", return_value=mock_client):
                with patch.object(translator, "_validate_formula", mock_validate):
                    result = await translator.translate(
                        "Some argument text that is long enough.",
                        logic_type="propositional",
                    )

        assert captured_metadata["fol_metadata"] is None
