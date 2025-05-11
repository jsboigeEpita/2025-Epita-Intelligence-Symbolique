"""
Script d'exemple pour l'utilisation de l'architecture hiérarchique à trois niveaux.

Ce script démontre comment utiliser l'architecture hiérarchique pour réaliser
une analyse rhétorique complète d'un texte.
"""

import os
import sys
import asyncio
import logging
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional

# Ajouter le répertoire parent au path pour pouvoir importer les modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from argumentiation_analysis.orchestration.hierarchical.strategic.state import StrategicState
from argumentiation_analysis.orchestration.hierarchical.tactical.state import TacticalState
from argumentiation_analysis.orchestration.hierarchical.operational.state import OperationalState

from argumentiation_analysis.orchestration.hierarchical.interfaces.strategic_tactical import StrategicTacticalInterface
from argumentiation_analysis.orchestration.hierarchical.interfaces.tactical_operational import TacticalOperationalInterface

from argumentiation_analysis.orchestration.hierarchical.strategic.manager import StrategicManager
from argumentiation_analysis.orchestration.hierarchical.strategic.planner import StrategicPlanner
from argumentiation_analysis.orchestration.hierarchical.strategic.allocator import ResourceAllocator

from argumentiation_analysis.orchestration.hierarchical.tactical.coordinator import TacticalCoordinator
from argumentiation_analysis.orchestration.hierarchical.tactical.monitor import TaskMonitor
from argumentiation_analysis.orchestration.hierarchical.tactical.resolver import ConflictResolver

from argumentiation_analysis.orchestration.hierarchical.operational.manager import OperationalManager
from argumentiation_analysis.orchestration.hierarchical.operational.agent_registry import AgentRegistry

from argumentiation_analysis.orchestration.hierarchical.operational.adapters.extract_agent_adapter import ExtractAgentAdapter
from argumentiation_analysis.orchestration.hierarchical.operational.adapters.informal_agent_adapter import InformalAgentAdapter
from argumentiation_analysis.orchestration.hierarchical.operational.adapters.pl_agent_adapter import PLAgentAdapter


