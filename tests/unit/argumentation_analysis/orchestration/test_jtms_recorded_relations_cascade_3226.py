"""#3226 — a JTMS justification carries only a RECORDED relation.

The R1110 replay (issue #3226) showed one fallacy on one unit (arg_38)
retracting every extracted claim: ``_invoke_jtms`` Step 2 wired ``ALL
argument beliefs`` into the IN-list of EVERY claim
(``session.add_justification(arg_beliefs, [], claim)``), so any retraction
anywhere cascaded through the whole network — a justification that recorded
nothing. The claim-less ``elif`` branch did the same to a synthetic
``overall_argument_validity`` conclusion (same defect class).

The repair: the synthetic network disappears. A justification is added only
for a relation the run actually recorded — a bipolar support pair between
two units, or a claim's recorded source unit when the producer stamps one.
A claim with no recorded support is an unjustified belief (valid=None, the
recompute's honest "unknown"), the result says so
(``claims_without_recorded_support``), and the debate context receives each
retraction's CAUSE (« set False by fallacy X on unit Y » / « cascaded
through justification J ») so a cascade is never read as a judgement on the
claim. The cascade itself survives — it now flows only through recorded
edges and names them (``cascade_edges`` on the trace entry).

Privacy: every fixture below is synthetic — opaque ids (arg_N) and neutral
French text; no corpus content. The stored-state replay reads local
gitignored states only.
"""

from __future__ import annotations

import glob
import json
import os
from pathlib import Path

import pytest

from argumentation_analysis.orchestration.invoke_callables import _invoke_jtms

# ── The R1110 recorded shape, rebuilt synthetically ─────────────────────
# Ten units under the stratified budget, six extracted claims, ONE fallacy
# (whataboutism) carrying its target's own id — the exact conditions under
# which the paid pass measured a 6-claim cascade.
_UNIT_IDS = [
    "arg_13",
    "arg_17",
    "arg_24",
    "arg_29",
    "arg_38",
    "arg_45",
    "arg_52",
    "arg_64",
    "arg_75",
    "arg_85",
]
_UNIT_TEXTS = {uid: f"Unite synthetique {uid}" for uid in _UNIT_IDS}
_CLAIM_TEXTS = [f"Conclusion synthetique numero {i}" for i in range(1, 7)]
_FALLACY_ON_ARG_38 = {
    "type": "whataboutism",
    "explanation": "Repli synthetique vers un autre sujet",
    "target_argument": "arg_38",
}


def _base_context() -> dict:
    return {
        "phase_extract_output": {
            "arguments": [
                {"unit_id": uid, "text": _UNIT_TEXTS[uid]} for uid in _UNIT_IDS
            ],
            "claims": [{"text": t} for t in _CLAIM_TEXTS],
        },
        "phase_hierarchical_fallacy_output": {
            "fallacies": [dict(_FALLACY_ON_ARG_38)],
        },
    }


def _claim_names() -> list[str]:
    return list(_CLAIM_TEXTS)


def _arg_belief_name(uid: str) -> str:
    return f"{uid}:{_UNIT_TEXTS[uid][:66]}"


def _arg38_entry(result: dict) -> dict:
    """The retraction-chain entry whose trigger is the arg_38 belief."""
    trigger = _arg_belief_name("arg_38")
    entries = [
        e for e in result.get("retraction_chain", []) if e.get("trigger") == trigger
    ]
    assert entries, f"no retraction entry for {trigger}"
    return entries[0]


class TestTheCascadeCarriesOnlyRecordedRelations:
    async def test_a_fallacy_on_one_unit_retracts_no_claim(self) -> None:
        """Born red: on main the arg_38 retraction cascades to all 6 claims."""
        result = await _invoke_jtms("texte synthetique", _base_context())
        entry = _arg38_entry(result)
        assert set(entry["cascaded"]) & set(_claim_names()) == set()

    async def test_unsupported_claims_stay_unknown_not_false(self) -> None:
        """A claim with no recorded justification is valid=None (unknown) —
        the cascade must not relabel it False by construction."""
        result = await _invoke_jtms("texte synthetique", _base_context())
        for claim in _claim_names():
            assert result["beliefs"][claim]["valid"] is None, claim

    async def test_claims_without_recorded_support_are_said_so(self) -> None:
        """The result carries the honest absence, not a synthetic network."""
        result = await _invoke_jtms("texte synthetique", _base_context())
        assert result["claims_without_recorded_support"] == _claim_names()

    async def test_no_synthetic_overall_conclusion_on_claim_less_run(self) -> None:
        """The ``elif`` branch of the same defect: arguments alone must not
        manufacture an all-args-supported conclusion."""
        context = _base_context()
        context["phase_extract_output"] = {
            "arguments": [
                {"unit_id": uid, "text": _UNIT_TEXTS[uid]} for uid in _UNIT_IDS[:3]
            ],
            "claims": [],
        }
        context["phase_hierarchical_fallacy_output"] = {"fallacies": []}
        result = await _invoke_jtms("texte synthetique", context)
        assert "overall_argument_validity" not in result["beliefs"]


