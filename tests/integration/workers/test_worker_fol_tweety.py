# tests/integration/workers/test_worker_fol_tweety.py
"""
Tests d'intégration pour le FirstOrderLogicAgent avec une connexion réelle à Tweety.

Ces tests valident les fonctionnalités de bout en bout de l'agent, notamment :
- La conversion de texte en un BeliefSet FOL valide.
- La détection de la cohérence et de l'incohérence.
- L'exécution de requêtes sur le BeliefSet.
- La robustesse face à des entrées invalides.
"""

import pytest
import pytest_asyncio
import asyncio
import os
import logging

# Configuration du logging pour les tests
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import des composants nécessaires
from semantic_kernel import Kernel
from config.unified_config import UnifiedConfig
from argumentation_analysis.agents.core.logic.first_order_logic_agent import FirstOrderLogicAgent as FOLLogicAgent
from argumentation_analysis.agents.core.logic.belief_set import FirstOrderBeliefSet

# Vérifie si la connexion à Tweety est possible
try:
    from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge
    TWEETY_AVAILABLE = True
except ImportError:
    TWEETY_AVAILABLE = False
    logger.warning("TweetyBridge non trouvé. Certains tests d'intégration seront ignorés.")

# Marqueur pour ignorer les tests si Tweety n'est pas configuré pour une utilisation réelle
skip_if_no_real_tweety = pytest.mark.skipif(
    not (TWEETY_AVAILABLE and os.getenv("USE_REAL_JPYPE", "false").lower() == "true"),
    reason="Ces tests nécessitent une connexion JVM réelle à Tweety (USE_REAL_JPYPE=true)."
)


# ==================== FIXTURES DE TEST ====================

@pytest_asyncio.fixture(scope="module")
async def fol_agent(jvm_session) -> FOLLogicAgent:
    """
    Fixture de scope 'module' pour créer et configurer une instance de FOLLogicAgent.
    L'agent est partagé entre tous les tests de ce module pour des raisons de performance,
    évitant de recréer le kernel et la connexion JVM à chaque test.
    """
    logger.info("--- Initialisation de la fixture 'fol_agent' (scope: module) ---")
    
    config = UnifiedConfig()
    kernel = config.get_kernel_with_gpt4o_mini()
    
    # S'assure que le service LLM est bien configuré dans le kernel
    try:
        kernel.get_service("default")
    except Exception:
        pytest.skip("Le service 'default' n'est pas configuré dans le kernel. Impossible de lancer les tests.")

    # S'assurer que la dépendance à la JVM est satisfaite avant de continuer.
    if jvm_session is None:
        pytest.skip("La fixture 'jvm_session' n'a pas pu démarrer la JVM.")

    # Crée l'agent
    agent = FOLLogicAgent(kernel=kernel, service_id="default")

    # La configuration des composants ne devrait plus démarrer la JVM,
    # car la fixture `jvm_session` s'en est déjà occupée.
    # L'appel reste nécessaire pour initialiser d'autres parties de l'agent.
    if TWEETY_AVAILABLE:
        try:
            # L'appel à setup_agent_components va utiliser la JVM déjà démarrée.
            await agent.setup_agent_components()
        except Exception as e:
            pytest.fail(f"La configuration des composants de l'agent a échoué, même avec une JVM pré-démarrée: {e}")
    
    yield agent
    
    logger.info("--- Nettoyage de la fixture 'fol_agent' ---")
    # Aucun nettoyage explicite nécessaire, la JVM est gérée par le TweetyBridge.


# ==================== TESTS D'INTÉGRATION ====================

