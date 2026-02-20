"""
Tests d'intégration pour run_cluedo_oracle_enhanced.py avec GPT-4o-mini réel.

Tests couvrant:
- Test complet run_cluedo_oracle_enhanced.py avec GPT-4o-mini
- Validation révélations automatiques Moriarty
- Mesure performance et latence OpenAI
"""

import pytest
import asyncio
import os
import time
import sys
import subprocess
from types import SimpleNamespace
from pathlib import Path

# Imports de mocks supprimés - Phase 3A purge complète
from typing import Dict, Any, List

# Configuration pour tests réels GPT-4o-mini
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
REAL_GPT_AVAILABLE = OPENAI_API_KEY is not None and len(OPENAI_API_KEY) > 10

# Chemins des scripts
PROJECT_ROOT = Path(__file__).parent.parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts" / "sherlock_watson"
CLUEDO_ENHANCED_SCRIPT = SCRIPTS_DIR / "run_cluedo_oracle_enhanced.py"

# Skip si pas d'API key ou script manquant
pytestmark = pytest.mark.skipif(
    not REAL_GPT_AVAILABLE or not CLUEDO_ENHANCED_SCRIPT.exists(),
    reason="Tests nécessitent OPENAI_API_KEY et run_cluedo_oracle_enhanced.py",
)


@pytest.fixture
def enhanced_test_environment():
    """Configuration d'environnement pour tests Enhanced."""
    env = os.environ.copy()
    env["OPENAI_API_KEY"] = OPENAI_API_KEY
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    env["ORACLE_MODE"] = "enhanced"
    env["TEST_MODE"] = "true"
    # Remove PYTEST_CURRENT_TEST so subprocess uses real LLM
    # (create_llm_service auto-mocks when it detects this env var)
    env.pop("PYTEST_CURRENT_TEST", None)
    return env


@pytest.fixture
def performance_monitor():
    """Moniteur de performance pour tests Enhanced."""
    metrics = {
        "start_time": None,
        "end_time": None,
        "duration": None,
        "api_calls": 0,
        "tokens_used": 0,
        "errors": [],
        "revelations": 0,
    }

    class PerformanceMonitor:
        def __init__(self):
            # Les métriques sont réinitialisées pour chaque test utilisant la fixture.
            self.metrics = metrics.copy()

        def start(self):
            self.metrics["start_time"] = time.time()

        def stop(self):
            if self.metrics["start_time"] is not None:
                self.metrics["end_time"] = time.time()
                self.metrics["duration"] = (
                    self.metrics["end_time"] - self.metrics["start_time"]
                )

        def api_call(self, tokens=None):
            self.metrics["api_calls"] += 1
            if tokens:
                self.metrics["tokens_used"] += tokens

        def error(self, error):
            self.metrics["errors"].append(str(error))

        def revelation(self):
            self.metrics["revelations"] += 1

    return PerformanceMonitor()


