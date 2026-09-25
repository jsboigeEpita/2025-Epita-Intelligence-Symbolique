"""The spectacular HTML report prints state values as text (#2346).

Argument text, justifications, counter-arguments and the narrative come from
the analysis state, which LLM output and the source text feed. The template
used to render with ``autoescape=False``, so a ``<`` in any of them became
markup, and a ``</script>`` in a Dung label closed the graph's script block.
The page is read back with ``html.parser``: what a browser would build, not
a substring of the source.
"""

import json
import re
from html.parser import HTMLParser

from argumentation_analysis.visualization.html_report import render_html_report

PAYLOAD = '<img src=x onerror="alert(1)">'
SCRIPT_BREAK = "</script><script>alert(2)</script>"


class _Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.text = []
        self.scripts = []
        self._in_script = False

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))
        self._in_script = tag == "script"
        if self._in_script:
            self.scripts.append("")

    def handle_endtag(self, tag):
        if tag == "script":
            self._in_script = False

    def handle_data(self, data):
        if self._in_script:
            self.scripts[-1] += data
        else:
            self.text.append(data)


def _read(html):
    page = _Page()
    page.feed(html)
    return page


def _state(**snapshot):
    base = {
        "identified_arguments": {},
        "identified_fallacies": {},
        "argument_quality_scores": {},
        "counter_arguments": [],
        "jtms_beliefs": {},
        "jtms_retraction_chain": [],
        "atms_contexts": [],
        "dung_frameworks": {},
        "governance_decisions": [],
        "narrative_synthesis": "",
    }
    base.update(snapshot)
    return {"source_id": "doc_X", "state_snapshot": base}


def _hostile_state():
    return _state(
        identified_arguments={"arg_1": "short " + PAYLOAD},
        identified_fallacies={
            "f1": {
                "type": "ad_hominem",
                "family": "relevance",
                "source_arg": "arg_1",
                "confidence": 0.9,
                "justification": "because " + PAYLOAD,
            }
        },
        counter_arguments=[
            {
                "strategy": "reductio",
                "target_arg": "arg_1",
                "strength": 0.8,
                "counter_content": "rebuttal " + PAYLOAD,
            }
        ],
        jtms_beliefs={
            "b1": {"status": "IN", "confidence": 0.7, "justification": PAYLOAD}
        },
        atms_contexts=[
            {
                "context_id": "ctx_1",
                "label": "label",
                "status": "consistent",
                "assumptions": [PAYLOAD],
                "environment": [],
            }
        ],
        narrative_synthesis="summary " + PAYLOAD,
    )


def test_state_text_is_printed_as_text_not_markup():
    page = _read(render_html_report(_hostile_state()))

    assert "img" not in [tag for tag, _ in page.tags]
    text = "".join(page.text)
    for printed in (
        "because " + PAYLOAD,
        "rebuttal " + PAYLOAD,
        "summary " + PAYLOAD,
    ):
        assert printed in text
    # JTMS justification and the ATMS assumption chip
    assert text.count(PAYLOAD) >= 5


def test_a_dung_label_cannot_close_the_script_block():
    labels = ["arg_1", SCRIPT_BREAK]
    state = _state(
        dung_frameworks={
            "fw": {
                "arguments": labels,
                "attacks": [{"from": SCRIPT_BREAK, "to": "arg_1"}],
                "extensions": {"grounded": [SCRIPT_BREAK]},
                "status_assignment": {"arg_1": "rejected", SCRIPT_BREAK: "accepted"},
            }
        }
    )
    html = render_html_report(state)
    page = _read(html)

    graph = [s for s in page.scripts if "nodeLabels" in s]
    assert len(graph) == 1
    found = re.search(r"var nodeLabels = (.*);", graph[0])
    assert json.loads(found.group(1)) == labels
    assert "alert(2)" not in "".join(s for s in page.scripts if "nodeLabels" not in s)


def test_a_status_value_is_text_inside_its_badge():
    state = _state(
        dung_frameworks={
            "fw": {
                "arguments": ["arg_1"],
                "attacks": [],
                "extensions": {},
                "status_assignment": {"arg_1": "undecided_" + PAYLOAD},
            }
        }
    )
    page = _read(render_html_report(state))

    assert "img" not in [tag for tag, _ in page.tags]
    assert "undecided " + PAYLOAD in "".join(page.text)


def test_score_helpers_still_render_their_markup():
    """Counter-pendulum: the helpers' own spans are markup, not escaped text."""
    state = _state(
        identified_arguments={"arg_1": "text"},
        argument_quality_scores={"arg_1": {"overall": 0.9, "scores": {"clarte": 0.5}}},
        dung_frameworks={
            "fw": {
                "arguments": ["arg_1"],
                "attacks": [],
                "extensions": {},
                "status_assignment": {"arg_1": "accepted"},
            }
        },
    )
    html = render_html_report(state)
    page = _read(html)

    classes = [attrs.get("class", "") for tag, attrs in page.tags if tag == "span"]
    assert "badge badge-green" in classes  # overall 90 % and the accepted status
    assert '<span class="badge badge-green">90%</span>' in html
    assert "0.50</span>" in html
    assert "&lt;span" not in html
    # a score that is not a number is text, placeholder included
    assert "<td>-</td>" in html


def test_graph_json_keeps_key_order():
    status = {"arg_b": "accepted", "arg_a": "rejected"}
    state = _state(
        dung_frameworks={
            "fw": {
                "arguments": ["arg_b", "arg_a"],
                "attacks": [],
                "extensions": {},
                "status_assignment": status,
            }
        }
    )
    page = _read(render_html_report(state))
    graph = [s for s in page.scripts if "statusMap" in s][0]
    found = re.search(r"var statusMap = (.*);", graph)
    assert found.group(1) == json.dumps(status)
