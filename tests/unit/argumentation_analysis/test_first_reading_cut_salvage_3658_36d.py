"""#3658 item 36d (R1206 dispatch, State 7089155290) — a cut first reading keeps
its complete objects, and the record NAMES the cut.

Measured by the coordinator on the free doc_J re-run (i1206) and on c21 (the
paid route): a first reading cut at its cap keeps only its pillars and is
recorded ``ok`` — the thesis, the mechanism and every complete move written
before the cut are lost, and nothing in the state says the reading was cut.

Cause, read in the code: ``_parse_answer`` falls back to ``_salvage_objects``,
which re-scans the inside of a BALANCED span. In a cut answer the outer ``{``
never closes, so ``_balanced_object_spans`` yields nothing and the inside is
never re-scanned; only ``pillars`` comes back, through ``_array_span``, which
finds the array by its key.

Asks (coordinator):
- (a) when the outer object never closes, the complete objects written before
  the cut are kept and routed by key (thesis, mechanism), local moves come back
  as moves, and the complete elements of a cut ``pillars`` array are kept;
- (b) the record names the cut: ``degraded: true`` with a reason naming the
  length stop and the cap, the status is NOT ``parse_error`` when something was
  kept, and the signal is the reading's OWN call's finish reason, never an
  inference from the token count;
- (c) witnesses born red on main: the probe's cut answer yields a thesis, a
  mechanism, 2 pillars and 4 moves (today: 2 pillars); a cut inside a pillar
  keeps the complete pillars; one mutation per point.

Seat-free: synthetic answers, invented words only — no corpus, no key, no
network. The cut signal rides the fake callable's ``last_finish_reason``, the
attribute the production persona callable exposes (#3658 item 36d ask b).
"""

from __future__ import annotations

import json
from types import SimpleNamespace

from argumentation_analysis.agents.core.reading import first_reading as fr

#: Invented document whose sentences are unambiguous (a real shape, not a blob).
DOC = (
    "Le rapport commence par une concession : la mesure a coûté cher à la "
    "région. Puis il affirme que l'effort en valait la peine, sur la foi d'un "
    "chiffre unique. Enfin il interpelle l'auditoire et l'invite à choisir "
    "son camp. Une annexe détaille le budget et le calendrier des travaux."
)


def _state(text: str = DOC) -> SimpleNamespace:
    return SimpleNamespace(raw_text=text)


class _CutModel:
    """Answers a CUT reply and exposes the reading's OWN finish reason — the
    attribute the production persona callable sets from the SDK envelope."""

    def __init__(self, answer: str, finish_reason: str = "length") -> None:
        self.answer = answer
        self.last_finish_reason = finish_reason
        self.prompts: list[str] = []

    async def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.answer


def _well_formed() -> str:
    """Thesis, mechanism, 2 pillars, 4 local moves — the probe's full answer."""
    return json.dumps(
        {
            "thesis": {
                "kind": "thesis",
                "reading": "T",
                "quote": "l'effort en valait la peine",
            },
            "mechanism": {
                "kind": "device",
                "reading": "M",
                "quote": "l'invite à choisir son camp",
            },
            "pillars": [
                {"kind": "claim", "reading": "P1", "quote": "la mesure a coûté cher"},
                {"kind": "claim", "reading": "P2", "quote": "un chiffre unique"},
            ],
            "moves": [
                {"kind": "claim", "reading": "m1", "quote": "Le rapport commence"},
                {"kind": "claim", "reading": "m2", "quote": "Puis il affirme"},
                {"kind": "claim", "reading": "m3", "quote": "Enfin il interpelle"},
                {"kind": "claim", "reading": "m4", "quote": "son camp"},
                {"kind": "claim", "reading": "m5", "quote": "Une annexe détaille"},
            ],
        },
        ensure_ascii=False,
    )


def _cut_inside_last_move() -> str:
    """The well-formed answer cut inside its 5th move (m5) — the outer ``{``
    never closes, so today only the pillars come back. m1..m4 are complete."""
    s = _well_formed()
    return s[: s.index("Une annexe") + 8]


# ---------------------------------------------------------------------------
# (a) The salvage reads a cut answer.
# ---------------------------------------------------------------------------


def test_the_salvage_recovers_a_cut_answer_complete_objects():
    """Born red on main (today: 2 pillars, nothing else). The cut answer of the
    probe must yield a thesis, a mechanism, 2 pillars and 4 local moves."""
    parsed, _malformed = fr._parse_answer(_cut_inside_last_move(), max_pillars=5)
    assert isinstance(parsed.get("thesis"), dict), parsed
    assert isinstance(parsed.get("mechanism"), dict), parsed
    assert len(parsed.get("pillars", [])) == 2, parsed
    # The 4 complete local moves written before the cut come back as moves.
    readings = {m.get("reading") for m in parsed.get("moves", [])}
    assert {"m1", "m2", "m3", "m4"} <= readings, readings


def test_a_cut_inside_a_pillar_keeps_the_complete_pillars():
    """A cut inside the SECOND pillar keeps the first (complete) one; the
    thesis and mechanism written before it are still recovered."""
    s = _well_formed()
    cut = s[: s.index("un chiffre unique") + 6]
    parsed, _malformed = fr._parse_answer(cut, max_pillars=5)
    pillars = parsed.get("pillars", [])
    assert any(p.get("reading") == "P1" for p in pillars), pillars
    assert isinstance(parsed.get("thesis"), dict), parsed


# ---------------------------------------------------------------------------
# (b) The record NAMES the cut, from the call's OWN finish reason.
# ---------------------------------------------------------------------------


async def test_a_cut_reading_is_recorded_degraded_not_parse_error():
    """Ask b: a cut reading that kept something is NOT a parse_error; it is
    ``ok`` AND ``degraded: true``, with a reason naming the length stop."""
    result = await fr.build_first_reading(_state(), _CutModel(_cut_inside_last_move()))
    assert result.status == "ok", result.status
    assert result.moves, "a cut reading that recovered moves must record them"
    payload = result.to_state()
    assert payload.get("degraded") is True, payload
    reason = payload.get("degraded_reason", "")
    assert "length" in reason.lower(), reason


async def test_a_complete_reading_is_not_marked_degraded():
    """A reading whose call did NOT stop on length is not marked degraded —
    the signal is the finish reason, never an inference from the token count."""
    result = await fr.build_first_reading(
        _state(), _CutModel(_well_formed(), finish_reason="stop")
    )
    assert result.status == "ok"
    assert not result.to_state().get("degraded"), result.to_state()


def test_the_cap_rides_the_degraded_reason():
    """The degraded reason names the cap the reading spent, so a reader can
    tell an 8 192 stop from a 4 096 one without re-deriving it."""
    result = fr.FirstReading(status="ok")
    result.degraded = True
    result.degraded_reason = fr._cut_degraded_reason(cap=8192)
    payload = result.to_state()
    assert "8192" in payload["degraded_reason"]
