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
"""

from __future__ import annotations

from typing import Any

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
