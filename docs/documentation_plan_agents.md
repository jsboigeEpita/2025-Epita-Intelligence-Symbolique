# Plan de Mise à Jour de la Documentation pour `argumentation_analysis/agents/`

Ce document détaille le plan de mise à jour de la documentation interne (docstrings, commentaires) pour le paquet `argumentation_analysis/agents/`. L'objectif est d'améliorer la clarté, la lisibilité et la maintenabilité du code.

## 1. Analyse de l'Arborescence

Le paquet `agents` est structuré autour de trois concepts principaux :
- **`core/`** : Contient la logique fondamentale et les définitions des différents types d'agents. C'est le cœur du système.
- **`tools/`** : Fournit des fonctionnalités spécialisées utilisées par les agents, comme l'analyse de sophismes.
- **`runners/`** : Contient des scripts pour exécuter et tester les agents et les systèmes d'agents.

## 2. Plan de Documentation par Priorité

### Priorité 1 : Le Cœur des Agents (`core/`)

La documentation du `core` est la plus critique car elle définit les contrats et les comportements de base de tous les agents.

#### 2.1. Classes de Base Abstraites (`core/abc/`)
- **Fichier :** [`argumentation_analysis/agents/core/abc/agent_bases.py`](argumentation_analysis/agents/core/abc/agent_bases.py)
- **Objectif :** Définir les interfaces et les classes de base pour tous les agents.
- **Actions :**
    - **Docstring de module :** Expliquer le rôle des classes de base abstraites dans l'architecture des agents.
    - **`BaseAgent` (classe) :** Documenter en détail la classe, ses attributs et le contrat qu'elle impose.
    - **`BaseLogicAgent` (classe) :** Documenter son rôle spécifique pour les agents basés sur la logique.
    - **Méthodes abstraites :** Documenter chaque méthode (`execute`, `prepare_input`, etc.) en expliquant son rôle, ses paramètres attendus et ce que les implémentations doivent retourner.

#### 2.2. Agents de Logique Formelle (`core/logic/`)
- **Fichiers clés :**
    - [`argumentation_analysis/agents/core/logic/first_order_logic_agent.py`](argumentation_analysis/agents/core/logic/first_order_logic_agent.py)
    - [`argumentation_analysis/agents/core/logic/propositional_logic_agent.py`](argumentation_analysis/agents/core/logic/propositional_logic_agent.py)
    - [`argumentation_analysis/agents/core/logic/tweety_bridge.py`](argumentation_analysis/agents/core/logic/tweety_bridge.py)
- **Objectif :** Implémenter des agents capables de raisonnement en logique formelle.
- **Actions :**
    - **Docstrings de module :** Expliquer le rôle de chaque module (ex: gestion de la logique propositionnelle).
    - **Classes d'agent (`FirstOrderLogicAgent`, `PropositionalLogicAgent`) :** Documenter leur spécialisation, leur initialisation et leurs méthodes principales.
    - **`TweetyBridge` (classe) :** Documenter en détail l'interaction avec la bibliothèque Tweety, les méthodes de conversion et d'appel.

#### 2.3. Agents de Logique Informelle (`core/informal/`)
- **Fichiers clés :**
    - [`argumentation_analysis/agents/core/informal/informal_agent.py`](argumentation_analysis/agents/core/informal/informal_agent.py)
    - [`argumentation_analysis/agents/core/informal/taxonomy_sophism_detector.py`](argumentation_analysis/agents/core/informal/taxonomy_sophism_detector.py)
- **Objectif :** Analyser des arguments en langage naturel pour détecter des sophismes.
- **Actions :**
    - **`InformalAgent` (classe) :** Documenter son fonctionnement, l'utilisation des LLMs et les prompts associés (référencés dans `prompts.py`).
    - **`TaxonomySophismDetector` (classe) :** Expliquer comment la taxonomie est utilisée pour la détection. Documenter les méthodes d'analyse.
    - **`prompts.py` et `informal_definitions.py` :** Ajouter des commentaires pour expliquer les différentes définitions et les structures des prompts.

#### 2.4. Autres modules `core`
- **`core/extract/`**: Documenter `ExtractAgent` pour clarifier son rôle dans l'extraction d'arguments.
- **`core/synthesis/`**: Documenter `SynthesisAgent` et les `data_models` pour expliquer comment les résultats de différents agents sont consolidés.
- **`core/oracle/`**: Documenter les agents gérant l'accès aux données (ex: `MoriartyInterrogatorAgent`) et les mécanismes de permission.

### Priorité 2 : Les Outils (`tools/`)

Les outils sont des composants réutilisables. Leur documentation doit être claire et inclure des exemples.

#### 2.1. Outils d'Analyse (`tools/analysis/`)
- **Fichiers clés :**
    - `complex_fallacy_analyzer.py`
    - `rhetorical_result_analyzer.py`
    - `rhetorical_result_visualizer.py`
    (Et leurs équivalents dans les sous-dossiers `enhanced/` et `new/`)
- **Objectif :** Fournir des capacités d'analyse approfondie des arguments et des sophismes.
- **Actions :**
    - **Docstrings de module :** Pour chaque analyseur, expliquer la technique utilisée.
    - **Classes d'analyseur :** Documenter les méthodes publiques, leurs entrées (ex: un objet résultat d'analyse) et leurs sorties (ex: un rapport, une visualisation).
    - **`README.md` :** Mettre à jour les README pour refléter les capacités actuelles et guider les développeurs vers le bon outil.

### Priorité 3 : Les Exécuteurs (`runners/`)

Les `runners` sont les points d'entrée pour utiliser les agents. La documentation doit être orientée utilisateur.

- **Fichiers clés :**
    - [`argumentation_analysis/agents/runners/run_complete_test_and_analysis.py`](argumentation_analysis/agents/runners/run_complete_test_and_analysis.py)
    - [`argumentation_analysis/agents/runners/test/orchestration/test_orchestration_complete.py`](argumentation_analysis/agents/runners/test/orchestration/test_orchestration_complete.py)
- **Objectif :** Démontrer et tester l'intégration et l'orchestration des agents.
- **Actions :**
    - **Docstrings de module :** Expliquer ce que le script exécute, quel est le scénario testé, et quelles sont les sorties attendues (logs, rapports, etc.).
    - **Fonctions principales (`main`, `run_test`, etc.) :** Ajouter des commentaires pour décrire les étapes clés du script (configuration, exécution de l'agent, analyse des résultats).
    - **Arguments de la ligne de commande :** Si applicable, documenter les arguments attendus par le script.

## 3. Création du Fichier de Plan

Ce plan sera sauvegardé dans le fichier [`docs/documentation_plan_agents.md`](docs/documentation_plan_agents.md) pour servir de guide à l'agent en charge de la rédaction de la documentation.