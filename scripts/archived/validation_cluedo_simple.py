#!/usr/bin/env python3
# scripts/validation_cluedo_simple.py

"""
Script de validation simple pour les démos Cluedo avec traces complètes.
Version focalisée sur les fonctionnalités qui existent réellement.
"""

# ===== INTÉGRATION AUTO_ENV - MÊME APPROCHE QUE CONFTEST.PY =====
import sys
import os
from pathlib import Path

# Déterminer le répertoire racine du projet
project_root = Path(__file__).parent.parent.absolute()

try:
    # Import direct par chemin absolu pour éviter les problèmes d'import
    scripts_core_path = project_root / "scripts" / "core"
    if str(scripts_core_path) not in sys.path:
        sys.path.insert(0, str(scripts_core_path))
    
    from auto_env import ensure_env
    success = ensure_env(silent=False)
    
    if success:
        print("[OK AUTO_ENV] Environnement projet activé avec succès")
    else:
        print("[WARN AUTO_ENV] Activation en mode dégradé")
        
except ImportError as e:
    print(f"[ERROR AUTO_ENV] Module auto_env non disponible: {e}")
except Exception as e:
    print(f"[ERROR AUTO_ENV] Erreur d'activation: {e}")

# ===== IMPORTS PRINCIPAUX =====
import asyncio
import json
import logging
import datetime
from typing import Dict, List, Any, Optional

from dotenv import load_dotenv
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

# Imports spécifiques au projet
from argumentation_analysis.orchestration.cluedo_extended_orchestrator import run_cluedo_oracle_game
from argumentation_analysis.utils.core_utils.logging_utils import setup_logging

