"""#1914 (Acte III slice) — rank what carries the verdict, state the zero-shot surplus.

The Acte II slice (#1914, ``specialist_roles``) classified each specialist
result by its evidential role. The reader-chair reviews behind #1894 named
the conclusion-side defect this module closes: *coverage without salience* —
the conclusion enumerated every label at the same level, so a reader could
not tell the two findings that move the interpretation from the fourteen
that accompany them, and nothing in the report said what the multi-agent
pipeline had established that a strong single-pass reading could not.

Two deterministic derivations, both from lower-level state, neither ever
asked of the LLM (the dispatch anti-pendulum: piloting vocabulary is not
wiring — a prompt that ASKS for a hierarchy or a surplus proves nothing;
only a render whose structure CARRIES them is verifiable):

* **Salience ranking** — the role assignments become a small bounded
  hierarchy (P1 decisif → P2 tension → P3 corroboré / unchallenged
  strength, ``_MAX_RANKED`` total). Non-discriminating results are
  DELIBERATELY excluded from the ranking: a verified-everything axis moves
  no judgment, and ranking it anywhere would reintroduce the badge the
  issue condemns. Strengths earn a rank only when unchallenged (strong
  measured quality, no localized fallacy, not Dung-rejected) — a strength
  contested by another axis is a tension, and the classifier already
  carries it as one.
* **Zero-shot surplus** — what this run established that a strong zero-shot
  reading cannot: formal refutations and Dung exclusions (decisive roles),
  structural relations (the structured-argumentation findings — cycles,
  articulation points, minimal retractions, attack scopes, coalitions,
  contraries, weights), and convergences carrying at least one non-LLM
  signal (Dung/JTMS — see ``_NON_LLM_SIGNALS``: an agreement between two
  LLM labelling methods is convergence, not surplus). Distinct from
  ``procedural_only``: all-verified axes, generated counters and labels are
  matter the report may inventory but must not sell as interpretive
  surplus. When nothing qualifies, ``established`` is empty and the
  conclusion renders the honest refusal — the reader-chair acceptance
  criterion (a report whose only multi-agent surplus is counters/labels
  must not claim a changed interpretive conclusion).

Privacy HARD: opaque ids only. Every item cites its anchors (same
traceability contract as #1911's ``GlobalFinding`` and #1914's
``RoleAssignment``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, List, Sequence, Tuple

from .specialist_roles import (
    ROLE_CONTRADICTOIRE,
    ROLE_CORROBORANT,
    ROLE_DECISIF,
    ROLE_NON_DISCRIMINANT,
    ROLE_ORDER,
    _QUALITY_STRONG_THRESHOLD,
    classify_specialist_roles,
)

# Bounded budgets, same discipline as the Acte II slice: the hierarchy and
# the surplus must not dominate the conducted prompt whatever the corpus.
_MAX_RANKED = 5
_MAX_STRENGTHS = 3
_MAX_SURPLUS = 6
_STATEMENT_CAP = 160

# Signals produced by the formal/structural machinery — the only methods a
# strong single-pass reading cannot replicate. A convergence of two LLM
# labelling methods (fallacy + counter, fallacy + weak quality) is genuine
# convergence and stays in the CONVERGENCES GLOBALES block, but it is NOT
# zero-shot surplus: the reader-chair acceptance criterion rejects a report
# whose claimed surplus is only counters and labels. Deep-synthesis value
# gates are excluded for the same reason the issue condemns gate
# self-assessment in the acts — a gate is the pipeline grading itself, not
# evidence it beat a reading.
_NON_LLM_SIGNALS = ("rejet dung", "jtms retracte")

# Evidential weights — P1 carries the verdict, P3 accompanies it.
_WEIGHT_DECISIVE = 1
_WEIGHT_TENSION = 2
_WEIGHT_ACCOMPANYING = 3

KIND_VULNERABILITY = "vulnerabilite"
KIND_TENSION = "tension"
KIND_STRENGTH = "force"


@dataclass(frozen=True)
class SalienceItem:
    """One ranked finding — what the conclusion may structure itself on.

    ``weight`` — 1 (decisive) to 3 (accompanying). ``kind`` — vulnerability,
    tension, or strength. ``cites`` — the opaque anchors, never empty.
    """

    weight: int
    kind: str
    statement: str
    cites: Tuple[str, ...]


@dataclass(frozen=True)
class SurplusItem:
    """One thing the run established beyond a strong zero-shot reading."""

    statement: str
    cites: Tuple[str, ...]


@dataclass(frozen=True)
class SurplusAssessment:
    """The zero-shot surplus split into its honest halves.

    ``established`` — findings a single-pass reading cannot produce (solver
    verdicts, graph-structural relations, cross-method convergences).
    ``procedural_only`` — code-authored French lines naming what remains
    procedural (all-verified axes, counters/labels inventory); the conclusion
    may inventory these but must not sell them as surplus.
    """

    established: List[SurplusItem]
    procedural_only: List[str]


@dataclass(frozen=True)
class ConclusionSalience:
    """The Acte III salience bundle: the ranked findings + the surplus."""

    ranked: List[SalienceItem]
    surplus: SurplusAssessment


def _truncate(text: Any, cap: int) -> str:
    if not text:
        return ""
    s = str(text).strip()
    return s if len(s) <= cap else s[:cap].rstrip() + " […]"


def _fallacy_target_ids(state: Any) -> set:
    """Opaque ids of every argument a localized fallacy sits on."""
    fallacies = getattr(state, "identified_fallacies", None)
    out: set = set()
    if isinstance(fallacies, dict):
        for _fid, fdata in fallacies.items():
            if isinstance(fdata, dict) and fdata.get("target_argument_id"):
                out.add(str(fdata["target_argument_id"]))
    return out


def _unchallenged_strengths(state: Any) -> List[SalienceItem]:
    """Strong measured quality that no other axis contests (rank-3 strengths).

    A strength earns a rank only when unchallenged: overall ≥ 7.0, no
    localized fallacy on the argument, and the Dung graph does not exclude
    it. A strong-quality argument carrying a fallacy is already classified
    ``contradictoire`` upstream (the tension IS the finding); a strong-
    quality argument Dung rejects is already ``decisif``. Ranking either
    here again would present a contested move as settled ground.
    """
    args = getattr(state, "identified_arguments", None)
    quality = getattr(state, "argument_quality_scores", None)
    if not isinstance(args, dict) or not isinstance(quality, dict):
        return []
    from .native_dung import decode_native_dung

    contested = _fallacy_target_ids(state)
    rejected = set(decode_native_dung(state).rejected_by_arg)
    out: List[SalienceItem] = []
    for arg_id in sorted(args):
        if arg_id in contested or arg_id in rejected:
            continue
        qs = quality.get(arg_id)
        overall = qs.get("overall") if isinstance(qs, dict) else None
        if not isinstance(overall, (int, float)) or overall < _QUALITY_STRONG_THRESHOLD:
            continue
        out.append(
            SalienceItem(
                weight=_WEIGHT_ACCOMPANYING,
                kind=KIND_STRENGTH,
                statement=(
                    f"{arg_id} tient : qualité mesurée solide ({overall:.1f}/10) "
                    f"et aucun axe ne la conteste."
                ),
                cites=(arg_id, "qualite"),
            )
        )
        if len(out) >= _MAX_STRENGTHS:
            break
    return out


def _assess_surplus(
    roles: Sequence[Any],
    structured_findings: Iterable[Any],
    global_findings: Iterable[Any],
    counters_total: int,
) -> SurplusAssessment:
    """Split what the run established beyond a zero-shot from the procedural.

    Established = decisive roles (formal refutations, Dung exclusions) +
    structured-argumentation findings (relations no single reading derives) +
    convergences that carry at least one non-LLM signal (see
    ``_NON_LLM_SIGNALS`` — an LLM-only agreement is convergence, not
    surplus). Procedural = non-discriminating roles + the counters/labels
    inventory — matter the conclusion may cite as context, never as
    interpretive surplus.
    """
    established: List[SurplusItem] = []
    for role in roles:
        if role.role == ROLE_DECISIF:
            established.append(
                SurplusItem(
                    statement=_truncate(role.statement, _STATEMENT_CAP),
                    cites=tuple(role.cites),
                )
            )
    for finding in structured_findings:
        statement = _truncate(getattr(finding, "statement", ""), _STATEMENT_CAP)
        if statement:
            established.append(
                SurplusItem(
                    statement=statement,
                    cites=(str(getattr(finding, "label", "")) or "cadre_structure"),
                )
            )
    for finding in global_findings:
        if str(getattr(finding, "kind", "")) != "convergence":
            continue
        cites = tuple(getattr(finding, "cites", ()) or ())
        methods = [str(c).lower() for c in cites[1:]]
        if not any(m in _NON_LLM_SIGNALS for m in methods):
            continue
        statement = _truncate(getattr(finding, "statement", ""), _STATEMENT_CAP)
        if statement:
            established.append(SurplusItem(statement=statement, cites=cites))
    established = established[:_MAX_SURPLUS]

    procedural: List[str] = []
    for role in roles:
        if role.role == ROLE_NON_DISCRIMINANT:
            procedural.append(_truncate(role.statement, _STATEMENT_CAP))
    if counters_total:
        procedural.append(
            f"les {counters_total} contre-argument(s) généré(s) et les labels de "
            "sophisme localisés sont de la matière disponible — aucun n'a changé "
            "la conclusion interprétative par lui-même."
        )
    return SurplusAssessment(established=established, procedural_only=procedural)


def assess_conclusion_salience(
    state: Any,
    structured_findings: Iterable[Any] = (),
    global_findings: Iterable[Any] = (),
    counters_total: int = 0,
) -> ConclusionSalience:
    """Derive the Acte III salience bundle (ranking + zero-shot surplus).

    Deterministic, no LLM, no JVM. ``structured_findings`` and
    ``global_findings`` are the components ``build_act3_evidence`` already
    derives (StructuredArgFinding / GlobalFinding) — passed in rather than
    recomputed so there is exactly one reader per state leaf (the #1633
    lesson). ``counters_total`` is the same honest count the evidence
    bundle carries.
    """
    roles = classify_specialist_roles(state)
    by_role = {role: [a for a in roles if a.role == role] for role in ROLE_ORDER}

    ranked: List[SalienceItem] = []
    for assignment in by_role[ROLE_DECISIF]:
        ranked.append(
            SalienceItem(
                weight=_WEIGHT_DECISIVE,
                kind=KIND_VULNERABILITY,
                statement=_truncate(assignment.statement, _STATEMENT_CAP),
                cites=tuple(assignment.cites),
            )
        )
    for assignment in by_role[ROLE_CONTRADICTOIRE]:
        ranked.append(
            SalienceItem(
                weight=_WEIGHT_TENSION,
                kind=KIND_TENSION,
                statement=_truncate(assignment.statement, _STATEMENT_CAP),
                cites=tuple(assignment.cites),
            )
        )
    for assignment in by_role[ROLE_CORROBORANT]:
        ranked.append(
            SalienceItem(
                weight=_WEIGHT_ACCOMPANYING,
                kind=KIND_VULNERABILITY,
                statement=_truncate(assignment.statement, _STATEMENT_CAP),
                cites=tuple(assignment.cites),
            )
        )
    ranked.extend(_unchallenged_strengths(state))
    ranked = ranked[:_MAX_RANKED]

    surplus = _assess_surplus(
        roles, structured_findings, global_findings, counters_total
    )
    return ConclusionSalience(ranked=ranked, surplus=surplus)
