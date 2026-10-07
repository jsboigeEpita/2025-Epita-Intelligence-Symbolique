"""#2980 — a rendered act printed a raw unit id, and the gate passed it.

The no-raw-id rule (FB-34, #1118; #2896 (d) for the thread) was enforced on
the **input** only: a prompt instruction, and ids kept out of the sequence
block. A measured sample (07/10, real writer, saved state) printed
« l'argument arg_6 » into the prose and ``ReadabilityGate`` said PASS —
nothing checked the OUTPUT. The movement blocks hand the writer
``• arg_N : <text>`` by design (the join), so the writer is one slip away
from echoing it, and #2977's letter legend makes « l'argument <label> » a
frequent construction.

The gate now flags internal-id tokens by CLASS — the opaque prefixes the
state mints — on word boundaries: ``abs_arg_dung`` is not an id (no ``\b``
fires inside a ``_``-joined token, and its tail is not a digit), and Greek
thread letters are the designed label. The band is not PASS, the motif is
recorded in ``restitution_acts_degraded`` through the existing plumbing,
and the writer's prose is NEVER rewritten — the gate reports.

Privacy: invented filler, opaque ids. Deterministic: no JVM, no LLM.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_narrative,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_conclusion,
)
from argumentation_analysis.reporting.restitution.acts import RestitutionActs
from argumentation_analysis.reporting.restitution.readability_gate import (
    ReadabilityGate,
)

# The measured shape: model prose around a raw unit id.
_BODY_WITH_ID = (
    "Le discours avance masqué : l'argument arg_6, lorsqu'une réponse "
    "directe aurait suffi, détourne l'examen vers la personne."
)

# The designed label and the appendix vocabulary — both must stay PASS.
_BODY_CLEAN = (
    "Le fil s'ouvre sur l'argument α, celui que la gouvernance désigne, "
    "et le lecteur retrouve la preuve repliée sous abs_arg_dung en annexe."
)


def _stub_llm(return_value: str) -> object:
    async def _call(_prompt: str) -> str:
        return return_value

    return _call


def _min_state() -> SimpleNamespace:
    return SimpleNamespace(
        identified_arguments={"arg_1": "Une revendication formulée simplement."},
        identified_fallacies={},
        argument_quality_scores={},
        counter_arguments=[],
        dung_frameworks={},
        fol_analysis_results=[],
        propositional_analysis_results=[],
        modal_analysis_results=[],
        narrative_synthesis="",
        governance_decisions=[],
        debate_transcripts=[],
    )


class TestTheBodyCheckFlagsIdClasses:
    def test_the_measured_body_is_not_pass_anymore(self) -> None:
        """On main this body passed; after the fix the band is not PASS and
        the reason names the token CLASS (arg_N), not the referent."""
        verdict = ReadabilityGate().check_body(_BODY_WITH_ID)
        assert verdict.band != "PASS"
        assert "arg_N" in " ".join(verdict.reasons)
        # the motif never names the referent's content — the class + the
        # opaque token only
        assert "revendication" not in " ".join(verdict.reasons)

    def test_positive_control_letters_and_appendix_vocabulary_stay_pass(self) -> None:
        """« l'argument α » is the designed label and ``abs_arg_dung`` is
        appendix vocabulary, not a state id — this body stays PASS."""
        verdict = ReadabilityGate().check_body(_BODY_CLEAN)
        assert verdict.band == "PASS"

    def test_three_ids_fail_the_band(self) -> None:
        """A jargon takeover (≥3 printed ids) fails like a manifest
        enumeration — WARN at 1–2, FAIL at 3 (the #2031 thresholds)."""
        body = (
            "Le fil relie arg_6 puis arg_7, avant que fallacy_1 ne s'y "
            "ajoute — trois ids que le lecteur ne peut résoudre."
        )
        verdict = ReadabilityGate().check_body(body)
        assert verdict.band == "FAIL"

    def test_a_partial_id_inside_a_longer_word_is_not_a_printed_id(self) -> None:
        """The boundary's actual job (measured): a token that merely
        CONTAINS an id shape — ``subarg_1``, ``arg_1x``, ``my_arg_2bis`` —
        is not an id printed to the reader. The digit tail is what excludes
        ``abs_arg_dung``; the ``\\b`` pair is what excludes these."""
        for word in ("subarg_1", "arg_1x", "my_arg_2bis"):
            verdict = ReadabilityGate().check_body(f"Le lecteur suit {word} ici.")
            assert verdict.band == "PASS", (word, verdict.reasons)


class TestThePerActCheckNamesTheAct:
    def test_the_reason_names_which_act_printed_the_id(self) -> None:
        acts = RestitutionActs(
            act1_framing="Le cadre du débat, sans id.",
            act2_narrative=_BODY_WITH_ID,
            act3_conclusion="La conclusion, sans id.",
        )
        verdict = ReadabilityGate().check_acts(acts)
        assert verdict.band != "PASS"
        assert any("Acte II" in r and "arg_N" in r for r in verdict.reasons)


class TestTheActsSelfCheckCarriesTheMotive:
    def test_act2_result_degraded_carries_the_motive(self) -> None:
        """The measured defect's channel: the act's own self-control
        (check_body) lands the motif in ``degraded``, which the writer path
        persists into ``restitution_acts_degraded``."""
        out = asyncio.get_event_loop().run_until_complete(
            build_act2_narrative(
                _min_state(), llm_callable=_stub_llm(_BODY_WITH_ID)  # type: ignore[arg-type]
            )
        )
        assert out.status == "woven"
        motif = " ".join(out.degraded.values())
        assert "arg_N" in motif
        assert "#2980" in motif

    def test_act3_result_degraded_carries_the_motive(self) -> None:
        out = asyncio.get_event_loop().run_until_complete(
            build_act3_conclusion(
                _min_state(), llm_callable=_stub_llm(_BODY_WITH_ID)  # type: ignore[arg-type]
            )
        )
        assert out.status == "woven"
        motif = " ".join(out.degraded.values())
        assert "arg_N" in motif
        assert "#2980" in motif

    def test_the_prose_is_reported_never_rewritten(self) -> None:
        """No silent repair: the narrative is returned exactly as the
        writer produced it — the gate reports, it does not edit."""
        out = asyncio.get_event_loop().run_until_complete(
            build_act2_narrative(
                _min_state(), llm_callable=_stub_llm(_BODY_WITH_ID)  # type: ignore[arg-type]
            )
        )
        assert out.narrative == _BODY_WITH_ID
