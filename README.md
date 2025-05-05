# Projet Intelligence Symbolique

## Table des Matières
- [Introduction](#introduction)
- [Structure du Projet](#structure-du-projet)
- [Architecture Technique](#architecture-technique)
- [Guide de Démarrage Rapide](#guide-de-démarrage-rapide)
- [Modalités du projet](#modalités-du-projet)
- [Utilisation des LLMs et IA Symbolique](#utilisation-des-llms-et-ia-symbolique)
- [Sujets de Projets](#sujets-de-projets)
- [Directives de Contribution](#directives-de-contribution)
- [Ressources et Documentation](#ressources-et-documentation)

## Introduction

Ce projet a pour but de vous permettre d'appliquer concrètement les méthodes et outils vus en cours sur l'intelligence symbolique. Vous serez amenés à résoudre des problèmes réels ou réalistes à l'aide de ces techniques en développant un projet complet, depuis la modélisation jusqu'à la solution opérationnelle.

Cette année, contrairement au cours précédent de programmation par contrainte où vous avez livré des travaux indépendants, vous travaillerez tous de concert sur ce dépôt. Un tronc commun est fourni sous la forme d'une infrastructure d'analyse argumentative multi-agents que vous pourrez explorer à travers les nombreux README du projet.

## Structure du Projet

Le projet est organisé en plusieurs modules principaux :

- **[`argumentiation_analysis/`](./argumentiation_analysis/README.md)** : Dossier principal contenant l'infrastructure d'analyse argumentative multi-agents.
  - **[`agents/`](./argumentiation_analysis/agents/README.md)** : Agents spécialisés pour l'analyse (PM, Informal, PL, Extract).
  - **[`core/`](./argumentiation_analysis/core/README.md)** : Composants fondamentaux partagés (État, LLM, JVM).
  - **[`orchestration/`](./argumentiation_analysis/orchestration/README.md)** : Logique d'exécution de la conversation.
  - **[`ui/`](./argumentiation_analysis/ui/README.md)** : Interface utilisateur pour la configuration des analyses.
  - **[`utils/`](./argumentiation_analysis/utils/README.md)** : Utilitaires généraux et outils de réparation d'extraits.
  - **[`tests/`](./argumentiation_analysis/tests/README.md)** : Tests unitaires et d'intégration.

- **[`scripts/`](./scripts/README.md)** : Scripts utilitaires pour le projet.
  - **[`cleanup/`](./scripts/cleanup/README.md)** : Scripts de nettoyage du projet.
  - **[`execution/`](./scripts/execution/README.md)** : Scripts d'exécution des fonctionnalités principales.
  - **[`validation/`](./scripts/validation/README.md)** : Scripts de validation des fichiers Markdown.

- **[`docs/`](./docs/README.md)** : Documentation supplémentaire du projet.

- **[`examples/`](./examples/README.md)** : Exemples de textes et données pour les tests.

Chaque module dispose de son propre README détaillé expliquant son fonctionnement et son utilisation.

## Architecture Technique

Cette section présente l'architecture technique du projet d'analyse argumentative multi-agents, expliquant comment les différents composants interagissent pour former un système cohérent.

### Vue d'ensemble

Le projet est construit autour d'une architecture multi-agents où différents agents spécialisés collaborent pour analyser des textes argumentatifs. Cette architecture permet une séparation claire des responsabilités et facilite l'extension du système avec de nouveaux agents ou fonctionnalités.

```
┌─────────────────────────────────────────────────────────────┐
│                      Interface Utilisateur                   │
└───────────────────────────────┬─────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────┐
│                        Orchestration                         │
└───────┬─────────────────┬─────────────────┬─────────────────┘
        │                 │                 │
┌───────▼───────┐ ┌───────▼───────┐ ┌───────▼───────┐
│  Agent Extract │ │ Agent Informal│ │   Agent PL    │ ...
└───────┬───────┘ └───────┬───────┘ └───────┬───────┘
        │                 │                 │
┌───────▼─────────────────▼─────────────────▼───────┐
│                   État Partagé                     │
└───────────────────────────────────────────────────┘
        │                 │                 │
┌───────▼───────┐ ┌───────▼───────┐ ┌───────▼───────┐
│  LLM Service  │ │  JVM (Tweety) │ │ Autres Services│
└───────────────┘ └───────────────┘ └───────────────┘
```

### Flux de données et cycle de vie d'une analyse

Le cycle de vie d'une analyse argumentative suit les étapes suivantes:

1. **Ingestion des données**: Le texte à analyser est fourni via l'interface utilisateur ou un script.
2. **Extraction des arguments**: L'agent Extract identifie les arguments présents dans le texte.
3. **Analyse informelle**: L'agent Informal analyse les arguments pour détecter les sophismes et évaluer leur qualité.
4. **Analyse formelle**: L'agent PL (Propositional Logic) formalise les arguments en logique propositionnelle et vérifie leur validité.
5. **Synthèse des résultats**: Les résultats des différents agents sont combinés dans l'état partagé.
6. **Présentation**: Les résultats sont formatés et présentés à l'utilisateur.

Chaque étape est gérée par un agent spécialisé, et l'orchestration assure la coordination entre ces agents.

## Guide de Démarrage Rapide

Ce guide vous permettra de configurer rapidement l'environnement de développement et d'exécuter le projet d'analyse argumentative multi-agents.

### 1. Cloner le dépôt

```bash
git clone https://github.com/jsboigeEpita/2025-Epita-Intelligence-Symbolique.git
cd 2025-Epita-Intelligence-Symbolique
```

### 2. Configurer l'environnement de développement

#### Prérequis

- **Python 3.9+** : Nécessaire pour exécuter le code Python
- **Java JDK 11+** : Requis pour l'intégration avec Tweety via JPype
- **Pip** : Gestionnaire de paquets Python

#### Installation des dépendances Python

Naviguez vers le dossier principal du projet et installez les dépendances :

```bash
cd argumentiation_analysis
pip install -r requirements.txt
```

### 3. Configurer les variables d'environnement

Créez ou modifiez le fichier `.env` dans le dossier `argumentiation_analysis` avec les informations nécessaires.

### 4. Lancer l'application

Plusieurs points d'entrée sont disponibles selon vos besoins et cas d'utilisation :

#### Notebook d'orchestration principal

```bash
jupyter notebook main_orchestrator.ipynb
```

#### Interface utilisateur web

```bash
python -m ui.app
```

#### Analyse via script Python

```bash
python run_analysis.py --input votre_texte.txt --output resultats.json
```

#### Scripts utilitaires

Le projet inclut plusieurs scripts utilitaires pour faciliter le développement et la maintenance :

- **Scripts de nettoyage** : Voir [documentation des scripts de nettoyage](./scripts/cleanup/README.md)
- **Scripts d'exécution** : Voir [documentation des scripts d'exécution](./scripts/execution/README.md)
- **Scripts de validation** : Voir [documentation des scripts de validation](./scripts/validation/README.md)

## Modalités du projet

[Section conservée du README original]

## Utilisation des LLMs et IA Symbolique

[Section conservée du README original]

## Sujets de Projets

Pour consulter la liste complète des sujets de projets proposés, veuillez vous référer au document [Sujets de Projets](./docs/nouvelle_section_sujets_projets.md).

## Directives de Contribution

[Section conservée du README original]

## Ressources et Documentation

Pour vous aider dans la réalisation de votre projet, vous trouverez dans ce dépôt :

- Des README détaillés pour chaque composant du système
- Des notebooks explicatifs et interactifs
- Des exemples d'utilisation des différentes bibliothèques
- Une documentation sur l'architecture du système

Documentation supplémentaire :
- [Changelog](./CHANGELOG.md) : Journal des modifications apportées au projet
- [Documentation supplémentaire](./docs/README.md) : Documentation additionnelle sur divers aspects du projet
- [Exemples](./examples/README.md) : Exemples de textes et données pour les tests

N'hésitez pas à explorer les différents répertoires du projet pour mieux comprendre son fonctionnement et identifier les opportunités d'amélioration.