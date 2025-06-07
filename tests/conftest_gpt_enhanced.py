"""
Configuration pytest pour tests GPT-4o-mini Enhanced.

Extension de conftest.py pour supporter :
- Configuration OpenAI API key depuis environnement
- Setup/teardown Semantic Kernel agents réels
- Fixtures GPT-4o-mini avec rate limiting
- Configuration logging détaillé pour debugging
"""

import os
import sys
import pytest
import asyncio
import time
import logging
from typing import Dict, Any, Optional
from unittest.mock import Mock, AsyncMock

# Imports Semantic Kernel
try:
    from semantic_kernel.kernel import Kernel
    from semantic_kernel.services.openai import OpenAIChatCompletion
    from semantic_kernel.connectors.ai.open_ai import OpenAIChatPromptExecutionSettings
    from semantic_kernel.contents.chat_message_content import ChatMessageContent
    SEMANTIC_KERNEL_AVAILABLE = True
except ImportError:
    SEMANTIC_KERNEL_AVAILABLE = False

# Imports du système Oracle
try:
    from argumentation_analysis.orchestration.cluedo_extended_orchestrator import CluedoExtendedOrchestrator
    from argumentation_analysis.core.cluedo_oracle_state import CluedoOracleState
    from argumentation_analysis.agents.core.oracle.moriarty_interrogator_agent import MoriartyInterrogatorAgent
    ORACLE_SYSTEM_AVAILABLE = True
except ImportError:
    ORACLE_SYSTEM_AVAILABLE = False


# Configuration GPT-4o-mini
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
REAL_GPT_AVAILABLE = OPENAI_API_KEY is not None and len(OPENAI_API_KEY) > 10
USE_REAL_GPT = os.environ.get('USE_REAL_GPT', 'false').lower() == 'true'

