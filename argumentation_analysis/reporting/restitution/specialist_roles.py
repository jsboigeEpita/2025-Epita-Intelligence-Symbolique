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

from .fr_accord import accord
from .formal_derivation import extract_tested_content

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

# #2046 — reader-facing leads, no bracket tags: the « [NON-DISCRIMINANT] »
# notation read as machine output in the middle of a narrative. The label is
# plain French now; the acts render it as a dash lead, never bracketed.
ROLE_LABELS = {
    ROLE_DECISIF: "Décisif",
    ROLE_CORROBORANT: "Corroborant",
    ROLE_CONTRADICTOIRE: "Contradictoire",
    ROLE_NON_DISCRIMINANT: "Non discriminant",
}

# Bounded budget, same discipline as #1911: the hierarchy section must not
# dominate the conducted prompt whatever the corpus size. #1914 : raised from
# 160 so a decisive statement can carry its tested-content derivation without
# being sliced mid-quote (an untruncated « à l'épreuve : … » beats a badge).
_MAX_PER_ROLE = 3
_STATEMENT_CAP = 240

# Quality verdicts read the NORMALIZED fraction of the applicable maximum
# (#1942): ``overall`` is a sum over the evaluated virtues, and post-#1923
# the denominator varies ({2, 6, 8} measured on real texts) — under the
# fraction scale a perfect argument on 6 virtues sums to 6.0 and the
# absolute 7.0 strong bar would be mathematically unreachable. Single
# source of truth in the synthesis plugin: ``quality_fraction``,
# ``QUALITY_WEAK_FRACTION`` (5.0/10), ``QUALITY_STRONG_FRACTION`` (7.0/10).
# Between the two fractions the quality axis neither corroborates nor
# contradicts the fallacy signal — it says nothing either way, no role.


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
        if len(statement) > _STATEMENT_CAP:
            # #1914 : cut at the last sentence boundary, never mid-word — a
            # half-sentence anchor invites the conductor to echo broken prose.
            cut = statement[:_STATEMENT_CAP]
            dot = cut.rfind(". ")
            statement = cut[: dot + 1] if dot > 0 else cut.rstrip() + "…"
        collected[role].append(
            RoleAssignment(role=role, statement=statement, cites=cites)
        )

    # --- decisif: a formal violation was established -------------------------
    # #1914 (constat 1) : the decisive statement carries WHAT was tested —
    # the refuted records' formulas — so the citation is a derivation, not a
    # badge. Placeholder-only records → tested stays None → the statement
    # says the honest absence instead of dressing a counter as a proof.
    def _decisif_statement(
        axis: str, noun_sg: str, noun_pl: str, n_false: int, tested: Optional[str]
    ) -> str:
        head = f"L'axe {axis} a réfuté {accord(n_false, noun_sg, noun_pl)}"
        if tested:
            return (
                f"{head} — à l'épreuve : {tested}. La mise à l'épreuve "
                f"formelle établit que ce contenu testé ne tient pas."
            )
        return (
            f"{head} : contenu testé non disponible dans l'état — la mise à "
            f"l'épreuve formelle établit qu'au moins {accord(1, noun_sg, noun_pl)} "
            f"testée ne tient pas."
        )

    pl_records = getattr(state, "propositional_analysis_results", None)
    pl_counts = _settled_counts(pl_records, _pl_verdict)
    if pl_counts["false"]:
        _add(
            ROLE_DECISIF,
            _decisif_statement(
                "PL",
                "inférence",
                "inférences",
                pl_counts["false"],
                extract_tested_content(
                    pl_records, _pl_verdict, refuted=True, max_atoms=2
                ),
            ),
            ("PL", "solveur Tweety"),
        )

    fol_records = getattr(state, "fol_analysis_results", None)
    fol_counts = _settled_counts(
        fol_records,
        lambda r: (
            r.get("consistent") if isinstance(r.get("consistent"), bool) else None
        ),
    )
    if fol_counts["false"]:
        _add(
            ROLE_DECISIF,
            _decisif_statement(
                "FOL",
                "théorie",
                "théories",
                fol_counts["false"],
                extract_tested_content(
                    fol_records,
                    lambda r: (
                        r.get("consistent")
                        if isinstance(r.get("consistent"), bool)
                        else None
                    ),
                    refuted=True,
                    max_atoms=2,
                ),
            ),
            ("FOL", "solveur Tweety"),
        )

    modal_records = getattr(state, "modal_analysis_results", None)
    modal_counts = _settled_counts(
        modal_records,
        lambda r: r.get("valid") if isinstance(r.get("valid"), bool) else None,
    )
    if modal_counts["false"]:
        _add(
            ROLE_DECISIF,
            _decisif_statement(
                "modal",
                "théorie",
                "théories",
                modal_counts["false"],
                extract_tested_content(
                    modal_records,
                    lambda r: (
                        r.get("valid") if isinstance(r.get("valid"), bool) else None
                    ),
                    refuted=True,
                    max_atoms=2,
                ),
            ),
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
        # Lazy import: the quality scale has a single source of truth in the
        # synthesis plugin (#1942 — fraction of the applicable maximum).
        from argumentation_analysis.plugins.narrative_synthesis_plugin import (
            QUALITY_STRONG_FRACTION,
            QUALITY_WEAK_FRACTION,
            quality_fraction,
            quality_population_spans_weak,
        )

        fallacy_by_arg = _fallacy_targets(getattr(state, "identified_fallacies", None))
        quality = getattr(state, "argument_quality_scores", None)
        # #1942 non-vacuity gate: weak corroborates nothing on a population
        # where 100% of the measured arguments are under the bar.
        quality_spans = quality_population_spans_weak(quality)
        for arg_id in sorted(args):
            if arg_id not in fallacy_by_arg:
                continue  # a single method's result is an axis result, no role
            qs = quality.get(arg_id) if isinstance(quality, dict) else None
            fraction = quality_fraction(qs)
            if fraction is None:
                continue  # unmeasured on this argument — no cross verdict
            if fraction >= QUALITY_STRONG_FRACTION:
                _add(
                    ROLE_CONTRADICTOIRE,
                    f"Tension non résolue sur {arg_id} : un sophisme y est "
                    f"localisé mais la qualité mesurée est solide ({fraction:.0%} "
                    f"du maximum applicable) — les axes se contredisent.",
                    (arg_id, "sophisme", "qualite"),
                )
            elif fraction < QUALITY_WEAK_FRACTION and quality_spans:
                _add(
                    ROLE_CORROBORANT,
                    f"Les axes sophisme et qualité corroborent la faiblesse de "
                    f"{arg_id} ({fraction:.0%} du maximum applicable) — deux "
                    f"méthodes indépendantes s'accordent.",
                    (arg_id, "sophisme", "qualite"),
                )

    # --- non-discriminant: ran, settled, moves nothing ------------------------
    if pl_counts["false"] == 0 and pl_counts["true"]:
        _add(
            ROLE_NON_DISCRIMINANT,
            f"L'axe PL a vérifié {accord(pl_counts['true'], 'inférence', 'inférences')}, toutes "
            f"satisfaisables — le test ne distingue rien ici.",
            ("PL", "solveur Tweety"),
        )
    if fol_counts["false"] == 0 and fol_counts["true"]:
        _add(
            ROLE_NON_DISCRIMINANT,
            f"L'axe FOL a vérifié {accord(fol_counts['true'], 'théorie', 'théories')}, toutes "
            f"cohérentes — le test ne distingue rien ici.",
            ("FOL", "solveur Tweety"),
        )
    if modal_counts["false"] == 0 and modal_counts["true"]:
        _add(
            ROLE_NON_DISCRIMINANT,
            f"L'axe modal a vérifié {accord(modal_counts['true'], 'théorie', 'théories')}, toutes "
            f"cohérentes — le test ne distingue rien ici.",
            ("modal", "solveur modal"),
        )
    # #1942: a quality axis whose ENTIRE measured population sits under the
    # weak bar has not discriminated anything — render that vacuity instead
    # of corroborating every fallacious argument for free.
    from argumentation_analysis.plugins.narrative_synthesis_plugin import (
        QUALITY_WEAK_FRACTION,
        quality_fraction,
    )

    quality_entries = getattr(state, "argument_quality_scores", None)
    measured_fractions = [
        f
        for f in (
            quality_fraction(qs)
            for qs in (
                quality_entries.values() if isinstance(quality_entries, dict) else []
            )
        )
        if f is not None
    ]
    if measured_fractions and not any(
        f >= QUALITY_WEAK_FRACTION for f in measured_fractions
    ):
        _add(
            ROLE_NON_DISCRIMINANT,
            f"L'axe qualité ne discrimine pas ce run : "
            f"{len(measured_fractions)}/{len(measured_fractions)} notes mesurées "
            f"sous le seuil faible ({QUALITY_WEAK_FRACTION:.0%} du maximum "
            f"applicable) — la faiblesse mesurée n'y distingue rien.",
            ("qualite", "évaluateur de vertus"),
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
