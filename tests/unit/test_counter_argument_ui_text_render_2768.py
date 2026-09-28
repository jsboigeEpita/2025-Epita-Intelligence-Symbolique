"""#2768 — the counter-argument student UI renders report values as text.

The report returned by ``/generate`` can quote the submitted argument. The
template used to interpolate ``summary`` and the fallacy fields into
``innerHTML``, so a submitted HTML payload was parsed and executed in the page.

The test runs the template's own inline script under Node with a minimal DOM
stub. The stub records every ``innerHTML`` write, then
``displayDynamicResults`` is called with an entirely synthetic HTML payload.
The payload must reach the page only through ``textContent``.
"""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

_TEMPLATE = (
    Path(__file__).resolve().parents[2]
    / "2.3.3-generation-contre-argument"
    / "counter_agent"
    / "ui"
    / "templates"
    / "index.html"
)

# Synthetic payload: nothing here comes from the corpus.
_PAYLOAD = '<img src=x onerror="window.__pwned_2768=1">'

_HARNESS = r"""
const writes = [];
function makeEl(tag) {
  const el = {
    tagName: tag, children: [], className: '', style: {}, _text: '', _html: '',
    appendChild(c) { this.children.push(c); return c; },
    addEventListener() {}, setAttribute() {}, getAttribute() { return null; },
  };
  Object.defineProperty(el, 'innerHTML', {
    get() { return el._html; },
    set(v) { writes.push(String(v)); el._html = String(v); el._text = ''; el.children = []; },
  });
  Object.defineProperty(el, 'textContent', {
    get() { return el._text + el.children.map((c) => c.textContent).join(''); },
    set(v) { el._text = String(v); el._html = ''; el.children = []; },
  });
  return el;
}
const els = {};
global.window = global;
global.document = {
  getElementById(id) { return els[id] || (els[id] = makeEl('div#' + id)); },
  createElement: makeEl,
  createTextNode(t) { return { textContent: String(t) }; },
  querySelectorAll() { return []; },
  addEventListener() {},
};
global.fetch = () => new Promise(() => {});
global.alert = () => {};
(0, eval)(SCRIPT);
displayDynamicResults(DATA);
const texts = {};
for (const [id, el] of Object.entries(els)) texts[id] = el.textContent;
process.stdout.write(JSON.stringify({ writes, texts }));
"""


def _inline_script() -> str:
    html = _TEMPLATE.read_text(encoding="utf-8")
    scripts = re.findall(r"<script>(.*?)</script>", html, flags=re.S)
    assert len(scripts) == 1, f"expected one inline script, found {len(scripts)}"
    return scripts[0]


def _render(data: dict) -> dict:
    node = shutil.which("node")
    if node is None:
        if os.environ.get("CI"):
            pytest.fail("node is provisioned in the CI job (setup-node); it is missing")
        pytest.skip("node is not installed on this seat")
    js = _HARNESS.replace("SCRIPT", json.dumps(_inline_script())).replace(
        "DATA", json.dumps(data)
    )
    proc = subprocess.run(
        [node, "-"],
        input=js,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


@pytest.fixture(scope="module")
def rendered() -> dict:
    return _render(
        {
            "summary": _PAYLOAD,
            "details": [
                {
                    "fallacy_name": _PAYLOAD,
                    "validation_score": _PAYLOAD,
                    "validation_justification": _PAYLOAD,
                }
            ],
        }
    )


def test_report_values_never_reach_inner_html(rendered):
    leaked = [w for w in rendered["writes"] if _PAYLOAD in w]
    assert leaked == []


def test_summary_is_rendered_literally(rendered):
    assert _PAYLOAD in rendered["texts"]["counter-argument-text"]


def test_fallacy_fields_are_rendered_literally(rendered):
    # name, score and justification: three literal copies in the card.
    assert rendered["texts"]["scores-container"].count(_PAYLOAD) == 3


def test_empty_report_keeps_the_placeholders():
    out = _render({"summary": "", "details": []})
    assert "Aucun résumé fourni." in out["texts"]["counter-argument-text"]
    assert any("Aucun détail de sophisme" in w for w in out["writes"])