# Configuration logging pour debugging
logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter pour respecter les limites OpenAI."""
    
    def __init__(self, requests_per_minute: int = 500, tokens_per_minute: int = 200000):
        self.requests_per_minute = requests_per_minute
        self.tokens_per_minute = tokens_per_minute
        self.request_times = []
        self.token_usage = []
        self.last_request_time = 0
    
    async def wait_if_needed(self, estimated_tokens: int = 100):
        """Attend si nécessaire pour respecter les rate limits."""
        current_time = time.time()
        
        # Nettoyage des anciens records (> 1 minute)
        cutoff_time = current_time - 60
        self.request_times = [t for t in self.request_times if t > cutoff_time]
        self.token_usage = [(t, tokens) for t, tokens in self.token_usage if t > cutoff_time]
        
        # Vérification rate limit requêtes
        if len(self.request_times) >= self.requests_per_minute:
            wait_time = 60 - (current_time - self.request_times[0])
            if wait_time > 0:
                logger.info(f"Rate limit requêtes: attente {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
        
        # Vérification rate limit tokens
        current_tokens = sum(tokens for _, tokens in self.token_usage)
        if current_tokens + estimated_tokens > self.tokens_per_minute:
            wait_time = 60 - (current_time - self.token_usage[0][0])
            if wait_time > 0:
                logger.info(f"Rate limit tokens: attente {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
        
        # Attente minimale entre requêtes
        min_interval = 0.1  # 100ms minimum
        time_since_last = current_time - self.last_request_time
        if time_since_last < min_interval:
            await asyncio.sleep(min_interval - time_since_last)
        
        # Enregistrement de la requête
        self.request_times.append(time.time())
        self.token_usage.append((time.time(), estimated_tokens))
        self.last_request_time = time.time()


class GPTTestSession:
    """Gestionnaire de session pour tests GPT-4o-mini."""
    
    def __init__(self):
        self.kernels = {}
        self.rate_limiter = RateLimiter()
        self.test_count = 0
        self.total_tokens_used = 0
        self.errors = []
        self.start_time = time.time()
    
    def create_kernel(self, service_id: str = "test-gpt4o-mini") -> Optional[Kernel]:
        """Crée un kernel Semantic avec GPT-4o-mini."""
        if not REAL_GPT_AVAILABLE or not SEMANTIC_KERNEL_AVAILABLE:
            return None
        
        try:
            kernel = Kernel()
            
            chat_service = OpenAIChatCompletion(
                service_id=service_id,
                ai_model_id="gpt-4o-mini",
                api_key=OPENAI_API_KEY
            )
            
            kernel.add_service(chat_service)
            self.kernels[service_id] = kernel
            
            logger.info(f"Kernel GPT-4o-mini créé: {service_id}")
            return kernel
            
        except Exception as e:
            logger.error(f"Erreur création kernel {service_id}: {e}")
            self.errors.append(f"Kernel creation failed: {e}")
            return None
    
    async def test_connection(self, kernel: Kernel, service_id: str) -> bool:
        """Test la connexion GPT-4o-mini."""
        try:
            await self.rate_limiter.wait_if_needed(50)
            
            chat_service = kernel.get_service(service_id)
            if not chat_service:
                return False
            
            settings = OpenAIChatPromptExecutionSettings(
                max_tokens=20,
                temperature=0.1
            )
            
            messages = [ChatMessageContent(role="user", content="Test connection")]
            
            response = await chat_service.get_chat_message_contents(
                chat_history=messages,
                settings=settings
            )
            
            self.test_count += 1
            self.total_tokens_used += 25  # Estimation
            
            return len(response) > 0 and response[0].content is not None
            
        except Exception as e:
            logger.error(f"Test connexion échoué {service_id}: {e}")
            self.errors.append(f"Connection test failed: {e}")
            return False
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de session."""
        duration = time.time() - self.start_time
        
        return {
            'duration': duration,
            'test_count': self.test_count,
            'total_tokens_used': self.total_tokens_used,
            'kernels_created': len(self.kernels),
            'errors': len(self.errors),
            'avg_tokens_per_test': self.total_tokens_used / max(self.test_count, 1),
            'tests_per_minute': (self.test_count * 60) / max(duration, 1)
        }
    
    def cleanup(self):
        """Nettoyage de session."""
        logger.info(f"Nettoyage session GPT: {len(self.kernels)} kernels")
        self.kernels.clear()


# Instance globale de session
gpt_session = GPTTestSession()


# Fixtures GPT-4o-mini Enhanced

@pytest.fixture(scope="session")
def gpt_test_session():
    """Session globale pour tests GPT-4o-mini."""
    yield gpt_session
    
    # Cleanup à la fin de la session
    stats = gpt_session.get_session_stats()
    logger.info(f"Session GPT terminée: {stats}")
    gpt_session.cleanup()


@pytest.fixture
def real_gpt_kernel(gpt_test_session):
    """Kernel Semantic Kernel avec vraie connexion GPT-4o-mini."""
    if not REAL_GPT_AVAILABLE:
        pytest.skip("OPENAI_API_KEY requis pour tests GPT réels")
    
    if not USE_REAL_GPT:
        pytest.skip("Tests GPT réels désactivés (USE_REAL_GPT=false)")
    
    kernel = gpt_test_session.create_kernel("pytest-real-gpt")
    
    if kernel is None:
        pytest.skip("Impossible de créer kernel GPT-4o-mini")
    
    return kernel


@pytest.fixture
async def validated_gpt_kernel(real_gpt_kernel, gpt_test_session):
    """Kernel GPT-4o-mini avec connexion validée."""
    connection_ok = await gpt_test_session.test_connection(
        real_gpt_kernel, 
        "pytest-real-gpt"
    )
    
    if not connection_ok:
        pytest.skip("Connexion GPT-4o-mini non validée")
    
    return real_gpt_kernel


@pytest.fixture
def gpt_rate_limiter(gpt_test_session):
    """Rate limiter pour tests GPT."""
    return gpt_test_session.rate_limiter


