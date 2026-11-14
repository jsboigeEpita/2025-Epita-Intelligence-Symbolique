"""#3547 — the counterfactual: what would fall if a premise were withdrawn.

The planted text (issue ask 1): four notes on a town market. A (« the survey
shows residents want the market moved ») supports B (« So the market will
move to the square »), which supports C (« So the square's parking must be
rebuilt »); D (« The square's lighting is already scheduled for replacement
») stands alone. Today the pipeline retracts a belief only when a fallacy
targets it — nothing says that withdrawing A would leave B and C without
their only justification while D holds.

The pass answers that on a COPY of the network: withdrawing A releases B
(its only justification died), the release cascades to C, and D — an
independent premise with no justification ever — never had one to lose. A
second live support on B (the mutation control) keeps B and C standing: the
pass measures justification structure, not graph reachability. The session's
own labels, retraction chain and trace never move.

Privacy: every fixture below is synthetic — opaque ids (arg_N) and neutral
text; no corpus content.

Chain under witness:
- solver: the real ``_invoke_jtms`` on the planted context →
  ``counterfactual_withdrawals`` (premises arg_1→[arg_2, arg_3],
  arg_2→[arg_3]) + ``counterfactual_premises_tested`` == 2;
- mutation: a second support (arg_4 → arg_2) removes arg_1's entry;
- positive control: a fallacy on arg_2 still produces today's chain entry;
- no side effect: ``JTMS.copy()`` mutations leave the original's labels,
  chain and trace untouched, and the counterfactual adds no chain entry;
- render: ``build_act3_evidence`` carries the issue's sentence — premise and
  falls named as TEXT, « le reste tient », the player whose case rests on
  the ground when the strategist's players locate it, no player otherwise,
  and no ``belief_maintenance`` finding when nothing falls.
"""

from __future__ import annotations

import types

from argumentation_analysis.orchestration.invoke_callables import _invoke_jtms
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_evidence,
)
from argumentation_analysis.services.jtms.jtms_core import JTMS

A_TEXT = "The survey shows residents want the market moved"
B_TEXT = "So the market will move to the square"
C_TEXT = "So the square's parking must be rebuilt"
D_TEXT = "The square's lighting is already scheduled for replacement"

UNITS = [
    ("arg_1", A_TEXT),
    ("arg_2", B_TEXT),
    ("arg_3", C_TEXT),
    ("arg_4", D_TEXT),
]
SUPPORTS = [["arg_1", "arg_2"], ["arg_2", "arg_3"]]

# The persona players (render class): one whose quote sits on A's ground,
# one whose quote sits elsewhere.
GROUNDED_PLAYER = {
    "name": "la marchande Ova",
    "role": "commerçante",
    "stance": "for",
    "quote": A_TEXT[:40],
    "offset": 10,
    "basis": "text",
}
DISTANT_PLAYER = {
    "name": "l'éclairagiste Lum",
    "role": "technicien",
    "stance": "against",
    "quote": D_TEXT[:40],
    "offset": 900,
    "basis": "text",
}
PROVENANCE = {
    "arg_1": {"producer": "llm_extract", "offset": 10, "source_quote": A_TEXT},
    "arg_2": {"producer": "llm_extract", "offset": 300, "source_quote": B_TEXT[:30]},
    "arg_3": {"producer": "llm_extract", "offset": 500, "source_quote": C_TEXT[:30]},
    "arg_4": {"producer": "llm_extract", "offset": 900, "source_quote": D_TEXT},
}


def _belief_name(uid: str) -> str:
    text = dict(UNITS)[uid]
    return f"{uid}:{text[:66]}"


def _context(supports: list | None = None, fallacy_on: str | None = None) -> dict:
    fallacies = []
    if fallacy_on:
        fallacies.append(
            {
                "type": "hasty_generalization",
                "explanation": "Generalisation synthetique",
                "target_argument": fallacy_on,
                "confidence": 0.8,
            }
        )
    return {
        "phase_extract_output": {
            "arguments": [{"unit_id": uid, "text": text} for uid, text in UNITS],
            "claims": [],
        },
        "phase_hierarchical_fallacy_output": {"fallacies": fallacies},
        "supports": list(supports if supports is not None else SUPPORTS),
    }


