"""#1676 — pin the third hop: what the projection carries vs what the render names.

#1624 pinned the relation between the two reading surfaces (prose / annexe).
This module pins the hop one step DOWNSTREAM: between what the *projection*
carries (``state_adapter._STATE_KEYS`` → ``state_to_appendix_mapping``) and
what the *render* names (the keys named by a rendered row of
``appendix._provenance_counts``).

Three keys were measured on ``main`` (``ca40f6d2``, unchanged by #1675) to
traverse the projection without any rendered line naming them::

    _STATE_KEYS  \\  {keys named by a rendered row}
      = source_metadata, stakes_and_stakeholders, workflow_results

Before this guard, a future addition to ``_STATE_KEYS`` without a
corresponding rendered row would pass silently — the projection would carry
it to the opt-in full-state dump, and the default render would stay mute.
The point of this module is that such an addition *fails* instead of drifting.

The guard does NOT prescribe equality. An explicit, key-by-key justified
``_UNRENDERED`` frozenset carries the legitimate exceptions — the whole
content of the issue is that the three cases are distinct and none is an
oversight.

Anti-pendule (from the issue body):

* Do NOT add three rows "to close the gap" — a row counting metadata fields
  informs nobody (``source_metadata``) and ``workflow_results`` is a generic
  bag. Only ``stakes_and_stakeholders`` earns a row (the Acte I framing
  mobilises it, a live writer fills it — #1604 R751).
* Do NOT remove the three keys from ``_STATE_KEYS`` to make the guard
  trivially green: the opt-in dump is their only traceability today.
* Do NOT mutualise a constant between ``state_adapter`` and ``appendix``: the
  file-disjoint wiring is deliberate (``state_adapter.py`` header l.6-8); the
  accord is carried by THIS test (same shape as #1624).

Falsifiability — two substitutions with disjoint kill-sets:

* **Sub A** — add a bogus key ``"future_axis"`` to ``state_adapter._STATE_KEYS``
  without a row: ``test_projection_render_relation_is_pinned`` fails (the new
  key is neither in the rendered set nor in ``_UNRENDERED``).
  ``test_every_unrendered_key_is_justified`` survives (it only checks the
  current ``_UNRENDERED`` explains itself). Kill-set = {relation}.
* **Sub B** — remove the ``enjeux`` row from ``_provenance_counts`` (revert the
  ``stakes_and_stakeholders`` attestation): ``stakes_and_stakeholders`` rejoins
  the unrendered set but is NOT in ``_UNRENDERED``, so
  ``test_projection_render_relation_is_pinned`` fails.
  ``test_stakes_axis_is_attested_by_cardinality`` also fails. Kill-set =
  {relation, stakes-canary}.

The two substitutions kill different tests, so neither assertion is vacuous.
"""

from __future__ import annotations

from typing import Any, Dict

from argumentation_analysis.reporting.restitution.appendix import (
    _provenance_counts,
    _stakes_summary,
    render_appendix,
)
from argumentation_analysis.reporting.restitution.state_adapter import (
    _STATE_KEYS,
    state_to_appendix_mapping,
)


def _full_state() -> Dict[str, Any]:
    """A projection where every key in ``_STATE_KEYS`` carries something.

    Synthetic atoms only (privacy HARD — no corpus tokens). Shapes match the
    writers' output so the cardinality helpers exercise their real branches.
    """
    return {
        "identified_arguments": {"a1": {}},
        "identified_fallacies": {"f1": {}},
        "counter_arguments": [{"strategy": "distinction"}],
        "argument_quality_scores": {"a1": 0.7},
        "fol_analysis_results": [{"consistent": True, "message": "ok"}],
        "propositional_analysis_results": [{"consistent": True}],
        "modal_analysis_results": [{"consistent": True}],
        "dung_frameworks": {"dung_1": {"name": "dung_arbitration"}},
        "aspic_results": [{"id": "aspic_1", "extensions": [["a"]]}],
        "belief_revision_results": [{"method": "dalal"}],
        "bipolar_results": [{"supports": [["a", "b"]]}],
        "debate_transcripts": [{"turns": []}],
        "governance_decisions": [{"method": "borda"}],
        "structured_arg_status": {
            "aspic_plus_reasoning": {
                "capability": "aspic_plus_reasoning",
                "status": "evaluated",
                "degraded": False,
                "reason": "",
                "extension_count": 1,
            }
        },
        "narrative_synthesis": "synthèse",
        "final_conclusion": "conclusion",
        "formal_synthesis_reports": [{"axis": "fol"}],
        # #1676 — the three keys the third-hop guard reasons about.
        "stakes_and_stakeholders": {
            "stakes": ["enjeu_A", "enjeu_B"],
            "stakeholders": ["partie_A"],
            "rhetorical_register": "",
            "discursive_arena": "",
        },
        "source_metadata": {"genre": "politique", "speaker_role": "orateur"},
        "workflow_results": {"total_duration_ms": 1000},
    }


