"""#1745 — the extraction inventory must carry BOTH poles of an opposition.

Measured against hand-annotated real-prose ground truth (issue #1745): the
baseline extraction prompt folds the cited/adversary position inside the
speaker's evaluative items, leaving every downstream attack axis a ONE-pole
inventory — the famine_proposal state of #1710. The production prompt now
appends ``_OPPOSING_POSITIONS_INSTRUCTION``.

Two contracts, explicitly separated:

1. ``test_instruction_reaches_the_wire`` (hermetic, no API key) — the
   instruction deployed in production is EXACTLY the variable measured in
   the #1745 two-arm runs (verbatim fidelity pin). A silent rewording or
   removal of the instruction would keep the behaviour test green on easy
   draws while voiding the 2-passage two-arm measurement evidence.
   Substitution control EXECUTED: emptying
   ``_OPPOSING_POSITIONS_INSTRUCTION`` turns this test red
   deterministically (3/3 draws).

2. ``test_inventory_carries_both_poles_of_explicit_opposition``
   (``requires_api``, real LLM) — BEHAVIOUR: on a dense synthetic text
   whose target position appears only as the object of disqualifying
   predicates, the inventory must carry the position as its own
   non-disqualified item, so downstream attack axes have a node to attack.
   Substitution matrix EXECUTED (2026-08-14, final test code): emptied
   arm — fold-red 2/3 draws, mint-pass 1/3 (gpt-5-mini stochastically
   mints an existential meta-claim "the claim exists that X" on synthetic
   prose); restored arm — green 3/3. The fold is NOT deterministically
   reproducible off the real corpus (control-arm fold rate on real prose:
   10/10), so this test is the carriage REGRESSION GUARD, not the causal
   evidence for the instruction; the causal evidence is the #1745
   measurement artifact (real prose, 2 passages x 2 arms x k=5).
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from argumentation_analysis.orchestration.invoke_callables import (
    _invoke_fact_extraction,
)

INVOKE_PATH = "argumentation_analysis.orchestration.invoke_callables"

# Synthetic op-ed (invented city, no dataset content), production window
# density (~2400 chars). The pro-subsidy position is NEVER asserted
# standalone — it exists only inside "whatever its architects still claim"
# and "the subsidy coalition's insistence that ... is the same thinking
# that gave us the failed stadium bond".
_TEXT = (
    "Downtown's revival did not come from the riverfront subsidy program, "
    "whatever its architects still claim. The program burned through forty "
    "million dollars in six years and delivered a convention center that "
    "sits empty most winters. The real drivers were the community college's "
    "night classes, which doubled enrollment in four years; the ferry "
    "contract, which put eleven hundred commuters on the water every "
    "morning; and the police walking beats again after the 2019 staffing "
    "deal. Each of those moved the vacancy numbers before a single subsidy "
    "check cleared. The subsidy coalition's insistence that the program "
    "deserves the credit is the same thinking that gave us the failed "
    "stadium bond and the abandoned tech campus: pick a flagship, pour "
    "money, announce success. The bond cost taxpayers thirty-one million "
    "and the stadium hosted four concerts. The tech campus drew no anchor "
    "tenant and was converted to storage. What actually revives a downtown "
    "is boring: permit times cut from nine months to eleven weeks, parking "
    "that costs less than the bus, landlords who can evict non-paying "
    "tenants inside a season, and a sanitation contract that gets the trash "
    "picked up before noon. Every one of those was proposed in the 2017 "
    "commission report the council shelved. The council keeps voting to "
    "renew the subsidy because canceling it would mean admitting the "
    "original vote was wrong, and the architects of that vote still chair "
    "the committees that would have to say so. The county next door cut "
    "its subsidy in 2021 and its vacancy rate fell below ours within two "
    "years. Ours rose. The program's own consultant counted the jobs it "
    "'created' by including transfers from existing hotels. When the state "
    "auditor asked for payroll records, the program office provided "
    "rounding-error summaries instead. Forty million, and the best its "
    "defenders can point to is a plaza where the fountains work on "
    "weekends."
)

# Disqualification markers — the author's evaluation. An item carrying one
# of these states the position AS THE AUTHOR DISQUALIFIES IT, not as its
# holder would state it; it cannot count as the neutral pole. Marker
# family mirrors the #1745 measurement script's _LOADED_MARKERS plus the
# fold frames observed on this text's baseline inventories.
_LOADED = (
    "fantasy",
    "fail",
    "myth",
    "wrong",
    "absurd",
    "fals",
    "so-called",
    "merely",
    "destroy",
    "harm",
    "decay",
    "deferred",
    "blocked",
    "waiting list",
    "not solve",
    "cannot solve",
    "whatever",
    "insistence",
    "challeng",
    "not result",
    "did not",
    "denial",
    "denies",
    "dismiss",
    "burned",
    "abandoned",
    "inflat",
    "resist",
    "accuse",
    "minimal",
    "shelved",
    "pour money",
    "announce success",
    "underused",
)


def _resp(content: str) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


def _item_texts(result: dict) -> list[str]:
    """Item TEXTS only — the verbatim source_quote legitimately contains
    the disqualifying phrasing of the cited mention, so scanning quotes
    would false-red a correct neutral item (observed on treated draws)."""
    texts: list[str] = []
    for key in ("arguments", "claims"):
        for item in result.get(key, []):
            if isinstance(item, dict):
                combined = str(item.get("text", ""))
            elif item:
                combined = str(item)
            else:
                continue
            if combined.strip():
                texts.append(combined.lower())
    return texts


def _target_content(t: str) -> bool:
    """Cited position: the subsidy program deserves the revival credit."""
    return ("subsidy" in t or "riverfront" in t) and (
        "credit" in t or "deserves" in t or "deserve" in t
    )


def _attacker_content(t: str) -> bool:
    """Speaker position: the program failed; the revival came from elsewhere."""
    return (
        "vacancy" in t
        or "ferry" in t
        or "permit" in t
        or "forty million" in t
        or "fountain" in t
        or "stadium" in t
        or "auditor" in t
        or "night classes" in t
    )


class TestInstructionReachesTheWire:
    """Contract 1 — the deployed system prompt carries the measured
    instruction VERBATIM (fidelity pin to the #1745 two-arm evidence)."""

    def test_instruction_reaches_the_wire(self):
        import argumentation_analysis.orchestration.invoke_callables as mod

        assert mod._OPPOSING_POSITIONS_INSTRUCTION.strip(), (
            "_OPPOSING_POSITIONS_INSTRUCTION is empty — the #1745 geste is "
            "not deployed"
        )
        valid_json = (
            '{"arguments": [{"text": "x", "source_quote": "x"}], '
            '"claims": [], "summary": "ok"}'
        )
        with (
            patch(
                f"{INVOKE_PATH}._get_openai_client",
                return_value=(MagicMock(), "m"),
            ),
            patch(
                f"{INVOKE_PATH}._guarded_chat_completion",
                new=AsyncMock(return_value=_resp(valid_json)),
            ) as mock_call,
            patch(f"{INVOKE_PATH}._get_determinism_params", return_value={}),
        ):
            asyncio.new_event_loop().run_until_complete(
                _invoke_fact_extraction("some text", {"_state_object": None})
            )
        system_message = mock_call.call_args.kwargs["messages"][0]["content"]
        assert mod._OPPOSING_POSITIONS_INSTRUCTION in system_message, (
            "the #1745 instruction is not threaded into the extraction " "system prompt"
        )


class TestInventoryCarriesBothPoles:
    """Contract 2 — BEHAVIOUR on a real LLM draw: the cited position must
    exist as its own non-disqualified item (a node the attack axes can
    attack). See module docstring for the honest substitution result."""

    @pytest.mark.requires_api
    async def test_inventory_carries_both_poles_of_explicit_opposition(self):
        result = await _invoke_fact_extraction(_TEXT, {"_state_object": None})
        assert (
            result.get("extraction_status") == "ok"
        ), f"extraction failed: {result.get('extraction_status')}"
        texts = _item_texts(result)
        assert texts, "empty inventory"

        # Attacker pole (the speaker's own assertion) — sanity anchor.
        assert any(
            _attacker_content(t) for t in texts
        ), "attacker pole (speaker position) absent from the inventory"
        # Target pole: a standalone restatement WITHOUT the author's
        # disqualification. A fused item carries a loaded marker by
        # construction and cannot satisfy this.
        neutral_target = [
            t for t in texts if _target_content(t) and not any(m in t for m in _LOADED)
        ]
        assert neutral_target, (
            "target pole FOLDED: the cited position (the subsidy program "
            "deserves the revival credit) appears only inside the "
            "speaker's evaluative items, never as its own neutral item — "
            "_OPPOSING_POSITIONS_INSTRUCTION not in effect (#1745). "
            f"Inventory: {texts}"
        )
