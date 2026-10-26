"""#3252 crossing on #3242 — the two sibling keys the #3242 scrub never saw.

#3226 gave each retraction-chain entry the structural cause of every drop:
``cascade_edges`` (jtms_core.py:431 — a list of ``{through_in: [belief
names], conclusion: belief name}``, every name the very belief-name
vocabulary) and, downstream, ``causes`` (invoke_callables.py:3689-3697 —
``{belief name: "cascaded through justification <names>"}``, the values a
free string embedding justification names). #3252 merged those keys while
#3242's scrub was in flight, so the merged scrubber opacifies
``trigger``/``retracted``/``cascaded`` but leaves both siblings clear —
``_opacify_list_values`` returns dicts unchanged, and the atom-map pass
(5h) only walked dict-shaped containers.

Reader census (the #3235 rule, export side): no export reader names a
belief through either key — the export reader of the chain
(``pattern_mining.JtmsRetractionRateDetector``) reads ``len(chain)``, and
the #3226 consumers (narrative_synthesis, html_report,
cross_reference_graph, deep_synthesis) read the LIVE state, not the export.
Decision — the same verdicts #3242 gave the sibling keys:

* ``cascade_edges`` — **opacify the name leaves** (``through_in`` members
  and ``conclusion``) via the 5d nested-item pass, so the edge count and
  each edge's arity survive and the deterministic ``opaque_id`` keeps the
  join with ``jtms_beliefs`` (pass 4b) and the chain's own name leaves;
* ``causes`` — both halves nominative, the ``constants_raw`` verdict:
  **keys and values** through the 5h atom-map pass (``keys_and_values``
  mode), the map arity intact, the belief-name join living in the keys
  (the value is one opaque id for the whole cause string — the embedded
  justification names ride it, they have no join to keep).

Planted through the real ``_write_jtms_to_state`` writer with the exact
product shapes the two producers assign. Born red on the unrepaired
scrubber: both canaries survive it.
"""

from __future__ import annotations

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.evaluation.opaque_id import opaque_id
from argumentation_analysis.evaluation.sanitize_state import sanitize_state
from argumentation_analysis.orchestration.state_writers import _write_jtms_to_state

# Synthetic strings invented for this witness — they appear in no corpus.
_CANARY = "CANARY_3252 the premier maintains the coalition holds without reneging"
_CANARY2 = "CANARY_3252_b a rival claim contending the timetable was never achievable"
_CANARY3 = "CANARY_3252_c the finance clause contradicts the announced surplus"

# Real producer literals — closed vocabularies the scrub must NOT touch.
_JTMS_REASON = "directly set to False"  # jtms_core.py:240, closed formula