class CluedoSimpleValidator:
    """Validateur simple pour les démos Cluedo avec traces."""
    
    def __init__(self, output_dir: str = ".temp"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.logger = logging.getLogger(__name__)
        
        # Création des répertoires de traces
        self.cluedo_dir = self.output_dir / "traces_cluedo"
        self.cluedo_dir.mkdir(parents=True, exist_ok=True)

    def create_kernel(self, model_name: str = "gpt-4o-mini") -> Kernel:
        """Création du kernel Semantic Kernel avec service OpenRouter."""
        from openai import AsyncOpenAI
        
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
        
        if not api_key:
            raise ValueError("OPENAI_API_KEY non définie dans l'environnement")
            
        # Configuration du client AsyncOpenAI pour OpenRouter
        client_kwargs = {
            "api_key": api_key,
            "base_url": base_url
        }
        
        openai_client = AsyncOpenAI(**client_kwargs)
        
        kernel = Kernel()
        chat_service = OpenAIChatCompletion(
            service_id="openai_chat",
            ai_model_id=model_name,
            async_client=openai_client
        )
        kernel.add_service(chat_service)
        return kernel

    def validate_environment(self) -> Dict[str, Any]:
        """Valide l'environnement avant d'exécuter les tests."""
        
        print("[VALIDATION DE L'ENVIRONNEMENT]")
        print("="*50)
        
        validation_results = {
            "openai_api_key": bool(os.getenv("OPENAI_API_KEY")),
            "directories_created": True,
            "python_imports": True,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # Vérification clé API
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("[ERREUR] OPENAI_API_KEY non définie")
            validation_results["openai_api_key"] = False
        else:
            print(f"[OK] OPENAI_API_KEY définie (longueur: {len(api_key)})")
            
        # Vérification des répertoires
        if self.cluedo_dir.exists():
            print("[OK] Répertoires de traces créés")
        else:
            print("[ERREUR] Répertoires de traces manquants")
            validation_results["directories_created"] = False
            
        # Test d'imports
        try:
            print("[OK] Imports des orchestrateurs réussis")
        except ImportError as e:
            print(f"[ERREUR] Erreur d'import: {e}")
            validation_results["python_imports"] = False
            
        # Résumé
        all_ok = all(validation_results[k] for k in ["openai_api_key", "directories_created", "python_imports"])
        validation_results["environment_ready"] = all_ok
        
        if all_ok:
            print("\n[SUCCES] ENVIRONNEMENT PRÊT POUR LA VALIDATION")
        else:
            print("\n[ATTENTION]  PROBLÈMES DÉTECTÉS - CORRECTION NÉCESSAIRE")
            
        return validation_results

    def generate_cases(self) -> List[Dict[str, str]]:
        """Génère les cas de test Cluedo."""
        return [
            {
                "name": "simple",
                "description": """Enquête Cluedo simple: 
                - Témoin A: 'J'ai vu Mme Peacock dans la bibliothèque vers 21h00'
                - Témoin B: 'Le chandelier manquait dans le salon après 21h30'
                - Témoin C: 'Professor Plum était dans la cuisine à 21h15'
                - Indice physique: Traces de cire dans la bibliothèque
                
                Question: Qui a commis le meurtre, avec quelle arme et dans quel lieu ?"""
            },
            {
                "name": "complexe",
                "description": """Enquête Cluedo complexe avec contradictions:
                - Témoin A: 'Mme Peacock était dans la bibliothèque vers 21h00'
                - Témoin B: 'Mme Peacock était dans le salon à 21h00' (CONTRADICTION)
                - Témoin C: 'J'ai entendu un bruit dans la bibliothèque vers 21h15'
                - Témoin D: 'Professor Plum avait le chandelier à 20h45'
                - Témoin E: 'Professor Plum n'avait pas d'arme à 20h45' (CONTRADICTION)
                - Indice: Empreintes de Mme Peacock sur le chandelier
                - Indice: Traces de cire dans la bibliothèque et le salon
                - Indice: Alibi partiel de Professor Plum en cuisine (20h30-21h00)
                - Indice: Porte de la bibliothèque fermée à clé après 21h30
                
                Question: Résolvez cette enquête en gérant les contradictions."""
            }
        ]

    async def run_cluedo_case(self, case: Dict[str, str]) -> Dict[str, Any]:
        """Exécute un cas Cluedo avec capture complète des traces."""
        
        case_name = case["name"]
        case_description = case["description"]
        
        print(f"\n[DETECTIVE] EXÉCUTION CAS CLUEDO: {case_name.upper()}")
        print("="*60)
        
        try:
            # Création du kernel
            kernel = self.create_kernel()
            
            # Capture du timestamp de début
            start_time = datetime.datetime.now()
            
            # Exécution du jeu Cluedo
            print(f"[SCENARIO] Scénario: {case_description[:100]}...")
            print("[LANCEMENT] Démarrage de l'enquête avec les agents Sherlock, Watson et Moriarty...")
            
            result = await run_cluedo_oracle_game(kernel, case_description)
            final_history = result.get('chat_history', [])
            final_state = result.get('final_state', {})
            
            # Capture du timestamp de fin
            end_time = datetime.datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Construction des résultats complets
            results = {
                "metadata": {
                    "case_name": case_name,
                    "timestamp": self.timestamp,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration_seconds": duration,
                    "model_used": "gpt-4o-mini"
                },
                "input": {
                    "case_description": case_description
                },
                "conversation_history": final_history,
                "final_state": {
                    "final_solution": getattr(final_state, 'final_solution', None),
                    "solution_secrete": getattr(final_state, 'solution_secrete_cluedo', None),
                    "hypotheses": getattr(final_state, 'hypotheses_enquete', []),
                    "tasks": getattr(final_state, 'tasks', {})
                },
                "analysis": {
                    "conversation_length": len(final_history) if final_history else 0,
                    "success": getattr(final_state, 'final_solution', None) is not None,
                    "agent_interactions": self._analyze_agent_interactions(final_history),
                    "tools_used": self._extract_tools_usage(final_history)
                }
            }
            
            # Sauvegarde des traces
            trace_file = self.cluedo_dir / f"trace_{case_name}_{self.timestamp}.json"
            with open(trace_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                
            print(f"[OK] Traces Cluedo sauvegardées: {trace_file}")
            
            # Affichage des résultats
            self._display_results(results)
            
            return results
            
        except Exception as e:
            print(f"[ERREUR] Erreur lors de l'exécution de {case_name}: {e}")
            error_results = {
                "metadata": {"case_name": case_name, "error": str(e)},
                "error": str(e),
                "timestamp": self.timestamp
            }
            
            # Sauvegarde de l'erreur
            error_file = self.cluedo_dir / f"error_{case_name}_{self.timestamp}.json"
            with open(error_file, 'w', encoding='utf-8') as f:
                json.dump(error_results, f, indent=2, ensure_ascii=False, default=str)
                
            raise

    def _analyze_agent_interactions(self, history: List) -> Dict[str, int]:
        """Analyse les interactions entre agents."""
        interactions = {}
        if not history:
            return interactions
            
        for entry in history:
            if isinstance(entry, dict) and 'sender' in entry:
                sender = entry['sender']
                interactions[sender] = interactions.get(sender, 0) + 1
                
        return interactions

    def _extract_tools_usage(self, history: List) -> List[str]:
        """Extrait les outils utilisés pendant la conversation."""
        tools_used = set()
        if not history:
            return list(tools_used)
            
        for entry in history:
            if isinstance(entry, dict) and 'message' in entry:
                message = entry['message'].lower()
                # Recherche de mentions d'outils
                if 'tweetyproject' in message or 'tweety' in message:
                    tools_used.add('TweetyProject')
                if 'semantic_kernel' in message or 'fonction' in message:
                    tools_used.add('SemanticKernel')
                if 'oracle' in message:
                    tools_used.add('Oracle')
                if 'enquête' in message or 'investigation' in message:
                    tools_used.add('Enquête')
                    
        return list(tools_used)

    def _display_results(self, results: Dict[str, Any]):
        """Affiche les résultats de l'analyse."""
        print(f"\n[RESULTATS] RÉSULTATS ANALYSE - {results['metadata']['case_name']}")
        print(f"[TEMPS]  Durée: {results['metadata']['duration_seconds']:.2f}s")
        print(f"[MESSAGES] Messages échangés: {results['analysis']['conversation_length']}")
        
        # Interactions des agents
        interactions = results['analysis']['agent_interactions']
        print(f"\n[AGENTS] Interactions des agents:")
        for agent, count in interactions.items():
            print(f"   - {agent}: {count} messages")
            
        # Outils utilisés
        tools = results['analysis']['tools_used']
        print(f"\n[OUTILS] Outils utilisés: {', '.join(tools) if tools else 'Aucun détecté'}")
        
        # Solution finale
        final_solution = results['final_state']['final_solution']
        success = results['analysis']['success']
        print(f"\n[OBJECTIF] Solution finale: {final_solution if final_solution else 'Non résolue'}")
        print(f"[OK] Succès: {'OUI' if success else 'NON'}")

    async def run_validation(self) -> Dict[str, Any]:
        """Exécute la validation complète des démos Cluedo."""
        
        print("VALIDATION DEMOS CLUEDO AVEC TRACES COMPLETES")
        print("="*80)
        print("[OBJECTIF] Tests: Cas simple et complexe avec agents Sherlock, Watson et Moriarty")
        print("[RESULTATS] Livrables: Traces JSON + Analyse des interactions agentiques")
        
        # Validation de l'environnement
        env_validation = self.validate_environment()
        if not env_validation["environment_ready"]:
            raise RuntimeError("Environnement non prêt pour la validation")
            
        start_time = datetime.datetime.now()
        all_results = {
            "metadata": {
                "validation_start": start_time.isoformat(),
                "timestamp": self.timestamp,
                "environment_validation": env_validation
            },
            "cluedo_results": []
        }
        
        try:
            # Exécution des cas de test
            cases = self.generate_cases()
            
            for i, case in enumerate(cases, 1):
                print(f"\n[SCENARIO] TEST {i}/{len(cases)}: CAS {case['name'].upper()}")
                print("="*60)
                
                case_results = await self.run_cluedo_case(case)
                all_results["cluedo_results"].append(case_results)
                
                print(f"[OK] Test {i} terminé avec succès")
            
            # Finalisation
            end_time = datetime.datetime.now()
            total_duration = (end_time - start_time).total_seconds()
            
            all_results["metadata"]["validation_end"] = end_time.isoformat()
            all_results["metadata"]["total_duration"] = total_duration
            
            # Génération du rapport global
            await self.generate_global_report(all_results)
            
            # Affichage du résumé final
            self.display_final_summary(all_results)
            
            return all_results
            
        except Exception as e:
            self.logger.error(f"[ERREUR] Erreur lors de la validation complète: {e}")
            raise

    async def generate_global_report(self, all_results: Dict[str, Any]):
        """Génère le rapport global de validation."""
        
        # Calcul des métriques globales
        total_tests = len(all_results["cluedo_results"])
        successful_tests = sum(1 for r in all_results["cluedo_results"] if r['analysis']['success'])
        total_messages = sum(r['analysis']['conversation_length'] for r in all_results["cluedo_results"])
        
        # Analyse des agents
        all_interactions = {}
        all_tools = set()
        
        for result in all_results["cluedo_results"]:
            # Agrégation des interactions
            for agent, count in result['analysis']['agent_interactions'].items():
                all_interactions[agent] = all_interactions.get(agent, 0) + count
            
            # Agrégation des outils
            all_tools.update(result['analysis']['tools_used'])
        
        # Construction du rapport
        global_report = {
            "metadata": all_results["metadata"],
            "summary": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "success_rate": successful_tests / total_tests if total_tests > 0 else 0,
                "total_messages": total_messages,
                "average_messages_per_test": total_messages / total_tests if total_tests > 0 else 0
            },
            "agent_analysis": {
                "total_interactions": all_interactions,
                "tools_coverage": list(all_tools)
            },
            "detailed_results": all_results["cluedo_results"]
        }
        
        # Sauvegarde du rapport
        report_file = self.output_dir / f"global_cluedo_report_{self.timestamp}.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(global_report, f, indent=2, ensure_ascii=False, default=str)
            
        print(f"\n[SCENARIO] Rapport global sauvegardé: {report_file}")

    def display_final_summary(self, all_results: Dict[str, Any]):
        """Affiche le résumé final de la validation."""
        
        print(f"\n{'='*80}")
        print(f"[SUCCES] VALIDATION CLUEDO TERMINÉE")
        print(f"{'='*80}")
        
        metadata = all_results['metadata']
        cluedo_results = all_results['cluedo_results']
        
        total_tests = len(cluedo_results)
        successful_tests = sum(1 for r in cluedo_results if r['analysis']['success'])
        
        print(f"[TEMPS]  Durée totale: {metadata['total_duration']:.2f}s")
        print(f"🧪 Tests exécutés: {total_tests}")
        print(f"[OK] Tests réussis: {successful_tests}/{total_tests}")
        print(f"📈 Taux de succès: {(successful_tests/total_tests)*100:.1f}%" if total_tests > 0 else "📈 Taux de succès: N/A")
        
        print(f"\n[FICHIERS] TRACES GÉNÉRÉES:")
        print(f"   - Traces Cluedo: {self.cluedo_dir}/")
        print(f"   - Rapport global: global_cluedo_report_{self.timestamp}.json")
        
        print(f"\n[OBJECTIF] CONCLUSION:")
        if successful_tests == total_tests:
            print("   [OK] Tous les tests ont réussi - Système agentique opérationnel")
        elif successful_tests > 0:
            print(f"   [ATTENTION]  {successful_tests}/{total_tests} tests réussis - Améliorations possibles")
        else:
            print("   [ERREUR] Aucun test réussi - Révision du système nécessaire")
            
        print(f"\n[OK] Validation des démos Sherlock, Watson et Moriarty terminée !")

async def main():
    """Fonction principale de validation simple avec traces."""
    
    # Configuration du logging
    setup_logging()
    
    # Chargement de l'environnement
    load_dotenv()
    
    try:
        # Création et lancement du validateur
        validator = CluedoSimpleValidator()
        
        # Exécution de la validation
        results = await validator.run_validation()
        
        return results
        
    except Exception as e:
        print(f"\n[ERREUR CRITIQUE]: {e}")
        logging.error(f"Erreur validation: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(main())
