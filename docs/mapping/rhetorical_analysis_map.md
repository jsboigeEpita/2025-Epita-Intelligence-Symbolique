# Cartographie du Système d'Analyse Rhétorique

Ce document décrit l'architecture, les composants clés et leurs interactions au sein du système d'analyse rhétorique situé dans le répertoire `argumentation_analysis`.

## Vue d'ensemble de l'architecture

Le système est organisé autour d'une architecture modulaire composée de plusieurs packages principaux :

- **`agents`**: Définit les agents autonomes responsables de tâches d'analyse spécifiques.
- **`core`**: Fournit les fonctionnalités de base comme la gestion de la JVM, la gestion d'état et la communication inter-agents.
- **`orchestration`**: Coordonne les agents et les outils pour exécuter des pipelines d'analyse complexes.
- **`tools`**: Contient des outils spécialisés pour l'analyse rhétorique, la détection de sophismes, etc.
- **`demos`**: Présente des scripts d'exemple qui illustrent comment utiliser le système.
- **`utils`**: Regroupe des fonctions et classes utilitaires transverses.

## Description des Composants

### 1. `argumentation_analysis/core`

Le cœur du système.

- **`jvm_setup.py`**: Gère le cycle de vie de la machine virtuelle Java (JVM), essentielle pour l'intégration avec des bibliothèques Java comme Tweety.
- **`shared_state.py`**: Gère l'état partagé entre les différents composants du système.
- **`communication/`**: Implémente le système de communication inter-agents (canaux, messages, etc.).

### 2. `argumentation_analysis/agents`

Ce répertoire contient les différentes familles d'agents. Chaque agent est spécialisé dans un type d'analyse.

- **`core/abc/agent_bases.py`**: Définit les classes de base abstraites pour tous les agents.
- **`core/informal/`**: Agents pour l'analyse de la logique informelle et la détection de sophismes.
- **`core/logic/`**: Agents capables de raisonnement en logique formelle (propositionnelle, premier ordre) via l'intégration avec Tweety.
- **`core/pm/`**: Agents pour l'analyse dialectique (par exemple, l'agent "Sherlock").
- **`core/extract/`**: Agents spécialisés dans l'extraction d'arguments depuis un texte.

### 3. `argumentation_analysis/tools`

Collection d'outils utilisés par les agents ou l'orchestrateur pour des tâches d'analyse fine.

- **`analysis/`**: Outils pour analyser la cohérence, la structure des arguments, et les sophismes. `rhetorical_result_analyzer.py` et `rhetorical_result_visualizer.py` sont des composants clés.

### 4. `argumentation_analysis/orchestration`

Ce package est responsable de la coordination des agents pour réaliser une analyse complète.

- **`analysis_runner.py`** et **`enhanced_pm_analysis_runner.py`**: Classes principales qui exécutent les pipelines d'analyse. Elles configurent l'environnement, instancient les agents et gèrent le flux de données.
- **`hierarchical/`**: Implémente une architecture d'orchestration hiérarchique (stratégique, tactique, opérationnel).

### 5. `argumentation_analysis/demos`

- **`run_rhetorical_analysis_demo.py`**: Le script de démonstration central pour le système d'analyse rhétorique. Il met en œuvre plusieurs scénarios de test pour valider le pipeline d'analyse.

## Interactions et Flux de Données

1.  Un script de haut niveau (comme `run_rhetorical_analysis_demo.py`) initialise un `AnalysisRunner`.
2.  Le `AnalysisRunner` charge la configuration, met en place les services nécessaires (comme la JVM via `jvm_setup`), et instancie les agents requis.
3.  Le texte à analyser est passé au premier agent du pipeline (souvent un `ExtractAgent`).
4.  Les agents communiquent et transmettent leurs résultats via les canaux de communication définis dans `core/communication`.
5.  Les outils d'analyse (`tools/`) sont invoqués par les agents pour affiner les résultats.
6.  L'orchestrateur `AnalysisRunner` collecte les résultats finaux et génère un rapport.

Ce flux permet de chaîner des analyses complexes, où le résultat d'un agent sert d'entrée pour le suivant.