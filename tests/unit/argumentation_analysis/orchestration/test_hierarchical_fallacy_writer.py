"""Tests for the hierarchical-fallacy state writer — D1a (#1167 / Epic #1165).

The spectacular run showed 25 orphan fallacies: the per-argument descent
detected them but they landed in state as ``{type, justification}`` only — no
family/taxonomy_path/target_argument_id — so Acte II could not narrate them.
Root cause: the wide-net ``confirm_fallacy`` tool emits no quote/target, and
while the per-argument harness attached ``source_arg_id`` (a real arg_id from
``state.identified_arguments``) to each fallacy, the writer never used it — it
only tried text-match fallbacks on empty fields.

D1a fix (wiring, not invention): the writer resolves ``target_argument_id``
from ``source_arg_id`` first (when it is a real arg_id in
``identified_arguments``), and the per-argument harness enriches each fallacy
with a grounded ``target_argument`` (= arg_id) + a verbatim
``problematic_quote`` span. These tests pin both ends.
"""

from __future__ import annotations

from types import SimpleNamespace

from argumentation_analysis.orchestration.state_writers import (
    _write_hierarchical_fallacy_to_state,
)


class _FakeState:
    """Minimal state stub mirroring add_fallacy's storage (shared_state.py:110).

    Records each add_fallacy call exactly as the real state does: stores
    family/taxonomy_path/target_argument_id only when non-empty.
    """

    def __init__(self) -> None:
        self.identified_arguments = {
            "arg_1": "Le locuteur attaque la personne plutôt que la thèse.",
            "arg_2": "Un raisonnement causal étayé défend la revendication.",
        }
        self.identified_fallacies: dict = {}
        self._counter = 0

    def add_trace_entry(self, **kwargs):  # noqa: ANN003 — degraded marker path
        pass

    def add_fallacy(
        self,
        fallacy_type: str,
        justification: str,
        target_arg_id=None,
        family: str = "",
        taxonomy_path: str = "",
    ) -> str:
        self._counter += 1
        fid = f"fallacy_{self._counter}"
        entry = {"type": fallacy_type, "justification": justification}
        if family:
            entry["family"] = family
        if taxonomy_path:
            entry["taxonomy_path"] = taxonomy_path
        if target_arg_id:
            entry["target_argument_id"] = target_arg_id
        self.identified_fallacies[fid] = entry
        return fid


def _state_with_args() -> _FakeState:
    return _FakeState()


def test_source_arg_id_resolves_to_target_argument_d1a():
    """A fallacy carrying ``source_arg_id`` (set by the per-arg harness) links
    to that arg_id even with NO target_argument / problematic_quote / family —
    the orphan-fallacy case (D1a #1167)."""
    state = _state_with_args()
    output = {
        "fallacies": [
            {
                "type": "ad hominem circonstanciel",
                "explanation": "Attaque la personne.",
                # The per-arg harness sets source_arg_id = the analyzed arg_id.
                "source_arg_id": "arg_1",
                # No target_argument / problematic_quote / family (wide-net emit).
            }
        ]
    }
    _write_hierarchical_fallacy_to_state(output, state, {})
    assert len(state.identified_fallacies) == 1
    entry = next(iter(state.identified_fallacies.values()))
    assert entry["target_argument_id"] == "arg_1"


def test_unknown_source_arg_id_falls_back_to_text_match_d1a():
    """When source_arg_id is not a real arg_id (e.g. paragraph_1 fallback),
    the writer falls back to text-match on target_argument/quote — does not
    fabricate a link (anti-pendule)."""
    state = _state_with_args()
    output = {
        "fallacies": [
            {
                "type": "ad hominem",
                "explanation": "Attaque.",
                "source_arg_id": "paragraph_1",  # not in identified_arguments
                "target_argument": "Le locuteur attaque la personne plutôt que la thèse.",
            }
        ]
    }
    _write_hierarchical_fallacy_to_state(output, state, {})
    entry = next(iter(state.identified_fallacies.values()))
    assert entry["target_argument_id"] == "arg_1"  # matched via target_argument text


