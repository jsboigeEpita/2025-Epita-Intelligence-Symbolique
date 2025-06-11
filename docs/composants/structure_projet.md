# Structure du Projet et Composants du Système d'Orchestration Agentique d'Analyse Rhétorique

## Table des matières

- [Vue d'ensemble](#vue-densemble)
- [Organisation des dossiers](#organisation-des-dossiers)
  - [Structure à la racine du projet](#structure-à-la-racine-du-projet)
  - [Structure du module `argumentation_analysis`](#structure-du-module-argumentation_analysis)
- [Composants principaux](#composants-principaux)
  - [Module `argumentation_analysis`](#module-argumentation_analysis)
    - [Core (`argumentation_analysis/core/`) : Composants fondamentaux](#core-argumentation_analysiscore--composants-fondamentaux)
    - [Agents (`argumentation_analysis/agents/`) : Agents spécialistes](#agents-argumentation_analysisagents--agents-spécialistes)
    - [Services Internes (`argumentation_analysis/services/`) : Services partagés](#services-internes-argumentation_analysisservices--services-partagés)
    - [Orchestration (`argumentation_analysis/orchestration/`) : Mécanismes d'orchestration](#orchestration-argumentation_analysisorchestration--mécanismes-dorchestration)
    - [UI (`argumentation_analysis/ui/`) : Interface utilisateur](#ui-argumentation_analysisui--interface-utilisateur)
    - [Models (`argumentation_analysis/models/`) : Modèles de données](#models-argumentation_analysismodels--modèles-de-données)
    - [Utils (`argumentation_analysis/utils/`) : Utilitaires spécifiques](#utils-argumentation_analysisutils--utilitaires-spécifiques)
    - [Analytics (`argumentation_analysis/analytics/`) : Analyse de données](#analytics-argumentation_analysisanalytics--analyse-de-données)
    - [NLP (`argumentation_analysis/nlp/`) : Traitement du Langage Naturel](#nlp-argumentation_analysisnlp--traitement-du-langage-naturel)
    - [Pipelines (`argumentation_analysis/pipelines/`) : Pipelines de traitement](#pipelines-argumentation_analysispipelines--pipelines-de-traitement)
    - [Reporting (`argumentation_analysis/reporting/`) : Génération de rapports](#reporting-argumentation_analysisreporting--génération-de-rapports)
    - [Service Setup (`argumentation_analysis/service_setup/`) : Configuration des services internes](#service-setup-argumentation_analysisservice_setup--configuration-des-services-internes)
    - [Config (`argumentation_analysis/config/`) : Configuration spécifique](#config-argumentation_analysisconfig--configuration-spécifique)
    - [Data (`argumentation_analysis/data/`) : Données spécifiques](#data-argumentation_analysisdata--données-spécifiques)
    - [Notebooks (`argumentation_analysis/notebooks/`) : Notebooks Jupyter](#notebooks-argumentation_analysisnotebooks--notebooks-jupyter)
    - [Scripts (`argumentation_analysis/scripts/`) : Scripts spécifiques au module](#scripts-argumentation_analysisscripts--scripts-spécifiques-au-module)
    - [Tests (`argumentation_analysis/tests/`) : Tests spécifiques au module](#tests-argumentation_analysistests--tests-spécifiques-au-module)
  - [Modules et dossiers à la racine du projet](#modules-et-dossiers-à-la-racine-du-projet)
    - [Project Core (`project_core/`) : Utilitaires de projet](#project-core-project_core--utilitaires-de-projet)
    - [Config (`config/`) : Configuration globale](#config-config--configuration-globale)
    - [Docs (`docs/`) : Documentation](#docs-docs--documentation)
    - [Tests (`tests/`) : Tests globaux](#tests-tests--tests-globaux)
    - [Scripts (`scripts/`) : Scripts généraux](#scripts-scripts--scripts-généraux)
    - [Services (`services/`) : API Web](#services-services--api-web)
    - [Libs (`libs/`) : Bibliothèques externes et natives](#libs-libs--bibliothèques-externes-et-natives)
    - [Examples (`examples/`) : Exemples globaux](#examples-examples--exemples-globaux)
    - [Archives (`_archives/`) : Archives](#archives-_archives--archives)
- [Flux de données](#flux-de-données)
- [Interfaces entre composants](#interfaces-entre-composants)
- [Extensibilité](#extensibilité)

## Vue d'ensemble

Le Système d'Orchestration Agentique d'Analyse Rhétorique est une plateforme avancée qui utilise plusieurs agents IA spécialisés collaborant pour analyser des textes argumentatifs sous différents angles. Le projet implémente une approche multi-agents en utilisant Python et le framework Semantic Kernel, permettant une analyse rhétorique complète qui combine :

- **Analyse informelle** : Identification d'arguments et de sophismes
- **Analyse formelle** : Formalisation en logique propositionnelle et vérification de validité
- **Extraction intelligente** : Identification et réparation des extraits de texte pertinents

L'architecture du système est conçue autour d'un état partagé central qui permet aux agents de communiquer et de construire une analyse collaborative. L'orchestration est basée sur la désignation explicite de l'agent suivant dans la chaîne d'analyse, ce qui permet une coordination efficace entre les agents.

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

## Organisation des dossiers

Le projet est organisé en plusieurs modules principaux, chacun ayant une responsabilité spécifique. Il est important de distinguer la structure à la racine du projet de celle du module principal `argumentation_analysis/`.

### Structure à la racine du projet

```
./
├── argumentation_analysis/   # Module principal de l'application d'analyse rhétorique (détaillé ci-dessous)
├── project_core/             # Utilitaires de développement, intégration, aspects fondamentaux non spécifiques
│   ├── dev_utils/            # Utilitaires pour les développeurs
│   ├── integration/          # Scripts ou configurations pour l'intégration continue/déploiement
│   └── utils/                # Utilitaires généraux pour le projet
├── config/                   # Configuration globale du projet
│   ├── .env.template         # Template pour les variables d'environnement globales
│   ├── pytest.ini            # Configuration pour Pytest (peut être à la racine aussi)
│   └── requirements-test.txt # Dépendances spécifiques pour les tests globaux
├── docs/                     # Documentation du projet (guides, architecture, rapports)
├── tests/                    # Ensemble des tests du projet (unitaires, intégration, fonctionnels)
│   ├── fixtures/             # Fixtures Pytest partagées
│   ├── mocks/                # Mocks globaux pour les tests
│   └── ...                   # Organisation des tests par type ou module testé
├── scripts/                  # Scripts généraux pour le projet
│   ├── setup/                # Scripts d'installation et de configuration de l'environnement
│   ├── maintenance/          # Scripts pour la maintenance du code (imports, formatage)
│   ├── cleanup/              # Scripts pour le nettoyage du projet
│   ├── reporting/            # Scripts pour générer des rapports globaux (couverture, etc.)
│   ├── execution/            # Scripts pour exécuter des workflows ou des tâches spécifiques
│   └── utils/                # Utilitaires pour les scripts
├── services/                 # Exposition de fonctionnalités via une API Web
│   └── web_api/              # Implémentation de l'API Web (ex: Flask, FastAPI)
│       ├── models/           # Modèles de données pour l'API
│       └── tests/            # Tests spécifiques à l'API Web
├── libs/                     # Bibliothèques tierces, incluant des binaires natifs et Tweety
│   ├── native/               # Bibliothèques natives (ex: lingeling.dll, minisat.dll)
│   └── tweety/               # Copie ou modules liés à Tweety
├── examples/                 # Exemples d'utilisation ou de données pour le projet global
├── _archives/                # Sauvegardes et versions archivées (généralement non versionné)
├── htmlcov_demonstration/    # Rapports de couverture de code HTML (générés, non versionnés)
├── .git/                     # Répertoire Git
├── .gitignore                # Fichiers et dossiers ignorés par Git
├── README.md                 # Description principale du projet
├── requirements.txt          # Dépendances Python principales du projet
├── setup.py                  # Script de configuration pour la distribution du projet (si applicable)
├── environment.yml           # Définition de l'environnement Conda (si utilisé)
├── conftest.py               # Fixtures Pytest globales (peut être à la racine)
└── ...                       # Autres fichiers de configuration ou scripts racine
```

### Structure du module `argumentation_analysis`

Ce module contient le cœur logique de l'application d'analyse rhétorique.

```
argumentation_analysis/
├── __init__.py
├── agents/                   # Agents spécialistes et leurs outils
│   ├── __init__.py
│   ├── core/                 # Implémentations des agents spécialistes (PM, Informal, PL, Extract)
│   │   ├── __init__.py
│   │   ├── extract/
│   │   ├── informal/
│   │   ├── logic/            # (Précédemment PL)
│   │   └── pm/
│   ├── data/                 # Données spécifiques aux agents (ex: taxonomie des sophismes)
│   ├── extract/              # Module de redirection vers agents.core.extract (compatibilité)
│   ├── tools/                # Outils utilisés par les agents (analyse de résultats, encryption)
│   └── utils/                # Utilitaires spécifiques aux agents (ex: optimisation agent informel)
├── analytics/                # (Nouveau) Modules pour l'analyse de données, métriques des analyses
├── config/                   # Fichiers de configuration spécifiques à argumentation_analysis
│   └── .env.template         # Template pour les variables d'environnement spécifiques
├── core/                     # Composants fondamentaux de l'application d'analyse
│   ├── __init__.py
│   ├── communication/        # Système de communication entre agents
│   ├── jvm_setup.py          # Configuration de l'environnement JVM pour Tweety
│   ├── llm_service.py        # Service d'accès aux modèles de langage (LLM)
│   ├── shared_state.py       # Gestion de l'état partagé de l'analyse
│   ├── state_manager_plugin.py # Plugin Semantic Kernel pour la gestion de l'état
│   └── strategies.py         # Stratégies d'orchestration des agents
├── data/                     # Données et ressources utilisées par l'analyse (corpus, etc.)
├── examples/                 # Exemples spécifiques à argumentation_analysis
├── mocks/                    # (Nouveau) Mocks pour les tests internes à argumentation_analysis
├── models/                   # Modèles de données (Pydantic, dataclasses) pour l'analyse
├── nlp/                      # (Nouveau) Composants pour le Traitement du Langage Naturel (NLP)
├── notebooks/                # Notebooks Jupyter pour l'expérimentation et l'orchestration interactive
│   └── ui/                   # Notebooks liés à l'interface utilisateur (ex: extract_marker_editor.ipynb)
├── orchestration/            # Mécanismes d'orchestration de la collaboration entre agents
├── pipelines/                # (Nouveau) Définition de pipelines de traitement ou d'analyse
├── reporting/                # (Nouveau) Outils pour générer des rapports spécifiques aux analyses
├── results/                  # (Potentiel) Résultats des analyses (créé dynamiquement)
├── scripts/                  # Scripts spécifiques aux opérations ou workflows de argumentation_analysis
│                             # (ex: run_fix_missing_first_letter.py, simulate_balanced_participation.py)
├── service_setup/            # (Nouveau) Configuration et initialisation des services internes
│   └── analysis_services.py  # Exemple de service d'analyse
├── services/                 # Services internes partagés par les composants de argumentation_analysis
│   ├── __init__.py
│   ├── cache_service.py      # Service de mise en cache
│   ├── crypto_service.py     # Service de chiffrement
│   ├── definition_service.py # Service de gestion des définitions
│   ├── extract_service.py    # Service d'extraction de texte
│   └── fetch_service.py      # Service de récupération de texte
├── tests/                    # Tests unitaires et d'intégration spécifiques au module argumentation_analysis
│                             # (ex: test_extract_agent.py, test_informal_agent.py)
├── ui/                       # Interface utilisateur (basée sur ipywidgets ou autre)
│   ├── __init__.py
│   ├── extract_editor/       # Éditeur de marqueurs d'extraits
│   ├── app.py                # Application principale de l'UI
│   ├── config.py             # Configuration de l'interface
│   ├── extract_utils.py      # Utilitaires pour l'extraction dans l'UI
│   ├── cache_utils.py        # Utilitaires de cache pour l'UI
│   ├── fetch_utils.py        # Utilitaires de récupération de données pour l'UI
│   ├── file_operations.py    # Opérations sur fichiers pour l'UI
│   └── utils.py              # Utilitaires généraux pour l'UI
└── utils/                    # Utilitaires généraux spécifiques à argumentation_analysis
    ├── __init__.py
    ├── core_utils/           # Utilitaires de base (fichiers, logs, système, texte)
    ├── dev_tools/            # Outils pour les développeurs (formatage, validation, refactoring)
    ├── extract_repair/       # Outils de réparation des extraits
    └── ...                   # Autres utilitaires (metrics_calculator, report_generator)
```

Cette organisation modulaire permet une séparation claire des responsabilités et facilite la maintenance et l'extension du système.
## Préparation et Pré-traitement des Données Textuelles

Avant que les textes ne soient soumis aux agents d'analyse principaux (comme `InformalAnalysisAgent`, `PropositionalLogicAgent`, ou même `ExtractAgent` pour son analyse sémantique), plusieurs étapes de pré-traitement peuvent être appliquées pour nettoyer, normaliser et structurer les données textuelles. Ces étapes visent à améliorer la qualité de l'analyse et la performance des modèles. Les utilitaires pour ces opérations se trouvent principalement dans `argumentation_analysis/utils/`.

### 1. Normalisation de Base

Des utilitaires de normalisation de texte sont disponibles dans [`argumentation_analysis/utils/core_utils/text_utils.py`](../../argumentation_analysis/utils/core_utils/text_utils.py:1). Ces fonctions permettent :

*   **Conversion en Minuscules :** Uniformisation de la casse du texte.
*   **Suppression des Accents :** Remplacement des caractères accentués par leurs équivalents non accentués (par exemple, "é" devient "e").
*   **Suppression de la Ponctuation :** Retrait des signes de ponctuation standard. Une attention particulière est portée aux apostrophes pour tenter de conserver leur rôle linguistique lorsque c'est pertinent.
*   **Normalisation des Espaces :** Remplacement des séquences d'espaces multiples (espaces, tabulations, sauts de ligne) par un seul espace, et suppression des espaces en début et fin de chaîne.

La fonction principale pour ces opérations est `normalize_text(text: str)` ([`../../argumentation_analysis/utils/core_utils/text_utils.py:17`](../../argumentation_analysis/utils/core_utils/text_utils.py:17)).

### 2. Tokenisation

Après la normalisation, le texte peut être segmenté en unités lexicales plus petites, appelées tokens (généralement des mots).

*   La fonction `tokenize_text(text: str)` ([`../../argumentation_analysis/utils/core_utils/text_utils.py:85`](../../argumentation_analysis/utils/core_utils/text_utils.py:85)) effectue d'abord une normalisation du texte puis le divise en tokens en se basant sur les espaces.

Ces tokens peuvent ensuite être utilisés pour des analyses statistiques, la création d'embeddings, ou d'autres traitements NLP.

### 3. Segmentation en Arguments

Pour des analyses au niveau des arguments, une première segmentation du texte source en unités argumentatives potentielles peut être réalisée.

*   La fonction `split_text_into_arguments(text: str)` ([`../../argumentation_analysis/utils/text_processing.py:12`](../../argumentation_analysis/utils/text_processing.py:12)) utilise des heuristiques basées sur la ponctuation (points, points d'exclamation, points d'interrogation suivis d'espaces ou de sauts de ligne) pour diviser un texte en segments qui pourraient correspondre à des arguments individuels.
*   Cette segmentation est une étape préliminaire et les "arguments" ainsi identifiés peuvent ensuite être affinés ou validés par des agents comme `ExtractAgent`.

### 4. Pré-traitement Spécifique aux Agents

*   **`ExtractAgent` et Textes Volumineux :** Comme détaillé dans la documentation de l'[`Argument Parser`](./argument_parser.md#pré-traitement-des-textes-volumineux-pour-lextraction), l'`ExtractAgent` implémente ses propres mécanismes de pré-traitement pour les textes longs, notamment la segmentation en blocs et la sélection de contexte pertinent avant de solliciter le LLM.

### 5. Étapes de Pré-traitement Avancées (Potentielles)

Bien que non explicitement implémentées comme des services centralisés actuellement, les étapes suivantes pourraient être considérées pour des besoins d'analyse plus poussés :

*   **Nettoyage HTML/XML :** Si les textes sources proviennent de pages web, la suppression des balises et la récupération du contenu textuel pur.
*   **Suppression des Mots Vides (Stop Words) :** Élimination des mots très fréquents et peu porteurs de sens (ex: "le", "la", "de", "est").
*   **Lemmatisation ou Racinisation (Stemming) :** Réduction des mots à leur forme de base (lemme) ou à leur racine pour regrouper les variantes flexionnelles.
*   **Reconnaissance d'Entités Nommées (NER) :** Identification et catégorisation des entités (personnes, lieux, organisations) dans le texte.

L'intégration de telles étapes dépendrait des exigences spécifiques des agents d'analyse et des tâches à accomplir. Elles pourraient être implémentées comme des services supplémentaires dans un répertoire dédié comme `argumentation_analysis/nlp/` ou en enrichissant davantage `argumentation_analysis/utils/`.

## Composants principaux

(Note: Les descriptions des composants ci-dessous se réfèrent principalement aux éléments situés dans `argumentation_analysis/` sauf indication contraire.)

### Module `argumentation_analysis`

#### Core (`argumentation_analysis/core/`) : Composants fondamentaux

Le module `core` contient les classes et fonctions fondamentales partagées par l'ensemble de l'application d'analyse rhétorique. Il assure la gestion de l'état, l'interaction avec les services externes (LLM, JVM) et définit les règles d'orchestration.

**Fichiers principaux :**
- `shared_state.py` : Définit la classe `RhetoricalAnalysisState` qui représente l'état mutable de l'analyse.
- `state_manager_plugin.py` : Définit la classe `StateManagerPlugin`, un plugin Semantic Kernel qui encapsule une instance de `RhetoricalAnalysisState`.
- `strategies.py` : Définit les stratégies d'orchestration pour `AgentGroupChat` de Semantic Kernel.
- `jvm_setup.py` : Gère l'interaction avec l'environnement Java pour l'intégration avec Tweety. Cette infrastructure est notamment utilisée par le [`Pont Tweety (Tweety Bridge)`](./tweety_bridge.md) pour l'intégration avec les bibliothèques de raisonnement logique de TweetyProject.
- `llm_service.py` : Gère la création du service LLM (OpenAI ou Azure).
- `communication/`: Contient les éléments pour la communication inter-agents.

**Responsabilités :**
- Gestion de l'état partagé entre les agents.
- Définition des stratégies d'orchestration.
- Intégration avec les services externes (LLM, JVM).
- Fourniture d'une API pour les agents pour accéder et modifier l'état partagé.
- Gestion de la communication entre les agents.

#### Agents (`argumentation_analysis/agents/`) : Agents spécialistes

Le module `agents` contient les définitions spécifiques à chaque agent IA participant à l'analyse rhétorique collaborative. Chaque agent est spécialisé dans un aspect particulier de l'analyse.

**Structure du module `agents` :**
- **`agents/core/`** : Contient les implémentations des agents spécialistes.
  - **Agent Project Manager (PM)** (`agents/core/pm/`): Orchestre l'analyse et coordonne les autres agents.
  - **Agent d'Analyse Informelle** (`agents/core/informal/`): Identifie les arguments et les sophismes dans le texte.
  - **Agent de Logique (ex-PL)** (`agents/core/logic/`): Gère la formalisation et l'interrogation logique via Tweety.
  - **Agent d'Extraction** (`agents/core/extract/`): Gère l'extraction et la réparation des extraits de texte.
- **`agents/extract/`** : Module de redirection vers `agents/core/extract/` pour maintenir la compatibilité.
- **`agents/tools/`** : Outils utilisés par les agents (ex: analyseur contextuel de sophismes, évaluateur de gravité, système d'encryption).
- **`agents/utils/`** : Utilitaires spécifiques aux agents (ex: `informal_optimization/`).
- **`agents/data/`** : Données spécifiques aux agents (ex: `argumentum_fallacies_taxonomy.csv`).

**Structure d'un agent (typique dans `agents/core/<type_agent>/`) :**
- `*_definitions.py` : Classes Plugin, fonction `setup_*_kernel`, constante `*_INSTRUCTIONS`.
- `prompts.py` : Constantes contenant les prompts sémantiques pour l'agent.
- `*_agent.py` : Classe principale de l'agent avec ses méthodes spécifiques.
- `README.md` : Documentation spécifique à l'agent.

**Mécanismes de redirection :**
Le projet utilise des mécanismes de redirection pour maintenir la compatibilité avec le code existant. Par exemple, le module `agents/extract` redirige vers `agents/core/extract` pour permettre aux importations existantes de continuer à fonctionner.

#### Services Internes (`argumentation_analysis/services/`) : Services partagés

Le module `services` au sein de `argumentation_analysis/` contient les services centralisés utilisés par les composants de ce module. Ils fournissent des fonctionnalités réutilisables.

**Services disponibles (exemples) :**
- **CacheService** (`cache_service.py`) : Service de mise en cache des textes sources.
- **CryptoService** (`crypto_service.py`) : Service de chiffrement et déchiffrement des données sensibles.
- **DefinitionService** (`definition_service.py`) : Service de gestion des définitions d'extraits.
- **ExtractService** (`extract_service.py`) : Service d'extraction de texte à partir de sources.
- **FetchService** (`fetch_service.py`) : Service de récupération de texte à partir de différentes sources.

**Responsabilités :**
- Fournir des fonctionnalités réutilisables pour les agents et l'orchestration au sein de `argumentation_analysis`.
- Gérer les interactions avec les ressources externes (fichiers, URLs, etc.) pour l'analyse.
- Assurer la persistance et la sécurité des données de l'analyse.

#### Orchestration (`argumentation_analysis/orchestration/`) : Mécanismes d'orchestration

Le module `orchestration` contient la logique principale qui orchestre la conversation collaborative entre les différents agents IA.

**Fichiers principaux (exemples) :**
- `analysis_runner.py` (ou équivalent) : Définit la fonction asynchrone principale pour exécuter la conversation d'analyse.

**Responsabilités :**
- Initialiser les instances locales de l'état, du kernel, des agents et des stratégies.
- Configurer le kernel avec le service LLM et les plugins des agents.
- Exécuter la conversation entre les agents.
- Suivre et afficher les tours de conversation et l'état final de l'analyse.

**Fonctionnalités avancées (exemples) :**
- Sélection dynamique des agents.
- Contrôle de verbosité des logs.
- Persistance des résultats.
- Gestion des erreurs.
- Collecte de métriques de performance.

#### UI (`argumentation_analysis/ui/`) : Interface utilisateur

Le module `ui` gère l'interface utilisateur (actuellement basée sur `ipywidgets` pour les notebooks) permettant de configurer et de lancer des analyses.

**Fichiers principaux (exemples) :**
- `app.py` : Logique principale de l'interface utilisateur.
- `config.py` : Configuration spécifique à l'UI.
- `utils.py`, `extract_utils.py`, `cache_utils.py`, `fetch_utils.py`, `file_operations.py`: Fonctions utilitaires pour l'UI.
- `extract_editor/`: Outils pour l'édition des marqueurs d'extraits.

**Responsabilités :**
- Permettre la sélection de sources de texte.
- Gérer l'extraction et la préparation du texte.
- Gérer le cache et la configuration des sources.
- Interagir avec le système d'orchestration.

#### Models (`argumentation_analysis/models/`) : Modèles de données

Le module `models` contient les modèles de données (souvent des classes Pydantic ou dataclasses) utilisés dans `argumentation_analysis`.

**Modèles disponibles (exemples) :**
- **ExtractDefinition** (`extract_definition.py`) : Classes pour les définitions d'extraits et de sources.
- **ExtractResult** (`extract_result.py`) : Résultat d'une extraction de texte.
- Autres modèles pour représenter les arguments, sophismes, états d'analyse, etc.

**Responsabilités :**
- Définir les structures de données.
- Fournir des méthodes pour manipuler ces structures.
- Assurer la sérialisation/désérialisation.

#### Utils (`argumentation_analysis/utils/`) : Utilitaires spécifiques

Le module `utils` dans `argumentation_analysis/` contient des fonctions utilitaires spécifiques à ce module.

**Structure (exemples) :**
- `core_utils/`: Utilitaires de base (fichiers, logs, système, texte).
- `dev_tools/`: Outils pour les développeurs (formatage, validation, refactoring).
- `extract_repair/`: Outils pour la réparation des bornes d'extraits.
- `metrics_calculator.py`, `report_generator.py`, `system_utils.py`.

**Responsabilités :**
- Fournir des fonctions utilitaires spécifiques à l'analyse rhétorique.
- Gérer la réparation d'extraits, calcul de métriques, génération de rapports.

#### Analytics (`argumentation_analysis/analytics/`) : Analyse de données

(Nouveau) Ce module est dédié à l'analyse des données issues des processus d'analyse rhétorique, calcul de statistiques, et potentiellement la visualisation de tendances.

#### NLP (`argumentation_analysis/nlp/`) : Traitement du Langage Naturel

(Nouveau) Ce module regroupe les composants spécifiquement liés au NLP qui sont utilisés au sein de `argumentation_analysis`, comme la gestion des embeddings, tokenisation avancée, etc.

#### Pipelines (`argumentation_analysis/pipelines/`) : Pipelines de traitement

(Nouveau) Ce module définit et gère des séquences d'opérations (pipelines) pour des tâches d'analyse complexes ou récurrentes.

#### Reporting (`argumentation_analysis/reporting/`) : Génération de rapports

(Nouveau) Ce module est responsable de la création de rapports structurés à partir des résultats d'analyse.

#### Service Setup (`argumentation_analysis/service_setup/`) : Configuration des services internes

(Nouveau) Ce module gère l'initialisation et la configuration des services internes utilisés par `argumentation_analysis`.
- `analysis_services.py`: Exemple de configuration de services d'analyse.

#### Config (`argumentation_analysis/config/`) : Configuration spécifique

Contient les fichiers de configuration propres au module `argumentation_analysis`.

#### Data (`argumentation_analysis/data/`) : Données spécifiques

Stocke les données nécessaires ou produites par le module `argumentation_analysis`, comme les corpus, les taxonomies, etc.

#### Notebooks (`argumentation_analysis/notebooks/`) : Notebooks Jupyter

Contient les notebooks Jupyter pour l'expérimentation, la démonstration, ou l'orchestration interactive des analyses.
- `ui/extract_marker_editor.ipynb`: Notebook pour l'éditeur de marqueurs.

#### Scripts (`argumentation_analysis/scripts/`) : Scripts spécifiques au module

Regroupe les scripts dédiés à des tâches spécifiques du module `argumentation_analysis`.

#### Tests (`argumentation_analysis/tests/`) : Tests spécifiques au module

Contient les tests unitaires et d'intégration qui valident le fonctionnement des composants du module `argumentation_analysis`.

### Modules et dossiers à la racine du projet

#### Project Core (`project_core/`) : Utilitaires de projet

Ce module contient des utilitaires et des composants fondamentaux qui ne sont pas spécifiques à l'analyse rhétorique mais plutôt au projet dans son ensemble (ex: outils de développement, intégration).

#### Config (`config/`) : Configuration globale

Ce dossier à la racine contient les fichiers de configuration globaux du projet.

#### Docs (`docs/`) : Documentation

Contient toute la documentation du projet, y compris ce fichier, les guides, les rapports d'architecture, etc.

#### Tests (`tests/`) : Tests globaux

Ce dossier à la racine contient les tests qui couvrent plusieurs modules ou l'intégration globale du projet. Il peut inclure des tests fonctionnels, des mocks globaux, et des fixtures partagées.
- `conftest.py` (racine ou ici) : Fixtures Pytest globales.
- Organisation par type de test (functional, integration, unit) ou par module testé.

#### Scripts (`scripts/`) : Scripts généraux

Ce dossier à la racine contient des scripts pour des tâches générales affectant l'ensemble du projet.

#### Services (`services/`) : API Web

Ce dossier à la racine est dédié à l'exposition des fonctionnalités du projet via une API Web.
- `web_api/`: Contient l'implémentation de l'API (ex: en utilisant Flask ou FastAPI), ses modèles de données et ses tests.

#### Libs (`libs/`) : Bibliothèques externes et natives

Ce dossier contient des bibliothèques tierces qui sont incluses directement dans le projet, notamment des binaires natifs ou des versions spécifiques de bibliothèques comme Tweety.

#### Examples (`examples/`) : Exemples globaux

Contient des exemples d'utilisation du projet dans son ensemble ou des exemples de données.

#### Archives (`_archives/`) : Archives

Contient des sauvegardes ou des versions archivées de fichiers ou de modules. Ce dossier n'est généralement pas suivi par Git.

## Flux de données

(Cette section semble globalement à jour et ne nécessite pas de modifications majeures basées sur la structure des fichiers.)

Le flux de données dans le système suit un cycle de vie bien défini, depuis l'ingestion des données jusqu'à la présentation des résultats :

1.  **Ingestion des données** : Le texte à analyser est fourni via l'interface utilisateur ou un script.
    *   L'utilisateur sélectionne une source de texte (bibliothèque prédéfinie, URL, fichier local, texte direct).
    *   Le texte est extrait et préparé par les services appropriés (principalement dans `argumentation_analysis/services/` et `argumentation_analysis/ui/`).

2.  **Extraction des arguments** : L'agent Extract (`argumentation_analysis/agents/core/extract/`) identifie les arguments présents dans le texte.
    *   L'agent utilise des marqueurs de début et de fin pour isoler les extraits pertinents.
    *   Les extraits sont stockés dans l'état partagé (`argumentation_analysis/core/shared_state.py`).

3.  **Analyse informelle** : L'agent Informal (`argumentation_analysis/agents/core/informal/`) analyse les arguments pour détecter les sophismes et évaluer leur qualité.
    *   L'agent utilise des outils spécialisés (dans `argumentation_analysis/agents/tools/`).
    *   Les résultats de l'analyse sont stockés dans l'état partagé.

4.  **Analyse formelle** : L'agent de Logique (`argumentation_analysis/agents/core/logic/`) formalise les arguments en logique propositionnelle et vérifie leur validité.
    *   L'agent utilise la bibliothèque Tweety (via `argumentation_analysis/core/jvm_setup.py` et `libs/tweety/`).
    *   Les résultats de l'analyse sont stockés dans l'état partagé.

5.  **Synthèse des résultats** : Les résultats des différents agents sont combinés dans l'état partagé.
    *   L'agent PM (`argumentation_analysis/agents/core/pm/`) coordonne la synthèse des résultats.
    *   Les résultats sont structurés pour faciliter leur présentation.

6.  **Présentation** : Les résultats sont formatés et présentés à l'utilisateur.
    *   Les résultats peuvent être visualisés via l'interface utilisateur (`argumentation_analysis/ui/`) ou exportés (via `argumentation_analysis/reporting/` ou des scripts).

```
┌───────────────┐     ┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│  Ingestion    │     │  Extraction   │     │    Analyse    │     │    Analyse    │
│  des données  │────▶│ des arguments │────▶│   informelle  │────▶│    formelle   │
└───────────────┘     └───────────────┘     └───────────────┘     └───────────────┘
                                                                          │
┌───────────────┐                           ┌───────────────┐             │
│ Présentation  │◀───────────────────────────│  Synthèse    │◀────────────┘
│ des résultats │                           │ des résultats │
└───────────────┘                           └───────────────┘
```

## Interfaces entre composants

(Cette section semble globalement à jour et ne nécessite pas de modifications majeures basées sur la structure des fichiers.)

Les interfaces entre les différents composants du système sont définies de manière claire pour assurer une communication efficace et une séparation des responsabilités.

### Interface État Partagé - Agents
(Principalement dans `argumentation_analysis/core/` et `argumentation_analysis/agents/`)

L'interface entre l'état partagé et les agents est définie par le `StateManagerPlugin`, qui expose des fonctions natives aux agents pour lire et écrire dans l'état partagé :

- **Lecture** : `get_current_state_snapshot`
- **Écriture** :
  - `add_task` : Ajouter une tâche à l'état
  - `add_argument` : Ajouter un argument identifié
  - `add_fallacy` : Ajouter un sophisme détecté
  - `add_belief_set` : Ajouter un ensemble de croyances logiques
  - `log_query_result` : Enregistrer le résultat d'une requête
  - `add_answer` : Ajouter une réponse d'agent
  - `set_final_conclusion` : Définir la conclusion finale
  - `designate_next_agent` : Désigner le prochain agent à intervenir

### Interface Orchestration - Agents
(Principalement dans `argumentation_analysis/orchestration/` et `argumentation_analysis/core/strategies.py`)

L'interface entre l'orchestration et les agents est définie par les stratégies d'orchestration :

- **SimpleTerminationStrategy** : Détermine quand la conversation doit se terminer.
- **DelegatingSelectionStrategy** : Détermine quel agent doit intervenir à chaque tour.

### Interface Services Internes (`argumentation_analysis/services/`) - Agents

Les services internes exposent des API claires que les agents peuvent utiliser pour accéder aux fonctionnalités partagées :

- **CacheService** : API pour la mise en cache des textes sources.
- **CryptoService** : API pour le chiffrement et le déchiffrement des données.
- **DefinitionService** : API pour la gestion des définitions d'extraits.
- **ExtractService** : API pour l'extraction de texte à partir de sources.
- **FetchService** : API pour la récupération de texte à partir de différentes sources.

### Interface UI (`argumentation_analysis/ui/`) - Orchestration

L'interface entre l'UI et l'orchestration est définie par la fonction `configure_analysis_task` (ou équivalent dans `app.py`) qui retourne le texte préparé à l'orchestrateur principal.

### Interface Agents - Services Externes
(Principalement `argumentation_analysis/core/llm_service.py` et `argumentation_analysis/core/jvm_setup.py`)

Les agents interagissent avec des services externes via des interfaces dédiées :

- **LLM Service** : Interface pour interagir avec les modèles de langage (OpenAI, Azure).
- **JVM (Tweety)** : Interface pour interagir avec la bibliothèque Tweety via JPype.

## Extensibilité

(Cette section semble globalement à jour et les chemins modifiés reflètent la nouvelle structure.)

Le système est conçu pour être facilement extensible, permettant l'ajout de nouveaux composants et fonctionnalités sans modifier le code existant.

### Ajout de nouveaux agents

Pour ajouter un nouvel agent au système, il suffit de :

1.  Créer un nouveau sous-répertoire dans `argumentation_analysis/agents/core/` avec le nom de l'agent (ex: `argumentation_analysis/agents/core/new_agent/`).
2.  Implémenter les fichiers nécessaires (`*_definitions.py`, `prompts.py`, `*_agent.py`).
3.  Mettre à jour l'orchestrateur principal (dans `argumentation_analysis/orchestration/`) pour intégrer le nouvel agent.
4.  Si nécessaire, créer un module de redirection dans `argumentation_analysis/agents/` pour maintenir la compatibilité.

### Ajout de nouveaux outils d'analyse

Pour ajouter un nouvel outil d'analyse, il suffit de :

1.  Créer un nouveau fichier dans `argumentation_analysis/agents/tools/` (ou un sous-dossier approprié comme `analysis/`).
2.  Implémenter les classes et fonctions nécessaires.
3.  Mettre à jour les agents (dans `argumentation_analysis/agents/core/`) qui utiliseront cet outil.

### Ajout de nouveaux services internes

Pour ajouter un nouveau service interne à `argumentation_analysis`, il suffit de :

1.  Créer un nouveau fichier dans `argumentation_analysis/services/` avec le nom du service.
2.  Implémenter les classes et fonctions nécessaires.
3.  Mettre à jour les composants (agents, orchestration) qui utiliseront ce service.
4.  Enregistrer et configurer le service dans `argumentation_analysis/service_setup/` si nécessaire.

### Ajout de nouvelles stratégies d'orchestration

Pour ajouter une nouvelle stratégie d'orchestration, il suffit de :

1.  Créer une nouvelle classe dans `argumentation_analysis/core/strategies.py`.
2.  Implémenter les méthodes nécessaires.
3.  Mettre à jour l'orchestrateur principal (dans `argumentation_analysis/orchestration/`) pour utiliser la nouvelle stratégie.

### Ajout de nouvelles fonctionnalités UI

Pour ajouter une nouvelle fonctionnalité à l'interface utilisateur, il suffit de :

1.  Mettre à jour les fichiers appropriés dans `argumentation_analysis/ui/`.
2.  Implémenter les widgets et callbacks nécessaires.
3.  Mettre à jour la logique principale de l'UI (ex: `argumentation_analysis/ui/app.py`) si nécessaire.

### Exemples d'extensions possibles

- **Nouveaux agents logiques** : Agents pour la logique du premier ordre, la logique modale, etc. (dans `argumentation_analysis/agents/core/logic/` ou nouveau sous-dossier).
- **Agents de tâches spécifiques** : Agents pour le résumé, l'extraction d'entités, etc. (nouveaux sous-dossiers dans `argumentation_analysis/agents/core/`).
- **Intégration d'outils externes** : Web, bases de données, etc. (via de nouveaux services dans `argumentation_analysis/services/` ou des outils dans `argumentation_analysis/agents/tools/`).
- **Interface web avancée** : Alternative type Gradio/Streamlit pour visualisation/interaction post-analyse (pourrait être dans `services/web_api/` ou un nouveau module UI).
- **Visualisation des résultats** : Amélioration de la visualisation des résultats d'analyse (dans `argumentation_analysis/reporting/` ou `argumentation_analysis/ui/`).
- **État RDF/KG** : Explorer `rdflib` ou base graphe pour état plus sémantique (impacterait `argumentation_analysis/core/shared_state.py` et `argumentation_analysis/models/`).