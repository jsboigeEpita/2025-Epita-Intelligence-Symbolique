"""
Tests d'intégration pour run_einstein_oracle_demo.py avec GPT-4o-mini réel.

Tests couvrant:
- Test complet run_einstein_oracle_demo.py avec GPT-4o-mini
- Validation indices progressifs Moriarty
- Test résolution puzzle Einstein par Sherlock/Watson
"""

import pytest
import asyncio
import os
import time
import sys
import subprocess
import json
from pathlib import Path
from unittest.mock import patch, Mock
from typing import Dict, Any, List

# Configuration pour tests réels GPT-4o-mini
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
REAL_GPT_AVAILABLE = OPENAI_API_KEY is not None and len(OPENAI_API_KEY) > 10

# Chemins des scripts
PROJECT_ROOT = Path(__file__).parent.parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts" / "sherlock_watson"
EINSTEIN_DEMO_SCRIPT = SCRIPTS_DIR / "run_einstein_oracle_demo.py"

# Skip si pas d'API key ou script manquant
pytestmark = pytest.mark.skipif(
    not REAL_GPT_AVAILABLE or not EINSTEIN_DEMO_SCRIPT.exists(),
    reason="Tests nécessitent OPENAI_API_KEY et run_einstein_oracle_demo.py",
)


@pytest.fixture
def einstein_test_environment():
    """Configuration d'environnement pour tests Einstein."""
    env = os.environ.copy()
    env["OPENAI_API_KEY"] = OPENAI_API_KEY
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    env["PUZZLE_MODE"] = "einstein"
    env["TEST_MODE"] = "true"
    env["PROGRESSIVE_HINTS"] = "true"
    return env


@pytest.fixture
def einstein_puzzle_config():
    """Configuration du puzzle Einstein pour tests."""
    return {
        "houses": 5,
        "attributes": ["nationality", "color", "pet", "drink", "cigarette"],
        "constraints": [
            "L'Anglais vit dans la maison rouge",
            "Le Suédois a un chien",
            "Le Danois boit du thé",
            "La maison verte est directement à gauche de la maison blanche",
            "Le propriétaire de la maison verte boit du café",
        ],
        "question": "Qui a le poisson ?",
    }