def _premise_entry(result: dict, uid: str) -> dict | None:
    name = _belief_name(uid)
    for entry in result.get("counterfactual_withdrawals", []):
        if entry.get("premise") == name:
            return entry
    return None


def _fall_names(entry: dict | None) -> set[str]:
    if not entry:
        return set()
    return {f.get("name") for f in entry.get("falls", [])}


class TestTheWithdrawalDropsTheDependents:
    async def test_withdrawing_a_drops_b_and_c(self) -> None:
        """The witness: A's entry falls exactly B and C, in cascade order."""
        result = await _invoke_jtms("texte synthetique", _context())
        entry = _premise_entry(result, "arg_1")
        assert entry is not None, result.get("counterfactual_withdrawals")
        assert _fall_names(entry) == {_belief_name("arg_2"), _belief_name("arg_3")}
        # Cascade order: B (directly premised on A) before C (premised on B).
        assert [f["name"] for f in entry["falls"]][0] == _belief_name("arg_2")

    async def test_withdrawing_b_drops_c_only(self) -> None:
        result = await _invoke_jtms("texte synthetique", _context())
        entry = _premise_entry(result, "arg_2")
        assert entry is not None
        assert _fall_names(entry) == {_belief_name("arg_3")}

    async def test_d_stands_alone_and_never_falls(self) -> None:
        """D has no justification ever — there is nothing to lose."""
        result = await _invoke_jtms("texte synthetique", _context())
        for entry in result.get("counterfactual_withdrawals", []):
            assert _belief_name("arg_4") not in _fall_names(entry)
        assert result["beliefs"][_belief_name("arg_4")]["valid"] is True

    async def test_premises_tested_is_said(self) -> None:
        """Two premises carry dependents (A and B); the count travels."""
        result = await _invoke_jtms("texte synthetique", _context())
        assert result["counterfactual_premises_tested"] == 2

    async def test_records_carry_unit_ids_and_texts(self) -> None:
        """The render's label/persona lookups need ids, the prose needs text."""
        result = await _invoke_jtms("texte synthetique", _context())
        entry = _premise_entry(result, "arg_1")
        assert entry["premise_unit_id"] == "arg_1"
        assert A_TEXT[:66] in entry["text"]
        by_name = {f["name"]: f for f in entry["falls"]}
        assert by_name[_belief_name("arg_2")]["unit_id"] == "arg_2"
        assert B_TEXT[:66] in by_name[_belief_name("arg_2")]["text"]


class TestMutationControl:
    async def test_a_second_live_support_keeps_everything_standing(self) -> None:
        """D also supports B: withdrawing A then drops NEITHER B nor C —
        the pass measures justification structure, not reachability."""
        supports = [["arg_1", "arg_2"], ["arg_2", "arg_3"], ["arg_4", "arg_2"]]
        result = await _invoke_jtms("texte synthetique", _context(supports=supports))
        assert _premise_entry(result, "arg_1") is None, result[
            "counterfactual_withdrawals"
        ]
        # B's own entry still falls C (withdrawing B kills C's only rule).
        assert _premise_entry(result, "arg_2") is not None


class TestPositiveControlAndSideEffects:
    async def test_a_fallacy_still_produces_todays_chain_entry(self) -> None:
        """The positive control: a fallacy on B retracts it exactly as before
        the counterfactual pass existed."""
        result = await _invoke_jtms("texte synthetique", _context(fallacy_on="arg_2"))
        triggers = [e.get("trigger") for e in result["retraction_chain"]]
        assert _belief_name("arg_2") in triggers

    async def test_the_counterfactual_adds_no_chain_entry(self) -> None:
        """No fallacy in the context → the session's chain stays empty: the
        copy's releases are questions, not retractions."""
        result = await _invoke_jtms("texte synthetique", _context())
        assert result["retraction_chain"] == []
        assert result["counterfactual_withdrawals"]  # the pass DID run

    async def test_a_fallacy_never_eligible_as_a_fall(self) -> None:
        """A belief the pipeline retracted (False) is not a withdrawal fall:
        only beliefs that HELD are asked about."""
        result = await _invoke_jtms("texte synthetique", _context(fallacy_on="arg_2"))
        for entry in result.get("counterfactual_withdrawals", []):
            assert _belief_name("arg_2") not in _fall_names(entry)


