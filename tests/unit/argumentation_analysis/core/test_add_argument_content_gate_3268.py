"""#3268 — a state field's name is not an argument of the text.

``SharedState.add_argument`` accepted any string. A producer that wrote what
it read of its own structure recorded a ghost argument: ``identified_arguments``
grew, and the growth guard counted it as progress (``_get_growth_fingerprint``
takes ``len()``), so a degenerate run validated itself. The only non-vacuity
check in the tree was a count in one test
(``tests/integration/test_growth_hook_corpus_a_597.py:57``).

Measured before the gate: 829 literals reached a method named ``add_argument``
across the tree (state writes and argparse alike — deliberately over-inclusive),
and **0** collided with the instance's attributes. The repair touches no
existing caller.

The refused vocabulary is derived from the instance (``vars(self)``), never
from a constant: a hardcoded blacklist is a pendulum — it fights the symptom
and expires at the first renamed field. The paraphrase witness below holds the
other edge: the gate must not become a requirement that the description appear
verbatim in the source text.
"""

import pytest

from argumentation_analysis.core.shared_state import (
    RhetoricalAnalysisState,
    UnifiedAnalysisState,
)

SOURCE_TEXT = (
    "La transition energetique exige des investissements massifs dans le "
    "reseau electrique, sans quoi les objectifs ne seront pas tenus."
)

# A plain reading of SOURCE_TEXT — deliberately a paraphrase, so it is NOT a
# substring of the source text.
PARAPHRASE = "Le reseau electrique doit etre massivement finance pour tenir les objectifs."


@pytest.fixture
def state() -> RhetoricalAnalysisState:
    return RhetoricalAnalysisState(initial_text=SOURCE_TEXT)


def test_a_state_field_name_is_refused(state) -> None:
    """The defect itself: ``"analysis_state"``-shaped writes used to land."""
    before = dict(state.identified_arguments)

    with pytest.raises(ValueError) as excinfo:
        state.add_argument("raw_text")

    assert "raw_text" in str(excinfo.value)
    assert "#3268" in str(excinfo.value)
    # Nothing was recorded — the refusal is total, not a partial write.
    assert state.identified_arguments == before


def test_every_carried_name_is_refused_not_only_a_sample(state) -> None:
    """The gate reads the instance, so it covers names nobody enumerated."""
    with pytest.raises(ValueError):
        state.add_argument("identified_fallacies")
    with pytest.raises(ValueError):
        # An attribute the class body never declares, opened in __init__.
        state.add_argument("reading_window_status")


def test_the_vocabulary_is_derived_from_the_instance_not_a_blacklist() -> None:
    """A name carried only by the richer state is refused there, accepted here.

    This is the anti-pendulum witness: a hardcoded list would answer the same
    way for both states, which is exactly the drift the repair must not have.
    """
    base = RhetoricalAnalysisState(initial_text=SOURCE_TEXT)
    rich = UnifiedAnalysisState(initial_text=SOURCE_TEXT)

    assert "act1_framing" not in vars(base)
    assert "act1_framing" in vars(rich)

    # Accepted on the state that does not carry the name...
    assert base.add_argument("act1_framing")
    # ...refused on the one that does.
    with pytest.raises(ValueError):
        rich.add_argument("act1_framing")


def test_a_paraphrase_is_still_an_argument(state) -> None:
    """Non-regression: the gate rejects field names, not non-quotations."""
    assert PARAPHRASE not in SOURCE_TEXT
    arg_id = state.add_argument(PARAPHRASE, producer="llm_extract")
    assert arg_id
    assert state.identified_arguments[arg_id] == PARAPHRASE


def test_an_ordinary_argument_is_unchanged(state) -> None:
    """The nominal path keeps its contract: an id, a description, a provenance."""
    arg_id = state.add_argument(
        "Il faut investir massivement dans le reseau electrique.",
        producer="llm_extract",
        source_quote="investissements massifs dans le reseau electrique",
        move_author="speaker",
    )
    assert arg_id.startswith("arg_")
    assert state.argument_provenance[arg_id]["producer"] == "llm_extract"
    assert state.argument_provenance[arg_id]["move_author"] == "speaker"