def test_per_arg_enrichment_fields_consumed_by_writer_d1a():
    """End-to-end of the D1a enrichment: a fallacy as emitted by the enriched
    per-arg harness (target_argument = arg_id, problematic_quote = span) is
    resolved by direct ID / quote match."""
    state = _state_with_args()
    output = {
        "fallacies": [
            {
                "type": "appel à l'autorité",
                "explanation": "Autorité invoquée sans expertise.",
                "source_arg_id": "arg_2",
                "target_argument": "arg_2",
                "problematic_quote": "Un raisonnement causal étayé",
                "family": "Appeal to Authority",
                "taxonomy_path": "racine > autorité",
            }
        ]
    }
    _write_hierarchical_fallacy_to_state(output, state, {})
    entry = next(iter(state.identified_fallacies.values()))
    assert entry["target_argument_id"] == "arg_2"
    assert entry["family"] == "Appeal to Authority"
    assert entry["taxonomy_path"] == "racine > autorité"


def test_no_target_link_when_nothing_matchable_d1a():
    """A fallacy with no grounded link and no text-match is stored WITHOUT a
    target_argument_id (honest — never fabricated). family/taxonomy_path still
    surface what was computed."""
    state = _state_with_args()
    output = {
        "fallacies": [
            {
                "type": "pente glissante",
                "explanation": "Enchaînement non causalement étayé.",
                "family": "Slippery Slope",
                "taxonomy_path": "racine > causalité",
            }
        ]
    }
    _write_hierarchical_fallacy_to_state(output, state, {})
    entry = next(iter(state.identified_fallacies.values()))
    assert "target_argument_id" not in entry  # honest: no link
    assert entry["family"] == "Slippery Slope"


# --------------------------------------------------------------------------
# #1633 site 3 — the two lanes must agree on the same payload.
#
# These tests pin the RELATION between the pipeline lane and the conversational
# lane, not the code they happen to share. They feed one identical payload to
# both real writers and compare the outcome, so they survive a rewrite of
# either lane: whoever changes one must keep it in step with the other, or
# these fail. Asserting "both call resolve_fallacy_target_arg_id" would instead
# die the moment either lane is refactored, while proving nothing about
# agreement.
#
# Measured before the fix, on the payload below: the pipeline lane targeted
# arg_3 and partitioned 1 surviving / 2 defeated; the conversational lane
# targeted the sentinel "whole_text" and partitioned 2 surviving / 1 defeated.
# --------------------------------------------------------------------------

ARG_TEXTS = [
    "Le rapport affirme que la mesure est efficace car un expert le dit.",
    "Les données montrent une baisse régulière sur les cinq dernières années.",
    "Si nous n'agissons pas, tout va s'effondrer très rapidement.",
]

# Shaped like the real producers: the per-argument descent stamps both
# source_arg_id and target_argument (each an arg_N); the wide-net whole-text
# pass is stamped source_arg_id="whole_text" by the conversational orchestrator
# itself, and carries the plugin's explicit target_argument_id.
_PER_ARG_FALLACY = {
    "fallacy_type": "Appel à l'autorité",
    "justification": "j1",
    "source_arg_id": "arg_1",
    "target_argument": "arg_1",
}
_WIDE_NET_FALLACY = {
    "fallacy_type": "Appel à la peur",
    "justification": "j2",
    "source_arg_id": "whole_text",
    "wide_net": True,
    "target_argument_id": "arg_3",
}


def _real_state():
    """A real UnifiedAnalysisState — _build_aspic_from_state needs add_aspic_result."""
    from argumentation_analysis.core.shared_state import UnifiedAnalysisState

    state = UnifiedAnalysisState(initial_text="probe")
    for text in ARG_TEXTS:
        state.add_argument(text)
    return state


def _targets(state) -> list:
    return [
        entry.get("target_argument_id") for entry in state.identified_fallacies.values()
    ]


