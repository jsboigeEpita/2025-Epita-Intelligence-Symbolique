"""Tests for KBToTweetyPlugin — KB to Tweety formula translation (#475).

Validates:
- Pydantic models for translation results
- PL/FOL/Modal formula building from KB text
- Dung and ASPIC translation
- Retry logic with validation
- Batch translation
- write_tweety_to_state
- Registry and factory integration
"""

import asyncio
import json
import pytest
from unittest.mock import MagicMock, patch

from argumentation_analysis.plugins.kb_to_tweety_plugin import (
    AspicTranslationResult,
    DungTranslationResult,
    KBToTweetyPlugin,
    TweetyTranslationResult,
    _build_modal_formula,
    _build_pl_formula,
    _translate_with_retry,
)


# ---------------------------------------------------------------------------
# Test: Pydantic models
# ---------------------------------------------------------------------------


class TestPydanticModels:
    def test_tweety_translation_result(self):
        r = TweetyTranslationResult(
            original_text="Il pleut",
            formula="rain",
            logic_type="pl",
            is_valid=True,
            attempts=1,
            validation_message="Valid",
        )
        assert r.formula == "rain"
        d = r.model_dump()
        assert d["is_valid"] is True

    def test_tweety_translation_result_with_signature(self):
        r = TweetyTranslationResult(
            original_text="Socrate est mortel",
            formula="mortal(X)",
            logic_type="fol",
            is_valid=True,
            signature={"predicates": ["mortal"], "constants": ["socrate"]},
        )
        assert len(r.signature["predicates"]) == 1

    def test_dung_translation_result(self):
        r = DungTranslationResult(
            arguments=["a", "b"],
            attacks=[["a", "b"]],
            is_valid=True,
        )
        assert len(r.attacks) == 1

    def test_aspic_translation_result(self):
        r = AspicTranslationResult(
            strict_rules=["p => q"],
            defeasible_rules=["r => s"],
            ordinary_premises=["p"],
            is_valid=True,
        )
        assert len(r.strict_rules) == 1
        assert len(r.defeasible_rules) == 1


# ---------------------------------------------------------------------------
# Test: Formula builders
# ---------------------------------------------------------------------------


class TestFormulaBuilders:
    def test_build_pl_formula(self):
        formula = _build_pl_formula("Il pleut beaucoup")
        assert formula  # non-empty
        assert len(formula) <= 10

    def test_build_pl_formula_empty(self):
        assert _build_pl_formula("") == ""

    def test_build_fol_formula_is_gone(self):
        """#3135: the first-token template is removed from the module — a
        formula named after a sentence's first word is not a translation of
        that sentence, whether or not it parses (76 of the 82 formal findings
        on the saved R1105b run were these stubs)."""
        import argumentation_analysis.plugins.kb_to_tweety_plugin as kbp

        assert not hasattr(
            kbp, "_build_fol_formula"
        ), "the first-token FOL template must not exist (#3135)"

    def test_fol_records_not_translated_tri_state(self):
        """#3135 / #1634: a belief with no translator is recorded not
        translated (is_valid=None — never evaluated), with no formula and no
        retry (the outcome cannot change between attempts). Main fabricated
        `<premier mot>(X)` and marked it valid whenever Tweety parsed it."""
        result = asyncio.get_event_loop().run_until_complete(
            _translate_with_retry("Socrate est mortel", "fol")
        )
        assert result.is_valid is None
        assert result.formula == ""
        assert "not translated" in (result.validation_message or "")

    def test_fol_never_builds_a_one_formula_kb(self):
        """#3135 run-log witness: on main every belief triggered up to three
        fol_handler one-formula KB builds inside _validate_fol (the 76 builds
        and 21 parse failures of the saved run); after the fix the validator
        is never called for fol beliefs."""
        from unittest.mock import patch

        import argumentation_analysis.plugins.kb_to_tweety_plugin as kbp

        calls = []

        def record(*args, **kwargs):
            calls.append(1)
            return False, "recorded"

        with patch.object(kbp, "_validate_fol", side_effect=record):
            result = asyncio.get_event_loop().run_until_complete(
                _translate_with_retry("Une croyance sans traducteur", "fol")
            )
        assert calls == []
        assert result.is_valid is None

    def test_build_modal_formula(self):
        formula = _build_modal_formula("Il est necessaire que P")
        assert "[]" in formula or formula  # has modal operator

    def test_build_modal_formula_empty(self):
        assert _build_modal_formula("") == ""


