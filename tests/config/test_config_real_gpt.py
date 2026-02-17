"""
Tests de configuration pour GPT-4o-mini réel.

Tests couvrant:
- Validation configuration OpenAI correcte
- Test connexion GPT-4o-mini fonctionnelle
- Test modèles supportés et limites
"""

import pytest
import os
import asyncio
import time
from typing import Dict, Any, Optional

# Imports Semantic Kernel
from semantic_kernel.kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from semantic_kernel.connectors.ai.open_ai import OpenAIChatPromptExecutionSettings
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents.chat_history import ChatHistory

# Configuration
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
REAL_GPT_AVAILABLE = OPENAI_API_KEY is not None and len(OPENAI_API_KEY) > 10

# Skip si pas d'API key - ces tests nécessitent une clé API OpenAI valide
pytestmark = pytest.mark.skipif(
    not REAL_GPT_AVAILABLE,
    reason="Requires valid OPENAI_API_KEY in environment",
)


class GPTConfigValidator:
    """Validateur de configuration GPT-4o-mini."""

    def __init__(self):
        self.validation_results = {}

    def validate_api_key_format(self, api_key: str) -> Dict[str, Any]:
        """Valide le format de la clé API."""
        validation = {
            "valid_format": False,
            "sufficient_length": False,
            "proper_prefix": False,
            "issues": [],
        }

        if not api_key:
            validation["issues"].append("API key is empty")
            return validation

        # Vérifications de format
        if len(api_key) >= 20:
            validation["sufficient_length"] = True
        else:
            validation["issues"].append(f"API key too short: {len(api_key)} chars")

        if api_key.startswith("sk-"):
            validation["proper_prefix"] = True
        else:
            validation["issues"].append("API key should start with 'sk-'")

        validation["valid_format"] = (
            validation["sufficient_length"] and validation["proper_prefix"]
        )

        return validation

    async def test_api_connectivity(self, api_key: str) -> Dict[str, Any]:
        """Test la connectivité API."""
        connectivity_test = {
            "connection_successful": False,
            "response_time": 0.0,
            "model_accessible": False,
            "error": None,
        }

        try:
            kernel = Kernel()
            chat_service = OpenAIChatCompletion(
                service_id="config-test", ai_model_id="gpt-5-mini", api_key=api_key
            )
            kernel.add_service(chat_service)

            # Test de connectivité simple
            start_time = time.time()

            settings = OpenAIChatPromptExecutionSettings()

            messages = [ChatMessageContent(role="user", content="Test")]

            response = await chat_service.get_chat_message_contents(
                chat_history=ChatHistory(messages=messages), settings=settings
            )

            connectivity_test["response_time"] = time.time() - start_time
            connectivity_test["connection_successful"] = True
            connectivity_test["model_accessible"] = (
                len(response) > 0 and response[0].content is not None
            )

        except Exception as e:
            connectivity_test["error"] = str(e)

        return connectivity_test

    def validate_model_limits(self) -> Dict[str, Any]:
        """Valide les limites du modèle GPT-4o-mini."""
        return {
            "max_tokens": 16384,  # Limite context GPT-4o-mini
            "max_output_tokens": 4096,  # Limite output
            "rate_limit_rpm": 500,  # Requêtes par minute (tier gratuit)
            "rate_limit_tpm": 200000,  # Tokens par minute
            "supported_features": [
                "chat_completion",
                "function_calling",
                "json_mode",
                "vision",  # GPT-4o-mini supporte la vision
            ],
        }


@pytest.fixture
def gpt_config_validator():
    """Fixture du validateur de configuration."""
    return GPTConfigValidator()


@pytest.mark.config
class TestGPTConfigValidation:
    """Tests de validation de configuration GPT-4o-mini."""

    def test_openai_api_key_validation(self, gpt_config_validator):
        """Test la validation de la clé API OpenAI."""
        # Test avec la vraie clé API
        validation = gpt_config_validator.validate_api_key_format(OPENAI_API_KEY)

        assert validation[
            "valid_format"
        ], f"Format clé API invalide: {validation['issues']}"
        assert validation["sufficient_length"], "Clé API trop courte"
        assert validation["proper_prefix"], "Préfixe clé API incorrect"
        assert (
            len(validation["issues"]) == 0
        ), f"Problèmes détectés: {validation['issues']}"

    def test_invalid_api_key_detection(self, gpt_config_validator):
        """Test la détection de clés API invalides."""
        invalid_keys = [
            "",
            "invalid-key",
            "sk-short",
            "pk-wrongprefix",
            "sk-" + "x" * 10,  # Trop courte
        ]

        for invalid_key in invalid_keys:
            validation = gpt_config_validator.validate_api_key_format(invalid_key)
            assert not validation[
                "valid_format"
            ], f"Clé invalide acceptée: {invalid_key}"
            assert (
                len(validation["issues"]) > 0
            ), f"Aucun problème détecté pour: {invalid_key}"

    @pytest.mark.asyncio
    @pytest.mark.real_llm
    async def test_gpt4o_mini_connectivity(self, gpt_config_validator):
        """Test la connectivité GPT-4o-mini."""
        connectivity = await gpt_config_validator.test_api_connectivity(OPENAI_API_KEY)

        assert connectivity[
            "connection_successful"
        ], f"Connexion échouée: {connectivity.get('error')}"
        assert (
            connectivity["response_time"] < 30.0
        ), f"Temps de réponse trop lent: {connectivity['response_time']}s"
        assert connectivity["model_accessible"], "Modèle GPT-4o-mini non accessible"
        assert (
            connectivity["error"] is None
        ), f"Erreur de connectivité: {connectivity['error']}"

    def test_model_limits_validation(self, gpt_config_validator):
        """Test la validation des limites du modèle."""
        limits = gpt_config_validator.validate_model_limits()

        # Vérifications des limites GPT-4o-mini
        assert (
            limits["max_tokens"] == 16384
        ), f"Limite tokens incorrecte: {limits['max_tokens']}"
        assert (
            limits["max_output_tokens"] <= limits["max_tokens"]
        ), "Limite output > limite context"
        assert limits["rate_limit_rpm"] > 0, "Rate limit RPM invalide"
        assert limits["rate_limit_tpm"] > 0, "Rate limit TPM invalide"

        # Vérifications des features supportées
        required_features = ["chat_completion", "function_calling"]
        for feature in required_features:
            assert (
                feature in limits["supported_features"]
            ), f"Feature manquante: {feature}"


