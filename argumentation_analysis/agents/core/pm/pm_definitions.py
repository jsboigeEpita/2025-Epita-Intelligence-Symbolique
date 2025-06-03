# agents/core/pm/pm_definitions.py
import semantic_kernel as sk
import logging
# Importer les prompts depuis le fichier voisin
from .prompts import prompt_define_tasks_v10, prompt_write_conclusion_v6

logger = logging.getLogger("Orchestration.AgentPM.Defs")
setup_logger = logging.getLogger("Orchestration.AgentPM.Setup") # Pour la fonction setup

# --- Plugin Spécifique PM (Vide actuellement) ---
class ProjectManagerPlugin:
    """Plugin pour fonctions natives spécifiques au Project Manager (si nécessaire)."""
    # Ajoutez ici des @kernel_function natives si besoin plus tard
    pass

logger.info("Plugin PM (vide) défini.")

# --- Fonction setup_pm_kernel ---
def setup_pm_kernel(kernel: sk.Kernel, llm_service):
    """Ajoute le plugin PM et ses fonctions sémantiques au kernel donné."""
    plugin_name = "PM"
    logger.info(f"Configuration Kernel pour {plugin_name} (V10 - Fix Désignation)...")

    if plugin_name not in kernel.plugins:
        kernel.add_plugin(ProjectManagerPlugin(), plugin_name=plugin_name)
        logger.debug(f"Plugin natif '{plugin_name}' ajouté au kernel PM.")
    else:
        logger.debug(f"Plugin natif '{plugin_name}' déjà présent dans le kernel PM.")

    default_settings = None
    if llm_service:
        try:
            default_settings = kernel.get_prompt_execution_settings_from_service_id(llm_service.service_id)
            logger.debug(f"Settings LLM récupérés pour {plugin_name}.")
        except Exception as e:
            logger.warning(f"Impossible de récupérer les settings LLM pour {plugin_name}: {e}")

    try:
        kernel.add_function(
            prompt=prompt_define_tasks_v10,
            plugin_name=plugin_name, function_name="semantic_DefineTasksAndDelegate",
            description="Définit la PROCHAINE tâche unique, l'enregistre, désigne 1 agent (Nom Exact Requis).",
            prompt_execution_settings=default_settings
        )
        logger.debug(f"Fonction {plugin_name}.semantic_DefineTasksAndDelegate (V10) ajoutée/mise à jour.")
    except ValueError as ve: logger.warning(f"Problème ajout/MàJ {plugin_name}.semantic_DefineTasksAndDelegate: {ve}")

    try:
        kernel.add_function(
            prompt=prompt_write_conclusion_v6,
            plugin_name=plugin_name, function_name="semantic_WriteAndSetConclusion",
            description="Rédige/enregistre conclusion finale (avec pré-vérification état).",
            prompt_execution_settings=default_settings
        )
        logger.debug(f"Fonction {plugin_name}.semantic_WriteAndSetConclusion (V6) ajoutée/mise à jour.")
    except ValueError as ve: logger.warning(f"Problème ajout/MàJ {plugin_name}.semantic_WriteAndSetConclusion: {ve}")

    logger.info(f"Kernel {plugin_name} configuré (V10).")

# --- Instructions Système ---
# (Provenant de la cellule [ID: 35a8132b] du notebook 'Argument_Analysis_Agentic-0-init.ipynb')
PM_INSTRUCTIONS_V9 = """
Votre Rôle: Chef d'orchestre. Vous devez coordonner les autres agents.
# <<< NOTE: La liste des agents pourrait être injectée ici via une variable de prompt >>>
**Noms Exacts des Agents à utiliser pour la désignation:** "InformalAnalysisAgent", "PropositionalLogicAgent", "ExtractAgent".
**ATTENTION:** Ne confondez pas le nom de l'agent "InformalAnalysisAgent" avec le nom de son plugin "InformalAnalyzer". Pour la désignation via `StateManager.designate_next_agent`, utilisez TOUJOURS "InformalAnalysisAgent".

**Processus OBLIGATOIRE:**

1.  **CONSULTER ÉTAT:** Appelez `StateManager.get_current_state_snapshot(summarize=True)`. Analysez **minutieusement** `tasks_defined`, `tasks_answered`, `final_conclusion`, et les derniers éléments ajoutés.
2.  **DÉCIDER ACTION:**
    * **A. Tâche Suivante?** Si une étape logique de la séquence (Extraction -> Args -> Sophismes -> PL Trad -> PL Query) est terminée (tâche correspondante dans `tasks_answered`) ET que la suivante n'a pas été lancée OU si aucune tâche n'existe :
        1.  Appelez `StateManager.get_current_state_snapshot(summarize=False)` (`snapshot_json`).
        2.  **CRUCIAL : Pour définir la prochaine tâche et désigner un agent, vous devez IMPÉRATIVEMENT appeler VOTRE PROPRE fonction sémantique `PM.semantic_DefineTasksAndDelegate`.** Passez `analysis_state_snapshot=snapshot_json` et `raw_text=[Contenu texte]` à cette fonction. NE TENTEZ JAMAIS d'appeler directement les fonctions sémantiques d'autres agents (comme `InformalAnalyzer.semantic_IdentifyArguments` ou `PropositionalLogicAgent_Refactored-TextToPLBeliefSet`). Votre rôle est d'orchestrer via `PM.semantic_DefineTasksAndDelegate`.
        3.  La sortie de `PM.semantic_DefineTasksAndDelegate` vous donnera les appels exacts à faire pour `StateManager.add_analysis_task` et `StateManager.designate_next_agent`, ainsi que le message de délégation. Formulez le message texte de délégation EXACTEMENT comme indiqué.
    * **B. Attente?** Si une tâche définie (`tasks_defined`) N'EST PAS dans `tasks_answered` -> Réponse: "J'attends la réponse de [Agent Probable] pour la tâche [ID Tâche manquante]." **NE PAS DEFINIR de nouvelle tâche.**
    * **C. Fin?** Si TOUTES les étapes d'analyse pertinentes (Extraction, Arguments, Sophismes, PL si pertinent) semblent terminées (vérifiez les `answers` pour les tâches correspondantes) ET `final_conclusion` est `null`:
        1. Appelez `StateManager.get_current_state_snapshot(summarize=False)` (`snapshot_json`).
        2. Appelez `PM.semantic_WriteAndSetConclusion(analysis_state_snapshot=snapshot_json, raw_text=[Contenu texte])`.
        3. Formulez un message indiquant que la conclusion est prête et enregistrée.
    * **D. Déjà Fini?** Si `final_conclusion` n'est PAS `null` -> Réponse: "L'analyse est déjà terminée."

**Règles CRITIQUES:**
* Pas d'analyse personnelle. Suivi strict de l'état (tâches/réponses).
* **Utilisez les noms d'agent EXACTS** ("InformalAnalysisAgent", "PropositionalLogicAgent", "ExtractAgent") lors de la désignation via `StateManager.designate_next_agent` (cet appel sera généré par `PM.semantic_DefineTasksAndDelegate`).
* Format de délégation strict.
* **UNE SEULE** tâche et **UNE SEULE** désignation par étape de planification (gérées par `PM.semantic_DefineTasksAndDelegate`).
* Ne concluez que si TOUT le travail pertinent est fait et vérifié dans l'état.
"""
PM_INSTRUCTIONS = PM_INSTRUCTIONS_V9
logger.info("Instructions Système PM_INSTRUCTIONS (V9 - Ajout ExtractAgent) définies.")

# Log de chargement
logging.getLogger(__name__).debug("Module agents.pm.pm_definitions chargé.")