# ---------------------------------------------------------------------------
# Test: Plugin translate_to_tweety
# ---------------------------------------------------------------------------


class TestTranslateToTweety:
    def test_translate_pl(self):
        plugin = KBToTweetyPlugin()
        result_json = asyncio.get_event_loop().run_until_complete(
            plugin.translate_to_tweety(
                json.dumps({"text": "Il pleut", "logic_type": "pl"})
            )
        )
        result = json.loads(result_json)
        assert "formula" in result
        assert result["logic_type"] == "pl"

    def test_translate_fol(self):
        """#3135: through the SK surface too, a fol belief comes back not
        translated — tri-state None, empty formula, named reason."""
        plugin = KBToTweetyPlugin()
        result_json = asyncio.get_event_loop().run_until_complete(
            plugin.translate_to_tweety(
                json.dumps({"text": "Socrate est mortel", "logic_type": "fol"})
            )
        )
        result = json.loads(result_json)
        assert result["logic_type"] == "fol"
        assert result["is_valid"] is None
        assert result["formula"] == ""
        assert "not translated" in (result.get("validation_message") or "")

    def test_translate_modal(self):
        plugin = KBToTweetyPlugin()
        result_json = asyncio.get_event_loop().run_until_complete(
            plugin.translate_to_tweety(
                json.dumps({"text": "Il est possible que P", "logic_type": "modal"})
            )
        )
        result = json.loads(result_json)
        assert "formula" in result
        assert result["logic_type"] == "modal"

    def test_translate_empty_text(self):
        plugin = KBToTweetyPlugin()
        result_json = asyncio.get_event_loop().run_until_complete(
            plugin.translate_to_tweety(json.dumps({"text": "", "logic_type": "pl"}))
        )
        result = json.loads(result_json)
        assert "error" in result

    def test_translate_bad_json(self):
        plugin = KBToTweetyPlugin()
        result_json = asyncio.get_event_loop().run_until_complete(
            plugin.translate_to_tweety("not json")
        )
        result = json.loads(result_json)
        assert "error" in result


# ---------------------------------------------------------------------------
# Test: Batch translation
# ---------------------------------------------------------------------------


class TestBatchTranslation:
    def test_batch_translates_multiple(self):
        plugin = KBToTweetyPlugin()
        result_json = asyncio.get_event_loop().run_until_complete(
            plugin.translate_batch_to_tweety(
                json.dumps({
                    "beliefs": ["Il pleut", "Le sol est mouille", "Le soleil brille"],
                    "logic_type": "pl",
                })
            )
        )
        result = json.loads(result_json)
        assert result["total"] == 3
        assert result["valid"] >= 0
        assert "pass_rate" in result

    def test_batch_empty_beliefs(self):
        plugin = KBToTweetyPlugin()
        result_json = asyncio.get_event_loop().run_until_complete(
            plugin.translate_batch_to_tweety(
                json.dumps({"beliefs": [], "logic_type": "pl"})
            )
        )
        result = json.loads(result_json)
        assert "error" in result

    def test_batch_fol_reports_not_translated(self):
        """#3135: the batch summary counts what was not translated instead of
        counting fabricated stubs as ``valid`` — on main these two beliefs
        became `<premier mot>(X)` formulas (valid under the JVM, three failed
        attempts without it), never a not-translated line."""
        plugin = KBToTweetyPlugin()
        result_json = asyncio.get_event_loop().run_until_complete(
            plugin.translate_batch_to_tweety(
                json.dumps(
                    {
                        "beliefs": [
                            "Croyance synthetique un",
                            "Croyance synthetique deux",
                        ],
                        "logic_type": "fol",
                    }
                )
            )
        )
        result = json.loads(result_json)
        assert result["total"] == 2
        assert result["valid"] == 0
        assert result["not_translated"] == 2
        for t in result["translations"]:
            assert t["is_valid"] is None
            assert t["formula"] == ""


# ---------------------------------------------------------------------------
# Test: Dung translation
# ---------------------------------------------------------------------------