@pytest.fixture
def mock_gpt_kernel():
    """Kernel mocké pour tests sans frais GPT."""
    kernel = Mock(spec=Kernel)
    kernel.add_service = Mock()
    
    # Mock du service
    mock_service = AsyncMock()
    mock_service.service_id = "mock-gpt4o-mini"
    mock_service.ai_model_id = "gpt-4o-mini"
    
    # Mock des réponses
    async def mock_get_chat_message_contents(chat_history=None, settings=None):
        await asyncio.sleep(0.1)  # Simulation latence
        
        content = "Mock response from GPT-4o-mini"
        if chat_history and len(chat_history) > 0:
            user_content = chat_history[-1].content.lower()
            
            if "moriarty" in user_content and "révèle" in user_content:
                content = "En tant que Moriarty, je révèle que j'ai la carte Colonel Moutarde!"
            elif "sherlock" in user_content:
                content = "En tant que Sherlock, j'enquête méthodiquement sur cette affaire."
            elif "watson" in user_content:
                content = "En tant que Watson, j'analyse logiquement les indices disponibles."
        
        mock_response = Mock()
        mock_response.content = content
        return [mock_response]
    
    mock_service.get_chat_message_contents = mock_get_chat_message_contents
    kernel.get_service = Mock(return_value=mock_service)
    
    return kernel


@pytest.fixture
def oracle_test_elements():
    """Éléments de test optimisés pour Oracle Enhanced."""
    return {
        "suspects": ["Colonel Moutarde", "Professeur Violet", "Mademoiselle Rose"],
        "armes": ["Poignard", "Chandelier", "Revolver"],
        "lieux": ["Salon", "Cuisine", "Bureau"]
    }


@pytest.fixture
async def enhanced_orchestrator(validated_gpt_kernel, oracle_test_elements):
    """Orchestrateur Enhanced avec GPT-4o-mini réel."""
    if not ORACLE_SYSTEM_AVAILABLE:
        pytest.skip("Système Oracle non disponible")
    
    orchestrator = CluedoExtendedOrchestrator(
        kernel=validated_gpt_kernel,
        max_turns=5,
        max_cycles=2,
        oracle_strategy="enhanced_auto_reveal"
    )
    
    # Setup optionnel pour tests rapides
    setup_requested = os.environ.get('QUICK_SETUP', 'false').lower() == 'true'
    if setup_requested:
        await orchestrator.setup_workflow(
            nom_enquete="Quick Test Enhanced",
            elements_jeu=oracle_test_elements
        )
    
    return orchestrator


@pytest.fixture
def mock_enhanced_orchestrator(mock_gpt_kernel, oracle_test_elements):
    """Orchestrateur Enhanced avec kernel mocké."""
    if not ORACLE_SYSTEM_AVAILABLE:
        pytest.skip("Système Oracle non disponible")
    
    orchestrator = CluedoExtendedOrchestrator(
        kernel=mock_gpt_kernel,
        max_turns=5,
        max_cycles=2,
        oracle_strategy="enhanced_auto_reveal"
    )
    
    return orchestrator


# Configuration pytest pour GPT Enhanced

def pytest_configure(config):
    """Configuration pytest pour tests GPT Enhanced."""
    # Markers personnalisés
    config.addinivalue_line(
        "markers", "real_gpt: tests nécessitant une vraie connexion GPT-4o-mini"
    )
    config.addinivalue_line(
        "markers", "enhanced: tests spécifiques Oracle Enhanced"
    )
    config.addinivalue_line(
        "markers", "expensive: tests coûteux en tokens GPT"
    )
    config.addinivalue_line(
        "markers", "slow: tests lents (>30s)"
    )
    
    # Configuration logging Enhanced
    if config.getoption("--log-level") is None:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] [GPT-Enhanced] %(name)s: %(message)s',
            datefmt='%H:%M:%S'
        )


