"""#1620 — the appendix's "synthèse narrative" signal must not favour one voie.

The two orchestration voies file the *same* semantic object under two different
state keys:

* **pipeline** — ``state_writers`` (l.1266 / l.1305) write the narrative
  synthesis into ``state.narrative_synthesis``.
* **conversational** — the PM prompt (``pm/prompts.py`` l.95) instructs the
  agent to call ``StateManager.set_final_conclusion(conclusion="[Copie de votre
  synthèse ici]")``, which lands in ``state.final_conclusion``
  (``shared_state.py`` l.224).

``_provenance_counts`` read only the first key, so a conversational run that
*did* synthesise was reported ``synthese_narrative = "absente"``. That is the
one-lane-writer bias: the quieter report reads as the healthier one, which
skews any pipeline-vs-conversational comparison in favour of the louder voie.

**Two hops, two ways to be inert.** The reader does not receive the state — it
receives ``state_adapter.state_to_appendix_mapping(state)``, a projection onto
``_STATE_KEYS``. A resolver that reads a key the projection drops is green in a
unit test built on a raw dict and dead in production. That happened here: the
first cut of this fix touched only the reader, and a probe on the real
``render_spectacular_restitution`` path still printed
``| synthese_narrative | absente |`` for a state carrying a synthesis (found in
review by po-2023). The tests below therefore pin *each hop separately* plus the
composed path, so no single edit can make the chain silently inert again:

===========================  ======================================  ==========
test class                   what it would catch                     hop
===========================  ======================================  ==========
``TestReaderResolvesBoth``   reader stops resolving the second key   reader
``TestProjectionCarries``    projection stops carrying the key       projection
``TestProdPathAgrees``       either hop breaks                       composed
``TestRenderedReport``       either hop breaks, at the surface        end-to-end
===========================  ======================================  ==========

Degenerate substitutions (all run, none reasoned):

* delete ``or _g("final_conclusion")`` in ``_provenance_counts`` → the reader,
  prod-path and rendered tests fail; the projection test **survives**.
* delete ``"final_conclusion"`` from ``_STATE_KEYS`` → the projection, prod-path
  and rendered tests fail; the reader test **survives**.

Neither substitution kills everything, so neither hop's guard is redundant.

Scope: this is a *reader-side* resolver fed by a widened projection. The two
state fields keep their own names and histories and are deliberately NOT merged
— aliasing one onto the other would misattribute its text in the opt-in
full-state dump, which renders mapped content verbatim.
"""

from __future__ import annotations

import pytest

from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    Act3Evidence,
)
from argumentation_analysis.reporting.restitution.appendix import _provenance_counts
from argumentation_analysis.reporting.restitution.pipeline_adapter import (
    render_spectacular_restitution,
)
from argumentation_analysis.reporting.restitution.state_adapter import (
    state_to_appendix_mapping,
)

# The synthesis text is identical on both voies — the voie is the only variable.
_SYNTHESIS = "Le discours articule trois mouvements argumentatifs distincts."


def _state(**overrides):
    """Minimal state; only the synthesis-carrying keys vary between cases."""
    base = {
        "identified_arguments": {"arg_1": "thèse A"},
        "identified_fallacies": {},
        "counter_arguments": [],
        "argument_quality_scores": {},
        "narrative_synthesis": "",
        "final_conclusion": None,
    }
    base.update(overrides)
    return base


def _prod_counts(**overrides):
    """Counts as production computes them: through the projection, not around it."""
    return _provenance_counts(state_to_appendix_mapping(_state(**overrides)))


class TestReaderResolvesBoth:
    """Hop 1 — the reader itself, handed both keys directly."""

    def test_reader_accepts_either_key(self) -> None:
        assert (
            _provenance_counts({"narrative_synthesis": _SYNTHESIS})[
                "synthese_narrative"
            ]
            == "présente"
        )
        assert (
            _provenance_counts({"final_conclusion": _SYNTHESIS})["synthese_narrative"]
            == "présente"
        )