# Keys carried by the projection (``_STATE_KEYS``) that NO rendered row of
# ``_provenance_counts`` names. Each is a deliberate decision documented at its
# site in ``state_adapter.py`` (#1676). The guard below asserts this set is
# EXACTLY the projection-minus-render difference, so a future addition to
# ``_STATE_KEYS`` without a row must either land here (with its justification)
# or fail the relation test.
#
# ``stakes_and_stakeholders`` is NOT here: it earns the ``enjeux`` row (Acte I
# framing mobilises it, live writer fills it — #1604 R751).
#
# ``source_metadata`` — privacy HARD. The values are nominative (a ``title`` is
# a source name per CLAUDE.md privacy); a count of metadata fields informs
# nobody. The prose reads it for the Acte I framing; values are opacified on
# the export boundary (``sanitize_state._OPAQUE_DICT_VALUES``).
#
# ``workflow_results`` — distinct case. Neither the prose nor any annexe line
# reads it: a generic bag of phase/workflow results with no informative count.
# Other surfaces read it (html_report durations, multi_format_exporter); the
# restitution does not.
_UNRENDERED = frozenset({"source_metadata", "workflow_results"})


def _rendered_keys() -> set[str]:
    """State keys named by a rendered row, in projection terms.

    ``_provenance_counts`` keys are dimension labels, not state keys. Each
    rendered dimension declares its state key(s) in ``_MOBILISATION``; the
    ``enjeux`` row added by #1676 names ``stakes_and_stakeholders``. Inverting
    that mapping gives the set of state keys the render attests.
    """
    # Inline rather than importing _MOBILISATION: the projection→render
    # relation is the claim under test, and reading the render's own declaration
    # keeps the guard honest if _MOBILISATION drifts from _provenance_counts.
    from argumentation_analysis.reporting.restitution.appendix import _MOBILISATION

    keys: set[str] = set()
    for _dim, (state_keys, _kind, _site) in _MOBILISATION.items():
        keys.update(state_keys)
    return keys


# ---------------------------------------------------------------------------
# DoD item 1 — the relation between projection and render is pinned
# ---------------------------------------------------------------------------


def test_projection_render_relation_is_pinned() -> None:
    """Every key in ``_STATE_KEYS`` is either rendered or explicitly justified.

    The difference ``_STATE_KEYS - rendered`` must equal ``_UNRENDERED``
    exactly. A future key added to the projection without a row lands in the
    difference; unless it is added to ``_UNRENDERED`` with its justification,
    this assertion fails — the drift becomes a deliberate decision instead of
    passing silently.
    """
    projected = set(_STATE_KEYS)
    rendered = _rendered_keys()
    unrendered = projected - rendered
    assert unrendered == _UNRENDERED, (
        "The projection carries keys the render never names, beyond the "
        f"explicitly justified set: {unrendered - _UNRENDERED} (unexpected) "
        f"and missing from the justified set: {_UNRENDERED - unrendered} "
        "(a key dropped from _STATE_KEYS or newly rendered)."
    )


def test_every_unrendered_key_is_justified() -> None:
    """Each key in ``_UNRENDERED`` is actually carried by the projection.

    A stale entry (a key removed from ``_STATE_KEYS`` or newly rendered) would
    make ``_UNRENDERED`` lie about the live decision. This is the mirror of the
    relation test: it pins the justified set against reality, not just against
    the difference.
    """
    projected = set(_STATE_KEYS)
    stale = _UNRENDERED - projected
    assert not stale, (
        f"_UNRENDERED lists keys the projection no longer carries: {stale}. "
        "Remove them or re-add them to _STATE_KEYS."
    )


