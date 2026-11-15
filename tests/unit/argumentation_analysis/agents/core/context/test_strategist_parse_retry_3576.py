"""#3576 — a malformed persona reply gets one retry, and the cause is kept.

Panel cycle 15 (15/11, #3374) measured the strategist read as ``parse_error``
on 4 of 9 documents with a read (doc_B, doc_C, doc_E, doc_I), against 4 of 81
over cycles 6 to 14. Every failure carries the decoder message
``Expecting ':' delimiter`` at a mid-reply character (1029 to 1608 at c15):
the reply is malformed in its middle, not truncated. The reply itself was kept
nowhere, so the cause could not be read from the recorded states — the
historian failed 0 times over the same cycles and is the blind sibling.

What this file pins, synthetic-only (invented parties, options and text —
never a corpus name, place or date):

- a malformed first reply is followed by ONE retry of the SAME prompt; a
  valid second reply yields ``ok``, the state records ``attempts: 2``, and
  the players are there;
- two malformed replies stay ``parse_error`` after exactly two calls, and
  the state keeps the cause: decoder message, position (char, line, column),
  the reply's length, and a window of the reply around the position bounded
  by ``JSON_REPLY_WINDOW_RADIUS`` — the cap BITES, the reply is longer than
  one radius on both sides of the position;
- the historian gets the same behaviour and the same record (one helper,
  never two copies);
- a valid first reply is exactly one call, with no ``attempts``/``error``/
  ``parse_failure`` key: the success path is byte-identical to the pre-#3576
  state — the control that stays green on both sides;
- an empty completion stays an ``llm_error`` after ONE call: only a
  MALFORMED reply gets the second chance, and the two failure statuses stay
  discriminated (each with its cause now written to the state);
- a retry call that RAISES keeps the first attempt's decode record, with the
  provider failure riding inside it as ``retry_error``: both causes matter
  in that one case, and neither erases the other.

The file collects on ``main``: the new symbols are imported inside the tests
that need them, so the feature arms redden while the controls stay green —
the born-red measurement keeps its control arm.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

from argumentation_analysis.agents.core.context.historian import (
    build_historical_context,
)
from argumentation_analysis.agents.core.context.strategist import (
    build_strategic_read,
)

#: Synthetic document: invented parties, no name, place or date of any corpus.
_DOC = (
    "La commission a présenté son texte ce matin. "
    "Le conseil demande une pause avant le vote final. "
    "Les deux parties disent vouloir un accord."
)

#: Neutral filler long enough that the decoder's position sits MORE than one
#: window radius from both ends of the reply: the cap is then measured, not
#: merely declared.
_PAD = "Une phrase neutre de remplissage, sans nom ni date. " * 3

#: The measured failure shape: after an object key, a ':' is expected and
#: something else follows — the ``Expecting ':' delimiter`` the panel logged,
#: mid-reply. ``_BAD_POS`` is the offending token's own index, the position a
#: decoder names.
_MALFORMED_REPLY = (
    '{"players": [{"name": "Parti Un", "role": "demandeur", '
    '"stance": "' + _PAD + '"}], '
    '"options": ["pause", "vote"], '
    '"preferences": {"Parti Un" ["pause", "vote"]}, '
    '"reading": "' + _PAD + '"}'
)
_BAD_TOKEN = '["pause", "vote"]}'
_BAD_POS = _MALFORMED_REPLY.index(_BAD_TOKEN)

#: The record's keys, pinned whole: the strategist and the historian must keep
#: the SAME cause (one helper, not two drifting copies).
_FAILURE_KEYS = {
    "message",
    "position",
    "line",
    "column",
    "reply_length",
    "window",
    "window_start",
}

_VALID_READ = json.dumps(
    {
        "players": [
            {
                "name": "Parti Un",
                "role": "demandeur",
                "stance": "veut une pause avant le vote",
            },
            {
                "name": "Parti Deux",
                "role": "opposant",
                "stance": "veut le vote immédiat",
            },
        ],
        "options": ["pause", "vote"],
        "preferences": {
            "Parti Un": ["pause", "vote"],
            "Parti Deux": ["vote", "pause"],
        },
        "reading": "Deux parties s'opposent sur le calendrier.",
        "blind_spot": "",
    }
)

_VALID_HISTORICAL = json.dumps(
    {
        "situation": "Une assemblée délibère du calendrier d'un texte.",
        "blind_spot": "",
        "items": [{"claim": "Le texte est présenté ce matin.", "confidence": 0.6}],
    }
)


def _state(raw_text: str = _DOC):
    return SimpleNamespace(
        raw_text=raw_text,
        source_metadata={"speaker": "Speaker_A", "venue": "assembly"},
        stakes_and_stakeholders={"stakes": [], "stakeholders": []},
    )


def _replies(*replies):
    """A fake model returning ``replies`` in order, reusing the last one.

    ``calls`` records every prompt: the witness can then state that the retry
    sends the SAME prompt, and that a first-try success is a single call.
    """
    calls: list = []

    async def _call(prompt: str) -> str:
        calls.append(prompt)
        return replies[min(len(calls), len(replies)) - 1]

    return _call, calls


def _window_of(reply: str, start: int, window: str) -> bool:
    """``window`` is exactly the reply's own characters starting at ``start``."""
    return reply[start : start + len(window)] == window


