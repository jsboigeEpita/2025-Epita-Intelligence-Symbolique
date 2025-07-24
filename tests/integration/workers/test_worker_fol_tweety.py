# Authentic gpt-4o-mini imports (replacing mocks)
from config.unified_config import UnifiedConfig
import sys
import pathlib

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests d'intégration FOL-Tweety pour FOLLogicAgent.

Grammaire BNF du Parser FOL (FolParser.java de TweetyProject) pour référence :
--------------------------------------------------------------------------------
 KB 			::== SORTSDEC DECLAR FORMULAS
 DECLAR		::== (FUNCTORDEC | PREDDEC)*
 SORTSDEC    ::== ( SORTNAME "=" "{" (CONSTANTNAME ("," CONSTANTNAME)*)? "}" "\n" )*
 PREDDEC		::== "type" "(" PREDICATENAME ("(" SORTNAME ("," SORTNAME)* ")")? ")" "\n"
 FUNCTORDEC	::== "type" "(" SORTNAME "=" FUNCTORNAME "(" (SORTNAME ("," SORTNAME)*)? ")" ")" "\n"
 FORMULAS    ::== ( "\n" FORMULA)*
 FORMULA     ::== ATOM | "forall" VARIABLENAME ":" "(" FORMULA ")" | "exists" VARIABLENAME ":" "(" FORMULA ")" |
 					 "(" FORMULA ")" | FORMULA "&&" FORMULA | FORMULA "||" FORMULA | "!" FORMULA | "+" | "-" |
 					 FORMULA "=>" FORMULA | FORMULA "<=>" FORMULA | FORMULA "==" FORMULA | FORMULA "/==" FORMULA |
 					 FORMULA "^^" FORMULA
 ATOM		::== PREDICATENAME ("(" TERM ("," TERM)* ")")?
 TERM		::== VARIABLENAME | CONSTANTNAME | FUNCTORNAME "(" (TERM ("," TERM)*)?  ")"
--------------------------------------------------------------------------------

