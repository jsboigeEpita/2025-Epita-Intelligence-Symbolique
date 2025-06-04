# Orchestration Simple avec `AgentGroupChat`

Ce document décrit le mécanisme d'orchestration simple utilisé dans ce projet, principalement mis en œuvre dans [`analysis_runner.py`](./analysis_runner.py:0). Il s'appuie sur la fonctionnalité `AgentGroupChat` de la bibliothèque Semantic Kernel.

## Vue d'ensemble

L'orchestration repose sur une conversation de groupe (`AgentGroupChat`) où plusieurs agents collaborent pour analyser un texte. La coordination se fait indirectement via un état partagé (`RhetoricalAnalysisState`) et des stratégies de sélection et de terminaison.

## Composants Clés

1.  **`run_analysis_conversation(texte_a_analyser, llm_service)` ([`analysis_runner.py`](./analysis_runner.py:66))** :
    *   C'est la fonction principale qui initialise et exécute la conversation d'analyse.
    *   Elle est également accessible via `AnalysisRunner().run_analysis_async(...)`.

2.  **Kernel Semantic Kernel (`local_kernel`)** :
    *   Une instance locale du kernel SK est créée pour chaque exécution.
    *   Le service LLM (ex: OpenAI, Azure) y est ajouté.
    *   Le `StateManagerPlugin` y est également ajouté, permettant aux agents d'interagir avec l'état partagé.

3.  **État Partagé (`RhetoricalAnalysisState`)** :
    *   Une instance de [`RhetoricalAnalysisState`](../core/shared_state.py:0) est créée pour chaque analyse.
    *   Elle contient des informations telles que le texte initial, les tâches définies, les tâches répondues, les arguments identifiés, la conclusion finale, et surtout, `next_agent_to_act` pour la désignation explicite.

4.  **`StateManagerPlugin` ([`../core/state_manager_plugin.py`](../core/state_manager_plugin.py:0))** :
    *   Ce plugin est ajouté au kernel local.
    *   Il expose des fonctions natives (ex: `get_current_state_snapshot`, `add_analysis_task`, `designate_next_agent`, `set_final_conclusion`) que les agents peuvent appeler via leurs fonctions sémantiques pour lire et modifier l'état partagé.

5.  **Agents (`ChatCompletionAgent`)** :
    *   Les agents principaux du système (ex: `ProjectManagerAgent`, `InformalAnalysisAgent`, `PropositionalLogicAgent`, `ExtractAgent`) sont d'abord instanciés comme des classes Python normales (héritant de `BaseAgent`). Leurs fonctions sémantiques spécifiques sont configurées dans leur kernel interne via leur méthode `setup_agent_components`.
    *   Ensuite, pour l'interaction au sein du `AgentGroupChat`, ces agents sont "enveloppés" dans des instances de `ChatCompletionAgent` de Semantic Kernel.
    *   Ces `ChatCompletionAgent` sont initialisés avec :
        *   Le kernel local (qui contient le `StateManagerPlugin`).
        *   Le service LLM.
        *   Les instructions système (provenant de l'instance de l'agent Python correspondant, ex: `pm_agent_refactored.system_prompt`).
        *   Des `KernelArguments` configurés avec `FunctionChoiceBehavior.Auto` pour permettre l'appel automatique des fonctions du `StateManagerPlugin` (et d'autres fonctions sémantiques enregistrées dans le kernel).

6.  **`AgentGroupChat`** :
    *   Une instance de `AgentGroupChat` est créée avec :
        *   La liste des `ChatCompletionAgent`.
        *   Une stratégie de sélection (`SelectionStrategy`).
        *   Une stratégie de terminaison (`TerminationStrategy`).

7.  **Stratégie de Sélection (`BalancedParticipationStrategy`)** :
    *   Définie dans [`../core/strategies.py`](../core/strategies.py:191).
    *   **Priorité à la désignation explicite** : Elle vérifie d'abord si `state.consume_next_agent_designation()` retourne un nom d'agent. Si oui, cet agent est sélectionné. C'est le mécanisme principal par lequel le `ProjectManagerAgent` (ou un autre agent) peut diriger le flux de la conversation.
    *   **Équilibrage** : Si aucune désignation explicite n'est faite, la stratégie calcule des scores de priorité pour chaque agent afin d'équilibrer leur participation. Les scores prennent en compte :
        *   L'écart par rapport à un taux de participation cible.
        *   Le temps écoulé depuis la dernière sélection de l'agent.
        *   Un "budget de déséquilibre" accumulé si un agent a été sur-sollicité par des désignations explicites.
    *   L'agent avec le score le plus élevé est sélectionné.

