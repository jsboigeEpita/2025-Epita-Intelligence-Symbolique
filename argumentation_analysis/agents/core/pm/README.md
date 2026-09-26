# 🧑‍🏫 Project Manager Agent (`ProjectManagerAgent`)

L'agent `ProjectManagerAgent` est au cœur de la coordination des processus d'analyse d'argumentation. Il ne gère pas directement l'état ou l'exécution des tâches des autres agents, mais il est responsable de la planification stratégique, de la définition des tâches et de la synthèse finale.

[Retour au README Agents](../README.md)

## Rôle et Fonctionnement 🎯

Le `ProjectManagerAgent` opère en plusieurs étapes clés, généralement sous la supervision d'un orchestrateur :

1.  **Analyse de la Demande et de l'État :**
    *   Prend en entrée l'état actuel de l'analyse (fourni par l'orchestrateur, souvent un instantané du `StateManager`) et le texte brut à analyser.
    *   Son instruction système (`PM_INSTRUCTIONS` dans [`pm_definitions.py`](./pm_definitions.py)) le guide sur la manière d'interpréter ces informations.

2.  **Planification et Définition des Tâches :**
    *   Utilise sa fonction sémantique `DefineTasksAndDelegate` (basée sur [`prompt_define_tasks_v11`](./prompts.py)) pour déterminer la prochaine tâche d'analyse pertinente.
    *   Cette fonction génère une description de la tâche et identifie l'agent spécialiste (par son nom exact) le plus apte à l'exécuter.
    *   Le résultat de cette fonction est une *instruction* ou un *plan* que l'orchestrateur doit ensuite interpréter pour :
        *   Enregistrer la nouvelle tâche (par exemple, via `StateManager.add_analysis_task`).
        *   Désigner l'agent approprié (par exemple, via `StateManager.designate_next_agent`).

3.  **Rédaction de la Conclusion :**
    *   Lorsque l'orchestrateur juge que toutes les étapes d'analyse nécessaires sont complétées (basé sur l'état et potentiellement guidé par les instructions du PM), il peut demander au `ProjectManagerAgent` de rédiger la conclusion.
    *   L'agent utilise alors sa fonction sémantique `WriteAndSetConclusion` (basée sur [`prompt_write_conclusion_v7`](./prompts.py)).
    *   Cette fonction génère le texte de la conclusion finale.
    *   De même, le résultat est une *instruction* que l'orchestrateur interprète pour enregistrer cette conclusion (par exemple, via `StateManager.set_final_conclusion`).

L'agent PM n'interagit donc pas directement avec le `StateManager` ou d'autres agents. Il fournit l'intelligence stratégique que l'orchestrateur met en œuvre.

## Capacités 🛠️

Les capacités principales de l'agent sont exposées via ses méthodes et fonctions sémantiques :

*   **`get_agent_capabilities()`**: Retourne un dictionnaire décrivant ce que l'agent peut faire :
    *   `define_tasks_and_delegate`: "Defines analysis tasks and delegates them to specialist agents." (Génère le plan pour cela)
    *   `synthesize_results`: "Synthesizes results from specialist agents (implicite via conclusion)."
    *   `write_conclusion`: "Writes the final conclusion of the analysis." (Génère le texte de la conclusion)
    *   `coordinate_analysis_flow`: "Manages the overall workflow of the argumentation analysis based on the current state." (Via ses instructions et prompts)

*   **`async define_tasks_and_delegate(analysis_state_snapshot: str, raw_text: str) -> str`**:
    *   Invoque la fonction sémantique `DefineTasksAndDelegate`.
    *   **Entrée :** Un instantané de l'état de l'analyse et le texte brut.
    *   **Sortie :** Une chaîne de caractères (souvent structurée, ex: JSON) contenant la définition de la prochaine tâche et l'agent désigné. L'orchestrateur doit parser cette sortie.

*   **`async write_conclusion(analysis_state_snapshot: str, raw_text: str) -> str`**:
    *   Invoque la fonction sémantique `WriteAndSetConclusion`.
    *   **Entrée :** Un instantané de l'état de l'analyse (devrait refléter l'achèvement des tâches précédentes) et le texte brut.
    *   **Sortie :** Une chaîne de caractères contenant la conclusion finale. L'orchestrateur doit parser cette sortie.

## Composants Clés 🧩

*   **[`pm_agent.py`](./pm_agent.py)**: Contient la classe `ProjectManagerAgent` qui hérite de `BaseAgent`.
    *   `__init__(...)`: Initialise l'agent avec un kernel Semantic Kernel et un nom.
    *   `setup_agent_components(llm_service_id: str)`: Ajoute les fonctions sémantiques (`DefineTasksAndDelegate`, `WriteAndSetConclusion`) au kernel de l'agent.

*   **[`pm_definitions.py`](./pm_definitions.py)**:
    *   `PM_INSTRUCTIONS` (ou une version spécifique comme `PM_INSTRUCTIONS_V9`): Les instructions système qui définissent le comportement général, le processus décisionnel, et les règles de délégation de l'agent PM. C'est un élément crucial pour guider le LLM.

*   **[`prompts.py`](./prompts.py)**:
    *   `prompt_define_tasks_v*`: Le template de prompt utilisé par la fonction sémantique `DefineTasksAndDelegate`. Il guide le LLM pour analyser l'état, le texte, et déterminer la prochaine tâche et l'agent.
    *   `prompt_write_conclusion_v*`: Le template de prompt utilisé par la fonction sémantique `WriteAndSetConclusion`. Il guide le LLM pour synthétiser les informations de l'état et rédiger une conclusion.

## Utilisation et Extension 🚀

### Utilisation

1.  **Initialisation :**
    ```python
    from semantic_kernel import Kernel
    from argumentation_analysis.agents.core.pm.pm_agent import ProjectManagerAgent
    # Supposons qu'un kernel SK est déjà configuré avec un service LLM
    kernel_instance = Kernel() 
    # ... (configuration du kernel et ajout du service LLM avec un service_id, ex: "default_llm")

    pm_agent = ProjectManagerAgent(kernel=kernel_instance, agent_name="MyPMAgent")
    ```

2.  **Configuration des Composants :**
    ```python
    # "default_llm" est l'ID du service LLM configuré dans le kernel
    pm_agent.setup_agent_components(llm_service_id="default_llm") 
    ```

3.  **Invocation (par un orchestrateur) :**
    ```python
    # L'orchestrateur récupère l'état et le texte
    current_state_snapshot = '{"tasks_defined": [], "tasks_answered": {}, "final_conclusion": null}' # Exemple
    raw_text_to_analyze = "Le texte original..."

    # Pour définir la prochaine tâche
    task_definition_output = await pm_agent.define_tasks_and_delegate(current_state_snapshot, raw_text_to_analyze)
    # L'orchestrateur parse task_definition_output et agit en conséquence (MAJ StateManager, appel autre agent)

    # ... plus tard, pour écrire la conclusion ...
    # Supposons que l'état a été mis à jour après plusieurs étapes d'analyse
    concluding_state_snapshot = '{"tasks_defined": [...], "tasks_answered": {...}, "final_conclusion": null}' # Exemple
    conclusion_output = await pm_agent.write_conclusion(concluding_state_snapshot, raw_text_to_analyze)
    # L'orchestrateur parse conclusion_output et enregistre la conclusion (via StateManager)
    ```

### Extension

*   **Modifier les Prompts :** Adapter les fichiers dans [`prompts.py`](./prompts.py) (ou créer de nouvelles versions) pour changer la logique de définition des tâches ou de rédaction de la conclusion. Mettre à jour les références dans `pm_agent.py` si de nouvelles versions de prompts sont utilisées.
*   **Affiner les Instructions Système :** Modifier `PM_INSTRUCTIONS` dans [`pm_definitions.py`](./pm_definitions.py) pour altérer le comportement global de l'agent.
*   **Ajouter des Fonctions Sémantiques :** Pour des capacités de planification ou de synthèse plus complexes, de nouvelles fonctions sémantiques peuvent être ajoutées en suivant le modèle existant (créer un prompt, l'ajouter dans `setup_agent_components`, et créer une méthode d'invocation dans `ProjectManagerAgent`).
*   **Spécialisation par Héritage :** La classe `ProjectManagerAgent` peut servir de base pour des agents de gestion de projet plus spécialisés (par exemple, un `SherlockProjectManagerAgent`). Ces sous-classes pourraient surcharger les prompts, les instructions, ou ajouter des logiques spécifiques tout en bénéficiant de la structure existante.
    ```python
    class SherlockProjectManagerAgent(ProjectManagerAgent):
        def __init__(self, kernel: Kernel, agent_name: str = "SherlockPMAgent"):
            # Utiliser des instructions ou prompts spécifiques à Sherlock
            sherlock_pm_instructions = "Instructions spécifiques pour Sherlock PM..." 
            super().__init__(kernel, agent_name, system_prompt=sherlock_pm_instructions)

        def setup_agent_components(self, llm_service_id: str) -> None:
            super().setup_agent_components(llm_service_id)
            # Potentiellement ajouter ou remplacer des fonctions sémantiques
            # spécifiques à Sherlock.
            # self.sk_kernel.add_function(prompt=prompt_sherlock_specific_task, ...)
            pass
    ```

Ce README vise à fournir une compréhension claire du rôle et du fonctionnement du `ProjectManagerAgent` dans le cadre d'une architecture orchestrée.