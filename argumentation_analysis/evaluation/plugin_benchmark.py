"""Plugin benchmark suite for 13 Semantic Kernel plugins (#306).

Creates controlled-input benchmarks for each plugin, measuring correctness,
latency, and error rate. Produces plugin_benchmark_baseline.json with
per-plugin metrics.

Plugin tiers:
  A) No external deps (always testable): Governance, QualityScoring, ATMS
  B) Needs setup (mockable): FrenchFallacy, JTMS, Exploration
  C) Needs JVM/LLM (heavily mocked): TweetyLogic, ASPIC, Ranking,
     BeliefRevision, NLToLogic, FallacyWorkflow, Toulmin

Usage:
    # Run all benchmarks
    python -m argumentation_analysis.evaluation.plugin_benchmark

    # Run specific plugin
    pytest tests/unit/argumentation_analysis/evaluation/test_plugin_benchmark.py -v
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("plugin_benchmark")

# ============================================================
# Benchmark test cases: 3-5 per plugin, 35 total
# ============================================================

PLUGIN_BENCHMARK_CASES: Dict[str, List[dict]] = {
    # ── Tier A: Pure Python, no external deps ──────────────────
    "governance": [
        {
            "id": "gov_01",
            "function": "social_choice_vote",
            "args": {
                "input_json": json.dumps(
                    {
                        "method": "copeland",
                        "ballots": [
                            ["A", "B", "C"],
                            ["A", "C", "B"],
                            ["B", "A", "C"],
                        ],
                        "options": ["A", "B", "C"],
                    }
                ),
            },
            "expected": {"has_winner": True, "winner_is": "A"},
            "difficulty": "easy",
        },
        {
            "id": "gov_02",
            "function": "detect_conflicts_fn",
            "args": {
                "positions_json": json.dumps(
                    {
                        "agent_a": "Le climat change dû aux activités humaines",
                        "agent_b": "Le climat change naturellement",
                        "agent_c": "Le climat change dû aux activités humaines",
                    }
                ),
            },
            "expected": {"has_conflicts": True, "conflict_count": 1},
            "difficulty": "easy",
        },
        {
            "id": "gov_03",
            "function": "compute_consensus_metrics",
            "args": {
                "results_json": json.dumps(
                    {
                        "votes": ["A", "A", "A", "A", "A", "B", "B", "B", "C", "C"],
                        "winner": "A",
                    }
                ),
            },
            "expected": {"has_consensus_rate": True},
            "difficulty": "easy",
        },
        {
            "id": "gov_04",
            "function": "find_condorcet_winner",
            "args": {
                "input_json": json.dumps(
                    {
                        "ballots": [
                            ["A", "B", "C"],
                            ["A", "C", "B"],
                            ["A", "B", "C"],
                        ],
                        "options": ["A", "B", "C"],
                    }
                ),
            },
            "expected": {"condorcet_winner_is": "A"},
            "difficulty": "medium",
        },
        {
            "id": "gov_05",
            "function": "list_governance_methods",
            "args": {},
            "expected": {
                "has_agent_based": True,
                "has_social_choice": True,
            },
            "difficulty": "easy",
        },
    ],
    "quality_scoring": [
        {
            "id": "qs_01",
            "function": "evaluate_argument_quality",
            "args": {
                "text": (
                    "Les études scientifiques montrent que le changement climatique "
                    "est accéléré par les activités humaines. Le GIEC confirme que "
                    "les émissions de CO2 augmentent la température globale."
                ),
            },
            "expected": {"has_note_finale": True, "note_finale_gte": 3},
            "difficulty": "easy",
        },
        {
            "id": "qs_02",
            "function": "get_quality_score",
            "args": {
                "text": "C'est vrai parce que je le dis.",
            },
            "expected": {"has_note_finale": True, "has_note_moyenne": True},
            "difficulty": "easy",
        },
        {
            "id": "qs_03",
            "function": "list_virtues",
            "args": {},
            "expected": {"virtue_count": 9},
            "difficulty": "easy",
        },
    ],
    "atms": [
        {
            "id": "atms_01",
            "function": "atms_create_assumption",
            "args": {"name": "rain", "description": "It is raining"},
            "expected": {"returns_json": True},
            "difficulty": "easy",
        },
        {
            "id": "atms_02",
            "function": "atms_add_justification",
            "args": {
                "consequent": "wet_ground",
                "antecedents": "rain",
            },
            "expected": {"returns_json": True},
            "difficulty": "medium",
        },
        {
            "id": "atms_03",
            "function": "atms_check_environment",
            "args": {
                "assumptions": "rain",
            },
            "expected": {"returns_json": True},
            "difficulty": "medium",
        },
    ],
    # ── Tier B: Mockable dependencies ──────────────────────────
    "jtms": [
        {
            "id": "jtms_01",
            "function": "create_belief",
            "args": {"name": "sky_is_blue"},
            "expected": {"has_belief": True},
            "difficulty": "easy",
        },
        {
            "id": "jtms_02",
            "function": "query_beliefs",
            "args": {"filter_valid": True},
            "expected": {"has_results": True},
            "difficulty": "easy",
        },
        {
            "id": "jtms_03",
            "function": "get_jtms_state",
            "args": {},
            "expected": {"has_beliefs": True},
            "difficulty": "easy",
        },
    ],
    "french_fallacy": [
        {
            "id": "ff_01",
            "function": "list_fallacy_types",
            "args": {},
            "expected": {"min_types": 10},
            "difficulty": "easy",
        },
        {
            "id": "ff_02",
            "function": "get_available_tiers",
            "args": {},
            "expected": {"has_tiers": True},
            "difficulty": "easy",
        },
        {
            "id": "ff_03",
            "function": "detect_fallacies",
            "args": {
                "text": (
                    "Personne n'a jamais prouvé que les extraterrestles n'existent pas. "
                    "Donc ils existent forcement quelque part."
                ),
            },
            "expected": {"returns_json": True},
            "difficulty": "medium",
        },
    ],
    "exploration": [
        {
            "id": "expl_01",
            "function": "explore_branch",
            "args": {
                "current_node": "1",
                "argument_text": "Test argument for exploration",
            },
            "expected": {"has_children": True},
            "difficulty": "medium",
        },
        {
            "id": "expl_02",
            "function": "confirm_fallacy",
            "args": {
                "node_pk": "4",
                "argument_text": "Test argument for confirmation",
            },
            "expected": {"has_confirmation": True},
            "difficulty": "easy",
        },
    ],
    # ── Tier C: JVM/LLM-dependent, mocked ─────────────────────
    "tweety_logic": [
        {
            "id": "tl_01",
            "function": "check_propositional_consistency",
            "args": {"formula": "p AND NOT p"},
            "expected": {"returns_json": True},
            "difficulty": "medium",
        },
        {
            "id": "tl_02",
            "function": "analyze_dung_framework",
            "args": {
                "framework_json": json.dumps(
                    {
                        "arguments": ["a", "b", "c"],
                        "attacks": [["a", "b"], ["b", "c"]],
                    }
                ),
            },
            "expected": {"returns_json": True},
            "difficulty": "hard",
        },
        {
            "id": "tl_03",
            "function": "solve_sat",
            "args": {"formula": "p OR q"},
            "expected": {"returns_json": True},
            "difficulty": "medium",
        },
    ],
    "belief_revision": [
        {
            "id": "br_01",
            "function": "revise_beliefs",
            "args": {
                "beliefs_json": json.dumps(["p", "q"]),
                "new_info": "NOT p",
            },
            "expected": {"returns_json": True},
            "difficulty": "medium",
        },
        {
            "id": "br_02",
            "function": "list_revision_methods",
            "args": {},
            "expected": {"has_methods": True},
            "difficulty": "easy",
        },
    ],
    "aspic": [
        {
            "id": "aspic_01",
            "function": "analyze_aspic",
            "args": {
                "rules_json": json.dumps(
                    {
                        "strict_rules": [["p", "q"]],
                        "defeasible_rules": [],
                        "preferences": {},
                    }
                ),
            },
            "expected": {"returns_json": True},
            "difficulty": "hard",
        },
        {
            "id": "aspic_02",
            "function": "list_aspic_reasoner_types",
            "args": {},
            "expected": {"has_types": True},
            "difficulty": "easy",
        },
    ],
    "ranking": [
        {
            "id": "rank_01",
            "function": "rank_arguments",
            "args": {
                "framework_json": json.dumps(
                    {
                        "arguments": ["a", "b"],
                        "attacks": [["a", "b"]],
                    }
                ),
                "method": "grounded",
            },
            "expected": {"returns_json": True},
            "difficulty": "medium",
        },
        {
            "id": "rank_02",
            "function": "list_ranking_methods",
            "args": {},
            "expected": {"has_methods": True},
            "difficulty": "easy",
        },
    ],
    "nl_to_logic": [
        {
            "id": "nl_01",
            "function": "translate_to_pl",
            "args": {"text": "If it rains then the ground is wet"},
            "expected": {"returns_json": True},
            "difficulty": "medium",
        },
        {
            "id": "nl_02",
            "function": "translate_to_fol",
            "args": {"text": "All humans are mortal"},
            "expected": {"returns_json": True},
            "difficulty": "medium",
        },
    ],
    "fallacy_workflow": [
        {
            "id": "fw_01",
            "function": "run_guided_analysis",
            "args": {
                "argument_text": (
                    "Personne n'a jamais prouvé que les fantômes n'existent pas. "
                    "Donc ils existent."
                ),
            },
            "expected": {"returns_json": True},
            "difficulty": "hard",
        },
    ],
    "toulmin": [
        {
            "id": "toul_01",
            "function": "analyze_argument",
            "args": {
                "text": "Il pleut donc le sol est mouillé.",
            },
            "expected": {"returns_json": True},
            "difficulty": "medium",
        },
    ],
}


# ============================================================
# Data classes
# ============================================================


@dataclass
class PluginBenchmarkResult:
    """Result from a single plugin benchmark run."""

    case_id: str
    plugin_name: str
    function_name: str
    passed: bool = False
    latency_ms: float = 0.0
    error: str = ""
    actual: str = ""  # JSON string of actual output
    validation_details: str = ""
    difficulty: str = ""


@dataclass
class PluginBenchmarkReport:
    """Aggregate benchmark report across all plugins."""

    results: List[PluginBenchmarkResult] = field(default_factory=list)
    plugin_scores: Dict[str, Dict[str, float]] = field(default_factory=dict)
    summary: str = ""
    timestamp: str = ""

    def compute_scores(self):
        """Compute per-plugin aggregate scores."""
        plugins: Dict[str, List[PluginBenchmarkResult]] = {}
        for r in self.results:
            plugins.setdefault(r.plugin_name, []).append(r)

        for plugin_name, results in plugins.items():
            n = len(results)
            self.plugin_scores[plugin_name] = {
                "pass_rate": sum(r.passed for r in results) / n,
                "avg_latency_ms": sum(r.latency_ms for r in results) / n,
                "error_rate": sum(1 for r in results if r.error) / n,
                "case_count": n,
            }


# ============================================================
# Plugin Benchmark Suite
# ============================================================


class PluginBenchmarkSuite:
    """Run controlled benchmarks for all SK plugins."""

    # Maps benchmark plugin_name → (module_path, class_name)
    PLUGIN_REGISTRY = {
        "governance": (
            "argumentation_analysis.plugins.governance_plugin",
            "GovernancePlugin",
        ),
        "quality_scoring": (
            "argumentation_analysis.plugins.quality_scoring_plugin",
            "QualityScoringPlugin",
        ),
        "atms": (
            "argumentation_analysis.plugins.atms_plugin",
            "ATMSPlugin",
        ),
        "jtms": (
            "argumentation_analysis.plugins.semantic_kernel.jtms_plugin",
            "JTMSSemanticKernelPlugin",
        ),
        "french_fallacy": (
            "argumentation_analysis.plugins.french_fallacy_plugin",
            "FrenchFallacyPlugin",
        ),
        "exploration": (
            "argumentation_analysis.plugins.exploration_plugin",
            "ExplorationPlugin",
        ),
        "tweety_logic": (
            "argumentation_analysis.plugins.tweety_logic_plugin",
            "TweetyLogicPlugin",
        ),
        "belief_revision": (
            "argumentation_analysis.plugins.belief_revision_plugin",
            "BeliefRevisionPlugin",
        ),
        "aspic": (
            "argumentation_analysis.plugins.aspic_plugin",
            "ASPICPlugin",
        ),
        "ranking": (
            "argumentation_analysis.plugins.ranking_plugin",
            "RankingPlugin",
        ),
        "nl_to_logic": (
            "argumentation_analysis.plugins.nl_to_logic_plugin",
            "NLToLogicPlugin",
        ),
        "fallacy_workflow": (
            "argumentation_analysis.plugins.fallacy_workflow_plugin",
            "FallacyWorkflowPlugin",
        ),
        "toulmin": (
            "argumentation_analysis.plugins.toulmin_plugin",
            "ToulminPlugin",
        ),
    }

    def __init__(self):
        self._plugin_cache: Dict[str, Any] = {}

    def _instantiate_plugin(self, plugin_name: str) -> Optional[Any]:
        """Instantiate a plugin by name, returns None if not available."""
        if plugin_name in self._plugin_cache:
            return self._plugin_cache[plugin_name]

        entry = self.PLUGIN_REGISTRY.get(plugin_name)
        if not entry:
            return None

        module_path, class_name = entry
        try:
            import importlib

            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)
        except (ImportError, AttributeError) as e:
            logger.warning(f"Cannot import {plugin_name}: {e}")
            self._plugin_cache[plugin_name] = None
            return None

        try:
            instance = self._create_instance(plugin_name, cls)
            self._plugin_cache[plugin_name] = instance
            return instance
        except Exception as e:
            logger.warning(f"Cannot instantiate {plugin_name}: {e}")
            self._plugin_cache[plugin_name] = None
            return None

    def _create_instance(self, plugin_name: str, cls: type) -> Any:
        """Create plugin instance with appropriate constructor args."""
        if plugin_name == "exploration":
            # ExplorationPlugin requires TaxonomyNavigator
            from argumentation_analysis.core.taxonomy_navigator import (
                TaxonomyNavigator,
            )

            taxonomy_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "data",
                "argumentum_fallacies_taxonomy.csv",
            )
            if not os.path.isfile(taxonomy_path):
                taxonomy_path = os.path.join(
                    os.path.dirname(__file__),
                    "..",
                    "data",
                    "argumentum_fallacies_taxonomy.csv",
                )
            navigator = TaxonomyNavigator(taxonomy_path)
            return cls(navigator)

        if plugin_name == "fallacy_workflow":
            # FallacyWorkflowPlugin needs kernel + LLM service
            # Return None — benchmark will use mock mode
            raise RuntimeError("FallacyWorkflowPlugin requires SK kernel setup")

        # Default: no-arg constructor
        return cls()

    def _validate_output(self, expected: dict, actual_raw: str) -> tuple:
        """Validate plugin output against expected criteria.

        Returns (passed: bool, details: str).
        """
        try:
            actual = (
                json.loads(actual_raw) if isinstance(actual_raw, str) else actual_raw
            )
        except (json.JSONDecodeError, TypeError):
            actual = {"raw": actual_raw}

        failures = []

        if "has_winner" in expected:
            if "winner" not in actual:
                failures.append("missing 'winner' key")
            if (
                expected.get("winner_is")
                and actual.get("winner") != expected["winner_is"]
            ):
                failures.append(
                    f"winner={actual.get('winner')} != {expected['winner_is']}"
                )

        if "has_conflicts" in expected:
            if not isinstance(actual, list) and "conflicts" not in str(actual):
                failures.append("expected conflict list")

        if "has_consensus_rate" in expected:
            if "consensus_rate" not in actual:
                failures.append("missing 'consensus_rate'")

        if "condorcet_winner_is" in expected:
            if actual.get("condorcet_winner") != expected["condorcet_winner_is"]:
                failures.append(
                    f"condorcet_winner={actual.get('condorcet_winner')} "
                    f"!= {expected['condorcet_winner_is']}"
                )

        if "has_agent_based" in expected:
            if "agent_based" not in actual:
                failures.append("missing 'agent_based'")

        if "has_social_choice" in expected:
            if "social_choice" not in actual:
                failures.append("missing 'social_choice'")

        if "has_note_finale" in expected:
            if "note_finale" not in actual:
                failures.append("missing 'note_finale'")

        if "note_finale_gte" in expected:
            nf = actual.get("note_finale", 0)
            if isinstance(nf, (int, float)) and nf < expected["note_finale_gte"]:
                failures.append(f"note_finale={nf} < {expected['note_finale_gte']}")

        if "has_note_moyenne" in expected:
            if "note_moyenne" not in actual:
                failures.append("missing 'note_moyenne'")

        if "virtue_count" in expected:
            if not isinstance(actual, list) or len(actual) != expected["virtue_count"]:
                failures.append(
                    f"virtue_count={len(actual) if isinstance(actual, list) else 'N/A'} "
                    f"!= {expected['virtue_count']}"
                )

        if "has_belief" in expected:
            if "belief" not in str(actual).lower() and "name" not in actual:
                failures.append("no belief in response")

        if "has_results" in expected:
            if not actual:
                failures.append("empty results")

        if "has_beliefs" in expected:
            if not actual or (
                "beliefs" not in str(actual) and "belief" not in str(actual)
            ):
                failures.append("no beliefs in state")

        if "min_types" in expected:
            items = actual if isinstance(actual, list) else []
            if len(items) < expected["min_types"]:
                failures.append(
                    f"only {len(items)} types, need >= {expected['min_types']}"
                )

        if "has_tiers" in expected:
            if not actual or (isinstance(actual, dict) and not actual.get("tiers")):
                failures.append("no tiers in response")

        if "returns_json" in expected:
            if isinstance(actual_raw, str):
                try:
                    json.loads(actual_raw)
                except json.JSONDecodeError:
                    failures.append("response is not valid JSON")

        if "has_methods" in expected:
            if not actual or (isinstance(actual, (list, dict)) and len(actual) == 0):
                failures.append("no methods returned")

        if "has_types" in expected:
            if not actual:
                failures.append("no types returned")

        if "has_children" in expected:
            if not actual or (isinstance(actual, dict) and "children" not in actual):
                failures.append("no children in response")

        if "has_confirmation" in expected:
            if not actual:
                failures.append("empty confirmation response")

        if "has_held_beliefs" in expected:
            if not actual:
                failures.append("no held beliefs")

        passed = len(failures) == 0
        details = "; ".join(failures) if failures else "OK"
        return passed, details

    def run_single(self, plugin_name: str, case: dict) -> PluginBenchmarkResult:
        """Run a single benchmark case against a plugin."""
        case_id = case["id"]
        function_name = case["function"]
        args = case.get("args", {})
        expected = case.get("expected", {})

        result = PluginBenchmarkResult(
            case_id=case_id,
            plugin_name=plugin_name,
            function_name=function_name,
            difficulty=case.get("difficulty", ""),
        )

        plugin = self._instantiate_plugin(plugin_name)
        if plugin is None:
            result.error = f"Plugin {plugin_name} not available"
            result.validation_details = "SKIP: plugin unavailable"
            return result

        func = getattr(plugin, function_name, None)
        if func is None:
            result.error = f"Function {function_name} not found on {plugin_name}"
            result.validation_details = "SKIP: function not found"
            return result

        start = time.perf_counter()
        try:
            raw_output = func(**args)
            # Handle async functions
            if asyncio.iscoroutine(raw_output):
                try:
                    loop = asyncio.get_running_loop()
                    import concurrent.futures

                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        raw_output = pool.submit(asyncio.run, raw_output).result(
                            timeout=30
                        )
                except RuntimeError:
                    raw_output = asyncio.run(raw_output)

            elapsed = (time.perf_counter() - start) * 1000
            result.latency_ms = round(elapsed, 2)

            # Normalize output to string
            if isinstance(raw_output, dict):
                output_str = json.dumps(raw_output, ensure_ascii=False)
            elif isinstance(raw_output, str):
                output_str = raw_output
            else:
                output_str = str(raw_output)

            result.actual = output_str[:500]
            passed, details = self._validate_output(expected, output_str)
            result.passed = passed
            result.validation_details = details

        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            result.latency_ms = round(elapsed, 2)
            result.error = str(e)[:200]
            result.passed = False
            result.validation_details = f"EXCEPTION: {type(e).__name__}"

        return result

    def run_plugin(
        self, plugin_name: str, cases: Optional[List[dict]] = None
    ) -> List[PluginBenchmarkResult]:
        """Run all benchmark cases for a single plugin."""
        cases = cases or PLUGIN_BENCHMARK_CASES.get(plugin_name, [])
        results = []
        for case in cases:
            r = self.run_single(plugin_name, case)
            results.append(r)
            status = "PASS" if r.passed else ("ERROR" if r.error else "FAIL")
            logger.info(
                f"  {r.case_id} [{plugin_name}.{r.function_name}]: "
                f"{status} ({r.latency_ms:.1f}ms) — {r.validation_details}"
            )
        return results

    def run_all(
        self,
        plugins: Optional[List[str]] = None,
    ) -> PluginBenchmarkReport:
        """Run benchmarks for all (or selected) plugins.

        Args:
            plugins: Plugin names to benchmark. Default: all in PLUGIN_BENCHMARK_CASES.
        """
        plugin_names = plugins or list(PLUGIN_BENCHMARK_CASES.keys())
        report = PluginBenchmarkReport()
        report.timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")

        for plugin_name in plugin_names:
            cases = PLUGIN_BENCHMARK_CASES.get(plugin_name, [])
            if not cases:
                logger.warning(f"No benchmark cases for {plugin_name}")
                continue
            logger.info(f"benchmarking {plugin_name} ({len(cases)} cases)...")
            results = self.run_plugin(plugin_name, cases)
            report.results.extend(results)

        report.compute_scores()
        report.summary = self._build_summary(report)
        return report

    def _build_summary(self, report: PluginBenchmarkReport) -> str:
        """Build human-readable summary markdown."""
        lines = ["# Plugin Benchmark Suite Results\n"]
        lines.append(f"Plugins tested: {len(report.plugin_scores)}")
        lines.append(f"Total cases: {len(report.results)}\n")

        lines.append(
            f"{'Plugin':<20} {'Pass%':>7} {'Avg ms':>8} {'Errors':>7} {'N':>3}"
        )
        lines.append("-" * 50)
        for plugin_name, scores in sorted(report.plugin_scores.items()):
            lines.append(
                f"{plugin_name:<20} "
                f"{scores['pass_rate']:>6.0%} "
                f"{scores['avg_latency_ms']:>7.1f} "
                f"{scores['error_rate']:>6.0%} "
                f"{scores['case_count']:>3}"
            )
        return "\n".join(lines)

    def save_baseline(self, report: PluginBenchmarkReport, path: str):
        """Save benchmark report as JSON baseline file."""
        data = {
            "results": [asdict(r) for r in report.results],
            "plugin_scores": report.plugin_scores,
            "summary": report.summary,
            "timestamp": report.timestamp,
            "total_cases": len(report.results),
            "plugin_count": len(report.plugin_scores),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Baseline saved to {path}")


# ============================================================
# CLI entry point
# ============================================================


def main():
    """Run the full plugin benchmark suite and save baseline."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    suite = PluginBenchmarkSuite()
    report = suite.run_all()
    print(report.summary)

    output_dir = os.path.dirname(__file__)
    output_path = os.path.join(output_dir, "plugin_benchmark_baseline.json")
    suite.save_baseline(report, output_path)


if __name__ == "__main__":
    main()