8.  **Stratégie de Terminaison (`SimpleTerminationStrategy`)** :
    *   Définie dans [`../core/strategies.py`](../core/strategies.py:27).
    *   La conversation se termine si :
        *   `state.final_conclusion` n'est plus `None` (c'est-à-dire qu'un agent, typiquement le `ProjectManagerAgent` via `StateManager.set_final_conclusion`, a marqué l'analyse comme terminée).
        *   Un nombre maximum de tours (`max_steps`, par défaut 15) est atteint.

## Flux d'une Conversation Simple

1.  **Initialisation** :
    *   `run_analysis_conversation` est appelée avec le texte à analyser et le service LLM.
    *   Le kernel, l'état, le `StateManagerPlugin`, les agents, et le `AgentGroupChat` (avec ses stratégies) sont initialisés comme décrit ci-dessus.

2.  **Premier Tour** :
    *   Un message initial est envoyé au `AgentGroupChat`, demandant généralement au `ProjectManagerAgent` de commencer l'analyse.
    *   Exemple : `"Bonjour à tous. Le texte à analyser est : ... ProjectManagerAgent, merci de définir les premières tâches d'analyse..."` ([`analysis_runner.py:214`](./analysis_runner.py:214)).
    *   La `BalancedParticipationStrategy`, en l'absence de désignation et d'historique, sélectionnera probablement l'agent par défaut (souvent le `ProjectManagerAgent`).

3.  **Tours Suivants (Boucle `AgentGroupChat.invoke()`)** :
    *   L'agent sélectionné (ex: `ProjectManagerAgent`) reçoit l'historique de la conversation.
    *   Son LLM, guidé par ses instructions système et le prompt implicite du `AgentGroupChat`, génère une réponse.
    *   **Interaction avec l'état** : Si l'agent doit interagir avec l'état (ex: le PM veut définir une tâche), sa réponse inclura un appel à une fonction du `StateManagerPlugin` (ex: `StateManager.add_analysis_task` et `StateManager.designate_next_agent`). Grâce à `FunctionChoiceBehavior.Auto`, cet appel de fonction est exécuté automatiquement par le kernel.
        *   Par exemple, le `ProjectManagerAgent`, via sa fonction sémantique `DefineTasksAndDelegate`, pourrait générer un appel à `StateManager.add_analysis_task({"task_description": "Identifier les arguments principaux"})` et `StateManager.designate_next_agent({"agent_name": "ExtractAgent"})`.
    *   Le `StateManagerPlugin` met à jour l'instance de `RhetoricalAnalysisState`.
    *   La `BalancedParticipationStrategy` est appelée pour le tour suivant. Elle lira `state.consume_next_agent_designation()` et sélectionnera `ExtractAgent`.
    *   L'`ExtractAgent` exécute sa tâche (potentiellement en appelant d'autres fonctions sémantiques ou des fonctions du `StateManager` pour lire des informations ou enregistrer ses résultats).
    *   Le cycle continue. Les agents peuvent se répondre, mais la coordination principale passe par les désignations explicites via l'état.

4.  **Terminaison** :
    *   La boucle continue jusqu'à ce que la `SimpleTerminationStrategy` décide d'arrêter la conversation (conclusion définie ou `max_steps` atteint).
    *   Par exemple, lorsque le `ProjectManagerAgent` estime que l'analyse est complète, il appelle (via sa fonction sémantique `WriteAndSetConclusion`) la fonction `StateManager.set_final_conclusion("Voici la conclusion...")`. Au tour suivant, la `SimpleTerminationStrategy` détectera que `state.final_conclusion` n'est plus `None` et arrêtera la conversation.

## Configuration pour une Démo Simple

Pour une démo simple impliquant, par exemple, le `ProjectManagerAgent` et l'`ExtractAgent` :

1.  Assurez-vous que ces deux agents sont inclus dans la liste `agent_list_local` passée au `AgentGroupChat` dans [`analysis_runner.py`](./analysis_runner.py:187).
2.  Le `ProjectManagerAgent` doit être configuré (via ses prompts et instructions) pour :
    *   Définir une tâche d'extraction.
    *   Désigner l'`ExtractAgent` pour cette tâche en utilisant `StateManager.designate_next_agent({"agent_name": "ExtractAgent"})`.
3.  L'`ExtractAgent` doit être configuré pour :
    *   Effectuer l'extraction.
    *   Enregistrer ses résultats (par exemple, via `StateManager.add_task_answer`).
    *   Potentiellement, désigner le `ProjectManagerAgent` pour la suite en utilisant `StateManager.designate_next_agent({"agent_name": "ProjectManagerAgent"})`.
4.  Le `ProjectManagerAgent` reprendrait la main, constaterait que la tâche est faite, et pourrait soit définir une nouvelle tâche, soit (si c'est la seule étape de la démo) rédiger une conclusion et appeler `StateManager.set_final_conclusion`.

Ce mécanisme, bien que simple dans sa structure de `GroupChat`, permet une orchestration flexible grâce à la combinaison de la désignation explicite d'agents et des capacités de raisonnement des LLM au sein de chaque agent.