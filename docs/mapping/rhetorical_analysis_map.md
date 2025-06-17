# Cartographie du Système d'Analyse Rhétorique Unifié

Ce document décrit l'architecture, les composants clés et les interactions du système d'analyse rhétorique.

## 1. Vue d'Ensemble de l'Architecture

Le système est conçu autour d'une architecture modulaire et hiérarchique, principalement localisée dans le répertoire `argumentation_analysis/`. Il combine plusieurs types d'agents (logiques, informels, de synthèse) coordonnés par un système d'orchestration multi-niveaux.

L'objectif est d'analyser un texte de discours pour en extraire la structure argumentative, identifier les sophismes et autres figures rhétoriques, et évaluer la cohérence et la qualité de l'argumentation.

## 2. Composants Principaux

### 2.1. `argumentation_analysis/` - Coeur du Système

- **`agents/`**: Contient les différents types d'agents intelligents qui effectuent les tâches d'analyse.
    - `core/`: Classes de base et abstractions pour les agents.
    - `extract/`: Agents responsables de l'extraction d'informations brutes du texte.
    - `informal/`: Agents spécialisés dans l'analyse informelle, notamment la détection de sophismes.
    - `logic/`: Agents basés sur la logique formelle (propositionnelle, premier ordre, modale) pour l'analyse structurelle, s'appuyant sur Tweety.
    - `synthesis/`: Agents qui agrègent et synthétisent les résultats des autres agents.
    - `pm/`: Agents de type "Project Manager" (e.g., Sherlock) pour l'orchestration de haut niveau.

- **`tools/`**: Outils spécialisés utilisés par les agents pour des analyses spécifiques.
    - `analysis/`: Analyseurs de sophismes (complexes, contextuels), évaluateurs de sévérité, et analyseurs de résultats rhétoriques.
    - `new/`: Nouveaux outils comme l'évaluateur de cohérence d'argument et le visualiseur de structure.

- **`orchestration/`**: Gère la collaboration et le flux de travail entre les agents.
    - `hierarchical/`: Implémente une structure de commandement à plusieurs niveaux (Stratégique, Tactique, Opérationnel).
    - `engine/`: Le moteur d'orchestration principal (`main_orchestrator.py`).
    - `service_manager.py`: Gère le cycle de vie et l'accès aux services.
    - `analysis_runner.py`: Un runner de haut niveau pour exécuter des analyses complètes.

- **`core/`**: Composants fondamentaux et partagés.
    - `jvm_setup.py`: Gestion de la JVM pour l'intégration Java (Tweety).
    - `llm_service.py`: Service pour interagir avec les grands modèles de langage.
    - `shared_state.py`: État partagé entre les différents composants du système.

- **`demos/`**: Scripts de démonstration pour illustrer l'utilisation du système.
    - `run_rhetorical_analysis_demo.py`: Point d'entrée pour la démo d'analyse rhétorique.
    - `jtms_demo_complete.py`: Démonstration spécifique au système JTMS (Justification-Truth-Maintenance-System).

### 2.2. `scripts/` - Scripts Utilitaires et d'Exécution

Ce répertoire contient des scripts de support pour diverses tâches :
- `execution/`: Scripts pour lancer des analyses. Le `README_rhetorical_analysis.md` fournit des instructions.
- `maintenance/`: Scripts pour le nettoyage, la refactorisation, et la mise à jour du projet.
- `validation/`: Scripts pour valider la fonctionnalité et l'intégrité du système.

## 3. Flux de Travail d'une Analyse

1.  **Point d'Entrée**: Une analyse est généralement initiée via un script de haut niveau comme [`argumentation_analysis/demos/run_rhetorical_analysis_demo.py`](argumentation_analysis/demos/run_rhetorical_analysis_demo.py:0) ou un pipeline défini dans `pipelines/`.
2.  **Orchestration**: L'orchestrateur principal (e.g. `MainOrchestrator`) prend le contrôle. Il configure l'environnement, initialise les agents et les services nécessaires.
3.  **Coordination Hiérarchique**:
    - Le **Manager Stratégique** définit les objectifs globaux de l'analyse.
    - Le **Coordinateur Tactique** décompose les objectifs en tâches et les assigne aux managers opérationnels.
    - Le **Manager Opérationnel** fait appel aux agents spécialisés (extraction, analyse informelle, logique) pour exécuter les tâches.
4.  **Exécution par les Agents**: Chaque agent utilise ses outils (`tools/`) pour analyser le texte.
5.  **Synthèse**: L'agent de synthèse collecte les résultats intermédiaires, les agrège et produit un rapport final.
6.  **Rapport**: Le résultat final est formaté et présenté, potentiellement avec des visualisations.