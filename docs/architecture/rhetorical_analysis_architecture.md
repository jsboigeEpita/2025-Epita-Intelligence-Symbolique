# Architecture du Système d'Analyse Rhétorique Unifié

Ce document décrit l'architecture du système d'analyse rhétorique, basée sur l'exploration de l'arborescence des fichiers.

## Vue d'Ensemble Conceptuelle

Le projet dispose de deux systèmes principaux pour l'analyse argumentative, chacun avec une philosophie distincte :

1.  **`argumentation_analysis/orchestration` :** Le "cerveau" collaboratif. Il gère des équipes d'agents intelligents qui travaillent ensemble de manière dynamique pour analyser un texte. C'est l'approche la plus moderne, flexible et puissante, conçue pour des analyses complexes et multi-facettes.
2.  **`argumentation_analysis/pipelines` :** La "chaîne de montage" séquentielle. Elle exécute des séquences d'analyse prédéfinies et linéaires. C'est une approche plus simple et statique, optimisée pour le traitement par lot.

---

## Répertoire `argumentation_analysis/`

Le répertoire racine du projet contient plusieurs modules clés, chacun ayant un rôle spécifique.

### `agents/`
*   **Description supposée :** Contient les différents agents intelligents spécialisés dans des tâches d'analyse. La structure suggère une décomposition par compétence (extraction, logique formelle, informelle).
*   `jtms_agent_base.py`: Classe de base pour les agents utilisant un JTMS (Justification-Truth Maintenance System).
*   `sherlock_jtms_agent.py`: Agent "Sherlock", probablement pour l'analyse déductive.
*   `watson_jtms_agent.py`: Agent "Watson", potentiellement pour l'analyse de données ou de langage naturel.
*   `core/`: Contient les cœurs logiques des agents, avec des spécialisations claires (logique propositionnelle, premier ordre, modale, etc.).

### `core/`
*   **Description supposée :** Le noyau central du système, gérant l'état, les services de bas niveau et l'initialisation.
*   `jvm_setup.py`: Indique une interaction avec la JVM, probablement pour utiliser des bibliothèques Java comme Tweety.
*   `llm_service.py`: Gère les interactions avec les grands modèles de langage (LLM).
*   `shared_state.py`: Gère l'état partagé entre les différents composants du système.
*   `source_manager.py`: Gère les sources de données à analyser.

### `orchestration/`
*   **Description supposée :** Gère la coordination et la collaboration entre les différents agents et services pour réaliser une analyse complète. Pour plus de détails sur l'implémentation technique, consultez la [documentation de l'`analysis_runner`](../reference/orchestration/analysis_runner.md).
*   `hierarchical/`: Suggère une architecture d'orchestration à plusieurs niveaux (Stratégique, Tactique, Opérationnel), ce qui implique une prise de décision complexe.
*   `service_manager.py`: Gère le cycle de vie et l'accès aux différents services.
*   `cluedo_extended_orchestrator.py`: Un orchestrateur spécifique pour un scénario complexe, probablement lié à une démonstration "Cluedo".
*   `main_orchestrator.py` (dans `engine/`): Semble être le point d'entrée principal de l'orchestration.

### `pipelines/`
*   **Description supposée :** Définit des séquences d'opérations standardisées pour des tâches d'analyse récurrentes.
*   `unified_pipeline.py`: Un pipeline central qui semble unifier différentes étapes d'analyse.
*   `reporting_pipeline.py`: Pipeline dédié à la génération de rapports.
*   `embedding_pipeline.py`: Pipeline pour la création de "vector embeddings" à partir du texte.

### `services/`
*   **Description supposée :** Fournit des services transverses utilisés par d'autres composants.
*   `crypto_service.py`: Service de chiffrement.
*   `jtms_service.py`: Service pour l'interaction avec le système JTMS.
*   `logic_service.py`: Service pour les opérations de logique formelle.
*   `web_api/`: Exposition des services via une API web (probablement Flask), pour une interaction externe.

### `utils/`
*   **Description supposée :** Fonctions et classes utilitaires.
*   `crypto_workflow.py`: Utilitaires pour gérer les workflows de chiffrement.
*   `taxonomy_loader.py`: Charge les taxonomies, comme celle des sophismes.
*   `visualization_generator.py`: Outils pour créer des visualisations des résultats d'analyse.

### Fichiers racines notables
*   `main_orchestrator.py`: Point d'entrée principal pour lancer l'orchestration.
*   `run_analysis.py`: Script pour exécuter une analyse.
*   `requirements.txt`: Liste des dépendances Python.
## Répertoire `scripts/`

Ce répertoire contient un ensemble de scripts pour l'exécution, la maintenance, le test et la démonstration du système.

### `scripts/pipelines/`
*   `run_rhetorical_analysis_pipeline.py`: **Description supposée :** Script principal pour lancer le pipeline d'analyse rhétorique complet.

### `scripts/reporting/`
*   `generate_rhetorical_analysis_summaries.py`: **Description supposée :** Génère des résumés à partir des résultats de l'analyse rhétorique.
*   `compare_rhetorical_agents.py`: **Description supposée :** Compare les performances ou les résultats de différents agents d'analyse.

### `scripts/apps/`
*   `start_api_for_rhetorical_test.py`: **Description supposée :** Démarre une API web spécifiquement pour tester l'analyse rhétorique.

### `scripts/demo/`
*   `DEMO_RHETORICAL_ANALYSIS.md`: **Description supposée :** Document de présentation de la démonstration d'analyse rhétorique.

### `scripts/execution/`
*   `README_rhetorical_analysis.md`: **Description supposée :** Instructions sur la manière d'exécuter les scripts liés à l'analyse rhétorique.


## Répertoire `argumentation_analysis/demos/`

Ce répertoire contient des scripts de démonstration pour illustrer les fonctionnalités du système d'analyse d'argumentation.

### `argumentation_analysis/demos/jtms_demo_complete.py`
*   **Description supposée :** Une démonstration complète utilisant le JTMS (Justification-Truth Maintenance System) pour l'analyse d'arguments.

### `argumentation_analysis/demos/run_rhetorical_analysis_demo.py`
*   **Description supposée :** Un script pour exécuter une démonstration spécifique à l'analyse rhétorique.

### `argumentation_analysis/demos/sample_epita_discourse.txt`
*   **Description supposée :** Un échantillon de texte de discours, probablement utilisé comme donnée d'entrée pour les démonstrations.

## Contexte et Évolution

Pour comprendre l'historique et les décisions qui ont mené à l'architecture actuelle, les documents suivants peuvent être consultés :

*   **Plan de Nettoyage :** [`../refactoring/03_argumentation_analysis_cleanup_plan.md`](../refactoring/03_argumentation_analysis_cleanup_plan.md)
*   **Rapport de Robustesse :** [`../reports_pass_2/rhetorical_analysis/hardening_report.md`](../reports_pass_2/rhetorical_analysis/hardening_report.md)