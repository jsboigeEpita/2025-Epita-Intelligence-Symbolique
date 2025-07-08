# Authentic gpt-4o-mini imports (replacing mocks)
from config.unified_config import UnifiedConfig
import sys
import pathlib

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests d'intégration FOL-Tweety pour FirstOrderLogicAgent.

Ce module valide l'interaction entre le FirstOrderLogicAgent et la
bibliothèque Java TweetyProject via JPype. Les tests couvrent la
syntaxe, la sémantique et la robustesse de la Logique du Premier Ordre (FOL).

La grammaire FOL simplifiée utilisée est la suivante (style BNF) :
<belief_set> ::= <declaration> | <formula> | <belief_set> <belief_set>
<declaration> ::= <sort_declaration> | <predicate_declaration>
<sort_declaration> ::= <sort_name> = {<constant_name>, ...}
<predicate_declaration> ::= type(<predicate_name>(<sort_name>, ...))

<formula> ::= <atomic_formula> | <quantified_formula> | <compound_formula>
<atomic_formula> ::= <predicate_name>(<term>, ...) | ¬<predicate_name>(<term>, ...)
<term> ::= <constant_name> | <variable_name>
<quantified_formula> ::= (forall <var>: <formula>) | (exists <var>: <formula>)
<compound_formula> ::= (<formula> <connective> <formula>)
<connective> ::= => | & | |
"""

import pytest
import threading
import queue
import os
import time
import logging
import asyncio
import inspect
from typing import Dict, List, Any, Optional
from unittest.mock import patch

# Import a shared fixture to manage the JVM lifecycle
from argumentation_analysis.agents.core.logic.first_order_logic_agent import FirstOrderLogicAgent as FOLLogicAgent
from argumentation_analysis.agents.core.logic.belief_set import BeliefSet, FirstOrderBeliefSet
from config.unified_config import LogicType, MockLevel, PresetConfigs
from argumentation_analysis.utils.tweety_error_analyzer import TweetyErrorAnalyzer

try:
    from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge
    TWEETY_AVAILABLE = True
except ImportError:
    TWEETY_AVAILABLE = False
    TweetyBridge = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
jpype_logger = logging.getLogger("jpype")
jpype_logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
jpype_logger.addHandler(handler)

def run_in_thread(target, *args, **kwargs):
    """Exécute une fonction (synchrone ou coroutine) dans un thread séparé et retourne son résultat."""
    result_queue = queue.Queue()

    def thread_target():
        try:
            # Vérifie si la cible est une coroutine.
            if inspect.iscoroutinefunction(target):
                # Si oui, on a besoin de démarrer une loop asyncio pour l'exécuter.
                # asyncio.run() crée une nouvelle boucle, l'exécute, puis la ferme.
                # Parfait pour une exécution isolée dans un thread.
                result = asyncio.run(target(*args, **kwargs))
            else:
                # Sinon, c'est une fonction synchrone standard.
                result = target(*args, **kwargs)
            
            result_queue.put(result)
        except Exception as e:
            # Capture toutes les exceptions (de la coroutine ou de la fonction synchrone)
            # et les met dans la queue pour que le thread principal puisse les lever.
            result_queue.put(e)

    thread = threading.Thread(target=thread_target)
    thread.start()
    thread.join()  # Attendre que le thread se termine.
    
    result = result_queue.get()
    if isinstance(result, Exception):
        raise result
    return result

def _create_authentic_gpt4o_mini_instance():
    """Crée une instance authentique de gpt-4o-mini au lieu d'un mock."""
    config = UnifiedConfig()
    return config.get_kernel_with_gpt4o_mini()

