# Projet Intelligence Symbolique

## Table des Matières
- [Introduction](#introduction)
- [Structure du Projet](#structure-du-projet)
- [Architecture Technique](#architecture-technique)
- [Guide de Démarrage Rapide](#guide-de-démarrage-rapide)
- [Modalités du projet](#modalités-du-projet)
- [Utilisation des LLMs et IA Symbolique](#utilisation-des-llms-et-ia-symbolique)
- [Sujets de Projets](#sujets-de-projets)
- [Guide de Contribution](#guide-de-contribution)
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
  - **[`tests/`](./argumentiation_analysis/tests/)** : Tests unitaires et d'intégration.

- **[`scripts/`](./scripts/)** : Scripts utilitaires pour le projet.
  - **[`cleanup/`](./scripts/cleanup/README.md)** : Scripts de nettoyage du projet.
  - **[`execution/`](./scripts/execution/README.md)** : Scripts d'exécution des fonctionnalités principales.

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

### 1. Créer un fork du dépôt

Pour commencer à travailler sur le projet, vous devez d'abord créer un fork du dépôt principal :

1. Connectez-vous à votre compte GitHub
2. Accédez au dépôt principal : [https://github.com/jsboigeEpita/2025-Epita-Intelligence-Symbolique](https://github.com/jsboigeEpita/2025-Epita-Intelligence-Symbolique)
3. Cliquez sur le bouton "Fork" en haut à droite de la page
4. Sélectionnez votre compte comme destination du fork

### 2. Cloner votre fork

Une fois le fork créé, clonez-le sur votre machine locale :

```bash
git clone https://github.com/VOTRE_NOM_UTILISATEUR/2025-Epita-Intelligence-Symbolique.git
cd 2025-Epita-Intelligence-Symbolique
```

### 3. Configurer l'environnement de développement

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

### 4. Configurer les variables d'environnement

Créez un fichier `.env` dans le dossier `argumentiation_analysis` en vous basant sur le fichier `.env.example` :

```bash
cp .env.example .env
```

Puis modifiez le fichier `.env` avec vos propres informations (clés API, etc.).

### 5. Lancer l'application

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

## Modalités du projet

### Organisation en groupes

Le projet peut être réalisé individuellement ou en groupe de 2 à 4 étudiants. Voici quelques conseils selon la taille de votre groupe :

#### Travail individuel
- Choisissez un sujet bien délimité et réaliste pour une personne
- Concentrez-vous sur une fonctionnalité spécifique à implémenter
- Documentez soigneusement votre travail pour faciliter l'intégration

#### Groupe de 2 étudiants
- Répartissez clairement les tâches entre les membres
- Établissez un planning de travail et des points de synchronisation réguliers
- Utilisez les branches Git pour travailler en parallèle

#### Groupe de 3-4 étudiants
- Désignez un chef de projet pour coordonner le travail
- Divisez le projet en sous-modules indépendants
- Mettez en place un processus de revue de code entre membres
- Utilisez les issues GitHub pour suivre l'avancement

### Livrables attendus

Pour chaque projet, vous devrez fournir :
1. Le code source de votre implémentation
2. Une documentation détaillée expliquant votre approche
3. Des tests unitaires et d'intégration
4. Un rapport final résumant votre travail

### Évaluation

L'évaluation portera sur :
- La qualité du code et de l'architecture
- La pertinence de l'approche choisie
- La couverture des tests
- La qualité de la documentation
- La présentation orale du projet

## Utilisation des LLMs et IA Symbolique

Ce projet combine l'utilisation des Grands Modèles de Langage (LLMs) avec des techniques d'IA symbolique pour l'analyse argumentative. Cette approche hybride permet de tirer parti des forces de chaque paradigme :

### Rôle des LLMs dans le projet

Les LLMs (comme GPT-4, Claude, etc.) sont utilisés pour :
- L'analyse sémantique des textes
- L'identification des arguments et sophismes
- La génération d'explications en langage naturel
- L'orchestration de haut niveau entre les agents

### Rôle de l'IA Symbolique

Les techniques d'IA symbolique (notamment via Tweety) sont utilisées pour :
- La formalisation logique des arguments
- La vérification de la validité des raisonnements
- La détection des contradictions
- L'inférence de nouvelles connaissances

### Intégration des approches

Le projet montre comment ces deux approches peuvent être intégrées efficacement :
- Les LLMs extraient et interprètent les arguments en langage naturel
- Ces arguments sont ensuite formalisés en logique propositionnelle
- Les outils symboliques vérifient la validité formelle
- Les résultats sont réintégrés dans un format compréhensible

Cette approche hybride représente une direction prometteuse pour développer des systèmes d'IA plus robustes et explicables.

## Sujets de Projets

Pour consulter la liste complète des sujets de projets proposés, veuillez vous référer au document [Sujets de Projets Détaillés](./docs/sujets_projets_detailles.md).

Les sujets sont organisés en trois catégories principales :
1. **Fondements théoriques et techniques** : Projets centrés sur les aspects formels, logiques et théoriques de l'argumentation
2. **Développement système et infrastructure** : Projets axés sur l'architecture, l'orchestration et les composants techniques
3. **Expérience utilisateur et applications** : Projets orientés vers les interfaces, visualisations et cas d'usage concrets

Chaque sujet est présenté avec une structure standardisée :
- **Contexte** : Présentation du domaine et de son importance
- **Objectifs** : Ce que le projet vise à accomplir
- **Technologies clés** : Outils, frameworks et concepts essentiels
- **Niveau de difficulté** : ⭐ (Accessible) à ⭐⭐⭐⭐⭐ (Très avancé)
- **Interdépendances** : Liens avec d'autres sujets de projets
- **Références** : Sources et documentation pour approfondir

Lors du choix de votre sujet, tenez compte de :
- La taille de votre groupe
- Vos compétences et intérêts
- Le temps disponible pour réaliser le projet

## Guide de Contribution

### Workflow de contribution

Pour contribuer au projet, suivez ces étapes :

1. **Créez une branche** dans votre fork pour votre fonctionnalité ou correction :
   ```bash
   git checkout -b feature/nom-de-votre-fonctionnalite
   ```

2. **Développez votre fonctionnalité** en suivant les bonnes pratiques de code :
   - Respectez les conventions de nommage existantes
   - Commentez votre code de manière claire
   - Écrivez des tests pour vos fonctionnalités

3. **Committez vos changements** avec des messages descriptifs :
   ```bash
   git add .
   git commit -m "Description claire de vos modifications"
   ```

4. **Poussez votre branche** vers votre fork :
   ```bash
   git push origin feature/nom-de-votre-fonctionnalite
   ```

5. **Créez une Pull Request (PR)** depuis votre branche vers le dépôt principal :
   - Accédez à votre fork sur GitHub
   - Cliquez sur "Pull Request"
   - Sélectionnez votre branche et le dépôt principal comme cible
   - Remplissez le formulaire avec une description détaillée de vos modifications

6. **Attendez la revue** de votre PR par les mainteneurs du projet
   - Soyez prêt à répondre aux commentaires et à apporter des modifications si nécessaire
   - Une fois approuvée, votre PR sera fusionnée dans le projet principal

### Bonnes pratiques de contribution

- **Maintenez votre fork à jour** avec le dépôt principal :
  ```bash
  git remote add upstream https://github.com/jsboigeEpita/2025-Epita-Intelligence-Symbolique.git
  git fetch upstream
  git merge upstream/main
  ```

- **Créez des branches spécifiques** pour chaque fonctionnalité ou correction
- **Testez vos modifications** avant de soumettre une PR
- **Documentez vos changements** dans les README appropriés
- **Respectez le style de code** existant
- **Communiquez clairement** dans vos messages de commit et descriptions de PR

### Résolution des conflits

Si des conflits surviennent lors de la fusion de votre PR :
1. Mettez à jour votre branche avec le dépôt principal
2. Résolvez les conflits localement
3. Poussez les modifications résolues vers votre branche

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

### Ressources externes utiles

- [Documentation Python](https://docs.python.org/fr/3/)
- [Documentation Semantic Kernel](https://learn.microsoft.com/fr-fr/semantic-kernel/)
- [Documentation Tweety Project](https://tweetyproject.org/doc/)
- [Guide Git pour les débutants](https://rogerdudler.github.io/git-guide/index.fr.html)
- [Guide des Pull Requests GitHub](https://docs.github.com/fr/pull-requests)

N'hésitez pas à explorer les différents répertoires du projet pour mieux comprendre son fonctionnement et identifier les opportunités d'amélioration.