# -*- coding: utf-8 -*-
"""#3188 — the JTMS cascade section reads the producer's keys.

The HTML report's cascade block rendered each entry from
``cascade.cascade_id`` and ``cascade.downstream_effects`` — keys NO producer
writes. ``JTMS.get_retraction_chain`` documents and returns
``{trigger, retracted, cascaded, reason}`` (``retracted`` is never empty: an
entry is appended only when a True belief is set to non-True, and
``cascaded`` collects the conclusions whose label dropped). On any real state
the section therefore showed an empty id and no effects: what was retracted
and what cascaded never appeared, while trigger and reason made it look
populated — the same family as #3178 cause 3.

The witnesses below render the report from a state whose chain carries the
PRODUCER's shape. Synthetic fixtures only, no corpus text (privacy HARD).
"""

from argumentation_analysis.visualization.html_report import render_html_report

#: One entry exactly as ``get_retraction_chain`` writes it.
_PRODUCER_CHAIN = [
    {
        "trigger": "b_counter_reductio",
        "retracted": ["b_arg_c1"],
        "cascaded": ["b_arg_c2"],
        "reason": "directly set to False",
    },
    {
        "trigger": "b_counter_example",
        "retracted": ["b_arg_p3"],
        "cascaded": [],
        "reason": "directly set to None",
    },
]


def _state(chain=None):
    return {
        "state_snapshot": {
            "jtms_beliefs": {},
            "jtms_retraction_chain": (_PRODUCER_CHAIN if chain is None else chain),
        }
    }


def _cascade_section(html: str) -> str:
    start = html.find("Retraction Cascades")
    assert start != -1, "the report must carry a Retraction Cascades section"
    end = html.find("</div>\n</div>", start)
    return html[start : end if end != -1 else None]


class TestTheCascadeSectionReadsTheProducer:
    """DoD — a witness renders the report from a producer-shaped chain and
    must SEE the retracted beliefs and the cascaded conclusions."""

    def test_every_retracted_belief_appears(self):
        html = render_html_report(_state())
        section = _cascade_section(html)
        assert "b_arg_c1" in section, section
        assert "b_arg_p3" in section, section

    def test_the_cascaded_conclusion_appears(self):
        html = render_html_report(_state())
        assert "b_arg_c2" in _cascade_section(html)

    def test_trigger_and_reason_still_appear(self):
        # They always did — that is what made the phantom shape look
        # populated. They must survive the fix.
        section = _cascade_section(render_html_report(_state()))
        assert "b_counter_reductio" in section
        assert "directly set to False" in section

    def test_an_empty_cascade_renders_without_inventing_content(self):
        # cascaded == []: nothing may be fabricated for the entry — no
        # invented id (the phantom « cascade_N »), no invented transition
        # (the phantom « old → new » effect line).
        html = render_html_report(
            _state(
                [
                    {
                        "trigger": "b_x",
                        "retracted": ["b_y"],
                        "cascaded": [],
                        "reason": "directly set to False",
                    }
                ]
            )
        )
        section = _cascade_section(html)
        assert "b_y" in section
        assert "cascade_" not in section
        assert "→" not in section

    def test_no_chain_no_section(self):
        html = render_html_report(_state([]))
        assert "Retraction Cascades" not in html
