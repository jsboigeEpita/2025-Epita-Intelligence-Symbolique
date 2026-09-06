# Cartographie de l'Architecture du Module `argumentation_analysis`

Ce document décrit l'architecture du module `argumentation_analysis` en se basant sur l'exploration de sa structure et l'analyse de son point d'entrée principal.

## 1. Structure des Répertoires et Composants Clés

Le module est organisé en plusieurs répertoires principaux, chacun avec un rôle distinct :

*   **`argumentation_analysis/`**: Racine du module.
    *   **`agents/`**: Contient la logique des agents autonomes, leurs outils, leurs prompts et leurs configurations. C'est le cœur "exécutant" de bas niveau.
    *   **`core/`**: Fournit les briques fondamentales et transversales : communication inter-composants (`communication/`), gestion de l'état partagé (`shared_state.py`), configuration (`config/`) et intégrations bas niveau (ex: `jvm_setup.py`).
    *   **`orchestration/`**: Le cerveau du système. Il contient la logique de coordination de haut niveau qui décide comment traiter une demande : le pipeline unifié (`unified_pipeline.py`), le DSL déclaratif de workflows (`workflow_dsl.py`), le routeur (`router.py`), le registre de capacités (`registry_setup.py`) et le mode hiérarchique (`hierarchical/`).
    *   **`pipelines/`**: Définit des séquences d'analyse complexes et structurées (ex: `analysis_pipeline.py`, `reporting_pipeline.py`). Ces pipelines sont probablement invoqués par l'orchestrateur.
    *   **`services/`**: Expose les fonctionnalités du système via des services, notamment une API web (`web_api/`), permettant l'interaction avec des clients externes.
    *   **`models/`**: Définit les structures de données (schémas Pydantic) utilisées pour la communication et la représentation des informations à travers le système.
    *   **`utils/`**: Fonctions utilitaires génériques pour la manipulation de fichiers, le logging, le traitement de texte, etc.

## 2. Flux de Travail de l'Orchestration

Le flux de travail est initié par l'entrée CLI `argumentation_analysis/run_orchestration.py` (`--mode pipeline|conversational|hierarchical|cluedo`, `--workflow light|standard|full|collaborative`) ou par l'API REST `api/main.py`. L'exécution est portée par le pipeline unifié (`orchestration/unified_pipeline.py`), dont le moteur d'exécution des phases est `pipelines/orchestration/execution/engine.py` (`analyze_text_orchestrated`).

### 2.1. Point d'Entrée

*   `run_orchestration.py --text "…" --workflow <nom>` est le point d'entrée CLI pour toute nouvelle tâche d'analyse ; l'API FastAPI `api/main.py` en est l'entrée programmatique.

### 2.2. Sélection du Workflow

*   L'orchestration ne suit pas un chemin unique : le workflow est choisi à l'entrée selon la profondeur d'analyse demandée, et le routeur (`orchestration/router.py`) aiguille chaque phase vers les capacités enregistrées dans le registre.

### 2.3. Modèles Architecturaux

Deux modèles architecturaux principaux peuvent être exécutés :

#### A. Le Modèle d'Orchestration Hiérarchique

*   **Activé par** : `--mode hierarchical` (variantes `--hierarchical-mode bridge|delegation`).
*   **Description** : C'est une architecture classique à trois niveaux :
    1.  **Niveau Stratégique (`StrategicManager`)** : Reçoit la demande initiale et la décompose en objectifs de haut niveau (ex: "identifier les sophismes", "évaluer la cohérence").
    2.  **Niveau Tactique (`TacticalCoordinator`)** : Prend les objectifs stratégiques et les traduit en un plan d'action détaillé, composé de tâches concrètes et ordonnancées.
    3.  **Niveau Opérationnel (`OperationalManager` et `DirectOperationalExecutor`)** : Exécute les tâches définies par le niveau tactique, en faisant probablement appel aux `agents` et aux `pipelines`.
*   **Flux** : `Demande -> Stratégique -> Tactique -> Opérationnel -> Synthèse des résultats`.

#### B. Le Modèle d'Orchestration Spécialisée (Plugin)

*   **Description** : Ce modèle court-circuite la hiérarchie pour des tâches spécifiques. Il sélectionne et exécute directement un **orchestrateur spécialisé**.
*   **Sélection** : La sélection est basée sur le type d'analyse demandé dans la configuration.
*   **Exemples d'orchestrateurs spécialisés** :
    *   `CluedoExtendedOrchestrator` : Pour les analyses de type "investigation".
    *   `ConversationOrchestrator` : Pour l'analyse de débats.
*   **Flux** : `Demande -> Sélection du Plugin -> Exécution par l'Orchestrateur Spécialisé -> Résultat`.

### 2.4. Synthèse

À la fin de chaque flux, les résultats sont agrégés et formatés avant d'être retournés à l'appelant. Le module `reporting` est utilisé pour générer des rapports structurés.