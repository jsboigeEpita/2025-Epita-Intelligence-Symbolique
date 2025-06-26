# Plan de Conception : Synthèse pour l'Agent FOL Robuste

Ce document présente l'architecture cible pour l'agent `FOLLogicAgent`, basée sur l'analyse comparative de 18 snapshots de code. Il intègre les "patterns gagnants" identifiés pour créer une solution robuste, maintenable et performante.

## 1. Analyse et Leçons Apprises

L'évolution du code à travers les snapshots a révélé une transition claire :

*   **Abandon d'une approche "Boîte Noire" :** La tentative initiale de faire générer par le LLM une structure logique JSON complexe en une seule fois (`conv1`) a conduit à des implémentations fragiles, nécessitant des boucles de ré-essai et du code de "réparation" complexe. **Conclusion : cette approche est une impasse.**
*   **Adoption d'une approche "Tool-Calling" :** Les versions les plus performantes (`conv2`, `conv3`) ont convergé vers une architecture où le LLM appelle des "outils" Python. Cette séparation claire des responsabilités est le **pattern gagnant fondamental**. Le LLM excelle dans la compréhension sémantique du texte, tandis que le code Python garantit la cohérence et la validité de la structure logique.
*   **Affinement des Outils :** Les derniers snapshots (`conv3_snapshot7`) montrent une évolution vers des outils de plus haut niveau (`add_universal_implication` au lieu de `add_formula` avec une syntaxe complexe). Cela simplifie encore la tâche du LLM et augmente la fiabilité.
*   **Stabilité de la JVM :** La configuration de la JVM a été simplifiée pour privilégier la stabilité, avec une augmentation de la mémoire et la suppression des options de diagnostic potentiellement perturbatrices. La validation explicite du classpath avant le démarrage est une amélioration clé.
*   **Environnement de Test :** Les fixtures de test les plus efficaces utilisent un scope `module` pour la performance, et sont paramétrées pour tester systématiquement les modes avec et sans sérialisation. Le mocking doit utiliser `unittest.mock`.

## 2. Architecture Cible

L'architecture finale s'articulera autour de l'approche "Tool-Calling" et de la sérialisation systématique pour le découplage.

### 2.1 Diagramme d'Interaction

```mermaid
sequenceDiagram
    participant User
    participant FOLLogicAgent
    participant SemanticKernel as Kernel + LLM
    participant BeliefSetBuilderPlugin as Plugin
    participant TweetyBridge

    User->>FOLLogicAgent: text_to_belief_set(text)
    FOLLogicAgent->>+Kernel + LLM: invoke(prompt, tools)
    Note over Kernel + LLM: Le prompt ordonne d'utiliser les outils dans un ordre strict (sorts > prédicats > constantes > formules).
    Kernel + LLM-->>+Plugin: add_sort("personne")
    Kernel + LLM-->>+Plugin: add_predicate("EstMortel", ["personne"])
    Kernel + LLM-->>+Plugin: add_constant("socrate", "personne")
    Kernel + LLM-->>+Plugin: add_formula("EstMortel(socrate)")
    Kernel + LLM-->>-FOLLogicAgent: Appels d'outils terminés
    FOLLogicAgent->>+Plugin: build_belief_set_structure()
    Plugin->>-FOLLogicAgent: logical_structure (dict Python)
    FOLLogicAgent->>+TweetyBridge: create_and_serialize_belief_set(logical_structure)
    TweetyBridge->>-FOLLogicAgent: serialized_content (JSON)
    FOLLogicAgent->>FOLLogicAgent: Crée FirstOrderBeliefSet(content=serialized_content, java_object=None)
    FOLLogicAgent-->>-User: belief_set, "Succès"
```

### 2.2 Composants Clés

1.  **`FOLLogicAgent` :** L'orchestrateur principal. Il ne contient plus de logique de parsing complexe.
    *   **Responsabilités :**
        *   Initialiser le `SemanticKernel`.
        *   Instancier et enregistrer le `BeliefSetBuilderPlugin`.
        *   Contenir le `SYSTEM_PROMPT_FOL` qui instruit le LLM sur l'ordre d'appel des outils (`conv3_snapshot7` est la meilleure version).
        *   Appeler le Kernel avec le texte de l'utilisateur.
        *   Récupérer la structure logique construite par le plugin.
        *   Utiliser le `TweetyBridge` pour créer et **sérialiser** le BeliefSet.
        *   Toujours opérer en mode **asynchrone**.

2.  **`BeliefSetBuilderPlugin` :** Le constructeur de la base de connaissances. C'est un simple objet Python qui accumule l'état.
    *   **Responsabilités :**
        *   Fournir des méthodes décorées comme des outils au Kernel (`@kernel_function`).
        *   Exposer des outils sémantiques de haut niveau (ex: `add_universal_implication`) pour simplifier la tâche du LLM.
        *   Maintenir un état interne (listes de sorts, prédicats, etc.).
        *   Fournir une méthode (`build_belief_set_structure`) pour retourner la structure logique complète sous forme de dictionnaire Python.

3.  **`TweetyBridge` :** La passerelle vers Java.
    *   **Responsabilités :**
        *   Contenir la logique de communication avec JPype.
        *   Exposer des méthodes qui acceptent des structures de données Python simples (dictionnaires) plutôt que des objets complexes.
        *   La méthode principale sera `create_and_serialize_belief_set`. Plus besoin de `create_belief_set_from_formulas`.

4.  **`jvm_setup.py` :**
    *   Doit utiliser la configuration **simplifiée et robuste** (`conv1_snapshot8`), avec une mémoire accrue et la validation du classpath.

## 3. Plan d'Implémentation

1.  **Créer `argumentation_analysis/agents/core/logic/first_order_logic_agent.py` :**
    *   Baser l'implémentation sur `conv2_snapshot3` et `conv3_snapshot*`.
    *   Utiliser le `SYSTEM_PROMPT_FOL` de `conv3_snapshot7`.
    *   Implémenter le `BeliefSetBuilderPlugin` avec des fonctions `add_sort`, `add_constant`, `add_predicate`, `add_formula` et des outils de plus haut niveau.
    *   La méthode `text_to_belief_set` doit orchestrer le flux décrit dans le diagramme.

2.  **Modifier `argumentation_analysis/core/jvm_setup.py` :**
    *   Appliquer les changements du diff `conv1_snapshot8/jvm_setup.py.diff` pour solidifier la configuration de la JVM.

3.  **Modifier `tests/integration/workers/test_worker_fol_tweety.py` :**
    *   La fixture `fol_agent_with_kernel` doit avoir un `scope="module"`.
    *   Elle doit être paramétrée pour la sérialisation (`[True, False]`).
    *   Tous les appels aux méthodes de l'agent doivent utiliser `await`.
    *   Les mocks doivent être créés avec `unittest.mock.AsyncMock`.

4.  **Supprimer le code obsolète :**
    *   Les boucles de ré-essai, les heuristiques de correction de JSON, et les fonctions de parsing complexes dans `first_order_logic_agent.py` ne sont plus nécessaires et doivent être supprimées.