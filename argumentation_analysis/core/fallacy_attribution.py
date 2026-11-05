# -*- coding: utf-8 -*-
"""#3180 — whose move a fallacy detection or an argument unit is.

The record carries ``move_author``: ``speaker`` (the analysed text's own
speaker commits the move), ``reported`` (the text reports or denounces a move
made by another party, named by ``move_author_label``), ``character`` (a
fiction's character commits it — #3390) or ``audience`` (an audience
interjection — #3390). Absent or invalid = not stated: every reader keeps the
historical speaker attribution and invents no third party (#1019).

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

import re
from typing import Any, Optional

MOVE_AUTHOR_SPEAKER = "speaker"
MOVE_AUTHOR_REPORTED = "reported"
MOVE_AUTHOR_CHARACTER = "character"
MOVE_AUTHOR_AUDIENCE = "audience"
#: The closed vocabulary, exported — the writers that gate a stored
#: ``move_author`` (``add_argument``, ``add_fallacy``, the plugins) read THIS
#: tuple, never a literal copy: #3390 extends it (``character``, ``audience``)
#: and seven copies of the two-value tuple would have drifted into seven
#: gates, five of them still dropping the new values (#1019's family).
MOVE_AUTHORS = (
    MOVE_AUTHOR_SPEAKER,
    MOVE_AUTHOR_REPORTED,
    MOVE_AUTHOR_CHARACTER,
    MOVE_AUTHOR_AUDIENCE,
)


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
        if value in MOVE_AUTHORS:
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


def move_author_note(entry: Any) -> str:
    """The ONE French clause a briefing prints for a non-speaker move (#3390).

    A fallacy or unit whose author is not the speaker carries this sentence
    on its briefing line, so no writer can read it as the speaker's own move:
    the Act II / synthesis contradiction of the v1 panel's cycle 0 (one act
    attributed a passage to third parties, the synthesis listed the same
    passage among the speaker's structural vulnerabilities) was two readers
    with no shared wording. The speaker case prints nothing — it is the
    historical default every line already carries, and a note on every line
    would bury the ones that matter. An absent or invalid record prints
    nothing either: not stated is not speaker-stated (#1019).
    """
    author = move_author_of(entry)
    if author == MOVE_AUTHOR_REPORTED:
        note = "RAPPORTÉ : le locuteur rapporte ce geste, il ne le commet pas"
        label = move_author_label_of(entry)
        return f"{note} (tiers : {label})" if label else note
    if author == MOVE_AUTHOR_CHARACTER:
        return (
            "PERSONNAGE : geste commis par un personnage de la fiction — "
            "pas une assertion de l'auteur"
        )
    if author == MOVE_AUTHOR_AUDIENCE:
        return "PUBLIC : interjection du public, pas le fait du locuteur"
    return ""


# --- #3391 — the register test (proportionality of an emotional appeal) ------

#: The two outcomes of the test the emotion / loyalty / flag family carries.
#: The taxonomy's own conditions for these nodes ARE the test: is the emotion,
#: and the call it drives, proportionate to what the text itself states — its
#: facts and its stakes? ``proportionate`` = legitimate in its register (the
#: move is NOT a fallacy; the verdict is recorded, not dropped);
#: ``disproportionate`` = the appeal drives past what the text states, and the
#: flag stands (anti-pendulum: the same map for every side).
REGISTER_TEST_PROPORTIONATE = "proportionate"
REGISTER_TEST_DISPROPORTIONATE = "disproportionate"
REGISTER_TESTS = (REGISTER_TEST_PROPORTIONATE, REGISTER_TEST_DISPROPORTIONATE)

#: #3391 — the marker vocabulary of the register family, matched on a
#: detection's NAME (the taxonomy splits the register across ``Influence`` and
#: ``Insuffisance``, so the CSV ``Famille`` cannot carry the predicate: the
#: twenty-seven nodes measured on the shipped taxonomy — appeals to emotion,
#: loyalty, the flag, pride, pity, fear, terror, moral panic, pathos and the
#: emotional-reasoning biases). Word boundaries on both sides, ``_`` and ``-``
#: in the word class: "peur" must not fire inside another word, and the
#: apostrophe forms (``l'émotion`` / ``l’émotion``) are reached because the
#: marker is the noun itself (#3390/R1141's boundary lesson).
_REGISTER_FAMILY_MARKERS = (
    "émotion",
    "émotionnel",
    "affectif",
    "pathétique",
    "pathos",
    "loyauté",
    "drapeau",
    "fierté",
    "pitié",
    "peur",
    "terreur",
    "crainte",
    "panique",
    "emotion",
    "emotional",
    "affective",
    "pathetic",
    "loyalty",
    "flag",
    "pride",
    "pity",
    "fear",
    "terror",
)

_REGISTER_FAMILY_PATTERNS = tuple(
    re.compile(r"(?<![\w-])" + re.escape(marker) + r"(?![\w-])")
    for marker in _REGISTER_FAMILY_MARKERS
)


def is_register_family_detection(name: str) -> bool:
    """#3391 — True when a detection's name belongs to the register family.

    The predicate reads the NAME, never the CSV ``Famille``: the register is
    split across ``Influence`` (appeal to emotion, pride, pity, fear) and
    ``Insuffisance`` (loyalty, the flag, pathetic fallacy), and matching the
    whole ``Influence`` family would sweep in four hundred nodes that carry no
    such test.
    """
    value = str(name or "").lower()
    if not value:
        return False
    return any(pattern.search(value) for pattern in _REGISTER_FAMILY_PATTERNS)


def normalize_register_test(value: Any) -> str:
    """The closed-vocabulary verdict from a raw value, ``""`` when unknown.

    The tool receives the value from the model (free text until this gate);
    the state door receives it from a writer. Both normalize HERE, so a
    stray ``"Disproportionate"`` reaches the record the same way and a
    non-vocabulary string is absence, never a measurement (#3029).
    """
    if isinstance(value, str):
        candidate = value.strip().lower()
        if candidate in REGISTER_TESTS:
            return candidate
    return ""


def register_test_of(entry: Any) -> str:
    """The register test the detector recorded, or ``""`` when unstated.

    Only the closed vocabulary travels: anything else is not a measurement
    (#3029's rule, applied to this field).
    """
    return normalize_register_test(_field(entry, "register_test"))


def register_test_note(entry: Any) -> str:
    """The ONE French clause a briefing prints for a register-family detection.

    Three states, each printed as what it is (#1019/#3029):

    * ``disproportionate`` — the flag stands, and the line carries the reason
      it stands: the appeal was tested against what the text itself states.
    * in the family, no test recorded — the line says the test is ABSENT, so
      no writer reads a bare flag as a strategy anchor (#3391 ask 3).
    * not in the family, or not a detection name at all — nothing is printed;
      the test is not owed there.
    """
    test = register_test_of(entry)
    name = str(_field(entry, "type") or _field(entry, "fallacy_type") or "")
    if test == REGISTER_TEST_DISPROPORTIONATE:
        return (
            "REGISTRE : l'appel dépasse ce que le texte énonce (faits et "
            "enjeux) — test de proportionnalité enregistré"
        )
    if test == REGISTER_TEST_PROPORTIONATE:
        # Defensive: a proportionate verdict is not a fallacy, and the descent
        # never confirms one. If a record ever carries it, the line says what
        # it measured rather than hiding it.
        return (
            "REGISTRE : appel proportionné à ce que le texte énonce — "
            "cas légitime, enregistré"
        )
    if is_register_family_detection(name):
        return "REGISTRE : test de proportionnalité non enregistré"
    return ""


# --- #3394 — the taxonomy's own definition for a printed label ---------------

# The taxonomy speaks to whoever commits the fallacy: its definitions are
# overwhelmingly second person (« Vous … »). The census that grounded the
# R1142 fix measured 1 403 of 1 408 cells matching this test.
_SECOND_PERSON_DEFINITION = re.compile(r"\b(vous|votre|vos)\b", re.IGNORECASE)


def taxonomy_definition_note(entry: Any) -> str:
    """The ONE French clause that carries a label's definition (#3394).

    Cycle 0 printed taxonomy labels bare — « sophisme métonymique » reached
    the reader with nothing to read it against, and the machinery words the
    labels ride on (« test modal », « cardinalité minimale ») did the rest.
    The note resolves the detection's node in the vendored taxonomy (stored
    dotted path first, exact name second) and carries that node's one-line
    ``desc_fr`` on the briefing line, so no writer has to know what the label
    means for the reader to learn it.

    #3394 R1143 — when the definition addresses the arguer (the same
    ``\\b(vous|votre|vos)\\b`` test as the census), the note SAYS so: a
    writer whose reader is not the speaker was carrying « vous » into the
    report's prose with nothing telling it who « vous » is. The register is
    stated here, by the ONE producer — upstream definitions are not
    rewritten (an impersonal definition stays impersonal and prints the
    bare form).

    The note is a definition, not a verdict: it prints in lowercase, it never
    restates the detection, and an unresolvable label prints NOTHING — a
    definition borrowed from a sibling node would be invention, not lookup
    (anti-#1019, :func:`taxonomy_definition`'s contract).
    """
    from argumentation_analysis.utils.taxonomy_loader import taxonomy_definition

    ftype = str(_field(entry, "type") or _field(entry, "fallacy_type") or "")
    path = _field(entry, "taxonomy_path")
    definition = taxonomy_definition(ftype, str(path) if path else None)
    if not definition:
        return ""
    if _SECOND_PERSON_DEFINITION.search(definition):
        return (
            "définition (la taxonomie s'adresse à qui commet le sophisme) : "
            f"{definition}"
        )
    return f"définition : {definition}"


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
