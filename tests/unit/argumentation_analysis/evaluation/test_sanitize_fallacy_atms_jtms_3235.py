"""#3235 — three containers still carry argument text through the scrubber.

After #3227, #3232 and #3233, the coordinator's probe measured (80 stored
states, after ``sanitize_state``): ``identified_fallacies.*.problematic_quote``
carried 1 267 verbatim argument spans on 74 states; ``atms_contexts`` 1 345
matching strings on 78; ``jtms_beliefs`` 121 argument texts (9 251 NL strings,
mostly ``justifications[*].in_list[*]``). The #1702 oracle never saw the first
(its canary planted the container by hand, without the key) and froze the
other two under an issue that closed on 13/08.

Reader census (export side — who reads the key FROM a sanitized export):
* ``problematic_quote`` — NO reader. The fallacy→argument join is
  ``target_argument_id``, resolved at write time (``resolve_fallacy_target_
  arg_id``) and already on the entry; the text-match fallback joins the LIVE
  payload before the writer runs. Decision: **drop** (#3217's ``source_quote``
  verdict on the fallacy axis).
* ``atms_contexts`` — one reader: ``pattern_mining.AtmsBranchingDetector``
  reads ``len(assumptions)`` per context and ``coherent``. Decision: keep
  exactly that — **opacify ``assumptions``** (the count must survive),
  **drop ``derivable_beliefs``/``contradicting_beliefs``** (no reader; the
  producer already writes ``derivation_count``/``contradiction_count`` ints,
  which survive), and leave ``label`` untouched: it is a CLOSED vocabulary at
  the producer (six literals in ``_generate_hypotheses``; 4 distinct values,
  0 argument-text matches, measured on the 49 local stored states) — the
  ``dung_frameworks.name`` verdict.
* ``jtms_beliefs`` — export readers read counts only (the ``justification``
  singular read in ``JtmsRetractionRateDetector`` touches a key no producer
  writes). The belief name is ``{unit_id}:{text[:66]}`` and the justification
  ``in_list`` entries repeat it verbatim (measured: 122 exact overlaps) — a
  same-text join, so **opacify** ``name`` and the ``in_list``/``out_list``
  leaves rather than drop: the same deterministic ``opaque_id`` keeps the
  linkage and the justification topology.

Measured on this seat's 49 stored states (before → the coordinator's three
columns): problematic_quote 48/557/557 · assumptions 48/790/790 · derivable
26/207/4 · contradicting 7/21/0 · label 48/96/0 (closed vocab) · jtms name
48/1 842/29 · jtms justifications 48/3 704/53.

Planted through the real producers — ``add_fallacy``, ``_write_atms_to_state``
and ``_write_jtms_to_state`` — never a hand-built dict. Born red on the
unrepaired scrubber: every canary below survives it.
"""

from __future__ import annotations

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.evaluation.sanitize_state import sanitize_state
from argumentation_analysis.orchestration.state_writers import (
    _write_atms_to_state,
    _write_jtms_to_state,
)

# Synthetic strings invented for this witness — they appear in no corpus.
_CANARY = "CANARY_3235 the orator insists the reform remains the sole viable course"
_CANARY2 = "CANARY_3235_b a rival claim contending the timetable was never achievable"

_ATMS_LABEL = "Skeptical: single argument only"  # a real producer literal


