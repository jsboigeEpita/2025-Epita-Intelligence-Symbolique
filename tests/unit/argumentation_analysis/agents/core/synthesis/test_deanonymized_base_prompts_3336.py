"""#3336 — in deanonymized mode the base prompts stop ordering opaque labels.

#1259 made the ``OPAQUE_ID_DIRECTIVE`` prepend conditional, but two
unconditional copies of the same rule survived **inside the base prompts**,
sent in both modes:

- ``GROUNDED_SYNTHESIS_PROMPT`` rule 5: « Désigne le locuteur et les parties
  par leurs labels opaques (Speaker_A, State_Q) … Jamais de noms réels. »
- ``SYSTEM_PROMPT`` tail: « Use opaque IDs only (Speaker_A, Authority_X,
  era_A) — never real names. »
- the 6-section user line: « Opaque IDs only — recall the opaque-ID discipline
  above applies to every paragraph. » — in deanonymized mode the discipline
  above is NOT prepended, so the line both points at nothing and re-orders
  opaque labels on its own.

The writer obeyed: one report named the speaker with the acts' inferred
identity while its synthesis wrote ``Speaker_A`` (19 of 29 paid renders on
the coordinator seat). The fix swaps each opaque order for the acts' own
designation — the LIGNE LOCUTEUR, wired from ``speaker_record`` with its
provenance, never writer-guessed.

Opaque mode (``deanonymized=False``) keeps every byte of its prompts: the
positive controls below pin that.

Every fixture is synthetic (invented identity, opaque ids). Deterministic —
no JVM, no LLM, no network.
"""

from __future__ import annotations

from types import SimpleNamespace

from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
    DeepSynthesisAgent,
    DeepSynthesisReport,
    _six_section_naming_line,
)
from argumentation_analysis.reporting.restitution.speaker_record import (
    format_speaker_line,
    build_speaker_record,
)


def _state(**fields) -> SimpleNamespace:
    base = dict(
        identified_arguments={"arg_1": "claim alpha asserted early"},
        identified_fallacies={},
        counter_arguments=[],
        argument_quality_scores={},
        propositional_analysis_results=[],
        fol_analysis_results=[],
        modal_analysis_results=[],
        dung_frameworks={},
        jtms_retraction_chain=[],
        belief_revision_results=[],
        source_metadata={},
        stakes_and_stakeholders={
            "stakeholders": [
                {"role": "speaker", "name": "Une Identité Inventée Pour Le Test"}
            ]
        },
    )
    base.update(fields)
    return SimpleNamespace(**base)


# ============================================================================
# The grounded base prompt — rule 5 follows the mode
# ============================================================================


class TestGroundedPrompt:
    def test_deanonymized_orders_no_opaque_label(self):
        prompt = DeepSynthesisAgent.grounded_synthesis_prompt(deanonymized=True)
        assert "Speaker_A" not in prompt, (
            "the deanonymized base prompt still orders the opaque label"
        )
        assert "labels opaques" not in prompt

    def test_deanonymized_names_from_the_speaker_line(self):
        prompt = DeepSynthesisAgent.grounded_synthesis_prompt(deanonymized=True)
        assert "LIGNE LOCUTEUR" in prompt
        # the machine-key discipline survives the swap (it is mode-independent)
        assert "jamais par sa clé machine" in prompt

    def test_opaque_mode_is_byte_for_byte_the_classvar(self):
        """Positive control: opaque mode keeps its order, unchanged."""
        prompt = DeepSynthesisAgent.grounded_synthesis_prompt(deanonymized=False)
        assert prompt == DeepSynthesisAgent.GROUNDED_SYNTHESIS_PROMPT
        assert "Speaker_A" in prompt
        assert "Jamais de noms réels" in prompt


# ============================================================================
# The 6-section system prompt — the tail follows the mode
# ============================================================================


