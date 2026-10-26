"""#3254 — the string-shaped ``counter_arguments`` artefact crosses the scrub.

One stored state (1/156 on this seat, measured during #3239) carries
``counter_arguments`` as a list of bare strings — the field's original
``List[str]`` shape, before it grew dicts. The census found NO production
writer that emits it any more: ``_write_counter_argument_to_state``
filters non-dicts before the adder (state_writers.py:608), and
``add_counter_argument`` only ever appends dicts (shared_state.py:1283).
The artefact predates that hardening, so it is repaired at the traversal,
not at a producer.

Before the fix, pass 5 called ``.items()`` on each member and the string
raised ``AttributeError`` — the export aborted for the whole state
(fail-closed, no leak, but the chokepoint died). The shape-tolerant
traversal gives each member the verdict its type measures:

* dict — unchanged behavior: the text-bearing leaves
  (``counter_content``/``generated_text``/``original_argument``) drop,
  the record and its shape survive;
* str — the Dung ``arguments`` verdict: one ``opaque_id`` for the whole
  prose, the slot kept, because the only export readers of the field
  count it (``counter_argument_count``, the appendix's
  « contre_arguments » count — appendix.py:372), and a bare string IS
  the text leaf the dict form drops;
* anything else — rides through: a non-string scalar carries no NL text
  by type, and no scrub rides suspicion (#1664).

Planted by direct field assignment — the honest path for an artefact no
writer emits any more. Born red on the unrepaired scrubber: the call
raises before any assertion runs.
"""

from __future__ import annotations

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.evaluation.opaque_id import opaque_id
from argumentation_analysis.evaluation.sanitize_state import sanitize_state

# Synthetic strings invented for this witness — they appear in no corpus.
_CANARY_STR = "CANARY_3254 a bare-string counter the older pipeline once stored whole"
_CANARY_TEXT = "CANARY_3254_b the counter-content leaf the dict form drops"


@pytest.fixture(autouse=True)
def _synthetic_opaque_salt(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the salt the scrubber demands (#1973) — everything here is fabricated."""
    monkeypatch.setenv("OPAQUE_ID_SALT", "synthetic-test-salt-3254")


def _planted_state() -> UnifiedAnalysisState:
    """The measured artefact's shape beside the current writer's product."""
    state = UnifiedAnalysisState("texte synthetique sans valeur de corpus")
    state.counter_arguments = [
        _CANARY_STR,  # the old List[str] shape (1/156 stored states)
        {  # the adder's product, through the real entry shape
            "id": "ca_1",
            "original_argument": _CANARY_TEXT,
            "counter_content": _CANARY_TEXT,
            "strategy": "direct_refutation",
            "score": 0.6,
        },
    ]
    return state


def _strings(obj: object) -> list[str]:
    found: list[str] = []
    if isinstance(obj, str):
        found.append(obj)
    elif isinstance(obj, dict):
        for key, value in obj.items():
            found.append(str(key))
            found.extend(_strings(value))
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            found.extend(_strings(item))
    return found


class TestTheStringShapeCrosses:
    def test_the_call_does_not_raise_and_the_arity_survives(self) -> None:
        """The chokepoint died on this state before — len() is the export
        reader's metric (counter_argument_count, the appendix count)."""
        out = sanitize_state(_planted_state().get_state_snapshot())
        assert len(out["counter_arguments"]) == 2

    def test_the_bare_string_takes_the_dung_arguments_verdict(self) -> None:
        out = sanitize_state(_planted_state().get_state_snapshot())
        assert out["counter_arguments"][0] == opaque_id(_CANARY_STR)

    def test_the_dict_shape_keeps_its_current_drop(self) -> None:
        out = sanitize_state(_planted_state().get_state_snapshot())
        entry = out["counter_arguments"][1]
        assert "counter_content" not in entry, "the text leaf must drop"
        assert "original_argument" not in entry, "the echoed target must drop"
        assert entry["id"] == "ca_1", "the structural id survives"
        assert entry["strategy"] == "direct_refutation", "closed vocab survives"
        assert entry["score"] == 0.6, "the numeric score survives"

    def test_a_non_text_scalar_rides_through(self) -> None:
        """No scrub rides suspicion (#1664): a number carries no NL text."""
        state = _planted_state()
        state.counter_arguments.append(3)
        out = sanitize_state(state.get_state_snapshot())
        assert out["counter_arguments"][2] == 3

    def test_no_canary_survives_under_the_container(self) -> None:
        out = sanitize_state(_planted_state().get_state_snapshot())
        assert not any("CANARY_3254" in s for s in _strings(out["counter_arguments"]))
