import argumentation_analysis.core.environment

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test simple du système d'analyse rhétorique unifié
=================================================
"""

import asyncio
import logging
import os
from argumentation_analysis.pipelines.unified_text_analysis import (
    UnifiedTextAnalysisPipeline,
    UnifiedAnalysisConfig,
)
from argumentation_analysis.orchestration.conversation_orchestrator import (
    ConversationOrchestrator,
)
from argumentation_analysis.orchestration.real_llm_orchestrator import (
    RealLLMOrchestrator,
)


async def test_unified_pipeline():
    """Test du pipeline unifié."""
    print("[TEST] Pipeline unifié...")

    try:
        # Respecter l'environnement pour l'authenticité
        use_mocks = os.getenv("FORCE_AUTHENTIC_EXECUTION", "false").lower() != "true"

        config = UnifiedAnalysisConfig(
            analysis_modes=["fallacies", "coherence"],
            logic_type="propositional",
            use_mocks=use_mocks,  # Respecte FORCE_AUTHENTIC_EXECUTION
            orchestration_mode="standard",
        )

        pipeline = UnifiedTextAnalysisPipeline(config)
        await pipeline.initialize()

        # Test avec un texte simple
        text = (
            "L'intelligence artificielle transforme notre société de manière profonde."
        )
        result = await pipeline.analyze_text_unified(text)

        print(f"[OK] Pipeline unifié - Analyse terminée")
        print(
            f"     Modes: {', '.join(result['metadata']['analysis_config']['analysis_modes'])}"
        )
        print(f"     Temps: {result['metadata']['processing_time_ms']:.1f}ms")
        print(
            f"     Fallacies détectés: {len(result.get('informal_analysis', {}).get('fallacies', []))}"
        )

        return True

    except Exception as e:
        print(f"[ERROR] Pipeline unifié: {e}")
        return False


def test_conversation_orchestrator():
    """Test de l'orchestrateur conversationnel."""
    print("[TEST] Orchestrateur conversationnel...")

    try:
        orchestrator = ConversationOrchestrator(mode="micro")
        text = "L'argumentation logique est essentielle pour un débat constructif."

        report = orchestrator.run_orchestration(text)

        print(f"[OK] Orchestrateur conversationnel - Rapport généré")
        print(f"     Mode: {orchestrator.mode}")
        print(f"     Agents: {len(orchestrator.agents)}")
        print(f"     Messages: {len(orchestrator.conv_logger.messages)}")

        return True

    except Exception as e:
        print(f"[ERROR] Orchestrateur conversationnel: {e}")
        return False


async def test_real_llm_orchestrator():
    """Test de l'orchestrateur LLM réel."""
    print("[TEST] Orchestrateur LLM réel...")

    try:
        orchestrator = RealLLMOrchestrator(mode="real")
        await orchestrator.initialize()

        text = "La rhétorique aristotélicienne distingue ethos, pathos et logos."
        result = await orchestrator.orchestrate_analysis(text)

        print(f"[OK] Orchestrateur LLM réel - Analyse terminée")
        print(f"     Temps: {result['processing_time_ms']:.1f}ms")
        print(
            f"     Messages: {len(result.get('conversation_log', {}).get('messages', []))}"
        )

        return True

    except Exception as e:
        print(f"[ERROR] Orchestrateur LLM réel: {e}")
        return False


async def main():
    """Fonction principale de test."""
    print("=" * 60)
    print("TEST DU SYSTÈME D'ANALYSE RHÉTORIQUE UNIFIÉ")
    print("=" * 60)
    print()

    # Configurer le logging pour réduire le bruit
    logging.getLogger().setLevel(logging.ERROR)

    results = []

    # Test 1: Pipeline unifié
    results.append(await test_unified_pipeline())
    print()

    # Test 2: Orchestrateur conversationnel
    results.append(test_conversation_orchestrator())
    print()

    # Test 3: Orchestrateur LLM réel
    results.append(await test_real_llm_orchestrator())
    print()

    # Résumé
    print("=" * 60)
    print("RÉSUMÉ DES TESTS")
    print("=" * 60)

    tests = [
        "Pipeline unifié",
        "Orchestrateur conversationnel",
        "Orchestrateur LLM réel",
    ]

    passed = sum(results)
    total = len(results)

    for i, (test_name, result) in enumerate(zip(tests, results)):
        status = "[OK]" if result else "[FAIL]"
        print(f"{status} {test_name}")

    print()
    print(f"BILAN: {passed}/{total} tests réussis ({passed/total*100:.0f}%)")

    if passed == total:
        print(
            "[SUCCESS] Tous les composants du système d'analyse rhétorique fonctionnent!"
        )
        return 0
    else:
        print("[WARNING] Certains composants nécessitent des corrections")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
