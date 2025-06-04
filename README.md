<!--
Ce fichier README.md a été partiellement mis à jour pour refléter la nouvelle structure des répertoires scripts/, docs/ et results/.
Les autres sections peuvent nécessiter une vérification manuelle.
-->
# Projet Intelligence Symbolique

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Tests](https://img.shields.io/badge/tests-100%25-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-87%25-yellow)
![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Documentation](https://img.shields.io/badge/docs-up%20to%20date-brightgreen)
![License](https://img.shields.io/badge/license-MIT-blue)

## Table des Matières
- [Introduction](#introduction)
- [Structure du Projet](#structure-du-projet)
- [Architecture Technique](#architecture-technique)
- [Guide de Démarrage Rapide](#guide-de-démarrage-rapide)
- [Modalités du projet](#modalités-du-projet)
- [Utilisation des LLMs et IA Symbolique](#utilisation-des-llms-et-ia-symbolique)
- [Documentation d'Architecture](#documentation-darchitecture)
- [API Web et Interfaces Modernes](#api-web-et-interfaces-modernes)
- [Sujets de Projets](#sujets-de-projets)
- [Guide de Contribution](#guide-de-contribution)
- [Ressources et Documentation](#ressources-et-documentation)

## Introduction

Ce projet a pour but de vous permettre d'appliquer concrètement les méthodes et outils vus en cours sur l'intelligence symbolique. Vous serez amenés à résoudre des problèmes réels ou réalistes à l'aide de ces techniques en développant un projet complet, depuis la modélisation jusqu'à la solution opérationnelle.

Cette année, contrairement au cours précédent de programmation par contrainte où vous avez livré des travaux indépendants, vous travaillerez tous de concert sur ce dépôt. Un tronc commun est fourni sous la forme d'une infrastructure d'analyse argumentative multi-agents que vous pourrez explorer à travers les nombreux README du projet.

## Structure du Projet

Le projet est organisé en plusieurs modules principaux :

- **[`argumentation_analysis/`](./argumentation_analysis/README.md)** : Dossier principal contenant l'infrastructure d'analyse argumentative multi-agents.
  - **[`agents/`](./argumentation_analysis/agents/README.md)** : Agents spécialisés pour l'analyse.
    - **`core/`** : Implémentations des agents spécialistes (PM, Informal, PL, Extract).
    - **`extract/`** : Module de redirection vers agents.core.extract.
    - **`tools/`** : Outils utilisés par les agents.
  - **[`config/`](./argumentation_analysis/config/)** : Fichiers de configuration du projet.
  - **[`core/`](./argumentation_analysis/core/README.md)** : Composants fondamentaux partagés (État, LLM, JVM).
    - **`communication/`** : Système de communication entre agents.
  - **[`data/`](./argumentation_analysis/data/README.md)** : Données et ressources utilisées par le projet.
  - **[`libs/`](./argumentation_analysis/libs/)** : Bibliothèques externes et natives.
  - **[`models/`](./argumentation_analysis/models/)** : Modèles de données du projet.
  - **[`orchestration/`](./argumentation_analysis/orchestration/README.md)** : Logique d'exécution de la conversation.
  - **[`results/`](./argumentation_analysis/results/README.md)** : Résultats des analyses.
  - **[`services/`](./argumentation_analysis/services/README.md)** : Services partagés (cache, crypto, extraction, etc.).
  - **[`ui/`](./argumentation_analysis/ui/README.md)** : Interface utilisateur pour la configuration des analyses.
    - **`extract_editor/`** : Éditeur de marqueurs d'extraits.
  - **[`utils/`](./argumentation_analysis/utils/README.md)** : Utilitaires généraux et outils de réparation d'extraits.
    - **`extract_repair/`** : Outils de réparation des extraits.
  - **[`tests/`](./argumentation_analysis/tests/)** : Tests unitaires et d'intégration.

- **[`scripts/`](./scripts/README.md)** : Scripts utilitaires pour le projet, incluant des outils pour le nettoyage, l'exécution, les rapports, la configuration, les tests, et la validation.
  - **[`cleanup/`](./scripts/cleanup/README.md)** : Scripts de nettoyage du projet.
  - **[`corrections_tests/`](./scripts/corrections_tests/)** : Scripts pour les corrections et diagnostics de tests.
  - **[`execution/`](./scripts/execution/README.md)** : Scripts d'exécution des fonctionnalités principales.
  - **[`reports/`](./scripts/reports/README.md)** : Scripts pour la génération et mise à jour de rapports.
  - **[`setup/`](./scripts/setup/README.md)** : Scripts pour la configuration de l'environnement et des dépendances.
  - **[`testing/`](./scripts/testing/README.md)** : Scripts liés à l'exécution et à la simulation de tests.
  - **[`utils/`](./scripts/utils/README.md)** : Utilitaires généraux pour les scripts.
  - **[`validation/`](./scripts/validation/README.md)** : Scripts de validation du projet.

- **[`docs/`](./docs/README.md)** : Documentation complète du projet, incluant :
  - **[`architecture/`](./docs/architecture/README.md)** : Détails sur l'architecture du système.
  - **[`composants/`](./docs/composants/README.md)** : Description des principaux composants.
  - **[`guides/`](./docs/guides/README.md)** : Guides pour les développeurs et utilisateurs.
  - **[`integration/`](./docs/integration/README.md)** : Informations sur l'intégration des modules.
  - **[`outils/`](./docs/outils/README.md)** : Documentation des outils d'analyse rhétorique.
  - **[`projets/`](./docs/projets/README.md)** : Informations sur les sujets de projets étudiants.
  - **[`reference/`](./docs/reference/README.md)** : Documentation de référence des API et modules.
  - Ainsi que d'autres sections pour l'analyse, les diagrammes, les rapports, etc.

- **[`examples/`](./examples/README.md)** : Exemples de textes et données pour les tests et démonstrations.

- **[`libs/`](./libs/README.md)** : Bibliothèques externes utilisées par le projet.
  - **[`native/`](./libs/native/)** : Bibliothèques natives (DLL) pour les solveurs SAT.

- **`logs/`** : Journaux d'exécution du système (dossier créé dynamiquement lors de l'exécution, non inclus dans le dépôt).

- **[`results/`](./results/README.md)** : Résultats des analyses, tests, comparaisons et visualisations.
  - **[`analyses/`](./results/analyses/)** : Analyses rhétoriques détaillées (basiques et avancées).
  - **[`comparisons/`](./results/comparisons/)** : Comparaisons de performance et métriques.
  - **[`reports/`](./results/reports/)** : Rapports de synthèse et d'analyse complets.
  - **[`summaries/`](./results/summaries/)** : Résumés d'analyses par agent et par texte.
  - **[`visualizations/`](./results/visualizations/)** : Graphiques et visualisations des résultats.
  - D'autres sous-dossiers peuvent contenir des rapports de tests spécifiques et des logs.

- **[`services/`](./services/README.md)** : Services web et API pour l'intégration externe.
  - **[`web_api/`](./services/web_api/)** : API REST Flask pour l'analyse argumentative, permettant l'intégration avec des interfaces web modernes.

- **[`tutorials/`](./tutorials/README.md)** : Tutoriels pour prendre en main le système.

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

- **Conda (Miniconda ou Anaconda)** : Nécessaire pour la gestion de l'environnement et des dépendances.
- **Git** : Pour cloner le dépôt.

#### Installation de l'environnement Conda

1.  **Assurez-vous que Conda est installé** et configuré dans votre PATH.
    Vous pouvez télécharger Miniconda (une version légère de Conda) depuis [https://docs.conda.io/en/latest/miniconda.html](https://docs.conda.io/en/latest/miniconda.html).

2.  **Exécutez le script de configuration de l'environnement** à la racine du projet cloné. Ce script est le point d'entrée principal pour préparer votre environnement de développement.
    Ouvrez un terminal PowerShell et exécutez :
    ```powershell
    .\setup_project_env.ps1
    ```
    Ce script [`setup_project_env.ps1`](setup_project_env.ps1:0) effectue les actions suivantes :
    * Vérifie la présence de Conda.
    * Crée (ou met à jour) l'environnement Conda nommé `projet-is` à partir du fichier [`environment.yml`](environment.yml:1). Cet environnement inclut Python, Clingo, JPype1, Octave (via `pip`) et toutes les autres dépendances nécessaires.
    * Télécharge et configure un JDK portable (actuellement Temurin 17) dans le dossier [`libs/portable_jdk/`](libs/portable_jdk:0) si non présent ou si `-ForceReinstall` est utilisé.
    * Télécharge et configure une version portable d'Octave dans le dossier [`libs/portable_octave/`](libs/portable_octave:0) si non présent ou si `-ForceReinstall` est utilisé.
    * Crée ou met à jour le fichier `.env` à partir de `.env.template`, en configurant notamment `JAVA_HOME` pour pointer vers le JDK portable et `USE_REAL_JPYPE=true`.
    * Nettoie les anciens répertoires d'environnements virtuels (`venv`, `.venv`, etc.) si détectés (avec confirmation en mode interactif).
    * À la fin de son exécution, il appelle automatiquement le script [`activate_project_env.ps1`](activate_project_env.ps1:0) pour charger les variables d'environnement du fichier `.env` dans la session PowerShell actuelle et afficher des instructions pour l'activation manuelle de l'environnement Conda ou l'exécution de commandes.

    **Options du script `setup_project_env.ps1` :**
    *   `-InteractiveMode` : Active le mode interactif, posant des questions avant certaines actions (ex: suppression d'un environnement Conda existant).
    *   `-ForceReinstall` : Force la réinstallation du JDK, d'Octave et de l'environnement Conda, même s'ils semblent déjà présents. Utile pour repartir d'une configuration propre.
    *   `-Python310Path "chemin\vers\python3.10.exe"` : (Optionnel, principalement pour des cas d'usage hérités) Spécifie un chemin vers un exécutable Python 3.10 si nécessaire pour des scripts hors Conda.

3.  **Activation de l'environnement et chargement des variables** :

    Le script [`setup_project_env.ps1`](setup_project_env.ps1:0) appelle [`activate_project_env.ps1`](activate_project_env.ps1:0) à la fin. Ce dernier script est responsable du chargement des variables d'environnement (comme `JAVA_HOME`) depuis le fichier `.env` dans votre session PowerShell actuelle.

    Si vous ouvrez un nouveau terminal après avoir exécuté `setup_project_env.ps1` une première fois, ou si vous souhaitez simplement charger les variables d'environnement et/ou exécuter une commande dans l'environnement Conda sans refaire tout le setup :

    *   **Pour charger les variables d'environnement et activer Conda manuellement** :
        ```powershell
        # Exécutez d'abord activate_project_env.ps1 pour charger .env
        . .\activate_project_env.ps1
        # Puis activez l'environnement Conda
        conda activate projet-is
        ```
        Votre prompt devrait maintenant indiquer `(projet-is)`.

    *   **Pour exécuter une commande spécifique directement dans l'environnement Conda configuré** (charge `.env` et active l'environnement pour la commande) :
        ```powershell
        powershell -File .\activate_project_env.ps1 -CommandToRun "votre_commande --arg1"
        # Exemple:
        powershell -File .\activate_project_env.ps1 -CommandToRun "python -m pytest -v"
        ```
        Cela est utile pour les tâches ponctuelles ou les scripts d'intégration continue.

### 4. Configurer les variables d'environnement (vérification)

Le script [`setup_project_env.ps1`](setup_project_env.ps1:0) (via [`activate_project_env.ps1`](activate_project_env.ps1:0)) configure le fichier `.env` et charge les variables. Normalement, `JAVA_HOME` est automatiquement pointé vers le JDK portable dans [`libs/portable_jdk/`](libs/portable_jdk:0) et `USE_REAL_JPYPE` est mis à `true`.
Vous pouvez vérifier le contenu du fichier `.env` pour des configurations spécifiques (par exemple, les clés API pour `semantic-kernel` si vous les utilisez).

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

L'évaluation des présentations avec slides et démo sera collégiale. La note de l'enseignant comptera pour moitié.

L'évaluation portera sur 4 critères :
1. **Forme/communication** : Qualité de la présentation, clarté des explications, structure des slides et de la démo
2. **Théorie** : Exploration et explication de l'état de l'art et des techniques utilisées
3. **Technique** : Réalisations, performances, tests et qualité du code
4. **Gestion de projet/collaboration** : Gestion intelligente de GitHub et du travail collaboratif durant la durée du projet

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

## Documentation d'Architecture

Une description détaillée de l'architecture du projet, incluant l'architecture globale, les systèmes de communication, l'analyse de l'état actuel et les propositions d'évolution, est disponible dans le répertoire [docs/architecture/](./docs/architecture/). Le document principal de cette section est le [README d'Architecture](./docs/architecture/README.md).

## API Web et Interfaces Modernes

Le projet inclut une **API REST complète** dans [`services/web_api/`](./services/web_api/) qui expose toutes les fonctionnalités d'analyse argumentative via des endpoints HTTP. Cette API permet aux étudiants de créer facilement des interfaces web modernes (React, Vue, Angular) sans avoir à gérer directement la complexité du moteur d'analyse.

### Fonctionnalités de l'API

- **Analyse complète de textes** : Endpoint `/api/analyze` pour l'analyse argumentative complète
- **Validation d'arguments** : Endpoint `/api/validate` pour la validation logique
- **Détection de sophismes** : Endpoint `/api/fallacies` pour identifier les erreurs de raisonnement
- **Construction de frameworks** : Endpoint `/api/framework` pour créer des frameworks de Dung
- **Documentation interactive** : Endpoint `/api/endpoints` listant tous les services disponibles

### Démarrage rapide de l'API

```bash
# Naviguer vers l'API
cd services/web_api

# Installer les dépendances
pip install -r requirements.txt

# Démarrer l'API
python app.py
```

L'API sera accessible sur `http://localhost:5000` avec une documentation complète des endpoints.

### Guides pédagogiques spécialisés

Pour faciliter le développement d'interfaces web, consultez les **guides pédagogiques détaillés** dans [`docs/projets/sujets/`](./docs/projets/sujets/) :

- **[Interface Web d'Analyse Argumentative](./docs/projets/sujets/3.1.1_Interface_Web_Analyse_Argumentative.md)** : Guide complet pour créer des interfaces web modernes
- **[Aide spécialisée Interface Web](./docs/projets/sujets/aide/interface-web/)** : Ressources pratiques, exemples de code React, et guides de démarrage rapide
- **[Démarrage Rapide Interface Web](./docs/projets/sujets/aide/interface-web/DEMARRAGE_RAPIDE.md)** : Checklist étape par étape pour être opérationnel en 50 minutes

Ces ressources incluent des exemples pratiques, des composants React prêts à l'emploi, et des solutions aux problèmes courants.

## Sujets de Projets

Pour une description détaillée de tous les sujets de projets, veuillez consulter le document [**Sujets de Projets**](./docs/projets/README.md) qui présente l'ensemble des projets possibles avec leurs spécifications complètes.

Les projets sont organisés en quatre catégories principales :
1. **Fondements théoriques et techniques** : Projets centrés sur les aspects formels, logiques et théoriques de l'argumentation
2. **Développement système et infrastructure** : Projets axés sur l'architecture, l'orchestration et les composants techniques
3. **Expérience utilisateur et applications** : Projets orientés vers les interfaces, visualisations et cas d'usage concrets
4. **Lutte contre la désinformation** : Projets axés sur la détection, l'analyse et la lutte contre la désinformation

Chaque sujet est présenté avec une structure standardisée :
- **Contexte** : Présentation du domaine et de son importance
- **Objectifs** : Ce que le projet vise à accomplir
- **Technologies clés** : Outils, frameworks et concepts essentiels
- **Niveau de difficulté** : ⭐ (Accessible) à ⭐⭐⭐⭐⭐ (Très avancé)
- **Estimation d'effort** : Temps de développement estimé en semaines-personnes
- **Interdépendances** : Liens avec d'autres sujets de projets
- **Références** : Sources et documentation pour approfondir
- **Livrables attendus** : Résultats concrets à produire

Lors du choix de votre sujet, tenez compte de :
- La taille de votre groupe
- Vos compétences et intérêts
- Le temps disponible pour réaliser le projet
- Les interdépendances avec d'autres projets

Pour faciliter votre choix, plusieurs vues transversales sont disponibles :
- [Projets par niveau de difficulté](./docs/projets/README.md#filtrage-par-niveau-de-difficulté) - Pour choisir selon vos compétences
- [Projets par technologie](./docs/projets/README.md#filtrage-par-technologie) - Pour choisir selon vos intérêts techniques
- [Projets par durée estimée](./docs/projets/README.md#filtrage-par-durée-estimée) - Pour choisir selon votre disponibilité
- [Matrice d'interdépendances](./docs/projets/matrice_interdependances.md) - Pour comprendre les relations entre projets

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
- [Architecture Globale](./docs/architecture/architecture_globale.md) : Description de l'architecture complète du système
- [Documentation des Tests](./tests/README.md) : Stratégie de test, exécution et interprétation des tests
- [Extraits chiffrés](./docs/reports/extraits_chiffres.md) : Documentation détaillée sur le système d'extraits chiffrés
- [Exemples](./examples/README.md) : Exemples de textes et données pour les tests

### Ressources externes utiles

- [Documentation Python](https://docs.python.org/fr/3/)
- [Documentation Semantic Kernel](https://learn.microsoft.com/fr-fr/semantic-kernel/)
- [Documentation Tweety Project](https://tweetyproject.org/doc/)
- [Guide Git pour les débutants](https://rogerdudler.github.io/git-guide/index.fr.html)
- [Guide des Pull Requests GitHub](https://docs.github.com/fr/pull-requests)

N'hésitez pas à explorer les différents répertoires du projet pour mieux comprendre son fonctionnement et identifier les opportunités d'amélioration.
