# Cartographie du Système d'Analyse Rhétorique

Ce document décrit l'architecture du système d'analyse rhétorique, ses composants principaux et leurs interactions.

## 1. Vue d'ensemble

Le système d'analyse rhétorique est un ensemble de modules complexes conçus pour analyser des discours, identifier des sophismes, et évaluer la qualité de l'argumentation. Il s'articule autour d'agents spécialisés, de pipelines de traitement et d'outils d'analyse.

## 2. Composants Clés

### 2.1. `argumentation_analysis/`

Ce répertoire est le cœur du système.

- **`argumentation_analysis/agents/`**: Contient les agents intelligents qui effectuent les analyses. On y trouve :
    - Des agents de base (`core/`)
    - Des agents spécialisés pour l'extraction (`extract/`), l'analyse informelle (`informal/`), la logique (`logic/`), etc.
    - Un`jtms_communication_hub.py` qui semble gérer la communication entre les agents.

- **`argumentation_analysis/core/`**: Composants de bas niveau, gestion de l'état partagé (`shared_state.py`), et configuration de la JVM pour Tweety (`jvm_setup.py`).

- **`argumentation_analysis/tools/`**: Outils pour l'analyse, incluant la détection de sophismes (`fallacy_analyzer`), l'évaluation de la sévérité (`fallacy_severity_evaluator.py`), et la visualisation (`rhetorical_result_visualizer.py`).

- **`argumentation_analysis/orchestration/`**: Modules responsables de l'orchestration des différents agents et outils pour réaliser une analyse complète.

- **`argumentation_analysis/pipelines/`**: Pipelines de traitement de données, comme `la classe `UnifiedPipeline` du module `argumentation_analysis/pipelines/unified_pipeline.py`` et `unified_text_analysis.py`, qui semblent chaîner les opérations.

- **`argumentation_analysis/demos/`**: Scripts de démonstration.
    - `run_rhetorical_analysis_demo.py`: Point d'entrée principal pour lancer une analyse rhétorique de démonstration.

### 2.2. `scripts/`

Ce répertoire contient divers scripts pour l'exécution, les tests, et la maintenance.

- **`scripts/apps/start_api_for_rhetorical_test.py`**: Suggère la présence d'une API pour le système.
- **`scripts/demo/`**: Contient des démonstrations plus complexes et des documents associés.
- **`scripts/execution/`**: D'après le `README_rhetorical_analysis.md`, ce dossier contient une suite d'outils autonomes pour l'analyse rhétorique :
    - `decrypt_extracts.py`: Pour déchiffrer les données d'entrée.
    - `rhetorical_analysis.py`: Pour lancer l'analyse principale.
    - `rhetorical_analysis_standalone.py`: Une version avec des mocks pour les dépendances.
    - `test_rhetorical_analysis.py`: Un script de test pour cette suite d'outils.
    Ceci indique un **second workflow potentiel**, distinct de celui initié par `run_rhetorical_analysis_demo.py`.

## 3. Flux de travail confirmés

### Flux 1: Pipeline d'analyse unifié

1.  Le script `argumentation_analysis/demos/run_rhetorical_analysis_demo.py` est le point d'entrée. Il sert de lanceur avec des exemples de textes.
2.  Il appelle le script `argumentation_analysis/run_analysis.py`.
3.  `run_analysis.py` est le véritable orchestrateur qui parse les arguments et appelle la fonction `run_text_analysis_pipeline` du module `argumentation_analysis/pipelines/analysis_pipeline.py`.
4.  Ce pipeline exécute la séquence complète d'analyse. C'est le workflow principal et le plus intégré.

### Flux 2: Suite d'outils d'exécution

1.  Ce flux est basé dans `scripts/execution/`.
2.  Il nécessite de lancer `decrypt_extracts.py` d'abord pour préparer les données.
3.  Ensuite, `rhetorical_analysis.py` est lancé sur les données déchiffrées.
4.  Ce flux semble plus manuel et potentiellement utilisé pour des analyses ciblées ou du débogage.

## 4. Prochaines étapes de l'audit

- Lire le contenu des READMEs identifiés (`scripts/execution/README_rhetorical_analysis.md`, etc.).
- Comprendre le fonctionnement exact de `run_rhetorical_analysis_demo.py`.
- Exécuter le script avec des données de test.