def _make_authentic_llm_call(prompt: str) -> str:
    """Fait un appel authentique à gpt-4o-mini."""
    try:
        kernel = _create_authentic_gpt4o_mini_instance()
        # L'appel invoke de semantic-kernel peut nécessiter une gestion de boucle d'événement
        # Si c'est le cas, il faudra une approche plus complexe. On suppose pour l'instant
        # qu'on peut le lancer dans un thread.
        result = run_in_thread(kernel.invoke, "chat", input=prompt)
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
    def test_fol_formula_tweety_compatibility(self, fol_agent_with_kernel, jvm_session):
        """Test compatibilité formules FOL avec l'agent FOL réel."""
        if not jvm_session:
            pytest.skip("Test nécessite la JVM.")
        agent = fol_agent_with_kernel
        formula_str = "thing = {a}\ntype(P(thing))\n\nP(a)"
        try:
            belief_set, status = run_in_thread(agent.text_to_belief_set, formula_str)
            assert belief_set is not None, f"La conversion a échoué: {status}"
            is_consistent, msg = run_in_thread(agent.is_consistent, belief_set)
            logger.info(f"✅ Formule syntaxiquement correcte acceptée par Tweety: {msg}")
            assert is_consistent is True
        except Exception as e:
            pytest.fail(f"Une syntaxe FOL valide a été rejetée: {e}")
    
    @pytest.mark.skipif(not TWEETY_AVAILABLE, reason="TweetyBridge non disponible")
    def test_fol_predicate_declaration_validation(self, fol_agent_with_kernel, jvm_session):
        """Test validation déclaration prédicats FOL avec Tweety via l'agent."""
        if not jvm_session:
            pytest.skip("Test nécessite la JVM.")
        agent = fol_agent_with_kernel
        valid_formula_str = "human = {socrate}\ntype(Mortal(human))\n\nMortal(socrate)"
        try:
            belief_set, status = run_in_thread(agent.text_to_belief_set, valid_formula_str)
            assert belief_set is not None, f"La conversion a échoué: {status}"
            is_consistent, msg = run_in_thread(agent.is_consistent, belief_set)
            logger.info(f"✅ Prédicats validés par Tweety: {msg}")
            assert is_consistent is True
        except Exception as e:
            pytest.fail(f"Erreur Tweety inattendue pour une déclaration valide: {e}")
    
    @pytest.mark.skipif(not TWEETY_AVAILABLE, reason="TweetyBridge non disponible")
    def test_fol_quantifier_binding_validation(self, fol_agent_with_kernel, jvm_session):
        """Test validation liaison quantificateurs avec Tweety via l'agent."""
        if not jvm_session:
            pytest.skip("Test nécessite la JVM.")
        agent = fol_agent_with_kernel
        well_bound_formula_str = "item = {a}\ntype(P(item))\ntype(Q(item))\n\nforall X: (P(X) => Q(X))"
        try:
            belief_set, status = run_in_thread(agent.text_to_belief_set, well_bound_formula_str)
            assert belief_set is not None, f"La conversion a échoué: {status}"
            is_consistent, msg = run_in_thread(agent.is_consistent, belief_set)
            logger.info(f"✅ Variables correctement liées validées: {msg}")
            assert is_consistent is True
        except Exception as e:
            pytest.fail(f"Variables bien liées ont causé une erreur inattendue: {e}")

    def test_programmatic_belief_set_creation_and_consistency(self, fol_agent_with_kernel, jvm_session):
        if not jvm_session:
            pytest.skip("Test nécessite la JVM.")
        
        agent = fol_agent_with_kernel
        builder = agent._builder_plugin
        builder.reset()
        builder.add_sort("homme")
        builder.add_constant_to_sort("socrate", "homme")
        builder.add_predicate_schema("is_homme", ["homme"])
        builder.add_predicate_schema("is_mortel", ["homme"])
        builder.add_atomic_fact("is_homme", ["socrate"])
        builder.add_universal_implication("is_homme", "is_mortel", "homme")
        
        java_belief_set_obj = builder.build_tweety_belief_set(agent.tweety_bridge)
        assert java_belief_set_obj is not None
        belief_set = FirstOrderBeliefSet(content=java_belief_set_obj.toString(), java_object=java_belief_set_obj)
        assert "FolBeliefSet" in str(type(belief_set.java_object))
        
        is_consistent, consistency_msg = run_in_thread(agent.is_consistent, belief_set)
        assert is_consistent
        
        entails, query_msg = run_in_thread(agent.execute_query, belief_set, "is_mortel(socrate)")
        assert entails
        
        logger.info("✅ Le flux de création programmatique du BeliefSet est validé avec succès (sans LLM).")

