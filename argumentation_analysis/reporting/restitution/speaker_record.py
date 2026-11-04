"""#3082 — the speaker as ONE record with its provenance, shared by Acts I, II and III.

The #3073 split, for the speaker. The speaker has the same two producers the
arena had: ``state.source_metadata`` (the corpus side — the run recorded it,
so it is a documented fact) and the stakes extractor's ``stakeholders``
entries whose ``role`` reads ``speaker`` (a reading of the text — an LLM
inference). Before this module the acts read them inconsistently: Acte I
printed the stakeholder line with no naming contract, Acte II carried neither
producer nor rule, Acte III bound naming to the MÉTADONNÉES block alone — and
when that block was empty, its instruction (« DIS-LE et n'en nomme aucun »)
read as a rule to copy, so the render could hand the reader the instruction
itself instead of a sentence.

This module resolves the two producers into a single record and renders the
one line every act quotes, so the three agree **by construction**: same
value, same provenance tag, from a single formatter. A documented speaker
beats an inferred one; a speaker recorded as ``unknown`` documents nothing;
nothing anywhere → said absent, with the sentence the reader receives — never
invented, and never the rule that produces the sentence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .arena_record import (
    PROVENANCE_INFERRED,
    PROVENANCE_METADATA,
    _NOT_DOCUMENTED,
    _cap,
    _documents,
)

# The metadata keys that document a speaker. ``speaker`` is the political
# vocabulary's own field — ``stakes_extractor`` reads
# ``source_metadata.get("speaker", "unknown")`` and the #2845 witness builds
# its recorded-speaker states from ``speaker``; ``orateur``/``locuteur`` are
# the French spellings a corpus may carry.
_SPEAKER_METADATA_KEYS = ("speaker", "orateur", "locuteur")

# The stakeholder roles that make an entry a speaker reading of the text
# (``stakes_extractor``'s own vocabulary is speaker/opponent/audience/
# authority/institution/group — everything else is another party).
_SPEAKER_ROLES = frozenset({"speaker", "locuteur", "orateur", "narrator"})

# #3390 — the roles that make a stakeholder a SECOND VOICE for the #2845
# caution: someone who SPEAKS in the document (the opponent the speaker
# answers, another narrator). ``audience`` is deliberately absent: an
# interjection from the public is not the document's second voice, and the
# measured panel document (one speaker, heckler lines) drew the caution
# twice on an attribution that was correct — the doubt must name a real
# second speaker or stay silent.
_SECOND_VOICE_ROLES = frozenset(
    {"speaker", "locuteur", "orateur", "narrator", "opponent", "interlocuteur"}
)

# #2845, travelling with the record: on a two-voice document (a reply), the
# only person the text names can be the interlocutor the speaker answers —
# an inferred orator can be the wrong one, and the reader must be told so
# wherever the inference is quoted.
_TWO_VOICE_CAUTION = (
    "prudence #2845 : sur un document à deux voix, l'orateur inféré peut "
    "être le mauvais"
)

_LABEL_METADATA = "métadonnée enregistrée"
_LABEL_INFERRED = "INFÉRÉE du texte par l'extracteur d'enjeux"

# The naming contract every act carries, from this one constant — no act
# names the speaker outside the record. Its absent case hands the writer the
# exact sentence a reader can receive; the rule that produces the sentence
# never reaches the reader as an instruction.
SPEAKER_NAMING_RULE = (
    "- LE LOCUTEUR SE NOMME UNIQUEMENT D'APRÈS LA LIGNE LOCUTEUR ci-dessus :\n"
    "  « métadonnée enregistrée » → nomme-le comme un fait enregistré ;\n"
    "  « INFÉRÉE du texte » → nomme-le en disant l'inférence (« le texte\n"
    "  présente le locuteur comme … », avec la prudence deux-voix de la\n"
    "  ligne) ; « non documenté » → n'invente aucun nom et écris au lecteur,\n"
    "  tel quel : « la source ne documente pas le locuteur ». Le lecteur\n"
    "  reçoit cette phrase — jamais la règle qui la produit."
)


@dataclass
class SpeakerRecord:
    """The speaker with its provenance — the single container every act reads.

    ``source_key`` names where the value came from (``source_metadata.speaker``,
    ``stakes_and_stakeholders.stakeholders``); empty on an absent record.
    ``second_voice`` (#3390) is True when the stakeholders carry another
    SPEAKING party (an opponent, a second narrator): the #2845 caution is
    printed only then — an audience interjection is not a second voice.
    """

    value: str = ""
    provenance: str = ""  # PROVENANCE_METADATA | PROVENANCE_INFERRED | ""
    source_key: str = ""
    second_voice: bool = False


def _second_voice_in(stakes: Any, speaker_value: str) -> bool:
    """#3390 — another stakeholder who SPEAKS (an opponent, a second narrator).

    An ``audience`` entry never counts: an interjection from the public is
    not the document's second voice, and the #2845 caution fired twice on a
    correct attribution for exactly that reason (measured, v1 panel cycle 0).
    The speaker's own entry does not count against itself (same name,
    case-insensitive).
    """
    if not isinstance(stakes, dict):
        return False
    folded_speaker = speaker_value.strip().lower()
    for sh in stakes.get("stakeholders", []) or []:
        if not isinstance(sh, dict):
            continue
        role = str(sh.get("role", "") or "").strip().lower()
        if role not in _SECOND_VOICE_ROLES:
            continue
        name = str(sh.get("name", "") or "").strip()
        if _documents(name) and name.strip().lower() != folded_speaker:
            return True
    return False


def build_speaker_record(state: Any) -> SpeakerRecord:
    """Resolve the state's two speaker producers into one record (no LLM).

    Metadata first: when the corpus documents the speaker, that is the record
    — the producer's own note travels in ``source_key``. Otherwise the stakes
    extractor's speaker stakeholder is the record, labelled as the inference
    it is. Neither producer documents anything → empty record, said absent.
    """
    metadata = getattr(state, "source_metadata", {}) or {}
    stakes = getattr(state, "stakes_and_stakeholders", {}) or {}
    if isinstance(metadata, dict):
        for key in _SPEAKER_METADATA_KEYS:
            value = str(metadata.get(key, "") or "").strip()
            if _documents(value):
                return SpeakerRecord(
                    value=_cap(value),
                    provenance=PROVENANCE_METADATA,
                    source_key=f"source_metadata.{key}",
                    second_voice=_second_voice_in(stakes, value),
                )
    if isinstance(stakes, dict):
        for sh in stakes.get("stakeholders", []) or []:
            if not isinstance(sh, dict):
                continue
            role = str(sh.get("role", "") or "").strip().lower()
            if role not in _SPEAKER_ROLES:
                continue
            name = str(sh.get("name", "") or "").strip()
            if _documents(name):
                return SpeakerRecord(
                    value=_cap(name),
                    provenance=PROVENANCE_INFERRED,
                    source_key="stakes_and_stakeholders.stakeholders",
                    second_voice=_second_voice_in(stakes, name),
                )
    return SpeakerRecord()


def format_speaker_line(record: SpeakerRecord) -> str:
    """The ONE line every act renders — same value, same tag, by construction."""
    if not record.value:
        return (
            "Locuteur : (non documenté — ni en métadonnée, ni inféré du "
            "texte par l'extracteur d'enjeux)"
        )
    if record.provenance == PROVENANCE_METADATA:
        # #3311 — the writer reads the provenance CLASS (enregistrée vs
        # inférée), never the internal dotted path that carried it;
        # ``source_key`` stays on the record for tests and debugging.
        return f"Locuteur : {record.value} " f"(provenance : {_LABEL_METADATA})"
    # #3390 — the #2845 caution names a real second voice or stays silent:
    # an audience interjection is not one, and an unearned caution read as
    # doubt on a correct attribution.
    caution = f" ; {_TWO_VOICE_CAUTION}" if record.second_voice else ""
    return (
        f"Locuteur : {record.value} "
        f"(provenance : {_LABEL_INFERRED} — jamais une donnée vérifiée"
        f"{caution})"
    )