# ============================================================================
# The strategist — one second chance, then the cause
# ============================================================================


class TestTheStrategistGetsOneSecondChance:
    async def test_a_malformed_first_reply_is_retried_once(self):
        llm, calls = _replies(_MALFORMED_REPLY, _VALID_READ)

        result = await build_strategic_read(_state(), llm)
        payload = result.to_state()

        assert result.status == "ok"
        assert len(calls) == 2, "exactly one second chance"
        assert calls[0] == calls[1], "the second chance is the SAME prompt"
        assert payload["attempts"] == 2, "the state records the second chance"
        assert [player["name"] for player in payload["players"]] == [
            "Parti Un",
            "Parti Deux",
        ]
        assert "error" not in payload
        assert "parse_failure" not in payload

    async def test_two_malformed_replies_keep_the_cause_in_the_state(self):
        from argumentation_analysis.agents.core.context._json_reply import (
            JSON_REPLY_WINDOW_RADIUS,
        )

        llm, calls = _replies(_MALFORMED_REPLY)

        result = await build_strategic_read(_state(), llm)
        payload = result.to_state()

        assert result.status == "parse_error"
        assert len(calls) == 2, "one second chance, never a third call"
        assert payload["status"] == "parse_error"
        assert payload["attempts"] == 2
        assert payload["players"] == [], "twice-failed stays an empty read"
        assert payload["error"].startswith("JSONDecodeError: Expecting ':'")
        failure = payload["parse_failure"]
        assert set(failure) == _FAILURE_KEYS
        assert failure["message"] == "Expecting ':' delimiter"
        assert failure["position"] == _BAD_POS
        assert _MALFORMED_REPLY[_BAD_POS] == _BAD_TOKEN[0]
        assert failure["line"] == 1
        assert failure["column"] == _BAD_POS + 1
        assert failure["reply_length"] == len(_MALFORMED_REPLY)
        # The window is the reply's own characters around the position …
        assert _window_of(_MALFORMED_REPLY, failure["window_start"], failure["window"])
        assert _MALFORMED_REPLY[failure["position"]] in failure["window"]
        # … and the cap bites: more than one radius on each side remains out.
        assert JSON_REPLY_WINDOW_RADIUS <= _BAD_POS
        assert _BAD_POS <= len(_MALFORMED_REPLY) - JSON_REPLY_WINDOW_RADIUS
        assert len(failure["window"]) == 2 * JSON_REPLY_WINDOW_RADIUS
        assert len(failure["window"]) < len(_MALFORMED_REPLY)

    async def test_a_valid_first_reply_is_one_call_with_no_new_key(self):
        llm, calls = _replies(_VALID_READ)

        result = await build_strategic_read(_state(), llm)
        payload = result.to_state()

        assert [player["name"] for player in payload["players"]] == [
            "Parti Un",
            "Parti Deux",
        ]
        assert len(calls) == 1, "a valid reply is never re-asked"
        assert "attempts" not in payload
        assert "error" not in payload
        assert "parse_failure" not in payload


# ============================================================================
# The historian — same behaviour, same record (one helper)
# ============================================================================


