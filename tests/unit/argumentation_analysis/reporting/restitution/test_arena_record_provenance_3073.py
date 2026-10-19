"""#3073 — the discursive arena is ONE record with its provenance, read by Acts I and III.

On the paid one-document pass of 19/10 the render contradicted itself on the
arena: Acte I said it **is verified** and named it, Acte III said the source
documents **neither the speaker nor the arena type**. One fact, two containers:
``source_metadata`` (the corpus side — a documented fact, no arena key on that
document) and ``stakes_and_stakeholders.discursive_arena`` (the stakes
extractor's reading of the text — an LLM inference). Acte I printed the
inference under a block headed ``DONNÉES VERIFIÉES DANS LE STATE`` (the writer
then repeated "verified", as instructed); Acte III read metadata only, so the
inference never reached it.

The witness sits on the **prompts** the two acts are built from — not on writer
prose, the writer obeys its prompt. A state whose metadata records no arena and
whose ``discursive_arena`` is non-empty must put the same value, with the same
provenance tag, into both prompts; a documented arena must carry its metadata
provenance; an absent one must be said absent, never invented.

Mutations that must redden it (both runs rendered in the PR): restoring Acte I's
``DONNÉES VERIFIÉES`` heading, and Acte III's metadata-only read.

Every assertion is made on the prompt string — the test touches no attribute a
fix introduces, so a reverted production fails on the behaviour, never on an
import. Synthetic opaque values only (no corpus token).
"""

from types import SimpleNamespace

from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
    build_act1_evidence,
    build_act1_prompt,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_evidence,
    build_act3_prompt,
)

_ARENA_INFERRED = "arena_deliberative_A"
_ARENA_DOCUMENTED = "arena_institutionnelle_B"

# The provenance tag both acts must share, verbatim, beside the value: one
# record, one wording, by construction (the fix renders both prompts from a
# single formatter — a divergent tag would be a second contract).
_SEGMENT_INFERRED = (
    f"Arène discursive : {_ARENA_INFERRED} (provenance : INFÉRÉE du texte"
)
_SEGMENT_DOCUMENTED = (
    f"Arène discursive : {_ARENA_DOCUMENTED} (provenance : métadonnée enregistrée"
)


def _state(metadata=None, arena=None, register=""):
    state = SimpleNamespace()
    state.source_metadata = dict(metadata or {})
    state.stakes_and_stakeholders = {
        "stakes": [],
        "stakeholders": [],
        "rhetorical_register": register,
        "discursive_arena": arena or "",
    }
    state.deanonymized = True
    return state


def _prompts(state):
    return (
        build_act1_prompt(build_act1_evidence(state)),
        build_act3_prompt(build_act3_evidence(state)),
    )


def test_both_acts_carry_the_inferred_arena_with_the_same_provenance_tag():
    """The witness: one inference, two prompts, one value and one tag."""
    p1, p3 = _prompts(_state(arena=_ARENA_INFERRED))
    assert _ARENA_INFERRED in p1, "Acte I dropped the arena the state carries"
    assert _ARENA_INFERRED in p3, (
        "Acte III reads source_metadata only — the inference never reaches it, "
        "so the act tells the reader the arena is undocumented while Acte I "
        "prints it"
    )
    assert (
        _SEGMENT_INFERRED in p1 and _SEGMENT_INFERRED in p3
    ), "both acts must quote the same value with the same provenance tag"


def test_no_inferred_field_sits_under_a_verified_heading():
    """Stakes, register and arena are inferences — the heading must not say otherwise."""
    p1, _ = _prompts(_state(arena=_ARENA_INFERRED))
    assert (
        "DONNÉES VERIFIÉES DANS LE STATE" not in p1
    ), "the block heading still promotes the whole bundle to 'verified'"
    assert "DONNÉES DU STATE" in p1, "the provenance-labelled heading"


def test_a_documented_arena_is_labelled_a_recorded_metadata_fact():
    """Non-vacuity: the documented side keeps its own tag, in both acts."""
    p1, p3 = _prompts(_state(metadata={"venue": _ARENA_DOCUMENTED}))
    assert _SEGMENT_DOCUMENTED in p1, "Acte I lost the metadata provenance"
    assert _SEGMENT_DOCUMENTED in p3, "Acte III lost the metadata provenance"


def test_the_documented_arena_wins_over_the_inference():
    """One record: when the corpus documents the arena, that is the value both acts quote."""
    p1, p3 = _prompts(
        _state(metadata={"venue": _ARENA_DOCUMENTED}, arena=_ARENA_INFERRED)
    )
    assert _SEGMENT_DOCUMENTED in p1 and _SEGMENT_DOCUMENTED in p3
    assert f"Arène discursive : {_ARENA_INFERRED}" not in p1
    assert f"Arène discursive : {_ARENA_INFERRED}" not in p3


def test_a_metadata_arena_reading_unknown_is_not_documentation():
    """doc_A's own shape: the key is present, its value documents nothing."""
    p1, p3 = _prompts(_state(metadata={"venue": "unknown"}, arena=_ARENA_INFERRED))
    assert _SEGMENT_INFERRED in p1 and _SEGMENT_INFERRED in p3


def test_an_undocumented_arena_is_told_absent_not_invented():
    """No producer has anything: both acts say so, neither invents one."""
    p1, p3 = _prompts(_state())
    assert "Arène discursive :" in p1 and "Arène discursive :" in p3
    assert "non renseignée" in p1 and "non renseignée" in p3