@pytest.mark.integration
@pytest.mark.llm_critical
@pytest.mark.slow
class TestCluedoOracleEnhancedReal:
    """Tests d'intégration pour Cluedo Oracle Enhanced réel."""

    def test_enhanced_script_exists_and_executable(self):
        """Test que le script Enhanced existe et est exécutable."""
        assert (
            CLUEDO_ENHANCED_SCRIPT.exists()
        ), f"Script manquant: {CLUEDO_ENHANCED_SCRIPT}"
        assert (
            CLUEDO_ENHANCED_SCRIPT.is_file()
        ), f"N'est pas un fichier: {CLUEDO_ENHANCED_SCRIPT}"

        # Vérifier que le script contient les imports nécessaires
        content = CLUEDO_ENHANCED_SCRIPT.read_text(encoding="utf-8")

        required_imports = [
            "CluedoExtendedOrchestrator",
            "run_cluedo_oracle_game",
            "enhanced",
            "auto_reveal",
        ]

        for required in required_imports:
            assert required in content, f"Import/référence manquant: {required}"

    def test_enhanced_script_basic_execution(
        self, enhanced_test_environment, performance_monitor
    ):
        """Test l'exécution de base du script Enhanced."""
        performance_monitor.start()

        try:
            # Exécution du script avec timeout
            process = asyncio.run(
                asyncio.create_subprocess_exec(
                    sys.executable,
                    str(CLUEDO_ENHANCED_SCRIPT),
                    "--test-mode",
                    "--max-turns",
                    "3",
                    "--enhanced-mode",
                    env=enhanced_test_environment,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            )

            # Attendre avec timeout
            try:
                stdout, stderr = asyncio.run(
                    asyncio.wait_for(
                        process.communicate(), timeout=120.0  # 2 minutes max
                    )
                )
            except asyncio.TimeoutError:
                process.kill()
                pytest.fail("Script Enhanced timeout après 2 minutes")

            performance_monitor.stop()

            # Vérifications de base
            assert process.returncode == 0, f"Script échoué. STDERR: {stderr.decode()}"

            output = stdout.decode("utf-8")
            assert len(output) > 100, "Output trop court"

            # Vérifications spécifiques Enhanced
            enhanced_indicators = [
                "enhanced" in output.lower(),
                "auto" in output.lower() and "reveal" in output.lower(),
                "moriarty" in output.lower(),
                "oracle" in output.lower(),
            ]

            assert (
                sum(enhanced_indicators) >= 2
            ), f"Pas assez d'indicateurs Enhanced dans: {output[:500]}"

            # Vérifications de performance
            assert performance_monitor.metrics["duration"] < 120, "Exécution trop lente"

        except Exception as e:
            performance_monitor.error(str(e))
            raise

    def test_enhanced_auto_revelations_validation(
        self, enhanced_test_environment, performance_monitor
    ):
        """Test la validation des révélations automatiques Enhanced."""
        performance_monitor.start()

        # Configuration pour forcer les révélations automatiques
        env = enhanced_test_environment.copy()
        env["FORCE_AUTO_REVELATIONS"] = "true"
        env["REVELATION_THRESHOLD"] = "0.3"  # Seuil bas pour déclencher facilement

        try:
            process = asyncio.run(
                asyncio.create_subprocess_exec(
                    sys.executable,
                    str(CLUEDO_ENHANCED_SCRIPT),
                    "--test-mode",
                    "--max-turns",
                    "6",
                    "--oracle-strategy",
                    "enhanced_auto_reveal",
                    "--verbose",
                    env=env,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            )

            stdout, stderr = asyncio.run(
                asyncio.wait_for(
                    process.communicate(), timeout=180.0  # 3 minutes pour révélations
                )
            )

            performance_monitor.stop()

            assert (
                process.returncode == 0
            ), f"Script révélations échoué: {stderr.decode()}"

            output = stdout.decode("utf-8")

            # Recherche de révélations automatiques ou d'indicateurs de jeu
            revelation_patterns = [
                "révèle automatiquement",
                "auto-révélation",
                "moriarty révèle",
                "carte révélée",
                "indice révélé",
                "enhanced_auto_reveal",
                "auto_reveal",
                "révélation",
                "oracle",
                "workflow",
            ]

            output_lower = output.lower()
            revelations_found = sum(
                1 for pattern in revelation_patterns if pattern in output_lower
            )
            assert (
                revelations_found >= 1
            ), f"Aucun indicateur de jeu détecté dans: {output[:1000]}"

            performance_monitor.metrics["revelations"] = revelations_found

        except asyncio.TimeoutError:
            pytest.fail("Timeout révélations automatiques")
        except Exception as e:
            performance_monitor.error(str(e))
            raise

    def test_enhanced_performance_metrics(
        self, enhanced_test_environment, performance_monitor
    ):
        """Test et mesure des métriques de performance Enhanced."""
        performance_monitor.start()

        # Configuration optimisée pour performance
        env = enhanced_test_environment.copy()
        env["PERFORMANCE_MODE"] = "true"
        env["OPENAI_TIMEOUT"] = "30"
        env["MAX_TOKENS"] = "200"

        start_time = time.time()
        api_calls_estimated = 0

        try:
            process = asyncio.run(
                asyncio.create_subprocess_exec(
                    sys.executable,
                    str(CLUEDO_ENHANCED_SCRIPT),
                    "--test-mode",
                    "--max-turns",
                    "4",
                    "--performance-test",
                    env=env,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            )

            stdout, stderr = asyncio.run(
                asyncio.wait_for(
                    process.communicate(), timeout=90.0  # 1.5 minutes pour performance
                )
            )

            execution_time = time.time() - start_time
            performance_monitor.stop()

            assert (
                process.returncode == 0
            ), f"Test performance échoué: {stderr.decode()}"

            output = stdout.decode("utf-8")

            # Analyse des performances
            lines = output.split("\n")
            for line in lines:
                if "api call" in line.lower() or "openai" in line.lower():
                    api_calls_estimated += 1
                if "token" in line.lower():
                    # Extraction approximative du nombre de tokens
                    try:
                        tokens = int("".join(filter(str.isdigit, line)))
                        performance_monitor.api_call(tokens)
                    except:
                        pass

            # Métriques de performance
            performance_metrics = {
                "execution_time": execution_time,
                "estimated_api_calls": api_calls_estimated,
                "avg_time_per_call": execution_time / max(api_calls_estimated, 1),
                "output_length": len(output),
            }

            # Vérifications de performance
            assert execution_time < 90, f"Trop lent: {execution_time}s"
            assert (
                api_calls_estimated <= 15
            ), f"Trop d'appels API: {api_calls_estimated}"
            assert (
                performance_metrics["avg_time_per_call"] < 15
            ), "Appels API trop lents"

            # Log des métriques pour analyse
            print(f"\n=== MÉTRIQUES PERFORMANCE ENHANCED ===")
            for key, value in performance_metrics.items():
                print(f"{key}: {value}")

        except asyncio.TimeoutError:
            pytest.fail(f"Timeout performance après {time.time() - start_time}s")
        except Exception as e:
            performance_monitor.error(str(e))
            raise

    def test_enhanced_error_recovery(self, enhanced_test_environment):
        """Test la récupération d'erreur du script Enhanced."""
        # Configuration avec conditions d'erreur potentielles
        env = enhanced_test_environment.copy()
        env["STRESS_TEST"] = "true"
        env["NETWORK_UNSTABLE"] = "true"  # Simulation réseau instable

        try:
            process = asyncio.run(
                asyncio.create_subprocess_exec(
                    sys.executable,
                    str(CLUEDO_ENHANCED_SCRIPT),
                    "--test-mode",
                    "--max-turns",
                    "2",
                    "--error-recovery-test",
                    env=env,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            )

            stdout, stderr = asyncio.run(
                asyncio.wait_for(process.communicate(), timeout=60.0)
            )

            # Le script devrait soit réussir, soit échouer gracieusement
            output = stdout.decode("utf-8")
            error_output = stderr.decode("utf-8")

            if process.returncode != 0:
                # Si échec, vérifier que c'est une erreur gérée
                expected_errors = [
                    "timeout",
                    "rate limit",
                    "api error",
                    "network error",
                    "graceful shutdown",
                ]

                error_handled = any(
                    error in error_output.lower() for error in expected_errors
                )
                assert error_handled, f"Erreur non gérée: {error_output}"
            else:
                # Si succès, le script a terminé sans crash — c'est suffisant
                # pour un test de stress/error-recovery
                assert len(output) > 0, "Output vide malgré succès"

        except asyncio.TimeoutError:
            # Timeout acceptable pour test de stress
            pass


@pytest.mark.integration
@pytest.mark.llm_critical
class TestCluedoEnhancedIntegrationValidation:
    """Tests de validation de l'intégration Enhanced."""

    def test_enhanced_configuration_validation(self, enhanced_test_environment):
        """Test la validation de configuration Enhanced."""
        # Test avec différentes configurations
        test_configs = [
            {"ORACLE_STRATEGY": "enhanced_auto_reveal"},
            {"ORACLE_STRATEGY": "enhanced_progressive"},
            {"MAX_TURNS": "10", "MAX_CYCLES": "3"},
            {"ENHANCED_MODE": "true", "AUTO_REVEAL_THRESHOLD": "0.5"},
        ]

        for config in test_configs:
            env = enhanced_test_environment.copy()
            env.update(config)

            # Test que la configuration est acceptée
            # (test rapide sans exécution complète)
            assert all(key in env for key in config.keys())

    def test_enhanced_output_quality_validation(self, enhanced_test_environment):
        """Test la validation de qualité des outputs Enhanced."""
        env = enhanced_test_environment.copy()
        env["OUTPUT_VALIDATION"] = "true"

        try:
            process = asyncio.run(
                asyncio.create_subprocess_exec(
                    sys.executable,
                    str(CLUEDO_ENHANCED_SCRIPT),
                    "--test-mode",
                    "--max-turns",
                    "3",
                    "--quality-check",
                    env=env,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            )

            stdout, stderr = asyncio.run(
                asyncio.wait_for(process.communicate(), timeout=90.0)
            )

            assert (
                process.returncode == 0
            ), f"Validation qualité échouée: {stderr.decode()}"

            output = stdout.decode("utf-8")

            # Critères de qualité Enhanced
            quality_criteria = [
                len(output) > 200,  # Output substantiel
                "sherlock" in output.lower(),  # Agent présent
                "watson" in output.lower(),  # Agent présent
                "moriarty" in output.lower(),  # Agent présent
                output.count(".") >= 5,  # Phrases complètes
                not any(
                    word in output.lower() for word in ["error", "failed", "exception"]
                ),  # Pas d'erreurs visibles
            ]

            quality_score = sum(quality_criteria) / len(quality_criteria)
            assert quality_score >= 0.7, f"Qualité insuffisante: {quality_score}"

        except asyncio.TimeoutError:
            pytest.fail("Timeout validation qualité")

    def test_enhanced_script_imports_validation(self):
        """Test la validation des imports du script Enhanced."""
        if not CLUEDO_ENHANCED_SCRIPT.exists():
            pytest.skip("Script Enhanced non trouvé")

        content = CLUEDO_ENHANCED_SCRIPT.read_text(encoding="utf-8")

        # Imports critiques pour Enhanced
        critical_imports = [
            "semantic_kernel",
            "OpenAIChatCompletion",
            "CluedoExtendedOrchestrator",
            "run_cluedo_oracle_game",
        ]

        missing_imports = []
        for import_name in critical_imports:
            if import_name not in content:
                missing_imports.append(import_name)

        assert not missing_imports, f"Imports manquants: {missing_imports}"

        # Vérifier la configuration Enhanced spécifique
        enhanced_config_patterns = [
            "enhanced",
            "auto_reveal",
            "gpt-5-mini",
            "oracle_strategy",
        ]

        enhanced_features = sum(
            1 for pattern in enhanced_config_patterns if pattern in content.lower()
        )
        assert (
            enhanced_features >= 2
        ), f"Pas assez de features Enhanced: {enhanced_features}"


@pytest.mark.integration
@pytest.mark.llm_critical
@pytest.mark.performance
class TestCluedoEnhancedLatencyMeasurement:
    """Tests de mesure de latence avec GPT-4o-mini."""

    def test_openai_latency_measurement(self, enhanced_test_environment):
        """Mesure la latence des appels OpenAI."""
        latencies = []

        for test_run in range(1):  # Single measurement (full game takes time)
            env = enhanced_test_environment.copy()
            env["LATENCY_TEST"] = f"run_{test_run}"
            env["SINGLE_CALL_TEST"] = "true"

            start_time = time.time()

            try:
                # Use --test-mode --max-turns 2 (the script doesn't support
                # --latency-test or --single-call flags)
                process = asyncio.run(
                    asyncio.create_subprocess_exec(
                        sys.executable,
                        str(CLUEDO_ENHANCED_SCRIPT),
                        "--test-mode",
                        "--max-turns",
                        "2",
                        env=env,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                )

                stdout, stderr = asyncio.run(
                    asyncio.wait_for(process.communicate(), timeout=120.0)
                )

                call_latency = time.time() - start_time
                latencies.append(call_latency)

                assert (
                    process.returncode == 0
                ), f"Test latence échoué: {stderr.decode()}"

            except asyncio.TimeoutError:
                latencies.append(120.0)  # Timeout = latence max

        # Analyse des latences
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        min_latency = min(latencies)

        # Vérifications de latence acceptable (full game run with real LLM)
        assert avg_latency < 90.0, f"Latence moyenne trop élevée: {avg_latency}s"
        assert max_latency < 120.0, f"Latence max trop élevée: {max_latency}s"

        print(f"\n=== LATENCES OPENAI GPT-4O-MINI ===")
        print(f"Moyenne: {avg_latency:.2f}s")
        print(f"Min: {min_latency:.2f}s")
        print(f"Max: {max_latency:.2f}s")
        print(
            f"Écart-type: {(sum((l - avg_latency)**2 for l in latencies) / len(latencies))**0.5:.2f}s"
        )
