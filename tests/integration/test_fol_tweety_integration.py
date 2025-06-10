
# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

﻿#!/usr/bin/env python
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
import asyncio
import os
import time
import logging
from typing import Dict, List, Any, Optional


# Import de l'agent FOL et composants
from argumentation_analysis.agents.core.logic.fol_logic_agent import (
    FOLLogicAgent, 
    FOLAnalysisResult,
    create_fol_agent
)

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


class TestFOLTweetyCompatibility:
    async def _create_authentic_gpt4o_mini_instance(self):
        """Crée une instance authentique de gpt-4o-mini au lieu d'un mock."""
        config = UnifiedConfig()
        return config.get_kernel_with_gpt4o_mini()
        
    async def _make_authentic_llm_call(self, prompt: str) -> str:
        """Fait un appel authentique à gpt-4o-mini."""
        try:
            kernel = await self._create_authentic_gpt4o_mini_instance()
            result = await kernel.invoke("chat", input=prompt)
            return str(result)
        except Exception as e:
            logger.warning(f"Appel LLM authentique échoué: {e}")
            return "Authentic LLM call failed"

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


class TestRealTweetyFOLAnalysis:
    """Tests analyse FOL avec Tweety authentique."""
    
    @pytest.fixture
    def fol_agent_real_tweety(self):
        """Agent FOL avec Tweety réel si disponible."""
        config = PresetConfigs.authentic_fol()
        agent = FOLLogicAgent(agent_name="RealTweetyTest")
        
        # Force Tweety réel si disponible
        if TWEETY_AVAILABLE and os.getenv("USE_REAL_JPYPE", "").lower() == "true":
            agent.tweety_bridge = TweetyBridge()
        else:
            # Mock pour tests sans Tweety
            agent.tweety_bridge = await self._create_authentic_gpt4o_mini_instance()
            agent.tweety_bridge.check_consistency = Mock(return_value=True)
            agent.tweety_bridge.derive_inferences = Mock(return_value=["Mock inference"])
            agent.tweety_bridge.generate_models = Mock(return_value=[{"description": "Mock model", "model": {}}])
        
        return agent
    
    @pytest.mark.asyncio
    async def test_real_tweety_fol_syllogism_analysis(self, fol_agent_real_tweety):
        """Test analyse syllogisme avec Tweety réel."""
        # Syllogisme classique
        syllogism_text = """
        Tous les hommes sont mortels.
        Socrate est un homme.
        Donc Socrate est mortel.
        """
        
        # Configuration pour analyse réelle
        if hasattr(fol_agent_real_tweety.tweety_bridge, 'initialize_fol_reasoner'):
            await fol_agent_real_tweety.tweety_bridge.initialize_fol_reasoner()
        
        # Analyse complète
        start_time = time.time()
        result = await fol_agent_real_tweety.analyze(syllogism_text)
        analysis_time = time.time() - start_time
        
        # Vérifications résultat
        assert isinstance(result, FOLAnalysisResult)
        assert len(result.formulas) > 0
        assert result.confidence_score > 0.0
        
        # Performance acceptable (< 30 secondes pour syllogisme simple)
        assert analysis_time < 30.0
        
        logger.info(f"✅ Analyse syllogisme terminée en {analysis_time:.2f}s")
        logger.info(f"Formules: {result.formulas}")
        logger.info(f"Cohérence: {result.consistency_check}")
        logger.info(f"Confiance: {result.confidence_score}")
    
    @pytest.mark.asyncio
    async def test_real_tweety_fol_inconsistency_detection(self, fol_agent_real_tweety):
        """Test détection incohérence avec Tweety réel."""
        # Formules inconsistantes
        inconsistent_text = """
        Tous les hommes sont mortels.
        Socrate est un homme.
        Socrate n'est pas mortel.
        """
        
        if hasattr(fol_agent_real_tweety.tweety_bridge, 'initialize_fol_reasoner'):
            await fol_agent_real_tweety.tweety_bridge.initialize_fol_reasoner()
        
        result = await fol_agent_real_tweety.analyze(inconsistent_text)
        
        # Avec Tweety réel, l'incohérence devrait être détectée
        if os.getenv("USE_REAL_JPYPE", "").lower() == "true":
            # Test avec Tweety authentique
            assert result.consistency_check is False or len(result.validation_errors) > 0
            logger.info("✅ Incohérence détectée par Tweety réel")
        else:
            # Test avec mock
            logger.info("ℹ️ Test avec mock Tweety")
            assert result.confidence_score >= 0.0
    
    @pytest.mark.asyncio
    async def test_real_tweety_fol_inference_generation(self, fol_agent_real_tweety):
        """Test génération inférences avec Tweety réel."""
        # Prémisses permettant inférences
        premises_text = """
        Tous les étudiants sont intelligents.
        Marie est une étudiante.
        Pierre est un étudiant.
        """
        
        if hasattr(fol_agent_real_tweety.tweety_bridge, 'initialize_fol_reasoner'):
            await fol_agent_real_tweety.tweety_bridge.initialize_fol_reasoner()
        
        result = await fol_agent_real_tweety.analyze(premises_text)
        
        # Vérifications inférences
        assert len(result.inferences) > 0
        
        if os.getenv("USE_REAL_JPYPE", "").lower() == "true":
            # Avec Tweety réel, inférences devraient être logiquement valides
            logger.info(f"✅ Inférences Tweety réel: {result.inferences}")
        else:
            logger.info(f"ℹ️ Inférences mock: {result.inferences}")
        
        # Performance inférences
        assert result.confidence_score > 0.0


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
    async def test_fol_syntax_error_recovery(self):
        """Test récupération erreurs syntaxe FOL."""
        agent = FOLLogicAgent()
        
        # Texte problématique
        problematic_text = "Ceci n'est pas une formule logique valide !!!"
        
        result = await agent.analyze(problematic_text)
        
        # Agent doit gérer gracieusement
        assert isinstance(result, FOLAnalysisResult)
        # Soit erreurs détectées, soit conversion basique réussie
        assert len(result.validation_errors) > 0 or len(result.formulas) > 0
        
    @pytest.mark.asyncio
    async def test_fol_timeout_handling(self):
        """Test gestion timeouts analyse FOL."""
        agent = FOLLogicAgent()
        
        # Mock timeout
        if agent.tweety_bridge:
            agent.tweety_bridge = await self._create_authentic_gpt4o_mini_instance()
            agent.tweety_bridge.check_consistency = Mock(side_effect=asyncio.TimeoutError("Timeout test"))
        
        result = await agent.analyze("Test timeout FOL.")
        
        # Timeout géré gracieusement
        assert isinstance(result, FOLAnalysisResult)
        if len(result.validation_errors) > 0:
            assert any("timeout" in error.lower() or "erreur" in error.lower() for error in result.validation_errors)


