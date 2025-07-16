# Cartographie de l'Architecture du Module `argumentation_analysis`

Ce document décrit l'architecture du module `argumentation_analysis` en se basant sur l'exploration de sa structure et l'analyse de son point d'entrée principal.

## 1. Structure des Répertoires et Composants Clés

Le module est organisé en plusieurs répertoires principaux, chacun avec un rôle distinct :

*   **`argumentation_analysis/`**: Racine du module.
    *   **`agents/`**: Contient la logique des agents autonomes, leurs outils, leurs prompts et leurs configurations. C'est le cœur "exécutant" de bas niveau.
    *   **`core/`**: Fournit les briques fondamentales et transversales : communication inter-composants (`communication/`), gestion de l'état partagé (`shared_state.py`), configuration (`config/`) et intégrations bas niveau (ex: `jvm_setup.py`).
    *   **`orchestration/`**: Le cerveau du système. Il contient la logique de coordination de haut niveau qui décide comment traiter une demande. Le fichier clé est `engine/main_orchestrator.py`.
    *   **`pipelines/`**: Définit des séquences d'analyse complexes et structurées (ex: `analysis_pipeline.py`, `reporting_pipeline.py`). Ces pipelines sont probablement invoqués par l'orchestrateur.
    *   **`services/`**: Expose les fonctionnalités du système via des services, notamment une API web (`web_api/`), permettant l'interaction avec des clients externes.
    *   **`models/`**: Définit les structures de données (schémas Pydantic) utilisées pour la communication et la représentation des informations à travers le système.
    *   **`utils/`**: Fonctions utilitaires génériques pour la manipulation de fichiers, le logging, le traitement de texte, etc.

## 2. Flux de Travail de l'Orchestrateur Principal

Le flux de travail est initié et géré par la classe `MainOrchestrator` dans `argumentation_analysis/orchestration/engine/main_orchestrator.py`.

### 2.1. Point d'Entrée

*   La méthode publique `run_analysis(text_input, ...)` est le point d'entrée unique pour toute nouvelle tâche d'analyse.

### 2.2. Sélection Dynamique de la Stratégie

*   L'orchestrateur ne suit pas un chemin unique. Il appelle d'abord la fonction `select_strategy` pour déterminer la meilleure **stratégie d'orchestration** à adopter en fonction de la configuration, du type d'analyse demandé et du contenu d'entrée.
*   Cette sélection dynamique est un concept architectural central. Les stratégies sont définies dans l'énumération `OrchestrationStrategy`.

### 2.3. Modèles Architecturaux

L'analyse de `main_orchestrator.py` révèle deux modèles architecturaux principaux qui peuvent être exécutés :

#### A. Le Modèle d'Orchestration Hiérarchique

*   **Activé par** : Stratégies comme `HIERARCHICAL_FULL`.
*   **Description** : C'est une architecture classique à trois niveaux :
    1.  **Niveau Stratégique (`StrategicManager`)** : Reçoit la demande initiale et la décompose en objectifs de haut niveau (ex: "identifier les sophismes", "évaluer la cohérence").
    2.  **Niveau Tactique (`TacticalCoordinator`)** : Prend les objectifs stratégiques et les traduit en un plan d'action détaillé, composé de tâches concrètes et ordonnancées.
    3.  **Niveau Opérationnel (`OperationalManager` et `DirectOperationalExecutor`)** : Exécute les tâches définies par le niveau tactique, en faisant probablement appel aux `agents` et aux `pipelines`.
*   **Flux** : `Demande -> Stratégique -> Tactique -> Opérationnel -> Synthèse des résultats`.

#### B. Le Modèle d'Orchestration Spécialisée (Plugin)

*   **Activé par** : Stratégie `SPECIALIZED_DIRECT`.
*   **Description** : Ce modèle court-circuite la hiérarchie pour des tâches spécifiques. Il sélectionne et exécute directement un **orchestrateur spécialisé**.
*   **Sélection** : La sélection est basée sur l' `AnalysisType` fourni dans la configuration.
*   **Exemples d'orchestrateurs spécialisés** :
    *   `CluedoExtendedOrchestrator` : Pour les analyses de type "investigation".
    *   `ConversationOrchestrator` : Pour l'analyse de débats.
    *   `RealLLMOrchestrator` : Pour une analyse rhétorique complète via un LLM.
    *   `LogiqueComplexeOrchestrator` : Pour les analyses logiques formelles.
*   **Flux** : `Demande -> Sélection du Plugin -> Exécution par l'Orchestrateur Spécialisé -> Résultat`.

### 2.4. Synthèse

À la fin de chaque flux, les résultats sont agrégés et formatés avant d'être retournés à l'appelant. Le module `reporting` est utilisé pour générer des rapports structurés.