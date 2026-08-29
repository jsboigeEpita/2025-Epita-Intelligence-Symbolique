"""Classify specialist results by their evidential role (#1914, Acte II slice).

The #1894 real-corpus verdict: even with every other defect fixed, the acts
expose the machinery — solver badges without derivations, coverage without
salience. A reader cannot tell which specialist result CHANGES the judgment,
which one merely corroborates it, which one disagrees with another method,
and which one ran without distinguishing anything.

This module is the #1914 Acte II slice: a deterministic classifier that
assigns each derivable specialist result one of four roles — **decisif**,
**corroborant**, **contradictoire**, **non-discriminant**. The roles are
derived from lower-level state, never asked of the LLM (the anti-pendulum
named in the dispatch: piloting vocabulary is not wiring — a prompt that
ASKS for a hierarchy proves nothing; only a render whose structure CARRIES
it is verifiable).

Role semantics (what the report may claim):

* **decisif** — the result materially changes the judgment: a formal
  violation was established (PL/FOL/modal settled false) or the Dung graph
  built from the extracted arguments excludes an argument from its accepted
  extension.
* **corroborant** — independent methods agree: a localized fallacy AND a
  weak measured quality on the same argument (the same agreement the
  synthesis convergence machinery counts; stated here at the evidence
  level, for the acts' citation hierarchy).
* **contradictoire** — methods disagree on the same argument: a localized
  fallacy BUT a strong measured quality. The tension is real and
  unresolved; the narrative must carry it as a tension, never silently
  pick a side.
* **non-discriminant** — the result ran and settled but cannot move the
  judgment either way: a formal axis whose every settled test passed, or a
  Dung extension shape that could not be decoded. Citing such a result as
  a strength ("N theories verified consistent") is exactly the badge
  without derivation the issue condemns.

Absent axes are NOT non-discriminating — an axis that never ran has no
role at all; its honest absence stays in the existing channels
(#1278/#1279). Privacy HARD: opaque ids only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

ROLE_DECISIF = "decisif"
ROLE_CORROBORANT = "corroborant"
ROLE_CONTRADICTOIRE = "contradictoire"
ROLE_NON_DISCRIMINANT = "non_discriminant"

# Descending evidential weight — the order the acts render the roles in.
ROLE_ORDER = (
    ROLE_DECISIF,
    ROLE_CONTRADICTOIRE,
    ROLE_CORROBORANT,
    ROLE_NON_DISCRIMINANT,
)

ROLE_LABELS = {
    ROLE_DECISIF: "DÉCISIF",
    ROLE_CORROBORANT: "CORROBORANT",
    ROLE_CONTRADICTOIRE: "CONTRADICTOIRE",
    ROLE_NON_DISCRIMINANT: "NON-DISCRIMINANT",
}

# Bounded budget, same discipline as #1911: the hierarchy section must not
# dominate the conducted prompt whatever the corpus size.
_MAX_PER_ROLE = 3
_STATEMENT_CAP = 160

# Quality is measured on a /10 scale. Below 5.0 the synthesis convergence
# machinery flags weakness (``QUALITY_WEAK_THRESHOLD``); at or above 7.0 the
# measured quality is solid enough that a co-located fallacy is a genuine
# cross-axis disagreement. Between the two, the quality axis neither
# corroborates nor contradicts the fallacy signal — it says nothing either
# way and gets no role.
_QUALITY_STRONG_THRESHOLD = 7.0


@dataclass(frozen=True)
class RoleAssignment:
    """One specialist result classified by its evidential role.

    ``cites`` — the opaque anchors a reader can follow back to lower-level
    state: the axis + solver for a formal verdict, the argument id + method
    names for a per-argument classification. Never empty (schema-level
    traceability, same contract as #1911's ``GlobalFinding``).
    """

    role: str
    statement: str
    cites: tuple


def _pl_verdict(result: Dict[str, Any]) -> Optional[bool]:
    """Tri-state PL verdict (canonical ``satisfiable`` then legacy
    ``consistent``). None = unverified — never collapsed to False (#1019)."""
    sat = result.get("satisfiable")
    if sat is None:
        sat = result.get("consistent")
    return sat if isinstance(sat, bool) else None


def _settled_counts(results: Any, verdict_reader) -> Dict[str, int]:
    """Count settled-true / settled-false entries of one formal axis."""
    counts = {"true": 0, "false": 0}
    if isinstance(results, list):
        for r in results:
            if not isinstance(r, dict):
                continue
            verdict = verdict_reader(r)
            if verdict is True:
                counts["true"] += 1
            elif verdict is False:
                counts["false"] += 1
    return counts


def _fallacy_targets(fallacies: Any) -> Dict[str, List[str]]:
    """Index fallacy types by target argument id (opaque)."""
    by_arg: Dict[str, List[str]] = {}
    if isinstance(fallacies, dict):
        for _fid, fdata in fallacies.items():
            if not isinstance(fdata, dict):
                continue
            tid = fdata.get("target_argument_id")
            if tid:
                by_arg.setdefault(str(tid), []).append(
                    str(fdata.get("type", "inconnu"))
                )
    return by_arg


def classify_specialist_roles(state: Any) -> List[RoleAssignment]:
    """Derive the bounded role classification from lower-level state.

    Deterministic, no LLM, no JVM. Returns assignments grouped in
    ``ROLE_ORDER`` (descending evidential weight), each role capped at
    ``_MAX_PER_ROLE``. Empty list when nothing classifiable emerges
    (honest absence — an axis that never ran has no role).
    """
    collected: Dict[str, List[RoleAssignment]] = {role: [] for role in ROLE_ORDER}

    def _add(role: str, statement: str, cites: tuple) -> None:
        collected[role].append(
            RoleAssignment(role=role, statement=statement[:_STATEMENT_CAP], cites=cites)
        )

    # --- decisif: a formal violation was established -------------------------
    pl_counts = _settled_counts(
        getattr(state, "propositional_analysis_results", None), _pl_verdict
    )
    if pl_counts["false"]:
        _add(
            ROLE_DECISIF,
            f"L'axe PL a réfuté {pl_counts['false']} inférence(s) : la mise à "
            f"l'épreuve formelle établit qu'au moins une inférence testée ne "
            f"tient pas.",
            ("PL", "solveur Tweety"),
        )

    fol_counts = _settled_counts(
        getattr(state, "fol_analysis_results", None),
        lambda r: (
            r.get("consistent") if isinstance(r.get("consistent"), bool) else None
        ),
    )
    if fol_counts["false"]:
        _add(
            ROLE_DECISIF,
            f"L'axe FOL a réfuté {fol_counts['false']} théorie(s) : la mise à "
            f"l'épreuve formelle établit qu'au moins une théorie testée est "
            f"incohérente.",
            ("FOL", "solveur Tweety"),
        )

    modal_counts = _settled_counts(
        getattr(state, "modal_analysis_results", None),
        lambda r: r.get("valid") if isinstance(r.get("valid"), bool) else None,
    )
    if modal_counts["false"]:
        _add(
            ROLE_DECISIF,
            f"L'axe modal a réfuté {modal_counts['false']} théorie(s) : la mise "
            f"à l'épreuve formelle établit qu'au moins une théorie modale "
            f"testée est incohérente.",
            ("modal", "solveur modal"),
        )

    # --- decisif: the Dung graph excludes an argument ------------------------
    # Lazy import (same pattern as global_projection): plugins import
    # restitution modules, so package-init order must not become load-bearing.
    from .native_dung import decode_native_dung

    for arg_id, label in sorted(decode_native_dung(state).rejected_by_arg.items()):
        _add(
            ROLE_DECISIF,
            f"Le graphe de Dung ({label}) bâti sur les arguments extraits ne "
            f"retient pas {arg_id} dans l'extension acceptée.",
            (arg_id, f"Dung {label}"),
        )

    # --- corroborant / contradictoire: per-argument cross-axis verdicts -------
    args = getattr(state, "identified_arguments", {}) or {}
    if isinstance(args, dict):
        # Lazy import: the weakness threshold has a single source of truth in
        # the synthesis plugin (5.0/10).
        from argumentation_analysis.plugins.narrative_synthesis_plugin import (
            QUALITY_WEAK_THRESHOLD,
        )

        fallacy_by_arg = _fallacy_targets(getattr(state, "identified_fallacies", None))
        quality = getattr(state, "argument_quality_scores", None)
        for arg_id in sorted(args):
            if arg_id not in fallacy_by_arg:
                continue  # a single method's result is an axis result, no role
            qs = quality.get(arg_id) if isinstance(quality, dict) else None
            overall = qs.get("overall") if isinstance(qs, dict) else None
            if not isinstance(overall, (int, float)):
                continue  # quality never ran on this argument — no cross verdict
            if overall >= _QUALITY_STRONG_THRESHOLD:
                _add(
                    ROLE_CONTRADICTOIRE,
                    f"Tension non résolue sur {arg_id} : un sophisme y est "
                    f"localisé mais la qualité mesurée est solide "
                    f"({overall:.1f}/10) — les axes se contredisent.",
                    (arg_id, "sophisme", "qualite"),
                )
            elif overall < QUALITY_WEAK_THRESHOLD:
                _add(
                    ROLE_CORROBORANT,
                    f"Les axes sophisme et qualité corroborent la faiblesse de "
                    f"{arg_id} ({overall:.1f}/10 mesuré) — deux méthodes "
                    f"indépendantes s'accordent.",
                    (arg_id, "sophisme", "qualite"),
                )

    # --- non-discriminant: ran, settled, moves nothing ------------------------
    if pl_counts["false"] == 0 and pl_counts["true"]:
        _add(
            ROLE_NON_DISCRIMINANT,
            f"L'axe PL a vérifié {pl_counts['true']} inférence(s), toutes "
            f"satisfaisables — le test ne distingue rien ici.",
            ("PL", "solveur Tweety"),
        )
    if fol_counts["false"] == 0 and fol_counts["true"]:
        _add(
            ROLE_NON_DISCRIMINANT,
            f"L'axe FOL a vérifié {fol_counts['true']} théorie(s), toutes "
            f"cohérentes — le test ne distingue rien ici.",
            ("FOL", "solveur Tweety"),
        )
    if modal_counts["false"] == 0 and modal_counts["true"]:
        _add(
            ROLE_NON_DISCRIMINANT,
            f"L'axe modal a vérifié {modal_counts['true']} théorie(s), toutes "
            f"cohérentes — le test ne distingue rien ici.",
            ("modal", "solveur modal"),
        )
    for label in decode_native_dung(state).non_concluable:
        _add(
            ROLE_NON_DISCRIMINANT,
            f"L'extension Dung {label} n'est pas décodable — aucun rejet "
            f"dérivable, l'axe ne peut pas trancher.",
            (f"Dung {label}",),
        )

    out: List[RoleAssignment] = []
    for role in ROLE_ORDER:
        out.extend(collected[role][:_MAX_PER_ROLE])
    return out
