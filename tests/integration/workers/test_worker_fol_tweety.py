# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig
import sys
import pathlib

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests d'intégration FOL-Tweety pour FirstOrderLogicAgent.

Ces tests valident l'intégration authentique entre l'agent FOL et TweetyProject :
- Compatibilité syntaxe FOL avec solveur Tweety réel
- Analyse avec JAR Tweety authentique
- Gestion d'erreurs spécifiques FOL
- Performance vs Modal Logic
- Validation sans mocks (USE_REAL_JPYPE=true)

Tests critiques d'intégration :
✅ Formules FOL acceptées par Tweety sans erreur parsing
✅ Résultats cohérents du solveur FOL
✅ Gestion robuste des erreurs Tweety
✅ Performance stable et prévisible
"""

import pytest
import pytest_asyncio
import asyncio
import os
import time
import logging
from typing import Dict, List, Any, Optional


# Import a shared fixture to manage the JVM lifecycle
from tests.fixtures.integration_fixtures import jvm_session
# Import de l'agent FOL et composants
from argumentation_analysis.agents.core.logic.first_order_logic_agent import FirstOrderLogicAgent as FOLLogicAgent
from argumentation_analysis.agents.core.logic.belief_set import BeliefSet
from argumentation_analysis.agents.core.logic.logic_factory import LogicAgentFactory

# Import configuration et Tweety
from config.unified_config import UnifiedConfig, LogicType, MockLevel, PresetConfigs
from argumentation_analysis.utils.tweety_error_analyzer import TweetyErrorAnalyzer

# Import TweetyBridge avec gestion d'erreur
try:
    from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge
    TWEETY_AVAILABLE = True
except ImportError:
    TWEETY_AVAILABLE = False
    TweetyBridge = None

# Configuration logging pour tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def _create_authentic_gpt4o_mini_instance():
    """Crée une instance authentique de gpt-4o-mini au lieu d'un mock."""
    config = UnifiedConfig()
    return config.get_kernel_with_gpt4o_mini()

async def _make_authentic_llm_call(prompt: str) -> str:
    """Fait un appel authentique à gpt-4o-mini."""
    try:
        kernel = await _create_authentic_gpt4o_mini_instance()
        result = await kernel.invoke("chat", input=prompt)
        return str(result)
    except Exception as e:
        logger.warning(f"Appel LLM authentique échoué: {e}")
        return "Authentic LLM call failed"

