"""Comparative fallacy detection benchmark (#84 Phase 4).

Compares three detection modes:
- Mode A (Free): LLM detects fallacies with zero taxonomy context
- Mode B (One-shot): LLM receives full taxonomy, picks freely
- Mode C (Constrained): Hierarchical taxonomy navigation with iterative deepening

Uses synthetic argument texts exhibiting specific taxonomy fallacies.
Measures: precision (exact PK match), family match, depth reached, justification quality.
"""

import asyncio
import csv
import json
import logging
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

logger = logging.getLogger("fallacy_benchmark")

# ============================================================
# Benchmark test cases: 10 fallacies across families and depths
# ============================================================

BENCHMARK_CASES = [
    # --- Easy (depth 3-4, common fallacies) ---
    {
        "id": "case_01",
        "expected_pk": "4",
        "expected_name": "Appel à l'ignorance",
        "expected_family": "Insuffisance",
        "expected_depth": 4,
        "difficulty": "easy",
        "text": (
            "Personne n'a jamais prouvé que les extraterrestres n'existent pas. "
            "Donc, ils existent forcément quelque part dans l'univers. "
            "L'absence de preuve n'est pas une preuve d'absence, comme on dit."
        ),
    },
    {
        "id": "case_02",
        "expected_pk": "71",
        "expected_name": "Argument d'autorité",
        "expected_family": "Insuffisance",
        "expected_depth": 3,
        "difficulty": "easy",
        "text": (
            "Le professeur Dupont, éminent physicien, affirme que ce régime alimentaire "
            "est le meilleur pour la santé. Si un scientifique de son calibre le dit, "
            "c'est forcément vrai. Il faut suivre ses conseils."
        ),
    },
    # --- Medium (depth 4-5, less common) ---
    {
        "id": "case_03",
        "expected_pk": "34",
        "expected_name": "Preuve anecdotique",
        "expected_family": "Insuffisance",
        "expected_depth": 4,
        "difficulty": "medium",
        "text": (
            "Mon voisin a guéri de son cancer grâce à des tisanes de camomille. "
            "Les traitements naturels sont donc plus efficaces que la chimiothérapie. "
            "Un seul cas suffit à prouver que la médecine conventionnelle est dépassée."
        ),
    },
    {
        "id": "case_04",
        "expected_pk": "96",
        "expected_name": "Sophisme naturaliste",
        "expected_family": "Insuffisance",
        "expected_depth": 3,
        "difficulty": "medium",
        "text": (
            "L'être humain a toujours mangé de la viande depuis la préhistoire. "
            "C'est donc naturel et bon pour la santé. Le végétarisme va contre "
            "notre nature profonde et ne peut être qu'une mode passagère."
        ),
    },
    {
        "id": "case_05",
        "expected_pk": "340",
        "expected_name": "Appel aux conséquences",
        "expected_family": "Influence",
        "expected_depth": 3,
        "difficulty": "medium",
        "text": (
            "Si nous autorisons le mariage homosexuel, bientôt les gens voudront "
            "épouser leurs animaux de compagnie. Il faut penser aux conséquences "
            "catastrophiques de cette décision sur la société tout entière."
        ),
    },
    # --- Hard (depth 4-5, specialized/obscure) ---
    {
        "id": "case_06",
        "expected_pk": "56",
        "expected_name": "Le marteau d'or",
        "expected_family": "Insuffisance",
        "expected_depth": 4,
        "difficulty": "hard",
        "text": (
            "La privatisation a résolu les problèmes du secteur des télécommunications. "
            "Il faut donc privatiser l'éducation, la santé et les transports. "
            "La même recette fonctionne pour tous les secteurs sans exception."
        ),
    },
    {
        "id": "case_07",
        "expected_pk": "134",
        "expected_name": "Sophisme ludique",
        "expected_family": "Insuffisance",
        "expected_depth": 3,
        "difficulty": "hard",
        "text": (
            "Gérer l'économie d'un pays, c'est comme gérer son budget familial. "
            "Si une famille ne peut pas dépenser plus qu'elle ne gagne, "
            "un gouvernement ne devrait pas non plus avoir de déficit budgétaire."
        ),
    },
    {
        "id": "case_08",
        "expected_pk": "62",
        "expected_name": "Rationalisation",
        "expected_family": "Insuffisance",
        "expected_depth": 4,
        "difficulty": "hard",
        "text": (
            "Si je n'ai pas été retenu pour ce poste, c'est certainement parce que "
            "le recruteur avait déjà son candidat en tête. De toute façon, "
            "l'entreprise n'était pas assez innovante pour moi."
        ),
    },
    # --- Very Hard (obscure, precise identification needed) ---
    {
        "id": "case_09",
        "expected_pk": "51",
        "expected_name": "Sophisme du psychologue",
        "expected_family": "Insuffisance",
        "expected_depth": 4,
        "difficulty": "very_hard",
        "text": (
            "Je trouve cette musique insupportable, donc elle est objectivement "
            "de mauvaise qualité. Tout le monde devrait reconnaître que ce genre "
            "musical n'a aucune valeur artistique, c'est une évidence."
        ),
    },
    {
        "id": "case_10",
        "expected_pk": "61",
        "expected_name": "Argument par le scénario",
        "expected_family": "Insuffisance",
        "expected_depth": 4,
        "difficulty": "very_hard",
        "text": (
            "Imaginez : vous achetez cette voiture, vous roulez sur une route de "
            "campagne au coucher du soleil, le vent dans les cheveux, libre et heureux. "
            "Cette voiture changera votre vie, c'est certain. Tout commence par ce choix."
        ),
    },
]


