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
argumentation_analysis/
├── __init__.py
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