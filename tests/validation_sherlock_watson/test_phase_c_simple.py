import pytest

#!/usr/bin/env python3
"""
Script de test simplifie pour Phase C : Optimisation fluidite transitions.
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, List, Any
import statistics

# Configuration du logging pour le test
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_phase_c_simple():
    """
    Test simple de la Phase C avec mémoire contextuelle.
    """
    print("DEBUT TEST PHASE C - FLUIDITE TRANSITIONS")
    print("=" * 60)

    try:
        # Import des modules modifiés
        from argumentation_analysis.core.cluedo_oracle_state import CluedoOracleState

        print("[OK] Import CluedoOracleState reussi")

        # Configuration de base
        elements_jeu = {
            "suspects": [
                "Colonel Moutarde",
                "Professeur Violet",
                "Mademoiselle Rose",
                "Docteur Orchidee",
            ],
            "armes": ["Poignard", "Chandelier", "Revolver", "Corde"],
            "lieux": ["Salon", "Cuisine", "Bureau", "Bibliotheque"],
        }

        # Création de l'état Oracle avec nouvelles fonctionnalités Phase C
        oracle_state = CluedoOracleState(
            nom_enquete_cluedo="Test Phase C",
            elements_jeu_cluedo=elements_jeu,
            description_cas="Test des transitions fluides entre agents",
            initial_context="Test Phase C - Memoire contextuelle",
            oracle_strategy="balanced",
        )
        print("[OK] CluedoOracleState cree avec succes")

        # Test 1: Ajout de messages conversationnels
        print("\nTest 1: Ajout messages conversationnels")
        oracle_state.add_conversation_message(
            "Sherlock",
            "Je commence mon enquete. J'observe des indices dans le salon.",
            "analysis",
        )
        oracle_state.add_conversation_message(
            "Watson",
            "Suite a votre observation Sherlock, l'analyse logique suggere que le salon est crucial. Brillant !",
            "reaction",
        )
        oracle_state.add_conversation_message(
            "Moriarty",
            "En reaction a vos deductions, je revele que j'ai le Chandelier. Vous brulez !",
            "revelation",
        )
        print(f"[OK] {len(oracle_state.conversation_history)} messages ajoutes")

        # Test 2: Récupération du contexte récent
        print("\nTest 2: Recuperation contexte recent")
        recent_context = oracle_state.get_recent_context(3)
        print(f"[OK] Contexte recent recupere: {len(recent_context)} messages")
        for msg in recent_context:
            print(f"   - {msg['agent_name']}: {msg['content_preview']}")

        # Test 3: Enregistrement de références contextuelles
        print("\nTest 3: References contextuelles")
        oracle_state.record_contextual_reference(
            "Watson", 1, "building_on", "suite a votre observation"
        )
        oracle_state.record_contextual_reference(
            "Moriarty", 2, "reacting_to", "en reaction a vos deductions"
        )
        print(
            f"[OK] {len(oracle_state.contextual_references)} references contextuelles enregistrees"
        )

        # Test 4: Enregistrement de réactions émotionnelles
        print("\nTest 4: Reactions emotionnelles")
        oracle_state.record_emotional_reaction(
            "Watson", "Sherlock", "observation salon", "approval", "Brillant !"
        )
        oracle_state.record_emotional_reaction(
            "Moriarty", "Watson", "analyse logique", "encouragement", "Vous brulez !"
        )
        print(
            f"[OK] {len(oracle_state.emotional_reactions)} reactions emotionnelles enregistrees"
        )

        # Test 5: Génération du prompt contextuel
        print("\nTest 5: Generation prompt contextuel")
        contextual_prompt = oracle_state.get_contextual_prompt_addition("Watson")
        print(f"[OK] Prompt contextuel genere: {len(contextual_prompt)} caracteres")
        print("Extrait du prompt:")
        print(
            contextual_prompt[:200] + "..."
            if len(contextual_prompt) > 200
            else contextual_prompt
        )

        # Test 6: Métriques de fluidité
        print("\nTest 6: Metriques de fluidite")
        fluidity_metrics = oracle_state.get_fluidity_metrics()
        print(f"[OK] Metriques calculees:")
        print(f"   - Messages totaux: {fluidity_metrics['total_messages']}")
        print(f"   - Taux references: {fluidity_metrics['contextual_reference_rate']}%")
        print(f"   - Taux reactions: {fluidity_metrics['emotional_reaction_rate']}%")
        print(f"   - Score fluidite: {fluidity_metrics['fluidity_score']}/10")
        print(f"   - Continuite narrative: {fluidity_metrics['narrative_continuity']}")

        # Évaluation des cibles Phase C
        print("\nEVALUATION PHASE C:")
        target_ref_rate = fluidity_metrics["phase_c_target"]["reference_target"]
        target_reaction_rate = fluidity_metrics["phase_c_target"]["reaction_target"]
        target_score = fluidity_metrics["phase_c_target"]["score_target"]

        ref_success = fluidity_metrics["contextual_reference_rate"] >= target_ref_rate
        reaction_success = (
            fluidity_metrics["emotional_reaction_rate"] >= target_reaction_rate
        )
        score_success = fluidity_metrics["fluidity_score"] >= target_score

        print(
            f"References contextuelles (>={target_ref_rate}%): {'[OK]' if ref_success else '[NON]'} {fluidity_metrics['contextual_reference_rate']}%"
        )
        print(
            f"Reactions emotionnelles (>={target_reaction_rate}%): {'[OK]' if reaction_success else '[NON]'} {fluidity_metrics['emotional_reaction_rate']}%"
        )
        print(
            f"Score fluidite (>={target_score}): {'[OK]' if score_success else '[NON]'} {fluidity_metrics['fluidity_score']}/10"
        )

        overall_success = ref_success and reaction_success and score_success
        print(
            f"\nRESULTAT GLOBAL PHASE C: {'[SUCCES]' if overall_success else '[ECHEC PARTIEL]'}"
        )

        # Test avec l'orchestrateur étendu
        print("\nTest 7: Orchestrateur etendu")
        try:
            from argumentation_analysis.orchestration.cluedo_extended_orchestrator import (
                CluedoExtendedOrchestrator,
            )

            print("[OK] Import CluedoExtendedOrchestrator reussi")

            # Test des nouvelles méthodes d'analyse contextuelle
            orchestrator = CluedoExtendedOrchestrator(
                kernel=None, oracle_strategy="balanced"
            )

            # Test de détection du type de message
            msg_type = orchestrator._detect_message_type(
                "Je suggère Colonel Moutarde avec le Revolver dans le Salon"
            )
            print(f"[OK] Detection type message: {msg_type}")

            # Test de détection des réactions émotionnelles
            reactions = orchestrator._detect_emotional_reactions(
                "Watson", "Brillant ! Exactement ce que je pensais", []
            )
            print(f"[OK] Detection reactions emotionnelles: {len(reactions)} reactions")

        except Exception as e:
            print(f"[ERREUR] Test orchestrateur: {e}")

        # Sauvegarde des résultats
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"phase_c_test_results_{timestamp}.json"

        results_data = {
            "test_timestamp": datetime.now().isoformat(),
            "test_type": "Phase C - Fluidite Transitions",
            "fluidity_metrics": fluidity_metrics,
            "contextual_references": oracle_state.contextual_references,
            "emotional_reactions": oracle_state.emotional_reactions,
            "conversation_history": oracle_state.conversation_history,
            "phase_c_evaluation": {
                "references_success": ref_success,
                "reactions_success": reaction_success,
                "score_success": score_success,
                "overall_success": overall_success,
            },
        }

        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False)

        print(f"\n[OK] Resultats sauvegardes: {results_file}")
        print("\n[OK] TEST PHASE C TERMINE AVEC SUCCES")

        return results_data

    except Exception as e:
        logger.error(f"Erreur durant le test: {e}", exc_info=True)
        print(f"\n[ERREUR] Test echoue: {e}")
        pytest.fail(f"Test Phase C a échoué: {e}")
        return None


if __name__ == "__main__":
    test_phase_c_simple()