def _run_pipeline_lane(fallacies: list):
    state = _real_state()
    _write_hierarchical_fallacy_to_state(
        {"fallacies": [dict(f) for f in fallacies]}, state, {}
    )
    assert state.identified_fallacies, "pipeline lane registered nothing"
    return state


async def _run_conversational_lane(fallacies: list):
    """Drive the REAL conversational writer, stubbing only the two detectors."""
    from unittest.mock import AsyncMock, patch

    import argumentation_analysis.orchestration.invoke_callables as ic
    from argumentation_analysis.orchestration.conversational_orchestrator import (
        _run_parent_harness_fallback,
    )

    state = _real_state()
    per_arg = [dict(f) for f in fallacies if f.get("source_arg_id") != "whole_text"]
    whole = [dict(f) for f in fallacies if f.get("source_arg_id") == "whole_text"]
    with patch.object(
        ic,
        "_invoke_hierarchical_fallacy_per_argument",
        new=AsyncMock(return_value={"fallacies": per_arg}),
    ), patch.object(
        ic,
        "_invoke_hierarchical_fallacy",
        new=AsyncMock(return_value={"fallacies": whole}),
    ):
        # >500 chars so the wide-net whole-text pass fires.
        await _run_parent_harness_fallback("x" * 600, state)
    assert state.identified_fallacies, "conversational lane registered nothing"
    return state


async def test_both_lanes_assign_the_same_targets_for_one_payload():
    """The relation: identical input must yield identical fallacy→argument links.

    Before the fix the wide-net fallacy landed on arg_3 in one lane and on the
    sentinel "whole_text" in the other.
    """
    payload = [_PER_ARG_FALLACY, _WIDE_NET_FALLACY]
    pipeline = _run_pipeline_lane(payload)
    conversational = await _run_conversational_lane(payload)
    assert sorted(_targets(pipeline)) == sorted(_targets(conversational))
    # Bite: the agreement must be on the grounded ids, not on both being empty.
    assert sorted(_targets(pipeline)) == ["arg_1", "arg_3"]


async def test_both_lanes_yield_the_same_aspic_partition():
    """The consequence the divergence had: survivors/defeated differed (1/2 vs 2/1).

    This is the measurement the issue asked for, pinned so it cannot drift back.
    """
    from argumentation_analysis.orchestration.conversational_orchestrator import (
        _build_aspic_from_state,
    )

    payload = [_PER_ARG_FALLACY, _WIDE_NET_FALLACY]
    from_pipeline = _build_aspic_from_state(_run_pipeline_lane(payload))
    from_conversational = _build_aspic_from_state(
        await _run_conversational_lane(payload)
    )
    assert from_pipeline is not None and from_conversational is not None
    assert from_pipeline["surviving"] == from_conversational["surviving"]
    assert from_pipeline["defeated"] == from_conversational["defeated"]
    # Bite: a partition where nothing is defeated would satisfy equality alone.
    assert from_pipeline["defeated"] == 2


async def test_the_whole_text_sentinel_never_becomes_a_target():
    """The membership guard, isolated.

    A wide-net fallacy whose ONLY reference is the sentinel must resolve to no
    target at all, rather than storing a dangling id that matches no argument.
    """
    orphan = {
        "fallacy_type": "Appel à la peur",
        "justification": "j",
        "source_arg_id": "whole_text",
    }
    for state in (
        _run_pipeline_lane([orphan]),
        await _run_conversational_lane([orphan]),
    ):
        assert _targets(state) == [None]


def test_an_explicit_target_outranks_the_analyzed_argument():
    """The precedence, isolated.

    ``source_arg_id`` names the argument the descent *analyzed*;
    ``target_argument_id`` names the one the plugin says is *attacked*. When
    both are present and real, the attacked one wins.
    """
    from argumentation_analysis.orchestration.state_writers import (
        resolve_fallacy_target_arg_id,
    )

    state = _real_state()
    resolved = resolve_fallacy_target_arg_id(
        state, {"source_arg_id": "arg_1", "target_argument_id": "arg_2"}
    )
    assert resolved == "arg_2"