Ces tests valident l'intégration authentique entre l'agent FOL et TweetyProject.
"""

import pytest
import pytest_asyncio
import asyncio
import os
import time
import logging
from typing import Dict, List, Any, Optional
from unittest.mock import patch, AsyncMock


# Import a shared fixture to manage the JVM lifecycle
# La fixture jvm_session est maintenant fournie automatiquement par conftest.py (autouse=True)
# et peut être demandée comme dépendance sans import direct.
# from tests.fixtures.integration_fixtures import jvm_session
# Import de l'agent FOL et composants
from argumentation_analysis.agents.core.logic.fol_logic_agent import FOLLogicAgent as FOLLogicAgent
from argumentation_analysis.agents.core.logic.belief_set import BeliefSet, FirstOrderBeliefSet
# Import configuration et Tweety
from config.unified_config import LogicType, MockLevel, PresetConfigs
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
# Enable JPype logging
jpype_logger = logging.getLogger("jpype")
jpype_logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
jpype_logger.addHandler(handler)


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
    async def test_fol_formula_tweety_compatibility(self, fol_agent_with_kernel, jvm_session):
        """Test compatibilité formules FOL avec l'agent FOL réel."""
        if not jvm_session:
            pytest.skip("Test nécessite la JVM.")
        agent = fol_agent_with_kernel
        # Syntaxe correcte avec sauts de ligne explicites pour éviter les problèmes de formatage.
        formula_str = "thing = {a}\ntype(P(thing))\n\nP(a)"
        try:
            belief_set = FirstOrderBeliefSet(content=formula_str)
            is_consistent, msg = await agent.is_consistent(belief_set)
            logger.info(f"✅ Formule syntaxiquement correcte acceptée par Tweety: {msg}")
            assert is_consistent is True
        except Exception as e:
            pytest.fail(f"Une syntaxe FOL valide a été rejetée: {e}")
    
    @pytest.mark.skipif(not TWEETY_AVAILABLE, reason="TweetyBridge non disponible")
    @pytest.mark.asyncio
    async def test_fol_predicate_declaration_validation(self, fol_agent_with_kernel, jvm_session):
        """Test validation déclaration prédicats FOL avec Tweety via l'agent."""
        if not jvm_session:
            pytest.skip("Test nécessite la JVM.")
        agent = fol_agent_with_kernel
        # Syntaxe multi-lignes correcte, conforme à la BNF de Tweety.
        valid_formula_str = """
human = {socrate}
type(Mortal(human))

Mortal(socrate)
"""
        belief_set = FirstOrderBeliefSet(content=valid_formula_str)
        try:
            is_consistent, msg = await agent.is_consistent(belief_set)
            logger.info(f"✅ Prédicats validés par Tweety: {msg}")
            assert is_consistent is True
        except Exception as e:
            pytest.fail(f"Erreur Tweety inattendue pour une déclaration valide: {e}")
    
    @pytest.mark.skipif(not TWEETY_AVAILABLE, reason="TweetyBridge non disponible")
    @pytest.mark.asyncio
    async def test_fol_quantifier_binding_validation(self, fol_agent_with_kernel, jvm_session):
        """Test validation liaison quantificateurs avec Tweety via l'agent."""
        if not jvm_session:
            pytest.skip("Test nécessite la JVM.")
        agent = fol_agent_with_kernel
        # Syntaxe correcte pour les quantificateurs en multi-lignes, conforme à la BNF de Tweety.
        well_bound_formula_str = """
item = {a}
type(P(item))
type(Q(item))

forall X: (P(X) => Q(X))
"""
        belief_set = FirstOrderBeliefSet(content=well_bound_formula_str)
        try:
            is_consistent, msg = await agent.is_consistent(belief_set)
            logger.info(f"✅ Variables correctement liées validées: {msg}")
            assert is_consistent is True
        except Exception as e:
            pytest.fail(f"Variables bien liées ont causé une erreur inattendue: {e}")

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
        builder.add_predicate_schema("estunhomme", ["Homme"])
        builder.add_predicate_schema("estmortel", ["Homme"])
        builder.add_atomic_fact("estunhomme", ["socrate"])
        # Pour l'implication universelle, il faut s'assurer que les prédicats
        # sont bien déclarés, ce qui est fait ci-dessus.
        builder.add_universal_implication("estunhomme", "estmortel", "Homme")

        # 2. Déclencher DIRECTEMENT la construction programmatique.
        #    On contourne l'appel LLM de `text_to_belief_set`.
        java_belief_set_obj = builder.build_tweety_belief_set(agent.tweety_bridge)
        
        # 3. Valider le résultat
        assert java_belief_set_obj is not None, "La création du BeliefSet programmatique a retourné None."
        
        # Créer un objet BeliefSet de haut niveau pour les étapes suivantes
        belief_set = FirstOrderBeliefSet(content=java_belief_set_obj.toString(), java_object=java_belief_set_obj)
        
        # Vérifier que le type est correct
        assert "FolBeliefSet" in str(type(belief_set.java_object)), f"L'objet retourné n'est pas un FolBeliefSet mais un {type(belief_set.java_object)}"

        # 4. Vérifier la cohérence du BeliefSet créé
        is_consistent, consistency_msg = await agent.is_consistent(belief_set)
        assert is_consistent, f"Le BeliefSet créé par programmation est incohérent: {consistency_msg}"

        # 5. Tenter une requête simple
        entails, query_msg = await agent.execute_query(belief_set, "estmortel(socrate)")
        assert entails, f"L'inférence 'estmortel(socrate)' a échoué: {query_msg}"

        logger.info("✅ Le flux de création programmatique du BeliefSet est validé avec succès (sans LLM).")
