"""Narrative Synthesis Plugin for Spectacular Analysis Pipeline (#351).

Produces 1-2 paragraphs of human-readable narrative weaving together
results from all analysis KBs (fallacies, JTMS, ATMS, Dung, quality,
counter-arguments). Reads from UnifiedAnalysisState and generates
prose without LLM calls — purely template-based for reliability.
Track CC (#636) adds an optional LLM prose layer over the convergent
synthesis skeleton produced by Track BB (#634).
"""

import logging
from typing import Any, Dict, List, Optional

try:
    from semantic_kernel.functions import kernel_function

    SK_AVAILABLE = True
except ImportError:

    def kernel_function(name=None, description=None):
        def decorator(func):
            func._sk_function_name = name or func.__name__
            func._sk_function_description = description or func.__doc__
            return func

        return decorator

    SK_AVAILABLE = False

logger = logging.getLogger(__name__)


def build_narrative(state: Any) -> str:
    """Build a narrative synthesis paragraph from UnifiedAnalysisState.

    Weaves together results from quality, fallacies, counter-arguments,
    JTMS beliefs, ATMS contexts, Dung extensions, and formal logic into
    1-2 readable paragraphs. Each referenced field is cited naturally.
    """
    parts: List[str] = []

    # ── Quality scores ─────────────────────────────────────────────
    quality = getattr(state, "argument_quality_scores", {})
    if quality:
        scores = [v.get("overall", 0) for v in quality.values() if isinstance(v, dict)]
        if scores:
            avg = sum(scores) / len(scores)
            quality_desc = (
                f"L'evaluation de la qualite argumentative couvre "
                f"{len(quality)} argument(s), avec une note moyenne de "
                f"{avg:.1f}/5."
            )
            weak = [
                k
                for k, v in quality.items()
                if isinstance(v, dict) and v.get("overall", 0) < 3
            ]
            if weak:
                quality_desc += f" {len(weak)} argument(s) presentent des faiblesses significatives."
            parts.append(quality_desc)

    # ── Fallacies ──────────────────────────────────────────────────
    fallacies = getattr(state, "identified_fallacies", {})
    neural_fallacies = getattr(state, "neural_fallacy_scores", [])
    total_fallacies = len(fallacies) + len(neural_fallacies)
    if total_fallacies:
        types = [
            v.get("type", "inconnu") for v in fallacies.values() if isinstance(v, dict)
        ]
        types_str = ", ".join(set(types)) if types else f"{total_fallacies} sophisme(s)"
        fallacy_text = (
            f"L'analyse a detecte {total_fallacies} sophisme(s) "
            f"({types_str}), ce qui fragilise la structure argumentative."
        )
        parts.append(fallacy_text)

    # ── Counter-arguments ──────────────────────────────────────────
    counters = getattr(state, "counter_arguments", [])
    if counters:
        strategies = set()
        for ca in counters:
            if isinstance(ca, dict):
                strategies.add(ca.get("strategy", "general"))
        strat_text = ", ".join(strategies) if strategies else "plusieurs approches"
        parts.append(
            f"Des contre-arguments ont ete generes via {strat_text}, "
            f"identifiant {len(counters)} point(s) de contestation."
        )

    # ── JTMS beliefs ───────────────────────────────────────────────
    jtms_beliefs = getattr(state, "jtms_beliefs", {})
    if jtms_beliefs:
        valid_count = sum(
            1
            for v in jtms_beliefs.values()
            if isinstance(v, dict) and v.get("valid") is True
        )
        invalid_count = sum(
            1
            for v in jtms_beliefs.values()
            if isinstance(v, dict) and v.get("valid") is False
        )
        jtms_text = (
            f"Le systeme JTMS maintient {len(jtms_beliefs)} croyance(s): "
            f"{valid_count} valide(s), {invalid_count} rejetee(s)."
        )
        retraction_chain = getattr(state, "jtms_retraction_chain", [])
        if retraction_chain:
            cascade_count = sum(len(r.get("cascaded", [])) for r in retraction_chain)
            jtms_text += (
                f" {len(retraction_chain)} retraction(s) en cascade ont ete observee(s), "
                f"affectant {cascade_count} croyance(s) dependante(s)."
            )
        parts.append(jtms_text)

    # ── ATMS multi-context ─────────────────────────────────────────
    atms_contexts = getattr(state, "atms_contexts", [])
    if atms_contexts:
        coherent = sum(
            1 for c in atms_contexts if isinstance(c, dict) and c.get("coherent")
        )
        incoherent = len(atms_contexts) - coherent
        parts.append(
            f"L'analyse ATMS multi-contextes a teste {len(atms_contexts)} hypothese(s): "
            f"{coherent} coherente(s), {incoherent} incoherente(s), "
            f"illustrant la sensibilite des conclusions aux hypotheses retenues."
        )

    # ── Dung frameworks ────────────────────────────────────────────
    dung = getattr(state, "dung_frameworks", {})
    if dung:
        ext_count = sum(
            len(v.get("extensions", [])) for v in dung.values() if isinstance(v, dict)
        )
        if ext_count:
            parts.append(
                f"L'argumentation abstraite (semantiques de Dung) a identifie "
                f"{ext_count} extension(s) parmi {len(dung)} cadre(s) d'attaque."
            )

    # ── Formal logic ───────────────────────────────────────────────
    fol = getattr(state, "fol_analysis_results", [])
    pl = getattr(state, "propositional_analysis_results", [])
    modal = getattr(state, "modal_analysis_results", [])
    formal_count = len(fol) + len(pl) + len(modal)
    if formal_count:
        formal_parts = []
        if fol:
            formal_parts.append(f"{len(fol)} en logique du premier ordre")
        if pl:
            formal_parts.append(f"{len(pl)} en logique propositionnelle")
        if modal:
            formal_parts.append(f"{len(modal)} en logique modale")
        formal_str = ", ".join(formal_parts)
        parts.append(
            f"L'analyse formelle a produit {formal_count} resultat(s) ({formal_str})."
        )

    if not parts:
        return (
            "L'analyse n'a pas produit suffisamment de donnees pour generer "
            "une synthese narrative. Seules des donnees partielles sont disponibles."
        )

    # ── Assemble into 1-2 paragraphs (ceil-split, never drops content) ──
    half = (len(parts) + 1) // 2
    paragraph_1 = " ".join(parts[:half])
    paragraph_2 = " ".join(parts[half:])

    if paragraph_2:
        return f"{paragraph_1}\n\n{paragraph_2}"
    return paragraph_1