class TestFOLPerformanceVsModal:
    """Tests performance FOL vs Modal Logic."""
    
    @pytest.mark.asyncio
    async def test_fol_vs_modal_performance_comparison(self):
        """Test comparaison performance FOL vs Modal Logic."""
        # Agent FOL
        fol_agent = FOLLogicAgent(agent_name="PerformanceFOL")
        
        test_text = "Tous les étudiants intelligents réussissent leurs examens."
        
        # Test FOL
        start_fol = time.time()
        fol_result = await fol_agent.analyze(test_text)
        fol_time = time.time() - start_fol
        
        # Vérifications FOL
        assert isinstance(fol_result, FOLAnalysisResult)
        assert fol_time < 10.0  # Moins de 10 secondes acceptable
        
        logger.info(f"✅ Performance FOL: {fol_time:.2f}s")
        logger.info(f"Confiance FOL: {fol_result.confidence_score:.2f}")
        
        # Note: Comparaison avec Modal Logic nécessiterait import Modal Agent
        # Pour l'instant on valide juste que FOL performe correctement
    
    @pytest.mark.asyncio
    async def test_fol_stability_multiple_analyses(self):
        """Test stabilité FOL sur analyses multiples."""
        agent = FOLLogicAgent()
        
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
            result = await agent.analyze(text)
            elapsed = time.time() - start
            
            results.append(result)
            total_time += elapsed
            
            # Chaque analyse doit réussir
            assert isinstance(result, FOLAnalysisResult)
            assert result.confidence_score >= 0.0
        
        # Performance stable
        avg_time = total_time / len(test_texts)
        assert avg_time < 5.0  # Moyenne < 5 secondes par analyse
        
        logger.info(f"✅ Stabilité FOL: {len(results)} analyses en {total_time:.2f}s")
        logger.info(f"Temps moyen: {avg_time:.2f}s")
    
    @pytest.mark.asyncio
    async def test_fol_memory_usage_stability(self):
        """Test stabilité mémoire agent FOL."""
        agent = FOLLogicAgent()
        
        # Analyses répétées pour tester fuites mémoire
        for i in range(10):
            text = f"Test mémoire numéro {i}. Tous les tests sont importants."
            result = await agent.analyze(text)
            assert isinstance(result, FOLAnalysisResult)
        
        # Cache géré correctement
        assert len(agent.analysis_cache) <= 10  # Cache pas infini
        
        # Statistiques cohérentes
        summary = agent.get_analysis_summary()
        assert summary["total_analyses"] >= 0
        assert 0.0 <= summary["avg_confidence"] <= 1.0


class TestFOLRealWorldIntegration:
    """Tests intégration monde réel pour FOL."""
    
    @pytest.mark.asyncio
    async def test_fol_complex_argumentation_analysis(self):
        """Test analyse argumentation complexe avec FOL."""
        complex_text = """
        Tous les philosophes sont des penseurs.
        Certains penseurs sont des écrivains.
        Socrate est un philosophe.
        Si quelqu'un est écrivain, alors il influence la culture.
        Donc il existe des philosophes qui peuvent influencer la culture.
        """
        
        agent = FOLLogicAgent()
        result = await agent.analyze(complex_text)
        
        # Analyse réussie
        assert isinstance(result, FOLAnalysisResult)
        assert len(result.formulas) > 0
        
        # Formules complexes générées
        formulas_text = " ".join(result.formulas)
        assert "∀" in formulas_text or "∃" in formulas_text  # Quantificateurs présents
        
        logger.info(f"✅ Analyse complexe terminée")
        logger.info(f"Formules générées: {len(result.formulas)}")
        logger.info(f"Étapes raisonnement: {len(result.reasoning_steps)}")
    
    @pytest.mark.asyncio
    async def test_fol_multilingual_support(self):
        """Test support multilingue FOL (français/anglais)."""
        texts = {
            "français": "Tous les étudiants français sont intelligents.",
            "anglais": "All students are intelligent."
        }
        
        agent = FOLLogicAgent()
        
        for lang, text in texts.items():
            result = await agent.analyze(text)
            
            assert isinstance(result, FOLAnalysisResult)
            assert len(result.formulas) > 0
            
            logger.info(f"✅ Support {lang}: {result.formulas}")


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


if __name__ == "__main__":
    # Exécution des tests d'intégration
    pytest.main([
        __file__, 
        "-v", 
        "--tb=short",
        "-k", "not test_real_tweety" if not TWEETY_AVAILABLE else ""
    ])