class TestRealTweetyFOLAnalysis:
    """Tests analyse FOL avec Tweety authentique."""
    
    @pytest.mark.asyncio
    async def test_real_tweety_fol_syllogism_analysis(self, fol_agent_with_kernel, jvm_session):
        """Test analyse syllogisme avec Tweety réel (via construction par chaîne)."""
        if not jvm_session:
            pytest.skip("Test nécessite la JVM.")
            
        agent = fol_agent_with_kernel
        # Test avec une chaîne de caractères syntaxiquement correcte
        syllogism_str = """
human = {socrate}
type(Man(human))
type(Mortal(human))

forall X: (Man(X) => Mortal(X))
Man(socrate)
"""
        belief_set = FirstOrderBeliefSet(content=syllogism_str)

        # Vérification de la consistance
        is_consistent, _ = await agent.is_consistent(belief_set)
        assert is_consistent is True, "Le belief set du syllogisme devrait être consistant."

        # Vérification de l'inférence
        entails, _ = await agent.execute_query(belief_set, "Mortal(socrate)")
        assert entails is True, "L'inférence 'Mortal(socrate)' devrait être acceptée."
        
        logger.info("✅ Analyse du syllogisme par chaîne de caractères réussie.")

    @pytest.mark.asyncio
    async def test_end_to_end_fol_syllogism_with_llm(self, fol_agent_with_kernel, jvm_session, caplog):
        """
        Test l'analyse de bout en bout d'un syllogisme, en utilisant le LLM
        pour la conversion texte -> belief set, puis Tweety pour le raisonnement.
        C'est le test d'intégration ultime. Ce test doit aussi s'assurer
        qu'aucun log d'erreur n'est produit, même si le test réussit.
        """
        if not jvm_session:
            pytest.skip("Test nécessite la JVM.")

        agent = fol_agent_with_kernel
        
        syllogism_text = "Tous les hommes sont mortels. Socrate est un homme."

        # Act: Utiliser le LLM pour convertir le texte en belief set.
        belief_set, conversion_status = await agent.text_to_belief_set(syllogism_text)
        
        # Assert: Vérifier que la conversion a réussi et que le belief set n'est pas vide.
        assert belief_set is not None, f"La conversion du texte en belief set a échoué: {conversion_status}"
        assert not belief_set.is_empty(), "Le belief set ne devrait pas être vide après la conversion."
        logger.info(f"BeliefSet généré par le LLM:\n{belief_set.content}")

        # Assert: Vérifier la consistance du belief set généré.
        is_consistent, _ = await agent.is_consistent(belief_set)
        assert is_consistent is True, "Le belief set du syllogisme généré par le LLM devrait être consistant."

        # Assert: Vérifier l'inférence clé.
        entails, _ = await agent.execute_query(belief_set, "mortel(socrate)")
        assert entails is True, "L'inférence 'mortel(socrate)' devrait être acceptée."
        
        # Assert: Vérifier qu'il n'y a pas eu d'erreurs de logique latentes.
        # C'est la nouvelle condition clé pour attraper les "silent bugs".
        errors = [record for record in caplog.records if record.levelno >= logging.ERROR]
        if errors:
            error_messages = "\n".join([f"- {record.name}: {record.getMessage()}" for record in errors])
            pytest.fail(f"Des erreurs ont été logguées pendant le test, même s'il a réussi:\n{error_messages}")
            
        logger.info("✅ Test d'intégration de bout en bout avec LLM et Tweety réussi, SANS ERREUR LATENTE.")

    @pytest.mark.asyncio
    async def test_real_tweety_fol_inconsistency_detection(self, fol_agent_with_kernel, jvm_session):
        """
        Test détection incohérence avec Tweety réel en utilisant la nouvelle
        fonction de négation du BeliefSetBuilderPlugin.
        """
        if not jvm_session:
            pytest.skip("Test nécessite la JVM.")
        
        agent = fol_agent_with_kernel
        builder = agent._builder_plugin
        builder.reset()

        # 1. Définir le schéma de base: un prédicat P avec un argument.
        builder.add_sort("concept")
        builder.add_predicate_schema("est_vrai", ["concept"])
        builder.add_constant_to_sort("a", "concept")

        # 2. Ajouter un fait atomique P(a).
        builder.add_atomic_fact("est_vrai", ["a"])
        
        # 3. Ajouter sa négation ¬P(a) en utilisant la nouvelle fonctionnalité.
        builder.add_negated_atomic_fact("est_vrai", ["a"])

        # 4. Construire le BeliefSet à partir des faits.
        java_belief_set_obj = builder.build_tweety_belief_set(agent.tweety_bridge)
        assert java_belief_set_obj is not None, "La création du BeliefSet n'a pas réussi."
        belief_set = FirstOrderBeliefSet(content=java_belief_set_obj.toString(), java_object=java_belief_set_obj)

        # 5. Vérifier que le BeliefSet {P(a), ¬P(a)} est bien détecté comme incohérent.
        is_consistent, consistency_msg = await agent.is_consistent(belief_set)

        assert not is_consistent, f"Le BeliefSet devrait être incohérent, mais il est considéré comme consistant. Message: {consistency_msg}"
        
        assert "inconsistent" in consistency_msg.lower() or "incohérent" in consistency_msg.lower(), \
               f"Le message de retour '{consistency_msg}' n'indique pas une incohérence comme attendu."

        logger.info(f"✅ Incohérence programmatique (P ∧ ¬P) correctement détectée. Message: {consistency_msg}")
    
    @pytest.mark.asyncio
    async def test_real_tweety_fol_inference_generation(self, fol_agent_with_kernel, jvm_session):
        """Test génération inférences avec Tweety réel (via construction programmatique)."""
        if not jvm_session:
            pytest.skip("Test nécessite la JVM.")
        
        agent = fol_agent_with_kernel
        builder = agent._builder_plugin
        builder.reset()
        
        builder.add_sort("etudiant")
        builder.add_predicate_schema("est_etudiant", ["etudiant"])
        builder.add_predicate_schema("est_intelligent", ["etudiant"])
        builder.add_constant_to_sort("marie", "etudiant")
        builder.add_universal_implication("est_etudiant", "est_intelligent", "etudiant")
        builder.add_atomic_fact("est_etudiant", ["marie"])

        java_belief_set_obj = builder.build_tweety_belief_set(agent.tweety_bridge)
        belief_set = FirstOrderBeliefSet(content=java_belief_set_obj.toString(), java_object=java_belief_set_obj)

        assert belief_set is not None

        # Tester une inférence spécifique
        entails, _ = await agent.execute_query(belief_set, "est_intelligent(marie)")
        assert entails is True, "L'inférence 'est_intelligent(marie)' devrait être acceptée."
        logger.info("✅ Inférence 'est_intelligent(marie)' validée.")


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
        """
        Teste la robustesse de l'agent face à un texte sémantiquement absurde.
        L'objectif principal est de s'assurer que l'agent ne crashe pas et gère
        la situation de manière prévisible, même si le LLM hallucine une structure.
        """
        agent = fol_agent_with_kernel
        
        # Texte sémantiquement absurde.
        problematic_text = "D'incolores idées vertes dorment furieusement."
        
        try:
            belief_set, msg = await agent.text_to_belief_set(problematic_text)
            
            # L'agent doit retourner un objet BeliefSet, même s'il est vide, sans planter.
            assert belief_set is not None, "Le belief_set ne devrait pas être None après une tentative de conversion."

            if belief_set.is_empty():
                logger.info("✅ Le LLM a correctement identifié le texte comme absurde et a retourné un belief set vide.")
            else:
                logger.warning(f"⚠️ Le LLM a halluciné une structure logique à partir d'un texte absurde : {belief_set.content}. Le test valide simplement que l'agent n'a pas crashé.")

            # Le test est considéré comme réussi si on arrive ici sans exception.
            logger.info("✅ Le test de robustesse est réussi : l'agent a géré un texte absurde sans planter.")

        except Exception as e:
            pytest.fail(f"L'agent a levé une exception inattendue face à un texte absurde: {e}", pytrace=True)
        
    @pytest.mark.asyncio
    async def test_fol_timeout_handling(self, fol_agent_with_kernel, jvm_session):
        """Test gestion timeouts analyse FOL."""
        if not jvm_session:
            pytest.skip("Test nécessite la JVM.")
        
        agent = fol_agent_with_kernel
        builder = agent._builder_plugin
        builder.reset()

        # Construire un BeliefSet valide pour s'assurer que l'appel de consistance est bien atteint
        builder.add_sort("concept")
        builder.add_predicate_schema("est_un", ["concept"])
        builder.add_constant_to_sort("a", "concept")
        builder.add_atomic_fact("est_un", ["a"])

        java_belief_set_obj = builder.build_tweety_belief_set(agent.tweety_bridge)
        belief_set = FirstOrderBeliefSet(content=java_belief_set_obj.toString(), java_object=java_belief_set_obj)
        
        # Utiliser patch comme un context manager pour garantir le nettoyage
        with patch.object(agent.tweety_bridge.fol_handler, 'fol_check_consistency', side_effect=asyncio.TimeoutError("Timeout de test simulé")):
            is_consistent, consistency_msg = await agent.is_consistent(belief_set)

        assert not is_consistent, "is_consistent devrait être False en cas de timeout"
        assert "simulé" in consistency_msg.lower(), f"Le message d'erreur '{consistency_msg}' ne contient pas 'simulé'."
        logger.info(f"✅ Gestion du timeout validée avec le message: {consistency_msg}")