class TestSystemPromptTail:
    def test_deanonymized_orders_no_opaque_label(self):
        prompt = DeepSynthesisAgent.system_prompt_for(deanonymized=True)
        assert "Speaker_A" not in prompt
        assert "opaque IDs only" not in prompt

    def test_deanonymized_designates_from_the_speaker_line(self):
        prompt = DeepSynthesisAgent.system_prompt_for(deanonymized=True)
        assert "SPEAKER LINE" in prompt

    def test_opaque_mode_is_byte_for_byte_the_1259_form(self):
        """Positive control: the #1259 assembly, unchanged."""
        prompt = DeepSynthesisAgent.system_prompt_for(deanonymized=False)
        assert prompt == (
            DeepSynthesisAgent.OPAQUE_ID_DIRECTIVE
            + DeepSynthesisAgent.SYSTEM_PROMPT
        )


# ============================================================================
# The 6-section user line — no order that points at a discipline not sent
# ============================================================================


class TestSixSectionNamingLine:
    def test_opaque_line_is_unchanged(self):
        assert _six_section_naming_line(deanonymized=False) == (
            "Opaque IDs only — recall the opaque-ID discipline above applies "
            "to every paragraph.\n"
        )

    def test_deanonymized_line_orders_the_speaker_line_not_opaque(self):
        line = _six_section_naming_line(deanonymized=True)
        assert "Opaque IDs only" not in line
        assert "SPEAKER LINE" in line


# ============================================================================
# The briefing — the designation is wired, never guessed
# ============================================================================


class TestTheBriefingCarriesTheActsDesignation:
    def test_deanonymized_briefing_carries_the_speaker_line(self):
        """The writer receives the acts' own line — same value, same
        provenance tag, from the single formatter the acts read."""
        state = _state()
        briefing = DeepSynthesisAgent.build_artifact_briefing(
            state, deanonymized=True
        )
        assert format_speaker_line(build_speaker_record(state)) in briefing

    def test_default_briefing_is_unchanged(self):
        """Positive control: every existing caller (no flag) keeps its
        briefing byte-for-byte — the line is added only when asked for."""
        state = _state()
        default = DeepSynthesisAgent.build_artifact_briefing(state)
        explicit = DeepSynthesisAgent.build_artifact_briefing(
            state, deanonymized=False
        )
        assert default == explicit
        assert "LIGNE LOCUTEUR" not in default


# ============================================================================
# The 6-section user prompt — the SPEAKER LINE reaches the writer
# ============================================================================


class TestTheSixSectionPromptCarriesTheSpeakerLine:
    @staticmethod
    def _captured_prompt(deanonymized: bool) -> str:
        import asyncio
        from unittest.mock import AsyncMock, MagicMock, create_autospec

        from semantic_kernel import Kernel

        kernel = create_autospec(Kernel, instance=True)
        kernel.get_prompt_execution_settings_from_service_id = MagicMock(
            return_value=MagicMock()
        )
        invoke_capture = AsyncMock(return_value="## 1. C\n## 6. L")
        kernel.invoke_prompt = invoke_capture

        stub = SimpleNamespace(
            _llm_service_id="default",
            kernel=kernel,
            _deanonymized=deanonymized,
        )
        report = DeepSynthesisReport()
        report.source_overview = SimpleNamespace(
            speaker="", topic="", venue="", date_or_year="", era="",
            register="", synopsis="", language="", length_words=0,
            contextual_frame="invented frame",
        )
        report._raw_stakes = {}
        report._speaker_record = build_speaker_record(_state())
        asyncio.new_event_loop().run_until_complete(
            DeepSynthesisAgent._llm_synthesis(stub, report)
        )
        return invoke_capture.call_args[1]["prompt"]

    def test_deanonymized_prompt_carries_the_acts_line_and_no_opaque_order(self):
        prompt = self._captured_prompt(deanonymized=True)
        assert "[SPEAKER LINE" in prompt
        assert format_speaker_line(build_speaker_record(_state())) in prompt
        assert "Opaque IDs only" not in prompt

    def test_opaque_prompt_keeps_its_line_and_carries_no_speaker_line(self):
        prompt = self._captured_prompt(deanonymized=False)
        assert "Opaque IDs only" in prompt
        assert "[SPEAKER LINE" not in prompt