class TestTheCascadeStillFlowsThroughARecordedRelation:
    """Anti-pendulum: the repair wires RECORDED edges, it does not delete
    the cascade. Mechanics on this producer: Step 3 sets every unit belief
    as a hard fact (existing semantics, untouched), so a unit→unit support
    pair wires a real justification edge but cannot drop its target — a
    fact keeps its label. The cascade fires through recorded relations on
    DERIVED conclusions: a claim whose recorded source unit is retracted
    drops through exactly that edge."""

    async def test_unit_support_pair_wires_one_recorded_edge(self) -> None:
        context = _base_context()
        # [source, target] — the bipolar pair convention: arg_38 REINFORCES
        # arg_45. The edge is recorded as a justification on arg_45…
        context["supports"] = [["arg_38", "arg_45"]]
        result = await _invoke_jtms("texte synthetique", context)
        arg45 = result["beliefs"][_arg_belief_name("arg_45")]
        assert any(
            j["in_list"] == [_arg_belief_name("arg_38")]
            for j in arg45["justifications"]
        )
        # …the network really depends on it now (not on a synthetic count)…
        assert result["has_real_dependencies"] is True
        # …and the fact target does not drop (Step 3 semantics, untouched).
        entry = _arg38_entry(result)
        assert _arg_belief_name("arg_45") not in entry["cascaded"]

    async def test_a_recorded_source_unit_cascades_its_claim_only(self) -> None:
        """The cascade through a recorded relation: claim 3's recorded
        source is arg_38, so retracting arg_38 drops claim 3 — and ONLY
        claim 3, through the recorded edge. Born red on main: every claim
        cascades there (all-args IN-list), with no cause named."""
        context = _base_context()
        context["phase_extract_output"]["claims"][2]["source_unit"] = "arg_38"
        result = await _invoke_jtms("texte synthetique", context)
        entry = _arg38_entry(result)
        # Claim 3 through its recorded source edge, plus the session's
        # defeat machinery: the fallacy's OUT-list defeat auto-wires
        # ``_CONTRADICTION_`` (extended_belief.py:157-163), which was True
        # while fallacy and target both held and falls with the target —
        # a recorded relation too, not a synthetic one.
        assert set(entry["cascaded"]) == {_CLAIM_TEXTS[2], "_CONTRADICTION_"}
        # The edge the propagation followed — sibling key (`cascaded` stays
        # list-of-str for its readers: narrative_synthesis, html_report,
        # cross_reference_graph).
        edges = entry.get("cascade_edges", [])
        assert any(
            e.get("conclusion") == _CLAIM_TEXTS[2]
            and e.get("through_in") == [_arg_belief_name("arg_38")]
            for e in edges
        )
        # The reader-facing cause map: the trigger's fallacy, the cascade's
        # justification.
        causes = entry.get("causes", {})
        assert (
            causes.get(_arg_belief_name("arg_38"), "")
            == "set False by fallacy whataboutism on unit arg_38"
        )
        cascade_cause = causes.get(_CLAIM_TEXTS[2], "")
        assert "cascaded through justification" in cascade_cause
        assert _arg_belief_name("arg_38") in cascade_cause
        # The other claims were never related to arg_38: still unknown.
        for claim in _claim_names()[:2] + _claim_names()[3:]:
            assert result["beliefs"][claim]["valid"] is None, claim

    async def test_cascaded_stays_a_plain_list_of_names(self) -> None:
        """Guard for the chain's existing readers (#3242 scrubber join,
        narrative_synthesis sum-of-len): the entry's `cascaded` key keeps
        its list-of-str shape — causes live in sibling keys only."""
        context = _base_context()
        context["phase_extract_output"]["claims"][2]["source_unit"] = "arg_38"
        result = await _invoke_jtms("texte synthetique", context)
        for entry in result["retraction_chain"]:
            assert isinstance(entry["cascaded"], list)
            assert all(isinstance(n, str) for n in entry["cascaded"])