# ════════════════════════════════════════════════════════════════════
# Convergent multidimensional synthesis (#634)
#
# The template synthesis above describes each KB in isolation. The real
# spectacular insight is *convergence*: when several independent methods
# (rhetorical fallacy detection, abstract argumentation, truth maintenance,
# quality scoring, counter-argumentation) flag the SAME argument as weak,
# that agreement is itself the finding — a verdict no single LLM pass
# produces. The functions below compute per-argument convergence and weave
# the convergent verdicts into the narrative.
# ════════════════════════════════════════════════════════════════════

QUALITY_WEAK_THRESHOLD = 5.0


def _dung_rejected_args(state: Any) -> Dict[str, str]:
    """Return {arg_id: semantics} for arguments present in a Dung framework
    but absent from its accepted extension (i.e. rejected by that semantics)."""
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
        semantics = fw.get("semantics", "grounded")
        # Accepted members: prefer enriched dict (all_members), fall back to
        # flat list-of-lists, then to a bare list.
        ext = fw.get("extensions", [])
        accepted: set = set()
        if isinstance(ext, dict):
            # Enriched form: {"all_members": [...]}; else semantics->list form:
            # {"grounded": ["arg_1", ...], "preferred": [...]}
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
                    elif isinstance(val, dict):
                        accepted.update(val.get("all_members", []) or [])
        elif isinstance(ext, list):
            for item in ext:
                if isinstance(item, list):
                    accepted.update(item)
                elif isinstance(item, str):
                    accepted.add(item)
        for arg in fw_args:
            if isinstance(arg, str) and arg not in accepted:
                # Don't overwrite a prior rejection from another framework
                rejected.setdefault(arg, semantics)
    return rejected


