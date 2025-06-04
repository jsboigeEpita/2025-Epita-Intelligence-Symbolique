# Rapport de Revue et Proposition de Mise à Jour pour docs/composants/structure_projet.md

## 1. Contenu actuel de docs/composants/structure_projet.md (pour référence)

```markdown
# Structure du Projet et Composants du Système d'Orchestration Agentique d'Analyse Rhétorique

## Table des matières

- [Vue d'ensemble](#vue-densemble)
- [Organisation des dossiers](#organisation-des-dossiers)
- [Composants principaux](#composants-principaux)
  - [Core : Composants fondamentaux](#core--composants-fondamentaux)
  - [Agents : Agents spécialistes](#agents--agents-spécialistes)
  - [Services : Services partagés](#services--services-partagés)
  - [Orchestration : Mécanismes d'orchestration](#orchestration--mécanismes-dorchestation)
  - [UI : Interface utilisateur](#ui--interface-utilisateur)
  - [Models : Modèles de données](#models--modèles-de-données)
  - [Utils : Utilitaires](#utils--utilitaires)
  - [Tests : Tests unitaires et d'intégration](#tests--tests-unitaires-et-dintégration)
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

Le projet est organisé en plusieurs modules principaux, chacun ayant une responsabilité spécifique :

```
argumentiation_analysis/
├── __init__.py
├── main_orchestrator.ipynb      # Notebook interactif pour l'orchestration
├── main_orchestrator.py         # Script principal d'orchestration
├── paths.py                     # Gestion centralisée des chemins du projet
├── run_analysis.py              # Script pour lancer l'analyse argumentative
├── run_extract_editor.py        # Script pour lancer l'éditeur de marqueurs d'extraits
├── run_extract_repair.py        # Script pour lancer la réparation des bornes défectueuses
├── run_orchestration.py         # Script pour lancer l'orchestration des agents
├── run_tests.py                 # Script pour exécuter les tests
├── requirements.txt             # Dépendances Python
├── agents/                      # Agents spécialistes
│   ├── core/                    # Implémentations des agents spécialistes
│   ├── extract/                 # Module de redirection vers agents.core.extract
│   └── tools/                   # Outils utilisés par les agents
├── config/                      # Fichiers de configuration
│   └── .env.template            # Template pour les variables d'environnement
├── core/                        # Composants fondamentaux
│   ├── communication/           # Système de communication entre agents
│   ├── jvm_setup.py             # Configuration de l'environnement JVM
│   ├── llm_service.py           # Service d'accès aux modèles de langage
│   ├── shared_state.py          # Gestion de l'état partagé
│   ├── state_manager_plugin.py  # Plugin pour la gestion de l'état
│   └── strategies.py            # Stratégies d'orchestration
├── data/                        # Données et ressources
├── libs/                        # Bibliothèques externes
│   └── native/                  # Bibliothèques natives
├── models/                      # Modèles de données
├── orchestration/               # Mécanismes d'orchestration
├── results/                     # Résultats des analyses
├── services/                    # Services partagés
│   ├── cache_service.py         # Service de mise en cache
│   ├── crypto_service.py        # Service de chiffrement
│   ├── definition_service.py    # Service de gestion des définitions
│   ├── extract_service.py       # Service d'extraction de texte
│   └── fetch_service.py         # Service de récupération de texte
├── tests/                       # Tests unitaires et d'intégration
├── ui/                          # Interface utilisateur
│   ├── extract_editor/          # Éditeur de marqueurs d'extraits
│   ├── app.py                   # Application principale
│   ├── config.py                # Configuration de l'interface
│   ├── extract_utils.py         # Utilitaires pour l'extraction
│   └── utils.py                 # Utilitaires généraux pour l'UI
└── utils/                       # Utilitaires généraux
    └── extract_repair/          # Outils de réparation des extraits