@pytest.fixture(autouse=True)
def _synthetic_opaque_salt(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the salt the scrubber demands (#1973) — everything here is fabricated."""
    monkeypatch.setenv("OPAQUE_ID_SALT", "synthetic-test-salt-3235")


def _planted_state() -> UnifiedAnalysisState:
    """One state with a canary in every NL slot the three producers write."""
    state = UnifiedAnalysisState("texte synthetique sans valeur de corpus")

    # --- identified_fallacies, through the real add_fallacy writer ----------
    # ``arg_1`` must exist first: the writer guards target membership.
    state.identified_arguments["arg_1"] = _CANARY2
    state.add_fallacy(
        fallacy_type="ad_hominem",
        justification=_CANARY,
        target_arg_id="arg_1",
        family="relevance",
        confidence=0.9,
        problematic_quote=_CANARY2,
    )

    # --- atms_contexts, through the real _write_atms_to_state writer --------
    # ``environments`` feeds the sibling JTMS beliefs the same writer adds:
    # the environment [[_CANARY]] becomes the bare-string justification
    # "assumption_env:['CANARY_3235 …']" — the ATMS-produced string shape
    # that rides the jtms_beliefs container next to the dict justifications.
    _write_atms_to_state(
        {
            "environments": {
                "node_a": {"is_assumption": True, "environments": [[_CANARY]]}
            },
            "atms_contexts": [
                {
                    "hypothesis_id": "ctx_1",
                    "label": _ATMS_LABEL,
                    "assumptions": [_CANARY, _CANARY2],
                    "coherent": False,
                    "derivable_beliefs": [_CANARY2],
                    "contradicting_beliefs": [_CANARY],
                    "derivation_count": 1,
                    "contradiction_count": 1,
                }
            ],
        },
        state,
        {},
    )

    # --- jtms_beliefs, through the real _write_jtms_to_state writer ---------
    # The JTMS producer serialises justifications as dicts
    # ({"in_list": [name[:40]...], "out_list": [...]}, invoke_callables.py) —
    # the bare-string shape is the ATMS writer's, planted above.
    _write_jtms_to_state(
        {
            "beliefs": {
                _CANARY: {
                    "valid": True,
                    "justifications": [{"in_list": [_CANARY2], "out_list": []}],
                },
            },
            "retraction_chain": [],
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


class TestProblematicQuoteIsDroppedFromTheExport:
    def test_no_canary_survives_and_the_structural_join_stays(self) -> None:
        out = sanitize_state(_planted_state().get_state_snapshot())
        fallacies = out["identified_fallacies"]
        assert fallacies, "the container vanished — the entry must stay"
        (entry,) = fallacies.values()
        assert "problematic_quote" not in entry, "the verbatim span must be dropped"
        assert "justification" not in entry, "the pass-4 drop predates this fix"
        assert not any(
            "CANARY_3235" in s for s in _strings(fallacies)
        ), "a canary survived under identified_fallacies"
        # The join the export actually carries: the id, not the quote.
        assert entry["type"] == "ad_hominem"
        assert entry["target_argument_id"] == "arg_1"
        assert entry["confidence"] == 0.9


class TestAtmsContextsKeepsExactlyWhatTheExportReaderReads:
    def test_assumptions_are_opacified_not_emptied(self) -> None:
        """The reader counts assumptions per context — the arity must survive."""
        out = sanitize_state(_planted_state().get_state_snapshot())
        (ctx,) = out["atms_contexts"]
        assumptions = ctx["assumptions"]
        assert len(assumptions) == 2, "len(assumptions) is the reader's metric"
        assert all(
            "CANARY_3235" not in a for a in assumptions
        ), "an assumption atom survived verbatim"
        assert ctx["coherent"] is False, "the reader's second field"

    def test_the_unread_belief_lists_are_dropped_and_their_counts_stay(self) -> None:
        """No export reader names these lists; the producer's ints carry the signal."""
        out = sanitize_state(_planted_state().get_state_snapshot())
        (ctx,) = out["atms_contexts"]
        assert "derivable_beliefs" not in ctx
        assert "contradicting_beliefs" not in ctx
        assert ctx["derivation_count"] == 1
        assert ctx["contradiction_count"] == 1
        assert ctx["hypothesis_id"] == "ctx_1"

    def test_the_closed_vocabulary_label_stays(self) -> None:
        """label is six literals at the producer — the dung .name verdict."""
        out = sanitize_state(_planted_state().get_state_snapshot())
        (ctx,) = out["atms_contexts"]
        assert ctx["label"] == _ATMS_LABEL

    def test_no_canary_survives_under_the_container(self) -> None:
        out = sanitize_state(_planted_state().get_state_snapshot())
        assert not any("CANARY_3235" in s for s in _strings(out["atms_contexts"]))


class TestJtmsBeliefsKeepTopologyNotText:
    def test_the_dict_justification_leaves_are_opacified(self) -> None:
        out = sanitize_state(_planted_state().get_state_snapshot())
        # The JTMS-phase entry is the one whose justifications are dicts; the
        # ATMS writer's entries carry bare strings.
        entry = next(
            v
            for v in out["jtms_beliefs"].values()
            if isinstance(v.get("justifications", [None])[0], dict)
        )
        (justification,) = entry["justifications"]
        assert len(justification["in_list"]) == 1, "the premise arity must survive"
        assert "CANARY_3235" not in justification["in_list"][0]
        assert entry["valid"] is True

    def test_the_name_and_the_string_justifications_are_opacified(self) -> None:
        """name is {unit_id}:{text[:66]} — nominative; the ATMS string
        justifications embed the same atoms. Both must be opaque, not gone:
        the name↔in_list linkage is a measured join (122 exact overlaps)."""
        out = sanitize_state(_planted_state().get_state_snapshot())
        beliefs = out["jtms_beliefs"]
        assert beliefs, "the container vanished — the entries must stay"
        for belief in beliefs.values():
            name = belief.get("name")
            assert isinstance(name, str) and name, "the belief identity stays (opaque)"
            assert "CANARY_3235" not in name
        assert not any("CANARY_3235" in s for s in _strings(beliefs)), (
            "a canary survived under jtms_beliefs (name, in_list or the "
            "assumption_env string justifications)"
        )

    def test_the_atms_written_string_justification_is_opacified(self) -> None:
        """The ATMS writer's ``assumption_env:[…]`` strings are the second
        real justification shape — they ride the same container."""
        out = sanitize_state(_planted_state().get_state_snapshot())
        atms_entries = [
            v
            for v in out["jtms_beliefs"].values()
            if any(isinstance(j, str) for j in v.get("justifications", []))
        ]
        assert atms_entries, "the ATMS-written beliefs must be in the container"
        assert not any("CANARY_3235" in s for s in _strings(atms_entries))
