"""
Tests de validation pour l'exécution des scripts Sherlock-Watson-Moriarty.

Tests couvrant:
- Test exécution run_cluedo_oracle_enhanced.py sans erreurs
- Test exécution run_einstein_oracle_demo.py sans erreurs
- Test test_oracle_behavior_simple.py validation
- Test intégration activate_project_env.ps1
"""

import pytest
import asyncio
import os
import sys
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="Script execution tests require OPENAI_API_KEY for LLM-based workflows",
)

# Configuration des chemins
PROJECT_ROOT = Path(__file__).parent.parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts" / "sherlock_watson"
VALIDATION_DIR = PROJECT_ROOT / "tests" / "validation_sherlock_watson"

# Scripts à tester
SCRIPTS_TO_VALIDATE = {
    "cluedo_enhanced": SCRIPTS_DIR / "run_cluedo_oracle_enhanced.py",
    "einstein_demo": SCRIPTS_DIR / "run_einstein_oracle_demo.py",
    "oracle_behavior_simple": SCRIPTS_DIR / "test_oracle_behavior_simple.py",
    "oracle_behavior_demo": SCRIPTS_DIR / "test_oracle_behavior_demo.py",
}

# Configuration environnement de test
TEST_ENV_BASE = {
    "PYTHONPATH": str(PROJECT_ROOT),
    "TEST_MODE": "true",
    "VALIDATION_RUN": "true",
    "MAX_EXECUTION_TIME": "60",
    "MOCK_MODE": "true",  # Par défaut en mock pour validation rapide
}


@pytest.fixture
def script_test_environment():
    """Environnement de test pour validation des scripts."""
    env = os.environ.copy()
    env.update(TEST_ENV_BASE)
    return env


@pytest.fixture
def script_timeout_config():
    """Configuration des timeouts pour différents scripts."""
    return {
        "cluedo_enhanced": 90,  # 1.5 minutes
        "einstein_demo": 120,  # 2 minutes
        "oracle_behavior_simple": 45,  # 45 secondes
        "oracle_behavior_demo": 60,  # 1 minute
        "default": 60,
    }