class TestTheDebateContextReadsTheCause:
    """The first consumer: the debate prompt lists retracted beliefs with
    WHY each fell — and only beliefs that are actually False (valid=None is
    unknown, not retracted — the old ``not v.get("valid", True)`` filter
    counted unknowns as retracted)."""

    def _lines(self, result: dict) -> list[str]:
        from argumentation_analysis.orchestration.invoke_callables import (
            _debate_retraction_lines,
        )

        return _debate_retraction_lines(result)

    async def test_only_false_beliefs_are_listed_with_their_cause(self) -> None:
        result = await _invoke_jtms("texte synthetique", _base_context())
        lines = self._lines(result)
        joined = "\n".join(lines)
        # The directly retracted unit, with its cause.
        assert _arg_belief_name("arg_38") in joined
        assert "whataboutism" in joined
        # Unknown claims are NOT retracted — none of them is listed.
        for claim in _claim_names():
            assert claim not in joined, claim

    async def test_a_cascaded_claim_is_not_listed_as_retracted(self) -> None:
        """A claim dropped by a cascade is unknown (valid=None), not False:
        the debate prompt must not list it as a retracted belief — that is
        the "never read a cascade as a judgement" guarantee."""
        context = _base_context()
        context["phase_extract_output"]["claims"][2]["source_unit"] = "arg_38"
        result = await _invoke_jtms("texte synthetique", context)
        joined = "\n".join(self._lines(result))
        assert _arg_belief_name("arg_38") in joined  # the trigger, with cause
        assert _CLAIM_TEXTS[2] not in joined  # the cascaded claim: absent

    def test_a_false_belief_from_a_cascade_carries_its_cause_line(self) -> None:
        """When a cascaded belief IS False (a false fact the propagation
        also reached), its debate line names the justification — the
        relation, never a bare judgement."""
        jtms_output = {
            "beliefs": {
                "arg_1:Texte": {"valid": False},
                "Conclusion synthetique": {"valid": False},
            },
            "retraction_chain": [
                {
                    "trigger": "arg_1:Texte",
                    "retracted": ["arg_1:Texte"],
                    "cascaded": ["Conclusion synthetique"],
                    "causes": {
                        "arg_1:Texte": "set False by fallacy straw man on unit arg_1",
                        "Conclusion synthetique": (
                            "cascaded through justification arg_1:Texte"
                        ),
                    },
                }
            ],
        }
        joined = "\n".join(self._lines(jtms_output))
        assert "set False by fallacy straw man on unit arg_1" in joined
        assert "cascaded through justification arg_1:Texte" in joined


class TestTheSyntheticNetworkIsGone:
    def test_no_all_arguments_in_list_wiring_remains(self) -> None:
        """Static mutation guard (DoD): restoring the "all arguments IN-list
        for each claim" block reddens here and in the cascade tests."""
        import argumentation_analysis.orchestration.invoke_callables as ic

        source = Path(ic.__file__).read_text(encoding="utf-8-sig")
        assert "arg_beliefs, [], claim" not in source
        assert "arg_beliefs, [], conclusion" not in source


# ── Deterministic replay on stored states (0 LLM) ───────────────────────
# The campaign states live on the coordinator's seat; the harness runs
# wherever they exist and measures: one fallacy on one stored trigger unit
# cascades to ZERO extracted claims.
_STORED_STATES = sorted(
    glob.glob(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "..",
            "..",
            "argumentation_analysis",
            "evaluation",
            "results",
            "campaign_2841_lecture",
            "04_annexes",
            "states",
            "state_full_*.json",
        )
    )
)


def _stored_units_and_claims(data: dict) -> tuple[list[dict], list[dict], str | None]:
    """Rebuild the _invoke_jtms inputs from a stored state's own containers
    (opaque ids and text stay local — nothing leaves this process)."""
    arguments: list[dict] = []
    raw_args = data.get("identified_arguments")
    if isinstance(raw_args, dict):
        arguments = [{"unit_id": str(k), "text": str(v)} for k, v in raw_args.items()]
    claims = [
        {"text": str(e.get("content", ""))}
        for e in (data.get("extracts") or [])
        if isinstance(e, dict) and e.get("type") == "claim" and e.get("content")
    ]
    chain = data.get("jtms_retraction_chain") or []
    trigger_uid = None
    if chain and isinstance(chain[0], dict):
        trigger = str(chain[0].get("trigger", ""))
        if ":" in trigger:
            trigger_uid = trigger.split(":", 1)[0]
    return arguments, claims, trigger_uid


@pytest.mark.skipif(not _STORED_STATES, reason="no stored states on this seat")
class TestTheStoredStateReplay:
    async def test_one_fallacy_cascades_to_zero_claims(self) -> None:
        """The DoD replay, seat-agnostic: for each stored state, one
        fallacy on a stored trigger unit reaches 0 extracted claims (base,
        on main: 6 per trigger on doc_A)."""
        for path in _STORED_STATES:
            data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
            arguments, claims, trigger_uid = _stored_units_and_claims(data)
            if not arguments or not claims or not trigger_uid:
                continue
            if trigger_uid not in {a["unit_id"] for a in arguments}:
                continue  # state predates the unit-id prefixes — not replayable
            context = {
                "phase_extract_output": {
                    "arguments": arguments,
                    "claims": claims,
                },
                "phase_hierarchical_fallacy_output": {
                    "fallacies": [
                        {"type": "replay_probe", "target_argument": trigger_uid}
                    ]
                },
            }
            result = await _invoke_jtms("replay", context)
            for entry in result["retraction_chain"]:
                leaked = set(entry["cascaded"]) & {
                    c["text"] for c in claims if c["text"] in result["beliefs"]
                }
                assert not leaked, f"{os.path.basename(path)}: {leaked}"