@pytest.fixture(autouse=True)
def _synthetic_opaque_salt(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the salt the scrubber demands (#1973) — everything here is fabricated."""
    monkeypatch.setenv("OPAQUE_ID_SALT", "synthetic-test-salt-3252")


def _planted_state() -> UnifiedAnalysisState:
    """One state with a canary in every name slot the two #3226 keys write.

    The chain entry carries the exact shapes of the two producers:
    ``cascade_edges`` as jtms_core.py:431 appends it, ``causes`` as
    invoke_callables.py:3689-3697 builds it (trigger cause + one cascade
    cause per edge). The belief names must sit in ``jtms_beliefs`` too:
    the cross-container join is the thing the scrub must keep.
    """
    state = UnifiedAnalysisState("texte synthetique sans valeur de corpus")
    state.add_jtms_belief(_CANARY, True, justifications=[])
    state.add_jtms_belief(_CANARY2, True, justifications=[])
    _write_jtms_to_state(
        {
            "beliefs": {},
            "retraction_chain": [
                {
                    "trigger": _CANARY,
                    "retracted": [_CANARY],
                    "cascaded": [_CANARY2, _CANARY3],
                    "cascade_edges": [
                        {"through_in": [_CANARY], "conclusion": _CANARY2},
                        {"through_in": [_CANARY, _CANARY2], "conclusion": _CANARY3},
                    ],
                    "reason": _JTMS_REASON,
                    "causes": {
                        _CANARY: "the trigger fell to an identified fallacy",
                        _CANARY2: f"cascaded through justification {_CANARY}",
                        _CANARY3: (
                            f"cascaded through justification {_CANARY} + {_CANARY2}"
                        ),
                    },
                }
            ],
        },
        state,
        {},
    )
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


class TestCascadeEdgesKeepTopologyNotText:
    def test_the_edge_count_and_each_edges_arity_survive(self) -> None:
        out = sanitize_state(_planted_state().get_state_snapshot())
        (item,) = out["jtms_retraction_chain"]
        edges = item["cascade_edges"]
        assert len(edges) == 2, "the edge count is the #3226 reader's topology"
        assert set(edges[0]) == {"through_in", "conclusion"}, "the edge shape stays"
        assert len(edges[1]["through_in"]) == 2, "the through_in arity must survive"

    def test_the_name_leaves_are_opacified(self) -> None:
        out = sanitize_state(_planted_state().get_state_snapshot())
        (item,) = out["jtms_retraction_chain"]
        first, second = item["cascade_edges"]
        assert first["through_in"] == [opaque_id(_CANARY)]
        assert first["conclusion"] == opaque_id(_CANARY2)
        assert second["through_in"] == [opaque_id(_CANARY), opaque_id(_CANARY2)]
        assert second["conclusion"] == opaque_id(_CANARY3)

    def test_the_joins_survive_the_scrub(self) -> None:
        """Every edge name is a belief name: same id as the sibling leaves
        (``cascaded``) and as ``jtms_beliefs.name`` — the two joins #3241
        and #3242 kept must span the new key too."""
        out = sanitize_state(_planted_state().get_state_snapshot())
        (item,) = out["jtms_retraction_chain"]
        edge_names = {e["conclusion"] for e in item["cascade_edges"]}
        edge_names |= {n for e in item["cascade_edges"] for n in e["through_in"]}
        assert edge_names <= set(item["cascaded"]) | {
            item["trigger"]
        }, "the edge↔sibling-leaf join broke — the ids diverged"
        belief_names = {b["name"] for b in out["jtms_beliefs"].values()}
        assert edge_names & belief_names == {
            opaque_id(_CANARY),
            opaque_id(_CANARY2),
        }, "the edge↔belief-name join broke — the ids diverged"

    def test_the_closed_formula_reason_stays(self) -> None:
        out = sanitize_state(_planted_state().get_state_snapshot())
        (item,) = out["jtms_retraction_chain"]
        assert item["reason"] == _JTMS_REASON


class TestCausesKeepTheMapNotTheText:
    def test_keys_and_values_are_opacified_and_the_arity_survives(self) -> None:
        """Both halves nominative — the ``constants_raw`` verdict of #3242."""
        out = sanitize_state(_planted_state().get_state_snapshot())
        (item,) = out["jtms_retraction_chain"]
        causes = item["causes"]
        assert len(causes) == 3, "the map arity must survive every reader"
        assert set(causes) == {
            opaque_id(_CANARY),
            opaque_id(_CANARY2),
            opaque_id(_CANARY3),
        }, "the belief-name keys must be opaque, not clear"
        assert set(causes.values()) == {
            opaque_id("the trigger fell to an identified fallacy"),
            opaque_id(f"cascaded through justification {_CANARY}"),
            opaque_id(f"cascaded through justification {_CANARY} + {_CANARY2}"),
        }, "the free cause strings must be opaque too"

    def test_the_key_join_spans_containers(self) -> None:
        """The keys are belief names: the join with ``jtms_beliefs`` and
        with the chain's own name leaves lives in the KEYS — that is why
        the value can ride one id for the whole string."""
        out = sanitize_state(_planted_state().get_state_snapshot())
        (item,) = out["jtms_retraction_chain"]
        belief_names = {b["name"] for b in out["jtms_beliefs"].values()}
        assert set(item["causes"]) & belief_names == {
            opaque_id(_CANARY),
            opaque_id(_CANARY2),
        }, "the causes↔belief-name join broke — the ids diverged"
        assert set(item["causes"]) <= set(item["cascaded"]) | {
            item["trigger"]
        }, "the causes↔sibling-leaf join broke — the ids diverged"


class TestNoCanarySurvives:
    def test_no_canary_survives_under_the_container(self) -> None:
        out = sanitize_state(_planted_state().get_state_snapshot())
        assert not any(
            "CANARY_3252" in s for s in _strings(out["jtms_retraction_chain"])
        )