```

Cette organisation modulaire permet une séparation claire des responsabilités et facilite la maintenance et l'extension du système.

## Composants principaux

### Core : Composants fondamentaux

Le module `core` contient les classes et fonctions fondamentales partagées par l'ensemble de l'application. Il assure la gestion de l'état, l'interaction avec les services externes (LLM, JVM) et définit les règles d'orchestration.

**Fichiers principaux :**
- `shared_state.py` : Définit la classe `RhetoricalAnalysisState` qui représente l'état mutable de l'analyse.
- `state_manager_plugin.py` : Définit la classe `StateManagerPlugin`, un plugin Semantic Kernel qui encapsule une instance de `RhetoricalAnalysisState`.
- `strategies.py` : Définit les stratégies d'orchestration pour `AgentGroupChat` de Semantic Kernel.
- `jvm_setup.py` : Gère l'interaction avec l'environnement Java pour l'intégration avec Tweety.
- `llm_service.py` : Gère la création du service LLM (OpenAI ou Azure).

**Responsabilités :**
- Gestion de l'état partagé entre les agents
- Définition des stratégies d'orchestration
- Intégration avec les services externes (LLM, JVM)
- Fourniture d'une API pour les agents pour accéder et modifier l'état partagé

### Agents : Agents spécialistes

Le module `agents` contient les définitions spécifiques à chaque agent IA participant à l'analyse rhétorique collaborative. Chaque agent est spécialisé dans un aspect particulier de l'analyse.

**Structure du module agents :**
- **`agents/core/`** : Contient les implémentations des agents spécialistes
  - **Agent Project Manager (PM)** : Orchestre l'analyse et coordonne les autres agents
  - **Agent d'Analyse Informelle** : Identifie les arguments et les sophismes dans le texte
  - **Agent de Logique Propositionnelle (PL)** : Gère la formalisation et l'interrogation logique via Tweety
  - **Agent d'Extraction** : Gère l'extraction et la réparation des extraits de texte
- **`agents/extract/`** : Module de redirection vers `agents.core.extract` pour maintenir la compatibilité
- **`agents/tools/`** : Outils utilisés par les agents
  - Outils d'analyse des résultats (analyseur contextuel de sophismes, évaluateur de gravité des sophismes, etc.)
  - Système d'encryption pour sécuriser les données sensibles
- **`agents/utils/`** : Utilitaires spécifiques aux agents
  - Outils d'optimisation pour l'agent d'analyse informelle

**Structure d'un agent :**
Chaque agent est généralement composé de :
- `*_definitions.py` : Classes Plugin, fonction `setup_*_kernel`, constante `*_INSTRUCTIONS`
- `prompts.py` : Constantes contenant les prompts sémantiques pour l'agent
- `*_agent.py` : Classe principale de l'agent avec ses méthodes spécifiques
- `README.md` : Documentation spécifique à l'agent

**Mécanismes de redirection :**
Le projet utilise des mécanismes de redirection pour maintenir la compatibilité avec le code existant. Par exemple, le module `agents/extract` redirige vers `agents/core/extract` pour permettre aux importations existantes de continuer à fonctionner.

### Services : Services partagés

Le module `services` contient les services centralisés utilisés dans le projet. Les services fournissent des fonctionnalités réutilisables pour manipuler les extraits, accéder aux sources, et gérer les données.

**Services disponibles :**
- **CacheService** (`cache_service.py`) : Service de mise en cache des textes sources.
- **CryptoService** (`crypto_service.py`) : Service de chiffrement et déchiffrement des données sensibles.
- **DefinitionService** (`definition_service.py`) : Service de gestion des définitions d'extraits.
- **ExtractService** (`extract_service.py`) : Service d'extraction de texte à partir de sources.
- **FetchService** (`fetch_service.py`) : Service de récupération de texte à partir de différentes sources.

**Responsabilités :**
- Fournir des fonctionnalités réutilisables pour les agents et l'orchestration
- Gérer les interactions avec les ressources externes (fichiers, URLs, etc.)
- Assurer la persistance et la sécurité des données

### Orchestration : Mécanismes d'orchestation

Le module `orchestration` contient la logique principale qui orchestre la conversation collaborative entre les différents agents IA.

**Fichiers principaux :**
- `analysis_runner.py` : Définit la fonction asynchrone principale `run_analysis_conversation(texte_a_analyser, llm_service)`.

**Responsabilités :**
- Initialiser les instances locales de l'état, du kernel, des agents et des stratégies
- Configurer le kernel avec le service LLM et les plugins des agents
- Exécuter la conversation entre les agents
- Suivre et afficher les tours de conversation et l'état final de l'analyse

**Fonctionnalités avancées :**
- Sélection dynamique des agents à inclure dans l'analyse
- Contrôle de verbosité des logs
- Persistance des résultats
- Gestion des erreurs
- Collecte de métriques de performance

### UI : Interface utilisateur

Le module `ui` gère l'interface utilisateur (basée sur `ipywidgets`) permettant à l'utilisateur de configurer la tâche d'analyse avant de lancer la conversation multi-agents.

**Fichiers principaux :**
- `app.py` : Définit la fonction principale `configure_analysis_task` qui crée les widgets, définit les callbacks et assemble l'interface.
- `config.py` : Contient les constantes (URLs, chemins), le chargement de la clé de chiffrement et la définition des sources par défaut.
- `utils.py` : Fonctions utilitaires pour le cache, le chiffrement/déchiffrement, etc.
- `extract_utils.py` : Fonctions utilitaires spécifiques à l'extraction de texte.

**Sous-modules :**
- `extract_editor/` : Outils pour l'édition des marqueurs d'extraits.

**Responsabilités :**
- Permettre à l'utilisateur de sélectionner une source de texte
- Extraire le contenu textuel via Jina Reader ou Apache Tika
- Appliquer des marqueurs de début/fin pour isoler un extrait spécifique
- Gérer un cache fichier pour les textes récupérés depuis des sources externes
- Charger/Sauvegarder la configuration des sources prédéfinies
- Retourner le texte final préparé au script orchestrateur principal

### Models : Modèles de données

Le module `models` contient les modèles de données utilisés dans le projet. Les modèles définissent les structures de données et les classes qui représentent les concepts clés du projet.

**Modèles disponibles :**
- **ExtractDefinition** (`extract_definition.py`) : Classes pour représenter les définitions d'extraits et de sources.
  - `Extract` : Représente un extrait individuel avec ses marqueurs de début et de fin.
  - `SourceDefinition` : Représente une source de texte (URL, fichier, etc.) et ses extraits associés.
  - `ExtractDefinitions` : Collection de définitions de sources.
- **ExtractResult** (`extract_result.py`) : Représente le résultat d'une extraction de texte à partir d'une source.

**Responsabilités :**
- Définir les structures de données utilisées dans le projet
- Fournir des méthodes pour manipuler ces structures
- Assurer la sérialisation/désérialisation des données

### Utils : Utilitaires

Le module `utils` contient des fonctions utilitaires générales non spécifiques à un domaine particulier de l'application.

**Fichiers principaux :**
- `system_utils.py` : Fonctions utilitaires système.

**Sous-modules :**
- `extract_repair/` : Outils pour la réparation des bornes d'extraits défectueuses.

**Responsabilités :**
- Fournir des fonctions utilitaires générales
- Gérer la réparation des bornes d'extraits défectueuses

### Tests : Tests unitaires et d'intégration

Le module `tests` contient les tests unitaires et d'intégration pour le projet. Les tests sont organisés par module et utilisent principalement le framework `pytest`, avec support pour `unittest`.

**Organisation des tests :**
- Tests des composants fondamentaux (Core)
- Tests des modèles
- Tests des services
- Tests des agents
- Tests des scripts
- Tests d'orchestration
- Tests d'intégration

**Scripts d'exécution des tests :**
- `run_tests.py` : Script pour exécuter tous les tests avec pytest.
- `run_tests.ps1` : Script PowerShell pour exécuter tous les tests.
- `run_coverage.py` : Script pour exécuter les tests avec couverture de code.
- `async_test_case.py` : Classe de base pour les tests asynchrones.
- `conftest.py` : Configuration et fixtures pour pytest.

**Responsabilités :**
- Vérifier le bon fonctionnement des composants du système
- Assurer la qualité du code
- Détecter les régressions
- Documenter le comportement attendu des composants

## Flux de données

Le flux de données dans le système suit un cycle de vie bien défini, depuis l'ingestion des données jusqu'à la présentation des résultats :

1. **Ingestion des données** : Le texte à analyser est fourni via l'interface utilisateur ou un script.
   - L'utilisateur sélectionne une source de texte (bibliothèque prédéfinie, URL, fichier local, texte direct).
   - Le texte est extrait et préparé par les services appropriés.

2. **Extraction des arguments** : L'agent Extract identifie les arguments présents dans le texte.
   - L'agent utilise des marqueurs de début et de fin pour isoler les extraits pertinents.
   - Les extraits sont stockés dans l'état partagé pour être utilisés par les autres agents.

3. **Analyse informelle** : L'agent Informal analyse les arguments pour détecter les sophismes et évaluer leur qualité.
   - L'agent utilise des outils spécialisés comme l'analyseur contextuel de sophismes et l'évaluateur de gravité des sophismes.
   - Les résultats de l'analyse sont stockés dans l'état partagé.

4. **Analyse formelle** : L'agent PL formalise les arguments en logique propositionnelle et vérifie leur validité.
   - L'agent utilise la bibliothèque Tweety via JPype pour la formalisation et la vérification logique.
   - Les résultats de l'analyse sont stockés dans l'état partagé.

5. **Synthèse des résultats** : Les résultats des différents agents sont combinés dans l'état partagé.
   - L'agent PM coordonne la synthèse des résultats.
   - Les résultats sont structurés pour faciliter leur présentation.

6. **Présentation** : Les résultats sont formatés et présentés à l'utilisateur.
   - Les résultats peuvent être visualisés via l'interface utilisateur ou exportés dans un format approprié.

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

Les interfaces entre les différents composants du système sont définies de manière claire pour assurer une communication efficace et une séparation des responsabilités.

### Interface État Partagé - Agents

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

L'interface entre l'orchestration et les agents est définie par les stratégies d'orchestration :

- **SimpleTerminationStrategy** : Détermine quand la conversation doit se terminer.
- **DelegatingSelectionStrategy** : Détermine quel agent doit intervenir à chaque tour.

### Interface Services - Agents

Les services exposent des API claires que les agents peuvent utiliser pour accéder aux fonctionnalités partagées :

- **CacheService** : API pour la mise en cache des textes sources.
- **CryptoService** : API pour le chiffrement et le déchiffrement des données.
- **DefinitionService** : API pour la gestion des définitions d'extraits.
- **ExtractService** : API pour l'extraction de texte à partir de sources.
- **FetchService** : API pour la récupération de texte à partir de différentes sources.

### Interface UI - Orchestration

L'interface entre l'UI et l'orchestration est définie par la fonction `configure_analysis_task` qui retourne le texte préparé à l'orchestrateur principal.

### Interface Agents - Services Externes

Les agents interagissent avec des services externes via des interfaces dédiées :

- **LLM Service** : Interface pour interagir avec les modèles de langage (OpenAI, Azure).
- **JVM (Tweety)** : Interface pour interagir avec la bibliothèque Tweety via JPype.

## Extensibilité

Le système est conçu pour être facilement extensible, permettant l'ajout de nouveaux composants et fonctionnalités sans modifier le code existant.

### Ajout de nouveaux agents

Pour ajouter un nouvel agent au système, il suffit de :

1. Créer un nouveau sous-répertoire dans `agents/core/` avec le nom de l'agent
2. Implémenter les fichiers nécessaires (`*_definitions.py`, `prompts.py`, `*_agent.py`)
3. Mettre à jour l'orchestrateur principal pour intégrer le nouvel agent
4. Si nécessaire, créer un module de redirection dans `agents/` pour maintenir la compatibilité

### Ajout de nouveaux outils d'analyse

Pour ajouter un nouvel outil d'analyse, il suffit de :

1. Créer un nouveau fichier dans `agents/tools/analysis/` avec le nom de l'outil
2. Implémenter les classes et fonctions nécessaires
3. Mettre à jour les agents qui utiliseront cet outil

### Ajout de nouveaux services

Pour ajouter un nouveau service, il suffit de :

1. Créer un nouveau fichier dans `services/` avec le nom du service.
2. Implémenter les classes et fonctions nécessaires.
3. Mettre à jour les composants qui utiliseront ce service.

### Ajout de nouvelles stratégies d'orchestration

Pour ajouter une nouvelle stratégie d'orchestration, il suffit de :

1. Créer une nouvelle classe dans `core/strategies.py`.
2. Implémenter les méthodes nécessaires.
3. Mettre à jour l'orchestrateur principal pour utiliser la nouvelle stratégie.

### Ajout de nouvelles fonctionnalités UI

Pour ajouter une nouvelle fonctionnalité à l'interface utilisateur, il suffit de :

1. Mettre à jour les fichiers appropriés dans `ui/`.
2. Implémenter les widgets et callbacks nécessaires.
3. Mettre à jour la fonction `configure_analysis_task` si nécessaire.

### Exemples d'extensions possibles

- **Nouveaux agents logiques** : Agents pour la logique du premier ordre, la logique modale, etc.
- **Agents de tâches spécifiques** : Agents pour le résumé, l'extraction d'entités, etc.
- **Intégration d'outils externes** : Web, bases de données, etc.
- **Interface web avancée** : Alternative type Gradio/Streamlit pour visualisation/interaction post-analyse.
- **Visualisation des résultats** : Amélioration de la visualisation des résultats d'analyse (graphes, tableaux, etc.).
- **État RDF/KG** : Explorer `rdflib` ou base graphe pour état plus sémantique.
```

