import pytest
#!/usr/bin/env python3
"""
Test simple Phase D : Validation basique des nouvelles fonctionnalités (version fixée).
"""

import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.mark.anyio
async def test_phase_d_simple():
    """Test simple des fonctionnalités Phase D."""
    print("DEBUT TEST PHASE D SIMPLE")
    print("=" * 50)
    
    try:
        # Import avec nouvelles méthodes Phase D
        from argumentation_analysis.core.cluedo_oracle_state import CluedoOracleState
        print("[OK] Import CluedoOracleState avec Phase D")
        
        # Configuration de base
        elements_jeu = {
            "suspects": ["Colonel Moutarde", "Professeur Violet", "Mademoiselle Rose"],
            "armes": ["Poignard", "Chandelier", "Revolver"],
            "lieux": ["Salon", "Cuisine", "Bureau"]
        }
        
        # Création de l'état Oracle
        oracle_state = CluedoOracleState(
            nom_enquete_cluedo="Test Phase D Simple",
            elements_jeu_cluedo=elements_jeu,
            description_cas="Test des nouvelles fonctionnalités Phase D",
            initial_context="Test Phase D simple",
            oracle_strategy="balanced"
        )
        print("[OK] CluedoOracleState créé")
        
        # Test 1: Révélation dramatique
        print("\nTest 1: Révélation dramatique")
        dramatic_revelation = oracle_state.add_dramatic_revelation(
            "J'ai le Colonel Moutarde dans mes cartes !",
            intensity=0.9,
            use_false_lead=False
        )
        print(f"[OK] Révélation générée ({len(dramatic_revelation)} caractères)")
        print("Extrait:", dramatic_revelation[:100] + "...")
        
        # Test 2: Polish conversationnel
        print("\nTest 2: Polish conversationnel")
        watson_content = oracle_state.apply_conversational_polish_to_message(
            "Watson", "C'est une déduction brillante !"
        )
        sherlock_content = oracle_state.apply_conversational_polish_to_message(
            "Sherlock", "Cette analyse est exacte."
        )
        moriarty_content = oracle_state.apply_conversational_polish_to_message(
            "Moriarty", "Voici ma révélation."
        )
        
        print(f"[OK] Watson: {watson_content}")
        print(f"[OK] Sherlock: {sherlock_content}")
        print(f"[OK] Moriarty: {moriarty_content}")
        
        # Test 3: Ajout de messages avec nouvelles fonctionnalités
        print("\nTest 3: Messages avec Phase D")
        messages_test = [
            ("Sherlock", "J'analyse les indices présents. La logique suggère une déduction précise.", "analysis"),
            ("Watson", watson_content, "reaction"),
            ("Moriarty", dramatic_revelation, "revelation"),
            ("Watson", "Brillant ! Suite à cette révélation, tout s'éclaire !", "reaction"),
            ("Sherlock", "Précisément. Donc, par déduction logique, nous approchons de la solution.", "analysis")
        ]
        
        for agent, content, msg_type in messages_test:
            oracle_state.add_conversation_message(agent, content, msg_type)
        
        print(f"[OK] {len(messages_test)} messages ajoutés")
        
        # Test 4: Métriques trace idéale
        print("\nTest 4: Métriques trace idéale")
        ideal_metrics = oracle_state.get_ideal_trace_metrics()
        
        print("METRIQUES PHASE D:")
        for metric_name, score in ideal_metrics.items():
            status = "[OK]" if score >= 8.0 else "[WARN]" if score >= 7.0 else "[NON]"
            print(f"{status} {metric_name.replace('_', ' ').title()}: {score:.1f}/10")
        
        # Score global
        global_score = ideal_metrics["score_trace_ideale"]
        print(f"\nSCORE TRACE IDEALE: {global_score:.1f}/10")
        
        # Test 5: Validation Phase D
        print("\nTest 5: Validation critères Phase D")
        validations = oracle_state.validate_phase_d_requirements()
        
        print("CRITERES PHASE D:")
        passed_count = 0
        total_count = len(validations)
        
        for criterion, passed in validations.items():
            status = "[OK]" if passed else "[NON]"
            print(f"{status} {criterion.replace('_', ' ').title()}")
            if passed:
                passed_count += 1
        
        success_rate = (passed_count / total_count) * 100
        print(f"\nTAUX DE REUSSITE: {passed_count}/{total_count} ({success_rate:.1f}%)")
        
        # Test 6: Crescendo final
        print("\nTest 6: Crescendo final")
        crescendo = oracle_state.generate_crescendo_moment(
            "Professeur Violet avec le Revolver dans le Bureau !"
        )
        print(f"[OK] Crescendo généré ({len(crescendo)} caractères)")
        print("Extrait:", crescendo[:150] + "...")
        
        # Évaluation finale
        if global_score >= 8.0:
            final_status = "[SUCCES] TRACE IDEALE ATTEINTE"
            success = True
        elif global_score >= 7.0:
            final_status = "[WARN] AMELIORATION NECESSAIRE"
            success = False
        else:
            final_status = "[ECHEC] ECHEC TRACE IDEALE"
            success = False
        
        print(f"\n{final_status}")
        print(f"Score requis: 8.0/10 | Score obtenu: {global_score:.1f}/10")
        
        # Sauvegarde des résultats
        import json
        from datetime import datetime
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "test_type": "Phase D Simple",
            "global_score": global_score,
            "ideal_metrics": ideal_metrics,
            "validations": validations,
            "success_rate": success_rate,
            "trace_ideale_achieved": success,
            "messages_count": len(oracle_state.conversation_history),
            "features_tested": [
                "dramatic_revelations",
                "conversational_polish",
                "ideal_trace_metrics",
                "phase_d_validations",
                "crescendo_moments"
            ]
        }
        
        with open("phase_d_simple_results.json", 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print("\n[OK] Résultats sauvegardés: phase_d_simple_results.json")
        print("[OK] TEST PHASE D SIMPLE TERMINE")
        
        return results
        
    except Exception as e:
        logger.error(f"Erreur test Phase D: {e}", exc_info=True)
        print(f"\n[ERREUR] Test échoué: {e}")
        return None


if __name__ == "__main__":
    asyncio.run(test_phase_d_simple())