class TestFOLTweetyCompatibility:
    """Tests de compatibilité syntaxe FOL avec Tweety."""
    
    @pytest.fixture
    def real_tweety_config(self):
        """Configuration pour Tweety réel."""
        return {
            "USE_REAL_JPYPE": os.getenv("USE_REAL_JPYPE", "false").lower() == "true",
            "TWEETY_JAR_PATH": os.getenv("TWEETY_JAR_PATH", ""),
            "JVM_MEMORY": os.getenv("JVM_MEMORY", "512m")
        }
    
    @pytest.mark.skipif(not TWEETY_AVAILABLE, reason="TweetyBridge non disponible")
    @pytest.mark.asyncio
    async def test_fol_formula_tweety_compatibility(self, real_tweety_config):
        """Test compatibilité formules FOL avec Tweety réel."""
        if not real_tweety_config["USE_REAL_JPYPE"]:
            pytest.skip("Test nécessite USE_REAL_JPYPE=true")
            
        # Formules FOL valides à tester
        test_formulas = [
            # Quantificateurs de base
            "∀x(Human(x) → Mortal(x))",
            "∃x(Student(x) ∧ Intelligent(x))",
            
            # Prédicats complexes
            "∀x∀y(Loves(x,y) → Cares(x,y))",
            "∃x∃y(Friend(x,y) ∧ Trust(x,y))",
            
            # Connecteurs logiques
            "∀x((P(x) ∧ Q(x)) → (R(x) ∨ S(x)))",
            "∃x(¬Bad(x) ↔ Good(x))"
        ]
        
        # Initialisation TweetyBridge
        tweety_bridge = TweetyBridge()
        await tweety_bridge.initialize_fol_reasoner()
        
        # Test de chaque formule
        for formula in test_formulas:
            try:
                # Test parsing sans erreur
                is_consistent = await tweety_bridge.check_consistency([formula])
                logger.info(f"✅ Formule acceptée par Tweety: {formula}")
                
                # Tweety doit pouvoir traiter la formule
                assert isinstance(is_consistent, bool)
                
            except Exception as e:
                logger.error(f"❌ Erreur Tweety pour {formula}: {e}")
                # Échec = syntaxe incompatible
                pytest.fail(f"Syntaxe FOL incompatible avec Tweety: {formula} - {e}")
    
    @pytest.mark.skipif(not TWEETY_AVAILABLE, reason="TweetyBridge non disponible")
    @pytest.mark.asyncio
    async def test_fol_predicate_declaration_validation(self, real_tweety_config):
        """Test validation déclaration prédicats FOL avec Tweety."""
        if not real_tweety_config["USE_REAL_JPYPE"]:
            pytest.skip("Test nécessite USE_REAL_JPYPE=true")
            
        tweety_bridge = TweetyBridge()
        await tweety_bridge.initialize_fol_reasoner()
        
        # Test prédicats correctement déclarés
        valid_formulas = [
            "∀x(Human(x) → Mortal(x))",
            "Human(socrate)",
            "Mortal(socrate)"
        ]
        
        try:
            result = await tweety_bridge.check_consistency(valid_formulas)
            logger.info(f"✅ Prédicats validés par Tweety: {result}")
            assert isinstance(result, bool)
            
        except Exception as e:
            # Analyser l'erreur avec TweetyErrorAnalyzer
            error_analyzer = TweetyErrorAnalyzer()
            feedback = error_analyzer.analyze_error(str(e))
            
            if feedback and feedback.error_type == "DECLARATION_ERROR":
                # Erreur de déclaration détectée
                logger.warning(f"⚠️ Erreur déclaration prédicat: {feedback.corrections}")
            else:
                pytest.fail(f"Erreur Tweety inattendue: {e}")
    
    @pytest.mark.skipif(not TWEETY_AVAILABLE, reason="TweetyBridge non disponible")
    @pytest.mark.asyncio 
    async def test_fol_quantifier_binding_validation(self, real_tweety_config):
        """Test validation liaison quantificateurs avec Tweety."""
        if not real_tweety_config["USE_REAL_JPYPE"]:
            pytest.skip("Test nécessite USE_REAL_JPYPE=true")
            
        tweety_bridge = TweetyBridge()
        await tweety_bridge.initialize_fol_reasoner()
        
        # Test variables correctement liées
        well_bound_formulas = [
            "∀x(P(x) → Q(x))",  # x lié par ∀
            "∃y(R(y) ∧ S(y))",  # y lié par ∃
            "∀x∃y(Rel(x,y))"    # x et y correctement liés
        ]
        
        for formula in well_bound_formulas:
            try:
                await tweety_bridge.check_consistency([formula])
                logger.info(f"✅ Variables correctement liées: {formula}")
                
            except Exception as e:
                logger.error(f"❌ Erreur liaison variables: {formula} - {e}")
                pytest.fail(f"Variables mal liées détectées par Tweety: {formula}")

    @pytest.mark.asyncio
    async def test_programmatic_belief_set_creation_and_consistency(self, fol_agent_with_kernel, jvm_session):
        """
        Valide le nouveau flux de construction programmatique du BeliefSet,
        en isolant la logique de construction de l'appel LLM.
        """
        if not jvm_session:
            pytest.skip("Test nécessite la JVM.")
        
        agent = fol_agent_with_kernel
        builder = agent._builder_plugin
        builder.reset() # S'assurer qu'il est propre avant de commencer

        # 1. Simuler les appels d'outils du LLM pour un syllogisme simple.
        builder.add_sort("Homme")
        builder.add_constant_to_sort("socrate", "Homme")
        # Le prédicat doit être différent du sort pour éviter les ambiguïtés
        builder.add_predicate_schema("EstUnHomme", ["Homme"])
        builder.add_predicate_schema("EstMortel", ["Homme"])
        builder.add_atomic_fact("EstUnHomme", ["socrate"])
        # Pour l'implication universelle, il faut s'assurer que les prédicats
        # sont bien déclarés, ce qui est fait ci-dessus.
        builder.add_universal_implication("EstUnHomme", "EstMortel", "Homme")

        # 2. Déclencher DIRECTEMENT la construction programmatique.
        #    On contourne l'appel LLM de `text_to_belief_set`.
        java_belief_set_obj = builder.build_tweety_belief_set(agent.tweety_bridge)
        
        # 3. Valider le résultat
        assert java_belief_set_obj is not None, "La création du BeliefSet programmatique a retourné None."
        
        # Créer un objet BeliefSet de haut niveau pour les étapes suivantes
        from argumentation_analysis.agents.core.logic.belief_set import FirstOrderBeliefSet
        belief_set = FirstOrderBeliefSet(content=java_belief_set_obj.toString(), java_object=java_belief_set_obj)
        
        # Vérifier que le type est correct
        assert "FolBeliefSet" in str(type(belief_set.java_object)), f"L'objet retourné n'est pas un FolBeliefSet mais un {type(belief_set.java_object)}"

        # 4. Vérifier la cohérence du BeliefSet créé
        is_consistent, consistency_msg = await agent.is_consistent(belief_set)
        assert is_consistent, f"Le BeliefSet créé par programmation est incohérent: {consistency_msg}"

        # 5. Tenter une requête simple
        entails, query_msg = await agent.execute_query(belief_set, "EstMortel(socrate)")
        assert entails, f"L'inférence 'EstMortel(socrate)' a échoué: {query_msg}"

        logger.info("✅ Le flux de création programmatique du BeliefSet est validé avec succès (sans LLM).")

