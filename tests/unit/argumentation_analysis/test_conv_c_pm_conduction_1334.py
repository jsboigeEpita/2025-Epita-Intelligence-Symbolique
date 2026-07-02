"""Tests for CONV-C PM conduction — phase 3 (#1334, Epic #1331).

Covers the three phase-3 deliverables on the conversational spine:

1. **De-templatised PM prompt (§5)** — the EXTRACTION-GATE (#595) and CROSS-KB
   ENRICHMENT (#208-I) sequence recipes are *subtracted* (anti-pendule: the fix
   removes the hard-coded sequence, it does not add a counterweight rule); the
   prompt now states mission + per-turn loop + capability map + motivated-
   designation requirement + budget.
2. **Designation backfill (§7.3)** — when the designated agent returns, its open
   ``DesignationRecord`` is closed with ``state_fingerprint_after`` + a delta
   summary, pairing each motivated designation with the state growth it produced.
3. **Pipeline-global cap (§6)** — a ``CapBreachRecord`` is appended on breach
   (fail-loud, #708) and excluded from the designation count.

Design doc: docs/architecture/CONV_C_PM_ECLAIRE.md (PR #1340; phase 3 of #1334).
"""

import pytest

from argumentation_analysis.core.shared_state import (
    RhetoricalAnalysisState,
    UnifiedAnalysisState,
)
from argumentation_analysis.orchestration.conversational_orchestrator import (
    AGENT_CONFIG,
    _backfill_designation_if_present,
)

# ---------------------------------------------------------------------------
# 1. PM prompt rewrite (§5) — subtraction + addition
# ---------------------------------------------------------------------------


def test_pm_prompt_subtracts_extraction_gate_and_cross_kb():
    """The templatised #595 / #208-I recipes are gone (anti-pendule: subtract)."""
    instr = AGENT_CONFIG["ProjectManager"]["instructions"]
    assert "EXTRACTION GATE" not in instr
    assert "CROSS-KB ENRICHMENT" not in instr
    # the surviving #595 form: an enunciated fact, not a gate to obey
    assert "[Fait :" in instr


def test_pm_prompt_requires_motivated_designation():
    """record_designation + mandatory motivation = the CONV-C core requirement."""
    instr = AGENT_CONFIG["ProjectManager"]["instructions"]
    assert "record_designation(agent, motivation, trigger)" in instr
    assert "OBLIGATOIRE" in instr
    assert "designate_next_agent(nom_exact)" in instr
    # capability map present (PM reasons about synergies, none imposed)
    assert "CARTE DES CAPACITES" in instr


def test_pm_prompt_surfaces_budget_placeholder():
    """The pipeline-global cap is surfaced as {budget_turns} (filled at build)."""
    assert "{budget_turns}" in AGENT_CONFIG["ProjectManager"]["instructions"]


def test_pm_prompt_budget_placeholder_formats_cleanly():
    """The template formats without stray braces for any budget value."""
    instr = AGENT_CONFIG["ProjectManager"]["instructions"]
    filled = instr.format(budget_turns=25)
    assert "{budget_turns}" not in filled
    assert "25 tours" in filled
    # no other brace placeholders leak
    assert "{" not in filled
    assert "}" not in filled


def test_non_pm_agents_have_no_budget_placeholder():
    """Only the PM carries {budget_turns} — formatting others must be safe."""
    for name, cfg in AGENT_CONFIG.items():
        if name == "ProjectManager":
            continue
        assert "{budget_turns}" not in cfg["instructions"], name


# ---------------------------------------------------------------------------
# 2. Designation backfill (§7.3) — delta paired to the returning agent
# ---------------------------------------------------------------------------


def test_backfill_closes_record_when_designated_agent_returns():
    """The open record is closed with fingerprint_after + delta on return."""
    state = UnifiedAnalysisState("Some text to analyse.")
    state.record_designation("FormalAgent", "contradiction arg_3", "deepening")
    assert state.deliberation_trace[0]["state_fingerprint_after"] is None
    # simulate FormalAgent's contribution growing the state
    state.add_identified_arguments(["premisses: P conclusion: Q"])
    closed = state.backfill_last_designation_for("FormalAgent")
    assert closed is True
    rec = state.deliberation_trace[0]
    assert rec["state_fingerprint_after"] is not None
    assert rec["state_fingerprint_after"]["argument_count"] == 1
    assert "argument+1" in rec["delta_summary"]


def test_backfill_does_not_close_on_pm_or_wrong_agent():
    """PM speaking (or a different specialist) leaves the record open."""
    state = UnifiedAnalysisState("Some text to analyse.")
    state.record_designation("FormalAgent", "x", "deepening")
    # the PM itself speaks -> must NOT close (else it closes its own record)
    assert state.backfill_last_designation_for("ProjectManager") is False
    assert state.deliberation_trace[0]["state_fingerprint_after"] is None
    # a different specialist (round-robin interloper) -> must NOT close
    assert state.backfill_last_designation_for("InformalAgent") is False
    assert state.deliberation_trace[0]["state_fingerprint_after"] is None
    # the designated agent -> closes
    assert state.backfill_last_designation_for("FormalAgent") is True