def compute_argument_convergence(state: Any) -> Dict[str, Dict[str, Any]]:
    """For each identified argument, count independent methods flagging it weak.

    Reads raw state fields (works on both UnifiedAnalysisState and a namespace
    built from a state dict). Returns a mapping
    ``{arg_id: {"score": int, "signals": [(method, detail), ...]}}``.
    """
    args = getattr(state, "identified_arguments", {}) or {}
    if not isinstance(args, dict):
        return {}

    fallacies = getattr(state, "identified_fallacies", {}) or {}
    quality = getattr(state, "argument_quality_scores", {}) or {}
    counters = getattr(state, "counter_arguments", []) or []
    jtms = getattr(state, "jtms_beliefs", {}) or {}
    rejected_by_dung = _dung_rejected_args(state)

    # Pre-index fallacies by target argument
    fallacy_by_arg: Dict[str, List[str]] = {}
    if isinstance(fallacies, dict):
        for _fid, fdata in fallacies.items():
            if not isinstance(fdata, dict):
                continue
            tid = fdata.get("target_argument_id")
            if tid:
                fallacy_by_arg.setdefault(tid, []).append(fdata.get("type", "inconnu"))

    # Pre-index counter-arguments by target (ID-based only — text matching is
    # handled by get_argument_profile elsewhere; here we stay strict/cheap)
    counter_by_arg: Dict[str, int] = {}
    if isinstance(counters, list):
        for ca in counters:
            if isinstance(ca, dict):
                tid = ca.get("target_arg_id")
                if tid:
                    counter_by_arg[tid] = counter_by_arg.get(tid, 0) + 1

    result: Dict[str, Dict[str, Any]] = {}
    for arg_id in args:
        signals: List[tuple] = []

        # 1. Rhetorical fallacy targeting this argument
        if arg_id in fallacy_by_arg:
            ftypes = sorted(set(fallacy_by_arg[arg_id]))
            signals.append(("sophisme", ", ".join(ftypes)))

        # 2. Low quality score
        qs = quality.get(arg_id) if isinstance(quality, dict) else None
        if isinstance(qs, dict):
            overall = qs.get("overall")
            if isinstance(overall, (int, float)) and overall < QUALITY_WEAK_THRESHOLD:
                signals.append(("qualite faible", f"{overall:.1f}/10"))

        # 3. Counter-argument generated against it
        if arg_id in counter_by_arg:
            signals.append(("contre-argument", str(counter_by_arg[arg_id])))

        # 4. JTMS belief retracted / invalid
        # Beliefs are named "arg_N:<text_excerpt>" (see _invoke_jtms).  Use
        # startswith for a precise match — substring check would false-positive
        # on defeat beliefs and other arg_id occurrences in text.
        jtms_prefix = f"{arg_id}:"
        if isinstance(jtms, dict):
            invalid = 0
            for _bid, bdata in jtms.items():
                if not isinstance(bdata, dict):
                    continue
                name = bdata.get("name", "")
                if name.startswith(jtms_prefix) and bdata.get("valid") is False:
                    invalid += 1
            if invalid:
                signals.append(("JTMS retracte", str(invalid)))

        # 5. Rejected by Dung abstract argumentation
        if arg_id in rejected_by_dung:
            signals.append(("rejet Dung", rejected_by_dung[arg_id]))

        if signals:
            result[arg_id] = {"score": len(signals), "signals": signals}

    return result


def _build_substantive_insight(
    arg_id: str,
    score: int,
    method_phrases: List[str],
    data: Dict[str, Any],
) -> str:
    """Build a substantive insight paragraph for high-convergence verdicts (>=3 methods).

    Produces a conclusion anchored in the actual signals: names the argument,
    lists the converging methods, and states WHY the cross-method agreement
    makes the argument's weakness over-determined rather than a single-method
    opinion.
    """
    joined = ", ".join(method_phrases)

    signal_reasons = []
    for method, detail in data["signals"]:
        if method == "sophisme":
            signal_reasons.append(
                f"la detection rhetorique a identifie un probleme ({detail})"
            )
        elif method == "qualite faible":
            signal_reasons.append(
                f"le scoring de qualite signale une faiblesse ({detail})"
            )
        elif method == "contre-argument":
            signal_reasons.append("un contre-argument solide a ete oppose")
        elif method == "JTMS retracte":
            signal_reasons.append(
                "le systeme de maintenance de verite (JTMS) a retracte "
                "la croyance associee"
            )
        elif method == "rejet Dung":
            signal_reasons.append(
                f"l'analyse argumentative abstraite (Dung) rejette l'argument "
                f"({detail})"
            )

    reasons_text = " ; en outre, ".join(signal_reasons)

    return (
        f"**Insight convergent sur {arg_id}** : {score} methodes independantes "
        f"concourent a signaler cet argument comme faible ({joined}). "
        f"Cette faiblesse est sur-determinee, et non le produit d'une seule "
        f"perspective : {reasons_text}. "
        f"Un tel accord inter-methodes est inaccessible a une analyse "
        f"LLM monotone et constitue un insight emergent propre au systeme "
        f"multi-agents."
    )


