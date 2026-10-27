"""#3249 — the five tolerated containers, decided by measurement.

The #3242 census (issue comment 6399207162) left five tolerated entries of the
#1702 guard each carrying measured NL. This witness pins the three scrubbed
decisions; the two documented closed vocabularies
(``restitution_acts_degraded``, ``workflow_results``) carry their measurement
beside the tolerated entry in the guard — nothing here scrubs them, and the
census numbers live in the guard's comment, not in a test that would restate
them.

Decisions (census in the PR body):

- ``structured_arg_status[*].reason`` — DROP the leaf, keep the record. The
  record is ``{capability, status, degraded, reason, extension_count}``
  (``add_structured_arg_status``, shared_state.py:1846). ``status`` is a
  closed vocabulary at every producer (measured on the stored states: 5
  literals); ``reason`` is free-form producer prose whose ``unavailable`` leg
  carries the insight's ``refusal_detail`` / the output's ``message``
  (docstring, shared_state.py:1904-1913) — the ``errors[*].message`` class of
  #3261, not declarable closed. The one export reader of the ledger
  (``rederive_surplus_aggregate.py:142-147``) reads the capability keys and
  the ``degraded`` boolean, never ``reason``.
- ``atomic_propositions`` — OPAQIFY every atom. ``Dict[source_key, List[str]]``
  (shared_state.py:834), the sole writer ``invoke_callables.py:9739-9744``
  storing the LLM-extracted proposition atoms (measured on the stored states:
  1 473 NL strings on 71/90, atoms named after the text's entities). The only
  export reader (``run_fp5_formal_matrix.py:115``) reads the count field, and
  arity survives the opacification; the deterministic ``opaque_id`` keeps any
  cross-container atom join for free.
- ``fol_signature`` — OPAQIFY every line. ``List[str]`` of signature lines
  (``invoke_callables.py:1644-1646`` / ``state_writers.py:1745-1750``), the
  member lists carrying entity names (measured: 405 NL on 71/90, e.g.
  ``sort = {entity, entity, ...}``). Export readers count it
  (``run_spectacular_comparison.py:148`` — ``len()``) and test populated-ness
  (:101); both survive the arity-preserving opacification.
"""

from __future__ import annotations

import json
import re

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.evaluation import sanitize_state as _sanitize_mod
from argumentation_analysis.evaluation.sanitize_state import sanitize_state

SALT = "synthetic-asset-salt"

# A free-form producer-prose canary (the reason leaf) and a distinct
# entity-named atom canary — different slots, different strings, so a survivor
# is attributable to its own leaf.
CANARY_REASON = (
    "CANARY_3249 the axis could not translate the genuine structure because "
    "the coalition demands the cost of the measure be published first"
)
CANARY_ATOM = "canary_3249_the_coalition_will_withdraw_its_support_over_the_debt"
CANARY_ATOM_BIS = "canary_3249_the_measure_is_withdrawn_before_the_deadline"
CANARY_SIG_LINE = "thing = {canary_3249_the_coalition, canary_3249_the_debt, munich}"

_OPAQUE_HEX = re.compile(r"^[0-9a-f]{8}$")


@pytest.fixture(autouse=True)
def _salt(monkeypatch):
    monkeypatch.setenv("OPAQUE_ID_SALT", SALT)


def _canaried_state() -> UnifiedAnalysisState:
    state = UnifiedAnalysisState("source_3249")
    # The real writer of the ledger (shared_state.add_structured_arg_status).
    state.add_structured_arg_status(
        "setaf_reasoning", "evaluated", False, CANARY_REASON, extension_count=2
    )
    state.add_structured_arg_status(
        "bipolar_argumentation",
        "translator_failed",
        True,
        "Bipolar translator raised PermissionDeniedError — synthetic input",
    )
    # The producers assign these two containers directly
    # (invoke_callables.py:9744 / :1646) — no adder exists; the plant uses the
    # same gesture. Same atom planted twice: the opacification must be
    # deterministic (same input -> same id).
    state.atomic_propositions["default"] = [
        CANARY_ATOM,
        CANARY_ATOM,
        CANARY_ATOM_BIS,
    ]
    state.fol_signature = [
        CANARY_SIG_LINE,
        "type(DeliveredAt(thing, thing))",
    ]
    return state


class TestStructuredArgStatusReason:
    def test_the_reason_leaf_is_dropped_and_the_record_kept(self) -> None:
        raw = _canaried_state().get_state_snapshot()
        assert CANARY_REASON in json.dumps(raw)  # the plant is real
        out = sanitize_state(raw)
        ledger = out["structured_arg_status"]
        assert set(ledger) == {"setaf_reasoning", "bipolar_argumentation"}
        setaf = ledger["setaf_reasoning"]
        assert "reason" not in setaf, "the reason leaf must not survive the export"
        # The record survives: closed-vocab status, tri-state flag, count.
        assert setaf["status"] == "evaluated"
        assert setaf["degraded"] is False
        assert setaf["extension_count"] == 2
        assert "capability" in setaf
        rendered = json.dumps(out)
        assert CANARY_REASON not in rendered
        assert "PermissionDeniedError" not in rendered

    def test_the_drop_is_the_named_table_entry(self, monkeypatch) -> None:
        tables = {k: set(v) for k, v in _sanitize_mod._TEXT_STRIP_DICT_OF_DICTS.items()}
        tables.pop("structured_arg_status", None)
        monkeypatch.setattr(_sanitize_mod, "_TEXT_STRIP_DICT_OF_DICTS", tables)
        out = sanitize_state(_canaried_state().get_state_snapshot())
        assert "reason" in out["structured_arg_status"]["setaf_reasoning"]


class TestAtomicPropositions:
    def test_atoms_are_opacified_arity_and_determinism_kept(self) -> None:
        raw = _canaried_state().get_state_snapshot()
        assert CANARY_ATOM in json.dumps(raw)
        out = sanitize_state(raw)
        atoms = out["atomic_propositions"]["default"]
        assert len(atoms) == 3  # arity survives for the count readers
        assert all(
            _OPAQUE_HEX.match(a) for a in atoms
        ), f"every atom must be an opaque id, got {atoms!r}"
        assert atoms[0] == atoms[1], "same atom must map to the same id (join)"
        assert atoms[0] != atoms[2]
        assert CANARY_ATOM not in json.dumps(out)

    def test_the_opacify_is_the_named_table_entry(self, monkeypatch) -> None:
        monkeypatch.setattr(_sanitize_mod, "_OPAQUE_WHOLE_CONTAINER_ATOMS", frozenset())
        out = sanitize_state(_canaried_state().get_state_snapshot())
        assert CANARY_ATOM in out["atomic_propositions"]["default"]


class TestFolSignature:
    def test_lines_are_opacified_arity_kept(self) -> None:
        raw = _canaried_state().get_state_snapshot()
        assert CANARY_SIG_LINE in json.dumps(raw)
        out = sanitize_state(raw)
        lines = out["fol_signature"]
        assert len(lines) == 2  # len() readers keep their count
        assert all(_OPAQUE_HEX.match(line) for line in lines)
        assert CANARY_SIG_LINE not in json.dumps(out)
        assert "DeliveredAt" not in json.dumps(out)

    def test_the_opacify_is_the_named_table_entry(self, monkeypatch) -> None:
        monkeypatch.setattr(_sanitize_mod, "_OPAQUE_WHOLE_CONTAINER_ATOMS", frozenset())
        out = sanitize_state(_canaried_state().get_state_snapshot())
        assert CANARY_SIG_LINE in out["fol_signature"]
