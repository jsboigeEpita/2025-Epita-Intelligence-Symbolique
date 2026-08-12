"""Tests for ``scripts/measure_1668_convo_gate.py`` (#1668 item 5-bis).

The measure is read-only over a state JSON — no API run, no dataset decrypt.
The unit under test is the vocabulary classifier + the gate matcher.
Privacy: tests use opaque fake strategy values (``strat_*``), never corpus
text. Substitution controls (leçon R794) verify the test is armed by the fix.
"""

from __future__ import annotations

from scripts.measure_1668_convo_gate import (
    COUNTER_STRATEGIES,
    DEBATE_STRATEGIES,
    GATE_STRATEGIES,
    _vocab_class,
    measure_state,
)


class TestVocabClassifier:
    """Disjoint-vocabulary classification: gate / counter / debate / other."""

    def test_gate_strategies_classify_as_gate(self) -> None:
        # The exact strings the gate reads (`ca.get("strategy", "").upper()`).
        for s in GATE_STRATEGIES:
            assert _vocab_class(s) == "gate"
        # Case-insensitive on the input — `upper()` is applied in the gate
        # predicate, so the classifier's caller must do the same.
        assert _vocab_class("undercut") == "gate"
        assert _vocab_class("rebuttal") == "gate"

    def test_counter_enum_classify_as_counter(self) -> None:
        # The 5 RhetoricalStrategy enum values from counter_argument/strategies.py
        for s in COUNTER_STRATEGIES:
            assert _vocab_class(s) == "counter"

    def test_debate_prompt_classify_as_debate(self) -> None:
        # The 5 strategy names from collaborative_debate.py:72 prompt.
        for s in DEBATE_STRATEGIES:
            assert _vocab_class(s) == "debate"

    def test_unknown_vocabulary_falls_into_other(self) -> None:
        # LLM-improvised values (evidential_refutation, process_tracing, …) —
        # the producer is free-text, so anything not in the 3 closed vocabs
        # is "other". This is the gate-inert bucket on corpus_A real run.
        assert _vocab_class("evidential_refutation") == "other"
        assert _vocab_class("process_tracing") == "other"
        assert _vocab_class("totally invented name") == "other"

    def test_classes_are_disjoint(self) -> None:
        # No strategy name should classify as more than one vocab (else the
        # bucket count is non-additive and the measure becomes self-contradictory).
        seen = set()
        for s in (
            "UNDERCUT",
            "reductio_ad_absurdum",
            "counter-example",
            "evidential_refutation",
        ):
            cls = _vocab_class(s)
            assert cls not in seen, f"{s!r} classified into already-used {cls}"
            seen.add(cls)


class TestMeasureState:
    """Measure the gate reach + the Dung framework population."""

    def _state(self, strategies: list[str], dung_attacks: int = 0) -> dict:
        return {
            "counter_arguments": [
                {"id": f"ca_{i}", "strategy": s} for i, s in enumerate(strategies)
            ],
            "dung_frameworks": {
                "dung_1": {
                    "arguments": ["arg_1", "arg_2"],
                    "attacks": [["x", "y"]] * dung_attacks,
                    "extensions": {"grounded": ["arg_1"]},
                }
            },
        }

    def test_gate_match_is_case_insensitive(self) -> None:
        m = measure_state(self._state(["UNDERcut", "rebut", "REBUTTAL"]))
        assert m["gate_matched"] == 3
        assert m["gate_not_matched"] == 0
        assert m["by_vocab"]["gate"] == 3

    def test_zero_match_when_no_strategy_in_gate_vocab(self) -> None:
        # R796 finding — corpus_A real run: 16 CAs, 0 in gate vocab.
        m = measure_state(self._state(["evidential_refutation", "process_tracing"]))
        assert m["gate_matched"] == 0
        assert m["gate_not_matched"] == 2
        assert m["by_vocab"]["other"] == 2

    def test_dung_attacks_counted_when_gate_inert(self) -> None:
        # R784/R796 — the gate being 0 does NOT mean the framework is empty;
        # fallacies build the framework via a separate branch.
        m = measure_state(self._state([], dung_attacks=11))
        assert m["dung_frameworks"]["dung_1"]["attacks"] == 11

    def test_empty_state_yields_zero_measurements(self) -> None:
        m = measure_state({})
        assert m["cas_present"] == 0
        assert m["gate_matched"] == 0
        assert m["dung_frameworks"] == {}

    def test_malformed_counter_arguments_dont_crash(self) -> None:
        # Defensive: a non-list ``counter_arguments`` should not raise (the
        # conversational orchestrator hands a list, but the state may carry
        # other shapes if a phase failed mid-run).
        m = measure_state({"counter_arguments": None})
        assert m["cas_present"] == 0
        assert m["gate_matched"] == 0


class TestSubstitutionControls:
    """Substitution controls EXECUTED (leçon R794): a correct reasoning is
    not an execution. The measure function is exercised by patching constants
    to verify the classification path is armed — not by trusting the doc."""

    def test_classifier_changes_when_gate_set_changes(self) -> None:
        # If GATE_STRATEGIES were missing ``UNDERCUT``, the classifier would
        # drop ``undercut`` to ``other``. Patch to prove the constant flows
        # through.
        import scripts.measure_1668_convo_gate as mod

        original = mod.GATE_STRATEGIES
        mod.GATE_STRATEGIES = frozenset({"REBUT", "REBUTTAL"})
        try:
            # Without UNDERCUT, the previously-gate value drops to other.
            assert _vocab_class("UNDERCUT") == "other"
            assert _vocab_class("REBUT") == "gate"
        finally:
            mod.GATE_STRATEGIES = original

    def test_substitution_disarms_gate_match(self) -> None:
        """Substitution control: add the gate vocabulary to the input string
        ⇒ measure_state reports the CA as matched. Proves the test is armed by
        the matcher logic, not by fixture values."""
        import scripts.measure_1668_convo_gate as mod

        # Strategy NOT in gate vocab → 0 match.
        m = measure_state(self._state(["evidential_refutation"]))
        assert m["gate_matched"] == 0

        # Same fixture, but the strategy IS one of the gate strings — proves
        # the matcher actually reads each strategy against GATE_STRATEGIES.
        m = measure_state(self._state(["UNDERCUT"]))
        assert m["gate_matched"] == 1
        # And the vocab class also flipped to gate:
        assert m["by_vocab"]["gate"] == 1

    @staticmethod
    def _state(strategies: list[str], dung_attacks: int = 0) -> dict:
        return {
            "counter_arguments": [
                {"id": f"ca_{i}", "strategy": s} for i, s in enumerate(strategies)
            ],
            "dung_frameworks": {
                "dung_1": {
                    "arguments": ["arg_1", "arg_2"],
                    "attacks": [["x", "y"]] * dung_attacks,
                    "extensions": {"grounded": ["arg_1"]},
                }
            },
        }