class TestDungTranslation:
    def test_translate_dung(self):
        plugin = KBToTweetyPlugin()
        result_json = asyncio.get_event_loop().run_until_complete(
            plugin.translate_dung(
                json.dumps({
                    "arguments": ["a", "b", "c"],
                    "attacks": [["a", "b"], ["b", "c"]],
                })
            )
        )
        result = json.loads(result_json)
        assert result["is_valid"] is True
        assert len(result["arguments"]) == 3
        assert len(result["attacks"]) == 2

    def test_translate_dung_invalid_attacks(self):
        plugin = KBToTweetyPlugin()
        result_json = asyncio.get_event_loop().run_until_complete(
            plugin.translate_dung(
                json.dumps({
                    "arguments": ["a", "b"],
                    "attacks": [["a", "x"], ["y", "b"]],  # x, y not in args
                })
            )
        )
        result = json.loads(result_json)
        assert len(result["attacks"]) == 0  # Invalid attacks filtered out

    def test_translate_dung_bad_json(self):
        plugin = KBToTweetyPlugin()
        result_json = asyncio.get_event_loop().run_until_complete(
            plugin.translate_dung("bad json")
        )
        result = json.loads(result_json)
        assert "error" in result


# ---------------------------------------------------------------------------
# Test: ASPIC translation
# ---------------------------------------------------------------------------


class TestAspicTranslation:
    def test_translate_aspic(self):
        plugin = KBToTweetyPlugin()
        result_json = asyncio.get_event_loop().run_until_complete(
            plugin.translate_aspic(
                json.dumps({
                    "strict_rules": ["p => q"],
                    "defeasible_rules": ["r => s"],
                    "ordinary_premises": ["p", "r"],
                })
            )
        )
        result = json.loads(result_json)
        assert result["is_valid"] is True
        assert len(result["strict_rules"]) == 1
        assert len(result["defeasible_rules"]) == 1

    def test_translate_aspic_empty(self):
        plugin = KBToTweetyPlugin()
        result_json = asyncio.get_event_loop().run_until_complete(
            plugin.translate_aspic(json.dumps({}))
        )
        result = json.loads(result_json)
        assert result["is_valid"] is False


# ---------------------------------------------------------------------------
# Test: write_tweety_to_state
# ---------------------------------------------------------------------------


class TestWriteTweetyToState:
    def test_writes_formulas(self):
        plugin = KBToTweetyPlugin()
        state = MagicMock()
        state.add_belief_set.return_value = "pl_bs_1"

        input_data = {
            "formulas": [
                {"formula": "a => b", "logic_type": "propositional"},
                {"formula": "p(X)", "logic_type": "fol"},
            ]
        }
        result_json = plugin.write_tweety_to_state(json.dumps(input_data), state=state)
        result = json.loads(result_json)

        assert result["formulas_written"] == 2
        assert state.add_belief_set.call_count == 2

    def test_no_state(self):
        plugin = KBToTweetyPlugin()
        result_json = plugin.write_tweety_to_state("{}", state=None)
        result = json.loads(result_json)
        assert "error" in result

    def test_bad_json(self):
        plugin = KBToTweetyPlugin()
        state = MagicMock()
        result_json = plugin.write_tweety_to_state("bad", state=state)
        result = json.loads(result_json)
        assert "error" in result


# ---------------------------------------------------------------------------
# Test: Registry and factory
# ---------------------------------------------------------------------------


class TestRegistryIntegration:
    def test_plugin_registered(self):
        from argumentation_analysis.orchestration.registry_setup import setup_registry

        registry = setup_registry(include_optional=False)
        reg = registry._registrations.get("kb_to_tweety_plugin")
        assert reg is not None
        assert "kb_to_tweety" in reg.capabilities


class TestFactoryIntegration:
    def test_formal_logic_has_kb_to_tweety(self):
        from argumentation_analysis.agents.factory import AGENT_SPECIALITY_MAP

        assert "kb_to_tweety" in AGENT_SPECIALITY_MAP["formal_logic"]

    def test_plugin_registry_entry(self):
        from argumentation_analysis.agents.factory import _PLUGIN_REGISTRY

        assert "kb_to_tweety" in _PLUGIN_REGISTRY
        module_path, class_name = _PLUGIN_REGISTRY["kb_to_tweety"]
        assert "kb_to_tweety_plugin" in module_path
        assert class_name == "KBToTweetyPlugin"
