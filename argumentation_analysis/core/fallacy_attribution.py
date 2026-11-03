# -*- coding: utf-8 -*-
"""#3180 — whose move a fallacy detection is.

The record carries ``move_author`` on a detection: ``speaker`` (the analysed
text's own speaker commits the move) or ``reported`` (the text reports or
denounces a move made by another party, named by ``move_author_label``).
Absent or invalid = not stated: every reader keeps the historical speaker
attribution and invents no third party (#1019).

``is_speaker_move`` is the ONE predicate attribution count sites read. It
accepts the stored dict record and the synthesised ``FallacyDiagnosis`` object
alike, so no reader can drift into its own reading (a reported detection must
never be counted as the speaker's, nor contest the unit that reports it).

``confidence_of`` reads the detector's own confidence off the same record with
#3029's guard (a measurement is a number; anything else — absent, a string, a
bool — is UNMEASURED, never a default value), and
``detector_confidence_note`` renders the standing the evidence lines print
(#3231).
"""

from __future__ import annotations

from typing import Any, Optional

MOVE_AUTHOR_SPEAKER = "speaker"
MOVE_AUTHOR_REPORTED = "reported"
_MOVE_AUTHORS = (MOVE_AUTHOR_SPEAKER, MOVE_AUTHOR_REPORTED)


def _field(entry: Any, name: str) -> Any:
    """Read ``name`` off a mapping record or an attribute-carrying object."""
    if isinstance(entry, dict):
        return entry.get(name)
    return getattr(entry, name, None)


def move_author_of(entry: Any) -> str:
    """The stated author, or ``speaker`` when the record is silent/invalid."""
    value = _field(entry, "move_author")
    if isinstance(value, str):
        value = value.strip()
        if value in _MOVE_AUTHORS:
            return value
    return MOVE_AUTHOR_SPEAKER


def is_speaker_move(entry: Any) -> bool:
    """True when the move belongs to the analysed text's own speaker.

    The shared predicate every attribution count site reads. An absent or
    unknown ``move_author`` reads as the speaker (legacy attribution), never
    as a third party.
    """
    return move_author_of(entry) == MOVE_AUTHOR_SPEAKER


def is_reported_move(entry: Any) -> bool:
    """True when the text reports/denounces another party's move."""
    return move_author_of(entry) == MOVE_AUTHOR_REPORTED


def move_author_label_of(entry: Any) -> str:
    """The opaque third-party label, empty when none was stated."""
    value = _field(entry, "move_author_label")
    if isinstance(value, str):
        return value.strip()
    return ""


# --- #3231 — how firmly the detector itself holds the detection --------------


def confidence_of(entry: Any) -> Optional[float]:
    """The detector's own confidence, or ``None`` when unmeasured (#3029).

    A measurement is a number the producer wrote; a bool is a flag, not a
    measure, and a string ("high") carries no number to print. Anything but
    a real number reads as UNMEASURED — never as a default value the
    producer never stated.
    """
    value = _field(entry, "confidence")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _confidence_fr(value: float) -> str:
    """A measured confidence in French prose: comma, no padding zero."""
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return (text or "0").replace(".", ",")


def detector_confidence_note(confidence: Optional[float]) -> str:
    """The standing every fallacy line prints next to its verdict (#3231).

    « confiance du détecteur : 0,4 — lecture provisoire » — the decimal
    keeps its place (evidence is where the figure belongs, #3231) and the
    ladder word stands BESIDE it (#3369): one scale printed once, so the
    writer copies the word instead of tracing its own bands. Or « non
    mesurée » when the producer stated no number — unmeasured is PRINTED as
    unmeasured, never filled in with a default (#3029's contract, on the
    surfaces the acts read), and carries no word: a scale needs a number.
    """
    if confidence is None:
        return "confiance du détecteur : non mesurée"
    note = f"confiance du détecteur : {_confidence_fr(confidence)}"
    word = detection_standing_word(confidence)
    return f"{note} — {word}" if word else note


#: #3369 — the scale under the ladder words. #3248 wrote the WORDS
#: (« provisoire, moyenne, ferme ») and the ban on the figure, but never
#: the line between the words: each act re-derived its own bands, and the
#: R1136a render read the same 0.70-0.72 detections « fermes » in Act II
#: and « confiance moyenne » in Act III. The boundaries are calibrated on
#: the measured confidences (the PR census): « ferme » from 0.70 — the top
#: band of what the detector actually emits (18 % of the stored values, all
#: of the R1136a highs); « moyenne » from 0.50 — the measured median of the
#: stored distribution; below 0.50 the reading is not yet posed, it is
#: « provisoire ».
_STANDING_FERME_MIN = 0.70
_STANDING_MOYENNE_MIN = 0.50


def detection_standing_word(confidence: Optional[float]) -> str:
    """The ONE ladder word for a detector confidence (#3369).

    « lecture ferme » from 0.70, « lecture moyenne » from 0.50 to below
    0.70, « lecture provisoire » below 0.50 — the same number gives the
    same word on every surface that prints it. An UNMEASURED confidence
    has no word (empty string): the evidence line says « non mesurée » and
    nothing is filled in (#3029). The justification's written reserve can
    only LOWER the word, never raise it (#3231) — that reserve stays the
    writer's judgement; this function is only the scale.
    """
    if confidence is None:
        return ""
    if confidence >= _STANDING_FERME_MIN:
        return "lecture ferme"
    if confidence >= _STANDING_MOYENNE_MIN:
        return "lecture moyenne"
    return "lecture provisoire"


# #3248 — the ONE reader-facing ladder for a detection's standing, and the
# ban on the figure above. The fallacy evidence lines print the detector's
# own number (``detector_confidence_note``); the R1113a writer copied that
# figure into the narrative (« avec une confiance de détection de 0,6 à
# 0,7 ») while the same render said the standing in words three pages
# earlier — both vocabularies live in one render and the reader cannot
# weigh a « 0,6 ». One constant, grafted into BOTH acts' consignes (the
# #3237 gesture); the check-side class lives in reader_vocabulary_check.
# #3369 — the rule now also points at the printed word: the evidence line
# carries the ladder word beside the measure, the writer takes THAT word
# and does not trace its own scale; a written reserve lowers it only.
DETECTION_STANDING_RULE = (
    "Le standing d'une détection se dit en mots — lecture provisoire, "
    "moyenne ou ferme — jamais en chiffre : la confiance chiffrée du "
    "détecteur ne paraît jamais dans le récit. La ligne de preuve imprime "
    "le mot du standing à côté de sa mesure : reprends CE mot, ne trace pas "
    "ta propre échelle. Une réserve écrite dans la justification peut "
    "abaisser le mot d'un cran, jamais l'élever."
)
