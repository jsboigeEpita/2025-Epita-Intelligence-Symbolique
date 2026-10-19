"""#3082 — the speaker is ONE record with its provenance, read by Acts I, II and III.

The #3073 split, for the speaker. The speaker has the same two producers the
arena had: ``source_metadata`` (the corpus side — a documented fact) and the
stakes extractor's ``stakeholders`` entries whose ``role`` reads ``speaker``
(an LLM inference about the text). Before this fix the acts read them
inconsistently — Acte I printed the stakeholder line without a naming
contract, Acte II carried neither producer nor rule, Acte III bound naming to
the MÉTADONNÉES block only and, when that block was empty, left the writer
with an instruction (« DIS-LE et n'en nomme aucun ») that reads as a rule to
copy instead of a sentence to write.

The witness sits on the **prompts** the three acts are built from — not on
writer prose, the writer obeys its prompt. Whatever the producers say, the
three prompts must quote the same value with the same provenance tag, from a
single formatter; a documented speaker beats an inferred one; ``unknown``
documents nothing; nothing anywhere → said absent with a sentence the reader
can receive, never invented, and the rule that produces that sentence never
reaches the reader as an instruction.

Mutations that must redden it (both runs rendered in the PR): dropping the
naming rule from Acte II, and restoring Acte III's metadata-only read.

Every assertion is made on the prompt string — the test touches no attribute a
fix introduces, so a reverted production fails on the behaviour, never on an
import. Synthetic opaque values only (no corpus token).
"""

from types import SimpleNamespace

from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
    build_act1_evidence,
    build_act1_prompt,
)
from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_evidence,
    build_act2_prompt,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_evidence,
    build_act3_prompt,
)

_SPEAKER_INFERRED = "Speaker_infere_A"
_SPEAKER_DOCUMENTED = "Speaker_enregistre_B"

# The provenance tag all three acts must share, verbatim, beside the value:
# one record, one wording, by construction (the fix renders every prompt from
# a single formatter — a divergent tag would be a second contract).
_SEGMENT_INFERRED = f"Locuteur : {_SPEAKER_INFERRED} (provenance : INFÉRÉE du texte"
_SEGMENT_DOCUMENTED = (
    f"Locuteur : {_SPEAKER_DOCUMENTED} (provenance : métadonnée enregistrée"
)

# The naming contract every act carries — and the reader-facing sentence its
# absent case hands the writer (the fix's core: the reader receives the
# sentence, never the rule).
_RULE_MARKER = "LE LOCUTEUR SE NOMME UNIQUEMENT D'APRÈS LA LIGNE LOCUTEUR"
_READER_PHRASE = "la source ne documente pas le locuteur"

_STAKEHOLDER_SPEAKER = [
    {"name": _SPEAKER_INFERRED, "role": "speaker", "stance": "pour"}
]


def _state(metadata=None, stakeholders=None):
    state = SimpleNamespace()
    state.source_metadata = dict(metadata or {})
    state.stakes_and_stakeholders = {
        "stakes": [],
        "stakeholders": stakeholders or [],
        "rhetorical_register": "",
        "discursive_arena": "",
    }
    state.deanonymized = True
    return state


def _prompts(state):
    return (
        build_act1_prompt(build_act1_evidence(state)),
        build_act2_prompt(build_act2_evidence(state)),
        build_act3_prompt(build_act3_evidence(state)),
    )


def test_all_three_acts_carry_the_inferred_speaker_with_the_same_provenance_tag():
    """The witness: one inference, three prompts, one value and one tag."""
    p1, p2, p3 = _prompts(_state(stakeholders=_STAKEHOLDER_SPEAKER))
    assert _SPEAKER_INFERRED in p1, "Acte I dropped the stakeholder the state carries"
    assert (
        _SPEAKER_INFERRED in p2
    ), "Acte II read neither producer — the speaker never reaches its prompt"
    assert _SPEAKER_INFERRED in p3, (
        "Acte III read source_metadata only — the inference never reaches it, "
        "so the act cannot name the speaker the other acts quote"
    )
    assert (
        _SEGMENT_INFERRED in p1 and _SEGMENT_INFERRED in p2 and _SEGMENT_INFERRED in p3
    ), "all three acts must quote the same value with the same provenance tag"