class TestTheHistorianGetsTheSameSecondChance:
    async def test_a_malformed_first_reply_is_retried_once(self):
        llm, calls = _replies(_MALFORMED_REPLY, _VALID_HISTORICAL)

        result = await build_historical_context(_state(), llm)
        payload = result.to_state()

        assert result.status == "ok"
        assert len(calls) == 2
        assert calls[0] == calls[1], "the second chance is the SAME prompt"
        assert payload["attempts"] == 2
        assert payload["items"][0]["claim"] == "Le texte est présenté ce matin."
        assert "error" not in payload
        assert "parse_failure" not in payload

    async def test_two_malformed_replies_keep_the_same_record(self):
        llm, calls = _replies(_MALFORMED_REPLY)

        result = await build_historical_context(_state(), llm)
        payload = result.to_state()

        assert result.status == "parse_error"
        assert len(calls) == 2
        assert payload["items"] == []
        assert payload["error"].startswith("JSONDecodeError: Expecting ':'")
        failure = payload["parse_failure"]
        assert set(failure) == _FAILURE_KEYS
        assert failure["message"] == "Expecting ':' delimiter"
        assert failure["position"] == _BAD_POS
        assert _window_of(_MALFORMED_REPLY, failure["window_start"], failure["window"])

    async def test_a_valid_first_reply_is_one_call_with_no_new_key(self):
        llm, calls = _replies(_VALID_HISTORICAL)

        result = await build_historical_context(_state(), llm)
        payload = result.to_state()

        assert payload["items"][0]["claim"] == "Le texte est présenté ce matin."
        assert len(calls) == 1
        assert "attempts" not in payload
        assert "error" not in payload
        assert "parse_failure" not in payload


# ============================================================================
# Only a MALFORMED reply is retried — llm_error keeps its meaning
# ============================================================================


class TestOnlyAMalformedReplyIsRetried:
    async def test_an_empty_completion_is_one_llm_error_with_its_cause(self):
        llm, calls = _replies("   ")

        result = await build_strategic_read(_state(), llm)
        payload = result.to_state()

        assert result.status == "llm_error"
        assert len(calls) == 1, "an empty completion is not a decode symptom"
        assert "attempts" not in payload
        assert payload["error"] == "empty completion"

    async def test_the_historian_discriminates_the_same_way(self):
        llm, calls = _replies("")

        result = await build_historical_context(_state(), llm)
        payload = result.to_state()

        assert result.status == "llm_error"
        assert len(calls) == 1
        assert "attempts" not in payload
        assert payload["error"] == "empty completion"


# ============================================================================
# A retry call that RAISES — the first attempt's record is the one to keep
# ============================================================================


class TestARaisingSecondChanceKeepsTheFirstRecord:
    """Review of #3597: attempt 1 failed to decode, attempt 2's CALL raised.

    The provider exception must not erase the decode record: that reply is
    still the primary cause, and losing its message/position here would lose
    the one thing #3576 exists to keep — in the one case where both causes
    matter. The provider failure rides INSIDE ``parse_failure`` as
    ``retry_error``; no new state key.
    """

    def _llm(self):
        calls: list = []

        async def _call(prompt: str) -> str:
            calls.append(prompt)
            if len(calls) > 1:
                raise TimeoutError("provider timeout")
            return _MALFORMED_REPLY

        return _call, calls

    async def test_the_strategist_keeps_the_first_attempts_record(self):
        llm, calls = self._llm()

        result = await build_strategic_read(_state(), llm)
        payload = result.to_state()

        assert result.status == "parse_error"
        assert len(calls) == 2, "the retry was asked for and raised"
        assert payload["attempts"] == 2
        assert payload["players"] == []
        # The primary cause stays the DECODE failure, not the provider one.
        assert payload["error"].startswith("JSONDecodeError: Expecting ':'")
        failure = payload["parse_failure"]
        assert set(failure) == _FAILURE_KEYS | {"retry_error"}
        assert failure["message"] == "Expecting ':' delimiter"
        assert failure["position"] == _BAD_POS
        assert failure["retry_error"] == "TimeoutError: provider timeout"

    async def test_the_historian_keeps_the_first_attempts_record(self):
        llm, calls = self._llm()

        result = await build_historical_context(_state(), llm)
        payload = result.to_state()

        assert result.status == "parse_error"
        assert len(calls) == 2
        assert payload["attempts"] == 2
        assert payload["items"] == []
        assert payload["error"].startswith("JSONDecodeError: Expecting ':'")
        failure = payload["parse_failure"]
        assert set(failure) == _FAILURE_KEYS | {"retry_error"}
        assert failure["message"] == "Expecting ':' delimiter"
        assert failure["position"] == _BAD_POS
        assert failure["retry_error"] == "TimeoutError: provider timeout"
