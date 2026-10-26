"""#3242 — three producer surfaces the #1702 oracle could not see.

After #3241, the coordinator's replay measured (on the stored states, after
``sanitize_state``): ``extracts[*].source_quote`` carried 427 verbatim source
spans ≥ 30 chars on 81/81 states; ``fol_shared_signature[*].constants_raw``
1 588 nominative keys (personal names among them) and 1 208 NL values on 79
states, with ``sorts`` republishing the same 1 595 identifiers; ``jtms_
retraction_chain[*].cascaded`` 661 items on 78 states — every one equal to a
raw ``jtms_beliefs`` name, the very names #3241 opacifies one container over.
The #1702 oracle never saw any of the three: its extracts plant carried no
``source_quote``, and the two containers sat in the tolerated set on an
unmeasured "structural bookkeeping" claim.

Reader census (export side — who reads the leaf FROM a sanitized export,
the #3235 rule) and the decision each measurement settles:

* ``extracts.source_quote`` — NO export reader (the render's quality phase
  reads it from the LIVE extraction payload, the measure_1710
  ``arguments[i]`` schema). Decision: **drop** the leaf, keep the record —
  the #3217 ``argument_provenance`` verdict on the extracts axis.
* ``fol_shared_signature.constants_raw`` / ``.sorts`` — ZERO export readers;
  but both halves of the map are nominative (keys = identifiers derived from
  the text, values = NL meanings) and ``sorts`` members ARE the
  ``constants_raw`` keys. Decision: **opacify keys AND values** for
  ``constants_raw`` (the ``contraries`` mapping precedent), **opacify the
  members** for ``sorts`` (the sort names are a closed vocabulary at the
  producer — 'If unsure about sort, use "Thing"', invoke_callables.py:10371)
  — the same deterministic ``opaque_id`` keeps the internal join.
* ``jtms_retraction_chain`` — one export reader,
  ``pattern_mining.JtmsRetractionRateDetector``, reads ``len(chain)`` only;
  ``trigger``/``retracted``/``cascaded`` all carry belief names (jtms_core
  .py:236-242, :422 — the producer is the belief-name vocabulary itself;
  measured: 412/412 cascaded items equal a ``jtms_beliefs`` name on this
  seat). Decision: **opacify the three name leaves** with the same id pass
  4b gives ``jtms_beliefs.name``, so the cross-container join survives;
  ``reason`` stays — a closed formula at the producer
  (``f"directly set to {validity}"``), the ``dung_frameworks.name`` verdict.

Planted through the real producers — ``_write_fact_extraction_to_state`` and
``_write_jtms_to_state`` — and, for the FOL signature, through the exact
product the pass-1 writer assigns (the site is inline in an async LLM path,
invoke_callables.py:10412: ``state.fol_shared_signature[source_id] = {sorts,
predicates, constants_raw, fol_solver}``). Born red on the unrepaired
scrubber: every canary below survives it.
"""

from __future__ import annotations

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.evaluation.opaque_id import opaque_id
from argumentation_analysis.evaluation.sanitize_state import sanitize_state
from argumentation_analysis.orchestration.state_writers import (
    _write_fact_extraction_to_state,
    _write_jtms_to_state,
)

# Synthetic strings invented for this witness — they appear in no corpus.
_CANARY = "CANARY_3242 the orator insists the reform remains the sole viable course"
_CANARY2 = "CANARY_3242_b a rival claim contending the timetable was never achievable"

# Real producer literals — closed vocabularies the scrub must NOT touch.
_SORT_PERSON = "Person"  # the pass-1 sort vocabulary (the prompt's own example)
_SORT_THING = "Thing"  # the prompt's fallback sort (invoke_callables.py:10371)
_JTMS_REASON = "directly set to False"  # jtms_core.py:240, closed formula


