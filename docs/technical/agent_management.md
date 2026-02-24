# Gestion des Agents

## 1. Introduction

Ce document décrit les mécanismes de gestion des agents au sein du système d'analyse rhétorique. Il couvre la création, la configuration, l'enregistrement, le cycle de vie, et la gestion des dépendances des agents spécialistes et des outils d'analyse. La bonne compréhension de ces mécanismes est essentielle pour étendre le système avec de nouveaux agents ou modifier le comportement des agents existants.

## 2. Principes de Conception

*   **Philosophie générale :** (Ex: agents comme services configurables, intégration flexible dans les orchestrations).
*   **Interaction avec les systèmes d'orchestration :**
    *   Rôle dans l'orchestration simple via `AgentGroupChat` (voir [`synthese_collaboration.md#11-orchestration-simple-via-agentgroupchat`](./synthese_collaboration.md#11-orchestration-simple-via-agentgroupchat)).
    *   Rôle dans l'architecture hiérarchique (voir [`synthese_collaboration.md#12-architecture-hierarchique-dorchestration`](./synthese_collaboration.md#12-architecture-hierarchique-dorchestration)).

## 3. Création et Instanciation des Agents

*   **Bases communes :**
    *   Héritage de `BaseAnalysisAgent` ([`../../argumentation_analysis/agents/core/abc/agent_bases.py`](../../argumentation_analysis/agents/core/abc/agent_bases.py:1) et décrit dans [`agents_specialistes.md#structure-generale-dun-agent-danalyse`](./agents_specialistes.md)).
    *   Interface `OperationalAgent` ([`../../argumentation_analysis/orchestration/hierarchical/operational/agent_interface.py`](../../argumentation_analysis/orchestration/hierarchical/operational/agent_interface.py:1)) pour l'architecture hiérarchique.
*   **Mécanismes de création :**
    *   (À compléter après analyse du code si des factories/builders existent, par exemple dans `argumentation_analysis/agents/` ou via les adaptateurs dans [`../../argumentation_analysis/orchestration/hierarchical/operational/adapters/`](../../argumentation_analysis/orchestration/hierarchical/operational/adapters/:1)).
    *   Instanciation directe des classes d'agents (ex: [`ProjectManagerAgent`](../../argumentation_analysis/agents/core/pm/pm_agent.py:1), [`InformalAnalysisAgent`](../../argumentation_analysis/agents/core/informal/informal_agent.py:1), etc.).

## 4. Configuration des Agents

*   **Sources de configuration :**
    *   Paramètres des constructeurs (voir exemples dans [`agents_specialistes.md`](./agents_specialistes.md)).
    *   Fichiers de configuration externes (ex: [`config/fallacies_taxonomy.json`](../../config/fallacies_taxonomy.json:1) pour `ContextualFallacyAnalyzer`).
    *   (À compléter : y a-t-il un système de configuration centralisé pour les prompts, les modèles LLM par défaut/spécifiques ?).
*   **Configuration des prompts et instructions système :**
    *   Localisation des prompts (généralement dans les répertoires des agents, ex: `argumentation_analysis/agents/core/informal/prompts/`).

## 5. Enregistrement et Intégration dans l'Orchestration

*   **Orchestration Simple (`AgentGroupChat`) :**
    *   Ajout des instances d'agents au `AgentGroupChat` (voir [`../../argumentation_analysis/orchestration/analysis_runner.py`](../../argumentation_analysis/orchestration/analysis_runner.py:1)).
*   **Architecture Hiérarchique :**
    *   Rôle de l'`OperationalManager` ([`../../argumentation_analysis/orchestration/hierarchical/operational/manager.py`](../../argumentation_analysis/orchestration/hierarchical/operational/manager.py:1)) pour la prise en charge des agents opérationnels.
    *   Utilisation des adaptateurs ([`../../argumentation_analysis/orchestration/hierarchical/operational/adapters/`](../../argumentation_analysis/orchestration/hierarchical/operational/adapters/:1)) pour intégrer les agents existants.

## 6. Cycle de Vie des Agents

*   **États principaux :** Initialisation, exécution, attente, terminaison, erreur.
*   **Gestion par l'orchestrateur :**
    *   Stratégies de sélection et de terminaison dans l'orchestration simple ([`../../argumentation_analysis/core/strategies.py`](../../argumentation_analysis/core/strategies.py:1)).
    *   Contrôle par l'`OperationalManager` dans l'architecture hiérarchique.
*   **Gestion des erreurs et exceptions.**

## 7. Gestion des Dépendances et Ressources Partagées

*   **Services communs :**
    *   `LLMService` : Injection via constructeur, potentiellement via `LLMServiceFactory` (mentionné dans [`agents_specialistes.md`](./agents_specialistes.md), à localiser dans `project_core/services/`).
    *   `CacheService` : Injection optionnelle.
*   **Accès à l'état :**
    *   `RhetoricalAnalysisState` et `StateManagerPlugin` ([`../../argumentation_analysis/core/shared_state.py`](../../argumentation_analysis/core/shared_state.py:1), [`../../argumentation_analysis/core/state_manager_plugin.py`](../../argumentation_analysis/core/state_manager_plugin.py:1)) pour l'orchestration simple.
    *   États spécifiques (`StrategicState`, `TacticalState`, `OperationalState`) dans l'architecture hiérarchique.
*   **Partage de taxonomies et autres configurations :** (ex: `fallacies_taxonomy.json`).

## 8. Extension : Ajouter un Nouvel Agent

*   Étapes recommandées :
    1.  Définir la classe de l'agent (héritant de `BaseAnalysisAgent` ou implémentant `OperationalAgent`).
    2.  Développer les prompts et logiques spécifiques.
    3.  Gérer ses dépendances.
    4.  L'intégrer dans le(s) système(s) d'orchestration pertinent(s) (créer un adaptateur si nécessaire pour l'architecture hiérarchique).
    5.  Ajouter la configuration nécessaire.
    6.  Écrire les tests.

## 9. Références Croisées

*   [`docs/composants/synthese_collaboration.md`](./synthese_collaboration.md)
*   [`docs/composants/agents_specialistes.md`](./agents_specialistes.md)
*   (Autres documents pertinents)