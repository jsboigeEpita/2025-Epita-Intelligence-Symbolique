"""Open-domain investigation module for Sherlock Modern (#358).

Extends the investigation paradigm beyond Cluedo to general rhetorical
analysis. Applies the whodunit-style framing:

- "Who attributes responsibility for fact X?"
- "Which thesis holds under which context/hypothesis?"
- "Under hypothesis H1, the author claims X; under H2, claim X collapses."

Works on any discourse text — no Cluedo-specific constraints.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from argumentation_analysis.core.shared_state import UnifiedAnalysisState

logger = logging.getLogger(__name__)


@dataclass
class Attribution:
    """A responsibility attribution under a specific hypothesis."""

    claim: str
    attribution: str
    hypothesis_id: str
    coherent: bool
    confidence: float = 0.0


@dataclass
class OpenDomainResult:
    """Result of an open-domain investigation."""

    document_id: str = ""
    claims_analyzed: int = 0
    attributions: List[Attribution] = field(default_factory=list)
    hypothesis_summary: Dict[str, str] = field(default_factory=dict)
    reasoning_trace: List[str] = field(default_factory=list)
    conclusion: str = ""


class OpenDomainInvestigator:
    """Whodunit-style argument analysis on any discourse.

    Uses SherlockModernOrchestrator for the heavy lifting, then
    interprets results through the attribution lens:
    - Who is responsible for what claim?
    - Which hypothesis supports or undermines each claim?
    """

    def __init__(self, state: Optional[UnifiedAnalysisState] = None):
        self.state = state

    async def investigate_document(
        self,
        discourse: str,
        document_id: str = "doc_A",
        context: Optional[Dict] = None,
    ) -> OpenDomainResult:
        """Run open-domain whodunit investigation on a discourse.

        Args:
            discourse: Text to analyze.
            document_id: Opaque ID for the document (privacy).
            context: Optional context for agents.

        Returns:
            OpenDomainResult with attributions and hypothesis analysis.
        """
        from argumentation_analysis.orchestration.sherlock_modern_orchestrator import (
            SherlockModernOrchestrator,
        )

        state = self.state or UnifiedAnalysisState(discourse)
        self.state = state

        # Run the Sherlock Modern investigation
        orchestrator = SherlockModernOrchestrator(state=state)
        inv_result = await orchestrator.investigate(discourse, context=context)

        # Build attributions from investigation trace
        claims = self._extract_claims_from_trace(inv_result.trace)
        hypotheses = inv_result.hypotheses

        attributions = self._build_attributions(claims, hypotheses)
        hypothesis_summary = self._build_hypothesis_summary(hypotheses)

        # Build conclusion
        conclusion = self._build_conclusion(
            document_id, claims, attributions, hypotheses
        )

        return OpenDomainResult(
            document_id=document_id,
            claims_analyzed=len(claims),
            attributions=attributions,
            hypothesis_summary=hypothesis_summary,
            reasoning_trace=inv_result.reasoning_chain,
            conclusion=conclusion,
        )

    def _extract_claims_from_trace(self, trace: List[Dict]) -> List[str]:
        """Extract claim descriptions from the investigation trace."""
        claims = []
        for step in trace:
            phase = step.get("phase", "")
            findings = step.get("findings", {})
            if phase == "extraction":
                claims_found = findings.get("claims_found", 0)
                args_found = findings.get("arguments_found", 0)
                if claims_found > 0:
                    claims.append(f"{claims_found} factual claim(s) extracted")
                if args_found > 0:
                    claims.append(f"{args_found} argumentative structure(s) identified")
            elif phase == "fallacy_detection":
                count = findings.get("fallacy_count", 0)
                if count > 0:
                    types = findings.get("types", [])
                    claims.append(
                        f"{count} inconsistency/es detected"
                        + (f" ({', '.join(types[:3])})" if types else "")
                    )
            elif phase == "quality_evaluation":
                score = findings.get("overall_score", 0)
                n = findings.get("arguments_evaluated", 0)
                # Skip the score line when no arguments were evaluated — the
                # 0.0/10 readout is meaningless and pollutes attribution
                # output (review #383).
                if n > 0:
                    claims.append(f"Reliability score: {score:.1f}/10 ({n} arguments)")
        return claims

    def _build_attributions(
        self,
        claims: List[str],
        hypotheses: List[Dict],
    ) -> List[Attribution]:
        """Build responsibility attributions under each hypothesis."""
        attributions = []
        for hyp in hypotheses:
            hyp_id = hyp.get("id", "unknown")
            coherent = hyp.get("coherent", False)
            assumptions = hyp.get("assumptions", [])

            for claim in claims:
                # Under a coherent hypothesis, the author's claim is maintained
                # Under an incoherent one, it is undermined
                if coherent:
                    attr_text = f"Author's claim ({claim}) is supported under {hyp_id}"
                    confidence = 0.7 + 0.1 * min(len(assumptions), 3)
                else:
                    attr_text = f"Author's claim ({claim}) is undermined under {hyp_id}"
                    confidence = 0.3

                attributions.append(
                    Attribution(
                        claim=claim,
                        attribution=attr_text,
                        hypothesis_id=hyp_id,
                        coherent=coherent,
                        confidence=min(confidence, 1.0),
                    )
                )
        return attributions

    def _build_hypothesis_summary(self, hypotheses: List[Dict]) -> Dict[str, str]:
        """Build a human-readable hypothesis summary."""
        summary = {}
        for hyp in hypotheses:
            hyp_id = hyp.get("id", "unknown")
            coherent = hyp.get("coherent", False)
            assumptions = hyp.get("assumptions", [])
            status = "COHERENT" if coherent else "INCOHERENT"
            summary[hyp_id] = f"{status} — assumptions: {assumptions}"
        return summary

    def _build_conclusion(
        self,
        doc_id: str,
        claims: List[str],
        attributions: List[Attribution],
        hypotheses: List[Dict],
    ) -> str:
        """Build the final whodunit conclusion."""
        if not claims and not hypotheses:
            return (
                f"Document {doc_id}: insufficient data for open-domain "
                f"investigation. Partial analysis only."
            )

        coherent_hyps = [h for h in hypotheses if h.get("coherent")]
        incoherent_hyps = [h for h in hypotheses if not h.get("coherent")]

        lines = [f"Document {doc_id} — Open-domain investigation"]

        if claims:
            lines.append(f"  Claims identified: {len(claims)}")
        if coherent_hyps:
            lines.append(
                f"  Coherent hypotheses: {len(coherent_hyps)} "
                f"({', '.join(h['id'] for h in coherent_hyps)})"
            )
        if incoherent_hyps:
            lines.append(
                f"  Incoherent hypotheses: {len(incoherent_hyps)} "
                f"({', '.join(h['id'] for h in incoherent_hyps)})"
            )

        if attributions:
            supported = [a for a in attributions if a.coherent]
            undermined = [a for a in attributions if not a.coherent]
            if supported:
                lines.append(f"  Supported attributions: {len(supported)}")
            if undermined:
                lines.append(f"  Undermined attributions: {len(undermined)}")

        # Attribution narrative
        if coherent_hyps and incoherent_hyps:
            lines.append(
                f"  The author's argumentation holds under "
                f"{', '.join(h['id'] for h in coherent_hyps)} "
                f"but collapses under "
                f"{', '.join(h['id'] for h in incoherent_hyps)}."
            )

        return "\n".join(lines)