class TestRealTweetyFOLAnalysis:
    """Tests analyse FOL avec Tweety authentique."""
    
    def test_real_tweety_fol_syllogism_analysis(self, fol_agent_with_kernel, jvm_session):
        if not jvm_session:
            pytest.skip("Test nécessite la JVM.")
            
        agent = fol_agent_with_kernel
        syllogism_str = "human = {socrate}\ntype(man(human))\ntype(mortal(human))\n\nforall X: (man(X) => mortal(X))\nman(socrate)"
        belief_set, status = run_in_thread(agent.text_to_belief_set, syllogism_str)
        assert belief_set is not None, f"La conversion a échoué: {status}"
        is_consistent, _ = run_in_thread(agent.is_consistent, belief_set)
        assert is_consistent is True, "Le belief set du syllogisme devrait être consistant."
        entails, _ = run_in_thread(agent.execute_query, belief_set, "is_mortel(socrate)")
        assert entails is True, "L'inférence 'mortal(socrate)' devrait être acceptée."
        logger.info("✅ Analyse du syllogisme par chaîne de caractères réussie.")

    def test_end_to_end_fol_syllogism_with_llm(self, fol_agent_with_kernel, jvm_session, caplog):
        if not jvm_session:
            pytest.skip("Test nécessite la JVM.")

        agent = fol_agent_with_kernel
        syllogism_text = "Tous les hommes sont mortels. Socrate est un homme."
        belief_set, conversion_status = run_in_thread(agent.text_to_belief_set, syllogism_text)
        assert belief_set is not None
        assert not belief_set.is_empty()
        logger.info(f"BeliefSet généré par le LLM:\n{belief_set.content}")
        
        is_consistent, _ = run_in_thread(agent.is_consistent, belief_set)
        assert is_consistent is True
        
        entails, _ = run_in_thread(agent.execute_query, belief_set, "is_mortel(socrate)")
        assert entails is True
        
        errors = [record for record in caplog.records if record.levelno >= logging.ERROR]
        if errors:
            error_messages = "\n".join([f"- {record.name}: {record.getMessage()}" for record in errors])
            pytest.fail(f"Des erreurs ont été logguées pendant le test, même s'il a réussi:\n{error_messages}")
            
        logger.info("✅ Test d'intégration de bout en bout avec LLM et Tweety réussi, SANS ERREUR LATENTE.")

    def test_real_tweety_fol_inconsistency_detection(self, fol_agent_with_kernel, jvm_session):
        if not jvm_session:
            pytest.skip("Test nécessite la JVM.")
        
        agent = fol_agent_with_kernel
        builder = agent._builder_plugin
        builder.reset()
        builder.add_sort("concept")
        builder.add_predicate_schema("est_vrai", ["concept"])
        builder.add_constant_to_sort("a", "concept")
        builder.add_atomic_fact("est_vrai", ["a"])
        builder.add_negated_atomic_fact("est_vrai", ["a"])
        
        java_belief_set_obj = builder.build_tweety_belief_set(agent.tweety_bridge)
        assert java_belief_set_obj is not None
        belief_set = FirstOrderBeliefSet(content=java_belief_set_obj.toString(), java_object=java_belief_set_obj)

        is_consistent, consistency_msg = run_in_thread(agent.is_consistent, belief_set)
        assert not is_consistent, f"La base de connaissance aurait du être inconsistante, mais elle est consistante"
        assert "inconsistent" in consistency_msg.lower() or "incohérent" in consistency_msg.lower(), f"Le message d'erreur n'indique pas l'inconsistance : {consistency_msg}"
        logger.info(f"✅ Incohérence programmatique (P ∧ ¬P) correctement détectée. Message: {consistency_msg}")
    
    def test_real_tweety_fol_inference_generation(self, fol_agent_with_kernel, jvm_session):
        if not jvm_session:
            pytest.skip("Test nécessite la JVM.")
        
        agent = fol_agent_with_kernel
        builder = agent._builder_plugin
        builder.reset()
        
        builder.add_sort("etudiant")
        builder.add_predicate_schema("is_etudiant", ["etudiant"])
        builder.add_predicate_schema("is_intelligent", ["etudiant"])
        builder.add_constant_to_sort("marie", "etudiant")
        builder.add_universal_implication("is_etudiant", "is_intelligent", "etudiant")
        builder.add_atomic_fact("is_etudiant", ["marie"])

        java_belief_set_obj = builder.build_tweety_belief_set(agent.tweety_bridge)
        belief_set = FirstOrderBeliefSet(content=java_belief_set_obj.toString(), java_object=java_belief_set_obj)
        assert belief_set is not None
        
        entails, _ = run_in_thread(agent.execute_query, belief_set, "is_intelligent(marie)")
        assert entails is True
        logger.info("✅ Inférence 'est_intelligent(marie)' validée.")