@skip_if_no_real_tweety
class TestFOLAgentIntegration:
    """Groupe de tests pour l'intégration de bout en bout du FOLLogicAgent."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("text, expected_substrings", [
        (
            "Tous les hommes sont mortels. Socrate est un homme.", 
            ["forall(X, implies(man(X), mortal(X)))", "man(socrates)"]
        ),
        (
            "Tweety est un oiseau. Les oiseaux volent.",
            ["bird(tweety)", "forall(X, implies(bird(X), flies(X)))"]
        ),
        (
            "Il existe un étudiant qui est brillant.",
            ["exists(X, and(student(X), brilliant(X)))"]
        )
    ])
    async def test_text_to_belief_set_syllogisms_classiques(self, fol_agent: FOLLogicAgent, text: str, expected_substrings: list):
        """
        Teste la capacité de l'agent à convertir des syllogismes simples en BeliefSet FOL corrects.
        """
        logger.info(f"Test de conversion pour le texte : '{text}'")
        
        belief_set, status = await fol_agent.text_to_belief_set(text)

        assert belief_set is not None, f"La conversion a échoué avec le statut : {status}"
        assert isinstance(belief_set, FirstOrderBeliefSet)
        assert belief_set.content is not None
        
        for sub in expected_substrings:
            assert sub in belief_set.content

        # La cohérence doit être vérifiée car les énoncés sont simples et cohérents
        is_consistent, _ = await fol_agent.is_consistent(belief_set)
        assert is_consistent is True

    @pytest.mark.asyncio
    async def test_is_consistent_sur_belief_set_coherent(self, fol_agent: FOLLogicAgent):
        """
        Vérifie que la méthode is_consistent retourne True pour un ensemble de croyances cohérent.
        """
        text = "Les planètes tournent autour du soleil. La Terre est une planète."
        belief_set, status = await fol_agent.text_to_belief_set(text)
        
        assert belief_set is not None, f"La conversion a échoué: {status}"

        is_consistent, details = await fol_agent.is_consistent(belief_set)
        
        assert is_consistent is True
        logger.info(f"Vérification de cohérence réussie : {details}")

    @pytest.mark.asyncio
    async def test_is_consistent_sur_belief_set_incoherent(self, fol_agent: FOLLogicAgent):
        """
        Vérifie que la méthode is_consistent retourne False pour un ensemble de croyances incohérent.
        """
        text = "Tous les oiseaux peuvent voler. Un pingouin est un oiseau. Un pingouin ne peut pas voler."
        belief_set, status = await fol_agent.text_to_belief_set(text)
        
        assert belief_set is not None, f"La conversion a échoué: {status}"

        is_consistent, details = await fol_agent.is_consistent(belief_set)

        assert is_consistent is False
        logger.info(f"Détection d'incohérence réussie : {details}")

    @pytest.mark.asyncio
    async def test_execute_query_entailed(self, fol_agent: FOLLogicAgent):
        """
        Teste que execute_query retourne True pour une requête qui est une conséquence logique.
        """
        text = "Tous les hommes sont mortels. Socrate est un homme."
        belief_set, status = await fol_agent.text_to_belief_set(text)
        assert belief_set is not None, f"La conversion a échoué: {status}"

        query = "mortal(socrates)"
        entailed, result_str = await fol_agent.execute_query(belief_set, query)

        assert entailed is True
        assert result_str == "ENTAILED"

    @pytest.mark.asyncio
    async def test_execute_query_not_entailed(self, fol_agent: FOLLogicAgent):
        """
        Teste que execute_query retourne False pour une requête qui n'est pas une conséquence logique.
        """
        text = "Tous les chats aiment le poisson. Felix est un chat."
        belief_set, status = await fol_agent.text_to_belief_set(text)
        assert belief_set is not None, f"La conversion a échoué: {status}"

        # On ne peut pas déduire que Felix aime les chiens
        query = "likes(felix, dogs)"
        entailed, result_str = await fol_agent.execute_query(belief_set, query)

        assert entailed is False
        assert result_str == "NOT_ENTAILED"

    @pytest.mark.asyncio
    async def test_gestion_texte_invalide(self, fol_agent: FOLLogicAgent):
        """
        Teste que l'agent gère gracieusement un texte qui ne peut pas être traduit en FOL.
        """
        text = "Ceci est une phrase sans signification logique claire pour la conversion."
        belief_set, status = await fol_agent.text_to_belief_set(text)

        assert belief_set is None
        assert "aucune structure logique" in status.lower()

    @pytest.mark.asyncio
    async def test_stabilite_sur_analyses_multiples(self, fol_agent: FOLLogicAgent):
        """
        Teste la stabilité de l'agent en effectuant plusieurs analyses consécutives.
        Ceci permet de s'assurer qu'il n'y a pas de fuite de mémoire ou d'état résiduel.
        """
        test_texts = [
            "Les chiens sont des mammifères.",
            "Il pleut aujourd'hui.",
            "Si un animal est un chat, alors il miaule."
        ]
        for text in test_texts:
            logger.info(f"Analyse de stabilité pour : '{text}'")
            belief_set, status = await fol_agent.text_to_belief_set(text)
            assert belief_set is not None, f"L'analyse a échoué pour '{text}': {status}"
            is_consistent, _ = await fol_agent.is_consistent(belief_set)
            assert is_consistent is True


if __name__ == "__main__":
    # Commande pour exécuter les tests avec pytest
    pytest.main([
        __file__, 
        "-v", 
        "--tb=short"
    ])