"""One JSON reply from a persona model: the call, the fence, the parse (#3576).

Panel cycle 15 (15/11, #3374) measured the strategist read as ``parse_error``
on 4 of 9 documents with a read, against 4 of 81 over cycles 6 to 14. Every
failure carried the decoder message ``Expecting ':' delimiter`` at a mid-reply
character (1029 to 1608 at c15): the reply is malformed in its middle, not
truncated — and the reply itself was kept nowhere, so the cause could not be
read from the recorded states.

This module is the ONE father of the call → strip fence → parse → retry logic
the two context personas share (``strategist.build_strategic_read`` and
``historian.build_historical_context``). It is deliberately small and private:
the ~14 other JSON parsers of the repository are out of scope (#3576).

Choices, stated because they change what a read can claim:

- the second chance is ONE retry of the SAME prompt — not a repair pass, not
  a lenient parser. Whatever is accepted is still the model's own JSON, run
  through ``json.loads`` on the same text a human would run it on. A repair
  pass would rewrite the reply and blur "the model said this" into "the
  pipeline made this parse"; a lenient parser would accept text the decoder
  rejects, hiding the very malformation this record exists to show.
- only a MALFORMED reply is retried. An empty completion or a provider
  exception stays ``llm_error`` after its one call: those are not a decode
  symptom, and a second paid call would not repair them. A retry that cannot
  answer — the call raises, or comes back empty — keeps the first attempt's
  decode record, the retry's own failure riding inside it as ``retry_error``
  (#3597 review).
- the failure record is BOUNDED: ``JSON_REPLY_WINDOW_RADIUS`` characters
  around the decoder's position, plus the reply's length — enough to read a
  malformed middle, never the whole reply.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict

#: How many calls a malformed reply is worth: the first one, then one second
#: chance with the SAME prompt. Named because the mutation control sets it to
#: 1 and the witness must redden.
JSON_REPLY_ATTEMPTS = 2

#: Half-width of the reply window kept around the decoder's position, in
#: characters. Bounded on purpose: the state records enough to read a malformed
#: middle, never the whole reply.
JSON_REPLY_WINDOW_RADIUS = 120


@dataclass
class JsonReply:
    """One persona reply after the fence, and at most ``attempts`` calls.

    ``status`` is discriminated: ``ok`` (``payload`` holds the decoded reply),
    ``llm_error`` (the call returned no content — never retried) or
    ``parse_error`` (every attempt failed to decode). ``error`` is the
    state-facing cause; ``detail`` is the bare decoder string the log line has
    always carried; ``parse_failure`` is the bounded record below.
    """

    payload: Any = None
    status: str = "parse_error"
    error: str = ""
    detail: str = ""
    attempts: int = 0
    parse_failure: Dict[str, Any] = field(default_factory=dict)


def strip_json_fence(content: Any) -> str:
    """The pre-#3576 fence rule, unchanged: strip, unwrap at most one fence.

    Kept byte-for-byte identical to the two personas' inline version so a reply
    that parsed before parses now, and one that failed before fails the same
    way.
    """
    text = (content or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    return text


def describe_parse_failure(exc: json.JSONDecodeError, content: str) -> Dict[str, Any]:
    """The bounded record of a reply ``json.loads`` refused (#3576 ask 2).

    ``position``/``line``/``column`` are the decoder's own (``e.pos``,
    ``e.lineno``, ``e.colno``): the exact character a reader can re-open.
    ``window`` is the reply's text around that character, cut to
    ``JSON_REPLY_WINDOW_RADIUS`` on each side; ``window_start`` is its offset,
    so a reader can place it without trusting the record's formatting.
    ``reply_length`` lets a reader tell a malformed MIDDLE from a truncated
    reply — the distinction the cycle-15 log could not settle.
    """
    position = int(exc.pos)
    start = max(0, position - JSON_REPLY_WINDOW_RADIUS)
    end = min(len(content), position + JSON_REPLY_WINDOW_RADIUS)
    return {
        "message": str(exc.msg),
        "position": position,
        "line": int(exc.lineno),
        "column": int(exc.colno),
        "reply_length": len(content),
        "window": content[start:end],
        "window_start": start,
    }


async def request_json_reply(
    llm_callable: Callable[[str], Awaitable[str]],
    prompt: str,
    *,
    attempts: int = JSON_REPLY_ATTEMPTS,
) -> JsonReply:
    """Call the model, strip its fence, and decode its JSON — with one retry.

    A decode failure is retried on the SAME prompt while attempts remain; any
    other outcome ends the loop. A provider exception on the FIRST attempt
    propagates to the caller, which owns the ``llm_error`` branch (unchanged
    behaviour); so does an empty completion on the first attempt. A retry that
    cannot answer — the call RAISES, or comes back EMPTY — does not erase what
    the first attempt left: the reply that failed to decode is still the
    primary cause, so the loop stops and returns ``parse_error`` with the
    first attempt's record, the retry's own failure riding inside it as
    ``retry_error`` — no new state key, and neither cause is lost (#3597
    review).
    """
    last_error = ""
    last_detail = ""
    failure: Dict[str, Any] = {}
    made = 0

    def _unanswered_retry(reason: str) -> JsonReply:
        """The retry could not answer (#3597 review): it raised, or was empty.

        One father for both shapes so they cannot drift: the reply that failed
        to decode is still the primary cause, and the retry's own failure
        JOINS its record as ``retry_error`` instead of replacing it.
        """
        record = dict(failure)
        record["retry_error"] = reason
        return JsonReply(
            status="parse_error",
            error=last_error,
            detail=last_detail,
            attempts=made,
            parse_failure=record,
        )

    while made < max(1, attempts):
        made += 1
        try:
            content = strip_json_fence(await llm_callable(prompt))
        except Exception as exc:
            if not failure:
                # First attempt, nothing held: the provider failure is the
                # whole story, and the caller's ``llm_error`` branch owns it
                # exactly as before #3576.
                raise
            return _unanswered_retry(f"{type(exc).__name__}: {exc}")
        if not content:
            if not failure:
                # First attempt: an empty completion is an ``llm_error``
                # exactly as before #3576 — it is not a decode symptom.
                return JsonReply(
                    status="llm_error", error="empty completion", attempts=made
                )
            return _unanswered_retry("empty completion")
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            last_detail = str(exc)
            failure = describe_parse_failure(exc, content)
            continue
        return JsonReply(payload=parsed, status="ok", attempts=made)
    return JsonReply(
        status="parse_error",
        error=last_error,
        detail=last_detail,
        attempts=made,
        parse_failure=failure,
    )
