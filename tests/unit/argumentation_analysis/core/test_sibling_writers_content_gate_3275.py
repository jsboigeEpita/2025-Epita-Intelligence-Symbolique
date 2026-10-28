"""#3275 — the same content gate on the five sibling ``add_*`` writers.

#3268/#3269 gated ``add_argument``: a state field's name is not an argument of
the text. The identical echo reaches five other writers — ``add_task``,
``add_fallacy``, ``add_belief_set``, ``add_extract`` and
``add_counter_argument`` — and nothing downstream distinguishes a name echoed
by a producer from a substantive entry. This module is the born-red witness:
every test here fails on main before the gate and passes after.

Two properties the writers must share, or they drift:

- **One vocabulary source** — the names *this instance* carries (``vars``),
  never a hardcoded list. The mutation witness below is what that costs.
- **Refuse a NAME, not a non-quotation** — a paraphrase stays content; the
  non-vacuity witness pins that.
"""

from __future__ import annotations

import pytest

from argumentation_analysis.core.shared_state import (
    RhetoricalAnalysisState,
    UnifiedAnalysisState,
)

TEXT = "Un texte de mesure, suffisamment long pour être un texte."


def _fresh() -> RhetoricalAnalysisState:
    return RhetoricalAnalysisState(TEXT)


def _fresh_unified() -> UnifiedAnalysisState:
    return UnifiedAnalysisState(TEXT)


# writer name -> (call, container accessor). The call takes a state and the
# content string, so the same witness drives every writer without copying its
# whole signature into the test table.
_WRITERS = {
    "add_task": (
        lambda s, v: s.add_task(v),
        lambda s: s.analysis_tasks,
    ),
    "add_fallacy": (
        lambda s, v: s.add_fallacy("Appel à l'autorité", v),
        lambda s: s.identified_fallacies,
    ),
    "add_belief_set": (
        lambda s, v: s.add_belief_set("propositional", v),
        lambda s: s.belief_sets,
    ),
    "add_extract": (
        lambda s, v: s.add_extract("extrait_1", v),
        lambda s: getattr(s, "extracts", []),
    ),
    "add_counter_argument": (
        lambda s, v: s.add_counter_argument("le texte d'origine", v, "socratic", 0.5),
        lambda s: s.counter_arguments,
    ),
}


class TestEachWriterRefusesAFieldName:
    @pytest.mark.parametrize("writer", sorted(_WRITERS))
    def test_a_field_name_is_refused_and_nothing_is_written(self, writer: str):
        call, container = _WRITERS[writer]
        state = _fresh_unified()
        before = len(container(state))
        with pytest.raises(ValueError) as excinfo:
            call(state, "raw_text")
        assert "#3275" in str(excinfo.value), (
            f"{writer} must cite the issue that extended the gate: {excinfo.value}"
        )
        assert writer in str(excinfo.value), (
            f"the message must name the refusing writer: {excinfo.value}"
        )
        assert len(container(state)) == before, (
            f"{writer} wrote something before refusing"
        )

    @pytest.mark.parametrize("writer", sorted(_WRITERS))
    def test_no_carried_name_survives_the_gate(self, writer: str):
        """Sweep every attribute the instance carries — no name may pass."""
        call, _ = _WRITERS[writer]
        state = _fresh_unified()
        names = sorted(vars(state))
        assert names, "vars(state) must expose the instance fields — #3275 relies on it"
        for name in names:
            with pytest.raises(ValueError):
                call(state, name)


class TestTheBatchRouterInherits:
    def test_add_identified_arguments_refuses_through_add_argument(self):
        """Verified, not assumed: the batch routes through the gated writer."""
        state = _fresh()
        with pytest.raises(ValueError):
            state.add_identified_arguments(["un vrai argument", "raw_text"])
        assert len(state.identified_arguments) == 1, (
            "the first element was written, then the batch hit the gate — "
            "inheritance confirmed"
        )


class TestParaphrasesStillPass:
    @pytest.mark.parametrize("writer", sorted(_WRITERS))
    def test_ordinary_prose_is_accepted(self, writer: str):
        call, container = _WRITERS[writer]
        state = _fresh_unified()
        before = len(container(state))
        call(state, "Le locuteur affirme que la mesure est justifiée.")
        assert len(container(state)) == before + 1


class TestTheVocabularyIsDerivedFromTheInstance:
    """Anti-pendulum: a hardcoded list is the counterfeit fix, and it expires.

    ``act1_framing`` is opened by the Unified subclass, not by the base class:
    accepted on a base instance, refused on a unified one. A constant listing
    names would have to know both instances and would answer the same — which
    is exactly why it is a counterfeit: it cannot follow the next renamed field.
    """

    @pytest.mark.parametrize("writer", sorted(_WRITERS))
    def test_a_subclass_field_is_refused_on_the_subclass_only(self, writer: str):
        # add_counter_argument lives on the unified state only; its "same
        # string on the base" arm is meaningless there, so the base arm is
        # skipped for it and the subclass arm alone carries the proof.
        call, _ = _WRITERS[writer]
        unified = _fresh_unified()
        with pytest.raises(ValueError):
            call(unified, "act1_framing")

        if writer == "add_counter_argument":
            pytest.skip("writer exists on UnifiedAnalysisState only")
        base = _fresh()
        call(base, "act1_framing")  # not a field of the BASE instance