@dataclass
class DetectionResult:
    """Result from a single detection attempt."""

    case_id: str
    mode: str  # "free", "one_shot", "constrained"
    detected_name: str = ""
    detected_pk: str = ""
    detected_family: str = ""
    confidence: float = 0.0
    justification: str = ""
    exact_pk_match: bool = False
    family_match: bool = False
    name_similarity: float = 0.0  # 0-1 Jaccard similarity on name tokens
    depth_reached: int = 0
    duration_seconds: float = 0.0
    error: str = ""
    raw_response: str = ""


@dataclass
class BenchmarkReport:
    """Aggregate benchmark results."""

    results: List[DetectionResult] = field(default_factory=list)
    mode_scores: Dict[str, Dict[str, float]] = field(default_factory=dict)
    summary: str = ""

    def compute_scores(self):
        """Compute aggregate scores per mode."""
        for mode in ("free", "one_shot", "constrained"):
            mode_results = [r for r in self.results if r.mode == mode]
            if not mode_results:
                continue
            n = len(mode_results)
            self.mode_scores[mode] = {
                "exact_pk_accuracy": sum(r.exact_pk_match for r in mode_results) / n,
                "family_accuracy": sum(r.family_match for r in mode_results) / n,
                "avg_name_similarity": sum(r.name_similarity for r in mode_results) / n,
                "avg_depth_reached": sum(r.depth_reached for r in mode_results) / n,
                "avg_confidence": sum(r.confidence for r in mode_results) / n,
                "avg_duration": sum(r.duration_seconds for r in mode_results) / n,
                "error_rate": sum(1 for r in mode_results if r.error) / n,
            }


