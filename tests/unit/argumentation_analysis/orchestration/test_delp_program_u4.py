"""#3546 — U4 of #1644: a DeLP phase that returns ``unavailable`` is filed
DEGRADED with its reason, so the absence ledger names it.

Measured on the recorded cycle-6 panel states (coordinator seat): phase
``delp_reasoning`` status ``completed`` on 9 of 10 documents, 0 of 10 in
``degraded_phases``. Yet ``_invoke_delp`` returned ``status: "unavailable"``
(no ``program`` in context — see #1215: prose is never parsed as DeLP).

Root cause: the unavailable payload carried ``status: "unavailable"`` but
NO ``degraded: True`` flag, so the rollup at
``workflow_dsl.py:_compute_workflow_degraded`` (which reads
``r.output.get("degraded") is True`` on COMPLETED phases) did not see it.
The phase read as healthy.

Two asks, tested here:
1. Filing: an ``unavailable`` DeLP result carries ``degraded=True`` and a
   ``degradation_reason``, matching the established pattern (self-hosted
   LLM invoke_callables:4810, :4970, bipolar honest-absent #1645).
2. Verdict (separate test, fake handler, no JVM): with a fake translator
   producing a DeLP program for the planted permit text, the handler
   returns one decided query and the program sidecar is populated.

Witness is red on ``main`` (no degraded flag, no program).
Mutation: removing the degraded flag (or the more specific rule from the
program) reddens the witness again.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Ask 1 — Filing: a DeLP phase returning ``unavailable`` carries degraded=True
# ---------------------------------------------------------------------------


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


class TestDelpUnavailableIsDegraded:
    """The unavailable payload (no program in context) must carry the
    degraded signal — otherwise the workflow rollup files the phase as
    completed and the absence ledger never names it (#3546)."""

    def test_unavailable_payload_is_flagged_degraded(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_delp,
        )

        result = _run(_invoke_delp("ignored text", {}))

        assert result.get("status") == "unavailable"
        assert (
            result.get("degraded") is True
        ), "unavailable DeLP payload must carry degraded=True so the rollup files it"
        assert result.get("degradation_reason"), (
            "unavailable DeLP payload must carry a degradation_reason "
            "(the absence ledger names the phase by it)"
        )

    def test_unavailable_payload_reason_names_the_missing_program(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_delp,
        )

        result = _run(_invoke_delp("ignored text", {}))
        reason = str(result.get("degradation_reason", "")).lower()
        assert (
            "program" in reason
        ), "the degradation_reason must name the missing 'program' so the ledger says why"