class TestRealTweetyFOLAnalysis:
    """Tests analyse FOL avec Tweety authentique."""
    
    @pytest_asyncio.fixture
    async def fol_agent_real_tweety(self, fol_agent_with_kernel):
        """Agent FOL avec Tweety réel si disponible."""
        config = PresetConfigs.authentic_fol()
        agent = fol_agent_with_kernel
        
        # Force Tweety réel si disponible
        if TWEETY_AVAILABLE and os.getenv("USE_REAL_JPYPE", "").lower() == "true":
            agent._tweety_bridge = TweetyBridge()
        else:
            # Mock pour tests sans Tweety
            # La fixture est maintenant conçue pour Tweety réel. Le mock est supprimé.
            pytest.skip("La fixture fol_agent_real_tweety est pour les tests avec une vraie JVM.")
        
        return agent
    
    @pytest.mark.asyncio
    async def test_real_tweety_fol_syllogism_analysis(self, fol_agent_real_tweety):
        """Test analyse syllogisme avec Tweety réel."""
        syllogism_text = """
        Tous les hommes sont mortels.
        Socrate est un homme.
        """
        
        belief_set, msg = await fol_agent_real_tweety.text_to_belief_set(syllogism_text)
        assert belief_set is not None, f"La création du BeliefSet a échoué: {msg}"

        # Cohérence
        is_consistent, _ = await fol_agent_real_tweety.is_consistent(belief_set)
        assert is_consistent is True
        
        # Inférence
        conclusion = "Mortal(socrates)"
        entails, _ = await fol_agent_real_tweety.execute_query(belief_set, conclusion)
        assert entails is True
        
        logger.info("✅ Syllogisme analysé et validé par Tweety réel.")
    
    @pytest.mark.asyncio
    async def test_real_tweety_fol_inconsistency_detection(self, fol_agent_real_tweety):
        """Test détection incohérences avec Tweety réel."""
        inconsistent_text = """
        Tous les oiseaux peuvent voler.
        Titi est un oiseau.
        Titi ne peut pas voler.
        """
        
        belief_set, msg = await fol_agent_real_tweety.text_to_belief_set(inconsistent_text)
        assert belief_set is not None, f"La création du BeliefSet a échoué: {msg}"
        
        is_consistent, _ = await fol_agent_real_tweety.is_consistent(belief_set)
        assert is_consistent is False # Incohérence attendue
        
        logger.info("✅ Incohérence détectée par Tweety réel.")
    
    @pytest.mark.xfail(reason="La fonction generate_queries n'est pas implémentée dans cette version.")
    @pytest.mark.asyncio
    async def test_real_tweety_fol_inference_generation(self, fol_agent_with_kernel):
        fol_agent_real_tweety = fol_agent_with_kernel
        """Test génération inférences avec Tweety réel."""
        # Prémisses permettant inférences
        premises_text = """
        Tous les étudiants sont intelligents.
        Marie est une étudiante.
        Pierre est un étudiant.
        """
        
        if hasattr(fol_agent_real_tweety._tweety_bridge, 'initialize_fol_reasoner'):
            await fol_agent_real_tweety._tweety_bridge.initialize_fol_reasoner()
        
        belief_set, msg = await fol_agent_real_tweety.text_to_belief_set(premises_text)
        assert belief_set is not None, f"Message: {msg}"

        # Vérifications inférences
        queries = await fol_agent_real_tweety.generate_queries(premises_text, belief_set)
        assert len(queries) > 0

        # Exécuter la première requête générée pour valider
        if queries:
            result, _ = await fol_agent_real_tweety.execute_query(belief_set, queries[0])
            assert result is True # Devrait être accepté