## 2. Résumé de la structure de projet observée (principaux répertoires et leur rôle)

*   **Racine du projet (`./`) :**
    *   `argumentation_analysis/`: Module principal contenant le cœur de l'application d'analyse rhétorique.
    *   `project_core/`: Utilitaires de développement, d'intégration et potentiellement des aspects fondamentaux non spécifiques à l'analyse argumentative elle-même.
    *   `config/`: Fichiers de configuration globaux pour le projet (ex: `pytest.ini`, `.env.template`, `requirements-test.txt`).
    *   `docs/`: Documentation du projet.
    *   `tests/`: Ensemble des tests du projet (unitaires, intégration, fonctionnels, mocks, fixtures).
    *   `scripts/`: Scripts pour diverses tâches (setup, maintenance, nettoyage, reporting, exécution de workflows).
    *   `services/`: Exposition de fonctionnalités via une API Web (actuellement `web_api/`).
    *   `libs/`: Bibliothèques tierces, incluant des binaires natifs (ex: `lingeling.dll`) et une copie de Tweety.
    *   `examples/`: Exemples d'utilisation ou de données pour le projet global.
    *   `_archives/`: Sauvegardes et versions archivées de fichiers ou de modules.
    *   `htmlcov_demonstration/`: Rapports de couverture de code HTML (générés).
    *   Autres fichiers : `README.md`, `requirements.txt` (dépendances principales), `setup.py`, scripts d'environnement (`environment.yml`, `setup_project_env.ps1`/`.sh`), fichiers de configuration d'outils (`pytest.ini`, `conftest.py`).

