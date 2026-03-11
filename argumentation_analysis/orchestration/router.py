"""
Intelligent text analysis router for automatic workflow selection.

Analyzes input text and dynamically selects the most relevant analysis
capabilities, building a custom WorkflowDefinition.

Strategy:
  - Tier 1 (primary): LLM-based routing via AsyncOpenAI — a well-prompted
    model determines which capabilities are relevant for the input text.
  - Tier 2 (fallback): Lightweight heuristics (text length, keywords, accent
    detection) — used only when no LLM API key is available.
"""

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from argumentation_analysis.orchestration.workflow_dsl import (
    WorkflowBuilder,
    WorkflowDefinition,
)

logger = logging.getLogger(__name__)


# ============================================================
# Constants
# ============================================================

KNOWN_CAPABILITIES: List[str] = [
    "argument_quality",
    "counter_argument_generation",
    "adversarial_debate",
    "governance_simulation",
    "belief_maintenance",
    "neural_fallacy_detection",
    "hierarchical_fallacy_detection",
    "semantic_indexing",
    "speech_transcription",
]

CAPABILITY_DESCRIPTIONS: Dict[str, str] = {
    "argument_quality": (
        "Evaluate argument clarity, coherence, relevance across 9 argumentative virtues"
    ),
    "counter_argument_generation": (
        "Generate counter-arguments using 5 rhetorical strategies "
        "(reductio ad absurdum, counter-example, distinction, reformulation, concession)"
    ),
    "adversarial_debate": (
        "Multi-personality adversarial debate simulation with argument scoring"
    ),
    "governance_simulation": (
        "Democratic voting and deliberation methods "
        "(majority, Borda, Condorcet, approval, quadratic, Byzantine, Raft)"
    ),
    "belief_maintenance": (
        "JTMS truth maintenance system — track belief dependencies, "
        "propagate retractions, maintain logical consistency"
    ),
    "neural_fallacy_detection": (
        "Neural fallacy/sophism detection using transformer models"
    ),
    "hierarchical_fallacy_detection": (
        "Hierarchical taxonomy-guided fallacy detection — iterative deepening "
        "through 1566-node taxonomy with 8 fallacy families (more precise, "
        "identifies obscure/specialized fallacies)"
    ),
    "semantic_indexing": (
        "Semantic argument search and indexing for large document collections"
    ),
    "speech_transcription": (
        "Speech-to-text transcription of audio content"
    ),
}

ROUTING_SYSTEM_PROMPT = """\
You are a text analysis router. Given a text and a list of available analysis \
capabilities, select which capabilities are relevant for analyzing this text. \
Consider the text's language, structure, content, and domain.

Available capabilities:
{capability_list}

Rules:
- Always include argument_quality (foundation for other analyses).
- Include counter_argument_generation for texts with clear argumentative structure.
- Include governance_simulation only for texts about collective decisions, voting, \
consensus, or democratic deliberation.
- Include adversarial_debate for controversial topics or texts presenting opposing \
viewpoints.
- Include belief_maintenance for texts with logical claims that can be modeled as \
beliefs with justification dependencies.
- Include neural_fallacy_detection for texts that may contain reasoning errors, \
sophisms, or manipulative rhetoric.
- Include hierarchical_fallacy_detection for texts where precise fallacy \
classification matters — it navigates a detailed taxonomy to find the most \
specific matching fallacy. Prefer this over neural_fallacy_detection for \
in-depth analysis.
- Include semantic_indexing only for long texts (>500 words) needing reference indexing.
- Include speech_transcription only if the input explicitly mentions audio or \
transcription needs.
- Prefer fewer capabilities for short texts, more for long substantive texts.

Respond with ONLY a JSON object (no markdown, no explanation):
{{"capabilities": ["cap1", "cap2", ...], "workflow_complexity": "light|standard|full"}}
"""

# Text truncation limit for LLM routing (cost control)
LLM_TEXT_LIMIT = 2000


# ============================================================
# Data structures
# ============================================================


@dataclass
class RoutingResult:
    """Result of text analysis routing."""

    selected_capabilities: List[str]
    workflow_complexity: str = "standard"  # "light", "standard", "full"
    routing_method: str = "heuristic"  # "llm" or "heuristic"
    confidence: float = 0.5  # 0-1, LLM routing typically gives higher confidence