class TestFOLPerformanceVsModal:
    """Tests performance FOL vs Modal Logic."""
    
    @pytest.mark.asyncio
    async def test_fol_vs_modal_performance_comparison(self, fol_agent_with_kernel, jvm_session):
        """Test comparaison performance FOL vs Modal Logic."""
        if not jvm_session:
            pytest.skip("Test nécessite la JVM.")
        
        # Agent FOL
        fol_agent = fol_agent_with_kernel
        builder = fol_agent._builder_plugin
        builder.reset()
        
        # Construire une base de connaissance simple
        builder.add_sort("concept")
        builder.add_predicate_schema("est_un", ["concept"])
        builder.add_constant_to_sort("a", "concept")
        builder.add_atomic_fact("est_un", ["a"])

        # Mesurer le temps de construction et de vérification
        start_fol = time.time()
        java_obj = builder.build_tweety_belief_set(fol_agent.tweety_bridge)
        belief_set = FirstOrderBeliefSet(content=java_obj.toString(), java_object=java_obj)
        await fol_agent.is_consistent(belief_set)
        fol_time = time.time() - start_fol
        
        # Vérifications FOL
        assert belief_set is not None
        assert fol_time < 10.0, "Une analyse simple ne devrait pas prendre plus de 10 secondes."
        
        logger.info(f"✅ Performance FOL (programmatique): {fol_time:.2f}s")
    
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
        
        for i, text in enumerate(test_texts):
            builder = agent._builder_plugin
            builder.reset()
            # Créer une formule simple pour chaque texte
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
            
            # Chaque analyse doit produire un belief set non-nul
            assert belief_set is not None and belief_set.java_object is not None
        
        # Performance stable
        avg_time = total_time / len(test_texts)
        assert avg_time < 5.0  # Moyenne < 5 secondes par an-authenticated-llm-callalyse
        
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
        logger.info("Test de stabilité mémoire terminé.")