# ---------------------------------------------------------------------------
# DoD item 2 — stakes_and_stakeholders earns the row (cardinality, not content)
# ---------------------------------------------------------------------------


class TestStakesAxisIsAttested:
    """``stakes_and_stakeholders`` is mobilised by the Acte I framing and has a
    live writer, so the annexe attests it — by cardinality only (privacy)."""

    def test_stakes_axis_is_attested_by_cardinality(self) -> None:
        counts = _provenance_counts(_full_state())
        assert "enjeux" in counts
        # Cardinality surfaced, names never.
        assert "2 enjeux" in counts["enjeux"]
        assert "1 partie prenante" in counts["enjeux"]

    def test_empty_stakes_is_indisponible(self) -> None:
        # An empty stakes container reads as "indisponible", not as a fabricated
        # count — the honest absence (#1019).
        assert _stakes_summary(None) == "indisponible"
        assert _stakes_summary({}) == "indisponible"
        assert _provenance_counts({})["enjeux"] == "indisponible"

    def test_singular_plural_forms(self) -> None:
        # The cardinality helper distinguishes 1 vs many — "1 enjeu" not "1 enjeux".
        # French pluralisation: 0 takes the plural ("0 parties prenantes").
        assert _stakes_summary({"stakes": ["x"], "stakeholders": []}) == (
            "1 enjeu, 0 parties prenantes"
        )
        assert (
            _stakes_summary({"stakes": ["x", "y"], "stakeholders": ["a", "b"]})
            == "2 enjeux, 2 parties prenantes"
        )

    def test_stakes_names_never_leak(self) -> None:
        # Privacy HARD: the names are nominative and must stay in the state.
        # A pure-NL sentinel (no entity structure) so the leak keys strip cannot
        # mask a miss — a leak here is attributable to _stakes_summary alone.
        state = _full_state()
        state["stakes_and_stakeholders"] = {
            "stakes": ["CANARY_TOKEN_STAKE"],
            "stakeholders": ["CANARY_TOKEN_HOLDER"],
            "rhetorical_register": "",
            "discursive_arena": "",
        }
        out = render_appendix(state)
        assert "CANARY_TOKEN_STAKE" not in out
        assert "CANARY_TOKEN_HOLDER" not in out
        assert "| enjeux |" in out

    def test_stakes_axis_survives_the_projection(self) -> None:
        # The #1620 trap (projection drops the key → the reader is inert in
        # production while passing unit tests on a raw dict). The stakes key
        # must be carried by _STATE_KEYS so the annexe reader can see it.
        assert "stakes_and_stakeholders" in set(_STATE_KEYS)


# ---------------------------------------------------------------------------
# DoD item 3 — source_metadata is NOT attested (privacy HARD decision)
# ---------------------------------------------------------------------------


class TestSourceMetadataPrivacyDecision:
    """``source_metadata`` is carried by the projection (opt-in dump
    traceability) but deliberately NOT rendered — its values are nominative
    (a ``title`` is a source name per CLAUDE.md privacy), and a count of
    metadata fields informs nobody."""

    def test_source_metadata_not_in_rendered_rows(self) -> None:
        counts = _provenance_counts(_full_state())
        # No dimension label surfaces the metadata content.
        assert "source_metadata" not in counts
        # No dimension's VALUE echoes a nominative metadata value.
        for value in counts.values():
            assert (
                "politique" not in str(value).lower()
                or "orateur" not in str(value).lower()
            )

    def test_source_metadata_carried_by_projection(self) -> None:
        # The key stays in _STATE_KEYS so the opt-in full-state dump keeps it
        # traceable (anti-pendule: do not remove to make the guard trivially green).
        assert "source_metadata" in set(_STATE_KEYS)
        mapping = state_to_appendix_mapping(_full_state())
        assert "source_metadata" in mapping

    def test_source_metadata_values_never_leak_in_default_render(self) -> None:
        # The default render (include_full_state_json=False) must not surface
        # nominative metadata even when the projection carries it.
        state = _full_state()
        state["source_metadata"] = {
            "title": "CANARY_TITLE_TOKEN",
            "speaker": "CANARY_SPEAKER_TOKEN",
        }
        out = render_appendix(state, include_full_state_json=False)
        assert "CANARY_TITLE_TOKEN" not in out
        assert "CANARY_SPEAKER_TOKEN" not in out