class ScriptExecutionValidator:
    """Validateur d'exécution des scripts."""

    def __init__(self):
        self.execution_results = {}
        self.performance_metrics = {}

    async def validate_script_execution(
        self,
        script_path: Path,
        script_name: str,
        environment: Dict[str, str],
        timeout: int = 60,
        additional_args: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Valide l'exécution d'un script."""

        if not script_path.exists():
            return {
                "success": False,
                "error": f"Script not found: {script_path}",
                "execution_time": 0,
            }

        args = [sys.executable, str(script_path)]
        if additional_args:
            args.extend(additional_args)

        start_time = time.time()

        try:
            process = await asyncio.create_subprocess_exec(
                *args,
                env=environment,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return {
                    "success": False,
                    "error": f"Script timeout after {timeout}s",
                    "execution_time": timeout,
                }

            execution_time = time.time() - start_time

            return {
                "success": process.returncode == 0,
                "return_code": process.returncode,
                "stdout": stdout.decode("utf-8", errors="ignore"),
                "stderr": stderr.decode("utf-8", errors="ignore"),
                "execution_time": execution_time,
                "error": (
                    None
                    if process.returncode == 0
                    else stderr.decode("utf-8", errors="ignore")
                ),
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time,
            }

    def analyze_script_output(self, output: str, script_type: str) -> Dict[str, Any]:
        """Analyse la sortie d'un script."""
        import re

        analysis = {
            "output_length": len(output),
            "line_count": len(output.split("\n")),
            "contains_errors": False,
            "contains_warnings": False,
            "quality_score": 0.0,
            "features_detected": [],
        }

        # Détection d'erreurs et warnings
        error_indicators = ["error", "exception", "failed", "traceback"]
        warning_indicators = ["warning", "warn", "attention"]

        # Exclure les erreurs contrôlées de l'analyse pour éviter les faux positifs
        clean_output = re.sub(
            r"---AGENT_ERROR_START---.*?---AGENT_ERROR_END---",
            "",
            output,
            flags=re.DOTALL | re.IGNORECASE,
        )
        output_lower = clean_output.lower()

        analysis["contains_errors"] = any(
            indicator in output_lower for indicator in error_indicators
        )

        # Pour les warnings, on peut rester sur la sortie complète
        analysis["contains_warnings"] = any(
            indicator in output.lower() for indicator in warning_indicators
        )

        # Score de qualité basé sur le contenu
        quality_score = 0.0

        if analysis["output_length"] > 100:
            quality_score += 0.2

        if not analysis["contains_errors"]:
            quality_score += 0.3

        # Features spécifiques par type de script
        if script_type == "cluedo_enhanced":
            cluedo_features = [
                "sherlock",
                "watson",
                "moriarty",
                "oracle",
                "enhanced",
                "revelation",
            ]
            detected = [f for f in cluedo_features if f in output_lower]
            analysis["features_detected"] = detected
            quality_score += 0.1 * len(detected)

        elif script_type == "einstein_demo":
            einstein_features = [
                "einstein",
                "puzzle",
                "hint",
                "maison",
                "progressive",
                "deduction",
            ]
            detected = [f for f in einstein_features if f in output_lower]
            analysis["features_detected"] = detected
            quality_score += 0.1 * len(detected)

        elif "oracle_behavior" in script_type:
            oracle_features = ["oracle", "behavior", "test", "validation", "moriarty"]
            detected = [f for f in oracle_features if f in output_lower]
            analysis["features_detected"] = detected
            quality_score += 0.1 * len(detected)

        analysis["quality_score"] = min(quality_score, 1.0)

        return analysis


@pytest.mark.validation
class TestScriptsExecution:
    """Tests de validation de l'exécution des scripts."""

    @pytest.fixture(autouse=True)
    def setup_validator(self):
        """Setup du validateur pour tous les tests."""
        self.validator = ScriptExecutionValidator()

    @pytest.mark.asyncio
    async def test_cluedo_enhanced_execution(
        self, script_test_environment, script_timeout_config
    ):
        """Test l'exécution de run_cluedo_oracle_enhanced.py."""
        script_path = SCRIPTS_TO_VALIDATE["cluedo_enhanced"]
        timeout = script_timeout_config["cluedo_enhanced"]

        result = await self.validator.validate_script_execution(
            script_path=script_path,
            script_name="cluedo_enhanced",
            environment=script_test_environment,
            timeout=timeout,
            additional_args=["--test-mode", "--max-turns", "2"],
        )

        # Vérifications de base
        assert result[
            "success"
        ], f"Cluedo Enhanced échoué: {result.get('error', 'Unknown error')}"
        assert (
            result["execution_time"] < timeout
        ), f"Trop lent: {result['execution_time']}s"

        # Analyse de la sortie
        output_analysis = self.validator.analyze_script_output(
            result["stdout"], "cluedo_enhanced"
        )

        if output_analysis["contains_errors"]:
            print("STDOUT:", result["stdout"])
            print("STDERR:", result["stderr"])

        assert not output_analysis[
            "contains_errors"
        ], "Erreurs détectées dans la sortie"
        assert (
            output_analysis["quality_score"] > 0.4
        ), f"Qualité insuffisante: {output_analysis['quality_score']}"
        assert (
            len(output_analysis["features_detected"]) >= 3
        ), "Pas assez de features Cluedo détectées"

    @pytest.mark.asyncio
    async def test_einstein_demo_execution(
        self, script_test_environment, script_timeout_config
    ):
        """Test l'exécution de run_einstein_oracle_demo.py."""
        script_path = SCRIPTS_TO_VALIDATE["einstein_demo"]
        timeout = script_timeout_config["einstein_demo"]

        result = await self.validator.validate_script_execution(
            script_path=script_path,
            script_name="einstein_demo",
            environment=script_test_environment,
            timeout=timeout,
            additional_args=["--integration-test"],
        )

        assert result[
            "success"
        ], f"Einstein Demo échoué: {result.get('error', 'Unknown error')}"
        assert (
            result["execution_time"] < timeout
        ), f"Trop lent: {result['execution_time']}s"

        # Analyse spécifique Einstein
        output_analysis = self.validator.analyze_script_output(
            result["stdout"], "einstein_demo"
        )

        assert not output_analysis[
            "contains_errors"
        ], "Erreurs détectées dans Einstein Demo"
        assert (
            output_analysis["quality_score"] > 0.3
        ), f"Qualité Einstein insuffisante: {output_analysis['quality_score']}"

        # Vérifications spécifiques Einstein
        einstein_keywords = ["einstein", "puzzle", "hint"]
        found_keywords = [
            kw for kw in einstein_keywords if kw in result["stdout"].lower()
        ]
        assert (
            len(found_keywords) >= 2
        ), f"Pas assez de mots-clés Einstein: {found_keywords}"

    @pytest.mark.asyncio
    async def test_oracle_behavior_simple_execution(
        self, script_test_environment, script_timeout_config
    ):
        """Test l'exécution de test_oracle_behavior_simple.py."""
        script_path = SCRIPTS_TO_VALIDATE["oracle_behavior_simple"]
        timeout = script_timeout_config["oracle_behavior_simple"]

        result = await self.validator.validate_script_execution(
            script_path=script_path,
            script_name="oracle_behavior_simple",
            environment=script_test_environment,
            timeout=timeout,
            additional_args=["--validation-mode"],
        )

        assert result[
            "success"
        ], f"Oracle Behavior Simple échoué: {result.get('error', 'Unknown error')}"
        assert (
            result["execution_time"] < timeout
        ), f"Trop lent: {result['execution_time']}s"

        # Analyse comportement Oracle
        output_analysis = self.validator.analyze_script_output(
            result["stdout"], "oracle_behavior_simple"
        )

        assert not output_analysis[
            "contains_errors"
        ], "Erreurs dans Oracle Behavior Simple"
        assert (
            output_analysis["quality_score"] > 0.3
        ), f"Qualité Oracle insuffisante: {output_analysis['quality_score']}"

    @pytest.mark.asyncio
    async def test_oracle_behavior_demo_execution(
        self, script_test_environment, script_timeout_config
    ):
        """Test l'exécution de test_oracle_behavior_demo.py."""
        script_path = SCRIPTS_TO_VALIDATE["oracle_behavior_demo"]
        timeout = script_timeout_config["oracle_behavior_demo"]

        result = await self.validator.validate_script_execution(
            script_path=script_path,
            script_name="oracle_behavior_demo",
            environment=script_test_environment,
            timeout=timeout,
            additional_args=["--demo-mode"],
        )

        assert result[
            "success"
        ], f"Oracle Behavior Demo échoué: {result.get('error', 'Unknown error')}"
        assert (
            result["execution_time"] < timeout
        ), f"Trop lent: {result['execution_time']}s"

        # Analyse demo Oracle
        output_analysis = self.validator.analyze_script_output(
            result["stdout"], "oracle_behavior_demo"
        )

        assert not output_analysis[
            "contains_errors"
        ], f"Erreurs dans Oracle Behavior Demo: {result.get('error', 'Unknown error')}"
        assert (
            output_analysis["quality_score"] > 0.3
        ), f"Qualité Demo insuffisante: {output_analysis['quality_score']}"

    @pytest.mark.asyncio
    async def test_all_scripts_parallel_execution(
        self, script_test_environment, script_timeout_config
    ):
        """Test l'exécution parallèle de tous les scripts."""

        tasks = []
        script_names_in_order = []
        start_time = time.time()

        for script_name, script_path in SCRIPTS_TO_VALIDATE.items():
            if script_path.exists():
                timeout = script_timeout_config.get(
                    script_name, script_timeout_config["default"]
                )

                task = self.validator.validate_script_execution(
                    script_path=script_path,
                    script_name=script_name,
                    environment=script_test_environment,
                    timeout=timeout,
                    additional_args=["--test-mode", "--quick"],
                )
                tasks.append(task)
                script_names_in_order.append(script_name)

        parallel_results = await asyncio.gather(*tasks)
        results = dict(zip(script_names_in_order, parallel_results))

        total_time = time.time() - start_time

        # Vérifications globales
        successful_scripts = [
            name for name, result in results.items() if result["success"]
        ]
        failed_scripts = [
            name for name, result in results.items() if not result["success"]
        ]

        assert len(successful_scripts) >= len(
            failed_scripts
        ), f"Plus d'échecs que de succès: {failed_scripts}"
        assert total_time < 180, f"Exécution parallèle trop lente: {total_time}s"

        # Log des résultats
        print(f"\n=== RÉSULTATS VALIDATION SCRIPTS ===")
        print(f"Succès: {len(successful_scripts)}")
        print(f"Échecs: {len(failed_scripts)}")
        print(f"Temps total: {total_time:.2f}s")

        for script_name, result in results.items():
            status = "✅" if result["success"] else "❌"
            time_taken = result.get("execution_time", 0)
            print(f"{status} {script_name}: {time_taken:.2f}s")


@pytest.mark.validation
class TestEnvironmentIntegration:
    """Tests d'intégration avec l'environnement."""

    def test_project_environment_setup(self):
        """Test la configuration de l'environnement du projet."""
        # Vérifier la structure du projet
        assert PROJECT_ROOT.exists(), f"Racine projet manquante: {PROJECT_ROOT}"
        assert SCRIPTS_DIR.exists(), f"Dossier scripts manquant: {SCRIPTS_DIR}"

        # Vérifier les modules Python importables
        sys.path.insert(0, str(PROJECT_ROOT))

        try:
            import argumentation_analysis
            import argumentation_analysis.core
            import argumentation_analysis.agents
            import argumentation_analysis.orchestration
        except ImportError as e:
            pytest.fail(f"Modules projet non importables: {e}")

        # Vérifier les variables d'environnement critiques
        critical_paths = [
            "PYTHONPATH",
        ]

        env = os.environ
        for path_var in critical_paths:
            if path_var in env:
                assert str(PROJECT_ROOT) in env[path_var] or env[path_var] == str(
                    PROJECT_ROOT
                )

    def test_powershell_activation_script(self):
        """Test l'intégration avec activate_project_env.ps1."""
        ps_script = PROJECT_ROOT / "activate_project_env.ps1"

        if not ps_script.exists():
            pytest.skip("Script PowerShell activate_project_env.ps1 non trouvé")

        # Vérifier le contenu du script
        content = ps_script.read_text(encoding="utf-8")

        required_elements = [
            # Vérifie que le script utilise conda run, la méthode d'exécution standard
            "conda run",
            # Vérifie que le script délègue la logique au manager Python
            "project_core.core_from_scripts.environment_manager",
            # Vérifie que la sortie est streamée, ce qui est crucial pour les tests
            "--no-capture-output",
        ]

        missing_elements = [elem for elem in required_elements if elem not in content]
        assert (
            not missing_elements
        ), f"Éléments manquants dans PS script: {missing_elements}"

    def test_scripts_directory_structure(self):
        """Test la structure du dossier scripts."""
        expected_scripts = [
            "run_cluedo_oracle_enhanced.py",
            "run_einstein_oracle_demo.py",
            "test_oracle_behavior_simple.py",
        ]

        existing_scripts = []
        missing_scripts = []

        for script_name in expected_scripts:
            script_path = SCRIPTS_DIR / script_name
            if script_path.exists():
                existing_scripts.append(script_name)
            else:
                missing_scripts.append(script_name)

        # Au moins 50% des scripts doivent exister
        assert (
            len(existing_scripts) >= len(expected_scripts) // 2
        ), f"Trop de scripts manquants: {missing_scripts}"

        # Vérifier que les scripts existants sont valides
        for script_name in existing_scripts:
            script_path = SCRIPTS_DIR / script_name
            content = script_path.read_text(encoding="utf-8")

            # Vérifications de base
            assert len(content) > 100, f"Script {script_name} trop court"
            assert "import" in content, f"Script {script_name} sans imports"
            assert (
                "def " in content or "class " in content or "if __name__" in content
            ), f"Script {script_name} structure invalide"


@pytest.mark.validation
class TestScriptErrorHandling:
    """Tests de gestion d'erreur des scripts."""

    @pytest.fixture(autouse=True)
    def setup_validator(self):
        """Setup du validateur."""
        self.validator = ScriptExecutionValidator()

    @pytest.mark.asyncio
    async def test_scripts_with_invalid_arguments(self, script_test_environment):
        """Test les scripts avec arguments invalides."""
        invalid_args_tests = [
            ["--invalid-flag"],
            ["--max-turns", "not_a_number"],
            ["--timeout", "-1"],
            ["--unknown-option", "value"],
        ]

        # Test avec un script existant
        test_script = None
        for script_name, script_path in SCRIPTS_TO_VALIDATE.items():
            if script_path.exists():
                test_script = script_path
                break

        if not test_script:
            pytest.skip("Aucun script disponible pour test d'erreur")

        for invalid_args in invalid_args_tests:
            result = await self.validator.validate_script_execution(
                script_path=test_script,
                script_name="error_test",
                environment=script_test_environment,
                timeout=30,
                additional_args=invalid_args,
            )

            # Le script devrait soit gérer l'erreur gracieusement (retour 0)
            # soit échouer proprement (retour non-0) sans crash
            assert isinstance(result["return_code"], int), "Code de retour invalide"

            # Pas de traceback Python non géré
            if not result["success"]:
                stderr = result.get("stderr", "")
                assert (
                    "Traceback" not in stderr or "handled" in stderr.lower()
                ), f"Erreur non gérée avec args {invalid_args}: {stderr}"

    @pytest.mark.asyncio
    async def test_scripts_with_missing_dependencies(self, script_test_environment):
        """Test les scripts avec dépendances manquantes."""
        # Environnement avec PYTHONPATH corrompu
        corrupted_env = script_test_environment.copy()
        corrupted_env["PYTHONPATH"] = "/nonexistent/path"

        test_script = None
        for script_name, script_path in SCRIPTS_TO_VALIDATE.items():
            if script_path.exists():
                test_script = script_path
                break

        if not test_script:
            pytest.skip("Aucun script disponible pour test dépendances")

        result = await self.validator.validate_script_execution(
            script_path=test_script,
            script_name="dependency_test",
            environment=corrupted_env,
            timeout=30,
            additional_args=["--test-mode"],
        )

        # Le script devrait échouer mais avec un message d'erreur clair
        if not result["success"]:
            stderr = result.get("stderr", "")
            assert any(
                keyword in stderr.lower()
                for keyword in ["import", "module", "dependency", "path"]
            ), f"Erreur de dépendance peu claire: {stderr}"
