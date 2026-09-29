"""#2845: Acte III names the speaker the run recorded — never one it harvested.

The conclusion's own prompt has always carried the instruction « nomme le
locuteur et l'arène (via les métadonnées) », while the evidence bundle Acte III
is built from carried no metadata at all: the instruction was unsatisfiable on
every run. Measured on a campaign state dump (the prompt rebuilt from the
stored state, deterministic, no LLM): neither the recorded venue nor the
recorded speaker appeared anywhere as a field — the label reached the prompt
only as prose inside Acte I's interpretive question, one line above a claims
block whose only person is the INTERLOCUTOR the speaker answers. The rendered
Act credited the thesis to that interlocutor, where Acte I — which does carry
the metadata block — named the source as recorded.

The guard is the wiring, not a wording: a state whose ``source_metadata``
records a speaker must put that speaker into the prompt, a state that records
none must say so rather than leave the writer to invent one, and the writer
must be told that a person cited in the extracts is an interlocutor. Every
assertion is made on the prompt string — the test touches no attribute that
this fix introduces, so reverted production fails on the behaviour, never on
an import.

Synthetic values only (no corpus token).
"""

from types import SimpleNamespace

from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_evidence,
    build_act3_prompt,
)

_SPEAKER = "Speaker_A"
_ARENA = "Arena_X"


def _prompt(metadata=None, deanonymized=True):
    state = SimpleNamespace()
    state.source_metadata = dict(metadata or {})
    state.deanonymized = deanonymized
    return build_act3_prompt(build_act3_evidence(state))


def test_the_recorded_speaker_reaches_the_prompt():
    """The witness (#2845): the metadata the instruction points at are there."""
    prompt = _prompt({"speaker": _SPEAKER, "venue": _ARENA})
    assert _SPEAKER in prompt, "the recorded speaker never reaches the writer"
    assert _ARENA in prompt, "the recorded arena never reaches the writer"


def test_a_state_recording_no_speaker_says_so():
    """No metadata must not read as an invitation to name one."""
    prompt = _prompt({})
    assert "MÉTADONNÉES DE LA SOURCE" in prompt
    assert (
        "aucune métadonnée renseignée" in prompt
    ), "an empty ledger left the naming instruction unsatisfied and silent"


def test_a_recorded_speaker_is_not_reported_as_absent():
    """Non-vacuity of the test above: a documented run reads as documented."""
    prompt = _prompt({"speaker": _SPEAKER})
    assert "aucune métadonnée renseignée" not in prompt


def test_the_writer_is_told_an_extract_name_is_an_interlocutor():
    """The prompt's claims block is where the wrong orator was harvested."""
    prompt = _prompt({"speaker": _SPEAKER})
    assert "INTERLOCUTEUR" in prompt, (
        "a person cited in the extracts is the one the speaker answers; "
        "nothing tells the writer so"
    )


def test_the_recorded_metadata_is_capped():
    """Privacy/contract: the block truncates like every other corpus field."""
    prompt = _prompt({"speaker": "S" * 500})
    assert "S" * 500 not in prompt
    assert "S" * 160 in prompt


def test_the_opaque_regime_keeps_its_directive():
    """Control: the block sits beside the FB-34 discipline, it does not replace it."""
    opaque = _prompt({"speaker": _SPEAKER}, deanonymized=False)
    assert "DISCIPLINE D'IDENTIFIANTS OPAQUES" in opaque
    assert _SPEAKER in opaque
