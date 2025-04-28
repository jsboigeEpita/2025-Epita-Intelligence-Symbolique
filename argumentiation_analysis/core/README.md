# 🧱 Noyau Applicatif (`core/`)

Ce répertoire contient les classes et fonctions fondamentales partagées par l'ensemble de l'application d'analyse rhétorique. Il assure la gestion de l'état, l'interaction avec les services externes (LLM, JVM) et définit les règles d'orchestration.

[Retour au README Principal](../README.md)

## Contenu

* **[`shared_state.py`](./shared_state.py)** : Définit la classe `RhetoricalAnalysisState`.
    * Représente l'état mutable de l'analyse (texte brut, tâches assignées, arguments identifiés, sophismes trouvés, belief sets logiques, logs de requêtes, réponses des agents, conclusion finale, prochain agent désigné).
    * Inclut des méthodes pour ajouter/modifier ces éléments et pour sérialiser/désérialiser l'état (JSON).
    * Possède un logging interne pour tracer les modifications.

* **[`state_manager_plugin.py`](./state_manager_plugin.py)** : Définit la classe `StateManagerPlugin`.
    * Un plugin Semantic Kernel qui encapsule une instance de `RhetoricalAnalysisState`.
    * Expose des fonctions natives (`@kernel_function`) aux agents pour lire (`get_current_state_snapshot`) et écrire (`add_task`, `add_argument`, `add_fallacy`, `add_belief_set`, `log_query_result`, `add_answer`, `set_final_conclusion`, `designate_next_agent`) dans l'état partagé de manière contrôlée et traçable.

* **[`strategies.py`](./strategies.py)** : Définit les stratégies d'orchestration pour `AgentGroupChat` de Semantic Kernel.
    * `SimpleTerminationStrategy` 🚦 : Arrête la conversation si `final_conclusion` est présente dans l'état ou si un nombre maximum de tours (`max_steps`) est atteint.
    * `DelegatingSelectionStrategy` 🔀 : Choisit le prochain agent. Priorise la désignation explicite (`_next_agent_designated` dans l'état). Sinon, retourne par défaut au `ProjectManagerAgent` après l'intervention d'un autre agent.

* **[`jvm_setup.py`](./jvm_setup.py)** : Gère l'interaction avec l'environnement Java. 🔥☕
    * Contient la logique (`initialize_jvm`) pour :
        * Vérifier/télécharger les JARs Tweety requis et leurs binaires natifs dans `libs/`.
        * Trouver un JDK valide (via `JAVA_HOME` ou détection automatique).
        * Démarrer la JVM via JPype avec le classpath et `java.library.path` corrects.
    * Retourne un statut indiquant si la JVM est prête, essentiel pour l'agent `PropositionalLogicAgent`.

* **[`llm_service.py`](./llm_service.py)** : Gère la création du service LLM. ☁️
    * Contient la logique (`create_llm_service`) pour lire la configuration LLM depuis `.env` (OpenAI ou Azure).
    * Crée et retourne l'instance du service (`OpenAIChatCompletion` ou `AzureChatCompletion`) qui sera injectée dans le kernel et utilisée par les `ChatCompletionAgent`.