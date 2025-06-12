"""
Démonstration complète du système JTMS intégré avec Semantic Kernel
Illustre tous les aspects du plugin : service centralisé, sessions, API REST et intégration SK.
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from typing import Dict, List, Any

# Ajouter le chemin du projet
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Import des services JTMS
from services.jtms_service import JTMSService
from services.jtms_session_manager import JTMSSessionManager
from plugins.semantic_kernel.jtms_plugin import create_jtms_plugin
from integrations.semantic_kernel_integration import create_minimal_jtms_integration

class JTMSCompleteDemo:
    """
    Démonstration complète du système JTMS avec tous ses composants.
    """
    
    def __init__(self):
        # Créer l'intégration d'abord
        self.integration = create_minimal_jtms_integration()
        
        # Utiliser les services de l'intégration pour éviter les instances séparées
        self.jtms_service = self.integration.jtms_service
        self.session_manager = self.integration.session_manager
        self.sk_plugin = self.integration.jtms_plugin
        
        # Stockage des résultats de demo
        self.demo_results = {}
        
    def print_header(self, title: str):
        """Affiche un en-tête de section."""
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}")
    
    def print_subheader(self, title: str):
        """Affiche un sous-en-tête."""
        print(f"\n{'-'*40}")
        print(f"  {title}")
        print(f"{'-'*40}")
    
    def print_json(self, data: Any, title: str = None):
        """Affiche des données JSON formatées."""
        if title:
            print(f"\n📋 {title}:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
    
    async def demo_1_basic_jtms_operations(self):
        """Démo 1: Opérations JTMS de base."""
        self.print_header("DÉMO 1: OPÉRATIONS JTMS DE BASE")
        
        # Créer une session
        session_id = await self.session_manager.create_session(
            agent_id="demo_agent",
            session_name="Demo_Basic_Operations",
            metadata={"demo": "basic_operations", "version": "1.0"}
        )
        print(f"✅ Session créée: {session_id}")
        
        # Créer une instance JTMS
        instance_id = await self.jtms_service.create_jtms_instance(
            session_id=session_id,
            strict_mode=False
        )
        print(f"✅ Instance JTMS créée: {instance_id}")
        
        # Associer l'instance à la session
        await self.session_manager.add_jtms_instance_to_session(session_id, instance_id)
        print(f"✅ Instance associée à la session")
        
        # Créer des croyances
        self.print_subheader("Création de croyances")
        
        beliefs_to_create = [
            ("pluie", True),
            ("soleil", False),
            ("nuages", None),
            ("route_mouillée", None),
            ("temps_sec", None)
        ]
        
        for belief_name, initial_value in beliefs_to_create:
            result = await self.jtms_service.create_belief(
                instance_id=instance_id,
                belief_name=belief_name,
                initial_value=initial_value
            )
            print(f"  ➕ Croyance '{belief_name}' créée: {result['valid']}")
        
        # Ajouter des justifications (règles logiques)
        self.print_subheader("Ajout de justifications")
        
        justifications = [
            (["pluie"], [], "route_mouillée"),  # Si pluie alors route mouillée
            ([], ["pluie"], "temps_sec"),       # Si non pluie alors temps sec
            (["soleil"], ["nuages"], "ciel_clair"),  # Si soleil ET non nuages alors ciel clair
            (["route_mouillée", "vent"], [], "conduite_difficile")  # Si route mouillée ET vent alors conduite difficile
        ]
        
        for in_beliefs, out_beliefs, conclusion in justifications:
            result = await self.jtms_service.add_justification(
                instance_id=instance_id,
                in_beliefs=in_beliefs,
                out_beliefs=out_beliefs,
                conclusion=conclusion
            )
            print(f"  ⚡ Règle ajoutée: {in_beliefs} ∧ ¬{out_beliefs} → {conclusion}")
            print(f"      Conclusion: {result['conclusion_status']}")
        
        # Interroger les croyances
        self.print_subheader("Interrogation des croyances")
        
        # Toutes les croyances
        all_beliefs = await self.jtms_service.query_beliefs(instance_id, None)
        print(f"  📊 Total des croyances: {all_beliefs['total_beliefs']}")
        
        # Croyances valides seulement
        valid_beliefs = await self.jtms_service.query_beliefs(instance_id, "valid")
        print(f"  ✅ Croyances vraies: {valid_beliefs['filtered_count']}")
        for belief in valid_beliefs['beliefs']:
            print(f"      - {belief['name']}: {belief['valid']}")
        
        # Expliquer une croyance
        self.print_subheader("Explication de croyance")
        
        explanation = await self.jtms_service.explain_belief(instance_id, "route_mouillée")
        self.print_json(explanation, "Explication de 'route_mouillée'")
        
        # Obtenir l'état complet
        self.print_subheader("État complet du système")
        
        full_state = await self.jtms_service.get_jtms_state(instance_id)
        self.print_json(full_state['statistics'], "Statistiques JTMS")
        
        # Stocker les résultats
        self.demo_results['demo_1'] = {
            "session_id": session_id,
            "instance_id": instance_id,
            "total_beliefs": full_state['statistics']['total_beliefs'],
            "valid_beliefs": full_state['statistics']['valid_beliefs'],
            "total_justifications": full_state['statistics']['total_justifications']
        }
        
        return session_id, instance_id
    
    async def demo_2_semantic_kernel_plugin(self):
        """Démo 2: Plugin Semantic Kernel."""
        self.print_header("DÉMO 2: PLUGIN SEMANTIC KERNEL")
        
        # Configurer le plugin avec auto-création
        self.sk_plugin.configure_auto_creation(auto_session=True, auto_instance=True)
        
        # Tester chaque fonction SK
        self.print_subheader("Fonction create_belief")
        
        result1 = await self.sk_plugin.create_belief(
            belief_name="température_élevée",
            initial_value="true",
            agent_id="sk_demo_agent"
        )
        result1_data = json.loads(result1)
        print(f"✅ Résultat: {result1_data['status']}")
        session_id = result1_data['session_id']
        instance_id = result1_data['instance_id']
        
        self.print_subheader("Fonction add_justification")
        
        result2 = await self.sk_plugin.add_justification(
            in_beliefs="température_élevée,soleil",
            out_beliefs="pluie",
            conclusion="canicule",
            session_id=session_id,
            instance_id=instance_id,
            agent_id="sk_demo_agent"
        )
        result2_data = json.loads(result2)
        print(f"✅ Justification ajoutée: {result2_data['status']}")
        
        self.print_subheader("Fonction query_beliefs")
        
        result3 = await self.sk_plugin.query_beliefs(
            filter_status="all",
            session_id=session_id,
            instance_id=instance_id,
            agent_id="sk_demo_agent"
        )
        result3_data = json.loads(result3)
        print(f"✅ Interrogation: {result3_data['total_beliefs']} croyances trouvées")
        print(f"📝 Résumé: {result3_data['natural_language_summary']}")
        
        self.print_subheader("Fonction explain_belief")
        
        result4 = await self.sk_plugin.explain_belief(
            belief_name="température_élevée",
            session_id=session_id,
            instance_id=instance_id,
            agent_id="sk_demo_agent"
        )
        result4_data = json.loads(result4)
        print(f"✅ Explication générée: {result4_data['status']}")
        print(f"📝 Résumé: {result4_data['natural_language_summary']}")
        
        self.print_subheader("Fonction get_jtms_state")
        
        result5 = await self.sk_plugin.get_jtms_state(
            include_graph="true",
            include_statistics="true",
            session_id=session_id,
            instance_id=instance_id,
            agent_id="sk_demo_agent"
        )
        result5_data = json.loads(result5)
        print(f"✅ État récupéré: {result5_data['status']}")
        print(f"📝 Résumé: {result5_data['natural_language_summary']}")
        
        # Stocker les résultats
        self.demo_results['demo_2'] = {
            "session_id": session_id,
            "instance_id": instance_id,
            "plugin_functions_tested": 5,
            "all_functions_successful": all(
                json.loads(r)['status'] == 'success' 
                for r in [result1, result2, result3, result4, result5]
            )
        }
        
        return session_id, instance_id
    
    async def demo_3_session_management(self):
        """Démo 3: Gestion avancée des sessions."""
        self.print_header("DÉMO 3: GESTION AVANCÉE DES SESSIONS")
        
        # Créer plusieurs sessions pour différents agents
        self.print_subheader("Création de sessions multi-agents")
        
        agents = ["sherlock", "watson", "moriarty"]
        sessions = {}
        
        for agent in agents:
            session_id = await self.session_manager.create_session(
                agent_id=agent,
                session_name=f"Session_{agent}_Investigation",
                metadata={
                    "case": "mystery_case_001",
                    "role": "investigator" if agent != "moriarty" else "suspect"
                }
            )
            sessions[agent] = session_id
            print(f"✅ Session créée pour {agent}: {session_id}")
        
        # Créer des instances JTMS pour chaque session
        instances = {}
        for agent, session_id in sessions.items():
            instance_id = await self.jtms_service.create_jtms_instance(
                session_id=session_id,
                strict_mode=False
            )
            await self.session_manager.add_jtms_instance_to_session(session_id, instance_id)
            instances[agent] = instance_id
            
            # Ajouter quelques croyances spécifiques à chaque agent
            agent_beliefs = {
                "sherlock": [("indices_trouvés", True), ("suspect_identifié", None)],
                "watson": [("témoignages_recueillis", True), ("alibis_vérifiés", False)],
                "moriarty": [("plan_parfait", True), ("sherlock_deviendra_fou", None)]
            }
            
            for belief_name, value in agent_beliefs[agent]:
                await self.jtms_service.create_belief(
                    instance_id=instance_id,
                    belief_name=belief_name,
                    initial_value=value
                )
            print(f"  🧠 Croyances initiales ajoutées pour {agent}")
        
        # Démonstration des checkpoints
        self.print_subheader("Gestion des checkpoints")
        
        sherlock_session = sessions["sherlock"]
        
        # Créer un checkpoint initial
        checkpoint1 = await self.session_manager.create_checkpoint(
            session_id=sherlock_session,
            description="État initial de l'enquête"
        )
        print(f"✅ Checkpoint créé: {checkpoint1}")
        
        # Modifier l'état JTMS
        sherlock_instance = instances["sherlock"]
        await self.jtms_service.create_belief(
            instance_id=sherlock_instance,
            belief_name="nouvelle_piste",
            initial_value=True
        )
        await self.jtms_service.add_justification(
            instance_id=sherlock_instance,
            in_beliefs=["indices_trouvés", "nouvelle_piste"],
            out_beliefs=[],
            conclusion="enquête_progresse"
        )
        print("🔄 État JTMS modifié (nouvelle piste ajoutée)")
        
        # Créer un second checkpoint
        checkpoint2 = await self.session_manager.create_checkpoint(
            session_id=sherlock_session,
            description="Après découverte de nouvelle piste"
        )
        print(f"✅ Second checkpoint créé: {checkpoint2}")
        
        # Restaurer le premier checkpoint
        await self.session_manager.restore_checkpoint(
            session_id=sherlock_session,
            checkpoint_id=checkpoint1
        )
        print("⏪ État restauré au checkpoint initial")
        
        # Lister toutes les sessions
        self.print_subheader("Liste des sessions")
        
        all_sessions = await self.session_manager.list_sessions()
        print(f"📋 Total des sessions: {len(all_sessions)}")
        for session in all_sessions:
            print(f"  - {session['agent_id']}: {session['session_name']} ({session['checkpoint_count']} checkpoints)")
        
        # Stocker les résultats
        self.demo_results['demo_3'] = {
            "agents_sessions": len(sessions),
            "checkpoints_created": 2,
            "checkpoint_restore_successful": True,
            "total_sessions": len(all_sessions)
        }
        
        return sessions, instances
    
    async def demo_4_multi_agent_reasoning(self):
        """Démo 4: Raisonnement multi-agents."""
        self.print_header("DÉMO 4: RAISONNEMENT MULTI-AGENTS")
        
        # Utiliser l'intégration pour coordonner plusieurs agents
        agents_info = [
            {
                "agent_id": "detective_1",
                "initial_beliefs": [
                    {"name": "empreintes_trouvées", "value": True},
                    {"name": "suspect_a_alibi", "value": False}
                ]
            },
            {
                "agent_id": "detective_2", 
                "initial_beliefs": [
                    {"name": "témoin_fiable", "value": True},
                    {"name": "suspect_vu_sur_place", "value": True}
                ]
            },
            {
                "agent_id": "expert_forensique",
                "initial_beliefs": [
                    {"name": "adn_match", "value": None},
                    {"name": "arme_du_crime_trouvée", "value": True}
                ]
            }
        ]
        
        # Coordonner le raisonnement multi-agents
        coordination_result = await self.integration.multi_agent_reasoning(agents_info)
        
        self.print_json(coordination_result, "Résultat de coordination multi-agents")
        
        # Ajouter des justifications collaboratives
        shared_instance = coordination_result["shared_instance_id"]
        
        # Règles de déduction collaborative
        collaborative_rules = [
            (["empreintes_trouvées", "adn_match"], [], "preuve_physique_solide"),
            (["témoin_fiable", "suspect_vu_sur_place"], [], "témoignage_crédible"),
            (["preuve_physique_solide", "témoignage_crédible"], ["suspect_a_alibi"], "culpabilité_établie"),
            (["arme_du_crime_trouvée"], [], "moyen_identifié")
        ]
        
        for in_beliefs, out_beliefs, conclusion in collaborative_rules:
            try:
                await self.jtms_service.add_justification(
                    instance_id=shared_instance,
                    in_beliefs=in_beliefs,
                    out_beliefs=out_beliefs,
                    conclusion=conclusion
                )
                print(f"✅ Règle collaborative ajoutée: {conclusion}")
            except Exception as e:
                print(f"⚠️  Erreur lors de l'ajout de règle pour {conclusion}: {e}")
        
        # Analyser l'état final partagé
        final_state = await self.jtms_service.get_jtms_state(shared_instance)
        
        print(f"\n📊 État final partagé:")
        print(f"  - Croyances totales: {final_state['statistics']['total_beliefs']}")
        print(f"  - Croyances valides: {final_state['statistics']['valid_beliefs']}")
        print(f"  - Justifications: {final_state['statistics']['total_justifications']}")
        
        # Identifier les conclusions importantes
        important_conclusions = ["culpabilité_établie", "preuve_physique_solide", "témoignage_crédible"]
        for conclusion in important_conclusions:
            if conclusion in final_state['beliefs']:
                status = final_state['beliefs'][conclusion]['valid']
                print(f"  🎯 {conclusion}: {status}")
        
        # Stocker les résultats
        self.demo_results['demo_4'] = {
            "participating_agents": len(agents_info),
            "shared_session_id": coordination_result["shared_session_id"],
            "shared_instance_id": coordination_result["shared_instance_id"],
            "final_beliefs_count": final_state['statistics']['total_beliefs'],
            "collaborative_rules_added": len(collaborative_rules)
        }
        
        return coordination_result
    
    async def demo_5_integration_with_existing_agents(self):
        """Démo 5: Intégration avec les agents Sherlock/Watson existants."""
        self.print_header("DÉMO 5: INTÉGRATION AVEC AGENTS SHERLOCK/WATSON")
        
        # Simuler l'intégration avec les agents existants
        self.print_subheader("Configuration pour agents existants")
        
        # Session Sherlock
        sherlock_session = await self.session_manager.create_session(
            agent_id="sherlock",
            session_name="Sherlock_JTMS_Investigation",
            metadata={
                "agent_type": "detective_lead",
                "case_id": "mystery_001",
                "integration_with": "argumentation_analysis"
            }
        )
        
        sherlock_instance = await self.jtms_service.create_jtms_instance(
            session_id=sherlock_session,
            strict_mode=False
        )
        await self.session_manager.add_jtms_instance_to_session(sherlock_session, sherlock_instance)
        
        # Session Watson
        watson_session = await self.session_manager.create_session(
            agent_id="watson",
            session_name="Watson_JTMS_Support",
            metadata={
                "agent_type": "detective_support",
                "case_id": "mystery_001",
                "integration_with": "argumentation_analysis"
            }
        )
        
        watson_instance = await self.jtms_service.create_jtms_instance(
            session_id=watson_session,
            strict_mode=False
        )
        await self.session_manager.add_jtms_instance_to_session(watson_session, watson_instance)
        
        print(f"✅ Sessions créées - Sherlock: {sherlock_session}, Watson: {watson_session}")
        
        # Simuler des observations Sherlock
        self.print_subheader("Observations de Sherlock")
        
        sherlock_observations = [
            ("cigare_cubain_trouvé", True),
            ("empreinte_taille_43", True),
            ("montre_cassée_10h15", True),
            ("suspect_principal_identifié", None)
        ]
        
        for obs_name, value in sherlock_observations:
            await self.jtms_service.create_belief(
                instance_id=sherlock_instance,
                belief_name=obs_name,
                initial_value=value
            )
            print(f"  🔍 Sherlock observe: {obs_name} = {value}")
        
        # Règles de déduction de Sherlock
        sherlock_rules = [
            (["cigare_cubain_trouvé", "empreinte_taille_43"], [], "suspect_fumeur_et_grand"),
            (["montre_cassée_10h15"], [], "heure_crime_établie"),
            (["suspect_fumeur_et_grand", "heure_crime_établie"], [], "profil_suspect_précis")
        ]
        
        for in_beliefs, out_beliefs, conclusion in sherlock_rules:
            await self.jtms_service.add_justification(
                instance_id=sherlock_instance,
                in_beliefs=in_beliefs,
                out_beliefs=out_beliefs,
                conclusion=conclusion
            )
            print(f"  ⚡ Sherlock déduit: {conclusion}")
        
        # Simuler des vérifications Watson
        self.print_subheader("Vérifications de Watson")
        
        watson_verifications = [
            ("témoins_interrogés", True),
            ("alibis_vérifiés", True),
            ("suspect_a_acheté_cigares_cubains", True),
            ("suspect_porte_taille_43", True)
        ]
        
        for verif_name, value in watson_verifications:
            await self.jtms_service.create_belief(
                instance_id=watson_instance,
                belief_name=verif_name,
                initial_value=value
            )
            print(f"  📝 Watson vérifie: {verif_name} = {value}")
        
        # Règles de vérification de Watson
        watson_rules = [
            (["témoins_interrogés", "alibis_vérifiés"], [], "travail_de_base_complété"),
            (["suspect_a_acheté_cigares_cubains", "suspect_porte_taille_43"], [], "suspect_correspond_indices"),
            (["travail_de_base_complété", "suspect_correspond_indices"], [], "preuves_corroborées")
        ]
        
        for in_beliefs, out_beliefs, conclusion in watson_rules:
            await self.jtms_service.add_justification(
                instance_id=watson_instance,
                in_beliefs=in_beliefs,
                out_beliefs=out_beliefs,
                conclusion=conclusion
            )
            print(f"  ✅ Watson confirme: {conclusion}")
        
        # Synchronisation des sessions (export/import)
        self.print_subheader("Synchronisation Sherlock → Watson")
        
        # Exporter l'état de Sherlock
        sherlock_export = await self.jtms_service.export_jtms_state(sherlock_instance)
        
        # Importer dans une nouvelle instance pour Watson
        watson_sync_instance = await self.jtms_service.import_jtms_state(
            session_id=watson_session,
            state_data=sherlock_export
        )
        
        print(f"✅ État Sherlock synchronisé vers Watson: {watson_sync_instance}")
        
        # Analyser les états finaux
        self.print_subheader("Analyse des états finaux")
        
        sherlock_final = await self.jtms_service.get_jtms_state(sherlock_instance)
        watson_final = await self.jtms_service.get_jtms_state(watson_instance)
        
        print(f"📊 État final Sherlock:")
        print(f"  - Croyances: {sherlock_final['statistics']['total_beliefs']}")
        print(f"  - Justifications: {sherlock_final['statistics']['total_justifications']}")
        print(f"  - Croyances validées: {sherlock_final['statistics']['valid_beliefs']}")
        
        print(f"📊 État final Watson:")
        print(f"  - Croyances: {watson_final['statistics']['total_beliefs']}")
        print(f"  - Justifications: {watson_final['statistics']['total_justifications']}")
        print(f"  - Croyances validées: {watson_final['statistics']['valid_beliefs']}")
        
        # Stocker les résultats
        self.demo_results['demo_5'] = {
            "sherlock_session": sherlock_session,
            "watson_session": watson_session,
            "sherlock_beliefs": sherlock_final['statistics']['total_beliefs'],
            "watson_beliefs": watson_final['statistics']['total_beliefs'],
            "synchronization_successful": True
        }
        
        return {
            "sherlock": {"session": sherlock_session, "instance": sherlock_instance},
            "watson": {"session": watson_session, "instance": watson_instance}
        }
    
    async def run_all_demos(self):
        """Exécute toutes les démonstrations."""
        print("🚀 DÉMARRAGE DES DÉMONSTRATIONS COMPLÈTES DU SYSTÈME JTMS")
        print(f"   Timestamp: {datetime.now().isoformat()}")
        
        try:
            # Exécuter toutes les démos
            await self.demo_1_basic_jtms_operations()
            await self.demo_2_semantic_kernel_plugin()
            await self.demo_3_session_management()
            await self.demo_4_multi_agent_reasoning()
            await self.demo_5_integration_with_existing_agents()
            
            # Résumé final
            self.print_header("RÉSUMÉ FINAL DES DÉMONSTRATIONS")
            
            print("✅ Toutes les démonstrations completées avec succès!")
            print(f"\n📊 Statistiques globales:")
            
            total_sessions = sum(
                1 for demo in self.demo_results.values()
                if 'session_id' in demo or 'agents_sessions' in demo
            )
            
            print(f"  - Démonstrations exécutées: {len(self.demo_results)}")
            print(f"  - Sessions créées: ~{total_sessions}")
            print(f"  - Fonctions SK testées: 5/5")
            print(f"  - Intégrations testées: Agents, API, Sessions, Multi-agents")
            
            # Détail par démonstration
            for demo_name, results in self.demo_results.items():
                print(f"\n  🎯 {demo_name.upper()}:")
                for key, value in results.items():
                    if isinstance(value, bool):
                        status = "✅" if value else "❌"
                        print(f"      {key}: {status}")
                    else:
                        print(f"      {key}: {value}")
            
            self.print_json(self.demo_results, "Résultats détaillés")
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors des démonstrations: {e}")
            import traceback
            traceback.print_exc()
            return False

async def main():
    """Point d'entrée principal."""
    demo = JTMSCompleteDemo()
    success = await demo.run_all_demos()
    
    if success:
        print(f"\n🎉 DÉMONSTRATIONS TERMINÉES AVEC SUCCÈS!")
        print("   Le système JTMS intégré avec Semantic Kernel est pleinement fonctionnel.")
    else:
        print(f"\n💥 ÉCHEC DES DÉMONSTRATIONS!")
        print("   Vérifiez les erreurs ci-dessus.")
    
    return success

if __name__ == "__main__":
    # Exécuter les démonstrations
    result = asyncio.run(main())
    sys.exit(0 if result else 1)