def build_convergent_synthesis(state: Any) -> Dict[str, Any]:
    """Build a spectacular synthesis surfacing cross-dimensional convergence.

    Returns a dict with:
      - ``narrative``: the base template narrative (backward-compatible)
      - ``convergent_verdicts``: per-argument list flagged by >=2 methods
      - ``emergent_insights``: human-readable convergence statements
      - ``conclusion``: a one-line verdict suitable for ``final_conclusion``
    """
    base_narrative = build_narrative(state)
    convergence = compute_argument_convergence(state)

    # Convergent verdicts = arguments flagged by >=2 independent methods
    verdicts = {aid: data for aid, data in convergence.items() if data["score"] >= 2}
    # Sort by descending convergence score (strongest agreement first)
    ordered = sorted(verdicts.items(), key=lambda kv: kv[1]["score"], reverse=True)

    insights: List[str] = []
    for arg_id, data in ordered:
        method_phrases = []
        for method, detail in data["signals"]:
            if method == "sophisme":
                method_phrases.append(f"detection rhetorique ({detail})")
            elif method == "qualite faible":
                method_phrases.append(f"score de qualite ({detail})")
            elif method == "contre-argument":
                method_phrases.append("contre-argumentation")
            elif method == "JTMS retracte":
                method_phrases.append("maintenance de verite (JTMS)")
            elif method == "rejet Dung":
                method_phrases.append(f"argumentation abstraite (Dung/{detail})")
            else:
                method_phrases.append(method)
        joined = ", ".join(method_phrases)
        score = data["score"]
        if score >= 3:
            insight = _build_substantive_insight(arg_id, score, method_phrases, data)
            insights.append(insight)
        else:
            insights.append(
                f"**Verdict convergent sur {arg_id}** : {score} methodes "
                f"independantes concourent a le signaler ({joined}). "
                f"Cette convergence inter-perspectives est inaccessible a une passe "
                f"LLM unique."
            )

    # Build the conclusion line
    if ordered:
        strongest_id, strongest = ordered[0]
        conclusion = (
            f"Synthese convergente : {len(ordered)} argument(s) signale(s) par "
            f"au moins deux methodes formelles independantes. "
            f"Convergence maximale sur {strongest_id} "
            f"({strongest['score']} methodes)."
        )
    elif convergence:
        single = len(convergence)
        conclusion = (
            f"Aucune convergence multi-methodes : {single} argument(s) signale(s) "
            f"par une seule methode. La structure argumentative resiste a "
            f"l'examen croise."
        )
    else:
        conclusion = (
            "Aucun argument signale comme faible par les methodes d'analyse. "
            "Structure argumentative robuste sur toutes les dimensions testees."
        )

    # Assemble the full narrative
    full_parts = [base_narrative]
    if insights:
        full_parts.append("## Insights emergents (convergence inter-methodes)\n")
        full_parts.append("\n\n".join(insights))
    full_parts.append(f"\n**Conclusion** : {conclusion}")
    full_narrative = "\n\n".join(full_parts)

    return {
        "narrative": full_narrative,
        "base_narrative": base_narrative,
        "convergent_verdicts": verdicts,
        "emergent_insights": insights,
        "conclusion": conclusion,
    }


_PROSE_INSTRUCTIONS = (
    "You are an expert argumentation analyst. Transform the structured convergence "
    "evidence below into polished analytical prose in French. "
    "Rules: (1) Only reference arguments, fallacies, and methods listed in the evidence. "
    "(2) Name every concordant method explicitly (e.g. 'detection rhetorique', "
    "'argumentation abstraite', 'maintenance de verite', 'scoring de qualite'). "
    "(3) Do not invent claims or details absent from the evidence. "
    "(4) Each paragraph covers one argument; cite at least two methods by name. "
    "(5) For arguments flagged by 3+ methods, produce a SUBSTANTIVE CONCLUSION: "
    "state WHY the cross-method agreement makes the weakness over-determined — "
    "not just list methods, but articulate the insight that emerges from their "
    "concordance (e.g. 'the argument combines X AND Y AND Z, making its weakness "
    "structural rather than circumstantial'). "
    "(6) Maximum 400 words."
)