def pytest_collection_modifyitems(config, items):
    """Modification de la collection de tests."""
    # Skip automatique des tests réels si pas d'API key
    if not REAL_GPT_AVAILABLE:
        real_gpt_marker = pytest.mark.skip(reason="OPENAI_API_KEY requis")
        for item in items:
            if "real_gpt" in item.keywords:
                item.add_marker(real_gpt_marker)
    
    # Skip des tests coûteux si mode économique
    if os.environ.get('ECONOMICAL_MODE', 'false').lower() == 'true':
        expensive_marker = pytest.mark.skip(reason="Mode économique activé")
        for item in items:
            if "expensive" in item.keywords:
                item.add_marker(expensive_marker)


def pytest_sessionstart(session):
    """Début de session pytest."""
    logger.info("=== DÉBUT SESSION TESTS GPT-4O-MINI ENHANCED ===")
    logger.info(f"API Key disponible: {REAL_GPT_AVAILABLE}")
    logger.info(f"Utilisation GPT réel: {USE_REAL_GPT}")
    logger.info(f"Semantic Kernel disponible: {SEMANTIC_KERNEL_AVAILABLE}")
    logger.info(f"Système Oracle disponible: {ORACLE_SYSTEM_AVAILABLE}")


def pytest_sessionfinish(session, exitstatus):
    """Fin de session pytest."""
    stats = gpt_session.get_session_stats()
    
    logger.info("=== FIN SESSION TESTS GPT-4O-MINI ENHANCED ===")
    logger.info(f"Durée: {stats['duration']:.2f}s")
    logger.info(f"Tests GPT: {stats['test_count']}")
    logger.info(f"Tokens utilisés: {stats['total_tokens_used']}")
    logger.info(f"Kernels créés: {stats['kernels_created']}")
    logger.info(f"Erreurs: {stats['errors']}")
    
    if stats['test_count'] > 0:
        logger.info(f"Moyenne tokens/test: {stats['avg_tokens_per_test']:.1f}")
        logger.info(f"Tests/minute: {stats['tests_per_minute']:.1f}")
    
    # Estimation coût (GPT-4o-mini: ~$0.15/1M tokens input, ~$0.60/1M tokens output)
    estimated_cost = (stats['total_tokens_used'] * 0.000375)  # Estimation mixte
    logger.info(f"Coût estimé: ${estimated_cost:.4f}")


# Helpers pour tests GPT Enhanced

def create_test_oracle_state(elements_jeu: Dict[str, Any]) -> Optional[CluedoOracleState]:
    """Crée un état Oracle pour tests."""
    if not ORACLE_SYSTEM_AVAILABLE:
        return None
    
    try:
        return CluedoOracleState(
            nom_enquete_cluedo="Test Enhanced",
            elements_jeu_cluedo=elements_jeu,
            oracle_strategy="enhanced_auto_reveal"
        )
    except Exception as e:
        logger.error(f"Erreur création état Oracle: {e}")
        return None


async def create_gpt_prompt_for_test(role: str, context: str) -> str:
    """Crée un prompt optimisé pour tests GPT."""
    prompts = {
        "sherlock": f"En tant que Sherlock Holmes dans {context}, enquêtez brièvement et méthodiquement.",
        "watson": f"En tant que Dr Watson dans {context}, analysez logiquement les indices disponibles.",
        "moriarty": f"En tant que Moriarty dans {context}, révélez dramatiquement un indice crucial."
    }
    
    return prompts.get(role, f"Dans le contexte {context}, répondez brièvement et de manière pertinente.")


def validate_gpt_response_for_oracle(response: str, expected_role: str) -> Dict[str, Any]:
    """Valide une réponse GPT pour Oracle Enhanced."""
    validation = {
        'valid_length': len(response) > 20,
        'contains_role': expected_role.lower() in response.lower(),
        'is_assertive': not any(word in response.lower() for word in ['peut-être', 'probablement', 'je pense']),
        'has_content': len(response.strip()) > 0,
        'appropriate_tone': True  # À améliorer selon les besoins
    }
    
    validation['overall_valid'] = all(validation.values())
    
    return validation