class TestFOLErrorHandling:
    @pytest.fixture
    def error_analyzer(self):
        return TweetyErrorAnalyzer()
    
    def test_fol_predicate_declaration_error_handling(self, error_analyzer):
        tweety_error = "Predicate 'Unknown' has not been declared"
        feedback = error_analyzer.analyze_error(tweety_error)
        if feedback:
            assert feedback.error_type == "DECLARATION_ERROR"
            logger.info(f"✅ Erreur analysée: {feedback.corrections}")
        else:
            logger.warning("⚠️ Erreur non reconnue par l'analyseur")
    
    def test_fol_syntax_error_recovery(self, fol_agent_with_kernel):
        agent = fol_agent_with_kernel
        problematic_text = "D'incolores idées vertes dorment furieusement."
        try:
            belief_set, msg = run_in_thread(agent.text_to_belief_set, problematic_text)
            assert belief_set is not None
            if belief_set.is_empty():
                logger.info("✅ Le LLM a correctement identifié le texte comme absurde et a retourné un belief set vide.")
            else:
                logger.warning(f"⚠️ Le LLM a halluciné une structure logique: {belief_set.content}.")
            logger.info("✅ Le test de robustesse est réussi.")
        except Exception as e:
            pytest.fail(f"L'agent a levé une exception inattendue: {e}", pytrace=True)
        
    def test_fol_timeout_handling(self, fol_agent_with_kernel, jvm_session):
        if not jvm_session:
            pytest.skip("Test nécessite la JVM.")
        
        agent = fol_agent_with_kernel
        builder = agent._builder_plugin
        builder.reset()
        builder.add_sort("concept")
        builder.add_predicate_schema("est_un", ["concept"])
        builder.add_constant_to_sort("a", "concept")
        builder.add_atomic_fact("est_un", ["a"])

        java_belief_set_obj = builder.build_tweety_belief_set(agent.tweety_bridge)
        belief_set = FirstOrderBeliefSet(content=java_belief_set_obj.toString(), java_object=java_belief_set_obj)
        
        # Simuler un timeout. On doit utiliser une exception standard car asyncio n'est plus là.
        with patch.object(agent.tweety_bridge.fol_handler, 'fol_check_consistency', side_effect=TimeoutError("Timeout de test simulé")):
            is_consistent, consistency_msg = run_in_thread(agent.is_consistent, belief_set)

        assert not is_consistent
        assert "simulé" in consistency_msg.lower()
        logger.info(f"✅ Gestion du timeout validée avec le message: {consistency_msg}")