def _build_prose_prompt(synthesis_result: Dict[str, Any]) -> str:
    """Build a strictly-grounded LLM prompt from convergent synthesis evidence."""
    verdicts = synthesis_result.get("convergent_verdicts", {})
    conclusion = synthesis_result.get("conclusion", "")

    if verdicts:
        evidence_lines = []
        for arg_id, data in sorted(verdicts.items(), key=lambda kv: -kv[1]["score"]):
            sig_parts = [f"{m}: {d}" for m, d in data["signals"]]
            evidence_lines.append(
                f"- {arg_id} ({data['score']} methods): {'; '.join(sig_parts)}"
            )
        evidence_block = "\n".join(evidence_lines)
    else:
        evidence_block = "(no convergent arguments detected)"

    return (
        f"{_PROSE_INSTRUCTIONS}\n\n"
        f"## Convergence Evidence\n{evidence_block}\n\n"
        f"## Structural Conclusion\n{conclusion}\n\n"
        f"Write the analytical prose report:"
    )


class NarrativeSynthesisPlugin:
    """Semantic Kernel plugin for narrative synthesis (#351).

    Produces human-readable analysis summaries by weaving together
    outputs from all pipeline phases. Pass an SK Kernel instance to
    enable the LLM prose layer (Track CC #636); without it the plugin
    falls back to template-based output.
    """

    def __init__(self, kernel: Optional[Any] = None) -> None:
        self._kernel = kernel

    @kernel_function(
        name="narrative_synthesis",
        description="Generate a narrative synthesis paragraph from all "
        "analysis results. Weaves quality scores, fallacy detection, "
        "counter-arguments, JTMS beliefs, ATMS contexts, and formal "
        "logic into readable prose.",
    )
    def synthesize(self, state_json: str = "{}") -> str:
        """Generate narrative synthesis from state JSON."""
        import json

        try:
            state_data = json.loads(state_json)
        except (json.JSONDecodeError, TypeError):
            state_data = {}

        # Build a simple namespace object from dict for build_narrative
        ns = type("State", (), state_data)()
        return build_narrative(ns)

    @kernel_function(
        name="convergent_synthesis",
        description="Generate a spectacular synthesis that surfaces "
        "cross-dimensional convergence: arguments flagged weak by several "
        "independent methods (fallacy detection, abstract argumentation, "
        "truth maintenance, quality scoring, counter-argumentation). "
        "Returns the full narrative plus convergent verdicts as JSON.",
    )
    def convergent_synthesize(self, state_json: str = "{}") -> str:
        """Generate convergent synthesis from state JSON, returned as JSON."""
        import json

        try:
            state_data = json.loads(state_json)
        except (json.JSONDecodeError, TypeError):
            state_data = {}

        ns = type("State", (), state_data)()
        result = build_convergent_synthesis(ns)
        return json.dumps(result, ensure_ascii=False)

    @kernel_function(
        name="narrate_convergence",
        description="Generate LLM-grounded analytical prose over convergent "
        "synthesis results. Each verdict paragraph cites the concordant methods "
        "by name with specific evidence (fallacy type, quality score, Dung "
        "semantics, JTMS retraction). Strictly grounded — no hallucinated claims. "
        "Falls back to template narrative when no LLM kernel is configured or "
        "when the LLM call fails.",
    )
    async def narrate_convergence(self, state_json: str = "{}") -> str:
        """Generate LLM-polished prose from convergent synthesis evidence.

        Calls build_convergent_synthesis internally, then invokes the kernel's
        LLM with a strictly grounded prompt. Falls back to the template narrative
        when no kernel is configured, no convergent verdicts exist, or the LLM
        call raises an exception.
        """
        import json

        try:
            state_data = json.loads(state_json)
        except (json.JSONDecodeError, TypeError):
            state_data = {}

        ns = type("State", (), state_data)()
        synthesis = build_convergent_synthesis(ns)

        if not synthesis.get("convergent_verdicts") or self._kernel is None:
            return synthesis["narrative"]

        prompt = _build_prose_prompt(synthesis)
        try:
            result = await self._kernel.invoke_prompt(prompt)
            prose = str(result).strip()
            if prose:
                return prose
            return synthesis["narrative"]
        except Exception:
            logger.warning(
                "narrate_convergence: LLM call failed, falling back to template"
            )
            return synthesis["narrative"]
