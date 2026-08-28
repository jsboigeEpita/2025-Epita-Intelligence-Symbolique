"""Project the global synthesis's STRUCTURED findings for the acts (#1911).

The #1894 real-corpus forensic established the post-#1620 state: the global
``deep_synthesis`` phase completes and writes ``state.narrative_synthesis``
(36/36 documents), ``formal_synthesis_reports`` is populated too, but Acts
II/III never receive their content — the appendix honestly labels both
"present but not mobilised".

This module is the mobilisation channel the #1620 comment anticipated ("a
different gesture — passing the text, not a boolean"): the acts consume a
BOUNDED, STRUCTURED projection of genuinely global findings — cross-axis
convergences and the deep-synthesis value gates — never the multi-thousand-
character prose, never a boolean.

Traceability is by construction, not by parsing: every finding is derived
from lower-level state (the same convergence machinery the synthesis phase
used: fallacies, quality, counters, JTMS, Dung) or from the synthesis's own
structured verdicts (``workflow_results["deep_synthesis_value_gates"]``).
No claim enters because "the synthesis text said it".

This module is part of the PROSE reading surface: the 1624 AST guard sweeps
it alongside the act plugins, so its ``getattr(state, ...)`` calls are what
makes the ``synthese_globale`` appendix row answerable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

# Bounded budget (#1911 DoD): the projection must not dominate the acts'
# conducted prompts. Each finding renders as ONE line; these caps bound the
# section to a few hundred characters whatever the corpus size.
_MAX_CONVERGENCE_FINDINGS = 4
_MAX_GATE_FINDINGS = 4
_STATEMENT_CAP = 160

# Two independent methods agreeing on the same argument is the smallest
# finding that is genuinely GLOBAL (one method alone is an axis result the
# acts already carry through their per-axis extractors).
_MIN_CONVERGENCE_SCORE = 2


@dataclass(frozen=True)
class GlobalFinding:
    """One global finding eligible for propagation into the acts.

    ``kind`` — "convergence" (N independent methods agree on one argument)
    or "gate" (a deep-synthesis value gate verdict).

    ``cites`` — the opaque anchors a reader can follow back to lower-level
    state: the argument id + method names for a convergence, the gate id for
    a gate. Never empty (schema-level traceability, #1911 DoD).
    """

    kind: str
    statement: str
    cites: tuple


def project_global_findings(state: Any) -> List[GlobalFinding]:
    """Derive the bounded global-findings projection from lower-level state.

    Deterministic, no LLM, no JVM. Returns findings whose every claim cites
    its underlying dimension(s); empty list when nothing genuinely global
    emerges (honest absence — a decorative "a synthesis exists" line is the
    degenerate case the #1911 DoD explicitly excludes).
    """
    findings: List[GlobalFinding] = []

    # --- convergences: N independent methods flagging the SAME argument ---
    # Lazy import: plugins import ``restitution.native_dung`` (leaf), so a
    # module-level import here would make package init order load-bearing.
    from argumentation_analysis.plugins.narrative_synthesis_plugin import (
        compute_argument_convergence,
    )

    convergence: Dict[str, Dict[str, Any]] = compute_argument_convergence(state)
    ranked = sorted(
        (
            (arg_id, data)
            for arg_id, data in convergence.items()
            if isinstance(data, dict) and data.get("score", 0) >= _MIN_CONVERGENCE_SCORE
        ),
        key=lambda kv: -int(kv[1].get("score", 0)),
    )
    for arg_id, data in ranked[:_MAX_CONVERGENCE_FINDINGS]:
        signals = data.get("signals") or []
        methods = sorted({str(method) for method, _detail in signals})
        if not methods:
            continue
        statement = (
            f"{arg_id} : {len(methods)} méthodes indépendantes convergent "
            f"({', '.join(methods)})"
        )[:_STATEMENT_CAP]
        findings.append(
            GlobalFinding(
                kind="convergence",
                statement=statement,
                cites=(arg_id, *methods),
            )
        )

    # --- gates: the deep synthesis's own structured verdicts (VG1-4) ---
    workflow_results = getattr(state, "workflow_results", None)
    gates = (
        workflow_results.get("deep_synthesis_value_gates")
        if isinstance(workflow_results, dict)
        else None
    )
    if isinstance(gates, dict) and gates:
        for gate_id, verdict in list(gates.items())[:_MAX_GATE_FINDINGS]:
            if not isinstance(verdict, (bool, str, int, float)):
                verdict = str(verdict)
            findings.append(
                GlobalFinding(
                    kind="gate",
                    statement=f"{gate_id} : {verdict}"[:_STATEMENT_CAP],
                    cites=(str(gate_id),),
                )
            )

    return findings