# ============================================================
# TextAnalysisRouter
# ============================================================


class TextAnalysisRouter:
    """Analyzes input text and selects appropriate workflow capabilities.

    Primary: LLM-based routing (well-prompted, structured JSON output).
    Fallback: Lightweight heuristics when no LLM is available.
    """

    def __init__(self, registry=None):
        """
        Args:
            registry: Optional CapabilityRegistry to check which capabilities
                      are actually available (have registered providers).
        """
        self.registry = registry
        self._api_key = os.environ.get("OPENAI_API_KEY")
        self._model = os.environ.get("OPENAI_CHAT_MODEL_ID", "gpt-5-mini")

    # ----------------------------------------------------------
    # Public API
    # ----------------------------------------------------------

    async def analyze_and_route_async(
        self,
        text: str,
        registry=None,
    ) -> WorkflowDefinition:
        """Analyze text and build a custom workflow (async primary).

        Args:
            text: The text to analyze.
            registry: Optional override for the registry set in __init__.

        Returns:
            A WorkflowDefinition tailored to the text's characteristics.
        """
        reg = registry or self.registry
        available = self._get_available_capabilities(reg)

        # Tier 1: Try LLM routing
        if self._api_key:
            try:
                result = await self._route_with_llm(text, available)
                return self._build_workflow(result)
            except Exception as e:
                logger.warning(
                    "LLM routing failed, falling back to heuristics: %s", e
                )

        # Tier 2: Heuristic fallback
        result = self._route_with_heuristics(text, available)
        return self._build_workflow(result)

    def analyze_and_route(
        self,
        text: str,
        registry=None,
    ) -> WorkflowDefinition:
        """Sync wrapper around analyze_and_route_async."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # Already in async context — use heuristics only (no nested event loop)
            reg = registry or self.registry
            available = self._get_available_capabilities(reg)
            result = self._route_with_heuristics(text, available)
            return self._build_workflow(result)

        return asyncio.run(self.analyze_and_route_async(text, registry=registry))

    # ----------------------------------------------------------
    # Capability discovery
    # ----------------------------------------------------------

    def _get_available_capabilities(self, registry) -> List[str]:
        """Get capabilities that have registered providers in the registry."""
        if registry is None:
            return list(KNOWN_CAPABILITIES)

        available = []
        for cap in KNOWN_CAPABILITIES:
            try:
                providers = registry.find_for_capability(cap)
                if providers:
                    available.append(cap)
            except Exception:
                pass

        # Always include argument_quality even if not registered
        if "argument_quality" not in available:
            available.insert(0, "argument_quality")

        return available

    # ----------------------------------------------------------
    # Tier 1: LLM-based routing
    # ----------------------------------------------------------

    async def _route_with_llm(
        self, text: str, available_caps: List[str]
    ) -> RoutingResult:
        """Use LLM to determine which capabilities to activate."""
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self._api_key)

        # Build capability list for the prompt
        cap_lines = []
        for cap in available_caps:
            desc = CAPABILITY_DESCRIPTIONS.get(cap, cap)
            cap_lines.append(f"- {cap}: {desc}")
        cap_list_str = "\n".join(cap_lines)

        system_prompt = ROUTING_SYSTEM_PROMPT.format(
            capability_list=cap_list_str
        )
        user_prompt = f"Text to analyze:\n\n{text[:LLM_TEXT_LIMIT]}"

        response = await client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        content = response.choices[0].message.content.strip()

        # Strip markdown fences if present
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)

        parsed = json.loads(content)

        # Filter to only available capabilities
        raw_caps = parsed.get("capabilities", [])
        selected = [c for c in raw_caps if c in available_caps]
        complexity = parsed.get("workflow_complexity", "standard")

        # Ensure argument_quality is always included
        if "argument_quality" not in selected:
            selected.insert(0, "argument_quality")

        # Validate complexity
        if complexity not in ("light", "standard", "full"):
            complexity = "standard"

        return RoutingResult(
            selected_capabilities=selected,
            workflow_complexity=complexity,
            routing_method="llm",
            confidence=0.9,
        )

    # ----------------------------------------------------------
    # Tier 2: Heuristic fallback
    # ----------------------------------------------------------

    def _route_with_heuristics(
        self, text: str, available_caps: List[str]
    ) -> RoutingResult:
        """Lightweight heuristic fallback (no LLM needed)."""
        selected = ["argument_quality"]  # Always include
        text_lower = text.lower()
        word_count = len(text.split())

        # Counter-argument for substantial texts
        if word_count > 30:
            selected.append("counter_argument_generation")

        # Fallacy detection — prefer hierarchical for depth, neural for speed
        fallacy_keywords = {
            "sophisme", "fallac", "raisonnement", "logique", "argument",
            "erreur", "manipulation", "rhétorique", "ad hominem",
        }
        french_chars = set("àâäéèêëïîôùûüçœæ")
        has_french = any(c in french_chars for c in text_lower)
        has_fallacy_cue = any(kw in text_lower for kw in fallacy_keywords)

        if has_fallacy_cue or (has_french and word_count > 50):
            if "hierarchical_fallacy_detection" in available_caps:
                selected.append("hierarchical_fallacy_detection")
        if has_french:
            if "neural_fallacy_detection" in available_caps:
                selected.append("neural_fallacy_detection")

        # Governance keywords
        gov_keywords = {
            "vote", "décision", "consensus", "majorité", "élection",
            "délibération", "scrutin", "suffrage", "proposition",
            "assemblée", "démocratie",
        }
        if any(kw in text_lower for kw in gov_keywords):
            if "governance_simulation" in available_caps:
                selected.append("governance_simulation")

        # Debate/opposition patterns
        debate_markers = {
            "en revanche", "au contraire", "cependant", "néanmoins",
            "toutefois", "d'un côté", "de l'autre", "s'oppose",
            "contestant", "réfute", "objecte",
        }
        if any(m in text_lower for m in debate_markers):
            if "adversarial_debate" in available_caps:
                selected.append("adversarial_debate")

        # Complexity from text length
        if word_count < 50:
            complexity = "light"
        elif word_count < 300:
            complexity = "standard"
        else:
            complexity = "full"
            if "belief_maintenance" in available_caps:
                selected.append("belief_maintenance")

        # Semantic indexing for very long texts
        if word_count > 500:
            if "semantic_indexing" in available_caps:
                selected.append("semantic_indexing")

        # Filter to available caps
        selected = [c for c in selected if c in available_caps]

        return RoutingResult(
            selected_capabilities=selected,
            workflow_complexity=complexity,
            routing_method="heuristic",
            confidence=0.5,
        )

    # ----------------------------------------------------------
    # Workflow construction
    # ----------------------------------------------------------

    def _build_workflow(self, result: RoutingResult) -> WorkflowDefinition:
        """Build a WorkflowDefinition from a RoutingResult."""
        builder = WorkflowBuilder(f"auto_{result.workflow_complexity}")

        # Quality is always first (foundation)
        builder.add_phase("quality", capability="argument_quality")
        added_phases = {"quality"}

        # Counter-argument depends on quality
        if "counter_argument_generation" in result.selected_capabilities:
            builder.add_phase(
                "counter",
                capability="counter_argument_generation",
                depends_on=["quality"],
            )
            added_phases.add("counter")

        # Anchor for remaining phases
        anchor = "counter" if "counter" in added_phases else "quality"

        # Map of remaining capabilities to phase names and their dependency
        optional_phases = [
            ("neural_fallacy_detection", "neural_fallacy", ["quality"]),
            ("hierarchical_fallacy_detection", "hierarchical_fallacy", ["quality"]),
            ("governance_simulation", "governance", ["quality"]),
            ("adversarial_debate", "debate", [anchor]),
            ("belief_maintenance", "jtms", [anchor]),
            ("semantic_indexing", "index", [anchor]),
            ("speech_transcription", "transcribe", []),
        ]

        for cap, phase_name, deps in optional_phases:
            if cap in result.selected_capabilities:
                builder.add_phase(
                    phase_name,
                    capability=cap,
                    depends_on=deps if deps else None,
                    optional=True,
                )

        return builder.build()
