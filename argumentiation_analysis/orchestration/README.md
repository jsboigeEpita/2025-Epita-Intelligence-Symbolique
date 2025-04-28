# Orchestration (`orchestration/`)

Ce répertoire contient la logique principale qui orchestre la conversation collaborative entre les différents agents IA.

## Contenu

* **`analysis_runner.py`**: Définit la fonction asynchrone principale `run_analysis_conversation(texte_a_analyser, llm_service)`.
    * **Isolation :** Crée à chaque appel des instances *locales* et *neuves* de l'état (`RhetoricalAnalysisState`), du `StateManagerPlugin`, du `Kernel` Semantic Kernel, de tous les agents définis (`ChatCompletionAgent`), et des stratégies d'orchestration (`SimpleTerminationStrategy`, `DelegatingSelectionStrategy`).
    * **Configuration :** Initialise le kernel local avec le service LLM fourni et le `StateManagerPlugin` local. Appelle les fonctions `setup_*_kernel` de chaque agent pour enregistrer leurs plugins et fonctions spécifiques sur ce kernel local.
    * **Exécution :** Crée une instance `AgentGroupChat` en lui passant les agents et les stratégies locales. Lance la conversation via `local_group_chat.invoke()` et gère la boucle d'échanges de messages.
    * **Suivi & Résultat :** Logue et affiche les tours de conversation, y compris les appels d'outils. Affiche l'historique complet et l'état final de l'analyse (`RhetoricalAnalysisState` sérialisé en JSON) à la fin de la conversation.

Cette fonction est le cœur de l'exécution de l'analyse et est conçue pour être appelée par le notebook principal (`main_orchestrator.ipynb`).