class HierarchicalOrchestrator:
    """
    Orchestrateur utilisant l'architecture hiérarchique à trois niveaux.
    
    Cette classe coordonne les trois niveaux de l'architecture pour réaliser
    une analyse rhétorique complète d'un texte.
    """
    
    def __init__(self):
        """Initialise l'orchestrateur hiérarchique."""
        # Configurer le logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger("HierarchicalOrchestrator")
        
        # Créer les états
        self.strategic_state = StrategicState()
        self.tactical_state = TacticalState()
        self.operational_state = OperationalState()
        
        # Créer les interfaces
        self.strategic_tactical_interface = StrategicTacticalInterface(
            strategic_state=self.strategic_state,
            tactical_state=self.tactical_state
        )
        
        self.tactical_operational_interface = TacticalOperationalInterface(
            tactical_state=self.tactical_state,
            operational_state=self.operational_state
        )
        
        # Créer les composants stratégiques
        self.strategic_planner = StrategicPlanner(strategic_state=self.strategic_state)
        self.resource_allocator = ResourceAllocator(strategic_state=self.strategic_state)
        self.strategic_manager = StrategicManager(
            strategic_state=self.strategic_state,
            strategic_tactical_interface=self.strategic_tactical_interface,
            planner=self.strategic_planner,
            allocator=self.resource_allocator
        )
        
        # Créer les composants tactiques
        self.task_monitor = TaskMonitor(tactical_state=self.tactical_state)
        self.conflict_resolver = ConflictResolver(tactical_state=self.tactical_state)
        self.tactical_coordinator = TacticalCoordinator(
            tactical_state=self.tactical_state,
            strategic_tactical_interface=self.strategic_tactical_interface,
            tactical_operational_interface=self.tactical_operational_interface,
            monitor=self.task_monitor,
            resolver=self.conflict_resolver
        )
        
        # Créer les composants opérationnels
        self.agent_registry = AgentRegistry()
        self.operational_manager = OperationalManager(
            operational_state=self.operational_state,
            tactical_operational_interface=self.tactical_operational_interface,
            agent_registry=self.agent_registry
        )
        
        # Initialiser les agents
        self.initialize_agents()
    
    def initialize_agents(self):
        """Initialise et enregistre les agents opérationnels."""
        # Créer les adaptateurs d'agents
        extract_agent = ExtractAgentAdapter(name="ExtractAgent")
        informal_agent = InformalAgentAdapter(name="InformalAgent")
        pl_agent = PLAgentAdapter(name="PLAgent")
        
        # Enregistrer les agents
        self.agent_registry.register_agent(extract_agent)
        self.agent_registry.register_agent(informal_agent)
        self.agent_registry.register_agent(pl_agent)
        
        self.logger.info(f"Agents enregistrés: {len(self.agent_registry.get_all_agents())}")
    
    async def initialize_all_agents(self):
        """Initialise tous les agents enregistrés."""
        self.logger.info("Initialisation de tous les agents...")
        
        for agent in self.agent_registry.get_all_agents():
            if hasattr(agent, 'initialize') and callable(agent.initialize):
                await agent.initialize()
        
        self.logger.info("Tous les agents ont été initialisés.")
    
    async def analyze_text(self, text: str, analysis_type: str = "complete") -> Dict[str, Any]:
        """
        Analyse un texte en utilisant l'architecture hiérarchique.
        
        Args:
            text: Le texte à analyser
            analysis_type: Le type d'analyse à réaliser (complete, fallacies, arguments, formal)
            
        Returns:
            Un dictionnaire contenant les résultats de l'analyse
        """
        self.logger.info(f"Début de l'analyse de type '{analysis_type}'")
        
        # Initialiser tous les agents
        await self.initialize_all_agents()
        
        # 1. Définir les objectifs stratégiques en fonction du type d'analyse
        objectives = self._create_objectives(analysis_type)
        
        # Ajouter les objectifs à l'état stratégique
        for objective in objectives:
            self.strategic_state.add_objective(objective)
        
        # 2. Créer un plan stratégique
        strategic_plan = self.strategic_planner.create_plan(objectives)
        
        # Ajouter le plan à l'état stratégique
        self.strategic_state.strategic_plan = strategic_plan
        
        # 3. Allouer les ressources
        self.resource_allocator.allocate_resources(objectives)
        
        # 4. Traduire les objectifs en directives tactiques
        tactical_directives = self.strategic_tactical_interface.translate_objectives(objectives)
        
        # 5. Créer des tâches tactiques à partir des directives
        tasks = self.tactical_coordinator.create_tasks(tactical_directives)
        
        # 6. Ajouter le texte à analyser comme source
        source_id = self.tactical_state.add_source({
            "id": f"source-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "type": "text",
            "content": text
        })
        
        # 7. Mettre à jour les tâches avec la source
        for task in tasks:
            task["source_id"] = source_id
            self.tactical_state.add_task(task)
        
        # 8. Exécuter les tâches
        await self.tactical_coordinator.execute_tasks()
        
        # 9. Attendre que toutes les tâches soient terminées
        while not self.tactical_coordinator.all_tasks_completed():
            self.logger.info("Attente de la fin des tâches...")
            await asyncio.sleep(1)
        
        # 10. Créer un rapport tactique
        tactical_report = self.tactical_coordinator.create_report()
        
        # 11. Traiter le rapport tactique au niveau stratégique
        strategic_report = self.strategic_tactical_interface.process_tactical_report(tactical_report)
        
        # 12. Créer le rapport final
        final_report = self._create_final_report(strategic_report, tactical_report)
        
        self.logger.info("Analyse terminée")
        
        return final_report
    
    def _create_objectives(self, analysis_type: str) -> List[Dict[str, Any]]:
        """
        Crée les objectifs stratégiques en fonction du type d'analyse.
        
        Args:
            analysis_type: Le type d'analyse à réaliser
            
        Returns:
            Liste des objectifs stratégiques
        """
        if analysis_type == "complete":
            return [
                {
                    "id": "obj-1",
                    "description": "Identifier les arguments principaux dans le texte",
                    "priority": "high"
                },
                {
                    "id": "obj-2",
                    "description": "Détecter les sophismes dans le texte",
                    "priority": "high"
                },
                {
                    "id": "obj-3",
                    "description": "Analyser la validité formelle des arguments",
                    "priority": "medium"
                },
                {
                    "id": "obj-4",
                    "description": "Évaluer la cohérence globale de l'argumentation",
                    "priority": "medium"
                }
            ]
        elif analysis_type == "fallacies":
            return [
                {
                    "id": "obj-1",
                    "description": "Détecter les sophismes dans le texte",
                    "priority": "high"
                },
                {
                    "id": "obj-2",
                    "description": "Identifier les arguments principaux dans le texte",
                    "priority": "medium"
                }
            ]
        elif analysis_type == "arguments":
            return [
                {
                    "id": "obj-1",
                    "description": "Identifier les arguments principaux dans le texte",
                    "priority": "high"
                },
                {
                    "id": "obj-2",
                    "description": "Évaluer la cohérence globale de l'argumentation",
                    "priority": "medium"
                }
            ]
        elif analysis_type == "formal":
            return [
                {
                    "id": "obj-1",
                    "description": "Identifier les arguments principaux dans le texte",
                    "priority": "high"
                },
                {
                    "id": "obj-2",
                    "description": "Analyser la validité formelle des arguments",
                    "priority": "high"
                }
            ]
        else:
            # Par défaut, analyse complète
            return self._create_objectives("complete")
    
    def _create_final_report(self, strategic_report: Dict[str, Any], tactical_report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crée le rapport final à partir des rapports stratégique et tactique.
        
        Args:
            strategic_report: Le rapport stratégique
            tactical_report: Le rapport tactique
            
        Returns:
            Le rapport final
        """
        # Extraire les résultats des tâches
        task_results = {}
        for task_id, task in self.tactical_state.get_completed_tasks().items():
            task_results[task_id] = task.get("results", {})
        
        # Créer le rapport final
        final_report = {
            "timestamp": datetime.now().isoformat(),
            "overall_progress": strategic_report["metrics"]["progress"],
            "quality_score": strategic_report["metrics"]["quality_indicators"]["quality_score"],
            "results": {
                "arguments": self._extract_arguments(task_results),
                "fallacies": self._extract_fallacies(task_results),
                "formal_analyses": self._extract_formal_analyses(task_results),
                "coherence_evaluation": self._extract_coherence_evaluation(task_results)
            },
            "metrics": {
                "strategic": strategic_report["metrics"],
                "tactical": tactical_report.get("metrics", {})
            },
            "issues": strategic_report["issues"]
        }
        
        return final_report
    
    def _extract_arguments(self, task_results: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extrait les arguments identifiés des résultats des tâches.
        
        Args:
            task_results: Les résultats des tâches
            
        Returns:
            Liste des arguments identifiés
        """
        arguments = []
        
        for task_id, results in task_results.items():
            if "identified_arguments" in results:
                arguments.extend(results["identified_arguments"])
        
        return arguments
    
    def _extract_fallacies(self, task_results: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extrait les sophismes détectés des résultats des tâches.
        
        Args:
            task_results: Les résultats des tâches
            
        Returns:
            Liste des sophismes détectés
        """
        fallacies = []
        
        for task_id, results in task_results.items():
            if "identified_fallacies" in results:
                fallacies.extend(results["identified_fallacies"])
        
        return fallacies
    
    def _extract_formal_analyses(self, task_results: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extrait les analyses formelles des résultats des tâches.
        
        Args:
            task_results: Les résultats des tâches
            
        Returns:
            Liste des analyses formelles
        """
        formal_analyses = []
        
        for task_id, results in task_results.items():
            if "formal_analyses" in results:
                formal_analyses.extend(results["formal_analyses"])
        
        return formal_analyses
    
    def _extract_coherence_evaluation(self, task_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extrait l'évaluation de cohérence des résultats des tâches.
        
        Args:
            task_results: Les résultats des tâches
            
        Returns:
            L'évaluation de cohérence
        """
        for task_id, results in task_results.items():
            if "coherence_analysis" in results:
                return results["coherence_analysis"]
        
        return {
            "score": 0.0,
            "inconsistencies": [],
            "explanation": "Aucune analyse de cohérence disponible"
        }


async def main():
    """Fonction principale du script."""
    # Analyser les arguments de la ligne de commande
    parser = argparse.ArgumentParser(description="Analyse rhétorique utilisant l'architecture hiérarchique")
    parser.add_argument("--file", "-f", help="Fichier texte à analyser")
    parser.add_argument("--text", "-t", help="Texte à analyser")
    parser.add_argument("--type", "-y", choices=["complete", "fallacies", "arguments", "formal"],
                        default="complete", help="Type d'analyse à réaliser")
    parser.add_argument("--output", "-o", help="Fichier de sortie pour les résultats (JSON)")
    args = parser.parse_args()
    
    # Vérifier qu'un texte ou un fichier est fourni
    if not args.file and not args.text:
        parser.error("Vous devez fournir un fichier ou un texte à analyser")
    
    # Lire le texte à analyser
    text = args.text
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception as e:
            print(f"Erreur lors de la lecture du fichier: {e}")
            return
    
    # Créer l'orchestrateur
    orchestrator = HierarchicalOrchestrator()
    
    # Analyser le texte
    results = await orchestrator.analyze_text(text, args.type)
    
    # Afficher les résultats
    if args.output:
        import json
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"Résultats enregistrés dans {args.output}")
        except Exception as e:
            print(f"Erreur lors de l'enregistrement des résultats: {e}")
    else:
        # Afficher un résumé des résultats
        print("\n=== RÉSULTATS DE L'ANALYSE ===")
        print(f"Progression globale: {results['overall_progress'] * 100:.1f}%")
        print(f"Score de qualité: {results['quality_score'] * 100:.1f}%")
        
        print("\nArguments identifiés:")
        for arg in results["results"]["arguments"]:
            print(f"- {arg['id']}: {arg['conclusion']} (confiance: {arg['confidence'] * 100:.1f}%)")
        
        print("\nSophismes détectés:")
        for fallacy in results["results"]["fallacies"]:
            print(f"- {fallacy['id']}: {fallacy['type']} (confiance: {fallacy['confidence'] * 100:.1f}%)")
            print(f"  Segment: {fallacy['segment']}")
            print(f"  Explication: {fallacy['explanation']}")
        
        print("\nAnalyses formelles:")
        for analysis in results["results"]["formal_analyses"]:
            validity = "valide" if analysis["is_valid"] else "invalide"
            print(f"- Argument {analysis['argument_id']}: {validity}")
            print(f"  Formalisation: {analysis['formalization']}")
            print(f"  Explication: {analysis['explanation']}")
        
        print("\nÉvaluation de la cohérence:")
        coherence = results["results"]["coherence_evaluation"]
        print(f"Score de cohérence: {coherence['score'] * 100:.1f}%")
        print(f"Explication: {coherence['explanation']}")
        
        if coherence["inconsistencies"]:
            print("Incohérences détectées:")
            for inconsistency in coherence["inconsistencies"]:
                print(f"- {inconsistency}")


if __name__ == "__main__":
    asyncio.run(main())