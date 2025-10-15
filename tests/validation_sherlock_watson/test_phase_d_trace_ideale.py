import pytest

#!/usr/bin/env python3
"""
Test Phase D : Validation de la trace idéale avec score 8.0+/10

Ce test valide toutes les optimisations Phase D :
- Révélations progressives Moriarty avec fausses pistes
- Système de retournements narratifs
- Polish conversationnel avancé
- Métriques de la trace idéale
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, List, Any
import statistics

# Import des extensions Phase D
from argumentation_analysis.agents.core.oracle.phase_d_extensions import (
    PhaseDExtensions,
    extend_oracle_state_phase_d,
)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_phase_d_trace_ideale():
    """
    Test complet de la Phase D pour atteindre la trace idéale (8.0+/10).
    """
    print("DEBUT TEST PHASE D - TRACE IDEALE")
    print("=" * 70)

    try:
        # Import et préparation
        from argumentation_analysis.core.cluedo_oracle_state import CluedoOracleState
        from argumentation_analysis.orchestration.cluedo_extended_orchestrator import (
            CluedoExtendedOrchestrator,
        )

        print("[OK] Imports réussis")

        # Étendre CluedoOracleState avec Phase D
        extend_oracle_state_phase_d(CluedoOracleState)
        print("[OK] Extensions Phase D appliquées")

        # Configuration du jeu
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

        # Création de l'état Oracle étendu Phase D
        oracle_state = CluedoOracleState(
            nom_enquete_cluedo="Phase D - Trace Ideale",
            elements_jeu_cluedo=elements_jeu,
            description_cas="Test de la trace idéale avec optimisations avancées",
            initial_context="Phase D - Révélations dramatiques et polish conversationnel",
            oracle_strategy="balanced",
        )

        # Initialisation Phase D
        oracle_state.__init_phase_d__()
        print("[OK] État Oracle Phase D créé")

        # SCÉNARIO 1: Test des révélations progressives
        print("\n" + "=" * 50)
        print("SCÉNARIO 1: RÉVÉLATIONS PROGRESSIVES")
        print("=" * 50)

        # Simulation d'une conversation avec révélations dramatiques
        conversation_scenario = [
            {
                "agent": "Sherlock",
                "content": "Mes observations du salon me mènent à une hypothèse précise.",
                "type": "analysis",
            },
            {
                "agent": "Watson",
                "content": "Suite à votre brillante analyse Sherlock, je confirme la logique.",
                "type": "reaction",
            },
            {
                "agent": "Moriarty",
                "content": oracle_state.add_dramatic_revelation(
                    "J'ai le Chandelier dans mes cartes !",
                    intensity=0.9,
                    use_false_lead=True,
                ),
                "type": "revelation",
            },
            {
                "agent": "Watson",
                "content": oracle_state.apply_conversational_polish_to_message(
                    "Watson", "Aha ! Cette révélation change tout !"
                ),
                "type": "reaction",
            },
            {
                "agent": "Sherlock",
                "content": oracle_state.apply_conversational_polish_to_message(
                    "Sherlock",
                    "Précisément ce que je soupçonnais. Continuons l'analyse.",
                ),
                "type": "analysis",
            },
        ]

        # Ajout des messages à l'historique
        for msg in conversation_scenario:
            oracle_state.add_conversation_message(
                msg["agent"], msg["content"], msg["type"]
            )
            print(f"\n[{msg['agent']}]: {msg['content'][:100]}...")

        print(f"\n[OK] {len(conversation_scenario)} messages ajoutés avec dramaturgie")

        # SCÉNARIO 2: Test des retournements narratifs
        print("\n" + "=" * 50)
        print("SCÉNARIO 2: RETOURNEMENTS NARRATIFS")
        print("=" * 50)

        # Extensions Phase D pour retournements
        extensions = PhaseDExtensions()

        # Génération d'un retournement narratif
        context = {"turn_number": len(oracle_state.conversation_history)}
        narrative_twist = extensions.generate_narrative_twist(context)

        if narrative_twist:
            print(f"[OK] Retournement généré: {narrative_twist.twist_type.value}")
            print(f"Setup: {narrative_twist.setup_content}")
            print(f"Payoff: {narrative_twist.payoff_content}")
            print(f"Impact: {narrative_twist.emotional_impact}")
        else:
            print("[INFO] Aucun retournement généré pour ce contexte")

        # SCÉNARIO 3: Progression avec crescendo
        print("\n" + "=" * 50)
        print("SCÉNARIO 3: CRESCENDO FINAL")
        print("=" * 50)

        # Simulation d'approche de la solution
        final_context = {
            "final_revelation": "Colonel Moutarde avec le Revolver dans le Bureau !",
            "turn_number": len(oracle_state.conversation_history),
        }

        crescendo_moment = extensions.generate_crescendo_moment(final_context)
        oracle_state.add_conversation_message("Moriarty", crescendo_moment, "crescendo")

        print("[OK] Crescendo final généré:")
        print(crescendo_moment[:200] + "...")

        # SCÉNARIO 4: Calcul des métriques trace idéale
        print("\n" + "=" * 50)
        print("SCÉNARIO 4: MÉTRIQUES TRACE IDÉALE")
        print("=" * 50)

        # Calcul des métriques Phase D
        ideal_metrics = oracle_state.get_ideal_trace_metrics()

        print("\nMÉTRIQUES TRACE IDÉALE:")
        print("-" * 30)

        for metric_name, score in ideal_metrics.items():
            status = "[OK]" if score >= 8.0 else "⚠️" if score >= 7.0 else "[FAIL]"
            print(f"{status} {metric_name.replace('_', ' ').title()}: {score:.1f}/10")

        # Score global et évaluation
        global_score = ideal_metrics["score_trace_ideale"]
        success_threshold = 8.0

        print(f"\n{'='*40}")
        print(f"SCORE TRACE IDÉALE: {global_score:.1f}/10")
        print(f"OBJECTIF PHASE D: {success_threshold}/10")

        if global_score >= success_threshold:
            print("🎉 TRACE IDÉALE ATTEINTE ! SUCCÈS PHASE D")
            success_status = "SUCCES"
        else:
            print("⚠️  Trace idéale non atteinte, optimisations nécessaires")
            success_status = "PARTIEL"

        # SCÉNARIO 5: Tests utilisateur simulés
        print("\n" + "=" * 50)
        print("SCÉNARIO 5: TESTS UTILISATEUR SIMULÉS")
        print("=" * 50)

        # Simulation de 3 conversations complètes
        user_test_scores = []

        for test_id in range(1, 4):
            print(f"\nTest utilisateur #{test_id}:")

            # Simulation d'une conversation complète
            test_conversation = []

            # 8-10 messages par test pour avoir assez de données
            test_messages = [
                (
                    "Sherlock",
                    "J'analyse les indices présents dans cette pièce.",
                    "analysis",
                ),
                (
                    "Watson",
                    "Brillante approche ! Je suis votre raisonnement.",
                    "reaction",
                ),
                (
                    "Moriarty",
                    extensions.generate_progressive_revelation(
                        "", f"Test {test_id}: J'ai le Professeur Violet !", 0.8
                    ),
                    "revelation",
                ),
                ("Watson", "Exactement ce que je pensais ! Continuons.", "reaction"),
                (
                    "Sherlock",
                    "Précisément. Cette information affine notre recherche.",
                    "analysis",
                ),
                (
                    "Moriarty",
                    "*pause dramatique* Voici une autre révélation...",
                    "revelation",
                ),
                ("Watson", "Aha ! Le mystère s'éclaircit !", "reaction"),
                (
                    "Sherlock",
                    "Logique implacable. Nous approchons de la solution.",
                    "analysis",
                ),
            ]

            # Ajout des messages avec polish
            for agent, content, msg_type in test_messages:
                polished_content = oracle_state.apply_conversational_polish_to_message(
                    agent, content
                )
                test_conversation.append(
                    {
                        "agent_name": agent,
                        "content": polished_content,
                        "message_type": msg_type,
                    }
                )

            # Calcul du score pour ce test
            test_data = {"messages": test_conversation}
            test_score = extensions.calculate_ideal_trace_metrics(test_data)[
                "score_trace_ideale"
            ]
            user_test_scores.append(test_score)

            print(f"   Score: {test_score:.1f}/10")

        # Score moyen des tests utilisateur
        average_user_score = statistics.mean(user_test_scores)
        print(f"\nSCORE MOYEN TESTS UTILISATEUR: {average_user_score:.1f}/10")

        # VALIDATION FINALE
        print("\n" + "=" * 70)
        print("VALIDATION FINALE PHASE D")
        print("=" * 70)

        # Critères de validation Phase D
        validation_criteria = {
            "Score trace idéale (≥8.0)": global_score >= 8.0,
            "Naturalité dialogue (≥7.5)": ideal_metrics["naturalite_dialogue"] >= 7.5,
            "Personnalités distinctes (≥7.5)": ideal_metrics["personnalites_distinctes"]
            >= 7.5,
            "Fluidité transitions (≥7.0)": ideal_metrics["fluidite_transitions"] >= 7.0,
            "Progression logique (≥8.0)": ideal_metrics["progression_logique"] >= 8.0,
            "Dosage révélations (≥8.0)": ideal_metrics["dosage_revelations"] >= 8.0,
            "Engagement global (≥8.0)": ideal_metrics["engagement_global"] >= 8.0,
            "Tests utilisateur (≥7.5)": average_user_score >= 7.5,
        }

        print("\nCRITÈRES DE VALIDATION:")
        passed_criteria = 0
        total_criteria = len(validation_criteria)

        for criterion, passed in validation_criteria.items():
            status = "[OK] VALIDÉ" if passed else "[FAIL] ÉCHEC"
            print(f"{status} {criterion}")
            if passed:
                passed_criteria += 1

        # Résultat final
        success_rate = (passed_criteria / total_criteria) * 100
        print(
            f"\nTAUX DE RÉUSSITE: {passed_criteria}/{total_criteria} ({success_rate:.1f}%)"
        )

        if success_rate >= 80:
            final_status = "🎉 PHASE D COMPLÈTEMENT RÉUSSIE"
            phase_d_success = True
        elif success_rate >= 60:
            final_status = "⚠️  PHASE D PARTIELLEMENT RÉUSSIE"
            phase_d_success = False
        else:
            final_status = "[FAIL] PHASE D ÉCHOUÉE"
            phase_d_success = False

        print(f"\n{final_status}")

        # Sauvegarde des résultats détaillés
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"phase_d_trace_ideale_results_{timestamp}.json"

        results_data = {
            "test_timestamp": datetime.now().isoformat(),
            "test_type": "Phase D - Trace Idéale",
            "global_score": global_score,
            "success_threshold": success_threshold,
            "phase_d_success": phase_d_success,
            "ideal_metrics": ideal_metrics,
            "user_test_scores": user_test_scores,
            "average_user_score": average_user_score,
            "validation_criteria": validation_criteria,
            "success_rate": success_rate,
            "conversation_history": [
                {
                    "agent": msg.get("agent_name", ""),
                    "content": msg.get("content", "")[:200],
                    "type": msg.get("message_type", ""),
                }
                for msg in oracle_state.conversation_history
            ],
            "optimization_features": {
                "progressive_revelations": True,
                "false_leads": True,
                "narrative_twists": narrative_twist is not None,
                "conversational_polish": True,
                "crescendo_moments": True,
                "dramatic_timing": True,
            },
        }

        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False)

        print(f"\n[OK] Résultats sauvegardés: {results_file}")

        # Recommandations pour amélioration si nécessaire
        if not phase_d_success:
            print("\n" + "=" * 50)
            print("RECOMMANDATIONS D'AMÉLIORATION")
            print("=" * 50)

            if ideal_metrics["dosage_revelations"] < 8.0:
                print("• Améliorer le timing dramatique des révélations")
            if ideal_metrics["progression_logique"] < 8.0:
                print("• Renforcer la logique narrative entre les tours")
            if ideal_metrics["engagement_global"] < 8.0:
                print("• Ajouter plus d'éléments dramatiques et d'interaction")
            if average_user_score < 7.5:
                print("• Optimiser l'expérience utilisateur globale")

        print(f"\n[OK] TEST PHASE D TERMINÉ - STATUS: {success_status}")

        assert phase_d_success, "La validation de la Phase D a échoué."
        return results_data

    except Exception as e:
        logger.error(f"Erreur durant le test Phase D: {e}", exc_info=True)
        pytest.fail(f"Test Phase D a échoué: {e}")
        return None


def demonstration_trace_ideale():
    """
    Démonstration complète d'une conversation trace idéale.
    """
    print("\n" + "=" * 70)
    print("DÉMONSTRATION TRACE IDÉALE - CONVERSATION COMPLÈTE")
    print("=" * 70)

    try:
        # Import et setup
        from argumentation_analysis.core.cluedo_oracle_state import CluedoOracleState

        extend_oracle_state_phase_d(CluedoOracleState)

        elements_jeu = {
            "suspects": ["Colonel Moutarde", "Professeur Violet", "Mademoiselle Rose"],
            "armes": ["Poignard", "Chandelier", "Revolver"],
            "lieux": ["Salon", "Cuisine", "Bureau"],
        }

        oracle_state = CluedoOracleState(
            nom_enquete_cluedo="Démonstration Trace Idéale",
            elements_jeu_cluedo=elements_jeu,
            description_cas="Conversation exemplaire optimisée Phase D",
            initial_context="Démonstration des fonctionnalités Phase D",
            oracle_strategy="balanced",
        )

        oracle_state.__init_phase_d__()
        extensions = PhaseDExtensions()

        # Conversation trace idéale étape par étape
        conversation_ideale = [
            {
                "tour": 1,
                "agent": "Sherlock",
                "content": "Mes premières observations révèlent des indices intrigants dans cette pièce. La disposition des objets suggère une séquence d'événements précise.",
                "type": "analysis",
            },
            {
                "tour": 2,
                "agent": "Watson",
                "content": "Brillante approche Sherlock ! Suite à votre observation, je remarque également que la logique des indices converge vers une hypothèse claire.",
                "type": "reaction",
            },
            {
                "tour": 3,
                "agent": "Moriarty",
                "content": oracle_state.add_dramatic_revelation(
                    "J'ai le Colonel Moutarde dans mes cartes !", intensity=0.9
                ),
                "type": "revelation",
            },
            {
                "tour": 4,
                "agent": "Watson",
                "content": oracle_state.apply_conversational_polish_to_message(
                    "Watson",
                    "Aha ! En réaction à cette révélation, tout s'éclaire ! Le puzzle prend forme.",
                ),
                "type": "reaction",
            },
            {
                "tour": 5,
                "agent": "Sherlock",
                "content": oracle_state.apply_conversational_polish_to_message(
                    "Sherlock",
                    "Précisément Watson. Après cette information, ma déduction se précise : nous cherchons l'arme et le lieu.",
                ),
                "type": "analysis",
            },
            {
                "tour": 6,
                "agent": "Moriarty",
                "content": extensions.generate_progressive_revelation(
                    "Hypothèse arme",
                    "Et voici ma seconde révélation : j'ai aussi le Chandelier !",
                    0.95,
                ),
                "type": "revelation",
            },
            {
                "tour": 7,
                "agent": "Watson",
                "content": "Exactement ce que je pensais ! Suite à ces révélations, la logique nous mène inexorablement vers la solution.",
                "type": "reaction",
            },
            {
                "tour": 8,
                "agent": "Sherlock",
                "content": "Donc, par élimination logique, la solution est : Professeur Violet avec le Revolver dans le Bureau !",
                "type": "conclusion",
            },
            {
                "tour": 9,
                "agent": "Moriarty",
                "content": extensions.generate_crescendo_moment(
                    {
                        "final_revelation": "Magistral ! Professeur Violet avec le Revolver dans le Bureau !"
                    }
                ),
                "type": "crescendo",
            },
        ]

        print("\nCONVERSATION TRACE IDÉALE:")
        print("-" * 50)

        for msg in conversation_ideale:
            oracle_state.add_conversation_message(
                msg["agent"], msg["content"], msg["type"]
            )

            print(f"\n[TOUR {msg['tour']}] {msg['agent']} ({msg['type']}):")
            print(f"{msg['content']}")
            print()

        # Métriques finales de la démonstration
        final_metrics = oracle_state.get_ideal_trace_metrics()

        print("MÉTRIQUES FINALES DÉMONSTRATION:")
        print("-" * 40)
        for metric, score in final_metrics.items():
            print(f"• {metric.replace('_', ' ').title()}: {score:.1f}/10")

        print(f"\n🎯 SCORE TRACE IDÉALE: {final_metrics['score_trace_ideale']:.1f}/10")

        if final_metrics["score_trace_ideale"] >= 8.0:
            print("🎉 TRACE IDÉALE DÉMONTRÉE AVEC SUCCÈS !")
        else:
            print("⚠️  Optimisations supplémentaires recommandées")

        return final_metrics

    except Exception as e:
        logger.error(f"Erreur démonstration: {e}", exc_info=True)
        return None


if __name__ == "__main__":
    # Exécution des tests Phase D
    def run_all_tests():
        print("LANCEMENT TESTS COMPLETS PHASE D")
        print("=" * 70)

        # Test principal
        results = test_phase_d_trace_ideale()

        if results:
            print("\n" + "=" * 50)
            print("TESTS PRINCIPAUX TERMINÉS")

            # Démonstration si tests réussis
            if results.get("phase_d_success", False):
                demo_results = demonstration_trace_ideale()
                if demo_results:
                    print("\n[OK] DÉMONSTRATION TRACE IDÉALE COMPLÉTÉE")

        print("\n🎉 PHASE D - TOUS LES TESTS TERMINÉS")

    run_all_tests()
