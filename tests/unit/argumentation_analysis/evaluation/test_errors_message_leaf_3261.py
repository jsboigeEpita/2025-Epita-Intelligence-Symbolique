# -*- coding: utf-8 -*-
"""#3261 — the ``errors`` container's ``message`` leaf never leaves the machine.

The coordinator measured 9 NL leaves ≥ 30 chars surviving ``sanitize_state``
under the top-level ``errors`` container (85 stored states on ai-01), every
sampled prefix technical ("stakes extraction parse_error: JSONDecodeError:
Expecting ',' delimiter: line 1 ..."). No table named the container and the
#1702 guard never planted it (``errors`` is written by error handlers, not the
analysis adders the canary state uses), so the empty frozen baseline said
nothing about it.

Producer census (this change): ``log_error`` (shared_state.py:584) is the only
writer, with exactly three callers —

* ``invoke_callables.py:14581-14589``: ``"stakes extraction {status}:
  {ExceptionType}: {e}"`` — the stakes extractor's ``result["error"]``
  (stakes_extractor.py:198/202). The ``parse_error`` leg is a
  ``JSONDecodeError``/``KeyError``/``IndexError`` string, a position, never
  the document; the model output goes to ``stakes``/``stakeholders``, already
  scrubbed. But the ``llm_error`` leg is ``str(e)`` of a foreign API
  exception, whose vocabulary no table can promise closed — the reason the
  leaf is not kept even though every measured sample read technical.
* ``workflow_dsl.py:1218``: ``str(result.error)`` (the phase-error reason).
* ``sherlock_modern_orchestrator.py:131``: ``str(exception)``.

Export readers: one — the synthesis snapshot counts ``len(errors)`` as
``error_count`` (shared_state.py:658); nothing reads ``message``.

Decision (the #3239 gesture on the errors axis): drop the leaf, keep the
record — ``id``/``agent_name``/``timestamp`` and the arity survive. This
witness is born red on the pre-#3261 scrubber, and the substitution control
proves the drop comes from the named table entry, not a catch-all.
"""

from __future__ import annotations

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.evaluation import sanitize_state as _sanitize_mod
from argumentation_analysis.evaluation.sanitize_state import sanitize_state

CANARY = (
    "CANARY_3261 the speaker warns that the coalition will withdraw its "
    "support unless the undisclosed cost of the measure is published first"
)

# The other leaf is deliberately technical-looking: the drop is uniform over
# the leaf, not a ≥30-chars filter that would keep short provider strings.
TECHNICAL = "stakes extraction parse_error: JSONDecodeError: Expecting ',' delimiter: line 1 column 42 (char 41)"


def _canaried_state() -> UnifiedAnalysisState:
    """Two errors through the real writer — the NL canary and a technical one."""
    s = UnifiedAnalysisState("source_3261")
    s.log_error("StakesExtractor", CANARY)
    s.log_error("StakesExtractor", TECHNICAL)
    return s


def test_the_errors_message_leaf_is_dropped_and_the_record_kept():
    s = _canaried_state()

    # measurement before verdict: the raw plant carries both leaves
    assert [e["message"] for e in s.errors] == [CANARY, TECHNICAL]

    out = sanitize_state(s.get_state_snapshot())

    # the record survives whole: arity, id, agent_name, timestamp
    errors = out.get("errors")
    assert isinstance(errors, list) and len(errors) == 2
    for entry in errors:
        assert "message" not in entry
        assert entry["agent_name"] == "StakesExtractor"
        assert isinstance(entry["id"], str) and entry["id"].startswith("error")

    # and neither leaf survives — not the canary, not the technical string
    rendered = repr(errors) + repr(out)
    assert "CANARY_3261" not in rendered
    assert "JSONDecodeError" not in rendered


def test_the_drop_is_the_named_table_entry(monkeypatch):
    """Substitution control: empty the ``errors`` row and the leaf comes back."""
    stripped = {
        k: set(v) for k, v in _sanitize_mod._TEXT_STRIP_LISTS.items() if k != "errors"
    }
    monkeypatch.setattr(_sanitize_mod, "_TEXT_STRIP_LISTS", stripped)

    out = sanitize_state(_canaried_state().get_state_snapshot())

    assert [e.get("message") for e in out["errors"]] == [CANARY, TECHNICAL]
