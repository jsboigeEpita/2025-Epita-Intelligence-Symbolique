"""#3123 — the synthesis reads the qualifiers its own input carries.

The R1104 render made two inferences its input never licensed:

* the grounded extension covered most arguments and the synthesis sold that
  breadth as robustness, while the evaluated attack graph held fewer attacks
  than arguments (the retention accounting was in the state and never reached
  the writer);
* a ``between_sources`` unsatisfiability — a conflict between source units
  with no speaker recorded — was read as the discourse's own incoherence.

The repair is input + a deterministic check, not a prompt plea: the briefing
carries the measured density and says what each cause class licenses, Section 9
keeps the cause it used to drop, and a non-LLM checker flags a produced text
that reads a qualifier as a conclusion. Flags never rewrite.

Everything here is offline: real ``UnifiedAnalysisState`` objects, recorded
synthesis strings, no kernel service, no network, zero spend.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, create_autospec

import pytest
from semantic_kernel import Kernel

from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
    DeepSynthesisAgent,
)
from argumentation_analysis.agents.core.synthesis.deep_synthesis_models import (
    DeepSynthesisReport,
)
from argumentation_analysis.agents.core.synthesis.reading_license import (
    check_reading_license,
)
from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_narrative,
)

_SPARSE_TEXT = (
    "L'extension grounded couvre les trois arguments et le propos est robuste."
)


def _state_with_graph(
    arguments, attacks, submitted=None, retained=None
) -> UnifiedAnalysisState:
    state = UnifiedAnalysisState("texte")
    entry = {
        "name": "af_1",
        "arguments": list(arguments),
        "attacks": [list(a) for a in attacks],
    }
    if submitted is not None:
        entry["attacks_submitted"] = submitted
    if retained is not None:
        entry["attacks_retained"] = retained
    state.dung_frameworks["af_1"] = entry
    return state


def _state_with_cause(cause: str, logic: str = "fol") -> UnifiedAnalysisState:
    state = UnifiedAnalysisState("texte")
    if logic == "fol":
        state.add_fol_analysis_result(["P(a)"], False, [], message="inconsistent")
        state.fol_analysis_results[-1]["consistency_cause"] = {
            "cause": cause,
            "ground": cause == "self_contradiction",
        }
    else:
        state.add_propositional_analysis_result(["a"], False, {})
        state.propositional_analysis_results[-1]["consistency_cause"] = {
            "cause": cause,
            "mus": True,
        }
    return state


class TestReadingLicenseCheck:
    def test_breadth_sold_as_robustness_is_flagged(self):
        state = _state_with_graph(["arg_1", "arg_2", "arg_3"], [["arg_1", "arg_2"]])
        result = check_reading_license(_SPARSE_TEXT, state)
        kinds = [flag["kind"] for flag in result["flags"]]
        assert kinds == ["breadth_as_robustness"]
        measured = result["flags"][0]["measured"]["frameworks"][0]
        assert measured["density"] == pytest.approx(1 / 3)
        assert measured["arguments"] == 3 and measured["attacks"] == 1

    def test_the_same_sentence_on_a_dense_graph_is_not_flagged(self):
        state = _state_with_graph(
            ["arg_1", "arg_2", "arg_3"],
            [["arg_1", "arg_2"], ["arg_2", "arg_3"], ["arg_3", "arg_1"]],
        )
        assert check_reading_license(_SPARSE_TEXT, state)["flags"] == []

    def test_a_negated_robustness_statement_is_not_a_claim(self):
        state = _state_with_graph(["arg_1", "arg_2", "arg_3"], [["arg_1", "arg_2"]])
        text = (
            "L'extension grounded couvre tout, mais elle n'est pas robuste "
            "face à une attaque supplémentaire."
        )
        assert check_reading_license(text, state)["flags"] == []

    def test_an_entirely_dropped_edge_set_makes_the_graph_sparse(self):
        # Every submitted edge was dropped before the frame was evaluated
        # (#1704's honest empty report): breadth there says nothing.
        state = _state_with_graph(["arg_1", "arg_2"], [], submitted=5, retained=0)
        result = check_reading_license(
            "Le graphe est robuste : l'extension grounded couvre les deux arguments.",
            state,
        )
        assert [f["kind"] for f in result["flags"]] == ["breadth_as_robustness"]

    def test_discourse_incoherence_with_between_sources_is_flagged(self):
        state = _state_with_cause("between_sources")
        result = check_reading_license(
            "Le discours est incohérent : ses engagements ne tiennent pas.", state
        )
        assert [f["kind"] for f in result["flags"]] == ["discourse_incoherence"]
        assert result["flags"][0]["measured"]["recorded_causes"] == ["between_sources"]

    def test_discourse_incoherence_with_self_contradiction_is_a_finding(self):
        # A self-contradiction IS attributable to the voice; the check must not
        # suppress the real finding (#1019 anti-pendulum).
        state = _state_with_cause("self_contradiction")
        assert (
            check_reading_license("Le discours est incohérent.", state)["flags"] == []
        )

    def test_a_sentence_that_names_the_conflict_site_is_not_flagged(self):
        state = _state_with_cause("between_sources")
        text = (
            "Le discours porte une contradiction entre unités sources "
            "(u1 / u2) — locuteurs non documentés par ce run."
        )
        assert check_reading_license(text, state)["flags"] == []

    def test_an_absent_synthesis_yields_no_flag(self):
        state = _state_with_cause("between_sources")
        result = check_reading_license("", state)
        assert result["flags"] == [] and result["checked"]["sentences"] == 0

    def test_a_per_speaker_claim_without_a_self_contradiction_is_flagged(self):
        state = _state_with_cause("between_voices")
        result = check_reading_license(
            "Les engagements du locuteur se contredisent.", state
        )
        assert [f["kind"] for f in result["flags"]] == ["discourse_incoherence"]

    def test_a_consistent_fol_that_decided_nothing_is_not_strength(self):
        # R1105b (Sonnet pass, coordinator instance): the synthesis called the
        # discourse robust "at the level of formal consistency" while the FOL
        # leg returned consistent without answering a single query — Act II of
        # the same render said it "ran without distinguishing anything, and
        # that is neither a strength nor a weakness".
        state = UnifiedAnalysisState("texte")
        state.add_fol_analysis_result(["P(a)"], True, [], message="consistent")
        result = check_reading_license(
            "Le discours est robuste au niveau des ancrages factuels et de la "
            "cohérence formelle.",
            state,
        )
        assert [f["kind"] for f in result["flags"]] == [
            "vacuous_consistency_as_strength"
        ]
        assert result["flags"][0]["measured"]["fol"] == {
            "vacuous_consistent": 1,
            "decisive": 0,
        }

    def test_a_decisive_fol_entry_licenses_the_strength_claim(self):
        # Positive control (coordinator): a consistent FOL entry on a theory
        # that DID decide something — an inference answered — may be cited.
        state = UnifiedAnalysisState("texte")
        state.add_fol_analysis_result(
            ["P(a)", "P(a) => Q(a)"], True, ["Q(a)"], message="consistent"
        )
        result = check_reading_license(
            "Le discours est robuste au niveau de la cohérence formelle.", state
        )
        assert result["flags"] == []

    def test_the_flag_carries_the_whole_sentence_not_a_slice(self):
        # The flag payload is the sentence as produced: a slice could only
        # hide the qualifier a reader needs (#2850 asked what the cut was
        # for; the answer was nothing, so the cut is gone).
        state = _state_with_cause("between_sources")
        sentence = (
            "Le discours est incohérent sur la totalité de ses engagements, et "
            "la synthèse en tire une lecture sévère que rien ne vient tempérer, "
            "ni la prudence factuelle des ancrages retenus, ni la longueur de "
            "la démonstration menée au fil des paragraphes de l'analyse."
        )
        assert len(sentence) > 240
        result = check_reading_license(sentence, state)
        assert [f["kind"] for f in result["flags"]] == ["discourse_incoherence"]
        assert result["flags"][0]["sentence"] == sentence


class TestBriefingCarriesTheNumbers:
    def test_the_dung_line_carries_the_density(self):
        state = _state_with_graph(["arg_1", "arg_2", "arg_3"], [["arg_1", "arg_2"]])
        briefing = DeepSynthesisAgent.build_artifact_briefing(state)
        assert "attack_density=0.33" in briefing

    def test_the_dung_line_carries_the_retention_accounting(self):
        state = _state_with_graph(
            ["arg_1", "arg_2", "arg_3"], [["arg_1", "arg_2"]], submitted=9, retained=1
        )
        briefing = DeepSynthesisAgent.build_artifact_briefing(state)
        assert "attacks_retained=1/submitted=9" in briefing

    def test_the_briefing_states_what_each_cause_class_licenses(self):
        state = _state_with_graph(["arg_1"], [])
        briefing = DeepSynthesisAgent.build_artifact_briefing(state)
        assert "READING RULES" in briefing
        for marker in (
            "self_contradiction",
            "between_voices",
            "between_sources",
            "batch_attribution",
            "unattributed_side",
            "undetermined",
        ):
            assert marker in briefing, marker

    def test_the_briefing_never_states_a_density_without_arguments(self):
        state = UnifiedAnalysisState("texte")
        state.dung_frameworks["af_empty"] = {
            "name": "af_empty",
            "arguments": [],
            "attacks": [],
        }
        briefing = DeepSynthesisAgent.build_artifact_briefing(state)
        dung_lines = [
            line
            for line in briefing.splitlines()
            if "[artifact:dung_frameworks.af_empty]" in line
        ]
        assert dung_lines, "the empty framework must still be reported"
        assert "attack_density" not in dung_lines[0]


class TestSectionNineKeepsTheCause:
    def test_a_fol_finding_carries_the_cause(self):
        state = _state_with_cause("between_sources", logic="fol")
        findings = DeepSynthesisAgent._build_formal_findings(state)
        fol = [f for f in findings if f.logic_type == "FOL"]
        assert len(fol) == 1
        assert any("unités sources" in r for r in fol[0].results), fol[0].results

    def test_a_pl_finding_carries_the_cause(self):
        state = _state_with_cause("between_sources", logic="pl")
        findings = DeepSynthesisAgent._build_formal_findings(state)
        pl = [f for f in findings if f.logic_type == "PL"]
        assert len(pl) == 1
        assert any("unités sources" in r for r in pl[0].results), pl[0].results

    def test_a_finding_without_a_cause_is_unchanged(self):
        state = UnifiedAnalysisState("texte")
        state.add_fol_analysis_result(["P(a)"], True, [], message="consistent")
        findings = DeepSynthesisAgent._build_formal_findings(state)
        assert findings[0].results == ["consistent"]


class TestSynthesizeStoresTheCheck:
    @staticmethod
    def _agent_stub():
        """The real ``synthesize`` body, with its builders and LLM paths bound.

        A real instance cannot be built offline: ``BaseAgent`` resolves the
        service id on the kernel and a mocked kernel hands back a MagicMock,
        which Pydantic rejects. The stub binds the REAL static builders and
        replaces only the three async LLM paths — so the wiring under test
        (``synthesize`` → ``attach_read_license``) is production code.
        """
        stub = SimpleNamespace(
            _llm_service_id=None,
            kernel=create_autospec(Kernel, instance=True),
            _build_source_overview=DeepSynthesisAgent._build_source_overview,
            _build_argument_map=DeepSynthesisAgent._build_argument_map,
            _build_fallacy_diagnoses=DeepSynthesisAgent._build_fallacy_diagnoses,
            _build_formal_findings=DeepSynthesisAgent._build_formal_findings,
            _build_dung_structure=DeepSynthesisAgent._build_dung_structure,
            _build_belief_retractions=DeepSynthesisAgent._build_belief_retractions,
            _build_counter_arguments=DeepSynthesisAgent._build_counter_arguments,
            _build_cross_text_parallels=DeepSynthesisAgent._build_cross_text_parallels,
            _cross_text_parallels_status=DeepSynthesisAgent._cross_text_parallels_status,
            _build_convergent_verdicts=DeepSynthesisAgent._build_convergent_verdicts,
            _build_adjudication_table=DeepSynthesisAgent._build_adjudication_table,
            count_populated_artifact_fields=(
                DeepSynthesisAgent.count_populated_artifact_fields
            ),
            validate_value_gates=DeepSynthesisAgent.validate_value_gates,
            attach_read_license=DeepSynthesisAgent.attach_read_license,
            _count_state_fields=DeepSynthesisAgent._count_state_fields,
            _count_populated_sections=DeepSynthesisAgent._count_populated_sections,
        )
        stub._llm_convergence_prose = AsyncMock(return_value="")
        stub._llm_synthesis = AsyncMock(return_value=None)
        stub.grounded_transversal_synthesis = AsyncMock(return_value="")
        return stub

    def test_synthesize_records_the_check_beside_the_value_gates(self):
        agent = self._agent_stub()
        state = _state_with_graph(["arg_1", "arg_2"], [["arg_1", "arg_2"]])
        report = asyncio.run(DeepSynthesisAgent.synthesize(agent, state))
        assert "read_license" in report.value_gates
        assert set(report.value_gates["read_license"]) == {
            "grounded",
            "final_synthesis",
        }
        # No LLM service → both texts are empty → nothing to flag, and the
        # check says so rather than pretending it ran over a text.
        assert report.value_gates["read_license"]["grounded"]["flags"] == []

    def test_a_recorded_misreading_is_flagged_through_the_agent(self):
        state = _state_with_cause("between_sources")
        report = DeepSynthesisReport()
        report.grounded_synthesis = (
            "Le discours est incohérent : ses engagements ne tiennent pas."
        )
        DeepSynthesisAgent.attach_read_license(report, state)
        check = report.value_gates["read_license"]["grounded"]
        assert [f["kind"] for f in check["flags"]] == ["discourse_incoherence"]


class TestActTwoReadsTheLicence:
    """R1105c (Opus): the cause is charged to the speaker in Act II.

    The Opus pass read ``between_sources`` — a conflict between source
    units with no speaker recorded — and Act II concluded that the case
    the speaker builds "does not hold together as a coherent whole".
    The check must cover the act narratives, not only the synthesis.
    """

    _CHARGE = (
        "Le cas que Speaker_A construit ne tient pas debout comme un tout "
        "coherent au regard des engagements registres."
    )

    @staticmethod
    def _act2(state, woven: str):
        async def _stub(_prompt: str) -> str:
            return woven

        return asyncio.run(build_act2_narrative(state, llm_callable=_stub))

    def test_an_act_two_sentence_charging_the_speaker_is_flagged(self):
        state = _state_with_cause("between_sources")
        state.add_argument("Une revendication du locuteur.")
        result = self._act2(state, self._CHARGE)
        kinds = [f["kind"] for f in result.read_license["flags"]]
        assert kinds == ["discourse_incoherence"]

    def test_the_same_sentence_under_self_contradiction_is_not_flagged(self):
        # Positive control: a self-contradiction IS the speaker's — the
        # same sentence under that cause is a finding, not a misreading.
        state = _state_with_cause("self_contradiction")
        state.add_argument("Une revendication du locuteur.")
        result = self._act2(state, self._CHARGE)
        assert result.read_license["flags"] == []

    def test_the_detector_covers_the_speaker_attribution_forms(self):
        # The shapes the acts use to charge a cause to the speaker: the
        # case the speaker builds, the demonstration they build, their
        # reasoning, their defence.
        state = _state_with_cause("between_sources")
        sentences = (
            "Le cas que Speaker_A construit ne tient pas debout.",
            "La demonstration qu'il construit ne tient pas.",
            "Le raisonnement de Speaker_A se contredit.",
            "La these que Speaker_A defend se contredit.",
        )
        for sentence in sentences:
            kinds = [f["kind"] for f in check_reading_license(sentence, state)["flags"]]
            assert kinds == ["discourse_incoherence"], sentence
