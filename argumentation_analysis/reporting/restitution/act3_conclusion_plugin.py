"""Acte III generator — actionable conclusion (the reader's payoff).

Epic #1134 (Restitution) / Track R4 #1138. LLM-conducted, woven per spec §4.
Consumed by the R6 renderer to populate ``RestitutionActs.act3_conclusion``.

Design (spec §1.3 + §3 + §4 + §7, issue #1138, dispatch coord R428/R429):
  - The conclusion hands back something *usable*. Three beats:
    1. **Synthèse honnête** — the verdict, **gated** on the non-triviality gates
       G1–G4 (#1008 §3) and on the verdict band (computed here, adapted from
       #1008 §2 — see ``_compute_verdict_band``). No over-claim.
    2. **Appréciations** — strengths **and** weaknesses of the discourse (both,
       honestly, woven from the quality axis and the fallacy/formal findings).
    3. **Que faire de l'analyse** — actionable: how to **counter** the arguments
       (the generated counter-arguments), the **weak points to target** (the
       structuring fallacies + the inferences Tweety invalidates + the attacks
       Dung isolates as defeated), and **what to expect next** (the probable
       follow-on moves — closing the loop on the Acte I game-theoretic framing).
  - Every framework citation gets a narrative anchor (passes the §4 gate — this
    module self-checks its own output with ``ReadabilityGate``).
  - **LLM-conducted**: the conclusion VARIES by corpus (no template #1108/#405).
    Fail-loud when no LLM is injected — empty string + explicit status; the
    renderer reports the gap honestly (anti-pendule #1019/#369).

Verdict band — honest adaptation of #1008 §2 to the restitution context:
  #1008 §2.1 frames the bands as "pipeline vs external analyst" (MATCH+ count
  over 10 yardstick dimensions). The restitution report has *no external
  analyst to compare against* (spec §3: "what this discourse is, honestly").
  We therefore compute the band from the **real analytical coverage** of the
  run — how many analytical axes produced non-trivial content — so the band
  governs *how strongly the discourse may be characterised*, never a fabricated
  comparison. This is the scorer the spec §2 table attributes to
  ``_compute_verdict()`` ("computed, not a state key").

Privacy HARD: opaque IDs only (``arg_N``, fallacy families are taxonomy
constants). The prompt carries the OPAQUE_ID_DIRECTIVE (FB-34). Corpus-derived
fields (fallacy justifications, counter-content, synthesis snippets) are
**truncated** before entering the prompt; the LLM is told to paraphrase, never
echo verbatim — the final R6 scrub (spec §6) is the downstream guard.

Testability: ``build_act3_evidence`` is deterministic (no LLM/JVM/API); the LLM
is an injectable async callable ``Callable[[str], Awaitable[str]]`` (FB-29/38
injectable-LLM pattern), so unit tests pass a stub and need no kernel.

Mirrors the R3 act-plugin pattern (``act2_narrative_plugin``) — same 3 infra
files, append-only.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

from .readability_gate import GateVerdict, ReadabilityGate
from .virtuous_identification import VirtuousModeAssessment, detect_virtuous_mode

logger = logging.getLogger(__name__)

# An async LLM callable: prompt in, completion text out (FB-29/38 injectable).
LlmCallable = Callable[[str], Awaitable[str]]

# Truncation caps for corpus-derived fields entering the prompt (privacy +
# prompt-budget discipline). The LLM is told to paraphrase, not echo.
_JUSTIFICATION_CAP = 200
_COUNTER_CAP = 200
_SYNTHESIS_CAP = 400
# SV (#1182): caps for governance/debate evidence (privacy + prompt budget).
_DEBATE_CAP = 200
_DEBATE_MAX_EXCHANGES = 4

# Verdict bands (adapted from #1008 §2.1 to the restitution coverage model).
_BAND_EXCEEDED = "EXCEEDED"
_BAND_MATCH = "MATCH"
_BAND_PARTIAL = "PARTIAL"
_BAND_BELOW = "BELOW"

# The analytical axes whose non-trivial coverage earns the verdict band. Each is
# real-in-state; we never fabricate an axis (G4).
_AXIS_FALLACIES = "fallacies"
_AXIS_QUALITY = "quality"
_AXIS_COUNTERS = "counter_arguments"
_AXIS_FORMAL_PL = "formal_pl"
_AXIS_FORMAL_FOL = "formal_fol"
_AXIS_DUNG = "dung"

# Thresholds mapping coverage count → band (anti-pendule: transparent, fixed).
# EXCEEDED needs formal depth (PL or FOL) AND quality (a characterised discourse)
# on top of broad coverage — the "depth surpassing" spirit of #1008 §2.1.
_EXCEEDED_MIN_AXES = 5
_MATCH_MIN_AXES = 4
_PARTIAL_MIN_AXES = 2


# --- evidence dataclasses ----------------------------------------------------


@dataclass
class StructuringWeakPoint:
    """A weak point the reader can target — a fallacy or a formal rejection.

    ``source`` is one of ``"fallacy"`` / ``"pl"`` / ``"fol"`` / ``"dung"`` so the
    LLM can anchor the citation to the framework that produced it (spec §4).
    """

    source: str
    label: str  # human-readable: fallacy family/type, or a formal verdict line
    target_arg_id: str
    detail: str = ""


@dataclass
class CounterStrategy:
    """A counter-argument the reader can use to push back."""

    strategy: str
    target_arg_id: str
    snippet: str
    # G6 (#1180): the validation verdict (ValidationResult shape) so the
    # narrative can cite counter-argument *validity*, not just existence.
    # None when the evaluator did not run (honest absence, not fabricated).
    is_valid_attack: Optional[bool] = None
    counter_succeeds: Optional[bool] = None


@dataclass
class GovernanceVerdict:
    """A governance voting decision (SV #1182), verified-in-state.

    ``scores`` maps opaque option IDs → Copeland/influence score. Privacy: the
    keys are opaque (no party/option names).
    """

    method: str
    winner: str
    scores: Dict[str, float] = field(default_factory=dict)


@dataclass
class DebateExchange:
    """One adversarial-debate exchange (SV #1182). Gap β G8: can be sparse."""

    point: str
    rebuttal: str


@dataclass
class QualityStrength:
    """A virtue where the discourse scores well (a strength to acknowledge)."""

    virtue: str
    score: float


@dataclass
class VerdictBand:
    """The computed verdict band + the honest coverage that earned it.

    Adapted from #1008 §2.1 to the restitution coverage model (no external
    analyst): the band governs how strongly the discourse may be characterised.
    """

    band: str
    nontrivial_axes: List[str] = field(default_factory=list)
    missing_axes: List[str] = field(default_factory=list)
    axes_count: int = 0


@dataclass
class Act3Evidence:
    """Deterministic evidence bundle for the Acte III conclusion.

    ``gates`` carries the G1–G4 statuses (#1008 §3.2) so the orchestrator can
    emit the honest fallback wording when the conclusion must not render.
    """

    args_total: int = 0
    fallacies_total: int = 0
    counters_total: int = 0
    quality_axis_available: bool = False
    quality_strengths: List[QualityStrength] = field(default_factory=list)
    weak_points: List[StructuringWeakPoint] = field(default_factory=list)
    counter_strategies: List[CounterStrategy] = field(default_factory=list)
    verdict: Optional[VerdictBand] = None
    narrative_synthesis_available: bool = False
    gates: Dict[str, bool] = field(default_factory=dict)
    # SV (#1182): governance verdict + debate exchanges, surfaced so the
    # conclusion can cite collective deliberation. None/empty when the phases
    # produced no non-trivial output (honest absence, not fabricated).
    governance_verdict: Optional[GovernanceVerdict] = None
    debate_exchanges: List[DebateExchange] = field(default_factory=list)
    # DERIVED virtuous flag (spec §5.1) — drives virtue-first titling when the
    # state characterises the text as virtuous (zero fallacies + non-trivial
    # quality/formal axis). None until build_act3_evidence populates it.
    virtuous_mode: Optional[VirtuousModeAssessment] = None


@dataclass
class Act3Result:
    """Outcome of :func:`build_act3_conclusion`.

    ``status`` is one of ``"woven"`` (LLM produced a conclusion), ``"unavailable"``
    (no LLM injected or LLM failed — fail-loud, #1108), ``"empty_state"`` (G1
    failed — no substrate), ``"gates_failed"`` (G1–G4 blocked the gated
    synthesis — honest fallback wording). ``gate_verdict`` is the honest §4
    self-check.
    """

    narrative: str
    status: str
    gate_verdict: Optional[GateVerdict] = None
    degraded: Dict[str, str] = field(default_factory=dict)
    # True when the conclusion was conducted in virtuous mode (spec §5) — the
    # headline titles on the measured virtues, not on the absence of fallacies.
    is_virtuous: bool = False


# --- deterministic evidence builder (no LLM) ---------------------------------


def _truncate(text: Any, cap: int) -> str:
    """Coerce to str and cap length (privacy + prompt budget)."""
    if not text:
        return ""
    s = str(text).strip()
    return s if len(s) <= cap else s[:cap].rstrip() + " […]"


def _pl_verdict(result: Dict[str, Any]) -> Optional[bool]:
    """Read a PL analysis verdict as a strict bool, or None when unverified.

    Canonical PL key is ``satisfiable`` (shared_state.add_propositional_analysis_result,
    #1151 Finding C); ``consistent`` is the legacy/FOL-shared key kept as a
    fallback. Preserves the strict ``True``/``False``/``None`` semantics so an
    unverified theory is never conflated with an inconsistent one (#1019) — do
    NOT collapse to ``bool()``.
    """
    sat = result.get("satisfiable")
    if sat is None:
        sat = result.get("consistent")
    return sat if isinstance(sat, bool) else None


def _pl_inconsistent(state: Any) -> int:
    """Count PL inferences the Tweety solver found inconsistent (real-in-state).

    Uses ``_pl_verdict`` (canonical ``satisfiable`` key) so the PL axis is read
    the same way as the FOL axis and the virtuous-mode detector — #1151 C.
    """
    pl = getattr(state, "propositional_analysis_results", None)
    if not isinstance(pl, list):
        return 0
    return sum(1 for r in pl if isinstance(r, dict) and _pl_verdict(r) is False)


def _pl_verified(state: Any) -> int:
    """Count PL theories the Tweety solver verified (any verdict, real-in-state).

    D1c (#1167): a CONSISTENT PL theory (``satisfiable is True``) is a real
    formal result, not a non-event — the solver ran and confirmed the
    discourse's propositional structure holds. The formal axis must credit it
    as non-trivial so a coherent text (no inconsistency) still surfaces a
    formal finding (satisfiable IS a result). Counts True AND False verdicts;
    unverified (None) theories are excluded — #1019 (never ``bool()`` a formal
    verdict: None ≠ False).
    """
    pl = getattr(state, "propositional_analysis_results", None)
    if not isinstance(pl, list):
        return 0
    return sum(
        1 for r in pl if isinstance(r, dict) and _pl_verdict(r) is not None
    )


def _fol_inconsistent(state: Any) -> int:
    """Count FOL theories the Tweety solver found inconsistent (real-in-state)."""
    fol = getattr(state, "fol_analysis_results", None)
    if not isinstance(fol, list):
        return 0
    return sum(
        1
        for r in fol
        if isinstance(r, dict) and r.get("consistent") is False
    )


def _fol_verified(state: Any) -> int:
    """Count FOL theories the Tweety solver verified (any verdict, real-in-state).

    D1c (#1167): a CONSISTENT FOL theory (``consistent is True``) is a real
    formal result — credit it so a coherent text surfaces a formal finding.
    Counts True AND False verdicts; excludes unverified (None) — #1019.
    """
    fol = getattr(state, "fol_analysis_results", None)
    if not isinstance(fol, list):
        return 0
    return sum(
        1
        for r in fol
        if isinstance(r, dict)
        and (r.get("consistent") is True or r.get("consistent") is False)
    )


def _dung_rejected_by_arg(state: Any) -> Dict[str, str]:
    """Map arg_id → Dung semantics label for arguments a framework rejected.

    A rejected argument is present in a framework's arguments but absent from
    its accepted extension — the attack isolates it as defeated. Mirrors the
    resolution in ``act2_narrative_plugin._dung_rejected_by_arg`` (kept local
    here for file-disjointness — R4 establishes its own copy, same logic).
    """
    rejected: Dict[str, str] = {}
    frameworks = getattr(state, "dung_frameworks", {}) or {}
    if not isinstance(frameworks, dict):
        return rejected
    for _fid, fw in frameworks.items():
        if not isinstance(fw, dict):
            continue
        fw_args = fw.get("arguments", []) or []
        if not isinstance(fw_args, list):
            continue
        semantics = str(fw.get("semantics", "grounded"))
        accepted: set[str] = set()
        ext = fw.get("extensions", [])
        if isinstance(ext, dict):
            if "all_members" in ext:
                accepted = set(ext.get("all_members", []) or [])
            else:
                for val in ext.values():
                    if isinstance(val, list):
                        for item in val:
                            if isinstance(item, list):
                                accepted.update(item)
                            elif isinstance(item, str):
                                accepted.add(item)
        elif isinstance(ext, list):
            for item in ext:
                if isinstance(item, list):
                    accepted.update(item)
                elif isinstance(item, str):
                    accepted.add(item)
        for arg in fw_args:
            if isinstance(arg, str) and arg not in accepted:
                rejected.setdefault(arg, semantics)
    return rejected


def _collect_weak_points(
    fallacies: Dict[str, Any],
    dung_rejected: Dict[str, str],
    pl_inc: int,
    fol_inc: int,
) -> List[StructuringWeakPoint]:
    """Collect the structuring weak points the reader can target (real-in-state).

    Each weak point is bound to (a) a located argument and (b) the concrete
    verdict that flagged it — the spec §4 weaving anchors. We surface the
    fallacies that *target* an argument, plus the formal rejections. Never
    fabricate a weak point (G4, anti-pendule #1019/#369).
    """
    points: List[StructuringWeakPoint] = []
    for _fid, fdata in fallacies.items():
        if not isinstance(fdata, dict):
            continue
        tid = fdata.get("target_argument_id") or ""
        if not tid:
            continue
        family = str(fdata.get("family", "inconnu"))
        ftype = str(fdata.get("type", "inconnu"))
        points.append(
            StructuringWeakPoint(
                source="fallacy",
                label=f"{ftype} (famille {family})",
                target_arg_id=str(tid),
                detail=_truncate(fdata.get("justification", ""), _JUSTIFICATION_CAP),
            )
        )
    for arg_id, semantics in dung_rejected.items():
        points.append(
            StructuringWeakPoint(
                source="dung",
                label=f"argument rejeté par le cadre de Dung (sémantique {semantics})",
                target_arg_id=str(arg_id),
            )
        )
    if pl_inc:
        points.append(
            StructuringWeakPoint(
                source="pl",
                label=f"{pl_inc} inférence(s) propositionnelle(s) inconsistantes (solveur Tweety)",
                target_arg_id="—",
            )
        )
    if fol_inc:
        points.append(
            StructuringWeakPoint(
                source="fol",
                label=f"{fol_inc} théorie(s) du premier ordre inconsistantes (solveur Tweety)",
                target_arg_id="—",
            )
        )
    return points


def _collect_quality_strengths(quality: Dict[str, Any]) -> List[QualityStrength]:
    """Surface the virtues where the discourse scores well (honest strengths).

    A strength is a virtue with a non-zero score on at least one argument.
    Aggregated as the max across arguments (the discourse's best tenue on that
    virtue) — surfaced so the LLM can acknowledge what holds, not only what
    breaks (the balanced "appréciations" beat, spec §1.3).
    """
    best: Dict[str, float] = {}
    for _arg, qs in quality.items():
        if not isinstance(qs, dict):
            continue
        # Canonical writer key is ``scores`` (shared_state.add_quality_score,
        # #1150/#1151); ``scores_par_vertu`` is the legacy key kept as a
        # fallback for any external source. Same {virtue: float} mapping.
        spv = qs.get("scores")
        if not isinstance(spv, dict):
            spv = qs.get("scores_par_vertu")
        if not isinstance(spv, dict):
            continue
        for vname, vval in spv.items():
            if isinstance(vval, (int, float)) and vval > 0:
                best[str(vname)] = max(best.get(str(vname), 0.0), float(vval))
    return [
        QualityStrength(virtue=k, score=v)
        for k, v in sorted(best.items(), key=lambda kv: kv[1], reverse=True)
    ]


def _collect_governance(state: Any) -> Optional[GovernanceVerdict]:
    """Collect the governance voting verdict (SV #1182).

    Reads ``state.governance_decisions``; surfaces the LAST non-trivial decision.
    Fail-loud: ``None`` when empty or winner is a placeholder ("N/A"/empty) —
    no fabricated verdict (#1019). Privacy: option keys stay opaque.
    """
    decisions = getattr(state, "governance_decisions", []) or []
    if not isinstance(decisions, list):
        return None
    chosen: Optional[GovernanceVerdict] = None
    for d in decisions:
        if not isinstance(d, dict):
            continue
        method = str(d.get("method", "")).strip()
        winner = str(d.get("winner", "")).strip()
        if not method or not winner or winner == "N/A":
            continue
        raw_scores = d.get("scores", {}) or {}
        scores: Dict[str, float] = {}
        if isinstance(raw_scores, dict):
            for k, v in raw_scores.items():
                try:
                    scores[str(k)] = float(v)
                except (TypeError, ValueError):
                    continue
        chosen = GovernanceVerdict(method=method, winner=winner, scores=scores)
    return chosen


def _collect_debate(state: Any) -> List[DebateExchange]:
    """Collect adversarial-debate exchanges (SV #1182). Gap β G8: can be sparse.

    Reads ``state.debate_transcripts``; surfaces ONLY non-empty exchanges
    (fail-loud: empty point+rebuttal would read as fabricated matter, #1019).
    """
    transcripts = getattr(state, "debate_transcripts", []) or []
    if not isinstance(transcripts, list):
        return []
    out: List[DebateExchange] = []
    for t in transcripts:
        if not isinstance(t, dict):
            continue
        exchanges = t.get("exchanges", []) or []
        if not isinstance(exchanges, list):
            continue
        for ex in exchanges:
            if not isinstance(ex, dict):
                continue
            point = _truncate(ex.get("point", ""), _DEBATE_CAP)
            rebuttal = _truncate(ex.get("rebuttal", ""), _DEBATE_CAP)
            if not point and not rebuttal:
                continue
            out.append(DebateExchange(point=point, rebuttal=rebuttal))
            if len(out) >= _DEBATE_MAX_EXCHANGES:
                return out
    return out


def _compute_verdict_band(
    axes_nontrivial: List[str],
) -> VerdictBand:
    """Compute the verdict band from the real analytical coverage.

    Honest adaptation of #1008 §2.1: the restitution report has no external
    analyst to compare against, so the band governs *how strongly the discourse
    may be characterised* based on how many analytical axes produced non-trivial
    content. The thresholds are transparent and fixed (anti-pendule: no curve).

    EXCEEDED needs formal depth (PL or FOL) AND the quality axis (a
    characterised discourse) on top of broad coverage — the "depth surpassing"
    spirit of #1008 §2.1, read as analytical depth rather than comparison.
    """
    all_axes = [
        _AXIS_FALLACIES,
        _AXIS_QUALITY,
        _AXIS_COUNTERS,
        _AXIS_FORMAL_PL,
        _AXIS_FORMAL_FOL,
        _AXIS_DUNG,
    ]
    present = set(axes_nontrivial)
    missing = [a for a in all_axes if a not in present]
    n = len(axes_nontrivial)
    has_formal_depth = _AXIS_FORMAL_PL in present or _AXIS_FORMAL_FOL in present
    has_quality = _AXIS_QUALITY in present

    if n >= _EXCEEDED_MIN_AXES and has_formal_depth and has_quality:
        band = _BAND_EXCEEDED
    elif n >= _MATCH_MIN_AXES:
        band = _BAND_MATCH
    elif n >= _PARTIAL_MIN_AXES:
        band = _BAND_PARTIAL
    else:
        band = _BAND_BELOW

    return VerdictBand(
        band=band,
        nontrivial_axes=list(axes_nontrivial),
        missing_axes=missing,
        axes_count=n,
    )


def build_act3_evidence(state: Any) -> Act3Evidence:
    """Build the deterministic Acte III evidence bundle from a shared state.

    No LLM, no JVM — pure state extraction. Privacy: corpus-derived fields are
    truncated; IDs stay opaque. The verdict band and the G1–G4 gate statuses are
    computed here (deterministic) so the orchestrator can gate the synthesis
    honestly.
    """
    args = getattr(state, "identified_arguments", {}) or {}
    fallacies = getattr(state, "identified_fallacies", {}) or {}
    quality = getattr(state, "argument_quality_scores", {}) or {}
    counters = getattr(state, "counter_arguments", []) or []

    if not isinstance(args, dict):
        args = {}
    if not isinstance(fallacies, dict):
        fallacies = {}
    if not isinstance(quality, dict):
        quality = {}
    if not isinstance(counters, list):
        counters = []

    args_total = len(args)
    fallacies_total = sum(1 for _f, d in fallacies.items() if isinstance(d, dict) and (d.get("target_argument_id") or ""))
    quality_axis_available = bool(quality)
    counters_total = sum(1 for c in counters if isinstance(c, dict) and (c.get("target_arg_id") or c.get("counter_content")))
    pl_inc = _pl_inconsistent(state)
    fol_inc = _fol_inconsistent(state)
    # D1c (#1167): a verified-consistent theory is a real formal result too —
    # the formal axis credits ANY verified verdict (satisfiable/consistent True
    # OR False), so a coherent text surfaces a non-trivial formal finding.
    pl_verified = _pl_verified(state)
    fol_verified = _fol_verified(state)
    dung_rejected = _dung_rejected_by_arg(state)

    # Non-trivial axes (real-in-state content), in a stable display order.
    axes_nontrivial: List[str] = []
    if fallacies_total:
        axes_nontrivial.append(_AXIS_FALLACIES)
    if quality_axis_available:
        axes_nontrivial.append(_AXIS_QUALITY)
    if counters_total:
        axes_nontrivial.append(_AXIS_COUNTERS)
    if pl_verified:
        axes_nontrivial.append(_AXIS_FORMAL_PL)
    if fol_verified:
        axes_nontrivial.append(_AXIS_FORMAL_FOL)
    if dung_rejected:
        axes_nontrivial.append(_AXIS_DUNG)

    weak_points = _collect_weak_points(fallacies, dung_rejected, pl_inc, fol_inc)
    counter_strategies: List[CounterStrategy] = []
    for ca in counters:
        if not isinstance(ca, dict):
            continue
        tid = ca.get("target_arg_id") or ""
        content = ca.get("counter_content") or ""
        if not (tid or content):
            continue
        # G6 (#1180): surface the validation verdict (absent → None, honest).
        validation = ca.get("validation")
        is_valid = None
        succeeds = None
        if isinstance(validation, dict):
            _iv = validation.get("is_valid_attack")
            _cs = validation.get("counter_succeeds")
            if isinstance(_iv, bool):
                is_valid = _iv
            if isinstance(_cs, bool):
                succeeds = _cs
        counter_strategies.append(
            CounterStrategy(
                strategy=str(ca.get("strategy", "")),
                target_arg_id=str(tid),
                snippet=_truncate(content, _COUNTER_CAP),
                is_valid_attack=is_valid,
                counter_succeeds=succeeds,
            )
        )

    quality_strengths = _collect_quality_strengths(quality)

    narrative_synthesis = getattr(state, "narrative_synthesis", None)
    narrative_synthesis_available = bool(
        narrative_synthesis and isinstance(narrative_synthesis, str) and narrative_synthesis.strip()
    )

    # SV (#1182): surface governance verdict + debate exchanges (debranched
    # capabilities — same fix shape as G6 for counter-arg validity).
    governance_verdict = _collect_governance(state)
    debate_exchanges = _collect_debate(state)

    # G1–G4 (#1008 §3.2). G3 passes once a band is computable (always, given the
    # deterministic scorer); G4 is structural (we only surface real-in-state
    # fields). The orchestrator emits the honest fallback when any gate fails.
    gates: Dict[str, bool] = {
        "G1_arguments_extracted": args_total > 0,
        "G2_one_dimension_nontrivial": len(axes_nontrivial) >= 1,
        "G3_verdict_computed": True,
        "G4_no_fabrication": True,
    }

    verdict = _compute_verdict_band(axes_nontrivial)
    virtuous_mode = detect_virtuous_mode(state)

    return Act3Evidence(
        args_total=args_total,
        fallacies_total=fallacies_total,
        counters_total=counters_total,
        quality_axis_available=quality_axis_available,
        quality_strengths=quality_strengths,
        weak_points=weak_points,
        counter_strategies=counter_strategies,
        verdict=verdict,
        narrative_synthesis_available=narrative_synthesis_available,
        gates=gates,
        virtuous_mode=virtuous_mode,
        governance_verdict=governance_verdict,
        debate_exchanges=debate_exchanges,
    )


# --- the conducted prompt (spec §4 weaving rule, no template) ----------------

_OPAQUE_ID_DIRECTIVE = (
    "DISCIPLINE D'IDENTIFIANTS OPAQUES (FB-34) — OBLIGATOIRE :\n"
    "- Désigne chaque argument par son ID opaque (arg_1, arg_2…), JAMAIS par un\n"
    "  nom de source, d'auteur, de lieu ou de date.\n"
    "- Ne reproduis JAMAIS de passage verbatim du texte source : paraphrase la\n"
    "  conclusion en une phrase qui dit quelque chose.\n"
    "- Les familles de sophismes (ad hominem, ad verecundiam…) sont des\n"
    "  constantes de taxonomie : tu peux les nommer comme ancrage."
)

_WEAVING_RULE = (
    "RÈGLE DE TISSAGE (spec §4) — le contrat anti-énumération :\n"
    "- CHAQUE citation d'un cadre (Tweety, Dung, taxonomie, vertus) DOIT être\n"
    "  ancrée narrativement : liée à (a) un argument localisé ET (b) le verdict\n"
    "  concret que ce cadre a produit.\n"
    "- INTERDIT : une ligne « nom + score isolé », ex. « ad verecundiam (0.8) ».\n"
    "  Ne produis JAMAIS de score entre parenthèses isolé comme (0.8) ou\n"
    "  « score 0.8 ». Les vertus sont le CARACTÈRE du discours, pas un tableau\n"
    "  de scores.\n"
    "- INTERDIT : numéroter en « Sophisme 1: » / « Argument 2: ». Donne aux\n"
    "  blocs des titres THÉMATIQUES en ### (ex. « Ce qui tient », « Ce qui\n"
    "  dérape et comment le contrer », « Les coups suivants probables »).\n"
    "- Le verdict formel appuie un battement narratif ; ce n'est jamais une\n"
    "  sous-section isolée."
)

_FAIL_LOUD_INSTRUCTION = (
    "HONNÊTETÉ (anti-pendule #1019/#369) :\n"
    "- La bande de verdict ci-dessous gouverne la force de ta caractérisation.\n"
    "  Ne formule JAMAIS un claim au-delà de ce que la bande autorise.\n"
    "- Si un axe est manquant (liste fournie), DIS-LE explicitement (« l'axe\n"
    "  qualité n'est pas concluable sur ce run »), ne le simule JAMAIS.\n"
    "- Si aucun point faible n'est localisé (texte vertueux), titre sur les\n"
    "  forces — la robustesse formelle, la tenue des schemes. Ne fabrique pas\n"
    "  de sophisme pour remplir un bloc."
)


def _band_claim_ceiling(band: str) -> str:
    """The allowed-claim ceiling per band (adapted from #1008 §2.2).

    Restitution framing (#1008 absorbed, spec §3): the band governs *how
    strongly the discourse may be characterised* — narrative, not a scorecard.
    """
    if band == _BAND_EXCEEDED:
        return (
            "Tu peux caractériser l'analyse comme APPROFONDIE et multi-axes : "
            "elle couvre largement les dimensions (dont la profondeur formelle "
            "vérifiée et le profil de qualité), et produit des verdicts "
            "vérifiables qui vont au-delà d'une lecture de surface. Cite les "
            "axes non-triviaux qui le justifient."
        )
    if band == _BAND_MATCH:
        return (
            "Tu peux caractériser l'analyse comme COMPLÈTE : elle couvre les "
            "axes principaux du discours. Nomme les axes touchés et ceux qui "
            "restent non-concluables, honnêtement."
        )
    if band == _BAND_PARTIAL:
        return (
            "Caractérise l'analyse comme PARTIELLE : elle touche certaines "
            "dimensions mais en manque de clés. Diagnostic honnête : nomme ce "
            "qui est couvert et ce qui manque (axes listés)."
        )
    # BELOW
    return (
        "Caractérise l'analyse comme MINIMALE : la couverture analytique est "
        "réduite. Donne la liste honnête des axes non-concluables. Ne rejette "
        "pas la responsabilité sur des facteurs externes (timeout, DLL) sans "
        "reconnaître la responsabilité du pipeline dans la dégradation gracieuse."
    )


def build_act3_prompt(evidence: Act3Evidence) -> str:
    """Build the §4-compliant LLM-conducted prompt for the Acte III conclusion.

    The prompt varies with the evidence (hence with the corpus) — it is not a
    static template (#1108/#405). It hands the LLM the gated verdict ceiling,
    the real strengths/weaknesses, and the actionable material (counters +
    structuring weak points), and instructs it to weave the three beats.
    """
    verdict = evidence.verdict

    # --- Synthèse honnête (gated) ---
    if verdict is not None:
        axes_present = ", ".join(verdict.nontrivial_axes) or "aucun axe non-trivial"
        axes_missing = ", ".join(verdict.missing_axes) or "aucun"
        synthesis_block = (
            f"Bande de verdict : {verdict.band} "
            f"(couverture analytique : {verdict.axes_count} axe(s) non-trivial(aux) "
            f"sur 6).\n"
            f"  Axes touchés : {axes_present}.\n"
            f"  Axes manquants / non-concluables : {axes_missing}.\n"
            f"  Plafond de claim autorisé : {_band_claim_ceiling(verdict.band)}"
        )
    else:
        synthesis_block = "Bande de verdict : NON CALCULABLE (gates G1–G4 non passés)."

    # --- Mode vertueux (spec §5) — titre sur les vertus quand l'état le dit ---
    vm = evidence.virtuous_mode
    is_virtuous = vm is not None and vm.is_virtuous
    if is_virtuous:
        virtuous_section = (
            "MODE VIRTUEUX (spec §5) — DÉCISION DE TITRE :\n"
            "Le TITRE de l'Acte III porte sur ce qui TIENT : les vertus mesurées,\n"
            "la robustesse formelle, la tenue des schemes. Le pipeline n'a localisé\n"
            "AUCUN sophisme sur ce texte — ce n'est pas un manque à combler, c'est\n"
            "le résultat honnête. Ne fabrique JAMAIS de sophisme ni de point faible\n"
            "pour remplir un battement (anti-pendule #1019/#369). Si un battement\n"
            "manque de matière faiblesse, titre sur la force qui le justifie.\n"
            f"Dérivation du flag : {vm.reasoning if vm is not None else ''}\n\n"
        )
        consigne_virtue = (
            "- MODE VIRTUEUX : ouvre la synthèse en caractérisant le discours par\n"
            "  ses vertus (ce qui tient). L'appréciation mène avec les forces ; les\n"
            "  faiblesses (si aucune localisée) s'effacent honnêtement. Le « que\n"
            "  faire » devient « comment s'appuyer sur ce qui tient / le préserver »\n"
            "  plutôt que « comment contrer ».\n"
        )
    else:
        virtuous_section = ""
        consigne_virtue = ""

    # --- Appréciations (forces + faiblesses) ---
    if evidence.quality_strengths:
        strengths_lines = "\n".join(
            f"  - {s.virtue} (meilleur score du discours : {s.score:.1f})"
            for s in evidence.quality_strengths[:6]
        )
    else:
        strengths_lines = (
            "  (axe qualité non concluable — aucune vertu caractérisée à "
            "acknowledger)"
        )
    if evidence.weak_points:
        weaknesses_lines = "\n".join(
            f"  - [{wp.source}] {wp.label} sur {wp.target_arg_id}"
            + (f" : {wp.detail}" if wp.detail else "")
            for wp in evidence.weak_points[:8]
        )
    else:
        weaknesses_lines = (
            "  (aucun point faible localisé — texte vertueux : titre sur la "
            "robustesse formelle et la tenue des schemes)"
        )

    # --- Que faire (actionnable) ---
    if evidence.counter_strategies:
        counters_lines = "\n".join(
            f"  - Pour contrer {cs.target_arg_id} ({cs.strategy}) : {cs.snippet}"
            for cs in evidence.counter_strategies[:8]
        )
    else:
        counters_lines = "  (aucun contre-argument généré — recommandations de contre limitées aux exceptions de scheme)"

    target_lines = (
        "\n".join(
            f"  - {wp.label} sur {wp.target_arg_id} (ancre : {wp.source})"
            for wp in evidence.weak_points if wp.source in ("fallacy", "pl", "fol", "dung")
        )
        or "  (aucun point faible structurel à viser identifié)"
    )

    what_next_block = (
        "  À quoi s'attendre ensuite : referme la boucle sur le cadrage "
        "game-theoretic de l'Acte I — les coups probables que l'orateur peut "
        "jouer ensuite pour esquiver les faiblesses signalées (doubler la mise "
        "sur l'autorité, glisser d'une attaque à une autre, amplification "
        "émotive). Ne fabrique pas de coups : déduis-les des faiblesses "
        "localisées."
    )

    # --- SV (#1182): délibération collective (governance + debate) ---
    deliberation_lines: List[str] = []
    gv = evidence.governance_verdict
    if gv is not None:
        deliberation_lines.append(
            f"  - GOUVERNANCE : méthode « {gv.method} » — l'option {gv.winner} "
            "sort gagnante du vote social-choice. (options opaques, FB-34.)"
        )
    if evidence.debate_exchanges:
        for i, ex in enumerate(evidence.debate_exchanges, start=1):
            deliberation_lines.append(
                f"  - DÉBAT (échange {i}) : position « {ex.point} » / "
                f"réplique « {ex.rebuttal} »."
            )
    deliberation_block = (
        "\n".join(deliberation_lines)
        if deliberation_lines
        else "  (aucune délibération governance/débat non-triviale — ne la fabrique pas)"
    )

    return (
        "Tu es l'auteur de l'ACTE III d'un rapport de restitution argumentative\n"
        "— la CONCLUSION ACTIONNABLE : ce que le lecteur FAIT de l'analyse.\n"
        "Trois battements en prose :\n"
        "1. Synthèse honnête (verdict gated sur la bande — pas de sur-claim) ;\n"
        "2. Appréciations (forces ET faiblesses du discours, équilibré) ;\n"
        "3. Que faire : comment CONTRER, les POINTS FAIBLES À VISER, à quoi\n"
        "   S'ATTENDRE ENSUITE (retour au cadrage game-theoretic de l'Acte I).\n\n"
        f"{_OPAQUE_ID_DIRECTIVE}\n\n"
        f"{_WEAVING_RULE}\n\n"
        f"{_FAIL_LOUD_INSTRUCTION}\n\n"
        f"{virtuous_section}"
        "DONNÉES VERIFIÉES DANS LE STATE (ne citer que celles-ci) :\n\n"
        f"[SYNTHÈSE HONNÊTE — verdict gated]\n{synthesis_block}\n\n"
        f"[APPRÉCIATIONS — forces (qualité)]\n{strengths_lines}\n\n"
        f"[APPRÉCIATIONS — faiblesses localisées]\n{weaknesses_lines}\n\n"
        f"[QUE FAIRE — comment contrer]\n{counters_lines}\n\n"
        f"[QUE FAIRE — points faibles à viser]\n{target_lines}\n\n"
        f"[DÉLIBÉRATION COLLECTIVE — governance + débat]\n{deliberation_block}\n\n"
        f"{what_next_block}\n\n"
        "CONSIGNE DE RÉDACTION :\n"
        f"{consigne_virtue}"
        "- Rédige 3 paragraphes thématiques (un par battement), en prose lisible,\n"
        "  pas une liste de champs. Titres thématiques en ###.\n"
        "- Le verdict formel (Tweety/Dung) appuie un battement : formule-le comme\n"
        "  « le solveur Tweety invalide cette inférence » (théorie inconsistante),\n"
        "  « le solveur Tweety confirme la cohérence de cette inférence »\n"
        "  (théorie consistante — un résultat formel aussi) ou « le cadre de Dung\n"
        "  isole cet argument comme rejeté/défaillant » (argument absent de\n"
        "  l'extension acceptée) — jamais une sous-section isolée.\n"
        "- Respecte STRICTEMENT le plafond de claim de la bande : ne formule rien\n"
        "  au-delà de ce qu'elle autorise.\n"
        "- La conclusion doit VARIER selon le contenu réel ci-dessus : pas de\n"
        "  prose générique recyclable.\n"
        "- Rédige en français, markdown léger. 300-600 mots selon la richesse.\n"
    )


# --- LLM-conducted weaving (fail-loud) ---------------------------------------


async def weave_act3_conclusion(
    evidence: Act3Evidence, llm_callable: LlmCallable
) -> str:
    """Conduct the Acte III conclusion via the LLM (fail-loud, #1108).

    Returns the LLM-produced markdown, or an empty string if the LLM produced
    nothing (the caller records the explicit ``unavailable`` status). No
    template fallback — anti-pendule #1019/#369.
    """
    prompt = build_act3_prompt(evidence)
    try:
        raw = await llm_callable(prompt)
    except Exception as exc:  # noqa: BLE001 — surface, don't fabricate
        logger.warning("Acte III LLM weaving failed (fail-loud): %s", exc)
        return ""
    if not raw:
        return ""
    return str(raw).strip()


# --- orchestrator ------------------------------------------------------------


async def build_act3_conclusion(
    state: Any, llm_callable: Optional[LlmCallable] = None
) -> Act3Result:
    """Build the Acte III actionable conclusion for ``state``.

    Deterministic evidence is always built (including the gated verdict band and
    the G1–G4 statuses). The conclusion is LLM-conducted only when
    ``llm_callable`` is provided; otherwise the result is fail-loud
    (``status="unavailable"``, empty narrative) — the renderer reports the gap
    honestly, never a template (#1108).

    G1–G4 (#1008 §3.2) gate the *gated synthesis* beat: on any gate failure the
    LLM is still conducted for the *appreciations* and *que-faire* beats (those
    do not require a comparative verdict), but the synthesis beat carries the
    honest fallback wording. A §4 self-check (``ReadabilityGate``) is attached
    to every woven result so the verdict is auditable; it never fabricates a
    pass.
    """
    evidence = build_act3_evidence(state)

    gates = evidence.gates
    failed_gates = [g for g, ok in gates.items() if not ok]

    if not gates["G1_arguments_extracted"]:
        # No substrate at all — the whole conclusion is fail-loud.
        return Act3Result(
            narrative="",
            status="empty_state",
            degraded={
                "act3_conclusion": (
                    "Aucun argument extrait — l'Acte III n'a pas de substrat à "
                    "conclure (G1 échoué : identified_arguments vide)."
                )
            },
        )

    if llm_callable is None:
        return Act3Result(
            narrative="",
            status="unavailable",
            degraded={
                "act3_conclusion": (
                    "Conclusion non conduite — aucun LLM injecté pour l'Acte III "
                    "(fail-loud, #1108)."
                )
            },
        )

    # If a gate beyond G1 failed, flag it: the synthesis beat must carry the
    # honest fallback, but we still conduct the LLM for the other beats and
    # attach the gate status so nothing is silently weakened.
    gate_note = ""
    if failed_gates:
        gate_note = (
            f"Gates G1–G4 : {', '.join(failed_gates)} non passé(s). La synthèse "
            "doit porter le wording de repli honnête (#1008 §3.3) — pas de "
            "verdict comparatif."
        )
        # Re-flag the verdict as ungated so the prompt's synthesis beat degrades.
        evidence.verdict = None

    narrative = await weave_act3_conclusion(evidence, llm_callable)
    if not narrative:
        return Act3Result(
            narrative="",
            status="unavailable",
            degraded={
                "act3_conclusion": (
                    "Conclusion indisponible — le LLM n'a rien produit "
                    "(fail-loud, #1108)."
                )
            },
        )

    # §4 self-check (honest, never grades on a curve).
    gate = ReadabilityGate()
    verdict = gate.check_body(narrative)
    degraded: Dict[str, str] = {}
    if verdict.band != "PASS":
        degraded["act3_conclusion_gate"] = (
            f"Self-check §4 = {verdict.band}: " + "; ".join(verdict.reasons[:3])
        )
    if gate_note:
        degraded["act3_conclusion_gates"] = gate_note
    if not evidence.quality_axis_available:
        degraded["act3_conclusion"] = (
            "Axe qualité non concluable ici (argument_quality_scores "
            "indisponible) — appréciations limitées aux faiblesses, fail-loud."
        )
    vm = evidence.virtuous_mode
    is_virtuous = vm is not None and vm.is_virtuous
    if vm is not None and vm.is_virtuous:
        degraded["act3_virtuous_mode"] = (
            "Mode vertueux (spec §5) — titre sur les vertus. " + vm.reasoning
        )
    elif not evidence.weak_points:
        # Defensive: no weak points AND not flagged virtuous (an empty-ish run
        # that still passed G1). Honest note — not a positive virtuous claim,
        # since no non-trivial axis qualified the text as virtuous.
        degraded["act3_conclusion"] = (
            "Aucun point faible localisé et aucun axe vertueux non-trivial — "
            "la conclusion titre sur les forces disponibles sans claim vertueux "
            "non dérivé (fail-loud)."
        )

    return Act3Result(
        narrative=narrative,
        status="woven",
        gate_verdict=verdict,
        degraded=degraded,
        is_virtuous=is_virtuous,
    )