@pytest.fixture(autouse=True)
def _synthetic_opaque_salt(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the salt the scrubber demands (#1973) — everything here is fabricated."""
    monkeypatch.setenv("OPAQUE_ID_SALT", "synthetic-test-salt-3242")


def _planted_state() -> UnifiedAnalysisState:
    """One state with a canary in every NL slot the three producers write."""
    state = UnifiedAnalysisState("texte synthetique sans valeur de corpus")

    # --- extracts, through the real _write_fact_extraction_to_state writer --
    # The writer appends ``{"type", "content", "source_quote"}`` straight onto
    # ``state.extracts`` (state_writers.py:1592-1595), bypassing ``add_extract``
    # — which is exactly why the #1702 hand plant (no quote key) was blind to
    # the leaf. A bare-string claim rides along to pin the no-quote shape.
    _write_fact_extraction_to_state(
        {
            "claims": [
                {"text": _CANARY, "source_quote": _CANARY2},
                "a bare claim without a quote",
            ],
            "arguments": [],
        },
        state,
        {},
    )

    # --- fol_shared_signature, the pass-1 writer's exact product shape ------
    # ``constants_raw`` keys = the identifiers derived from the text (the
    # canary stands for a nominative identifier); values = NL meanings.
    # ``sorts`` members = the same identifiers under closed sort names.
    # ``predicates`` (sort-typed signature) and ``fol_solver`` are not this
    # issue's surface and carry no canary — planting NL there would freeze a
    # gap the census never measured (#1664).
    state.fol_shared_signature["src_1"] = {
        "sorts": {
            _SORT_PERSON: [_CANARY],
            _SORT_THING: [_CANARY, _CANARY2],
        },
        "predicates": {"advocate": [_SORT_PERSON, _SORT_THING]},
        "constants_raw": {_CANARY: _CANARY2, _CANARY2: _CANARY},
        "fol_solver": "tweety",
    }

    # --- jtms_beliefs + jtms_retraction_chain, through the real writer ------
    # The belief name must sit in ``jtms_beliefs`` too: the cross-container
    # join (cascaded item == belief name) is the thing the scrub must keep.
    state.add_jtms_belief(_CANARY, True, justifications=[])
    _write_jtms_to_state(
        {
            "beliefs": {},
            "retraction_chain": [
                {
                    "trigger": _CANARY,
                    "retracted": [_CANARY],
                    "cascaded": [_CANARY, _CANARY2],
                    "reason": _JTMS_REASON,
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


class TestExtractSourceQuoteIsDroppedFromTheExport:
    def test_the_verbatim_span_is_dropped_and_the_record_stays(self) -> None:
        out = sanitize_state(_planted_state().get_state_snapshot())
        extracts = out["extracts"]
        assert (
            len(extracts) == 2
        ), "the records must stay (drop the leaf, not the entry)"
        claim = extracts[0]
        assert "source_quote" not in claim, "the verbatim span must be dropped"
        assert "content" not in claim, "the pass-5 content drop predates this fix"
        assert claim["type"] == "claim", "the structural type survives"
        assert extracts[1] == {"type": "claim"}, "the bare claim keeps its shape"

    def test_no_canary_survives_under_the_container(self) -> None:
        out = sanitize_state(_planted_state().get_state_snapshot())
        assert not any("CANARY_3242" in s for s in _strings(out["extracts"]))


class TestFolSharedSignatureAtomsAreOpaque:
    def test_constants_raw_keys_and_values_are_opacified(self) -> None:
        """Both halves are nominative — the argument_labels lesson of #3228."""
        out = sanitize_state(_planted_state().get_state_snapshot())
        entry = out["fol_shared_signature"]["src_1"]
        constants = entry["constants_raw"]
        assert len(constants) == 2, "the map arity must survive every reader"
        assert set(constants) == {
            opaque_id(_CANARY),
            opaque_id(_CANARY2),
        }, "the nominative keys must be opaque, not clear"
        assert set(constants.values()) == {
            opaque_id(_CANARY2),
            opaque_id(_CANARY),
        }, "the NL meanings must be opaque too"

    def test_sorts_members_are_opacified_and_the_names_survive(self) -> None:
        """Sort names are a closed vocabulary at the producer — they stay."""
        out = sanitize_state(_planted_state().get_state_snapshot())
        sorts = out["fol_shared_signature"]["src_1"]["sorts"]
        assert set(sorts) == {
            _SORT_PERSON,
            _SORT_THING,
        }, "the closed sort vocabulary survives (the dung .name verdict)"
        assert sorts[_SORT_PERSON] == [opaque_id(_CANARY)]
        assert sorts[_SORT_THING] == [opaque_id(_CANARY), opaque_id(_CANARY2)]
        assert len(sorts[_SORT_THING]) == 2, "the member arity must survive"

    def test_the_internal_join_survives_the_scrub(self) -> None:
        """sorts members ARE constants_raw keys — same id, same join."""
        out = sanitize_state(_planted_state().get_state_snapshot())
        entry = out["fol_shared_signature"]["src_1"]
        members = {a for atoms in entry["sorts"].values() for a in atoms}
        assert members <= set(
            entry["constants_raw"]
        ), "the constants↔sorts join broke — the ids diverged"

    def test_the_untouched_leaves_ride_through(self) -> None:
        """predicates/fol_solver are not this issue's surface — no canary
        planted there, no scrub applied (#1664: no scrub rides suspicion)."""
        out = sanitize_state(_planted_state().get_state_snapshot())
        entry = out["fol_shared_signature"]["src_1"]
        assert entry["predicates"] == {"advocate": [_SORT_PERSON, _SORT_THING]}
        assert entry["fol_solver"] == "tweety"

    def test_no_canary_survives_under_the_container(self) -> None:
        out = sanitize_state(_planted_state().get_state_snapshot())
        assert not any(
            "CANARY_3242" in s for s in _strings(out["fol_shared_signature"])
        )


class TestRetractionChainKeepsTopologyNotText:
    def test_the_three_name_leaves_are_opacified(self) -> None:
        out = sanitize_state(_planted_state().get_state_snapshot())
        chain = out["jtms_retraction_chain"]
        assert (
            len(chain) == 1
        ), "len(chain) is the export reader's metric — the entries must stay"
        (item,) = chain
        assert item["trigger"] == opaque_id(_CANARY)
        assert item["retracted"] == [opaque_id(_CANARY)]
        assert item["cascaded"] == [opaque_id(_CANARY), opaque_id(_CANARY2)]
        assert len(item["cascaded"]) == 2, "the cascade arity must survive"

    def test_the_cross_container_join_survives(self) -> None:
        """cascaded items are jtms_beliefs names — the same id pass 4b gives
        them, so the join #3241 kept inside jtms_beliefs now spans containers."""
        out = sanitize_state(_planted_state().get_state_snapshot())
        (item,) = out["jtms_retraction_chain"]
        names = {b["name"] for b in out["jtms_beliefs"].values()}
        assert opaque_id(_CANARY) in names, "the planted belief must be there"
        assert set(item["cascaded"]) & names == {
            opaque_id(_CANARY)
        }, "the cascaded↔belief-name join broke — the ids diverged"

    def test_the_closed_formula_reason_stays(self) -> None:
        out = sanitize_state(_planted_state().get_state_snapshot())
        (item,) = out["jtms_retraction_chain"]
        assert item["reason"] == _JTMS_REASON

    def test_no_canary_survives_under_the_container(self) -> None:
        out = sanitize_state(_planted_state().get_state_snapshot())
        assert not any(
            "CANARY_3242" in s for s in _strings(out["jtms_retraction_chain"])
        )
