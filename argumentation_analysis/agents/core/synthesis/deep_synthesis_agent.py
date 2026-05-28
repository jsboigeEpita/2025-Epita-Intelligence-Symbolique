"""DeepSynthesisAgent — multi-page grounded analysis aggregator.

Consumes a ``UnifiedAnalysisState`` snapshot (and optional conversation
transcript) produced by a spectacular conversational run, and emits a
structured markdown report covering 9 analytical dimensions.  Each claim
in the report is grounded by a textual citation, a formal artefact, or a
scored counter-argument.

The section structure is template-driven (deterministic formatting of
state data).  An optional LLM call via SK kernel is used *only* for
section 9 (final synthesis thesis).
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional

from semantic_kernel import Kernel
from pydantic import PrivateAttr

from ..abc.agent_bases import BaseAgent
from .deep_synthesis_models import (
    ArgumentMapEntry,
    BeliefRetraction,
    ConvergentVerdict,
    CounterArgumentEntry,
    CrossTextParallel,
    DeepSynthesisReport,
    DungStructure,
    FallacyDiagnosis,
    FormalFinding,
    SourceOverview,
)

logger = logging.getLogger("DeepSynthesisAgent")


class DeepSynthesisAgent(BaseAgent):
    """Aggregates spectacular-run state into a multi-page grounded markdown report."""

    SYSTEM_PROMPT: ClassVar[str] = (
        "You are an intelligence analyst producing a political-rhetorical "
        "briefing on a discourse. Your output is structured into exactly 6 "
        "numbered sections (8-12 paragraphs total). Each section heading must "
        "be on its own line, formatted as '## N. Title' (N = 1-6).\n"
        "\n"
        "## 1. Contexte & énonciation (1-2 paragraphs)\n"
        "Identify who is speaking (pseudonymised ID), to whom, in what venue "
        "and era, on what topic. State the rhetorical register and discursive "
        "arena. Articulate the central thesis of the discourse in one sentence. "
        "If metadata is missing, infer from the text but mark as [inferred].\n"
        "\n"
        "## 2. Enjeux soulevés (1-2 paragraphs)\n"
        "List and explain the stakes at play — what is genuinely at issue "
        "beneath the surface argument. Use the typed stakes data (economic, "
        "political, ideological, security, identity…) and connect each to "
        "specific argument passages. Do NOT paraphrase the discourse; explain "
        "what the discourse reveals about underlying tensions.\n"
        "\n"
        "## 3. Parties engagées & positionnement (1 paragraph)\n"
        "Map the stakeholders: who is positioned where, with what stance (for, "
        "against, ambivalent). Explain the power dynamics and alliances. "
        "Reference at least one stakeholder by pseudonymised ID and their "
        "relationship to the stakes identified in section 2.\n"
        "\n"
        "## 4. Ressorts rhétoriques (2-3 paragraphs)\n"
        "Analyse the rhetorical devices employed: name specific fallacies (with "
        "family), cite at least one scored counter-argument, and reference "
        "formal-method results (PL entailments, Dung grounded extension). "
        "Explain WHY these devices matter in context — what they achieve for "
        "the speaker's strategy. Do NOT list counts; name findings and their "
        "significance.\n"
        "\n"
        "## 5. Voix des spécialistes (1 paragraph)\n"
        "If specialist commentaries are provided, synthesise them into a "
        "narrative: which analysts flagged what, and where they agree or "
        "diverge. If no commentaries are available, write: 'No specialist "
        "commentaries were deposited during this analysis run.' and instead "
        "highlight the convergent verdicts — arguments independently flagged "
        "by multiple methods.\n"
        "\n"
        "## 6. Lecture politique (2-3 paragraphs)\n"
        "Deliver the political reading: what does this discourse reveal about "
        "the speaker's strategy, the power dynamics at play, and the broader "
        "political stakes? Identify the dominant rhetorical strategy and "
        "evaluate overall argument quality. Take a position grounded in the "
        "evidence cited above. This is the closing thesis — it must not "
        "paraphrase the discourse but interpret what it means politically.\n"
        "\n"
        "Register: intelligence briefing — concise, factual, specific "
        "citations, no academic hedging. Journalistic-analytical tone. "
        "Do NOT summarize the analysis pipeline. Use opaque IDs only "
        "(Speaker_A, Authority_X, era_A) — never real names."
    )

    _llm_service_id: Optional[str] = PrivateAttr(default=None)

    def __init__(
        self,
        kernel: Kernel,
        agent_name: str = "DeepSynthesisAgent",
        service_id: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(kernel, agent_name, self.SYSTEM_PROMPT, **kwargs)
        self._llm_service_id = service_id

    # ------------------------------------------------------------------
    # BaseAgent abstract implementations
    # ------------------------------------------------------------------

    def get_agent_capabilities(self) -> Dict[str, Any]:
        return {
            "deep_synthesis": True,
            "multi_page_report": True,
            "grounded_analysis": True,
            "sections": 9,
            "report_version": "1.0.0",
        }

    async def invoke_single(self, text: str, **kwargs) -> DeepSynthesisReport:
        state = kwargs.get("state") or kwargs.get("shared_state")
        transcript = kwargs.get("transcript", [])
        source_meta = kwargs.get("source_metadata", {})
        if state is None:
            raise ValueError(
                "DeepSynthesisAgent requires a 'state' kwarg (UnifiedAnalysisState)"
            )
        return await self.synthesize(state, transcript, source_meta)

    async def get_response(self, *args, **kwargs):
        report = await self.invoke_single("", **kwargs)
        return self.render_markdown(report)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def synthesize(
        self,
        state: Any,
        transcript: Optional[List[Dict[str, Any]]] = None,
        source_metadata: Optional[Dict[str, str]] = None,
    ) -> DeepSynthesisReport:
        """Build the full 9-section report from state."""
        report = DeepSynthesisReport()

        # Section 1 — source overview
        report.source_overview = self._build_source_overview(state, source_metadata)

        # Section 2 — argument map
        report.argument_map = self._build_argument_map(state)

        # Section 3 — fallacy diagnosis
        report.fallacy_diagnoses = self._build_fallacy_diagnoses(state)

        # Section 4 — formal method findings
        report.formal_findings = self._build_formal_findings(state)

        # Section 5 — Dung dialectical structure
        report.dung_structure = self._build_dung_structure(state)

        # Section 6 — belief revision trace
        report.belief_retractions = self._build_belief_retractions(state)

        # Section 7 — counter-arguments
        report.counter_arguments = self._build_counter_arguments(state)

        # Section 8 — cross-text parallels (if available)
        report.cross_text_parallels = self._build_cross_text_parallels(state)

        # Convergence layer (Track DD #637) — cross-method agreement, computed
        # before section 9 so both the LLM and template thesis can ground in it.
        (
            report.convergent_verdicts,
            report.convergence_conclusion,
        ) = self._build_convergent_verdicts(state)

        # Convergence prose (Track GG #644) — citation-rich LLM narration of the
        # convergence evidence, grounded strictly in the structured verdicts.
        # Empty when no kernel/verdicts; renderer falls back to template statements.
        report.convergence_prose = await self._llm_convergence_prose(state)

        # Adjudication table (Track NN #659) — grounded vs claimed families.
        report.adjudication_table = self._build_adjudication_table(
            report.fallacy_diagnoses, report.convergent_verdicts
        )

        # TT #723: attach stakes data for use in LLM synthesis
        stakes_data = getattr(state, "stakes_and_stakeholders", {})
        if stakes_data and any(
            stakes_data.get(k)
            for k in ("stakes", "stakeholders", "rhetorical_register")
        ):
            report._raw_stakes = stakes_data
        else:
            report._raw_stakes = {}

        # UU #724: attach analysis trace for specialist commentary
        analysis_trace = getattr(state, "analysis_trace", [])
        report._raw_analysis_trace = analysis_trace if analysis_trace else []

        # Section 9 — final synthesis (tries LLM, falls back to template)
        try:
            thesis = await self._llm_synthesis(report)
            if thesis:
                report.final_synthesis = thesis
            else:
                report.final_synthesis = (
                    await DeepSynthesisAgent._build_final_synthesis(
                        state, report, transcript
                    )
                )
        except Exception as e:
            logger.warning(f"LLM synthesis failed, using template: {e}")
            report.final_synthesis = await DeepSynthesisAgent._build_final_synthesis(
                state, report, transcript
            )

        # Metadata
        report.total_state_fields = self._count_state_fields(state)
        report.sections_populated = self._count_populated_sections(report)
        report.report_timestamp = datetime.now().isoformat()

        logger.info(
            f"DeepSynthesis report generated: {report.sections_populated}/9 sections, "
            f"{report.total_state_fields} state fields consumed"
        )
        return report

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------

    @staticmethod
    def _build_source_overview(
        state: Any, meta: Optional[Dict[str, str]]
    ) -> SourceOverview:
        text = getattr(state, "raw_text", "")
        meta = meta or {}
        speaker = meta.get("speaker", "")
        date_or_year = meta.get("date_or_year", "")
        venue = meta.get("venue", "")
        topic = meta.get("topic", "")
        register = meta.get("register", "")
        synopsis = meta.get("synopsis", "")
        # PP #715: build rich contextual frame when context is available
        parts = [f"Source '{meta.get('opaque_id', '?')}'"]
        if speaker:
            parts.append(f"by {speaker}")
        if date_or_year:
            parts.append(f"({date_or_year})")
        if venue:
            parts.append(f"at {venue}")
        if topic:
            parts.append(f"— Topic: {topic}")
        parts.append(
            f"— {meta.get('discourse_type', '?')} discourse "
            f"in {meta.get('language', '?')}, {meta.get('era', '?')} era, "
            f"{len(text)} characters."
        )
        return SourceOverview(
            opaque_id=meta.get("opaque_id", "unknown"),
            era=meta.get("era", ""),
            language=meta.get("language", ""),
            discourse_type=meta.get("discourse_type", ""),
            length_chars=len(text),
            length_words=len(text.split()) if text else 0,
            contextual_frame=" ".join(parts),
            speaker=speaker,
            date_or_year=date_or_year,
            venue=venue,
            topic=topic,
            register=register,
            synopsis=synopsis,
        )

    @staticmethod
    def _build_argument_map(state: Any) -> List[ArgumentMapEntry]:
        args = getattr(state, "identified_arguments", {})
        if not args:
            return []
        # Build attack relations from fallacies and counter-arguments
        fallacies = getattr(state, "identified_fallacies", {})
        attack_map: Dict[str, List[str]] = {}
        for fid, fdata in fallacies.items():
            target = fdata.get("target_argument_id")
            if target and target in args:
                attack_map.setdefault(f"fallacy_{fid}", []).append(target)

        counter_args = getattr(state, "counter_arguments", [])
        for ca in counter_args:
            orig = ca.get("original_argument", "")
            ca_id = ca.get("id", "ca")
            # Match counter to argument by partial text match
            for arg_id, desc in args.items():
                if orig and (orig[:60] in desc or desc[:60] in orig):
                    attack_map.setdefault(f"counter_{ca_id}", []).append(arg_id)

        entries = []
        for arg_id, desc in args.items():
            attacked_by = [
                src for src, targets in attack_map.items() if arg_id in targets
            ]
            entries.append(
                ArgumentMapEntry(
                    arg_id=arg_id,
                    stance=DeepSynthesisAgent._infer_stance(desc),
                    description=desc,
                    attacks=[],
                    attacked_by=attacked_by,
                )
            )
        return entries

    @staticmethod
    def _build_fallacy_diagnoses(state: Any) -> List[FallacyDiagnosis]:
        fallacies = getattr(state, "identified_fallacies", {})
        if not fallacies:
            return []
        entries = []
        for fid, fdata in fallacies.items():
            ftype = fdata.get("type", "unknown")
            family = fdata.get("family", "")
            if not family:
                family = DeepSynthesisAgent._fallacy_family(ftype)
            taxonomy_path = fdata.get("taxonomy_path", "")
            if not taxonomy_path:
                taxonomy_path = f"fallacy/{family}/{ftype}"
            entries.append(
                FallacyDiagnosis(
                    fallacy_id=fid,
                    family=family,
                    taxonomy_path=taxonomy_path,
                    textual_span=fdata.get("justification", "")[:200],
                    commentary=fdata.get("justification", ""),
                    impacted_args=(
                        [fdata["target_argument_id"]]
                        if fdata.get("target_argument_id")
                        else []
                    ),
                )
            )
        return entries

    @staticmethod
    def _build_formal_findings(state: Any) -> List[FormalFinding]:
        findings = []
        # PL results
        for r in getattr(state, "propositional_analysis_results", []):
            findings.append(
                FormalFinding(
                    logic_type="PL",
                    axioms=r.get("axioms", []),
                    queries=r.get("queries", []),
                    results=r.get("results", []),
                    inconsistency_measures=r.get("inconsistency_measures", {}),
                    linked_args=r.get("linked_args", []),
                )
            )
        # FOL results
        for r in getattr(state, "fol_analysis_results", []):
            findings.append(
                FormalFinding(
                    logic_type="FOL",
                    axioms=r.get("axioms", []),
                    queries=r.get("queries", []),
                    results=r.get("results", []),
                    inconsistency_measures=r.get("inconsistency_measures", {}),
                    linked_args=r.get("linked_args", []),
                )
            )
        # Modal results
        for r in getattr(state, "modal_analysis_results", []):
            findings.append(
                FormalFinding(
                    logic_type="Modal",
                    axioms=r.get("axioms", []),
                    queries=r.get("queries", []),
                    results=r.get("results", []),
                    inconsistency_measures=r.get("inconsistency_measures", {}),
                    linked_args=r.get("linked_args", []),
                )
            )
        # Belief sets + query log
        belief_sets = getattr(state, "belief_sets", {})
        query_log = getattr(state, "query_log", [])
        if belief_sets:
            for bs_id, bs_data in belief_sets.items():
                related_queries = [
                    q for q in query_log if q.get("belief_set_id") == bs_id
                ]
                findings.append(
                    FormalFinding(
                        logic_type=bs_data.get("logic_type", "unknown"),
                        axioms=[bs_data.get("content", "")],
                        queries=[q.get("query", "") for q in related_queries],
                        results=[q.get("raw_result", "") for q in related_queries],
                        linked_args=[],
                    )
                )
        return findings

    @staticmethod
    def _build_dung_structure(state: Any) -> DungStructure:
        dung = getattr(state, "dung_frameworks", {})
        if not dung:
            return DungStructure()
        # Use the first framework (most runs have one)
        first_id = next(iter(dung))
        df = dung[first_id]
        return DungStructure(
            framework_name=df.get("name", first_id),
            arguments=df.get("arguments", []),
            attacks=df.get("attacks", []),
            grounded_extension=df.get("extensions", {}).get("grounded", []),
            preferred_extensions=df.get("extensions", {}).get("preferred", []),
            stable_extensions=df.get("extensions", {}).get("stable", []),
            interpretation=DeepSynthesisAgent._interpret_dung(df),
        )

    @staticmethod
    def _build_belief_retractions(state: Any) -> List[BeliefRetraction]:
        retractions: List[BeliefRetraction] = []

        # Source 1: JTMS retraction cascade chain (jtms_core → jtms_retraction_chain)
        chain = getattr(state, "jtms_retraction_chain", [])
        for entry in chain:
            retractions.append(
                BeliefRetraction(
                    belief_name=entry.get("belief_name", ""),
                    was_valid=entry.get("was_valid"),
                    trigger=entry.get("trigger", ""),
                )
            )

        # Source 2: AGM belief revision results (conversational_orchestrator
        # _run_belief_revision_from_state → belief_revision_results).
        # Each entry has {id, method, original: List[str], revised: List[str]}.
        # Beliefs present in original but absent from revised were contracted.
        br_results = getattr(state, "belief_revision_results", [])
        for br in br_results:
            original = set(br.get("original", []))
            revised = set(br.get("revised", []))
            contracted = original - revised
            method = br.get("method", "unknown")
            for belief in contracted:
                retractions.append(
                    BeliefRetraction(
                        belief_name=belief,
                        was_valid=True,
                        trigger=f"{method}_contraction",
                    )
                )

        return retractions

    @staticmethod
    def _build_counter_arguments(state: Any) -> List[CounterArgumentEntry]:
        cas = getattr(state, "counter_arguments", [])
        weak_args = set()
        # Identify weak arguments from quality scores
        quality = getattr(state, "argument_quality_scores", {})
        for arg_id, scores in quality.items():
            if isinstance(scores, dict) and scores.get("overall", 10.0) < 5.0:
                weak_args.add(arg_id)

        entries = []
        for ca in cas:
            ca_id = ca.get("id", "")
            entries.append(
                CounterArgumentEntry(
                    counter_id=ca_id,
                    original_arg=ca.get("original_argument", ""),
                    counter_content=ca.get("counter_content", ""),
                    strategy=ca.get("strategy", ""),
                    score=ca.get("score", 0.0),
                    criteria_scores=ca.get("criteria_scores", {}),
                    targets_weakest=any(
                        a in weak_args for a in ca.get("target_arg_ids", [])
                    ),
                )
            )
        return entries

    @staticmethod
    def _build_cross_text_parallels(state: Any) -> List[CrossTextParallel]:
        # Cross-text parallels require comparison data not yet in state.
        # Placeholder — will be populated when multi-corpus runs happen.
        parallels = getattr(state, "cross_text_parallels", [])
        if parallels:
            return [CrossTextParallel(**p) for p in parallels]
        return []

    @staticmethod
    def _build_convergent_verdicts(state: Any) -> tuple:
        """Compute cross-method convergence verdicts (Track DD #637).

        Delegates to ``build_convergent_synthesis`` (Track BB #634) and maps its
        output onto ``ConvergentVerdict`` records ordered by descending
        convergence strength. Returns ``(verdicts, conclusion)``.
        """
        from argumentation_analysis.plugins.narrative_synthesis_plugin import (
            build_convergent_synthesis,
        )

        try:
            synthesis = build_convergent_synthesis(state)
        except Exception as e:  # never let synthesis crash report generation
            logger.warning(f"Convergence computation failed: {e}")
            return [], ""

        verdicts_dict = synthesis.get("convergent_verdicts", {})
        insights = synthesis.get("emergent_insights", [])
        ordered = sorted(
            verdicts_dict.items(), key=lambda kv: kv[1]["score"], reverse=True
        )
        verdicts = []
        for (arg_id, data), statement in zip(ordered, insights):
            methods = [m for m, _ in data["signals"]]
            verdicts.append(
                ConvergentVerdict(
                    arg_id=arg_id,
                    score=data["score"],
                    methods=methods,
                    statement=statement,
                )
            )
        return verdicts, synthesis.get("conclusion", "")

    @staticmethod
    async def _build_final_synthesis(
        state: Any, report: DeepSynthesisReport, transcript: Optional[List[Dict]] = None
    ) -> str:
        """Section 9: 6-section political-rhetorical briefing (template fallback)."""
        so = report.source_overview
        stakes_data = getattr(report, "_raw_stakes", {}) or {}
        stakes_list = stakes_data.get("stakes", [])
        sh_list = stakes_data.get("stakeholders", [])
        register = stakes_data.get("rhetorical_register", "")
        arena = stakes_data.get("discursive_arena", "")

        # Section 1 — Contexte & énonciation
        s1 = (
            f"## 1. Contexte & énonciation\n\n"
            f"This {so.discourse_type or 'unknown'} discourse originates from source "
            f"'{so.opaque_id}', delivered in {so.language or 'unknown'} during the "
            f"{so.era or 'unknown'} era"
        )
        if so.speaker:
            s1 += f" by {so.speaker}"
        if so.venue:
            s1 += f" at {so.venue}"
        if so.topic:
            s1 += f" on the topic of {so.topic}"
        s1 += f". The text comprises {so.length_words:,} words.\n"
        if register:
            s1 += f"Rhetorical register: {register}. "
        if arena:
            s1 += f"Discursive arena: {arena}."
        s1 += "\n"

        # Section 2 — Enjeux soulevés
        s2 = "## 2. Enjeux soulevés\n\n"
        if stakes_list:
            for s in stakes_list[:5]:
                s2 += (
                    f"- **{s.get('stake_type', 'unknown')}**: "
                    f"{s.get('description', 'No description')}\n"
                )
        else:
            s2 += "No typed stakes were extracted for this discourse.\n"

        # Section 3 — Parties engagées & positionnement
        s3 = "## 3. Parties engagées & positionnement\n\n"
        if sh_list:
            for sh in sh_list[:5]:
                s3 += (
                    f"- **{sh.get('name', '?')}** (role: {sh.get('role', '?')}, "
                    f"stance: {sh.get('stance', '?')})\n"
                )
        else:
            s3 += "No stakeholders were identified in this analysis.\n"

        # Section 4 — Ressorts rhétoriques
        n_args = len(report.argument_map)
        n_fallacies = len(report.fallacy_diagnoses)
        n_formal = len(report.formal_findings)
        n_counters = len(report.counter_arguments)
        families = sorted(set(f.family for f in report.fallacy_diagnoses))
        dung_ext = ", ".join(report.dung_structure.grounded_extension) or "none"
        s4 = (
            f"## 4. Ressorts rhétoriques\n\n"
            f"The analysis identified **{n_args} arguments**, "
            f"**{n_fallacies} fallacies** across {len(families)} families "
            f"({', '.join(families) or 'none'}), and **{n_formal} formal findings**. "
            f"Dung grounded extension: [{dung_ext}].\n"
        )
        if report.fallacy_diagnoses:
            top = sorted(
                report.fallacy_diagnoses,
                key=lambda f: len(f.commentary),
                reverse=True,
            )[:3]
            s4 += "\nTop fallacies:\n"
            for f in top:
                s4 += f"- {f.family} ({f.taxonomy_path}): " f"{f.commentary[:120]}\n"
        if report.counter_arguments:
            best = max(report.counter_arguments, key=lambda c: c.score)
            s4 += (
                f"\nStrongest counter-argument (score {best.score:.2f}, "
                f"strategy: {best.strategy}): {best.counter_content[:120]}...\n"
            )

        # Section 5 — Voix des spécialistes
        specialist_commentary = getattr(report, "_specialist_commentary", "")
        trace_data = getattr(report, "_raw_analysis_trace", [])
        s5 = "## 5. Voix des spécialistes\n\n"
        has_content = False
        if specialist_commentary:
            s5 += f"{specialist_commentary}\n"
            has_content = True
        if trace_data:
            for entry in trace_data:
                agent = entry.get("agent", "?")
                reacts = ", ".join(entry.get("reacts_to", []))
                summary = entry.get("summary", "")
                s5 += f'- [{agent}] (réagit à: {reacts}) → "{summary}"\n'
            has_content = True
        if not has_content and report.convergent_verdicts:
            s5 += (
                "No specialist commentaries were deposited "
                "during this analysis run.\n\n"
            )
            s5 += "Convergent verdicts (cross-method agreement):\n"
            for v in report.convergent_verdicts:
                s5 += f"- {v.arg_id}: {v.score} methods ({', '.join(v.methods)})\n"
        elif not has_content:
            s5 += (
                "No specialist commentaries were deposited during this analysis run. "
                "No cross-method convergence was detected.\n"
            )

        # Section 6 — Lecture politique
        s6 = (
            f"## 6. Lecture politique\n\n"
            f"This {so.discourse_type or 'unknown'} discourse deploys "
            f"{n_args} arguments across {len(families)} fallacy families, "
            f"revealing a structured rhetorical strategy."
        )
        if register:
            s6 += f" The dominant register is **{register}**"
            if arena:
                s6 += f", deployed in a **{arena}** arena"
            s6 += "."
        s6 += (
            f"\n\nThe multi-agent orchestration identified {n_fallacies} fallacies "
            f"and {n_counters} counter-arguments, with {n_formal} formal-method "
            f"findings providing independent verification. "
            f"The Dung grounded extension contains [{dung_ext}], "
            f"indicating which arguments survive dialectical scrutiny."
        )
        if report.convergent_verdicts:
            n_conv = len(report.convergent_verdicts)
            s6 += (
                f"\n\nCrucially, **{n_conv} argument(s) converge across independent "
                f"methods**, signalling robustness in the diagnostic findings. "
                f"This cross-method agreement is the signature insight unavailable "
                f"to a single LLM pass."
            )
        s6 += "\n"

        return "\n".join([s1, s2, s3, s4, s5, s6])

    # ------------------------------------------------------------------
    # Markdown rendering
    # ------------------------------------------------------------------

    @staticmethod
    def render_markdown(report: DeepSynthesisReport) -> str:
        """Render the full report as markdown."""
        sections = []

        # Header
        sections.append(f"# Deep Analysis Report — {report.source_overview.opaque_id}")
        sections.append(f"_Generated: {report.report_timestamp}_  ")
        sections.append(f"_Sections populated: {report.sections_populated}/9_  ")
        sections.append(f"_State fields consumed: {report.total_state_fields}_\n")

        # S1 — Source overview
        so = report.source_overview
        sections.append("## 1. Source Overview\n")
        sections.append(f"| Field | Value |")
        sections.append(f"|-------|-------|")
        sections.append(f"| Opaque ID | `{so.opaque_id}` |")
        sections.append(f"| Era | {so.era} |")
        sections.append(f"| Language | {so.language} |")
        sections.append(f"| Discourse type | {so.discourse_type} |")
        sections.append(
            f"| Length | {so.length_chars:,} chars / {so.length_words:,} words |\n"
        )
        if so.contextual_frame:
            sections.append(f"{so.contextual_frame}\n")

        # S2 — Argument map
        sections.append("## 2. Argument Map\n")
        if report.argument_map:
            sections.append("| ID | Stance | Description | Attacked by |")
            sections.append("|----|--------|-------------|-------------|")
            for a in report.argument_map:
                desc = a.description[:100] + ("..." if len(a.description) > 100 else "")
                attacked = ", ".join(a.attacked_by) if a.attacked_by else "—"
                sections.append(f"| `{a.arg_id}` | {a.stance} | {desc} | {attacked} |")
            sections.append("")
        else:
            sections.append("_No arguments identified in this run._\n")

        # S3 — Fallacy diagnosis
        sections.append("## 3. Fallacy Diagnosis by Family\n")
        if report.fallacy_diagnoses:
            for f in report.fallacy_diagnoses:
                sections.append(
                    f"### {f.fallacy_id}: {f.family} — `{f.taxonomy_path}`\n"
                )
                sections.append(f'> **Textual span**: "{f.textual_span}"\n')
                sections.append(f"{f.commentary}\n")
                if f.impacted_args:
                    sections.append(
                        f"_Impacts: {', '.join(f'`{a}`' for a in f.impacted_args)}_\n"
                    )
        else:
            sections.append("_No fallacies detected in this run._\n")

        # S4 — Formal method findings
        sections.append("## 4. Formal-Method Findings\n")
        if report.formal_findings:
            for i, ff in enumerate(report.formal_findings, 1):
                sections.append(f"### Finding {i}: {ff.logic_type}\n")
                if ff.axioms:
                    sections.append("**Axioms:**")
                    for ax in ff.axioms:
                        sections.append(f"- `{ax}`")
                    sections.append("")
                if ff.queries:
                    sections.append("**Queries:**")
                    for q in ff.queries:
                        sections.append(f"- `{q}`")
                    sections.append("")
                if ff.results:
                    sections.append("**Results:**")
                    for r in ff.results:
                        sections.append(f"- {r}")
                    sections.append("")
                if ff.inconsistency_measures:
                    sections.append(
                        f"**Inconsistency measures:** `{ff.inconsistency_measures}`\n"
                    )
                if ff.linked_args:
                    sections.append(
                        f"_Linked to arguments: {', '.join(f'`{a}`' for a in ff.linked_args)}_\n"
                    )
        else:
            sections.append("_No formal findings in this run._\n")

        # S5 — Dung dialectical structure
        sections.append("## 5. Dialectical Structure (Dung)\n")
        ds = report.dung_structure
        if ds and ds.arguments:
            sections.append(
                f"**Framework**: {ds.framework_name} ({len(ds.arguments)} arguments, {len(ds.attacks)} attacks)\n"
            )
            if ds.attacks:
                sections.append("**Attack relations:**")
                for atk in ds.attacks:
                    sections.append(f"- `{atk[0]}` → `{atk[1]}`")
                sections.append("")
            if ds.grounded_extension:
                sections.append(
                    f"**Grounded extension**: {', '.join(f'`{a}`' for a in ds.grounded_extension)}\n"
                )
            if ds.preferred_extensions:
                sections.append("**Preferred extensions:**")
                for ext in ds.preferred_extensions:
                    sections.append(f"- {', '.join(f'`{a}`' for a in ext)}")
                sections.append("")
            if ds.stable_extensions:
                sections.append("**Stable extensions:**")
                for ext in ds.stable_extensions:
                    sections.append(f"- {', '.join(f'`{a}`' for a in ext)}")
                sections.append("")
            if ds.interpretation:
                sections.append(f"{ds.interpretation}\n")
        else:
            sections.append("_No Dung framework computed in this run._\n")

        # S6 — Belief revision trace
        sections.append("## 6. Belief Revision Trace\n")
        if report.belief_retractions:
            for br in report.belief_retractions:
                status = "valid" if br.was_valid else "invalid"
                sections.append(
                    f"- **{br.belief_name}** (was {status}): retracted because _{br.trigger}_"
                )
            sections.append("")
        else:
            sections.append("_No belief retractions in this run._\n")

        # S7 — Counter-arguments
        sections.append("## 7. Counter-Arguments\n")
        if report.counter_arguments:
            sections.append("| ID | Strategy | Score | Targets weakest | Content |")
            sections.append("|----|----------|-------|-----------------|---------|")
            for ca in report.counter_arguments:
                content = ca.counter_content[:80] + (
                    "..." if len(ca.counter_content) > 80 else ""
                )
                weakest = "Yes" if ca.targets_weakest else "No"
                sections.append(
                    f"| `{ca.counter_id}` | {ca.strategy} | {ca.score:.2f} | {weakest} | {content} |"
                )
            sections.append("")
        else:
            sections.append("_No counter-arguments generated in this run._\n")

        # S8 — Cross-text parallels
        sections.append("## 8. Cross-Text Rhetorical Parallels\n")
        if report.cross_text_parallels:
            for p in report.cross_text_parallels:
                sections.append(
                    f"- **{p.corpus_x}** ↔ **{p.corpus_y}** ({p.parallel_type}): "
                    f'"{p.move_x[:60]}..." ↔ "{p.move_y[:60]}..."'
                )
                if p.commentary:
                    sections.append(f"  _{p.commentary}_")
            sections.append("")
        else:
            sections.append(
                "_No cross-text parallels in this run (single-corpus analysis)._\n"
            )

        # Convergent verdicts (Track DD #637) — cross-method agreement, rendered
        # from the structured field so it appears regardless of synthesis path.
        sections.append("## Convergent Verdicts (cross-method agreement)\n")
        if report.convergent_verdicts:
            if report.convergence_prose:
                # Track GG #644 — citation-rich LLM narration grounded in the
                # verdicts. The structured statements remain available via
                # report.convergent_verdicts for downstream/JSON consumers.
                sections.append(report.convergence_prose)
                sections.append("")
            else:
                for v in report.convergent_verdicts:
                    sections.append(v.statement)
                    sections.append("")
            if report.convergence_conclusion:
                sections.append(f"**Conclusion** : {report.convergence_conclusion}\n")
        else:
            sections.append(
                "_No argument was independently flagged by two or more methods — "
                "the argumentative structure resists cross-method scrutiny._\n"
            )

        # Adjudication (Track NN #659) — grounded vs claimed families
        sections.append("## Adjudication: Claimed vs Grounded Fallacy Families\n")
        if report.adjudication_table:
            sections.append("| Family | Status | Evidence |")
            sections.append("|--------|--------|----------|")
            for row in report.adjudication_table:
                icon = "✅" if row["status"] == "grounded" else "⚠️"
                sections.append(
                    f"| {row['family']} | {icon} {row['status']} | {row['evidence']} |"
                )
            sections.append("")
        else:
            sections.append("_No fallacy families to adjudicate._\n")

        # S9 — Final synthesis
        sections.append(
            report.final_synthesis
            if report.final_synthesis
            else "_Final synthesis not generated._\n"
        )

        return "\n".join(sections)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _infer_stance(text: str) -> str:
        lower = text.lower()
        pro_words = ["support", "affirm", "defend", "argue for", "claim", "propose"]
        con_words = ["oppose", "reject", "refute", "against", "deny", "attack"]
        if any(w in lower for w in pro_words):
            return "pro"
        if any(w in lower for w in con_words):
            return "con"
        return "neutral"

    @staticmethod
    def _fallacy_family(fallacy_type: str) -> str:
        """Map a free-text fallacy label to its taxonomic family.

        The per-argument detector emits free-text leaf names (bilingual FR/EN,
        e.g. "Sophisme génétique", "causal oversimplification", "appel au
        peuple") rather than a taxonomy_pk, so the report must re-derive the
        family here. The previous 11-keyword English-only map sent ~90% of real
        detections to "other" — every dense-corpus report was a wall of
        `fallacy/other/...`, which reads worse to a jury than a one-shot naming
        recognizable families. This bilingual table covers the labels the
        detector actually produces. Rules are checked in order and the first
        matching substring wins, so disambiguating multi-word keys are placed
        before the generic ones they contain (e.g. "appel au peuple" before the
        bare "appel" relevance catch-all; the inductive/causal/presumption
        blocks precede the relevance block so "appel à l'anecdote" resolves to
        inductive and "appel aux conséquences" to presumption).
        """
        ft = fallacy_type.lower()
        rules = [
            # presumption (precedes "nature"/"naturalistic" → relevance)
            ("is→ought", "presumption"),
            ("is-ought", "presumption"),
            ("faux dilemme", "presumption"),
            ("false dilemma", "presumption"),
            ("false dichotomy", "presumption"),
            ("homme de paille", "presumption"),
            ("straw", "presumption"),
            ("pétition de principe", "presumption"),
            ("begging", "presumption"),
            ("circular", "presumption"),
            ("enthym", "presumption"),
            ("package", "presumption"),
            ("conséquences", "presumption"),
            ("consequences", "presumption"),
            ("fin justifie", "presumption"),
            # causal
            ("simplification causale", "causal"),
            ("causal oversimplification", "causal"),
            ("causalité", "causal"),
            ("false cause", "causal"),
            ("fausse cause", "causal"),
            ("post hoc", "causal"),
            ("temporalité-cause", "causal"),
            ("pente", "causal"),
            ("slippery", "causal"),
            ("complot", "causal"),
            ("conspiracy", "causal"),
            # inductive
            ("généralisation", "inductive"),
            ("generaliz", "inductive"),
            ("hasty", "inductive"),
            ("anecdote", "inductive"),
            ("anecdotal", "inductive"),
            ("regroupement", "inductive"),
            ("clustering", "inductive"),
            ("cherry", "inductive"),
            ("suppression des preuves", "inductive"),
            ("comparaison trompeuse", "inductive"),
            ("false analogy", "inductive"),
            ("fausse analogie", "inductive"),
            # relevance
            ("génétique", "relevance"),
            ("genetic", "relevance"),
            ("ad hominem", "relevance"),
            ("attaque personnelle", "relevance"),
            ("appel à l'émotion", "relevance"),
            ("appel a l'emotion", "relevance"),
            ("appeal to emotion", "relevance"),
            ("appel à la peur", "relevance"),
            ("appeal to fear", "relevance"),
            ("appel au peuple", "relevance"),
            ("ad populum", "relevance"),
            ("bandwagon", "relevance"),
            ("appel à l'autorité", "relevance"),
            ("appeal to authority", "relevance"),
            ("nature", "relevance"),
            ("naturalistic", "relevance"),
            ("scapegoat", "relevance"),
            ("red herring", "relevance"),
            ("hareng rouge", "relevance"),
            ("tu quoque", "relevance"),
            ("appel", "relevance"),
            ("appeal", "relevance"),
            # ambiguity
            ("equivocation", "ambiguity"),
            ("équivoque", "ambiguity"),
            ("amphiboly", "ambiguity"),
            ("amphibologie", "ambiguity"),
            ("tromperie implicite", "ambiguity"),
            ("étiquetage", "ambiguity"),
            ("mislabel", "ambiguity"),
        ]
        for kw, family in rules:
            if kw in ft:
                return family
        return "other"

    @staticmethod
    def _interpret_dung(df: Dict[str, Any]) -> str:
        args = df.get("arguments", [])
        attacks = df.get("attacks", [])
        extensions = df.get("extensions", {})
        grounded = extensions.get("grounded", [])
        if not args:
            return ""
        lines = [
            f"The framework contains {len(args)} arguments and {len(attacks)} attacks."
        ]
        if grounded:
            lines.append(
                f"The grounded extension contains {len(grounded)} argument(s): "
                f"{', '.join(grounded)}. These are the arguments that survive all attacks."
            )
        return " ".join(lines)

    @staticmethod
    def _count_state_fields(state: Any) -> int:
        count = 0
        for attr in [
            "identified_arguments",
            "identified_fallacies",
            "belief_sets",
            "query_log",
            "counter_arguments",
            "argument_quality_scores",
            "jtms_beliefs",
            "jtms_retraction_chain",
            "dung_frameworks",
            "propositional_analysis_results",
            "fol_analysis_results",
            "modal_analysis_results",
            "formal_synthesis_reports",
            "aspic_results",
            "belief_revision_results",
            "ranking_results",
            "debate_transcripts",
            "narrative_synthesis",
        ]:
            val = getattr(state, attr, None)
            if val:
                count += len(val)
        return count

    @staticmethod
    def _count_populated_sections(report: DeepSynthesisReport) -> int:
        n = 0
        if report.source_overview.length_chars > 0:
            n += 1
        if report.argument_map:
            n += 1
        if report.fallacy_diagnoses:
            n += 1
        if report.formal_findings:
            n += 1
        if report.dung_structure and report.dung_structure.arguments:
            n += 1
        if report.belief_retractions:
            n += 1
        if report.counter_arguments:
            n += 1
        if report.cross_text_parallels:
            n += 1
        if report.final_synthesis:
            n += 1
        return n

    @staticmethod
    def _build_adjudication_table(
        fallacy_diagnoses: List[FallacyDiagnosis],
        convergent_verdicts: List[ConvergentVerdict],
    ) -> List[Dict[str, str]]:
        """Track NN #659 — adjudicate claimed vs grounded fallacy families.

        For each detected family, decide:
        - 'grounded': at least one per-argument detection targets an argument
          that also appears in a convergent verdict (cross-method confirmed).
        - 'claimed': detected, but no per-argument anchor with convergence
          (wide-net only, or per-arg but without cross-method support).
        """
        converged_args: Dict[str, ConvergentVerdict] = {
            v.arg_id: v for v in convergent_verdicts
        }
        family_entries: Dict[str, List[FallacyDiagnosis]] = {}
        for fd in fallacy_diagnoses:
            family_entries.setdefault(fd.family, []).append(fd)

        rows: List[Dict[str, str]] = []
        for family in sorted(family_entries):
            entries = family_entries[family]
            grounded_args = [
                a for fd in entries for a in fd.impacted_args if a in converged_args
            ]
            if grounded_args:
                best = grounded_args[0]
                v = converged_args[best]
                evidence = (
                    f"`{best}` — {v.score} independent method(s): "
                    f"{', '.join(v.methods)}"
                )
                rows.append(
                    {"family": family, "status": "grounded", "evidence": evidence}
                )
            else:
                per_arg_ids = sorted({a for fd in entries for a in fd.impacted_args})
                if per_arg_ids:
                    evidence = (
                        f"per-argument detection "
                        f"(`{'`, `'.join(per_arg_ids)}`) — no cross-method confirmation"
                    )
                else:
                    evidence = "wide-net (whole-text) detection only — no argument-level anchor"
                rows.append(
                    {"family": family, "status": "claimed", "evidence": evidence}
                )
        return rows

    async def _llm_convergence_prose(self, state: Any) -> str:
        """Track GG #644 — LLM prose for the convergence section.

        Reuses Track CC's grounded prompt builder (``_build_prose_prompt``) over
        the convergent-synthesis evidence and invokes this agent's own kernel.
        Returns "" (renderer falls back to template verdict statements) when no
        LLM service is configured, no convergent verdicts exist, or the call
        fails. The prompt is strictly grounded in arg IDs / methods / scores, so
        the prose cannot introduce content absent from the structured evidence.
        """
        if not self._llm_service_id:
            return ""
        try:
            from argumentation_analysis.plugins.narrative_synthesis_plugin import (
                build_convergent_synthesis,
                _build_prose_prompt,
            )

            synthesis = build_convergent_synthesis(state)
            if not synthesis.get("convergent_verdicts"):
                return ""

            prompt = _build_prose_prompt(synthesis)
            settings = self.kernel.get_prompt_execution_settings_from_service_id(
                self._llm_service_id
            )
            result = await self.kernel.invoke_prompt(
                function_name="deep_synthesis_convergence_prose",
                plugin_name="deep_synthesis",
                prompt=prompt,
                settings=settings,
            )
            prose = str(result).strip() if result else ""
            return prose
        except Exception as e:
            logger.debug(f"LLM convergence prose skipped: {e}")
            return ""

    async def _llm_synthesis(self, report: DeepSynthesisReport) -> Optional[str]:
        """Produce a 6-section political-rhetorical briefing via LLM."""
        if not self._llm_service_id:
            return None
        try:
            so = report.source_overview

            # -- Section 1 data: Contexte & énonciation --
            context_block = ""
            if so.speaker or so.topic or so.venue:
                context_block = (
                    f"\n[SECTION 1 DATA — Contexte & énonciation]\n"
                    f"Speaker: {so.speaker or 'unknown'}. "
                    f"Date/era: {so.date_or_year or so.era or 'unknown'}. "
                    f"Venue: {so.venue or 'unknown'}. "
                    f"Topic: {so.topic or 'unknown'}. "
                    f"Register: {so.register or 'unknown'}. "
                    f"Synopsis: {so.synopsis or 'not available'}.\n"
                    f"Language: {so.language or 'unknown'}. "
                    f"Length: {so.length_words} words.\n"
                )
            else:
                context_block = (
                    f"\n[SECTION 1 DATA — Contexte & énonciation]\n"
                    f"Source: {so.contextual_frame}\n"
                )

            # -- Section 2 data: Enjeux soulevés (from TT stakes) --
            stakes_section = "\n[SECTION 2 DATA — Enjeux soulevés]\n"
            stakes_data = getattr(report, "_raw_stakes", {})
            if stakes_data:
                stakes_list = stakes_data.get("stakes", [])
                register = stakes_data.get("rhetorical_register", "")
                arena = stakes_data.get("discursive_arena", "")
                if stakes_list:
                    for s in stakes_list[:5]:
                        stakes_section += (
                            f"  Stake [{s.get('stake_type', '?')}]: "
                            f"{s.get('description', '')}\n"
                        )
                else:
                    stakes_section += "  No typed stakes extracted.\n"
                if register:
                    stakes_section += f"  Rhetorical register: {register}\n"
                if arena:
                    stakes_section += f"  Discursive arena: {arena}\n"
            else:
                stakes_section += "  No stakes data available.\n"

            # -- Section 3 data: Parties engagées (from TT stakeholders) --
            parties_section = "\n[SECTION 3 DATA — Parties engagées]\n"
            if stakes_data:
                sh_list = stakes_data.get("stakeholders", [])
                if sh_list:
                    for sh in sh_list[:5]:
                        parties_section += (
                            f"  {sh.get('name', '?')} "
                            f"(role={sh.get('role', '?')}, "
                            f"stance={sh.get('stance', '?')})\n"
                        )
                else:
                    parties_section += "  No stakeholders identified.\n"
            else:
                parties_section += "  No stakeholder data available.\n"

            # -- Section 4 data: Ressorts rhétoriques --
            rhetoric_section = "\n[SECTION 4 DATA — Ressorts rhétoriques]\n"
            rhetoric_section += (
                f"  Arguments: {len(report.argument_map)}. "
                f"Fallacies: {len(report.fallacy_diagnoses)}. "
                f"Formal findings: {len(report.formal_findings)}. "
                f"Counter-arguments: {len(report.counter_arguments)}.\n"
                f"  Key fallacy families: "
                f"{', '.join(set(f.family for f in report.fallacy_diagnoses)) or 'none'}. "
                f"Dung grounded extension: "
                f"{', '.join(report.dung_structure.grounded_extension) or 'none'}.\n"
            )
            if report.fallacy_diagnoses:
                top_3 = sorted(
                    report.fallacy_diagnoses,
                    key=lambda f: len(f.commentary),
                    reverse=True,
                )[:3]
                for f in top_3:
                    rhetoric_section += (
                        f"  Fallacy: {f.family} ({f.taxonomy_path}): "
                        f"{f.commentary[:150]}\n"
                    )
            if report.counter_arguments:
                best = max(report.counter_arguments, key=lambda c: c.score)
                rhetoric_section += (
                    f"  Strongest counter-argument (score {best.score:.2f}): "
                    f"{best.counter_content[:150]}\n"
                )
            if report.formal_findings:
                for ff in report.formal_findings[:2]:
                    rhetoric_section += (
                        f"  Formal result ({ff.logic_type}): "
                        f"{'; '.join(ff.results[:3]) if ff.results else 'no query results'}\n"
                    )

            # -- Section 5 data: Voix des spécialistes --
            specialists_section = "\n[SECTION 5 DATA — Voix des spécialistes]\n"
            specialist_commentary = getattr(report, "_specialist_commentary", "")
            if specialist_commentary:
                specialists_section += f"{specialist_commentary}\n"
            # UU #724: enrich with analysis_trace entries
            trace_data = getattr(report, "_raw_analysis_trace", [])
            if trace_data:
                for entry in trace_data:
                    agent = entry.get("agent", "?")
                    reacts = ", ".join(entry.get("reacts_to", []))
                    summary = entry.get("summary", "")
                    specialists_section += (
                        f'  [{agent}] (réagit à: {reacts}) → "{summary}"\n'
                    )
            if not specialist_commentary and not trace_data:
                specialists_section += "  No specialist commentaries deposited.\n"

            # -- Section 6 data: Convergence (feeds Lecture politique) --
            convergence_section = "\n[SECTION 6 DATA — Convergence evidence]\n"
            if report.convergent_verdicts:
                for v in report.convergent_verdicts:
                    convergence_section += (
                        f"  {v.arg_id}: {v.score} methods concur "
                        f"({', '.join(v.methods)})\n"
                    )
                convergence_section += (
                    f"  Convergence conclusion: " f"{report.convergence_conclusion}\n"
                )
            else:
                convergence_section += "  No cross-method convergence.\n"

            prompt = (
                "Produce the 6-section political-rhetorical briefing as specified "
                "in your system prompt. Use the data blocks below. Each section "
                "heading must be '## N. Title' on its own line. 8-12 paragraphs "
                "total. Intelligence-briefing register. Opaque IDs only.\n"
                f"\nSource: {so.contextual_frame}"
                f"{context_block}"
                f"{stakes_section}"
                f"{parties_section}"
                f"{rhetoric_section}"
                f"{specialists_section}"
                f"{convergence_section}"
            )
            # Use SK chat completion
            settings = self.kernel.get_prompt_execution_settings_from_service_id(
                self._llm_service_id
            )
            result = await self.kernel.invoke_prompt(
                function_name="deep_synthesis_thesis",
                plugin_name="deep_synthesis",
                prompt=prompt,
                settings=settings,
            )
            return str(result) if result else None
        except Exception as e:
            logger.debug(f"LLM thesis generation skipped: {e}")
            return None


# Module-level registry function
def register_with_capability_registry(registry):
    """Register DeepSynthesisAgent with the capability registry."""
    registry.register_agent(
        name="deep_synthesis_agent",
        agent_class=DeepSynthesisAgent,
        capabilities=[
            "deep_synthesis",
            "multi_page_report",
            "grounded_analysis",
        ],
        metadata={
            "description": "Aggregates spectacular-run state into multi-page grounded markdown report (9 sections)",
            "sections": 9,
            "report_version": "1.0.0",
        },
    )