def test_the_inferred_line_carries_the_two_voice_caution():
    """#2845 travelling with the record: an inferred orator on a two-voice
    document (a reply) can be the wrong one — the caution is part of the
    line every act quotes, not a footnote one act may drop."""
    p1, p2, p3 = _prompts(_state(stakeholders=_STAKEHOLDER_SPEAKER))
    for p in (p1, p2, p3):
        assert "deux voix" in p, "the #2845 two-voice caution left a prompt"


def test_a_documented_speaker_is_labelled_a_recorded_metadata_fact():
    """Non-vacuity: the documented side keeps its own tag, in all three acts."""
    p1, p2, p3 = _prompts(_state(metadata={"speaker": _SPEAKER_DOCUMENTED}))
    for p in (p1, p2, p3):
        assert _SEGMENT_DOCUMENTED in p, "an act lost the metadata provenance"


def test_the_documented_speaker_wins_over_the_inference():
    """One record: when the corpus documents the speaker, that is the value
    every act quotes — the stakeholder entry does not override it."""
    p1, p2, p3 = _prompts(
        _state(
            metadata={"speaker": _SPEAKER_DOCUMENTED}, stakeholders=_STAKEHOLDER_SPEAKER
        )
    )
    for p in (p1, p2, p3):
        assert _SEGMENT_DOCUMENTED in p
        assert f"Locuteur : {_SPEAKER_INFERRED}" not in p


def test_a_metadata_speaker_reading_unknown_is_not_documentation():
    """The measured shape: the key is present, its value documents nothing —
    the record falls through to the inference rather than quoting
    ``unknown`` as a name."""
    p1, p2, p3 = _prompts(
        _state(metadata={"speaker": "unknown"}, stakeholders=_STAKEHOLDER_SPEAKER)
    )
    for p in (p1, p2, p3):
        assert _SEGMENT_INFERRED in p
        assert "Locuteur : unknown" not in p


def test_an_undocumented_speaker_is_told_absent_with_a_reader_facing_phrase():
    """No producer has anything: every act says so with the same line, and
    the rule hands the writer the exact sentence a reader can receive —
    « la source ne documente pas le locuteur » — instead of an instruction
    the writer may copy to the reader."""
    p1, p2, p3 = _prompts(_state())
    for p in (p1, p2, p3):
        assert "Locuteur :" in p, "an act renders no speaker line at all"
        assert "non documenté" in p, "an act leaves the absence unsaid"
        assert (
            _READER_PHRASE in p
        ), "the absent case must hand the writer the reader-facing sentence"


def test_every_act_carries_the_same_naming_rule():
    """Acte II gets Acte III's rule, and Acte I's « d'après les blocs » no
    longer floats free: the three prompts carry ONE rule, from one constant —
    no act names the speaker outside the record."""
    p1, p2, p3 = _prompts(_state())
    for act, p in (("I", p1), ("II", p2), ("III", p3)):
        assert _RULE_MARKER in p, f"Acte {act} carries no record-based naming rule"


def test_act3_names_from_the_record_not_the_metadata_block():
    """The old clause bound naming to « le bloc MÉTADONNÉES DE LA SOURCE » —
    true only while the record read that block alone. Naming now binds to
    the record's own line, which every producer feeds."""
    p3 = build_act3_prompt(
        build_act3_evidence(_state(stakeholders=_STAKEHOLDER_SPEAKER))
    )
    assert (
        "d'après le bloc MÉTADONNÉES DE LA SOURCE" not in p3
    ), "Acte III still binds the naming to the metadata block alone"