@pytest.fixture
def progressive_hints_monitor():
    """Moniteur pour les indices progressifs."""
    hints_data = {
        "hints_given": [],
        "complexity_levels": [],
        "hint_timing": [],
        "effectiveness_scores": [],
    }

    def record_hint(hint_content, complexity_level, timestamp=None):
        if timestamp is None:
            timestamp = time.time()

        hints_data["hints_given"].append(hint_content)
        hints_data["complexity_levels"].append(complexity_level)
        hints_data["hint_timing"].append(timestamp)

        # Score d'efficacité basé sur la longueur et les mots-clés
        effectiveness = len(hint_content) / 100  # Base sur longueur
        if any(
            word in hint_content.lower()
            for word in ["maison", "couleur", "animal", "boisson"]
        ):
            effectiveness += 0.2
        hints_data["effectiveness_scores"].append(min(effectiveness, 1.0))

    def get_progression_analysis():
        if len(hints_data["complexity_levels"]) < 2:
            return {"progression": "insufficient_data"}

        # Analyse de la progression
        avg_complexity_first_half = sum(
            hints_data["complexity_levels"][: len(hints_data["complexity_levels"]) // 2]
        )
        avg_complexity_second_half = sum(
            hints_data["complexity_levels"][len(hints_data["complexity_levels"]) // 2 :]
        )

        return {
            "progression": (
                "increasing"
                if avg_complexity_second_half > avg_complexity_first_half
                else "stable"
            ),
            "total_hints": len(hints_data["hints_given"]),
            "avg_effectiveness": sum(hints_data["effectiveness_scores"])
            / len(hints_data["effectiveness_scores"]),
            "complexity_trend": hints_data["complexity_levels"],
        }

    monitor = type(
        "ProgressiveHintsMonitor",
        (),
        {
            "record_hint": record_hint,
            "get_analysis": get_progression_analysis,
            "data": hints_data,
        },
    )()

    return monitor


@pytest.mark.integration
@pytest.mark.llm_critical
@pytest.mark.slow
class TestEinsteinOracleDemoReal:
    """Tests d'intégration pour Einstein Oracle Demo réel."""

    def test_einstein_demo_script_exists(self):
        """Test que le script Einstein demo existe."""
        assert EINSTEIN_DEMO_SCRIPT.exists(), f"Script manquant: {EINSTEIN_DEMO_SCRIPT}"
        assert (
            EINSTEIN_DEMO_SCRIPT.is_file()
        ), f"N'est pas un fichier: {EINSTEIN_DEMO_SCRIPT}"

        # Vérifier le contenu Einstein spécifique
        content = EINSTEIN_DEMO_SCRIPT.read_text(encoding="utf-8")

        einstein_keywords = [
            "einstein",
            "puzzle",
            "maison",
            "progressive",
            "hint",
            "riddle",
        ]

        found_keywords = sum(
            1 for keyword in einstein_keywords if keyword in content.lower()
        )
        assert (
            found_keywords >= 3
        ), f"Pas assez de mots-clés Einstein: {found_keywords}/6"

    def test_einstein_demo_basic_execution(self, einstein_test_environment):
        """Test l'exécution de base du demo Einstein."""

        async def run_test():
            try:
                process = await asyncio.create_subprocess_exec(
                    sys.executable,
                    str(EINSTEIN_DEMO_SCRIPT),
                    "--test-mode",
                    "--max-hints",
                    "3",
                    "--puzzle-mode",
                    "simplified",
                    env=einstein_test_environment,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(), timeout=180.0  # 3 minutes pour Einstein
                    )
                except asyncio.TimeoutError:
                    process.kill()
                    pytest.fail("Demo Einstein timeout après 3 minutes")

                assert (
                    process.returncode == 0
                ), f"Demo Einstein échoué. STDERR: {stderr.decode()}"

                output = stdout.decode("utf-8")
                assert len(output) > 200, "Output Einstein trop court"

                # Vérifications spécifiques Einstein
                einstein_indicators = [
                    "einstein" in output.lower(),
                    "puzzle" in output.lower() or "énigme" in output.lower(),
                    "maison" in output.lower() or "house" in output.lower(),
                    "indice" in output.lower() or "hint" in output.lower(),
                    "moriarty" in output.lower(),
                ]

                assert (
                    sum(einstein_indicators) >= 3
                ), f"Pas assez d'indicateurs Einstein: {output[:500]}"

            except Exception as e:
                pytest.fail(f"Erreur exécution Einstein demo: {e}")

        asyncio.run(run_test())

    def test_progressive_hints_validation(
        self, einstein_test_environment, progressive_hints_monitor
    ):
        """Test la validation des indices progressifs."""

        async def run_test():
            env = einstein_test_environment.copy()
            env["PROGRESSIVE_HINTS"] = "true"
            env["HINT_COMPLEXITY_TRACKING"] = "true"

            try:
                process = await asyncio.create_subprocess_exec(
                    sys.executable,
                    str(EINSTEIN_DEMO_SCRIPT),
                    "--test-mode",
                    "--max-hints",
                    "5",
                    "--progressive-mode",
                    "--verbose",
                    env=env,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=240.0,  # 4 minutes pour indices progressifs
                )

                assert (
                    process.returncode == 0
                ), f"Progressive hints échoué: {stderr.decode()}"

                output = stdout.decode("utf-8")

                # Analyse des indices progressifs
                lines = output.split("\n")
                hints_found = []

                for line in lines:
                    if any(
                        word in line.lower()
                        for word in ["indice", "hint", "révèle", "clé"]
                    ):
                        hints_found.append(line.strip())

                        # Estimation du niveau de complexité
                        complexity = 1  # Base
                        if len(line) > 100:
                            complexity += 1
                        if any(
                            word in line.lower()
                            for word in ["déduction", "logique", "contrainte"]
                        ):
                            complexity += 1
                        if any(
                            word in line.lower()
                            for word in ["directement", "gauche", "droite", "voisin"]
                        ):
                            complexity += 1

                        progressive_hints_monitor.record_hint(line, complexity)

                # Vérifications de progression
                assert (
                    len(hints_found) >= 2
                ), f"Pas assez d'indices trouvés: {len(hints_found)}"

                analysis = progressive_hints_monitor.get_analysis()
                assert analysis["total_hints"] >= 2, "Pas assez d'indices enregistrés"
                assert (
                    analysis["avg_effectiveness"] > 0.3
                ), "Indices pas assez efficaces"

                # Vérifier la progression de complexité
                if len(analysis["complexity_trend"]) >= 3:
                    # Les derniers indices devraient être plus complexes
                    early_avg = sum(analysis["complexity_trend"][:2]) / 2
                    late_avg = sum(analysis["complexity_trend"][-2:]) / 2
                    assert late_avg >= early_avg, "Pas de progression de complexité"

            except asyncio.TimeoutError:
                pytest.fail("Timeout indices progressifs")
            except Exception as e:
                pytest.fail(f"Erreur indices progressifs: {e}")

        asyncio.run(run_test())

    def test_sherlock_watson_einstein_solving(self, einstein_test_environment):
        """Test la résolution du puzzle Einstein par Sherlock/Watson."""

        async def run_test():
            env = einstein_test_environment.copy()
            env["SOLVING_MODE"] = "collaborative"
            env["SHERLOCK_WATSON_FOCUS"] = "true"

            try:
                process = await asyncio.create_subprocess_exec(
                    sys.executable,
                    str(EINSTEIN_DEMO_SCRIPT),
                    "--test-mode",
                    "--solving-focus",
                    "--max-turns",
                    "8",
                    env=env,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=300.0  # 5 minutes pour résolution
                )

                assert (
                    process.returncode == 0
                ), f"Résolution Einstein échouée: {stderr.decode()}"

                output = stdout.decode("utf-8")

                # Vérifications de résolution collaborative
                sherlock_contributions = []
                watson_contributions = []

                lines = output.split("\n")
                for line in lines:
                    if "sherlock" in line.lower():
                        sherlock_contributions.append(line)
                    elif "watson" in line.lower():
                        watson_contributions.append(line)

                assert (
                    len(sherlock_contributions) >= 2
                ), "Pas assez de contributions Sherlock"
                assert (
                    len(watson_contributions) >= 2
                ), "Pas assez de contributions Watson"

                # Vérifier les tentatives de résolution
                solving_attempts = []
                for line in lines:
                    if any(
                        word in line.lower()
                        for word in ["solution", "réponse", "poisson", "résultat"]
                    ):
                        solving_attempts.append(line)

                assert (
                    len(solving_attempts) >= 1
                ), "Aucune tentative de résolution détectée"

                # Vérifier la qualité du raisonnement
                reasoning_quality = 0
                for line in lines:
                    if any(
                        word in line.lower()
                        for word in [
                            "déduction",
                            "logique",
                            "contrainte",
                            "élimination",
                        ]
                    ):
                        reasoning_quality += 1

                assert (
                    reasoning_quality >= 3
                ), f"Raisonnement insuffisant: {reasoning_quality}"

            except asyncio.TimeoutError:
                pytest.fail("Timeout résolution Einstein")
            except Exception as e:
                pytest.fail(f"Erreur résolution Einstein: {e}")

        asyncio.run(run_test())

    def test_einstein_puzzle_complexity_levels(self, einstein_test_environment):
        """Test différents niveaux de complexité du puzzle Einstein."""

        async def run_test():
            complexity_levels = ["simple", "medium", "complex"]

            for complexity in complexity_levels:
                env = einstein_test_environment.copy()
                env["PUZZLE_COMPLEXITY"] = complexity
                env["ADAPTIVE_HINTS"] = "true"

                try:
                    process = await asyncio.create_subprocess_exec(
                        sys.executable,
                        str(EINSTEIN_DEMO_SCRIPT),
                        "--test-mode",
                        "--complexity",
                        complexity,
                        "--max-hints",
                        "4",
                        env=env,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )

                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(), timeout=120.0  # 2 minutes par niveau
                    )

                    assert (
                        process.returncode == 0
                    ), f"Complexité {complexity} échouée: {stderr.decode()}"

                    output = stdout.decode("utf-8")

                    # Vérifications spécifiques au niveau de complexité
                    if complexity == "simple":
                        assert (
                            len(output.split("\n")) < 50
                        ), "Output trop verbeux pour simple"
                    elif complexity == "complex":
                        assert (
                            len(output.split("\n")) > 20
                        ), "Output trop court pour complex"

                    # Vérifier que la complexité est mentionnée
                    assert complexity in output.lower() or len(output) > 100

                except asyncio.TimeoutError:
                    pytest.fail(f"Timeout complexité {complexity}")
                except Exception as e:
                    pytest.fail(f"Erreur complexité {complexity}: {e}")

        asyncio.run(run_test())


@pytest.mark.integration
@pytest.mark.llm_critical
class TestEinsteinPuzzleLogic:
    """Tests de logique du puzzle Einstein."""

    def test_constraint_validation(self, einstein_test_environment):
        """Test la validation des contraintes Einstein."""

        async def run_test():
            env = einstein_test_environment.copy()
            env["CONSTRAINT_VALIDATION"] = "true"
            env["LOGIC_CHECK"] = "true"

            try:
                process = await asyncio.create_subprocess_exec(
                    sys.executable,
                    str(EINSTEIN_DEMO_SCRIPT),
                    "--test-mode",
                    "--constraint-check",
                    "--max-turns",
                    "4",
                    env=env,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=90.0
                )

                assert (
                    process.returncode == 0
                ), f"Validation contraintes échouée: {stderr.decode()}"

                output = stdout.decode("utf-8")

                # Vérifier que les contraintes classiques sont mentionnées
                classic_constraints = [
                    "anglais",
                    "rouge",
                    "suédois",
                    "chien",
                    "danois",
                    "thé",
                    "verte",
                    "blanche",
                    "café",
                ]

                constraints_found = sum(
                    1
                    for constraint in classic_constraints
                    if constraint in output.lower()
                )
                assert (
                    constraints_found >= 5
                ), f"Pas assez de contraintes Einstein: {constraints_found}"

            except asyncio.TimeoutError:
                pytest.fail("Timeout validation contraintes")
            except Exception as e:
                pytest.fail(f"Erreur validation contraintes: {e}")

        asyncio.run(run_test())

    def test_logical_deduction_process(self, einstein_test_environment):
        """Test le processus de déduction logique."""

        async def run_test():
            env = einstein_test_environment.copy()
            env["DEDUCTION_TRACKING"] = "true"
            env["STEP_BY_STEP"] = "true"

            try:
                process = await asyncio.create_subprocess_exec(
                    sys.executable,
                    str(EINSTEIN_DEMO_SCRIPT),
                    "--test-mode",
                    "--deduction-mode",
                    "--verbose",
                    env=env,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=150.0
                )

                assert (
                    process.returncode == 0
                ), f"Déduction logique échouée: {stderr.decode()}"

                output = stdout.decode("utf-8")

                # Vérifier les étapes de déduction
                deduction_indicators = [
                    "étape" in output.lower() or "step" in output.lower(),
                    "donc" in output.lower() or "alors" in output.lower(),
                    "si" in output.lower() and "alors" in output.lower(),
                    "déduction" in output.lower(),
                    "conclusion" in output.lower(),
                ]

                deduction_score = sum(deduction_indicators)
                assert (
                    deduction_score >= 3
                ), f"Processus de déduction insuffisant: {deduction_score}"

            except asyncio.TimeoutError:
                pytest.fail("Timeout déduction logique")
            except Exception as e:
                pytest.fail(f"Erreur déduction logique: {e}")

        asyncio.run(run_test())


@pytest.mark.integration
@pytest.mark.llm_critical
@pytest.mark.performance
class TestEinsteinPerformanceMetrics:
    """Tests de performance pour le demo Einstein."""

    def test_einstein_solving_performance(self, einstein_test_environment):
        """Test la performance de résolution Einstein."""

        async def run_test():
            performance_metrics = {
                "execution_times": [],
                "hint_counts": [],
                "api_calls_estimated": [],
                "memory_usage": [],
            }

            # Test sur plusieurs exécutions
            for run in range(2):  # Limité pour éviter coûts
                env = einstein_test_environment.copy()
                env["PERFORMANCE_RUN"] = str(run)
                env["METRICS_COLLECTION"] = "true"

                start_time = time.time()

                try:
                    process = await asyncio.create_subprocess_exec(
                        sys.executable,
                        str(EINSTEIN_DEMO_SCRIPT),
                        "--test-mode",
                        "--performance-test",
                        "--max-hints",
                        "3",
                        env=env,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )

                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(), timeout=120.0
                    )

                    execution_time = time.time() - start_time
                    performance_metrics["execution_times"].append(execution_time)

                    assert (
                        process.returncode == 0
                    ), f"Performance run {run} échouée: {stderr.decode()}"

                    output = stdout.decode("utf-8")

                    # Compter les indices et appels API estimés
                    hint_count = output.lower().count("indice") + output.lower().count(
                        "hint"
                    )
                    api_calls = output.lower().count("api") + output.lower().count(
                        "openai"
                    )

                    performance_metrics["hint_counts"].append(hint_count)
                    performance_metrics["api_calls_estimated"].append(api_calls)

                except asyncio.TimeoutError:
                    performance_metrics["execution_times"].append(120.0)
                    performance_metrics["hint_counts"].append(0)
                    performance_metrics["api_calls_estimated"].append(0)

            # Analyse des performances
            avg_execution_time = sum(performance_metrics["execution_times"]) / len(
                performance_metrics["execution_times"]
            )
            avg_hints = sum(performance_metrics["hint_counts"]) / len(
                performance_metrics["hint_counts"]
            )

            # Vérifications de performance
            assert (
                avg_execution_time < 90
            ), f"Temps d'exécution trop lent: {avg_execution_time}s"
            assert avg_hints >= 1, f"Pas assez d'indices générés: {avg_hints}"

            print(f"\n=== PERFORMANCE EINSTEIN DEMO ===")
            print(f"Temps moyen: {avg_execution_time:.2f}s")
            print(f"Indices moyens: {avg_hints:.1f}")
            print(
                f"Stabilité: {max(performance_metrics['execution_times']) - min(performance_metrics['execution_times']):.2f}s"
            )

        asyncio.run(run_test())

    def test_memory_efficiency_einstein(self, einstein_test_environment):
        """Test l'efficacité mémoire du demo Einstein."""

        async def run_test():
            env = einstein_test_environment.copy()
            env["MEMORY_MONITORING"] = "true"
            env["LIGHTWEIGHT_MODE"] = "true"

            try:
                process = await asyncio.create_subprocess_exec(
                    sys.executable,
                    str(EINSTEIN_DEMO_SCRIPT),
                    "--test-mode",
                    "--memory-efficient",
                    "--max-hints",
                    "2",
                    env=env,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=60.0
                )

                assert (
                    process.returncode == 0
                ), f"Test mémoire échoué: {stderr.decode()}"

                output = stdout.decode("utf-8")

                # Vérifications d'efficacité
                lines = output.split("\n")
                assert len(lines) < 200, f"Output trop verbeux: {len(lines)} lignes"

                # Pas d'indicateurs de fuite mémoire
                memory_issues = [
                    "memory error",
                    "out of memory",
                    "allocation failed",
                    "memory leak",
                ]

                for issue in memory_issues:
                    assert (
                        issue not in output.lower()
                    ), f"Problème mémoire détecté: {issue}"

            except asyncio.TimeoutError:
                pytest.fail("Timeout test mémoire")
            except Exception as e:
                pytest.fail(f"Erreur test mémoire: {e}")

        asyncio.run(run_test())
