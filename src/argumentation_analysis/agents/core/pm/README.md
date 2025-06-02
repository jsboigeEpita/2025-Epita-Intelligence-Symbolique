# 🧑‍🏫 Project Manager Agent (`agents/pm/`)

Agent responsable de l'orchestration globale de l'analyse rhétorique collaborative.

[Retour au README Agents](../README.md)

## Rôle 🎯

* **Analyser** la demande initiale et l'état actuel de l'analyse via `StateManager.get_current_state_snapshot`.
* **Planifier** la prochaine étape logique en suivant une séquence idéale (Arguments -> Sophismes -> Traduction PL -> Requêtes PL -> Conclusion).
* **Définir** les tâches d'analyse spécifiques pour les agents spécialistes via `StateManager.add_analysis_task` (utilisant `PM.semantic_DefineTasksAndDelegate`).
* **Déléguer** explicitement la tâche à l'agent approprié via `StateManager.designate_next_agent` (en utilisant le **nom exact** de l'agent).
* **Suivre** l'avancement en vérifiant quelles tâches ont reçu une réponse dans l'état (`tasks_answered`).
* **Synthétiser** les résultats et enregistrer la conclusion finale via `StateManager.set_final_conclusion` (utilisant `PM.semantic_WriteAndSetConclusion`) uniquement lorsque l'analyse est jugée complète.

## Composants 🛠️

* **[`pm_definitions.py`](./pm_definitions.py)** :
    * `ProjectManagerPlugin`: Classe pour fonctions natives (vide actuellement).
    * `setup_pm_kernel`: Fonction de configuration du kernel SK pour cet agent.
    * `PM_INSTRUCTIONS`: Instructions système détaillant le processus décisionnel et les règles de délégation.
* **[`prompts.py`](./prompts.py)** :
    * `prompt_define_tasks_v*`: Prompt pour la planification et la délégation.
    * `prompt_write_conclusion_v*`: Prompt pour la synthèse et la conclusion.