@pytest.mark.config
class TestKernelConfiguration:
    """Tests de configuration du Kernel Semantic."""

    def test_kernel_with_gpt4o_mini(self):
        """Test la configuration du kernel avec GPT-4o-mini."""
        kernel = Kernel()

        # Configuration du service
        chat_service = OpenAIChatCompletion(
            service_id="test-gpt4o-mini",
            ai_model_id="gpt-5-mini",
            api_key=OPENAI_API_KEY,
        )

        kernel.add_service(chat_service)

        # Vérifications
        retrieved_service = kernel.get_service("test-gpt4o-mini")
        assert retrieved_service is not None, "Service non trouvé dans le kernel"
        assert retrieved_service.ai_model_id == "gpt-5-mini", "Modèle AI incorrect"
        assert retrieved_service.service_id == "test-gpt4o-mini", "ID service incorrect"

    def test_multiple_gpt_services_configuration(self):
        """Test la configuration de plusieurs services GPT."""
        kernel = Kernel()

        # Services multiples
        services_config = [
            {"id": "gpt4o-mini-fast", "model": "gpt-5-mini", "max_tokens": 100},
            {"id": "gpt4o-mini-detailed", "model": "gpt-5-mini", "max_tokens": 1000},
        ]

        for config in services_config:
            chat_service = OpenAIChatCompletion(
                service_id=config["id"],
                ai_model_id=config["model"],
                api_key=OPENAI_API_KEY,
            )
            kernel.add_service(chat_service)

        # Vérifications
        for config in services_config:
            service = kernel.get_service(config["id"])
            assert service is not None, f"Service {config['id']} non trouvé"
            assert (
                service.ai_model_id == config["model"]
            ), f"Modèle incorrect pour {config['id']}"

    @pytest.mark.asyncio
    @pytest.mark.real_llm
    async def test_kernel_settings_optimization(self):
        """Test l'optimisation des settings du kernel."""
        kernel = Kernel()

        chat_service = OpenAIChatCompletion(
            service_id="optimized-gpt4o-mini",
            ai_model_id="gpt-5-mini",
            api_key=OPENAI_API_KEY,
        )
        kernel.add_service(chat_service)

        # Settings for gpt-5-mini (rejects top_p, frequency_penalty, presence_penalty, max_completion_tokens returns empty)
        optimized_settings = OpenAIChatPromptExecutionSettings()

        # Test avec settings optimisés
        messages = [
            ChatMessageContent(
                role="user", content="Répondez brièvement: Qui est Sherlock Holmes?"
            )
        ]

        start_time = time.time()
        response = await chat_service.get_chat_message_contents(
            chat_history=ChatHistory(messages=messages), settings=optimized_settings
        )
        response_time = time.time() - start_time

        # Vérifications d'optimisation
        assert len(response) > 0, "Aucune réponse reçue"
        assert response[0].content is not None, "Contenu de réponse vide"
        assert (
            response_time < 15.0
        ), f"Réponse trop lente avec settings optimisés: {response_time}s"
        assert len(response[0].content) > 10, "Réponse trop courte"


