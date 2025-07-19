# Fichier: argumentation_analysis/orchestration/fallacy_workflow_orchestrator.py

import asyncio
from typing import List, Dict, Any
from semantic_kernel import Kernel

# Importer les outils que nous venons de créer
from .plugins.exploration_tool import ExplorationTool
from .plugins.hypothesis_validation_tool import HypothesisValidationTool
from .plugins.aggregation_tool import AggregationTool

class CounterArgumentAgent:
    """
    Orchestre le workflow d'analyse de sophismes en utilisant des outils modulaires.
    """
    ALL_TOOLS = {
        "ExplorationTool": ExplorationTool,
        "HypothesisValidationTool": HypothesisValidationTool,
        "AggregationTool": AggregationTool,
    }

    def __init__(self, kernel: Kernel, enabled_tools: List[str] = None):
        """
        Initialise l'orchestrateur.

        Args:
            kernel: Le Kernel sémantique configuré.
            enabled_tools: Liste des noms de classes des outils à activer.
                           Si None, tous les outils sont activés.
        """
        self.kernel = kernel
        self.enabled_tools = enabled_tools or list(self.ALL_TOOLS.keys())
        self.plugins = {}
        print(f"CounterArgumentAgent initialisé avec les outils : {self.enabled_tools}")

    def _load_plugins(self, taxonomy: Any):
        """Charge les plugins demandés dans le kernel."""
        # Vide les plugins existants pour eviter les doublons
        self.kernel.remove_all_plugins()
        self.plugins = {}

        for tool_name in self.enabled_tools:
            if tool_name in self.ALL_TOOLS:
                tool_class = self.ALL_TOOLS[tool_name]
                # L'outil d'exploration est le seul à nécessiter la taxonomie
                if tool_name == "ExplorationTool":
                    instance = tool_class(taxonomy)
                else:
                    instance = tool_class()
                self.plugins[tool_name] = self.kernel.add_plugin(instance, tool_name)
                print(f"Plugin '{tool_name}' chargé.")

    async def analyze_argument(self, argument_text: str, taxonomy: Any) -> Dict[str, Any]:
        """
        Exécute le workflow complet d'analyse d'un argument.

        Args:
            argument_text: Le texte de l'argument à analyser.
            taxonomy: L'objet taxonomie nécessaire pour l'outil d'exploration.

        Returns:
            Un rapport d'analyse final et complet.
        """
        print(f"\n--- Début de l'analyse de l'argument : '{argument_text[:60]}...' ---")
        
        # Charger les plugins configurés
        self._load_plugins(taxonomy)

        # Vérifier que les outils nécessaires sont bien chargés
        if "ExplorationTool" not in self.plugins:
            raise ValueError("L'outil 'ExplorationTool' est essentiel et doit être activé.")


        # === Étape 1: Générer des hypothèses d'exploration ===
        print("\n[Étape 1/3] Génération des hypothèses d'exploration...")
        hypotheses_result = await self.kernel.invoke(
            self.plugins["ExplorationTool"]["get_exploration_hypotheses"],
            input=argument_text
        )
        # La valeur de retour est un dictionnaire de la forme {node_id: branch_details}
        fallacy_hypotheses = hypotheses_result.value
        
        if not fallacy_hypotheses:
            print("Aucune hypothèse de sophisme pertinente n'a été trouvée.")
            return {"summary": "L'analyse n'a pas pu identifier de pistes de sophismes à explorer.", "details": []}
            
        print(f"-> {len(fallacy_hypotheses)} hypothèses de sophismes à valider trouvées.")

        # === Étape 2: Valider chaque hypothèse en parallèle ===
        print("\n[Étape 2/3] Validation des hypothèses en parallèle...")
        validation_tasks = []
        if "HypothesisValidationTool" in self.plugins:
            for node_id, hypothesis_details in fallacy_hypotheses.items():
                hypothesis_input = {
                    "id": node_id,
                    "name": hypothesis_details.get("name", "N/A"),
                    "description": hypothesis_details.get("description", "N/A"),
                }
                task = self.kernel.invoke(
                    self.plugins["HypothesisValidationTool"]["validate_fallacy"],
                    argument_text=argument_text,
                    fallacy_hypothesis=hypothesis_input
                )
                validation_tasks.append(task)
        else:
            # Si l'outil de validation est désactivé, on passe les hypothèses comme résultats validés.
            print("-> Outil de validation désactivé. Les hypothèses sont considérées comme des rapports bruts.")
            validation_results = [hypotheses_result]
        
        # Exécuter toutes les tâches de validation simultanément
        validation_results = await asyncio.gather(*validation_tasks)
        print(f"-> {len(validation_results)} rapports de validation reçus.")

        # === Étape 3: Agréger les résultats en un rapport final ===
        print("\n[Étape 3/3] Agrégation du rapport final...")
        # Si l'outil de validation a été sauté, les résultats sont déjà dans `validation_results`
        if validation_tasks:
            validation_results = await asyncio.gather(*validation_tasks)
            print(f"-> {len(validation_results)} rapports de validation reçus.")
            report_list = [res.value for res in validation_results]
        else:
            # On transforme directement les hypothèses en "rapport"
             report_list = list(fallacy_hypotheses.values())


        if "AggregationTool" in self.plugins:
             final_report_result = await self.kernel.invoke(
                self.plugins["AggregationTool"]["summarize_reports"],
                reports=str(report_list)
            )
        else:
            print("-> Outil d'agrégation désactivé. Retour des rapports bruts.")
            return {"summary": "Agrégation désactivée.", "details": report_list}
        
        final_report = final_report_result.value
        print("-> Rapport final généré.")
        
        print("\n--- Analyse terminée. ---")
        return final_report