def test_backfill_no_op_when_no_open_record():
    """No record / none open -> False, no crash."""
    state = UnifiedAnalysisState("Some text to analyse.")
    assert state.backfill_last_designation_for("FormalAgent") is False
    state.record_designation("FormalAgent", "x", "deepening")
    assert state.backfill_last_designation_for("FormalAgent") is True
    # now closed -> a second call finds nothing open
    assert state.backfill_last_designation_for("FormalAgent") is False


def test_backfill_skips_cap_breach_marker_to_reach_open_designation():
    """A cap_breach marker between the open record and the scan is skipped."""
    state = UnifiedAnalysisState("Some text to analyse.")
    state.record_designation("FormalAgent", "x", "deepening")
    # FormalAgent never returned; budget then hits -> cap_breach appended after
    state.record_cap_breach("pipeline_global", 10, "budget atteint")
    # reversed scan meets the cap_breach first; it must be skipped so the still-
    # open designation is reachable (not mistaken for an open record).
    assert state.backfill_last_designation_for("FormalAgent") is True
    assert state.deliberation_trace[0]["state_fingerprint_after"] is not None


def test_delta_summary_reports_growth_and_no_growth():
    """Delta lists grown dimensions; 'no_growth' when nothing changed.

    The delta window is designation -> agent return: the agent's contribution
    lands AFTER record_designation (captured in fingerprint_before) and BEFORE
    backfill (captured in fingerprint_after).
    """
    state = UnifiedAnalysisState("Some text to analyse.")
    # designation 1: ExtractAgent adds nothing during its turn -> no_growth
    state.record_designation("ExtractAgent", "etat vide", "initial")
    state.backfill_last_designation_for("ExtractAgent")
    assert state.deliberation_trace[0]["delta_summary"] == "no_growth"
    # designation 2: ExtractAgent again, this time it extracts 2 args
    state.record_designation(
        "ExtractAgent", "reprendre, extraire les args", "deepening"
    )
    state.add_identified_arguments(["a: prem b: conc", "c: prem d: conc"])
    state.backfill_last_designation_for("ExtractAgent")
    assert "argument+2" in state.deliberation_trace[1]["delta_summary"]


def test_backfill_helper_noop_on_base_state_and_none():
    """_backfill_designation_if_present must not raise on state without trace."""
    base = RhetoricalAnalysisState("Some text to analyse.")
    _backfill_designation_if_present(base, "FormalAgent")  # no trace -> no-op
    _backfill_designation_if_present(None, "FormalAgent")  # type: ignore[arg-type]
    _backfill_designation_if_present(base, None)
    # and it actually closes on a Unified state
    u = UnifiedAnalysisState("Some text to analyse.")
    u.record_designation("FormalAgent", "x", "deepening")
    _backfill_designation_if_present(u, "FormalAgent")
    assert u.deliberation_trace[0]["state_fingerprint_after"] is not None


# ---------------------------------------------------------------------------
# 3. Pipeline-global cap (§6) — CapBreachRecord, fail-loud, count exclusion
# ---------------------------------------------------------------------------


def test_record_cap_breach_appends_marker_excluded_from_count():
    """A cap breach is recorded but not counted as a designation turn."""
    state = UnifiedAnalysisState("Some text to analyse.")
    state.record_designation("ExtractAgent", "x", "initial")
    assert state.get_state_snapshot(summarize=True)["deliberation_turn_count"] == 1
    state.record_cap_breach("pipeline_global", 12, "budget atteint")
    # count unchanged: the breach is a marker, not a designation
    assert state.get_state_snapshot(summarize=True)["deliberation_turn_count"] == 1
    breaches = [
        r for r in state.deliberation_trace if r.get("record_type") == "cap_breach"
    ]
    assert len(breaches) == 1
    assert breaches[0]["cap_kind"] == "pipeline_global"
    assert breaches[0]["turn"] == 12


def test_cap_breach_record_serializes_with_trace():
    """The cap_breach marker survives to_json (CONV-D / audit read the trace)."""
    import json

    state = UnifiedAnalysisState("Some text to analyse.")
    state.record_designation("ExtractAgent", "x", "initial")
    state.record_cap_breach("pipeline_global", 8, "detail")
    payload = json.loads(state.to_json(indent=None))
    trace = payload["deliberation_trace"]
    assert any(r.get("record_type") == "cap_breach" for r in trace)
    assert any(r.get("designated_agent") == "ExtractAgent" for r in trace)
