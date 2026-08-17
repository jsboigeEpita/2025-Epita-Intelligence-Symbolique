"""stakes_extraction joins CAPABILITY_STATE_WRITERS — duality invariant repair.

``_invoke_stakes_extractor`` (Track TT #723) landed with its state write
inline, so ``stakes_extraction`` was the only primary pipeline capability
absent from ``CAPABILITY_STATE_WRITERS`` and the workflow executor did not
recognise it as primary — ``test_capability_duality_invariant`` has been red
on main since #723 (the integration suite is not in CI, so nothing flagged
it). These tests pin the extracted-writer contract:

- the writer is registered under ``stakes_extraction``;
- it populates ``state.stakes_and_stakeholders`` from the invoke output;
- an error output leaves the honest empty default (never fabricate, #1019);
- a direct (non-executor) invoke call still persists — the conversational
  orchestrator's post-processing path relies on it.
"""

import asyncio
from unittest.mock import patch

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.state_writers import (
    CAPABILITY_STATE_WRITERS,
    _write_stakes_to_state,
)

_EMPTY_DEFAULT = {
    "stakes": [],
    "stakeholders": [],
    "rhetorical_register": "",
    "discursive_arena": "",
}


class TestWriteStakesToState:
    def test_registered_under_stakes_extraction(self):
        assert (
            CAPABILITY_STATE_WRITERS.get("stakes_extraction") is _write_stakes_to_state
        )

    def test_populates_state_from_output(self):
        state = UnifiedAnalysisState("speech")
        output = {
            "stakes": [{"stake_type": "economic", "description": "tax base"}],
            "stakeholders": [{"name": "government", "stance": "for"}],
            "rhetorical_register": "mobilization",
            "discursive_arena": "parliament",
            "summary": "extracted",
        }
        _write_stakes_to_state(output, state, {})
        assert state.stakes_and_stakeholders["stakes"] == output["stakes"]
        assert state.stakes_and_stakeholders["stakeholders"] == output["stakeholders"]
        assert state.stakes_and_stakeholders["rhetorical_register"] == "mobilization"
        assert state.stakes_and_stakeholders["discursive_arena"] == "parliament"

    def test_error_output_leaves_honest_default(self):
        state = UnifiedAnalysisState("speech")
        _write_stakes_to_state({"error": "No shared state"}, state, {})
        assert state.stakes_and_stakeholders == _EMPTY_DEFAULT

    def test_empty_output_leaves_honest_default(self):
        state = UnifiedAnalysisState("speech")
        _write_stakes_to_state(None, state, {})
        _write_stakes_to_state({}, state, {})
        assert state.stakes_and_stakeholders == _EMPTY_DEFAULT


class TestDirectInvokeStillPersists:
    """The conversational orchestrator calls the invoke directly (no
    executor), so the invoke's inline writer call must persist — strengthened
    from B02's ``hasattr`` (which passed even with no write at all, the attr
    is initialised in ``UnifiedAnalysisState.__init__``)."""

    def test_direct_call_populates_state(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_stakes_extractor,
        )

        state = UnifiedAnalysisState("speech")
        state.identified_arguments = {"a1": "We must reform the tax system."}

        class _StubExtractor:
            async def extract(self, **kwargs):
                return {
                    "stakes": [{"stake_type": "economic", "description": "d"}],
                    "stakeholders": [{"name": "gov", "stance": "for"}],
                    "rhetorical_register": "legitimation",
                    "discursive_arena": "assembly",
                }

        with (
            patch(
                "argumentation_analysis.orchestration.invoke_callables"
                "._get_openai_client",
                return_value=(None, ""),
            ),
            patch(
                "argumentation_analysis.agents.core.political.stakes_extractor"
                ".StakesExtractor",
                return_value=_StubExtractor(),
            ),
        ):
            result = asyncio.get_event_loop().run_until_complete(
                _invoke_stakes_extractor(
                    "", {"_state_object": state, "source_metadata": {}}
                )
            )

        assert "error" not in result
        assert state.stakes_and_stakeholders["stakes"] == [
            {"stake_type": "economic", "description": "d"}
        ]
        assert state.stakes_and_stakeholders["rhetorical_register"] == "legitimation"