class TestCopyPrimitive:
    """The no-side-effect root: mutations on the copy never reach the original."""

    def _network(self) -> JTMS:
        net = JTMS()
        for name in ("a", "b", "c"):
            net.add_belief(name)
        net.add_justification(["a"], [], "b")
        net.add_justification(["b"], [], "c")
        net.set_belief_validity("a", True)
        net.set_belief_validity("b", True)
        net.set_belief_validity("c", True)
        return net

    def test_labels_unchanged_after_copy_mutation(self):
        net = self._network()
        before = {n: b.valid for n, b in net.beliefs.items()}
        net.enable_tracing()
        copy = net.copy()
        copy.set_belief_validity("a", False)
        copy.set_belief_validity("b", None)
        assert {n: b.valid for n, b in net.beliefs.items()} == before
        assert copy.beliefs["a"].valid is False
        assert copy.beliefs["b"].valid is None

    def test_copy_tracing_stays_off_and_trace_stays_empty(self):
        """A counterfactual is not a retraction: the copy never traces."""
        net = self._network()
        net.enable_tracing()
        copy = net.copy()
        copy.set_belief_validity("a", False)
        assert copy._tracing_enabled is False
        assert copy._retraction_trace == []
        assert net._retraction_trace == []

    def test_facts_travel_to_the_copy(self):
        net = self._network()
        copy = net.copy()
        assert copy._facts == net._facts
        assert {n: b.valid for n, b in copy.beliefs.items()} == {
            n: b.valid for n, b in net.beliefs.items()
        }


class TestTheRender:
    """Acte III carries the issue's sentence (through build_act3_evidence)."""

    def _state(
        self,
        withdrawals: list | None = None,
        players: list | None = None,
        provenance: dict | None = None,
    ) -> types.SimpleNamespace:
        if withdrawals is None:
            withdrawals = [
                {
                    "premise": _belief_name("arg_1"),
                    "premise_unit_id": "arg_1",
                    "text": A_TEXT,
                    "falls": [
                        {
                            "name": _belief_name("arg_2"),
                            "unit_id": "arg_2",
                            "text": B_TEXT,
                        },
                        {
                            "name": _belief_name("arg_3"),
                            "unit_id": "arg_3",
                            "text": C_TEXT,
                        },
                    ],
                }
            ]
        return types.SimpleNamespace(
            jtms_counterfactual_withdrawals=withdrawals,
            strategic_read={"players": players or []},
            argument_provenance=dict(
                provenance if provenance is not None else PROVENANCE
            ),
        )

    def _statement(self, state: types.SimpleNamespace) -> str:
        evidence = build_act3_evidence(state)
        for finding in evidence.structured_findings:
            if finding.capability == "belief_maintenance":
                return finding.statement
        return ""

    def test_the_sentence_names_texts_and_says_the_rest_holds(self):
        statement = self._statement(self._state())
        assert A_TEXT[:60] in statement, statement
        assert B_TEXT[:60] in statement, statement
        assert C_TEXT[:60] in statement, statement
        assert "seule justification" in statement, statement
        assert "le reste tient" in statement, statement

    def test_the_sentence_names_the_grounded_player(self):
        statement = self._statement(
            self._state(players=[DISTANT_PLAYER, GROUNDED_PLAYER])
        )
        assert "la marchande Ova" in statement, statement
        assert "Lum" not in statement, statement

    def test_no_player_names_no_player(self):
        statement = self._statement(self._state(players=[]))
        assert "repose sur cet appui" not in statement, statement

    def test_no_withdrawal_is_honest_absence(self):
        """Nothing falls → no belief_maintenance finding, no fabricated line."""
        state = self._state(withdrawals=[])
        assert self._statement(state) == ""
        state = types.SimpleNamespace()  # field absent (pre-#3547 states)
        assert self._statement(state) == ""

    def test_a_fall_without_text_is_skipped(self):
        withdrawals = [
            {
                "premise": _belief_name("arg_1"),
                "premise_unit_id": "arg_1",
                "text": A_TEXT,
                "falls": [{"name": _belief_name("arg_2"), "unit_id": "arg_2"}],
            }
        ]
        statement = self._statement(self._state(withdrawals=withdrawals))
        assert statement == ""
