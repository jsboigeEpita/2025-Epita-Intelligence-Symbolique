import logging
from typing import Dict, Any, List
import semantic_kernel as sk
from argumentation_analysis.agents.core.extract import ExtractAgent, ExtractResult
from argumentation_analysis.agents.core.informal import InformalAnalysisAgent
from argumentation_analysis.agents.core.logic.propositional_logic_agent import PropositionalLogicAgent
from argumentation_analysis.agents.core.synthesis import SynthesisAgent, LogicAnalysisResult, InformalAnalysisResult

# Configuration de base pour le logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DirectOperationalExecutor:
    """
    Exécuteur opérationnel direct pour le Pipeline 1.
    Coordonne les agents spécialisés de manière séquentielle.
    """
    def __init__(self, kernel: sk.Kernel):
        """
        Initialise l'exécuteur avec un kernel Semantic Kernel.
        """
        self.kernel = kernel
        self.extract_agent = ExtractAgent(kernel)
        self.extract_agent.setup_agent_components(llm_service_id="default")
        
        self.informal_agent = InformalAnalysisAgent(kernel)
        self.informal_agent.setup_agent_components(llm_service_id="default")

        self.logic_agent = PropositionalLogicAgent(kernel, service_id="default")
        self.logic_agent.setup_agent_components(llm_service_id="default")
        
        self.synthesis_agent = SynthesisAgent(kernel)
        self.synthesis_agent.setup_agent_components(llm_service_id="default")

        # Les autres agents seront initialisés ici dans les prochaines étapes
        logger.info("DirectOperationalExecutor initialisé avec tous les agents opérationnels.")

    async def execute_operational_pipeline(self, text_input: str, tactical_results: Dict, chat_history: List[Dict[str, str]] = None) -> Dict:
        """
        Exécute la pipeline opérationnelle avec de vrais agents.
        
        Séquence d'exécution :
        1. ExtractAgent : Extraction d'informations structurées
        2. InformalAgent : Analyse rhétorique et sophismes
        3. PropositionalLogicAgent : Analyse logique formelle
        4. SynthesisAgent : Synthèse unifiée des résultats
        """
        
        # NOTE: Les implémentations réelles des appels aux agents seront ajoutées
        # dans les prochaines étapes. Pour l'instant, ce sont des placeholders.

        # Étape 1 : Extraction
        extract_results = await self._execute_extract_agent(text_input, tactical_results)
        
        # Étape 2 : Analyse Informelle
        informal_results = await self._execute_informal_agent(text_input, extract_results)
        
        # Étape 3 : Analyse Logique
        logic_results = await self._execute_logic_agent(text_input, extract_results, chat_history)
        
        # Étape 4 : Synthèse
        synthesis_results = await self._execute_synthesis_agent(
            text_input, extract_results, informal_results, logic_results
        )
        
        return self._format_unified_results(synthesis_results)

    async def _execute_extract_agent(self, text_input: str, tactical_results: Dict) -> Dict:
        """
        Exécute les tâches d'extraction définies dans le plan tactique.
        """
        logger.info("Début de l'étape d'extraction...")
        extraction_tasks = [task for task in tactical_results.get("tasks", []) if task.get("type") == "extraction"]
        
        if not extraction_tasks:
            logger.info("Aucune tâche d'extraction à exécuter.")
            return {"extracted_data": [], "status": "no_task"}

        results = []
        for task in extraction_tasks:
            extract_name = task.get("parameters", {}).get("extract_name")
            if not extract_name:
                logger.warning(f"Tâche d'extraction ignorée car 'extract_name' est manquant: {task}")
                continue

            logger.info(f"Exécution de l'extraction pour : '{extract_name}'")
            source_info = {"source_name": "Input Text"} # Info source basique
            
            try:
                extract_result: ExtractResult = await self.extract_agent.extract_from_name(
                    source_info=source_info,
                    extract_name=extract_name,
                    source_text=text_input
                )
                results.append(extract_result.to_dict())
                logger.info(f"Extraction pour '{extract_name}' terminée avec le statut : {extract_result.status}")
            except Exception as e:
                logger.error(f"Erreur lors de l'extraction pour '{extract_name}': {e}", exc_info=True)
                results.append({
                    "extract_name": extract_name,
                    "status": "error",
                    "message": str(e)
                })

        final_result = {"extracted_data": results, "status": "completed"}
        logger.info("Étape d'extraction terminée.")
        return final_result

    async def _execute_informal_agent(self, text_input: str, extract_results: Dict) -> Dict:
        """
        Exécute l'analyse informelle sur le texte d'entrée.
        """
        logger.info("Début de l'étape d'analyse informelle...")
        
        try:
            # Pour cette première version, nous analysons le texte complet.
            # Une version plus avancée pourrait itérer sur les extraits.
            informal_results = await self.informal_agent.analyze_fallacies(text_input)
            
            logger.info(f"Analyse informelle terminée, {len(informal_results)} sophismes trouvés.")
            return {"informal_analysis": informal_results, "status": "completed"}
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse informelle: {e}", exc_info=True)
            return {"informal_analysis": [], "status": "error", "message": str(e)}

    async def _execute_logic_agent(self, text_input: str, extract_results: Dict, chat_history: List[Dict[str, str]] = None) -> Dict:
        """
        Exécute l'analyse logique propositionnelle sur le texte d'entrée.
        Prend en compte l'historique de conversation si disponible.
        """
        logger.info("Début de l'étape d'analyse logique...")
        try:
            # Si un historique de chat est fourni, l'utiliser pour l'analyse
            if chat_history:
                logger.info("Utilisation de l'historique de conversation pour l'analyse logique.")
                # L'agent logique doit être appelé avec l'historique
                # Note: `invoke_single` est un placeholder conceptuel, nous utilisons
                # `text_to_belief_set_with_history` si c'est la méthode réelle.
                # Pour l'instant, nous adaptons au code existant qui appelle `text_to_belief_set`
                
                # Création d'un historique simple pour la méthode text_to_belief_set
                # Ceci est un workaround, l'idéal serait d'avoir une méthode dédiée.
                belief_set, message = await self.logic_agent.invoke_single(chat_history=chat_history)

            else:
                logger.info("Analyse logique sans historique de conversation.")
                belief_set, message = await self.logic_agent.text_to_belief_set(text_input)
            
            if belief_set:
                logger.info("Analyse logique terminée avec succès, BeliefSet créé.")
                return {
                    "logic_analysis": belief_set.to_dict(),
                    "status": "completed",
                    "message": message
                }
            else:
                logger.warning(f"Échec de la création du BeliefSet: {message}")
                return {
                    "logic_analysis": None,
                    "status": "error",
                    "message": message
                }

        except Exception as e:
            logger.error(f"Erreur lors de l'analyse logique: {e}", exc_info=True)
            return {"logic_analysis": None, "status": "error", "message": str(e)}

    async def _execute_synthesis_agent(self, text_input: str, extract_results: Dict, informal_results: Dict, logic_results: Dict) -> Dict:
        """
        Exécute l'agent de synthèse pour unifier les résultats des analyses précédentes.
        """
        logger.info("Début de l'étape de synthèse...")
        try:
            # Convertir les dictionnaires de résultats en objets Pydantic attendus par l'agent de synthèse
            # Note: C'est une conversion basique. Une vraie implémentation pourrait nécessiter un mapping plus complexe.
            logic_analysis_result = LogicAnalysisResult(
                propositional_result=logic_results.get("logic_analysis")
            )
            
            informal_analysis_result = InformalAnalysisResult(
                fallacies_detected=informal_results.get("informal_analysis", [])
            )

            # Appel de la méthode d'unification
            unified_report = await self.synthesis_agent.unify_results(
                logic_result=logic_analysis_result,
                informal_result=informal_analysis_result,
                original_text=text_input
            )
            
            logger.info("Étape de synthèse terminée avec succès.")
            return {"synthesis_report": unified_report.to_dict(), "status": "completed"}

        except Exception as e:
            logger.error(f"Erreur lors de la synthèse: {e}", exc_info=True)
            return {"synthesis_report": None, "status": "error", "message": str(e)}

    def _format_unified_results(self, synthesis_results: Dict) -> Dict:
        """
        Formate les résultats finaux de la pipeline opérationnelle.
        """
        if synthesis_results.get("status") == "completed":
            return {
                "status": "success",
                "results": synthesis_results.get("synthesis_report")
            }
        else:
            return {
                "status": "error",
                "message": "La pipeline opérationnelle a échoué à l'étape de synthèse.",
                "details": synthesis_results.get("message")
            }