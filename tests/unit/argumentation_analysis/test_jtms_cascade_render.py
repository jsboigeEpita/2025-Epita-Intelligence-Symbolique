"""Tests for JTMS retraction cascade rendering (#350).

Validates that JTMS tracks cascading retractions when fallacies undermine
beliefs, and that the cascade chain is properly stored in state.
"""

import asyncio
import pytest

from argumentation_analysis.services.jtms.jtms_core import JTMS, Belief
from argumentation_analysis.orchestration.invoke_callables import _invoke_jtms
from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.state_writers import _write_jtms_to_state


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class TestJTMSCoreRetractionTrace:
    """Tests for JTMS core retraction trace."""

    def test_enable_tracing(self):
        jtms = JTMS()
        jtms.enable_tracing()
        assert jtms._tracing_enabled is True
        assert jtms._retraction_trace == []

    def test_retraction_recorded_when_belief_set_false(self):
        jtms = JTMS()
        jtms.add_belief("A")
        jtms.set_belief_validity("A", True)
        jtms.enable_tracing()
        jtms.set_belief_validity("A", False)
        chain = jtms.get_retraction_chain()
        assert len(chain) == 1
        assert chain[0]["trigger"] == "A"
        assert "A" in chain[0]["retracted"]

    def test_cascade_retraction_tracked(self):
        """A → B; retract A → cascade retracts B."""
        jtms = JTMS()
        jtms.add_belief("A")
        jtms.add_belief("B")
        jtms.add_justification(["A"], [], "B")
        jtms.set_belief_validity("A", True)
        # B should be valid via A
        assert jtms.beliefs["B"].valid is True

        jtms.enable_tracing()
        jtms.set_belief_validity("A", False)

        chain = jtms.get_retraction_chain()
        assert len(chain) == 1
        assert chain[0]["trigger"] == "A"
        assert "A" in chain[0]["retracted"]
        assert "B" in chain[0]["cascaded"]

    def test_no_trace_when_not_tracing(self):
        jtms = JTMS()
        jtms.add_belief("A")
        jtms.set_belief_validity("A", True)
        # Not enabling tracing
        jtms.set_belief_validity("A", False)
        chain = jtms.get_retraction_chain()
        assert len(chain) == 0

    def test_deep_cascade_three_levels(self):
        """A → B → C; retract A → cascades to B and C."""
        jtms = JTMS()
        jtms.add_belief("A")
        jtms.add_belief("B")
        jtms.add_belief("C")
        jtms.add_justification(["A"], [], "B")
        jtms.add_justification(["B"], [], "C")
        jtms.set_belief_validity("A", True)

        assert jtms.beliefs["B"].valid is True
        assert jtms.beliefs["C"].valid is True

        jtms.enable_tracing()
        jtms.set_belief_validity("A", False)

        chain = jtms.get_retraction_chain()
        assert len(chain) == 1
        assert "B" in chain[0]["cascaded"]

    def test_chain_entry_format(self):
        """Each chain entry has the required format fields."""
        jtms = JTMS()
        jtms.add_belief("X")
        jtms.set_belief_validity("X", True)
        jtms.enable_tracing()
        jtms.set_belief_validity("X", False)

        chain = jtms.get_retraction_chain()
        assert len(chain) == 1
        entry = chain[0]
        assert "trigger" in entry
        assert "retracted" in entry
        assert "cascaded" in entry
        assert "reason" in entry
        assert isinstance(entry["retracted"], list)
        assert isinstance(entry["cascaded"], list)

    def test_get_retraction_chain_returns_copy(self):
        """get_retraction_chain returns a copy, not the internal list."""
        jtms = JTMS()
        jtms.add_belief("A")
        jtms.set_belief_validity("A", True)
        jtms.enable_tracing()
        jtms.set_belief_validity("A", False)

        chain1 = jtms.get_retraction_chain()
        chain2 = jtms.get_retraction_chain()
        assert chain1 == chain2
        assert chain1 is not chain2


class TestInvokeJtmsRetractionChain:
    """Tests for _invoke_jtms retraction chain output."""

    def test_retraction_chain_in_output(self):
        context = {
            "phase_extract_output": {
                "arguments": [
                    {"text": "First argument about X"},
                    {"text": "Second argument about Y"},
                    {"text": "Third argument about Z"},
                ],
                "claims": [{"text": "Main claim"}],
            },
            "phase_hierarchical_fallacy_output": {
                "fallacies": [
                    {"type": "ad_hominem", "target_argument": "First argument about X"},
                ],
            },
        }
        result = _run(_invoke_jtms("Some text.", context))
        assert "retraction_chain" in result
        assert isinstance(result["retraction_chain"], list)

    def test_cascade_chain_with_fallacy(self):
        """When a fallacy undermines an argument, it creates a retraction entry."""
        context = {
            "phase_extract_output": {
                "arguments": [
                    {"text": "Premise supporting conclusion A"},
                    {"text": "Another premise"},
                ],
                "claims": [{"text": "Conclusion A follows from premises"}],
            },
            "phase_hierarchical_fallacy_output": {
                "fallacies": [
                    {
                        "type": "straw_man",
                        "target_argument": "Premise supporting conclusion A",
                    },
                ],
            },
        }
        result = _run(_invoke_jtms("Text.", context))
        chain = result["retraction_chain"]
        # At least one retraction should have happened
        assert len(chain) >= 1
        # The chain entry should have proper format
        entry = chain[0]
        assert entry["trigger"]  # non-empty trigger
        assert isinstance(entry["retracted"], list)
        assert isinstance(entry["cascaded"], list)

    def test_no_fallacies_empty_chain(self):
        """Without fallacies, retraction chain is empty."""
        context = {
            "phase_extract_output": {
                "arguments": [{"text": "Clean argument"}],
                "claims": [{"text": "Clean claim"}],
            },
        }
        result = _run(_invoke_jtms("Text.", context))
        chain = result.get("retraction_chain", [])
        assert len(chain) == 0


class TestStateWriterRetractionChain:
    """Tests for state_writer integration with retraction chain."""

    def test_retraction_chain_stored_in_state(self):
        state = UnifiedAnalysisState("test text")
        output = {
            "beliefs": {"A": {"valid": False, "justifications": []}},
            "retraction_chain": [
                {
                    "trigger": "A",
                    "retracted": ["A"],
                    "cascaded": ["B"],
                    "reason": "directly set to False",
                }
            ],
        }
        _write_jtms_to_state(output, state, {})
        assert len(state.jtms_retraction_chain) == 1
        assert state.jtms_retraction_chain[0]["trigger"] == "A"
        assert "B" in state.jtms_retraction_chain[0]["cascaded"]

    def test_empty_chain_when_no_output(self):
        state = UnifiedAnalysisState("test text")
        _write_jtms_to_state(None, state, {})
        assert state.jtms_retraction_chain == []

    def test_state_has_retraction_chain_field(self):
        state = UnifiedAnalysisState("test")
        assert hasattr(state, "jtms_retraction_chain")
        assert isinstance(state.jtms_retraction_chain, list)