class TestProjectionCarries:
    """Hop 2 — the projection must not drop what the reader resolves.

    This is the guard whose absence made the first cut of the fix inert: the
    reader was correct and never saw the key.
    """

    def test_projection_carries_both_synthesis_keys(self) -> None:
        mapping = state_to_appendix_mapping(_state(final_conclusion=_SYNTHESIS))
        assert "final_conclusion" in mapping, (
            "the appendix reader receives this projection, not the state — "
            "a key dropped here is invisible downstream whatever the reader does"
        )

    def test_projection_omits_absent_keys(self) -> None:
        """Anti-pendule: widening the projection must not fabricate entries."""
        assert "final_conclusion" not in state_to_appendix_mapping(_state())


class TestProdPathAgrees:
    """Composed — same content in ⇒ same signal out, whichever voie wrote it."""

    def test_both_voies_agree_when_each_wrote_its_own_key(self) -> None:
        """The load-bearing assertion: agreement, not a particular wording."""
        pipeline = _prod_counts(narrative_synthesis=_SYNTHESIS)
        conversational = _prod_counts(final_conclusion=_SYNTHESIS)

        assert (
            pipeline["synthese_narrative"] == conversational["synthese_narrative"]
        ), "the two voies must report the same synthesis presence for the same content"
        assert pipeline["synthese_narrative"] == "présente"

    def test_conversational_synthesis_is_not_reported_absent(self) -> None:
        """The concrete regression, measured where production measures it."""
        assert _prod_counts(final_conclusion=_SYNTHESIS)["synthese_narrative"] == (
            "présente"
        )

    def test_neither_voie_wrote_anything_stays_absent(self) -> None:
        """Anti-pendule: the resolver must not fabricate presence from nothing."""
        assert _prod_counts()["synthese_narrative"] == "absente"

    def test_empty_conversational_conclusion_stays_absent(self) -> None:
        """An empty/whitespace conclusion is not a synthesis (falsy, like the twin)."""
        assert _prod_counts(final_conclusion="")["synthese_narrative"] == "absente"


class TestRenderedReport:
    """End-to-end — the row a reader actually sees in the rendered appendix."""

    class _ConvState:
        """A conversational run: the PM copied its synthèse into final_conclusion."""

        act1_framing = "Cadrage."
        act2_investigation = "Investigation."
        act3_conclusion = "Conclusion."
        final_conclusion = _SYNTHESIS
        identified_arguments = {"arg_1": "thèse A"}

    def test_conversational_run_renders_synthesis_as_present(self) -> None:
        markdown = render_spectacular_restitution(
            self._ConvState(), source_id="doc_A"
        ).markdown
        assert "| synthese_narrative | présente |" in markdown, (
            "a conversational run that synthesised must not be rendered 'absente' — "
            "this is the surface the one-lane bias reached"
        )


class TestAct3DroppedTheUnreadFlag:
    """#1620 defect 1 — the flag is gone by subtraction, not relocated.

    ``Act3Evidence.narrative_synthesis_available`` was computed from
    ``state.narrative_synthesis`` and passed into the bundle, and no code ever
    read it (3 sites, all declaration/computation/construction). Measured on
    three real artifacts, the Acte III prose asserts nothing about a narrative
    synthesis even where the state carries a 5053-char one — so the flag
    guarded no claim.

    This test pins the *rule*, not the instance: a boolean on the evidence
    bundle exists to gate prose, so re-adding this one silently would restore
    the defect. Re-adding it **with a reader** is a different change and would
    come with its own test.
    """

    def test_flag_is_absent_from_the_evidence_bundle(self) -> None:
        assert not hasattr(Act3Evidence(), "narrative_synthesis_available")

    def test_evidence_builder_does_not_reintroduce_it(self) -> None:
        """Constructing the bundle must not accept the removed keyword."""
        with pytest.raises(TypeError):
            Act3Evidence(narrative_synthesis_available=True)