*   **Dans `argumentation_analysis/` :**
    *   `agents/`: Implémentation des agents IA spécialisés et de leurs outils.
    *   `analytics/`: (Nouveau) Modules pour l'analyse de données, la génération de statistiques ou de métriques liées aux analyses.
    *   `config/`: Fichiers de configuration spécifiques au module `argumentation_analysis`.
    *   `core/`: Composants fondamentaux de l'application d'analyse (gestion de l'état, communication inter-agents, interaction LLM/JVM).
    *   `data/`: Données utilisées ou générées par `argumentation_analysis` (corpus, ressources).
    *   `examples/`: Exemples spécifiques à `argumentation_analysis`.
    *   `mocks/`: Mocks utilisés pour les tests internes à `argumentation_analysis`.
    *   `models/`: Définition des structures de données (modèles Pydantic, etc.) utilisées dans `argumentation_analysis`.
    *   `nlp/`: (Nouveau) Composants liés au traitement du langage naturel (NLP) spécifiques à l'analyse.
    *   `notebooks/`: Notebooks Jupyter pour l'expérimentation, l'orchestration interactive ou la démonstration.
    *   `orchestration/`: Logique d'orchestration de la collaboration entre agents.
    *   `pipelines/`: (Nouveau) Définition de pipelines de traitement ou d'analyse.
    *   `reporting/`: (Nouveau) Outils pour générer des rapports spécifiques aux analyses effectuées.
    *   `scripts/`: Scripts spécifiques aux opérations ou workflows de `argumentation_analysis`.
    *   `service_setup/`: (Nouveau) Configuration et initialisation des services internes à `argumentation_analysis`.
    *   `services/`: Services internes partagés par les composants de `argumentation_analysis` (ex: cache, crypto, extraction).
    *   `tests/`: Tests spécifiques au module `argumentation_analysis`.
    *   `ui/`: Composants de l'interface utilisateur (basée sur `ipywidgets` ou autre).
    *   `utils/`: Fonctions et modules utilitaires spécifiques à `argumentation_analysis` (réparation d'extraits, utilitaires de base, outils de développement).

## 3. Résumé détaillé des inconsistances trouvées entre le document et la réalité

*   **Arborescence principale :** Le document actuel présente une arborescence sous `argumentation_analysis/` qui mélange des éléments de la racine du projet (ex: `requirements.txt` listé sous `argumentation_analysis/`) et des éléments réellement dans `argumentation_analysis/`. La distinction entre le scope global du projet et le module `argumentation_analysis` n'est pas claire dans l'arborescence fournie.
*   **Dossiers racine manquants dans le document :**
    *   `project_core/`: Son rôle et son contenu ne sont pas décrits.
    *   `services/` (à la racine, contenant `web_api/`): Ce service d'API Web n'est pas mentionné.
    *   `libs/`: Bien que mentionné sous `argumentation_analysis/` dans le document, il semble être un dossier racine important contenant des dépendances natives et Tweety.
    *   `_archives/`, `examples/` (racine), `htmlcov_demonstration/`: Non mentionnés, mais pourraient l'être brièvement pour leur rôle.
*   **Fichiers à la racine de `argumentation_analysis/` :** Le document liste plusieurs scripts et notebooks (`main_orchestrator.ipynb`, `run_analysis.py`, etc.) directement sous `argumentation_analysis/`. L'exploration via `list_files` suggère que ces fichiers pourraient maintenant résider dans des sous-dossiers plus spécifiques comme `argumentation_analysis/scripts/` ou `argumentation_analysis/notebooks/`.
*   **Nouveaux sous-dossiers dans `argumentation_analysis/` non documentés :**
    *   `analytics/`
    *   `mocks/` (distinct du `tests/mocks/` global)
    *   `nlp/`
    *   `pipelines/`
    *   `reporting/`
    *   `service_setup/`
*   **Contenu de `argumentation_analysis/utils/` :** Le document mentionne principalement `extract_repair/` et `system_utils.py`. La structure réelle est plus riche avec des sous-dossiers comme `core_utils/` et `dev_tools/`.
*   **Dossier `results/` :** Mentionné dans le document sous `argumentation_analysis/`, mais non visible dans les listages de fichiers. Il est possible qu'il soit créé dynamiquement ou qu'il soit actuellement vide. Il est préférable de le mentionner comme un dossier potentiellement créé.
*   **Dossier `tests/` :** Le document mentionne `tests/` sous `argumentation_analysis/` et décrit également un module `Tests` plus global. La relation et la spécificité de `argumentation_analysis/tests/` par rapport au `tests/` racine doivent être clarifiées.
*   **Scripts d'exécution des tests :** Listés dans la section `Tests` du document (`run_tests.py`, `run_tests.ps1`), ils se trouvent probablement à la racine du projet ou dans le dossier `scripts/` principal, ou même dans `argumentation_analysis/scripts/` ou `argumentation_analysis/tests/` pour certains. Leur emplacement exact doit être vérifié et documenté correctement.

## 4. Propositions de modifications complètes pour docs/composants/structure_projet.md

```markdown
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

## Composants principaux

(Note: Les descriptions des composants ci-dessous se réfèrent principalement aux éléments situés dans `argumentation_analysis/` sauf indication contraire.)

### Module `argumentation_analysis`

#### Core (`argumentation_analysis/core/`) : Composants fondamentaux

Le module `core` contient les classes et fonctions fondamentales partagées par l'ensemble de l'application d'analyse rhétorique. Il assure la gestion de l'état, l'interaction avec les services externes (LLM, JVM) et définit les règles d'orchestration.

**Fichiers principaux :**
- `shared_state.py` : Définit la classe `RhetoricalAnalysisState` qui représente l'état mutable de l'analyse.
- `state_manager_plugin.py` : Définit la classe `StateManagerPlugin`, un plugin Semantic Kernel qui encapsule une instance de `RhetoricalAnalysisState`.
- `strategies.py` : Définit les stratégies d'orchestration pour `AgentGroupChat` de Semantic Kernel.
- `jvm_setup.py` : Gère l'interaction avec l'environnement Java pour l'intégration avec Tweety.
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