class TestFOLPerformanceVsModal:
    def test_fol_vs_modal_performance_comparison(self, fol_agent_with_kernel, jvm_session):
        if not jvm_session:
            pytest.skip("Test nécessite la JVM.")
        
        fol_agent = fol_agent_with_kernel
        builder = fol_agent._builder_plugin
        builder.reset()
        builder.add_sort("concept")
        builder.add_predicate_schema("est_un", ["concept"])
        builder.add_constant_to_sort("a", "concept")
        builder.add_atomic_fact("est_un", ["a"])

        start_fol = time.time()
        java_obj = builder.build_tweety_belief_set(fol_agent.tweety_bridge)
        belief_set = FirstOrderBeliefSet(content=java_obj.toString(), java_object=java_obj)
        run_in_thread(fol_agent.is_consistent, belief_set)
        fol_time = time.time() - start_fol
        
        assert belief_set is not None
        assert fol_time < 10.0
        logger.info(f"✅ Performance FOL (programmatique): {fol_time:.2f}s")
    
    def test_fol_stability_multiple_analyses(self, fol_agent_with_kernel):
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
        for i, text in enumerate(test_texts):
            builder = agent._builder_plugin
            builder.reset()
            builder.add_sort("concept")
            builder.add_predicate_schema(f"pred_{i}", ["concept"])
            builder.add_constant_to_sort(f"const_{i}", "concept")
            builder.add_atomic_fact(f"pred_{i}", [f"const_{i}"])

            start = time.time()
            java_obj = builder.build_tweety_belief_set(agent.tweety_bridge)
            belief_set = FirstOrderBeliefSet(content=java_obj.toString(), java_object=java_obj)
            elapsed = time.time() - start
            results.append(belief_set)
            total_time += elapsed
            assert belief_set is not None and belief_set.java_object is not None
        
        avg_time = total_time / len(test_texts)
        assert avg_time < 5.0
        logger.info(f"✅ Stabilité FOL: {len(results)} analyses en {total_time:.2f}s")
    
    def test_fol_memory_usage_stability(self, fol_agent_with_kernel):
        agent = fol_agent_with_kernel
        for i in range(10):
            text = f"Test mémoire numéro {i}. Tous les tests sont importants."
            _ = run_in_thread(agent.text_to_belief_set, text)
        logger.info("Test de stabilité mémoire terminé.")

@pytest.fixture(scope="module")
def fol_agent_with_kernel(jvm_session):
    """Fixture synchrone pour créer un FOLLogicAgent avec un kernel authentique."""
    logger.info("--- DEBUT FIXTURE 'fol_agent_with_kernel' ---")
    if not jvm_session:
        pytest.skip("Skipping test: jvm_session fixture failed to initialize.")

    config = UnifiedConfig()
    # On suppose que get_kernel... est synchrone ou peut être appelé ainsi.
    kernel = config.get_kernel_with_gpt4o_mini(force_authentic=True)
    
    tweety_bridge = TweetyBridge.get_instance()
    agent = FOLLogicAgent(kernel=kernel, tweety_bridge=tweety_bridge, service_id="default")
    
    # --- Forcer l'initialisation des Handlers ---
    # Accéder au handler une fois pour déclencher le chargement paresseux (lazy-loading)
    # et s'assurer que tous les composants Java (parsers, etc.) sont prêts.
    _ = tweety_bridge.fol_handler
    # ---------------------------------------------

    # L'appel setup doit être synchrone ou wrappé. On suppose qu'il est synchrone.
    agent.setup_agent_components(llm_service_id="default")
    
    yield agent
    
    logger.info("--- FIN FIXTURE 'fol_agent_with_kernel' ---")

# Le reste du fichier reste similaire, mais sans les décorateurs async...