"""Acte II generator — dialectical narrative by argumentative movement.

Epic #1134 (Restitution) / Track R3 #1137. LLM-conducted, woven per spec §4.
Consumed by the R6 renderer to populate ``RestitutionActs.act2_narrative``.

Design (spec §1.2 + §4 + §7, dispatch coord R427):
  - Cut by argumentative **movement** (a cluster of arguments sharing a
    rhetorical fate — attacked by the same fallacy family, or the un-attacked
    "soutiens" that hold), **not** by analytical dimension.
  - Each movement beat weaves the argument + its virtues (quality, as
    *character*) + its dérapages (localized fallacies w/ descent + counter-args)
    + its formal tenue (PL/FOL/Dung cited as PROOF, never a standalone block).
  - Every framework citation gets a narrative anchor (passes the §4 gate — this
    module self-checks its own output with ``ReadabilityGate``).
  - **LLM-conducted**: the narrative VARIES by corpus (no template #1108/#405).
    Fail-loud when no LLM is injected — empty string + explicit status; the
    renderer reports the gap honestly (anti-pendule #1019/#369).

Privacy HARD: opaque IDs only (``arg_N``, fallacy families are taxonomy
constants). The prompt carries the OPAQUE_ID_DIRECTIVE (FB-34). Corpus-derived
fields (argument descriptions, fallacy justifications, counter-content) are
**truncated** before entering the prompt and the LLM is instructed to
**paraphrase the move, never echo verbatim text** — the final R6 scrub (spec
§6) is the downstream guard.

Testability: ``build_act2_evidence`` is deterministic (no LLM/JVM/API); the LLM
is an injectable async callable ``Callable[[str], Awaitable[str]]`` (FB-29/38
injectable-LLM pattern), so unit tests pass a stub and need no kernel.
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
_DESC_CAP = 220
_JUSTIFICATION_CAP = 200
_COUNTER_CAP = 200
# SV (#1182): truncation + count caps for governance/debate evidence (privacy
# + prompt-budget discipline; the LLM paraphrases, never echoes).
_DEBATE_CAP = 220
_DEBATE_MAX_EXCHANGES = 6

# Fallacy families form the mouvement theme (taxonomy constants, not source
# content — safe to surface). The reserved theme for arguments no fallacy
# targets — the claims that hold.
_SOUTIENS_THEME = "soutiens"


# --- evidence dataclasses ----------------------------------------------------


@dataclass
class FallacyEvidence:
    """One localized fallacy attacking an argument."""

    fallacy_id: str
    family: str
    type: str
    taxonomy_path: str
    justification: str
    target_arg_id: str


@dataclass
class CounterEvidence:
    """One counter-argument generated against an argument."""

    strategy: str
    target_arg_id: str
    snippet: str
    # G6 (#1180): validation verdict (ValidationResult shape) so the narrative
    # can cite counter-argument *validity*. None when the evaluator did not run.
    is_valid_attack: Optional[bool] = None
    counter_succeeds: Optional[bool] = None


@dataclass
class ArgEvidence:
    """Per-argument evidence woven into a movement beat."""

    arg_id: str
    description: str
    virtues: Dict[str, float] = field(default_factory=dict)
    quality_overall: Optional[float] = None
    quality_available: bool = False
    fallacies: List[FallacyEvidence] = field(default_factory=list)
    counter_args: List[CounterEvidence] = field(default_factory=list)
    dung_rejected: Optional[str] = None  # semantics label, if rejected


@dataclass
class MovementEvidence:
    """A cluster of arguments sharing a rhetorical fate (the mouvement)."""

    movement_id: str
    theme: str  # family name (taxonomy constant) or "soutiens"
    arguments: List[ArgEvidence] = field(default_factory=list)


@dataclass
class FormalFinding:
    """A global formal-tenue anchor the LLM weaves as backing (verified-in-state)."""

    kind: str  # "pl" | "fol" | "dung"
    verdict: (
        str  # human-readable, e.g. "inconsistant (Tweety)", "rejet (Dung grounded)"
    )
    detail: str


@dataclass
class DungSolverTrace:
    """Concrete Dung computation trace (opaque IDs) for honest framing.

    Track D #1280 — the restitution used to say « Dung rejette X » ~15× while
    presenting the framework as an *external oracle*. In reality the attack
    graph is **built from the extracted arguments** (the pipeline's own attacks),
    so Dung only reorganises what the upstream extraction produced — it is not
    an independent corroboration. This trace surfaces the actual computation
    (graph size, accepted members, rejected args, a sample of the attack
    relations) so the narrative can frame it honestly: « le graphe construit à
    partir des arguments extraits donne… ». All IDs stay opaque (arg_N, never
    source text) — privacy HARD.
    """

    available: bool = False  # False when no verification_* framework was written
    semantics_label: str = ""  # e.g. "grounded", "preferred" — the primary one surfaced
    n_arguments: int = 0
    n_attacks: int = 0
    accepted_members: List[str] = field(
        default_factory=list
    )  # opaque arg_ids in the extension
    rejected_args: Dict[str, str] = field(
        default_factory=dict
    )  # arg_id -> semantics label
    sample_attacks: List[List[str]] = field(
        default_factory=list
    )  # up to N opaque [attacker, target] pairs


@dataclass
class GovernanceVerdict:
    """A governance voting decision (7-method social-choice layer), verified-in-state.

    SV (#1182): the spectacular pipeline runs a governance phase (7 voting methods,
    Copeland winner, consensus) but it was invisible in the report — the same
    debranching G6 fixed for counter-argument validity. ``scores`` maps opaque
    option IDs → Copeland/influence score (privacy: opaque keys, never party names).

    Track E #1281 — ``extraction_method`` carries the honest origin signal so the
    restitution can frame the verdict correctly. ``"llm"`` means the assessment was
    produced by a SINGLE LLM call dressed as governance (NOT a genuine multi-agent
    deliberation); the narrative must then present it as a model-assessed ranking,
    not procedural legitimacy. ``None`` = origin not recorded (caller pre-#1281);
    the prompt then falls back to its prior framing.
    """

    method: str
    winner: str
    scores: Dict[str, float] = field(default_factory=dict)
    extraction_method: Optional[str] = None  # "llm" | "heuristic" | None


@dataclass
class DebateExchange:
    """One Walton-Krabbe adversarial-debate exchange (point vs rebuttal).

    SV (#1182): the debate phase produces key exchanges. NB (gap β G8): the
    schemes-engine (student ``ArgumentationEngine`` 10 schemes) was dropped in the
    #35 unification → exchanges can be sparse. We surface what exists honestly
    and never fabricate a rich debate (#1019). G8 is a separate follow-up.

    G8 (#1184) CLOSED: the 10-scheme engine is restored; each exchange now
    carries the Walton ``scheme`` it relies on + its ``critical_question`` when
    the deterministic classifier matched (None when no scheme fit — honest, not
    fabricated). The SV reader contract (point/rebuttal) is preserved.
    """

    point: str
    rebuttal: str
    scheme: Optional[str] = None
    critical_question: Optional[str] = None


@dataclass
class Act2Evidence:
    """Deterministic evidence bundle for the Acte II narrative."""

    movements: List[MovementEvidence] = field(default_factory=list)
    formal_findings: List[FormalFinding] = field(default_factory=list)
    quality_axis_available: bool = True
    # SV (#1182): governance voting verdict + adversarial-debate exchanges,
    # surfaced so the narrative can cite them. Empty/None when the phases did
    # not produce non-trivial output (honest absence, not fabricated).
    governance_verdict: Optional[GovernanceVerdict] = None
    debate_exchanges: List[DebateExchange] = field(default_factory=list)
    args_total: int = 0
    fallacies_total: int = 0
    # Note (a) (#1153): fallacies whose target_argument_id could not be
    # resolved to an identified argument. These cannot join a movement beat,
    # but they ARE counted (here) rather than silently dropped (#1019) — the
    # LLM/rapport surfaces them honestly as "non rattaché(s) à un argument
    # identifié". ``fallacies_total`` counts only the attributed ones.
    unattributed_fallacies: int = 0
    # DERIVED virtuous flag (spec §5.1) — when the state characterises the text
    # as virtuous, the narrative leads with WHY THE ARGUMENTATION HOLDS (the
    # soutiens movement becomes the centrepiece; formal tenue is the proof).
    virtuous_mode: Optional[VirtuousModeAssessment] = None
    # Epic #1258 / Track 1 #1259 — when True, build_act2_prompt DROPS the
    # opaque-ID directive so the readable restitution names the real argument.
    deanonymized: bool = True


@dataclass
class Act2Result:
    """Outcome of :func:`build_act2_narrative`.

    ``status`` is one of ``"woven"`` (LLM produced a narrative), ``"unavailable"``
    (no LLM injected or LLM failed — fail-loud, #1108), ``"empty_state"`` (no
    arguments to narrate). ``gate_verdict`` is the honest §4 self-check.
    """

    narrative: str
    status: str
    gate_verdict: Optional[GateVerdict] = None
    degraded: Dict[str, str] = field(default_factory=dict)
    # True when the narrative was conducted leading with why the argumentation
    # holds (spec §5) — the virtuous reading.
    is_virtuous: bool = False


# --- deterministic evidence builder (no LLM) ---------------------------------


def _truncate(text: Any, cap: int) -> str:
    """Coerce to str and cap length (privacy + prompt budget)."""
    if not text:
        return ""
    s = str(text).strip()
    return s if len(s) <= cap else s[:cap].rstrip() + " […]"


def _dung_rejected_by_arg(state: Any) -> Dict[str, str]:
    """Map arg_id → Dung semantics label for arguments rejected by a framework.

    Mirrors the resolution logic of ``narrative_synthesis_plugin._dung_rejected_args``
    (kept local here for file-disjointness — R3 establishes its own pattern).
    A rejected argument is one present in a framework's arguments but absent
    from its accepted extension.
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
        # Finding D (#1151/#1153): add_dung_framework stores no ``semantics``
        # key — the writer folds it into ``name=f"verification_{semantics}"``
        # (state_writers.py:717). Prefer an explicit key if present, else parse
        # it back from ``name``; only default to ``grounded`` when neither
        # carries a signal (honest: the label stays, but it is now correct when
        # the name encodes the semantics).
        semantics = fw.get("semantics")
        if not semantics:
            name = str(fw.get("name", "") or "")
            if name.startswith("verification_"):
                semantics = name[len("verification_") :]
        semantics = str(semantics or "grounded")
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


# Cap on how many attack relations we surface in the trace / prompt. The full
# attack list can be long; a representative sample suffices to make the graph
# inspectable without blowing the prompt budget (privacy + budget discipline).
_TRACE_ATTACK_SAMPLE = 4


def _collect_dung_trace(state: Any) -> DungSolverTrace:
    """Collect the concrete Dung computation trace for honest framing (#1280).

    Reads ``state.dung_frameworks`` (written by ``state_writers`` as
    ``verification_{semantics}`` entries carrying ``arguments`` + ``attacks`` +
    ``extensions``). The attack graph is **built from the extracted arguments**,
    so this trace lets the restitution frame the result as « le graphe construit
    à partir des arguments extraits donne… » rather than as an external oracle.

    Picks the primary framework (preferred → grounded → first verification_*),
    then records graph size, the accepted extension members, the rejected args
    (reusing ``_dung_rejected_by_arg``), and a capped sample of attack pairs.
    All IDs opaque (arg_N) — privacy HARD. Returns ``available=False`` when no
    verification framework was written (honest absence, not fabricated).
    """
    frameworks = getattr(state, "dung_frameworks", {}) or {}
    if not isinstance(frameworks, dict):
        return DungSolverTrace()
    # Prefer the semantics the pipeline surfaces as primary (preferred, then
    # grounded), then any verification_* entry as a last resort.
    primary: Optional[Dict[str, Any]] = None
    primary_sem = ""
    for pref in ("preferred", "grounded"):
        for _fid, fw in frameworks.items():
            if not isinstance(fw, dict):
                continue
            name = str(fw.get("name", "") or "")
            if name == f"verification_{pref}":
                primary = fw
                primary_sem = pref
                break
        if primary is not None:
            break
    if primary is None:
        for _fid, fw in frameworks.items():
            if not isinstance(fw, dict):
                continue
            name = str(fw.get("name", "") or "")
            if name.startswith("verification_"):
                primary = fw
                primary_sem = name[len("verification_") :] or "grounded"
                break
    if primary is None:
        return DungSolverTrace()

    fw_args = primary.get("arguments", []) or []
    fw_args = fw_args if isinstance(fw_args, list) else []
    fw_attacks = primary.get("attacks", []) or []
    fw_attacks = fw_attacks if isinstance(fw_attacks, list) else []

    # Accepted extension members (opaque arg_ids).
    accepted: List[str] = []
    ext = primary.get("extensions", [])
    if isinstance(ext, dict) and "all_members" in ext:
        members = ext.get("all_members", []) or []
        accepted = [str(m) for m in members if isinstance(m, str)]
    elif isinstance(ext, dict):
        for val in ext.values():
            if isinstance(val, list):
                for item in val:
                    if isinstance(item, list):
                        accepted.extend(str(x) for x in item if isinstance(x, str))
                    elif isinstance(item, str):
                        accepted.append(item)
        accepted = sorted(set(accepted))
    elif isinstance(ext, list):
        for item in ext:
            if isinstance(item, list):
                accepted.extend(str(x) for x in item if isinstance(x, str))
            elif isinstance(item, str):
                accepted.append(item)
        accepted = sorted(set(accepted))

    # Rejected args (arg present in the framework but absent from the accepted
    # extension) — reuse the canonical resolver so the labels stay consistent
    # with the per-argument ``dung_rejected`` beat.
    rejected = _dung_rejected_by_arg(state)

    sample_attacks: List[List[str]] = []
    for pair in fw_attacks:
        if (
            isinstance(pair, (list, tuple))
            and len(pair) >= 2
            and isinstance(pair[0], str)
            and isinstance(pair[1], str)
        ):
            sample_attacks.append([pair[0], pair[1]])
        if len(sample_attacks) >= _TRACE_ATTACK_SAMPLE:
            break

    return DungSolverTrace(
        available=True,
        semantics_label=primary_sem or "grounded",
        n_arguments=len(fw_args),
        n_attacks=len(fw_attacks),
        accepted_members=accepted,
        rejected_args=rejected,
        sample_attacks=sample_attacks,
    )


def _quality_axis_usable(quality: Any) -> bool:
    """§5 gate (#1153): is the quality axis *usable*, not merely present?

    The old gate ``bool(quality)`` stayed ``True`` for a non-empty dict whose
    entries were unusable (no overall, no per-virtue scores) — a silent bug that
    hid Finding A (#1151). This gate requires at least one scored entry to carry
    a usable ``overall`` OR a usable per-virtue map (under the canonical
    ``scores`` key or the legacy ``scores_par_vertu``).

    Calibrated, NOT over-strict (anti-pendule): a single usable entry suffices
    (we degrade the unusable ones per-entry, not the whole axis); we never
    require ALL virtues populated (some args are short/degraded with overall
    only). An empty/partial-but-empty axis returns ``False`` → the report
    fail-louds « non concluable » honestly.
    """
    if not isinstance(quality, dict) or not quality:
        return False
    for entry in quality.values():
        if not isinstance(entry, dict):
            continue
        ov = entry.get("overall")
        if isinstance(ov, (int, float)):
            return True
        spv = entry.get("scores")
        if not isinstance(spv, dict):
            spv = entry.get("scores_par_vertu")
        if isinstance(spv, dict) and spv:
            return True
    return False


def build_act2_evidence(state: Any) -> Act2Evidence:
    """Build the deterministic Acte II evidence bundle from a shared state.

    Groups ``identified_arguments`` into movements by the fallacy family that
    targets them (the family IS the movement theme); arguments no fallacy
    targets fall into the ``soutiens`` movement (the claims that hold). This
    realises the spec §1.2 *thèse → soutiens → dérapages* thread: each attacked
    movement is a dérapage, the un-attacked cluster is the soutien.

    No LLM, no JVM — pure state extraction. Privacy: corpus-derived fields are
    truncated; IDs stay opaque.
    """
    args = getattr(state, "identified_arguments", {}) or {}
    fallacies = getattr(state, "identified_fallacies", {}) or {}
    quality = getattr(state, "argument_quality_scores", {}) or {}
    counters = getattr(state, "counter_arguments", []) or []

    quality_axis_available = _quality_axis_usable(quality)
    if not isinstance(args, dict):
        args = {}
    if not isinstance(fallacies, dict):
        fallacies = {}
    if not isinstance(counters, list):
        counters = []

    # Index fallacies by target arg.
    fallacy_by_arg: Dict[str, List[FallacyEvidence]] = {}
    fallacies_total = 0
    unattributed_fallacies = 0  # Note (a) (#1153): traced, not dropped (#1019)
    for _fid, fdata in fallacies.items():
        if not isinstance(fdata, dict):
            continue
        tid = fdata.get("target_argument_id") or ""
        if not tid:
            # Note (a): no resolved target — count it apart so the report can
            # surface it honestly instead of silently losing the detection.
            unattributed_fallacies += 1
            continue
        fallacies_total += 1
        fallacy_by_arg.setdefault(tid, []).append(
            FallacyEvidence(
                fallacy_id=str(_fid),
                family=str(fdata.get("family", "inconnu")),
                type=str(fdata.get("type", "inconnu")),
                taxonomy_path=str(fdata.get("taxonomy_path", "")),
                justification=_truncate(
                    fdata.get("justification", ""), _JUSTIFICATION_CAP
                ),
                target_arg_id=str(tid),
            )
        )

    # Index counters by target arg.
    counter_by_arg: Dict[str, List[CounterEvidence]] = {}
    for ca in counters:
        if not isinstance(ca, dict):
            continue
        tid = ca.get("target_arg_id") or ""
        if not tid:
            continue
        validation = ca.get("validation")
        is_valid_attack = None
        counter_succeeds = None
        if isinstance(validation, dict):
            iva = validation.get("is_valid_attack")
            if isinstance(iva, bool):
                is_valid_attack = iva
            cs = validation.get("counter_succeeds")
            if isinstance(cs, bool):
                counter_succeeds = cs
        counter_by_arg.setdefault(tid, []).append(
            CounterEvidence(
                strategy=str(ca.get("strategy", "")),
                target_arg_id=str(tid),
                snippet=_truncate(ca.get("counter_content", ""), _COUNTER_CAP),
                is_valid_attack=is_valid_attack,
                counter_succeeds=counter_succeeds,
            )
        )

    dung_rejected = _dung_rejected_by_arg(state)

    # Assign each argument a movement key = primary fallacy family (sorted for
    # determinism) or the soutiens theme if un-attacked.
    movement_key_by_arg: Dict[str, str] = {}
    for arg_id in args:
        flist = fallacy_by_arg.get(arg_id, [])
        if flist:
            families = sorted({f.family for f in flist if f.family})
            key = families[0] if families else "inconnu"
        else:
            key = _SOUTIENS_THEME
        movement_key_by_arg[arg_id] = key

    # Build movement evidence, ordering attack-movements first (alphabetical
    # theme) then the soutiens movement last — the claims that hold close the
    # thread.
    movements_by_key: Dict[str, MovementEvidence] = {}

    def _movement_for(key: str) -> MovementEvidence:
        if key not in movements_by_key:
            mid = (
                f"mvt_{_SOUTIENS_THEME}"
                if key == _SOUTIENS_THEME
                else f"mvt_{key}".replace(" ", "_")
            )
            movements_by_key[key] = MovementEvidence(movement_id=mid, theme=key)
        return movements_by_key[key]

    for arg_id, desc in args.items():
        key = movement_key_by_arg[arg_id]
        mvt = _movement_for(key)
        qs = quality.get(arg_id) if isinstance(quality, dict) else None
        virtues: Dict[str, float] = {}
        q_overall: Optional[float] = None
        q_available = False
        if isinstance(qs, dict):
            q_available = True
            # Finding A (#1151/#1153): the writer add_quality_score stores
            # per-virtue scores under the canonical key ``scores``
            # (shared_state.py:536); read that first, then the legacy
            # ``scores_par_vertu`` key for any external source. Both shapes
            # carry the same {virtue: float} mapping.
            spv = qs.get("scores")
            if not isinstance(spv, dict):
                spv = qs.get("scores_par_vertu")
            if isinstance(spv, dict):
                for vname, vval in spv.items():
                    if isinstance(vval, (int, float)):
                        virtues[str(vname)] = float(vval)
            ov = qs.get("overall")
            if isinstance(ov, (int, float)):
                q_overall = float(ov)
        mvt.arguments.append(
            ArgEvidence(
                arg_id=str(arg_id),
                description=_truncate(desc, _DESC_CAP),
                virtues=virtues,
                quality_overall=q_overall,
                quality_available=q_available,
                fallacies=fallacy_by_arg.get(arg_id, []),
                counter_args=counter_by_arg.get(arg_id, []),
                dung_rejected=dung_rejected.get(str(arg_id)),
            )
        )

    attack_keys = sorted(k for k in movements_by_key if k != _SOUTIENS_THEME)
    ordered: List[MovementEvidence] = [movements_by_key[k] for k in attack_keys]
    if _SOUTIENS_THEME in movements_by_key:
        ordered.append(movements_by_key[_SOUTIENS_THEME])

    formal_findings = _collect_formal_findings(state)
    virtuous_mode = detect_virtuous_mode(state)
    # SV (#1182): surface governance verdict + debate exchanges (debranched
    # capabilities — same fix shape as G6 for counter-arg validity).
    governance_verdict = _collect_governance(state)
    debate_exchanges = _collect_debate(state)

    return Act2Evidence(
        movements=ordered,
        formal_findings=formal_findings,
        quality_axis_available=quality_axis_available,
        args_total=len(args),
        fallacies_total=fallacies_total,
        unattributed_fallacies=unattributed_fallacies,
        virtuous_mode=virtuous_mode,
        governance_verdict=governance_verdict,
        debate_exchanges=debate_exchanges,
        deanonymized=bool(getattr(state, "deanonymized", True)),
    )


def _collect_governance(state: Any) -> Optional[GovernanceVerdict]:
    """Collect the governance voting verdict (SV #1182, spec §1.2.4 social-choice).

    Reads ``state.governance_decisions`` (written by
    ``state_writers._write_governance_to_state``). Each entry carries the
    recommended voting ``method``, the ``winner`` (Copeland / recommended
    resolution), and per-option ``scores``. We surface the LAST decision (the
    terminal aggregation) — fail-loud: return ``None`` when the list is empty
    or carries no non-trivial winner/scores (no fabricated verdict, #1019).

    Privacy: option keys are kept as-is (opaque IDs from the pipeline). The
    writer already scrubs source names; we never echo raw option labels.
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
        raw_scores = d.get("scores", {}) or {}
        scores: Dict[str, float] = {}
        if isinstance(raw_scores, dict):
            for k, v in raw_scores.items():
                try:
                    scores[str(k)] = float(v)
                except (TypeError, ValueError):
                    continue
        # Trivial / placeholder winners ("N/A", empty) carry no verdict.
        if not method or not winner or winner == "N/A":
            continue
        # Track E #1281 — carry the honest origin signal so the prompt can frame
        # an LLM-assessed verdict as model-assessed, not procedural legitimacy.
        em_raw = d.get("extraction_method")
        extraction_method = (
            str(em_raw).strip() if isinstance(em_raw, str) and em_raw.strip() else None
        )
        chosen = GovernanceVerdict(
            method=method,
            winner=winner,
            scores=scores,
            extraction_method=extraction_method,
        )
    return chosen


def _collect_debate(state: Any) -> List[DebateExchange]:
    """Collect adversarial-debate key exchanges (SV #1182, spec §1.2.4).

    Reads ``state.debate_transcripts`` (written by
    ``state_writers._write_debate_to_state``). Each transcript carries a list of
    ``exchanges`` (point + rebuttal). Gap β G8: the schemes-engine was dropped in
    #35 unification → exchanges can be sparse; we surface ONLY the real, non-empty
    ones and never invent exchanges (#1019). Capped to keep the prompt budget sane.
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
            # Fail-loud: skip empty exchanges (no point AND no rebuttal) — they
            # would read as fabricated debate matter (#1019).
            if not point and not rebuttal:
                continue
            # G8 (#1184): carry the scheme grounding (None when no scheme matched
            # — honest absence, not fabricated).
            scheme_raw = ex.get("scheme")
            scheme = (
                str(scheme_raw).strip()
                if isinstance(scheme_raw, str) and scheme_raw.strip()
                else None
            )
            cq_raw = ex.get("critical_question")
            critical_question = (
                str(cq_raw).strip()
                if isinstance(cq_raw, str) and cq_raw.strip()
                else None
            )
            out.append(
                DebateExchange(
                    point=point,
                    rebuttal=rebuttal,
                    scheme=scheme,
                    critical_question=critical_question,
                )
            )
            if len(out) >= _DEBATE_MAX_EXCHANGES:
                return out
    return out


def _pl_verdict(result: Dict[str, Any]) -> Optional[bool]:
    """Resolve a PL analysis verdict from a stored result dict.

    Finding C (#1151/#1153): the canonical writer key is ``satisfiable``
    (shared_state.py:801); the legacy reader key is ``consistent``. Both map
    to the same satisfiability semantics here. Returns ``True``/``False`` for a
    settled verdict, or ``None`` when unverified (the entry carries neither key
    or an explicit None) — never collapses None to False (#1019).
    """
    sat = result.get("satisfiable")
    if sat is None:
        sat = result.get("consistent")
    return sat if isinstance(sat, bool) else None


def _collect_formal_findings(state: Any) -> List[FormalFinding]:
    """Collect verified-in-state formal verdicts as weaving anchors (spec §1.2.3).

    The LLM is told to bind each cited verdict to the movement it speaks about.
    We surface PL/FOL consistency + Dung rejection counts — never fabricate a
    verdict that is not in the state (DoD (c): cited formal verdicts are real).
    """
    findings: List[FormalFinding] = []

    pl = getattr(state, "propositional_analysis_results", None)
    if isinstance(pl, list):
        # Finding C (#1151/#1153): the writer add_propositional_analysis_result
        # stores the verdict under ``satisfiable`` (shared_state.py:801), NOT
        # ``consistent``. Read the canonical PL key first, then the legacy
        # ``consistent`` key (some external/older writers use it). Preserve the
        # strict ``is True``/``is False`` check — NEVER ``bool(sat)``: that
        # would conflate the unverified sentinel (None) with ``inconsistent``
        # (False), an #1019 silent-degradation.
        consistent = sum(
            1 for r in pl if isinstance(r, dict) and _pl_verdict(r) is True
        )
        inconsistent = sum(
            1 for r in pl if isinstance(r, dict) and _pl_verdict(r) is False
        )
        if consistent or inconsistent:
            findings.append(
                FormalFinding(
                    kind="pl",
                    verdict=(
                        f"{inconsistent} inférence(s) PL inconsistantes sur "
                        f"{consistent + inconsistent} vérifiée(s)"
                        if inconsistent
                        else f"{consistent} inférence(s) PL consistantes"
                    ),
                    detail="solveur Tweety (logique propositionnelle)",
                )
            )

    fol = getattr(state, "fol_analysis_results", None)
    if isinstance(fol, list):
        consistent = sum(
            1 for r in fol if isinstance(r, dict) and r.get("consistent") is True
        )
        inconsistent = sum(
            1 for r in fol if isinstance(r, dict) and r.get("consistent") is False
        )
        if consistent or inconsistent:
            findings.append(
                FormalFinding(
                    kind="fol",
                    verdict=(
                        f"{inconsistent} théorie(s) FOL inconsistantes sur "
                        f"{consistent + inconsistent} vérifiée(s)"
                        if inconsistent
                        else f"{consistent} théorie(s) FOL consistantes"
                    ),
                    detail="solveur Tweety (logique du premier ordre)",
                )
            )
        else:
            # Track B #1278: no decided FOL verdict — surface the honest
            # unavailability instead of silence. An entry with consistent=None
            # and message "unavailable:<raison>" means the pipeline tried but
            # could not formalize the source (no translation / parse-fail).
            # The reader must see that the axis is honestly absent, never a
            # "trivially consistent sur vide" fabrication (#1019).
            unavailable = [
                r
                for r in fol
                if isinstance(r, dict)
                and r.get("consistent") is None
                and isinstance(r.get("message"), str)
                and str(r.get("message")).startswith("unavailable:")
            ]
            if unavailable:
                findings.append(
                    FormalFinding(
                        kind="fol",
                        verdict=(
                            "FOL indisponible : aucune théorie du premier ordre "
                            "n'a pu être formalisée puis validée sur ce corpus"
                        ),
                        detail=(
                            "logique du premier ordre — la traduction NL→FOL n'a "
                            "produit aucune formule analysable (belief set vide ou "
                            "non parsable) ; axe honnêtement absent, non « consistant "
                            "sur vide » (#1278/#1019)"
                        ),
                    )
                )

    modal = getattr(state, "modal_analysis_results", None)
    if isinstance(modal, list):
        # Track C #1279: surface the modal verdict when decided, OR the honest
        # unavailability (no-translation / no-solver OOM) instead of silence —
        # mirroring the FOL block (#1278). ``valid`` is tri-state: True/False =
        # SPASS/SimpleMlReasoner decided; None = degraded.
        decided = [
            r for r in modal if isinstance(r, dict) and r.get("valid") in (True, False)
        ]
        if decided:
            sat = sum(1 for r in decided if r.get("valid") is True)
            unsat = sum(1 for r in decided if r.get("valid") is False)
            findings.append(
                FormalFinding(
                    kind="modal",
                    verdict=(
                        f"{unsat} théorie(s) modales inconsistantes sur "
                        f"{len(decided)} vérifiée(s)"
                        if unsat
                        else f"{sat} théorie(s) modales consistantes"
                    ),
                    detail="solveur modal (SPASS/Tweety)",
                )
            )
        else:
            unavailable_modal = [
                r
                for r in modal
                if isinstance(r, dict)
                and r.get("valid") is None
                and isinstance(r.get("message"), str)
                and str(r.get("message")).startswith("unavailable:")
            ]
            if unavailable_modal:
                findings.append(
                    FormalFinding(
                        kind="modal",
                        verdict=(
                            "Modal indisponible : aucune théorie modale n'a pu "
                            "être formalisée puis validée sur ce corpus"
                        ),
                        detail=(
                            "logique modale — traduction NL→modal vide ou solveur "
                            "indisponible (OOM/absent) ; axe honnêtement absent, "
                            "non silencieusement dégradé (#1279/#1019)"
                        ),
                    )
                )

    dung_trace = _collect_dung_trace(state)
    if dung_trace.available and dung_trace.rejected_args:
        sems = sorted(set(dung_trace.rejected_args.values()))
        n_acc = len(dung_trace.accepted_members)
        n_rej = len(dung_trace.rejected_args)
        # Track D #1280 — frame Dung honestly: the attack graph is BUILT from the
        # extracted arguments (the pipeline's own attack relations), so Dung
        # reorganises upstream extraction rather than corroborating it from
        # outside. Surface the graph so the reader can see the computation, not
        # a black-box oracle. Cadrage « graphe construit à partir des arguments
        # extraits », pas « le cadre isole ».
        verdict = (
            f"graphe de Dung construit sur les {dung_trace.n_arguments} arguments "
            f"extraits ({dung_trace.n_attacks} relations d'attaque) — "
            f"extension {dung_trace.semantics_label} : {n_acc} retenu(s), "
            f"{n_rej} rejeté(s) (absents de l'extension acceptée)."
        )
        accepted_preview = ", ".join(sorted(dung_trace.accepted_members)[:6]) or "—"
        attacks_preview = "; ".join(f"{p[0]}→{p[1]}" for p in dung_trace.sample_attacks)
        detail = (
            f"cadre abstrait de Dung bâti à partir des arguments extraits "
            f"(PAS un oracle externe indépendant) — acceptés: [{accepted_preview}] ; "
            f"attaques échantillonnées: {attacks_preview or '—'} ; "
            f"sémantique(s): {', '.join(sems)}."
        )
        findings.append(FormalFinding(kind="dung", verdict=verdict, detail=detail))

    return findings


# --- the conducted prompt (spec §4 weaving rule, no template) ----------------

_OPAQUE_ID_DIRECTIVE = (
    "DISCIPLINE D'IDENTIFIANTS OPAQUES (FB-34) — OBLIGATOIRE :\n"
    "- Désigne chaque argument par son ID opaque (arg_1, arg_2…), JAMAIS par un\n"
    "  nom de source, d'auteur, de lieu ou de date.\n"
    "- Ne reproduis JAMAIS de passage verbatim du texte source : paraphrase le\n"
    "  MOUVEMENT argumentatif en une phrase qui dit quelque chose.\n"
    "- Les familles de sophismes (ad hominem, ad verecundiam…) sont des\n"
    "  constantes de taxonomie : tu peux les nommer comme ancrage."
)

_WEAVING_RULE = (
    "RÈGLE DE TISSAGE (spec §4) — le contrat anti-énumération :\n"
    "- CHAQUE citation d'un cadre (Tweety, Dung, taxonomie, vertus) DOIT être\n"
    "  ancrée narrativement : liée à (a) un mouvement textuel localisé ET (b) le\n"
    "  verdict concret que ce cadre a produit.\n"
    "- INTERDIT : une ligne « nom + score isolé », ex. « ad verecundiam (0.8) ».\n"
    "  Ne produis JAMAIS de score entre parenthèses isolé comme (0.8) ou\n"
    "  « score 0.8 ». Les vertus sont le CARACTÈRE de l'argument, pas un tableau\n"
    "  de scores.\n"
    "- INTERDIT : numéroter en « Sophisme 1: » / « Argument 2: ». Donne aux\n"
    "  mouvements des titres THÉMATIQUES (ex. « Le mouvement ad hominem »,\n"
    "  « Les soutiens qui tiennent »).\n"
    "- Le verdict formel appuie un battement narratif ; ce n'est jamais une\n"
    "  sous-section isolée."
)


def build_act2_prompt(evidence: Act2Evidence) -> str:
    """Build the §4-compliant LLM-conducted prompt for the Acte II narrative.

    The prompt varies with the evidence (hence with the corpus) — it is not a
    static template (#1108/#405). It instructs the LLM to weave each movement
    and to cite only the verified formal verdicts provided.
    """
    # --- Mode vertueux (spec §5) — le récit mène avec pourquoi ça tient ---
    vm = evidence.virtuous_mode
    is_virtuous = vm is not None and vm.is_virtuous
    if is_virtuous:
        virtuous_section = (
            "MODE VIRTUEUX (spec §5) — LE RÉCIT MÈNE AVEC POURQUOI ÇA TIENT :\n"
            "Ce texte est caractérisé comme vertueux (zéro sophisme localisé +\n"
            "vertus mesurées). Le mouvement des soutiens est le CENTRE du récit,\n"
            "pas un résidu. Tisse d'abord ce qui tient : le caractère (vertus),\n"
            "la cohérence, et — si le solveur a validé des inférences — la tenue\n"
            "formelle comme PREUVE que l'argumentation ne dérape pas. Peu (aucun)\n"
            "contre-argument ne mord : c'est le résultat honnête, ne le présente\n"
            "pas comme un manque. Ne fabrique JAMAIS de dérapage pour équilibrer.\n"
            f"Dérivation du flag : {vm.reasoning if vm is not None else ''}\n\n"
        )
    else:
        virtuous_section = ""

    # --- movement data blocks (truncated, opaque) ---
    blocks: List[str] = []
    for mvt in evidence.movements:
        is_soutiens = mvt.theme == _SOUTIENS_THEME
        header = f"MOUVEMENT « {mvt.theme} » — " + (
            "les soutiens qui tiennent (aucun sophisme localisé)"
            if is_soutiens
            else f"les arguments attaqués par la famille « {mvt.theme} »"
        )
        lines: List[str] = [header]
        for a in mvt.arguments:
            lines.append(f"  • {a.arg_id} : {a.description}")
            if a.quality_available:
                vchar = ", ".join(f"{k}" for k in sorted(a.virtues.keys())) or "—"
                lines.append(
                    f"      Profil de vertus (caractère) : {vchar}. "
                    f"Note globale : {a.quality_overall:.1f}/10."
                    if a.quality_overall is not None
                    else f"      Profil de vertus (caractère) : {vchar}."
                )
            else:
                lines.append(
                    "      Axe qualité : non concluable ici "
                    "(argument_quality_scores indisponible sur ce run)."
                )
            for fl in a.fallacies:
                path = f" [descente: {fl.taxonomy_path}]" if fl.taxonomy_path else ""
                lines.append(
                    f"      Dérapage : « {fl.type} » (famille {fl.family}){path}. "
                    f"Justification : {fl.justification}"
                )
            for ca in a.counter_args:
                lines.append(f"      Contre-argument ({ca.strategy}) : {ca.snippet}")
            if a.dung_rejected:
                # Track D #1280 — frame honestly: the Dung graph is built from
                # the extracted arguments, so the verdict is a reorganisation of
                # upstream extraction, not an external corroboration.
                lines.append(
                    f"      Tenue formelle : le graphe de Dung bâti sur les "
                    f"arguments extraits ne retient pas {a.arg_id} dans "
                    f"l'extension acceptée (sémantique {a.dung_rejected})."
                )
        blocks.append("\n".join(lines))

    # --- formal anchors (verified-in-state) ---
    formal_block = "AUCUN verdict formel vérifié dans le state."
    if evidence.formal_findings:
        formal_block = "\n".join(
            f"  - [{f.kind}] {f.verdict} — ancrage : {f.detail}"
            for f in evidence.formal_findings
        )

    # --- SV (#1182): délibération collective (governance + debate) ---
    # Both capabilities were completing in the 40 phases but invisible in the
    # report. We surface what exists — honestly sparse when the schemes-engine
    # gap (β G8) left debate thin. Each citation must bind to a narrative beat
    # (spec §4 anti-énumération); never a bare score/label line.
    # Track E #1281 — frame governance honestly. When extraction_method == "llm",
    # the verdict is a SINGLE-LLM assessment dressed as a voting layer (NOT a
    # genuine multi-agent deliberation); present it as a model-assessed ranking,
    # never as procedural legitimacy / an independent social-choice verdict.
    deliberation_lines: List[str] = []
    gv = evidence.governance_verdict
    if gv is not None:
        if gv.extraction_method == "llm":
            gov_origin = (
                "ATTENTION : ce verdict governance est une ÉVALUATION D'UN MODÈLE "
                "(issue d'un seul appel LLM, pas d'une délibération multi-agent "
                "réelle). Présente-le comme un classement évalué par le modèle, "
                "PAS comme une caution de légitimité procédurale indépendante."
            )
            gov_lead = (
                f"  - GOUVERNANCE (évaluation modèle) : l'analyste-LLM classe "
                f"{gv.winner} en tête sous la méthode « {gv.method} ». "
            )
        else:
            gov_origin = ""
            gov_lead = (
                f"  - GOUVERNANCE : sous la méthode « {gv.method} », l'option "
                f"{gv.winner} sort gagnante du vote social-choice. "
            )
        if gov_origin:
            deliberation_lines.append(gov_origin)
        deliberation_lines.append(
            gov_lead + "(noms d'options maintenus opaques — discipline FB-34.)"
        )
    if evidence.debate_exchanges:
        for i, ex in enumerate(evidence.debate_exchanges, start=1):
            scheme_anchor = ""
            if ex.scheme:
                scheme_anchor = f" [scheme : {ex.scheme}"
                if ex.critical_question:
                    scheme_anchor += f" — question critique : {ex.critical_question}"
                scheme_anchor += "]"
            deliberation_lines.append(
                f"  - DÉBAT (échange {i}) : position « {ex.point} » / "
                f"réplique « {ex.rebuttal} »{scheme_anchor}."
            )
    deliberation_block = (
        "\n".join(deliberation_lines)
        if deliberation_lines
        else "  (aucune délibération governance/débat non-triviale dans le state — "
        "ne la fabrique pas, note l'absence honnêtement si tu l'évoques)"
    )

    quality_note = (
        "L'axe qualité est disponible : tisse les vertus comme CARACTÈRE."
        if evidence.quality_axis_available
        else "L'axe qualité est INDISPONIBLE sur ce run : note-le honnêtement, "
        "ne fabrique jamais de profil de vertus."
    )

    opaque_block = f"{_OPAQUE_ID_DIRECTIVE}\n\n" if not evidence.deanonymized else ""

    return (
        "Tu es l'auteur de l'ACTE II d'un rapport de restitution argumentative.\n"
        "Le récit suit le FIL ARGUMENTATIF (thèse → soutiens → dérapages), découpé\n"
        "par MOUVEMENT argumentatif, PAS par dimension analytique.\n\n"
        f"{opaque_block}"
        f"{_WEAVING_RULE}\n\n"
        f"{virtuous_section}"
        "DONNÉES VERIFIÉES DANS LE STATE (ne citer que celles-ci) :\n\n"
        f"{chr(10).join(blocks)}\n\n"
        f"TENUE FORMELLE (ancres vérifiées, à tisser comme PREUVE d'un battement) :\n"
        f"{formal_block}\n\n"
        f"DÉLIBÉRATION COLLECTIVE (governance + débat, à tisser dans le récit — "
        f"le verdict de gouvernance ou un échange de débat peut appuyer un "
        f"battement, jamais une sous-section isolée) :\n"
        f"{deliberation_block}\n\n"
        f"{quality_note}\n\n"
        "CONSIGNE DE RÉDACTION :\n"
        "- Pour chaque mouvement, écris un paragraphe qui tisse en UN battement : "
        "l'argument, son caractère (vertus) si l'axe est disponible, ses dérapages "
        "(sophisme localisé + descente + contre-argument), et sa tenue formelle "
        "citée comme preuve.\n"
        "- Le verdict formel (Tweety/Dung) appuie le battement ; formule-le comme "
        "« le solveur Tweety confirme l'inconsistance de cette inférence » "
        "(théorie inconsistante), « le solveur Tweety confirme la cohérence de "
        "cette inférence » (théorie consistante — un résultat formel aussi) ou "
        "« le graphe de Dung bâti sur les arguments extraits ne retient pas cet "
        "argument dans l'extension acceptée » (Dung : le graphe d'attaques est "
        "construit à partir des arguments extraits, ce n'est PAS un oracle "
        "externe — cadre-le comme un reorganisation du matériau extrait).\n"
        "- Si un mouvement n'a ni sophisme ni verdict formel (les soutiens), "
        "dis ce qui le tient (le caractère, la cohérence).\n"
        "- Le récit doit VARIER selon le contenu réel ci-dessus : pas de prose\n"
        "  générique recyclable. Ce que tu écris découle des données.\n"
        "- Rédige en français, markdown léger (titres thématiques en ###). "
        "300-700 mots selon la richesse réelle.\n"
    )


# --- LLM-conducted weaving (fail-loud) ---------------------------------------


async def weave_act2_narrative(
    evidence: Act2Evidence, llm_callable: LlmCallable
) -> str:
    """Conduct the Acte II narrative via the LLM (fail-loud, #1108).

    Returns the LLM-produced markdown, or an empty string if the LLM produced
    nothing (the caller records the explicit ``unavailable`` status). No
    template fallback — anti-pendule #1019/#369.
    """
    prompt = build_act2_prompt(evidence)
    try:
        raw = await llm_callable(prompt)
    except Exception as exc:  # noqa: BLE001 — surface, don't fabricate
        logger.warning("Acte II LLM weaving failed (fail-loud): %s", exc)
        return ""
    if not raw:
        return ""
    return str(raw).strip()


# --- orchestrator ------------------------------------------------------------


async def build_act2_narrative(
    state: Any, llm_callable: Optional[LlmCallable] = None
) -> Act2Result:
    """Build the Acte II dialectical narrative for ``state``.

    Deterministic evidence is always built. The narrative is LLM-conducted only
    when ``llm_callable`` is provided; otherwise the result is fail-loud
    (``status="unavailable"``, empty narrative) — the renderer reports the gap
    honestly, never a template (#1108).

    A §4 self-check (``ReadabilityGate``) is attached to every woven result so
    the verdict is auditable; it never fabricates a pass.
    """
    evidence = build_act2_evidence(state)

    if evidence.args_total == 0:
        return Act2Result(
            narrative="",
            status="empty_state",
            degraded={
                "act2_narrative": (
                    "Aucun argument extrait — l'Acte II n'a pas de substrat "
                    "argumentatif à narrer (identified_arguments vide)."
                )
            },
        )

    if llm_callable is None:
        return Act2Result(
            narrative="",
            status="unavailable",
            degraded={
                "act2_narrative": (
                    "Récit dialectique non conduit — aucun LLM injecté pour "
                    "l'Acte II (fail-loud, #1108)."
                )
            },
        )

    narrative = await weave_act2_narrative(evidence, llm_callable)
    if not narrative:
        return Act2Result(
            narrative="",
            status="unavailable",
            degraded={
                "act2_narrative": (
                    "Récit dialectique indisponible — le LLM n'a rien produit "
                    "(fail-loud, #1108)."
                )
            },
        )

    # §4 self-check (honest, never grades on a curve).
    gate = ReadabilityGate()
    verdict = gate.check_body(narrative)
    degraded: Dict[str, str] = {}
    if verdict.band != "PASS":
        degraded["act2_narrative_gate"] = (
            f"Self-check §4 = {verdict.band}: " + "; ".join(verdict.reasons[:3])
        )
    if not evidence.quality_axis_available:
        degraded["act2_narrative"] = (
            "Axe qualité non concluable ici (argument_quality_scores "
            "indisponible) — vertus tues, fail-loud."
        )
    vm = evidence.virtuous_mode
    is_virtuous = vm is not None and vm.is_virtuous
    if vm is not None and vm.is_virtuous:
        degraded["act2_virtuous_mode"] = (
            "Mode vertueux (spec §5) — récit mené par pourquoi ça tient. "
            + vm.reasoning
        )

    return Act2Result(
        narrative=narrative,
        status="woven",
        gate_verdict=verdict,
        degraded=degraded,
        is_virtuous=is_virtuous,
    )