class FallacyBenchmarkRunner:
    """Run comparative fallacy detection benchmark."""

    def __init__(self, taxonomy_path: Optional[str] = None):
        self.taxonomy_path = taxonomy_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "argumentation_analysis",
            "data",
            "argumentum_fallacies_taxonomy.csv",
        )
        # Fix path if we're already inside argumentation_analysis
        if not os.path.isfile(self.taxonomy_path):
            self.taxonomy_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "data",
                "argumentum_fallacies_taxonomy.csv",
            )
        self.taxonomy_data = self._load_taxonomy()
        self.node_map = {str(n.get("PK", "")): n for n in self.taxonomy_data}

    def _load_taxonomy(self) -> list:
        """Load taxonomy from CSV."""
        if not os.path.isfile(self.taxonomy_path):
            logger.error(f"Taxonomy not found: {self.taxonomy_path}")
            return []
        with open(self.taxonomy_path, "r", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def _get_family_for_pk(self, pk: str) -> str:
        """Get the root family name for a given PK."""
        node = self.node_map.get(pk)
        if not node:
            return ""
        path = node.get("path", "")
        root_pk = path.split(".")[0] if "." in path else path
        root = self.node_map.get(root_pk)
        return root.get("text_fr", root.get("nom_vulgarisé", "")) if root else ""

    async def run_mode_a_free(self, text: str) -> Dict[str, Any]:
        """Mode A: Free LLM detection with zero taxonomy context."""
        from openai import AsyncOpenAI

        api_key = os.environ.get("OPENAI_API_KEY", "")
        base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        model_id = os.environ.get("OPENAI_CHAT_MODEL_ID", "gpt-5-mini")

        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        response = await client.chat.completions.create(
            model=model_id,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert in logical fallacies (sophismes). "
                        "Identify the single most specific fallacy in the given French text. "
                        "Respond with ONLY a JSON object:\n"
                        '{"fallacy_name_fr": "nom en français", '
                        '"fallacy_name_en": "English name", '
                        '"confidence": 0.0-1.0, '
                        '"justification": "brief explanation"}'
                    ),
                },
                {"role": "user", "content": text},
            ],
        )
        raw = response.choices[0].message.content or ""
        return self._parse_json(raw)

    async def run_mode_b_one_shot(self, text: str) -> Dict[str, Any]:
        """Mode B: One-shot with full taxonomy available."""
        from openai import AsyncOpenAI

        api_key = os.environ.get("OPENAI_API_KEY", "")
        base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        model_id = os.environ.get("OPENAI_CHAT_MODEL_ID", "gpt-5-mini")

        # Build compact taxonomy reference
        taxonomy_ref = []
        for node in self.taxonomy_data:
            pk = node.get("PK", "")
            name = node.get("text_fr", node.get("nom_vulgarisé", ""))
            depth = node.get("depth", "")
            path = node.get("path", "")
            if name and pk:
                taxonomy_ref.append(f"PK={pk} depth={depth} path={path}: {name}")
        taxonomy_text = "\n".join(taxonomy_ref)

        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        response = await client.chat.completions.create(
            model=model_id,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert in logical fallacies. "
                        "Below is a complete taxonomy of fallacies with their PK identifiers. "
                        "Identify the MOST SPECIFIC fallacy from this taxonomy that matches "
                        "the given French text. Choose the deepest (most specialized) node. "
                        "Respond with ONLY a JSON object:\n"
                        '{"taxonomy_pk": "the PK number", '
                        '"fallacy_name_fr": "exact name from taxonomy", '
                        '"confidence": 0.0-1.0, '
                        '"justification": "brief explanation"}\n\n'
                        f"--- TAXONOMY ({len(self.taxonomy_data)} nodes) ---\n"
                        f"{taxonomy_text}"
                    ),
                },
                {"role": "user", "content": text},
            ],
        )
        raw = response.choices[0].message.content or ""
        return self._parse_json(raw)

    async def run_mode_c_constrained(self, text: str) -> Dict[str, Any]:
        """Mode C: Constrained hierarchical navigation via FallacyWorkflowPlugin."""
        from openai import AsyncOpenAI
        from semantic_kernel.kernel import Kernel
        from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
        from argumentation_analysis.plugins.fallacy_workflow_plugin import (
            FallacyWorkflowPlugin,
        )

        api_key = os.environ.get("OPENAI_API_KEY", "")
        base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        model_id = os.environ.get("OPENAI_CHAT_MODEL_ID", "gpt-5-mini")

        async_client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        llm_service = OpenAIChatCompletion(
            ai_model_id=model_id, async_client=async_client
        )
        kernel = Kernel()
        kernel.add_service(llm_service)

        plugin = FallacyWorkflowPlugin(
            master_kernel=kernel,
            llm_service=llm_service,
            taxonomy_data=self.taxonomy_data,
        )

        result_json = await plugin.run_guided_analysis(argument_text=text)
        result = json.loads(result_json)

        # Extract best fallacy from result
        fallacies = result.get("fallacies", [])
        if fallacies:
            best = fallacies[0]
            return {
                "taxonomy_pk": best.get("taxonomy_pk", ""),
                "fallacy_name_fr": best.get("fallacy_type", ""),
                "confidence": best.get("confidence", 0.0),
                "justification": best.get("explanation", ""),
                "navigation_trace": best.get("navigation_trace", []),
                "exploration_method": result.get("exploration_method", ""),
            }
        return {
            "error": "No fallacy detected",
            "exploration_method": result.get("exploration_method", ""),
        }

    def _parse_json(self, raw: str) -> Dict[str, Any]:
        """Parse JSON from LLM response."""
        text = raw.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
        return {"raw": raw, "error": "Failed to parse JSON"}

    @staticmethod
    def _name_similarity(expected: str, detected: str) -> float:
        """Compute Jaccard similarity on lowered word tokens."""
        if not expected or not detected:
            return 0.0
        a = set(expected.lower().split())
        b = set(detected.lower().split())
        intersection = a & b
        union = a | b
        return len(intersection) / len(union) if union else 0.0

    def _score_result(
        self, case: dict, mode: str, result: Dict[str, Any], duration: float
    ) -> DetectionResult:
        """Score a detection result against the expected answer."""
        detected_pk = str(result.get("taxonomy_pk", ""))
        detected_name = result.get("fallacy_name_fr", "")
        confidence = float(result.get("confidence", 0.0))
        justification = result.get("justification", "")

        # Check exact PK match
        exact_match = detected_pk == case["expected_pk"]

        # Check family match
        detected_family = self._get_family_for_pk(detected_pk) if detected_pk else ""
        if not detected_family and detected_name:
            # Try fuzzy family match from name
            detected_family = detected_name  # fallback
        family_match = (
            detected_family.lower() == case["expected_family"].lower()
            if detected_family
            else False
        )

        # Name similarity (Jaccard on word tokens)
        name_sim = self._name_similarity(case["expected_name"], detected_name)

        # Determine depth reached
        detected_node = self.node_map.get(detected_pk)
        depth_reached = int(detected_node.get("depth", 0)) if detected_node else 0

        return DetectionResult(
            case_id=case["id"],
            mode=mode,
            detected_name=detected_name,
            detected_pk=detected_pk,
            detected_family=detected_family,
            confidence=confidence,
            justification=justification[:200],
            exact_pk_match=exact_match,
            family_match=family_match,
            name_similarity=name_sim,
            depth_reached=depth_reached,
            duration_seconds=duration,
            error=result.get("error", ""),
            raw_response=str(result)[:500],
        )

    async def _run_single(
        self,
        case: dict,
        mode: str,
        runner,
        semaphore: asyncio.Semaphore,
    ) -> DetectionResult:
        """Run a single case+mode with concurrency control."""
        async with semaphore:
            logger.info(
                f"Running {case['id']} mode={mode} "
                f"(expected: {case['expected_name']})"
            )
            start = time.time()
            try:
                result = await runner(case["text"])
            except Exception as e:
                result = {"error": str(e)}
                logger.warning(f"  {mode} failed: {e}")
            duration = time.time() - start

            detection = self._score_result(case, mode, result, duration)
            logger.info(
                f"  {mode}: pk={detection.detected_pk} "
                f"exact={detection.exact_pk_match} "
                f"family={detection.family_match} "
                f"conf={detection.confidence:.2f} "
                f"({duration:.1f}s)"
            )
            return detection

    async def run_benchmark(
        self,
        cases: Optional[List[dict]] = None,
        modes: Optional[List[str]] = None,
        concurrency: int = 1,
    ) -> BenchmarkReport:
        """Run the full comparative benchmark.

        Args:
            cases: Test cases (default: BENCHMARK_CASES)
            modes: Detection modes (default: all three)
            concurrency: Max parallel LLM tasks (1=sequential, 3+ for parallel)
        """
        cases = cases or BENCHMARK_CASES
        modes = modes or ["free", "one_shot", "constrained"]
        report = BenchmarkReport()

        mode_runners = {
            "free": self.run_mode_a_free,
            "one_shot": self.run_mode_b_one_shot,
            "constrained": self.run_mode_c_constrained,
        }

        semaphore = asyncio.Semaphore(concurrency)

        if concurrency > 1:
            # Parallel execution
            tasks = []
            for case in cases:
                for mode in modes:
                    runner = mode_runners[mode]
                    tasks.append(self._run_single(case, mode, runner, semaphore))
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, Exception):
                    logger.error(f"Task failed: {r}")
                elif isinstance(r, DetectionResult):
                    report.results.append(r)
        else:
            # Sequential execution (original behavior)
            for case in cases:
                for mode in modes:
                    runner = mode_runners[mode]
                    detection = await self._run_single(case, mode, runner, semaphore)
                    report.results.append(detection)

        report.compute_scores()

        # Build summary
        lines = ["# Fallacy Detection Benchmark Results\n"]
        for mode, scores in report.mode_scores.items():
            lines.append(f"## Mode: {mode}")
            lines.append(f"  Exact PK accuracy: {scores['exact_pk_accuracy']:.1%}")
            lines.append(f"  Family accuracy:   {scores['family_accuracy']:.1%}")
            lines.append(f"  Name similarity:   {scores['avg_name_similarity']:.2f}")
            lines.append(f"  Avg depth reached: {scores['avg_depth_reached']:.1f}")
            lines.append(f"  Avg confidence:    {scores['avg_confidence']:.2f}")
            lines.append(f"  Avg duration:      {scores['avg_duration']:.1f}s")
            lines.append(f"  Error rate:        {scores['error_rate']:.1%}")
            lines.append("")
        report.summary = "\n".join(lines)

        return report

    def save_report(self, report: BenchmarkReport, path: str):
        """Save benchmark report to JSON."""
        data = {
            "results": [asdict(r) for r in report.results],
            "mode_scores": report.mode_scores,
            "summary": report.summary,
            "case_count": len(BENCHMARK_CASES),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Report saved to {path}")
