"""
Tests authentiques pour InformalAnalysisAgent - Phase 5 Mock Elimination
Remplace complètement les mocks par des composants authentiques
"""

import os
import sys
import time
import json
import pytest
from typing import Optional, List, Dict
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.chat_message_content import ChatMessageContent

# Import auto-configuration environnement
from argumentation_analysis.core import environment as auto_env
from .fixtures_authentic import simple_authentic_informal_agent

# Imports fixtures authentiques
from .fixtures_authentic import (
    authentic_semantic_kernel,
    authentic_fallacy_detector,
    authentic_rhetorical_analyzer,
    authentic_contextual_analyzer,
    authentic_informal_agent,
    setup_authentic_taxonomy_csv,
    authentic_informal_analysis_plugin,
    sample_authentic_test_text,
)

# Imports composants authentiques
from argumentation_analysis.agents.core.informal.informal_agent import (
    InformalAnalysisAgent,
)
from argumentation_analysis.agents.core.informal.informal_definitions import (
    InformalAnalysisPlugin,
)


class TestInformalAnalysisAgentAuthentic:
    """
    Tests authentiques pour InformalAnalysisAgent - Sans mocks, composants réels

    Phase 5: Élimination complète des mocks
    - Semantic Kernel authentique avec connecteurs Azure/OpenAI réels
    - Détecteurs de sophismes authentiques avec vraie logique
    - Analyseurs rhétoriques et contextuels authentiques
    - InformalAnalysisAgent sans mocks
    - Tests d'analyse argumentative avec taxonomie réelle
    """

    @pytest.mark.llm_integration
    @pytest.mark.phase5
    @pytest.mark.informal
    def test_initialization_and_setup_authentic(self, authentic_informal_agent):
        """
        Test authentique d'initialisation et configuration - AUCUN MOCK
        """
        start_time = time.time()

        agent = authentic_informal_agent

        # Vérifications de base authentiques
        assert agent.name == "authentic_informal_agent"
        assert agent.kernel is not None
        # Le nouvel agent 'ChatCompletionAgent' n'a plus de 'kernel_wrapper'
        # assert hasattr(agent, 'kernel_wrapper')

        # Le nouvel agent expose ses fonctions (outils) via la propriété 'plugins'
        # Correction: Les plugins sont dans le kernel, pas directement sur l'agent.
        assert agent.kernel.plugins is not None
        assert len(agent.kernel.plugins) > 0

        # On vérifie la présence d'au moins un plugin important
        assert "FallacyIdentificationPlugin" in agent.kernel.plugins

        print(
            f"[AUTHENTIC] Plugins chargés dans le kernel de l'agent: {list(agent.kernel.plugins.keys())}"
        )

        # Les méthodes get_agent_capabilities() et get_agent_info() n'existent plus
        # sur le ChatCompletionAgent. On vérifie les attributs directement.
        assert agent.instructions is not None
        assert len(agent.instructions) > 10
        assert (
            agent.id is not None
        )  # L'id du service LLM est dans le kernel, pas directement sur l'agent

        print(
            f"[AUTHENTIC] Agent initialisé avec un prompt de {len(agent.instructions)} caractères."
        )

        execution_time = time.time() - start_time
        print(f"[AUTHENTIC] Test d'initialisation terminé en {execution_time:.2f}s")

    @pytest.mark.asyncio
    @pytest.mark.llm_integration
    @pytest.mark.phase5
    @pytest.mark.informal
    async def test_analyze_fallacies_authentic(
        self, simple_authentic_informal_agent, sample_authentic_test_text
    ):
        """
        Test authentique d'analyse de sophismes avec vrai LLM, utilisant le nouveau paradigme d'invocation.
        """
        if not simple_authentic_informal_agent.id:
            pytest.skip("Service LLM non configuré - test authentique impossible")

        start_time = time.time()

        agent = simple_authentic_informal_agent
        text = sample_authentic_test_text

        # Le 'full' agent configuré dans la fixture devrait utiliser des outils.
        chat_history = ChatHistory()
        prompt = (
            "Instruction: Tu es un expert en analyse argumentative. Analyse le texte fourni pour identifier les sophismes. "
            f"Texte à analyser: '{text}'"
        )
        chat_history.add_user_message(prompt)

        try:
            # InformalFallacyAgent.analyze_text() returns a FunctionResult from SK,
            # not a structured dict. We extract the text and validate the content.
            result = await agent.analyze_text(text, analysis_type="fallacies")
            result_text = str(result)

            print(
                f"[AUTHENTIC] Réponse de l'agent (analyse de sophismes): {result_text[:500]}"
            )

            # Vérifier que l'analyse est substantielle
            assert len(result_text) > 100, f"L'analyse est trop courte: {result_text[:200]}"

            # Vérifier que l'analyse mentionne des sophismes/fallacies
            result_lower = result_text.lower()
            assert any(
                term in result_lower
                for term in ["sophisme", "fallac", "appel à", "faux dilemme", "ad hominem"]
            ), f"L'analyse ne mentionne aucun sophisme: {result_text[:500]}"

        except Exception as e:
            pytest.fail(
                f"L'invocation de l'agent a échoué avec une exception non gérée: {e}",
                pytrace=True,
            )

        execution_time = time.time() - start_time
        print(
            f"[AUTHENTIC] Test d'analyse de sophismes (invoke) terminé en {execution_time:.2f}s"
        )

    @pytest.mark.asyncio
    @pytest.mark.llm_integration
    @pytest.mark.phase5
    @pytest.mark.informal
    async def test_identify_arguments_authentic(
        self, simple_authentic_informal_agent, sample_authentic_test_text
    ):
        """
        Test authentique d'identification d'arguments via le nouveau paradigme d'invocation.
        """
        if not simple_authentic_informal_agent.id:
            pytest.skip("Service LLM non configuré - test authentique impossible")

        start_time = time.time()

        agent = simple_authentic_informal_agent
        text = sample_authentic_test_text

        # On utilise ChatHistory pour formuler une demande claire
        prompt = (
            "Instruction: Tu es un expert en analyse argumentative. Identifie les arguments principaux dans le texte suivant. "
            f"Texte à analyser: '{text}'"
        )
        chat_history = ChatHistory()
        chat_history.add_user_message(prompt)

        try:
            # InformalFallacyAgent.analyze_text() returns a FunctionResult from SK,
            # not a structured dict. We extract the text and validate the content.
            result = await agent.analyze_text(text, analysis_type="arguments")
            result_text = str(result)

            print(
                f"[AUTHENTIC] Réponse de l'agent (identification d'arguments): {result_text[:500]}"
            )

            # Vérifier que l'analyse est substantielle
            assert len(result_text) > 100, f"L'analyse est trop courte: {result_text[:200]}"

            # Vérifier que l'analyse identifie des arguments
            result_lower = result_text.lower()
            assert any(
                term in result_lower
                for term in ["argument", "affirm", "prétend", "soutien", "expert"]
            ), f"L'analyse ne mentionne aucun argument: {result_text[:500]}"

        except Exception as e:
            pytest.fail(
                f"L'invocation directe de 'analyze_text' a échoué: {e}", pytrace=True
            )

        execution_time = time.time() - start_time
        print(
            f"[AUTHENTIC] Test d'identification d'arguments (invoke) terminé en {execution_time:.2f}s"
        )

    @pytest.mark.asyncio
    @pytest.mark.llm_integration
    @pytest.mark.phase5
    @pytest.mark.informal
    async def test_analyze_argument_authentic(self, simple_authentic_informal_agent):
        """
        Test authentique d'analyse d'argument, refactorisé pour utiliser une invocation directe.
        """
        if not simple_authentic_informal_agent.id:
            pytest.skip("Service LLM non configuré - test authentique impossible")

        start_time = time.time()

        agent = simple_authentic_informal_agent
        test_argument = "Les experts affirment que ce produit est sûr. N'est-il pas évident que vous devriez l'acheter?"

        try:
            # InformalFallacyAgent.analyze_text() returns a FunctionResult from SK.
            result = await agent.analyze_text(test_argument, analysis_type="fallacies")
            result_text = str(result)

            print(
                f"[AUTHENTIC] Réponse de l'agent (analyse d'argument): {result_text[:500]}"
            )

            # Vérifier que l'analyse est substantielle
            assert len(result_text) > 50, f"L'analyse est trop courte: {result_text[:200]}"

            # Vérifier que l'analyse détecte un appel à l'autorité
            result_lower = result_text.lower()
            assert any(
                term in result_lower
                for term in ["appel à l'autorité", "appeal to authority", "autorité", "expert"]
            ), f"L'analyse ne détecte pas l'appel à l'autorité: {result_text[:500]}"

        except Exception as e:
            pytest.fail(
                f"L'invocation directe de 'analyze_text' a échoué pour l'analyse d'argument: {e}",
                pytrace=True,
            )

        execution_time = time.time() - start_time
        print(
            f"[AUTHENTIC] Test d'analyse d'argument (invoke) terminé en {execution_time:.2f}s"
        )

    @pytest.mark.asyncio
    @pytest.mark.llm_integration
    @pytest.mark.phase5
    @pytest.mark.informal
    async def test_analyze_text_authentic(
        self, authentic_informal_agent, sample_authentic_test_text
    ):
        """
        Test authentique d'analyse de texte complète via le nouveau paradigme d'invocation.
        """
        if not authentic_informal_agent.id:
            pytest.skip("Service LLM non configuré - test authentique impossible")

        start_time = time.time()

        agent = authentic_informal_agent
        text = sample_authentic_test_text

        # On utilise ChatHistory pour formuler une demande claire
        prompt = (
            "Instruction: Tu es un expert en analyse argumentative. Analyse de manière complète le texte suivant, en identifiant les arguments, les sophismes et le ton général. "
            f"Texte à analyser: '{text}'"
        )
        chat_history = ChatHistory()
        chat_history.add_user_message(prompt)

        final_answer = None
        try:
            async for result in agent.invoke(chat_history):
                # BaseAgent.invoke() yields the full result from invoke_single().
                # This can be a list, a FunctionResult, or a ChatMessageContent.
                if isinstance(result, list):
                    for msg in result:
                        if isinstance(msg, ChatMessageContent) and msg.role == "assistant":
                            final_answer = msg.content if isinstance(msg.content, str) else str(msg.content)
                elif isinstance(result, ChatMessageContent) and result.role == "assistant":
                    final_answer = result.content if isinstance(result.content, str) else str(result.content)
                elif result is not None:
                    # FunctionResult or other SK type
                    final_answer = str(result)

            # Vérification de la réponse finale
            assert (
                final_answer is not None
            ), "L'agent n'a pas produit de réponse finale."
            print(f"[AUTHENTIC] Réponse de l'agent (analyse de texte): {final_answer[:500]}")

            # Vérification de base du contenu
            final_answer_lower = final_answer.lower()
            assert any(
                term in final_answer_lower
                for term in ["analyse", "sophisme", "argument", "fallac"]
            ), f"Réponse ne contient pas les termes attendus: {final_answer[:300]}"

        except Exception as e:
            pytest.fail(
                f"L'invocation de l'agent a échoué pour l'analyse de texte: {e}"
            )

        execution_time = time.time() - start_time
        print(
            f"[AUTHENTIC] Test d'analyse de texte (invoke) terminé en {execution_time:.2f}s"
        )

    @pytest.mark.llm_integration
    @pytest.mark.phase5
    @pytest.mark.informal
    def test_fallacy_detection_local_authentic(
        self, authentic_fallacy_detector, sample_authentic_test_text
    ):
        """
        Test authentique du détecteur de sophismes local (sans LLM)
        """
        start_time = time.time()

        detector = authentic_fallacy_detector
        text = sample_authentic_test_text

        # Détection authentique locale
        fallacies = detector.detect(text)

        # Vérifications authentiques
        assert isinstance(fallacies, list)
        print(f"[AUTHENTIC] Sophismes détectés localement: {len(fallacies)}")

        for fallacy in fallacies:
            assert isinstance(fallacy, dict)
            assert "fallacy_type" in fallacy
            assert "text" in fallacy
            assert "confidence" in fallacy
            assert "details" in fallacy
            assert "pattern" in fallacy

            assert isinstance(fallacy["confidence"], float)
            assert 0.0 <= fallacy["confidence"] <= 1.0

            print(
                f"[AUTHENTIC] Sophisme local: {fallacy['fallacy_type']} (confiance: {fallacy['confidence']:.2f})"
            )

        execution_time = time.time() - start_time
        print(f"[AUTHENTIC] Test de détection locale terminé en {execution_time:.2f}s")

    @pytest.mark.llm_integration
    @pytest.mark.phase5
    @pytest.mark.informal
    def test_rhetorical_analysis_authentic(
        self, authentic_rhetorical_analyzer, sample_authentic_test_text
    ):
        """
        Test authentique de l'analyseur rhétorique
        """
        start_time = time.time()

        analyzer = authentic_rhetorical_analyzer
        text = sample_authentic_test_text

        # Analyse rhétorique authentique
        analysis = analyzer.analyze(text)

        # Vérifications authentiques
        assert isinstance(analysis, dict)
        assert "tone" in analysis
        assert "style" in analysis
        assert "techniques" in analysis
        assert "effectiveness" in analysis
        assert "tone_scores" in analysis

        assert isinstance(analysis["techniques"], list)
        assert isinstance(analysis["effectiveness"], float)
        assert 0.0 <= analysis["effectiveness"] <= 1.0
        assert isinstance(analysis["tone_scores"], dict)

        print(f"[AUTHENTIC] Ton: {analysis['tone']}")
        print(f"[AUTHENTIC] Style: {analysis['style']}")
        print(f"[AUTHENTIC] Techniques: {analysis['techniques']}")
        print(f"[AUTHENTIC] Efficacité: {analysis['effectiveness']:.2f}")

        execution_time = time.time() - start_time
        print(f"[AUTHENTIC] Test d'analyse rhétorique terminé en {execution_time:.2f}s")

    @pytest.mark.llm_integration
    @pytest.mark.phase5
    @pytest.mark.informal
    def test_contextual_analysis_authentic(
        self, authentic_contextual_analyzer, sample_authentic_test_text
    ):
        """
        Test authentique de l'analyseur contextuel
        """
        start_time = time.time()

        analyzer = authentic_contextual_analyzer
        text = sample_authentic_test_text

        # Analyse contextuelle authentique
        analysis = analyzer.analyze_context(text)

        # Vérifications authentiques
        assert isinstance(analysis, dict)
        assert "context_type" in analysis
        assert "audience" in analysis
        assert "intent" in analysis
        assert "confidence" in analysis
        assert "all_contexts" in analysis

        assert isinstance(analysis["confidence"], float)
        assert 0.0 <= analysis["confidence"] <= 1.0
        assert isinstance(analysis["all_contexts"], dict)

        print(f"[AUTHENTIC] Type de contexte: {analysis['context_type']}")
        print(f"[AUTHENTIC] Audience: {analysis['audience']}")
        print(f"[AUTHENTIC] Intention: {analysis['intent']}")
        print(f"[AUTHENTIC] Confiance: {analysis['confidence']:.2f}")

        execution_time = time.time() - start_time
        print(
            f"[AUTHENTIC] Test d'analyse contextuelle terminé en {execution_time:.2f}s"
        )

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.llm_integration
    @pytest.mark.phase5
    @pytest.mark.informal
    async def test_complete_informal_analysis_workflow_authentic(
        self, authentic_informal_agent, sample_authentic_test_text
    ):
        """
        Test authentique du workflow complet d'analyse informelle via une seule invocation.
        """
        if not authentic_informal_agent.id:
            pytest.skip("Service LLM requis pour test intégration authentique")

        start_time = time.time()

        agent = authentic_informal_agent
        text = sample_authentic_test_text

        # On formule un prompt complexe qui demande un workflow complet
        prompt = (
            "Instruction: Tu es un expert en analyse argumentative. "
            "Effectue une analyse argumentative complète du texte suivant. "
            "Je veux que tu identifies les arguments principaux, que tu listes les sophismes présents, "
            "et que tu fournisses un résumé global de ta conclusion. "
            f"Texte à analyser: '{text}'"
        )

        chat_history = ChatHistory()
        chat_history.add_user_message(prompt)

        final_answer = None
        try:
            async for result in agent.invoke(chat_history):
                # BaseAgent.invoke() yields the full result from invoke_single().
                if isinstance(result, list):
                    for msg in result:
                        if isinstance(msg, ChatMessageContent) and msg.role == "assistant":
                            final_answer = msg.content if isinstance(msg.content, str) else str(msg.content)
                elif isinstance(result, ChatMessageContent) and result.role == "assistant":
                    final_answer = result.content if isinstance(result.content, str) else str(result.content)
                elif result is not None:
                    final_answer = str(result)

            # Vérification de la réponse finale
            assert (
                final_answer is not None
            ), "L'agent n'a pas produit de réponse finale."
            print(f"[AUTHENTIC] Réponse de l'agent (workflow complet): {final_answer[:500]}")

            # Vérification que la réponse contient les éléments clés du workflow
            final_answer_lower = final_answer.lower()
            assert any(
                term in final_answer_lower
                for term in ["argument", "sophisme", "fallac", "analyse"]
            ), f"Réponse ne contient pas les termes attendus: {final_answer[:300]}"

        except Exception as e:
            pytest.fail(
                f"L'invocation de l'agent a échoué pour le workflow complet: {e}"
            )

        execution_time = time.time() - start_time
        print(
            f"[AUTHENTIC] Test du workflow complet (invoke) terminé en {execution_time:.2f}s"
        )

    @pytest.mark.performance
    @pytest.mark.llm_integration
    @pytest.mark.phase5
    @pytest.mark.informal
    def test_local_components_performance_authentic(
        self,
        authentic_fallacy_detector,
        authentic_rhetorical_analyzer,
        authentic_contextual_analyzer,
    ):
        """
        Test authentique de performance des composants locaux
        """
        start_time = time.time()

        # Textes de test variés
        test_texts = [
            "Les experts affirment que ce produit est révolutionnaire.",
            "Vous êtes trop jeune pour comprendre cette situation complexe.",
            "Si nous permettons cela, bientôt tout sera autorisé.",
            "N'est-ce pas évident que cette solution est la meilleure?",
            "Pensez aux enfants qui souffriront de cette décision.",
        ]

        total_fallacies = 0
        total_analyses = 0

        for i, text in enumerate(test_texts):
            # Test détecteur de sophismes
            fallacies = authentic_fallacy_detector.detect(text)
            total_fallacies += len(fallacies)

            # Test analyseur rhétorique
            rhetorical = authentic_rhetorical_analyzer.analyze(text)
            assert isinstance(rhetorical, dict)

            # Test analyseur contextuel
            contextual = authentic_contextual_analyzer.analyze_context(text)
            assert isinstance(contextual, dict)

            total_analyses += 3
            print(f"[AUTHENTIC] Texte {i+1}: {len(fallacies)} sophismes détectés")

        execution_time = time.time() - start_time

        print(
            f"[AUTHENTIC] Performance: {total_analyses} analyses en {execution_time:.2f}s"
        )
        print(f"[AUTHENTIC] Total sophismes détectés: {total_fallacies}")
        if execution_time > 0:
            print(
                f"[AUTHENTIC] Vitesse: {total_analyses/execution_time:.1f} analyses/seconde"
            )
        else:
            print("[AUTHENTIC] Vitesse: Exécution trop rapide pour mesurer.")

        # Performance attendue : traitement rapide local
        assert execution_time < 2.0  # Moins de 2 secondes pour traitement local


# Marqueurs pytest pour organisation des tests authentiques
pytestmark = [
    pytest.mark.llm_integration,  # Tests LLM intégration (remplace authentic + no_mocks)
    pytest.mark.phase5,  # Marqueur Phase 5
    pytest.mark.informal,  # Marqueur spécifique analyse informelle
]


if __name__ == "__main__":
    # Exécution directe pour débogage
    pytest.main([__file__, "-v", "--tb=short"])