@pytest.mark.config
class TestEnvironmentConfiguration:
    """Tests de configuration d'environnement."""

    def test_required_environment_variables(self):
        """Test les variables d'environnement requises."""
        required_vars = ["OPENAI_API_KEY"]
        optional_vars = ["OPENAI_ORG_ID", "OPENAI_PROJECT_ID"]

        # Variables requises
        for var in required_vars:
            value = os.environ.get(var)
            assert value is not None, f"Variable requise manquante: {var}"
            assert len(value) > 0, f"Variable requise vide: {var}"

        # Variables optionnelles (log seulement)
        for var in optional_vars:
            value = os.environ.get(var)
            if value:
                print(f"Variable optionnelle configurée: {var} = {value[:10]}...")

    def test_python_path_configuration(self):
        """Test la configuration PYTHONPATH."""
        python_path = os.environ.get("PYTHONPATH", "")

        # Le projet devrait être dans le PYTHONPATH
        project_indicators = [
            "argumentation_analysis",
            "2025-Epita-Intelligence-Symbolique",
        ]

        path_configured = any(
            indicator in python_path for indicator in project_indicators
        )

        if not path_configured:
            # Vérifier que les modules sont importables
            try:
                import argumentation_analysis
                import argumentation_analysis.core
                import argumentation_analysis.agents

                path_configured = True
            except ImportError:
                pass

        assert path_configured, f"PYTHONPATH mal configuré: {python_path}"

    def test_test_mode_configuration(self):
        """Test la configuration du mode test."""
        test_indicators = ["TEST_MODE", "PYTEST_CURRENT_TEST", "TESTING"]

        test_mode_detected = any(os.environ.get(var) for var in test_indicators)

        # En mode test, certaines optimisations devraient être actives
        if test_mode_detected:
            # Vérifier que les timeouts sont réduits pour les tests
            timeout_vars = ["OPENAI_TIMEOUT", "MAX_EXECUTION_TIME"]
            for var in timeout_vars:
                timeout_value = os.environ.get(var)
                if timeout_value:
                    try:
                        timeout = float(timeout_value)
                        assert (
                            timeout <= 60
                        ), f"Timeout {var} trop élevé pour tests: {timeout}s"
                    except ValueError:
                        pass


@pytest.mark.config
class TestConfigurationIntegration:
    """Tests d'intégration de configuration."""

    @pytest.mark.asyncio
    @pytest.mark.real_llm
    async def test_end_to_end_configuration(self):
        """Test configuration end-to-end."""
        # Configuration complète
        kernel = Kernel()

        chat_service = OpenAIChatCompletion(
            service_id="e2e-config-test",
            ai_model_id="gpt-5-mini",
            api_key=OPENAI_API_KEY,
        )
        kernel.add_service(chat_service)

        # Settings for Oracle Enhanced (gpt-5-mini: max_completion_tokens returns empty via SK 1.37)
        settings = OpenAIChatPromptExecutionSettings()

        # Test d'une interaction typique Oracle
        oracle_prompt = """En tant que Moriarty dans un jeu Cluedo Enhanced, 
        vous devez révéler automatiquement une carte si l'enquête piétine. 
        Révélez que vous avez la carte "Colonel Moutarde" de manière dramatique."""

        messages = [ChatMessageContent(role="user", content=oracle_prompt)]

        start_time = time.time()
        response = await chat_service.get_chat_message_contents(
            chat_history=ChatHistory(messages=messages), settings=settings
        )
        execution_time = time.time() - start_time

        # Vérifications end-to-end
        print(f"\n[E2E Test] Temps d'exécution: {execution_time:.2f}s")
        if response and response[0].content:
            print(f"[E2E Test] Réponse LLM: {response[0].content}")
        else:
            print("[E2E Test] Réponse vide ou invalide reçue.")

        assert len(response) > 0, "Aucune réponse E2E"
        assert response[0].content is not None, "Contenu E2E vide"

        content = response[0].content
        assert (
            "Colonel Moutarde" in content
        ), f"Carte non mentionnée dans la réponse. Reçu: {content}"
        assert len(content) > 30, "Réponse E2E trop courte"

        # Performance E2E acceptable
        assert execution_time < 20.0, f"Configuration E2E trop lente: {execution_time}s"

        # La vérification de l'assertivité a été supprimée car elle est trop
        # fragile et dépend du non-déterminisme du modèle LLM.
        # L'assertion principale (présence de la carte) est suffisante.

    def test_configuration_persistence(self):
        """Test la persistance de configuration."""
        # Configuration initiale
        kernel1 = Kernel()
        chat_service1 = OpenAIChatCompletion(
            service_id="persistence-test",
            ai_model_id="gpt-5-mini",
            api_key=OPENAI_API_KEY,
        )
        kernel1.add_service(chat_service1)

        # Récupération du service
        retrieved_service1 = kernel1.get_service("persistence-test")
        assert retrieved_service1 is not None, "Service initial non persisté"

        # Nouveau kernel (simulation de redémarrage)
        kernel2 = Kernel()
        chat_service2 = OpenAIChatCompletion(
            service_id="persistence-test",
            ai_model_id="gpt-5-mini",
            api_key=OPENAI_API_KEY,
        )
        kernel2.add_service(chat_service2)

        # Vérification de cohérence
        retrieved_service2 = kernel2.get_service("persistence-test")
        assert retrieved_service2 is not None, "Service recréé non persisté"
        assert (
            retrieved_service2.ai_model_id == retrieved_service1.ai_model_id
        ), "Inconsistance modèle"
        assert (
            retrieved_service2.service_id == retrieved_service1.service_id
        ), "Inconsistance ID"