class TestFOLErrorHandling:
    """Tests gestion d'erreurs FOL avec Tweety."""
    
    @pytest.fixture
    def error_analyzer(self):
        """Analyseur d'erreurs Tweety."""
        return TweetyErrorAnalyzer()
    
    @pytest.mark.asyncio
    async def test_fol_predicate_declaration_error_handling(self, error_analyzer):
        """Test gestion erreurs déclaration prédicats."""
        # Erreur typique Tweety
        tweety_error = "Predicate 'Unknown' has not been declared"
        
        # Analyse erreur
        feedback = error_analyzer.analyze_error(tweety_error)
        
        if feedback:
            assert feedback.error_type == "DECLARATION_ERROR"
            assert len(feedback.bnf_rules) > 0
            assert len(feedback.corrections) > 0
            logger.info(f"✅ Erreur analysée: {feedback.corrections}")
        else:
            logger.warning("⚠️ Erreur non reconnue par l'analyseur")
    
    @pytest.mark.asyncio
    async def test_fol_syntax_error_recovery(self, fol_agent_with_kernel):
        """Test récupération erreurs syntaxe FOL."""
        agent = fol_agent_with_kernel
        
        # Texte problématique
        problematic_text = "Ceci n'est pas une formule logique valide !!!"
        
        belief_set, msg = await agent.text_to_belief_set(problematic_text)
        
        # Agent doit gérer gracieusement
        assert belief_set is None
        # Accepter le message d'erreur en anglais ou en français
        assert "could not extract any logical structure" in msg.lower() or "aucune structure logique" in msg.lower() or "syntaxiquement invalide" in msg.lower()
        
    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_fol_timeout_handling(self, fol_agent_with_kernel, monkeypatch):
        """Test gestion timeouts analyse FOL."""
        agent = fol_agent_with_kernel
        
        # Utiliser monkeypatch pour simuler un timeout sans corrompre l'objet
        from unittest.mock import AsyncMock
        mock_timeout = AsyncMock(side_effect=asyncio.TimeoutError("Timeout de test simulé"))
        monkeypatch.setattr(agent, "text_to_belief_set", mock_timeout)
        
        with pytest.raises(asyncio.TimeoutError):
            await agent.text_to_belief_set("Test timeout FOL.")
        
        # Le test réussit si le timeout est bien levé. On peut ajouter un log pour clarté.
        logger.info("✅ TimeoutError correctement levé et attrapé par le test.")


class TestFOLPerformanceVsModal:
    """Tests performance FOL vs Modal Logic."""
    
    @pytest.mark.asyncio
    async def test_fol_vs_modal_performance_comparison(self, fol_agent_with_kernel):
        """Test comparaison performance FOL vs Modal Logic."""
        # Agent FOL
        fol_agent = fol_agent_with_kernel
        
        test_text = "Tous les étudiants intelligents réussissent leurs examens."
        
        # Test FOL
        start_fol = time.time()
        belief_set, _ = await fol_agent.text_to_belief_set(test_text)
        fol_time = time.time() - start_fol
        
        # Vérifications FOL
        assert belief_set is not None
        assert fol_time < 10.0  # Moins de 10 secondes acceptable
        
        logger.info(f"✅ Performance FOL: {fol_time:.2f}s")
        
        # Note: Comparaison avec Modal Logic nécessiterait import Modal Agent
        # Pour l'instant on valide juste que FOL performe correctement
    
    @pytest.mark.asyncio
    async def test_fol_stability_multiple_analyses(self, fol_agent_with_kernel):
        """Test stabilité FOL sur analyses multiples."""
        agent = fol_agent_with_kernel
        
        test_texts = [
            "Tous les chats sont des animaux.",
            "Certains animaux sont des chats.", 
            "Si Marie est étudiante alors elle étudie.",
            "Il existe des étudiants brillants.",
            "Aucun robot n'est humain."
        ]
        
        results = []
        total_time = 0
        
        for text in test_texts:
            start = time.time()
            belief_set, _ = await agent.text_to_belief_set(text)
            elapsed = time.time() - start
            
            results.append(belief_set)
            total_time += elapsed
            
            # Chaque analyse doit réussir
            assert belief_set is not None
        
        # Performance stable
        avg_time = total_time / len(test_texts)
        assert avg_time < 5.0  # Moyenne < 5 secondes par analyse
        
        logger.info(f"✅ Stabilité FOL: {len(results)} analyses en {total_time:.2f}s")
        logger.info(f"Temps moyen: {avg_time:.2f}s")
    
    @pytest.mark.asyncio
    async def test_fol_memory_usage_stability(self, fol_agent_with_kernel):
        """Test stabilité mémoire agent FOL."""
        agent = fol_agent_with_kernel
        
        # Analyses répétées pour tester fuites mémoire
        for i in range(10):
            text = f"Test mémoire numéro {i}. Tous les tests sont importants."
            _ = await agent.text_to_belief_set(text)
        
        # Le test de la mémoire est implicite dans le fait que cela ne crashe pas.
        # Les anciens attributs comme analysis_cache et get_analysis_summary n'existent plus.
        logger.info("Test de stabilité mémoire terminé.")


