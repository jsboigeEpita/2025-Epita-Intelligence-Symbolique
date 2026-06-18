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
