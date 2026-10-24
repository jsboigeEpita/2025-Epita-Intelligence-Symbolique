# -*- coding: utf-8 -*-
"""#3205 — the counter-arguments section reads the keys a producer writes.

`add_counter_argument` (``shared_state.py``) writes ``{id, original_argument,
counter_content, strategy, score}`` plus ``target_arg_id`` when the echoed
target matched a known argument. The HTML template read ``ca.target_arg`` and
``ca.strength`` — keys no producer writes — and ``ca.strength * 100`` made the
whole report **unrenderable from any real stored state** (measured:
``UndefinedError: 'dict object' has no attribute 'strength'`` on a 19-counter
state whose entries carry exactly the producer's six keys).

These witnesses build the state through the real producer, render, and read
the section: the target comes from the id when it exists and from the stored
target text otherwise, and an unlinked target carries the producer's own
``target_unresolved_reason`` beside it (#2968, the synthesis line's idiom
since #3208). The badge prints the producer's RAW ``score`` — two decimals,
never a percent, never a strength band: ``score=`` has no scale (#3201's
licence, extended to this reader). The old shape (only
``target_arg``/``strength``) must render too, WITHOUT a badge — which is
what proves the template no longer reads those keys.

Synthetic vocabulary only (no corpus content, privacy HARD).
"""

from __future__ import annotations

import html as _html

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.visualization.html_report import render_html_report

_TARGET_TEXT = "Le registre du port consigne chaque marée depuis 1900."
_COUNTER_TEXT = "Les houles d'automne décident des marées, pas le registre."


def _section(html: str) -> str:
    """The counter-arguments section only — the rest of the page is noise."""
    start = html.index("6. Counter-Arguments")
    end = html.index("7. Governance", start)
    return html[start:end]


def _text(section: str) -> str:
    """The section's text, unescaped: the template autoescapes, and a quoted
    apostrophe is printed as ``&#39;`` (that escaping is #2346's subject, not
    this issue's)."""
    return _html.unescape(section)


def _render_snapshot(snapshot: dict) -> str:
    return _section(render_html_report({"state_snapshot": snapshot}))


def _producer_state(**kwargs) -> UnifiedAnalysisState:
    state = UnifiedAnalysisState("Texte de départ synthétique.")
    state.add_counter_argument(
        original_arg=kwargs.pop("original_arg", _TARGET_TEXT),
        counter_content=kwargs.pop("counter_content", _COUNTER_TEXT),
        strategy=kwargs.pop("strategy", "distinction"),
        score=kwargs.pop("score", 0.9),
        **kwargs,
    )
    return state


class TestTheProducerShapeRenders:
    def test_a_linked_counter_shows_its_target_and_its_raw_score(self):
        """Red before the fix: `ca.strength * 100` raised UndefinedError, so
        the page could not be produced at all. Rework pin: the badge carries
        the RAW score — `score 0.90` — never a percent, never a strength
        band (#3201's licence: `score=` has no scale)."""
        state = _producer_state(target_arg_id="arg_alpha")
        section = _render_snapshot(state.get_state_snapshot())
        assert "<code>arg_alpha</code>" in section
        assert "score 0.90" in section
        assert "Strength" not in section
        assert "%" not in section
        assert _COUNTER_TEXT in _text(section)

    def test_an_unlinked_counter_shows_the_target_text_and_its_reason(self):
        """#2968 — a counter with no `target_arg_id` is a measured fact; the
        producer still stores the target text and, when it says why the
        target stayed unresolved, the reason rides beside the text — the
        synthesis line's idiom since #3208."""
        state = _producer_state(
            target_unresolved_reason="cible absente de l'inventaire pesé"
        )
        section = _render_snapshot(state.get_state_snapshot())
        assert _TARGET_TEXT in _text(section)
        assert "score 0.90" in section
        assert "cible absente de l'inventaire pesé" in _text(section)


class TestTheAbsenceStaysVisible:
    def test_a_counter_without_a_score_shows_no_badge(self):
        """No measured score means no badge — never a fabricated number."""
        section = _render_snapshot(
            {
                "counter_arguments": [
                    {
                        "id": "ca_x",
                        "original_argument": _TARGET_TEXT,
                        "counter_content": _COUNTER_TEXT,
                        "strategy": "distinction",
                        "target_arg_id": "arg_alpha",
                    }
                ]
            }
        )
        assert "Strength" not in section
        assert "%" not in section
        assert "score 0" not in section
        assert "<code>arg_alpha</code>" in section

    def test_the_old_phantom_shape_renders_without_inventing_a_target_or_a_score(self):
        """The witness for the removal itself: keys no producer writes are not
        read. Before the fix this entry crashed the render; now it yields no
        target id and no badge, and the counter's content still prints."""
        section = _render_snapshot(
            {
                "counter_arguments": [
                    {
                        "strategy": "distinction",
                        "target_arg": "arg_ghost",
                        "strength": 0.8,
                        "counter_content": _COUNTER_TEXT,
                    }
                ]
            }
        )
        assert "arg_ghost" not in section
        assert "Strength" not in section
        assert "score 0" not in section
        assert _COUNTER_TEXT in _text(section)