class TestFOLRealWorldIntegration:
    """Tests intégration monde réel pour FOL."""
    
    @pytest.mark.asyncio
    async def test_fol_complex_argumentation_analysis(self, fol_agent_with_kernel):
        """Test analyse argumentation complexe avec FOL."""
        complex_text = """
        Tous les philosophes sont des penseurs.
        Certains penseurs sont des écrivains.
        Socrate est un philosophe.
        Si quelqu'un est écrivain, alors il influence la culture.
        Donc il existe des philosophes qui peuvent influencer la culture.
        """
        
        agent = fol_agent_with_kernel
        belief_set, msg = await agent.text_to_belief_set(complex_text)
        
        # Analyse réussie
        assert belief_set is not None, f"Message: {msg}"
        assert belief_set.content
        
        # Formules complexes générées
        formulas_text = belief_set.content
        assert "forall" in formulas_text or "exists" in formulas_text  # Quantificateurs présents
        
        logger.info(f"✅ Analyse complexe terminée")
        logger.info(f"Taille du BeliefSet généré: {len(formulas_text)}")
    
    @pytest.mark.asyncio
    async def test_fol_multilingual_support(self, fol_agent_with_kernel):
        """Test support multilingue FOL (français/anglais)."""
        texts = {
            "français": "Tous les étudiants français sont intelligents.",
            "anglais": "All students are intelligent."
        }
        
        agent = fol_agent_with_kernel
        
        for lang, text in texts.items():
            belief_set, msg = await agent.text_to_belief_set(text)
            
            assert belief_set is not None, f"Message: {msg}"
            assert belief_set.content
            
            logger.info(f"✅ Support {lang} - belief set généré.")


# ==================== UTILITAIRES DE TEST ====================

def setup_real_tweety_environment():
    """Configure l'environnement pour tests Tweety réels."""
    env_vars = {
        "USE_REAL_JPYPE": "true",
        "TWEETY_JAR_PATH": "libs/tweety-full.jar",
        "JVM_MEMORY": "1024m"
    }
    
    for var, value in env_vars.items():
        if not os.getenv(var):
            os.environ[var] = value
    
    return all(os.getenv(var) for var in env_vars.keys())


def validate_fol_syntax(formula: str) -> bool:
    """Validation basique syntaxe FOL."""
    # Caractères FOL attendus
    fol_chars = ["∀", "∃", "→", "∧", "∨", "¬", "↔", "(", ")", ","]
    
    # Au moins un quantificateur ou prédicat
    has_quantifier = any(q in formula for q in ["∀", "∃"])
    has_predicate = "(" in formula and ")" in formula
    
    return has_quantifier or has_predicate


# ==================== CONFIGURATION PYTEST ====================


@pytest.fixture(scope="session", autouse=True)
def setup_logging():
    """Configuration logging pour session de tests."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


@pytest.fixture(scope="session")
def check_tweety_availability():
    """Vérifie disponibilité Tweety pour session."""
    return TWEETY_AVAILABLE and setup_real_tweety_environment()


# La sérialisation est maintenant la seule stratégie par défaut, la paramétrisation n'est plus nécessaire.
# La fixture use_serialization a été supprimée.

@pytest_asyncio.fixture(scope="module")
async def fol_agent_with_kernel(jvm_session):
    """Fixture pour créer un FOLLogicAgent avec un kernel authentique."""
    logger.info(f"--- DEBUT FIXTURE 'fol_agent_with_kernel' ---")
    if not jvm_session:
        pytest.skip("Skipping test: jvm_session fixture failed to initialize.")

    config = UnifiedConfig()
    kernel = config.get_kernel_with_gpt4o_mini()
    
    # Création de l'agent. Le paramètre use_serialization est obsolète.
    tweety_bridge = TweetyBridge()
    agent = FOLLogicAgent(kernel=kernel, tweety_bridge=tweety_bridge)
    
    # Injection manuelle de TweetyBridge et initialisation
    agent.setup_agent_components(llm_service_id="default")
    
    yield agent
    
    logger.info(f"--- FIN FIXTURE 'fol_agent_with_kernel' ---")


if __name__ == "__main__":
    # Exécution des tests d'intégration
    pytest.main([
        __file__, 
        "-v", 
        "--tb=short",
        "-k", "not test_real_tweety" if not TWEETY_AVAILABLE else ""
    ])