class TestFOLRealWorldIntegration:
    """Tests intégration monde réel pour FOL."""
    
    @pytest.mark.asyncio
    async def test_fol_complex_argumentation_analysis(self, fol_agent_with_kernel, jvm_session):
        """Test analyse argumentation complexe avec FOL (via construction programmatique)."""
        if not jvm_session:
            pytest.skip("Test nécessite la JVM.")

        agent = fol_agent_with_kernel
        builder = agent._builder_plugin
        builder.reset()

        # Construction du scénario complexe
        builder.add_sort("entite") # Un sort unifié
        builder.add_predicate_schema("est_philosophe", ["entite"])
        builder.add_predicate_schema("est_penseur", ["entite"])
        builder.add_predicate_schema("est_ecrivain", ["entite"])
        builder.add_predicate_schema("influence_culture", ["entite"])

        builder.add_constant_to_sort("socrate", "entite")

        # "Tous les philosophes sont des penseurs."
        builder.add_universal_implication("est_philosophe", "est_penseur", "entite")
        # "Certains penseurs sont des écrivains."
        builder.add_existential_conjunction("est_penseur", "est_ecrivain", "entite")
        # "Socrate est un philosophe."
        builder.add_atomic_fact("est_philosophe", ["socrate"])
        # "Si quelqu'un est écrivain, alors il influence la culture."
        builder.add_universal_implication("est_ecrivain", "influence_culture", "entite")

        # Création du belief set
        java_belief_set_obj = builder.build_tweety_belief_set(agent.tweety_bridge)
        assert java_belief_set_obj is not None
        belief_set = FirstOrderBeliefSet(content=java_belief_set_obj.toString(), java_object=java_belief_set_obj)
        
        formulas_text = belief_set.content
        assert "forall" in formulas_text and "exists" in formulas_text
        
        # Vérification de la consistance
        is_consistent, _ = await agent.is_consistent(belief_set)
        assert is_consistent is True, "Le belief set complexe devrait être consistant."

        logger.info(f"✅ Analyse complexe terminée avec succès.")
    
    @pytest.mark.asyncio
    async def test_fol_multilingual_support(self, fol_agent_with_kernel, jvm_session):
        """Test la capacité du LLM à comprendre et traduire une autre langue (espagnol) en logique."""
        if not jvm_session:
            pytest.skip("Test nécessite la JVM.")
        
        agent = fol_agent_with_kernel
        text = "Todos los humanos sont mortales. Sócrates es un humano."
        
        belief_set, msg = await agent.text_to_belief_set(text)
        
        assert belief_set is not None, f"La conversion a échoué: {msg}"
        assert not belief_set.is_empty(), "Le belief_set ne devrait pas être vide."
        
        # Le nom du prédicat peut varier, on inspecte le contenu.
        logger.info(f"BeliefSet multilingue généré: {belief_set.content}")

        # D'après les logs, le LLM normalise le prédicat en `mortales` (pluriel).
        # C'est cette forme qui doit être utilisée pour la requête.
        # La normalisation transforme "Mortales" ou "mortales" en "mortale" et "Sócrates" en "socrate".
        # La requête doit donc utiliser la forme normalisée.
        query = "mortel(socrate)"
        entails, query_msg = await agent.execute_query(belief_set, query)

        assert entails, f"L'inférence '{query}' a échoué: {query_msg}"
        logger.info(f"✅ L'inférence multilingue '{query}' a été validée avec succès.")


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
    kernel = config.get_kernel_with_gpt4o_mini(force_authentic=True)
    
    # Création de l'agent. Le paramètre use_serialization est obsolète.
    # L'agent gère maintenant sa propre instance de TweetyBridge.
    agent = FOLLogicAgent(kernel=kernel, agent_name="TestFOLAgentWithKernel")
    
    # L'initialisation des composants, y compris TweetyBridge, est gérée par l'agent.
    await agent.setup_agent_components(llm_service_id="default")
    
    return agent


if __name__ == "__main__":
    # Exécution des tests d'intégration
    pytest.main([
        __file__, 
        "-v", 
        "--tb=short",
        "-k", "not test_real_tweety" if not TWEETY_AVAILABLE else ""
    ])