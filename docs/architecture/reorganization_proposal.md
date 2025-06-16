# Proposition de Réorganisation de l'Architecture du Projet

## 1. Introduction

Ce document présente une proposition de réorganisation de l'architecture du projet "2025-Epita-Intelligence-Symbolique". L'objectif principal est d'adresser les incohérences et les problèmes potentiels identifiés dans le rapport d'analyse de l'architecture actuelle ([`docs/architecture/current_state_analysis.md`](docs/architecture/current_state_analysis.md:1) et consolidés dans [`docs/architecture/rapport_analyse_architecture.md`](docs/architecture/rapport_analyse_architecture.md:1)), afin de créer une structure de projet et une architecture applicative plus cohérentes, maintenables et alignées sur les bonnes pratiques.

Les principes directeurs de cette réorganisation sont :

*   **Clarté et Lisibilité :** La nouvelle structure et architecture doivent être faciles à comprendre et à naviguer.
*   **Cohérence :** Adopter des conventions de nommage et d'organisation uniformes.
*   **Modularité :** Séparer clairement les préoccupations (code source, tests, scripts, documentation, configuration, dépendances externes, logique applicative).
*   **Maintenabilité :** Faciliter les modifications futures et l'intégration de nouveaux contributeurs.
*   **Conventions Python :** Suivre les standards de la communauté Python.

## 2. Proposition de Nouvelle Structure de Projet (Fichiers et Répertoires)

### 2.1. Arborescence Cible Proposée

```
.
├── argumentation_analysis/  # Package Python principal
│   ├── __init__.py
│   ├── agents/
│   ├── core/                # Logique métier principale, intégrant les éléments pertinents de l'ancien project_core/
│   │   ├── __init__.py
│   │   ├── jvm_setup.py     # Gestion centralisée et unique de l'initialisation de la JVM
│   │   └── orchestration_service.py # Proposition: Service centralisant la logique d'orchestration
│   ├── models/
│   ├── orchestration/       # Scripts et configurations liés à l'orchestration des agents
│   ├── services/
│   ├── ui/
│   └── utils/               # Utilitaires spécifiques au package argumentation_analysis
├── docs/                    # Documentation du projet
│   ├── architecture/
│   │   ├── current_state_analysis.md
│   │   ├── rapport_analyse_architecture.md
│   │   ├── architecture_hierarchique.md
│   │   └── reorganization_proposal.md  # Ce présent rapport
│   ├── cleaning_reports/
│   └── ... (autres guides, rapports, etc.)
├── examples/                # Scripts d'exemples, notebooks d'expérimentation et de démonstration
│   └── scratch_tweety_interactions.py # Exemple de script d'expérimentation
│   └── ... (autres notebooks ou exemples)
├── libs/                    # Emplacement unique pour les JARs TweetyProject et autres dépendances externes non-Python
│   └── tweety/              # JARs spécifiques à TweetyProject
│       └── ... (org.tweetyproject.commons-1.28-with-dependencies.jar, etc.)
│       └── native/          # Bibliothèques natives pour Tweety
│           └── ...
│   └── ... (autres libs externes si besoin, ex: JDK portable si nécessaire)
├── scripts/                 # Scripts d'utilité générale, de déploiement, de maintenance, etc. (hors scripts d'env. à la racine)
│   ├── data_processing/
│   ├── execution/
│   ├── maintenance/
│   ├── reporting/
│   ├── setup/               # Scripts d'installation et de configuration d'environnement
│   │   └── setup_env.py
│   └── validation/          # Scripts de validation et de diagnostic
│       └── check_jpype_env.py
│       └── temp_arch_check.py
│       └── verify_jar_content.ps1
├── tests/                   # Répertoire unique et centralisé pour tous les tests
│   ├── __init__.py
│   ├── conftest.py          # Fichier unique pour les fixtures Pytest globales et configuration des tests
│   ├── functional/          # Tests fonctionnels
│   ├── integration/         # Tests d'intégration (ex: interaction avec JVM, APIs externes)
│   │   └── test_jvm_initialization.py
│   ├── unit/                # Tests unitaires, reflétant la structure du package source
│   │   └── argumentation_analysis/
│   │       ├── __init__.py
│   │       ├── core/
│   │       │   └── test_jvm_setup.py
│   │       └── ... (autres tests unitaires)
│   ├── environment_checks/  # Tests de diagnostic d'environnement (ex: dépendances critiques)
│   │   └── test_minimal_jpype.py
│   └── support/             # Utilitaires, mocks, et aides spécifiques aux tests
├── .env                     # Variables d'environnement locales (non versionné)
├── .env.template            # Modèle pour le fichier .env
├── .gitignore               # Fichiers et répertoires à ignorer par Git
├── LICENSE                  # Licence du projet
├── README.md                # README principal du projet, incluant instructions de démarrage et aperçu
├── activate_project_env.ps1 # Script d'activation d'environnement (accès facile à la racine)
├── activate_project_env.sh  # Script d'activation d'environnement (accès facile à la racine)
├── environment.yml          # Fichier de configuration d'environnement Conda (si maintenu)
├── pytest.ini               # Fichier unique de configuration Pytest à la racine
├── requirements.txt         # Dépendances Python principales
├── requirements-test.txt    # Dépendances Python spécifiques aux tests (à la racine)
├── setup.py                 # Script de packaging et d'installation (standard Python)
├── setup_project_env.ps1    # Script de configuration d'environnement (accès facile à la racine)
└── setup_project_env.sh     # Script de configuration d'environnement (accès facile à la racine)
```

### 2.2. Justification des Choix de Réorganisation (Fichiers et Répertoires)

*   **Package Principal `argumentation_analysis/`**:
    *   **Justification**: Regroupe tout le code source Python applicatif en un seul package installable. Les éléments pertinents de l'ancien `project_core/` (utilitaires généraux, logique de base non spécifique à un module) seront intégrés dans `argumentation_analysis/core/` ou `argumentation_analysis/utils/` selon leur nature. Cela simplifie la structure, réduit la dispersion et clarifie le périmètre du code principal.
*   **Répertoire `tests/` Unique et Standardisé**:
    *   **Justification**: Centralise tous les tests, conformément aux bonnes pratiques. La structure interne (`unit/`, `functional/`, `integration/`, `environment_checks/`) permet une organisation claire. `tests/unit/` reflète la structure de `argumentation_analysis/` pour une navigation aisée. Un seul `tests/conftest.py` gère les fixtures globales. Cela élimine la redondance de `argumentation_analysis/tests/` et clarifie le rôle de `scripts/testing/` (qui pourrait contenir des scripts pour des scénarios de test complexes, mais pas les tests eux-mêmes).
*   **Répertoire `scripts/` Centralisé**:
    *   **Justification**: Rassemble tous les scripts qui ne font pas partie du package applicatif principal mais sont utiles pour le développement, la maintenance, le déploiement, etc. Les scripts précédemment à la racine (ex: [`check_jpype_env.py`](check_jpype_env.py:1)) y trouvent une place logique (ex: `scripts/validation/`).
*   **Répertoire `examples/`**:
    *   **Justification**: Isole les notebooks Jupyter, les scripts d'expérimentation ou de démonstration (comme [`scratch_tweety_interactions.py`](scratch_tweety_interactions.py:1)) du code de production et des scripts utilitaires.
*   **Répertoire `docs/`**:
    *   **Justification**: Maintien de la structure actuelle qui est déjà bien organisée pour la documentation.
*   **Gestion des Dépendances et Configuration (Standard Python)**:
    *   **Justification**: Maintien de l'approche actuelle avec `setup.py` pour la définition du package et `requirements.txt` (et `requirements-test.txt` à la racine) pour la gestion des dépendances. Cela évite une migration d'outil immédiate (vers Poetry/PDM et `pyproject.toml`), qui pourra être envisagée ultérieurement. L'objectif est de consolider les multiples `requirements.txt` en une version principale et une pour les tests, et d'avoir un seul `pytest.ini` à la racine.
*   **Répertoire `libs/` à la Racine**:
    *   **Justification**: Conserve un emplacement unique et bien rodé pour les bibliothèques JAR externes (TweetyProject) et potentiellement d'autres dépendances non-Python. Le répertoire `argumentation_analysis/libs/` sera supprimé et son contenu pertinent rapatrié ici. Cela assure un point unique pour ces dépendances, simplifie la gestion du classpath et réduit les risques de conflits.
*   **Fichiers à la Racine**:
    *   **Justification**: Minimise le nombre de fichiers à la racine pour une meilleure clarté, tout en conservant un accès direct aux scripts d'environnement essentiels (`activate_project_env.*`, `setup_project_env.*`). Les autres fichiers à la racine sont ceux standards pour un projet Python (`setup.py`, `requirements.txt`, `pytest.ini`, `README.md`, `LICENSE`, `.gitignore`, `.env`, `.env.template`, `environment.yml`). Le `conftest.py` racine sera supprimé, sa logique de chargement de `.env` pouvant être gérée par des bibliothèques Python dédiées et la gestion de `sys.path` devenant moins nécessaire. La gestion de la JVM est centralisée dans `argumentation_analysis/core/jvm_setup.py`.

## 3. Avantages Attendus de la Nouvelle Structure (Fichiers et Répertoires)

*   **Clarté et Lisibilité Accrues**: Navigation simplifiée et compréhension plus aisée de l'organisation du projet.
*   **Cohérence Renforcée**: Conventions de nommage et d'organisation uniformes.
*   **Modularité Améliorée**: Séparation nette des préoccupations.
*   **Maintenabilité Facilitée**: Modifications et évolutions futures plus simples à implémenter.
*   **Réduction de la Complexité**: Moins de dispersion des fichiers de configuration, de dépendances et des bibliothèques externes, simplifiant les imports et la gestion du classpath.
*   **Diminution des Risques**: Moins de risques de conflits (versions de JARs, configurations pytest, dépendances Python) et d'incohérences.
*   **Intégration Facilitée**: Courbe d'apprentissage réduite pour les nouveaux contributeurs.
*   **Standardisation**: Utilisation d'outils et de conventions modernes de la communauté Python.
*   **Gestion Centralisée de la JVM**: Logique de démarrage et de configuration de la JVM claire et unique.

## 4. Plan de Migration (Grandes Lignes pour la Structure des Fichiers)

1.  **Phase de Préparation**:
    *   **Sauvegarde Complète**: Assurer une sauvegarde complète du projet avant toute modification.
    *   **Validation par l'Équipe**: Obtenir l'accord de l'équipe sur la nouvelle structure et le plan de migration.
    *   **Consolidation des `requirements.txt`**: Analyser les différents `requirements.txt` et `requirements-test.txt` pour les fusionner en une version principale à la racine et une `requirements-test.txt` également à la racine.
    *   **Analyse Détaillée de `project_core/`**: Identifier précisément quels modules/utilitaires de `project_core/` doivent être fusionnés dans `argumentation_analysis/` et où.
2.  **Restructuration Initiale des Répertoires et Fichiers**:
    *   Créer la nouvelle arborescence de répertoires (`libs/tweety/`, `examples/`, etc.).
    *   Déplacer les fichiers et répertoires existants vers leurs nouveaux emplacements conformément à l'arborescence cible (ex: scripts de la racine vers `scripts/` ou `examples/`, JARs vers `libs/tweety/`).
    *   Supprimer les répertoires redondants après déplacement de leur contenu (ex: `argumentation_analysis/libs/`, `argumentation_analysis/tests/`, `argumentation_analysis/config/` si son contenu est migré).
3.  **Consolidation des Fichiers de Dépendances**:
    *   Créer le `requirements.txt` et `requirements-test.txt` uniques à la racine, basés sur l'analyse de la phase de préparation.
    *   S'assurer que `setup.py` est correctement configuré pour le package `argumentation_analysis`.
    *   Supprimer les anciens fichiers `requirements.txt` dispersés (ex: dans `argumentation_analysis/`, `config/`).
4.  **Consolidation de la Configuration**:
    *   Fusionner les configurations des deux `pytest.ini` en un seul (`pytest.ini` unique à la racine).
    *   S'assurer que la configuration de `pytest` (chemins de test, options) est correcte.
    *   Créer un `.env.template` unique à la racine.
5.  **Intégration de `project_core` et Mise à Jour des Imports**:
    *   Fusionner les modules identifiés de `project_core/` dans `argumentation_analysis/core/` ou `argumentation_analysis/utils/`.
    *   **Étape critique**: Parcourir l'ensemble du code source (`argumentation_analysis/`, `tests/`, `scripts/`, `examples/`) et mettre à jour systématiquement toutes les instructions `import` pour refléter la nouvelle structure des packages et l'emplacement des modules. Des outils de refactoring peuvent être utiles.
6.  **Adaptation de la Gestion de la JVM**:
    *   S'assurer que `argumentation_analysis/core/jvm_setup.py` est le seul responsable de l'initialisation de la JVM et qu'il utilise correctement les JARs depuis `libs/tweety/`.
    *   Mettre à jour les appels à l'initialisation de la JVM (notamment dans `tests/conftest.py` et potentiellement au démarrage de l'application/scripts).
    *   Supprimer l'ancien `conftest.py` racine après s'être assuré que sa logique pertinente a été migrée.
7.  **Vérification et Adaptation des Scripts et Exemples**:
    *   Vérifier que tous les scripts dans `scripts/` et `examples/` fonctionnent correctement après les changements de structure et d'imports.
8.  **Exécution et Validation des Tests**:
    *   Lancer l'ensemble de la suite de tests et corriger les erreurs éventuelles liées aux imports, aux chemins ou à la configuration.
    *   S'assurer que `pytest` découvre et exécute correctement tous les tests depuis le répertoire `tests/` unique.
9.  **Mise à Jour de la Documentation**:
    *   Mettre à jour le `README.md` principal pour refléter la nouvelle structure et les nouvelles instructions de configuration/démarrage.
    *   Documenter la nouvelle architecture du projet.
    *   Mettre à jour les scripts d'environnement (`setup_project_env.ps1`, etc.) si nécessaire.
10. **Nettoyage Final**:
    *   Supprimer les fichiers et répertoires obsolètes qui n'ont pas été supprimés lors des étapes précédentes.
    *   Vérifier le fichier `.gitignore`.

## 5. Propositions d'Évolution de l'Architecture Applicative

Au-delà de la structure des fichiers, l'analyse de l'architecture actuelle ([`docs/architecture/rapport_analyse_architecture.md`](docs/architecture/rapport_analyse_architecture.md:1)) a mis en évidence des points d'amélioration concernant l'architecture applicative elle-même. Les propositions suivantes visent à adresser ces points.

### 5.1. Centralisation de l'Orchestration

*   **Motivation**: L'orchestration actuelle est décrite comme "plate" et gérée principalement par le framework Semantic Kernel via `AgentGroupChat`, sans un service dédié clairement identifié. Le fichier [`argumentation_analysis/core/orchestration_service.py`](../../argumentation_analysis/core/orchestration_service.py:1) est manquant, ce qui est une faiblesse pour la clarté et la maintenabilité de la logique d'orchestration (constat du [`docs/architecture/rapport_analyse_architecture.md`](docs/architecture/rapport_analyse_architecture.md:93)).
*   **Proposition**:
    1.  Créer un module dédié `argumentation_analysis/core/orchestration_service.py`.
    2.  Ce service centraliserait la logique d'orchestration principale du système d'analyse rhétorique.
    3.  Ses responsabilités incluraient :
        *   La gestion du cycle de vie d'une session d'analyse.
        *   La coordination de haut niveau entre les différents agents ou groupes d'agents.
        *   L'exploitation structurée du `MessageMiddleware` ([`argumentation_analysis/core/communication/middleware.py`](../../argumentation_analysis/core/communication/middleware.py:1)) pour la communication inter-agents.
        *   L'interaction avec l'état partagé (`RhetoricalAnalysisState`) de manière contrôlée.
*   **Justification**: Cette centralisation améliorerait la clarté de l'architecture, faciliterait la maintenance et l'évolution de la logique d'orchestration, et fournirait un point d'entrée unique pour la gestion des analyses. Cela répond aux recommandations formulées dans [`docs/architecture/rapport_analyse_architecture.md`](docs/architecture/rapport_analyse_architecture.md:157).

### 5.2. Évaluation de l'Architecture Hiérarchique

*   **Motivation**: Une architecture hiérarchique à trois niveaux (Stratégique, Tactique, Opérationnel) a été proposée ([`docs/architecture/architecture_hierarchique.md`](docs/architecture/architecture_hierarchique.md:1)) pour adresser les limitations de l'orchestration "plate" actuelle, notamment en termes de scalabilité et de gestion de la complexité. Le [`docs/architecture/rapport_analyse_architecture.md`](docs/architecture/rapport_analyse_architecture.md:100) souligne que cette proposition est active mais encore conceptuelle pour ses aspects majeurs.
*   **Proposition**:
    1.  Mener une évaluation formelle de la pertinence et de la faisabilité de l'architecture hiérarchique proposée.
    2.  Si l'évaluation est positive et que cette direction est jugée prioritaire :
        *   Définir un plan d'implémentation par étapes, en commençant par un Proof of Concept (PoC).
        *   Le PoC pourrait se concentrer sur la validation des interactions clés entre un agent de chaque niveau (conceptuel) et l'utilisation du `HierarchicalChannel` ([`argumentation_analysis/core/communication/hierarchical_channel.py`](../../argumentation_analysis/core/communication/hierarchical_channel.py:1)) via le `MessageMiddleware`.
*   **Justification**: Prendre une décision éclairée sur l'évolution de l'architecture d'orchestration est crucial. Un PoC permettrait de valider les concepts clés de l'architecture hiérarchique à moindre coût avant un engagement plus conséquent. Cela s'aligne avec les recommandations du [`docs/architecture/rapport_analyse_architecture.md`](docs/architecture/rapport_analyse_architecture.md:153).

### 5.3. Clarification de la Gestion de la JVM

*   **Motivation**: La gestion de la JVM pour l'intégration avec TweetyProject a été identifiée comme un point nécessitant une clarification ([`docs/architecture/rapport_analyse_architecture.md`](docs/architecture/rapport_analyse_architecture.md:161)). Bien que la structure de fichiers proposée (section 2.1) centralise la logique dans `argumentation_analysis/core/jvm_setup.py`, il est important de s'assurer que son rôle est unique et bien compris.
*   **Proposition**:
    1.  Confirmer et documenter que `argumentation_analysis/core/jvm_setup.py` est le seul point d'initialisation et de configuration de la JVM pour l'ensemble du projet (application et tests).
    2.  S'assurer que toutes les dépendances aux JARs Tweety pointent correctement vers le répertoire `libs/tweety/` centralisé.
    3.  Vérifier que les configurations de test (notamment dans `tests/conftest.py`) utilisent exclusivement ce module centralisé pour la gestion de la JVM.
*   **Justification**: Une gestion claire et centralisée de la JVM réduit les risques d'erreurs de configuration, simplifie le débogage et assure la cohérence de l'environnement Java à travers tout le projet.

## 6. Défis Potentiels de la Migration

*   **Mise à Jour des Imports**: C'est la tâche la plus susceptible d'être longue et fastidieuse, avec un risque élevé d'erreurs manuelles si elle n'est pas outillée.
*   **Consolidation Manuelle des Dépendances**: S'assurer que la fusion des `requirements.txt` est correcte et ne manque aucune dépendance ou n'introduit pas de conflits peut être délicat.
*   **Compatibilité des Tests**: S'assurer que tous les tests continuent de passer après des changements structurels majeurs peut être complexe.
*   **Gestion du Classpath Java**: Bien que simplifiée, la configuration initiale pour que la JVM trouve correctement les JARs depuis `libs/tweety/` doit être validée rigoureusement.
*   **Impact sur les Flux de Travail Existants**: Les développeurs devront s'adapter à la nouvelle structure et potentiellement à de nouveaux outils.
*   **Complexité de l'Évolution Architecturale**: L'introduction d'un service d'orchestration ou l'exploration d'une architecture hiérarchique sont des changements significatifs qui demandent une planification et une exécution rigoureuses.

## 7. Liste Détaillée des Opérations de Réorganisation de Structure (Atomiques)

Voici la liste détaillée des opérations de déplacement, création et suppression de fichiers/répertoires, par phase, pour la réorganisation de la structure des fichiers.

**Phase 1: Préparation et Nettoyage Initial à la Racine**

1.  **Supprimer les fichiers temporaires/logs/outputs à la racine :**
    *   Supprimer le fichier : `extract_agent.log`
    *   Supprimer le fichier : `repair_extract_markers.log`
    *   Supprimer le fichier : `temp_asp_for_manual_check.lp`
    *   Supprimer le fichier : `pytest_hierarchical_full_v4.txt`
    *   Supprimer le fichier : `modules.bak` (Considéré comme non essentiel)

**Phase 2: Consolidation des Bibliothèques (`libs/`)**

*   **Note Importante :** L'objectif est d'avoir un unique répertoire `libs/tweety/` à la racine contenant tous les JARs Tweety et leurs dépendances natives.
2.  **Préparation du répertoire `libs/tweety/` à la racine :**
    *   S'assurer que le répertoire `libs/tweety/` existe.
    *   Créer le répertoire : `libs/tweety/native/` (si non existant).
3.  **Mise à Jour des Scripts de Setup et des Références aux JARs Tweety :**
    *   Les fichiers `*.jar` de `argumentation_analysis/libs/` doivent être déplacés vers `libs/tweety/`.
    *   **Action Requise Prioritaire :**
        *   Modifier les scripts de setup du projet (ex: [`setup_project_env.ps1`](setup_project_env.ps1:1), [`setup_project_env.sh`](setup_project_env.sh:1), et potentiellement `scripts/setup/setup_env.py`) pour :
            *   S'assurer qu'ils téléchargent/placent les JARs Tweety dans `libs/tweety/`.
            *   Nettoyer les anciens emplacements de JARs (ex: directement sous `libs/` si des scripts les y plaçaient, ou dans `argumentation_analysis/libs/`).
        *   Identifier tous les emplacements dans le code (`argumentation_analysis/`, `scripts/`, `tests/`) où ces JARs sont référencés, chargés, ou leur chemin est construit (ex: pour le classpath Java). Mettre à jour ces références pour pointer vers `libs/tweety/[nom_du_jar].jar`.
4.  **Déplacement des bibliothèques natives Tweety :**
    *   Pour chaque fichier dans `argumentation_analysis/libs/native/` :
        Déplacer `argumentation_analysis/libs/native/[nom_du_fichier_natif]` vers `libs/tweety/native/[nom_du_fichier_natif]`.
5.  **Gestion du README et suppression de l'ancien répertoire `libs` :**
    *   Lire le contenu de `argumentation_analysis/libs/README.md` (s'il existe et contient des informations pertinentes).
    *   Lire le contenu de `libs/README.md` (à la racine, s'il existe, sinon le créer).
    *   Fusionner les informations pertinentes de `argumentation_analysis/libs/README.md` dans `libs/README.md`.
    *   Supprimer le répertoire : `argumentation_analysis/libs/` (après s'être assuré que tout son contenu pertinent, y compris `native/`, a été déplacé et que les READMEs sont fusionnés).

**Phase 3: Réorganisation des Scripts**

6.  **Déplacement des scripts Python de la racine :**
    *   Déplacer [`check_jpype_env.py`](check_jpype_env.py:1) vers `scripts/validation/check_jpype_env.py`.
    *   Déplacer [`minimal_jpype_test.py`](minimal_jpype_test.py:1) vers `tests/environment_checks/test_minimal_jpype.py` (changement de nom pour convention de test).
    *   Déplacer [`scratch_tweety_interactions.py`](scratch_tweety_interactions.py:1) vers `examples/scratch_tweety_interactions.py`.
    *   Déplacer [`temp_arch_check.py`](temp_arch_check.py:1) vers `scripts/validation/temp_arch_check.py`.
    *   Déplacer [`setup_env.py`](setup_env.py:1) vers `scripts/setup/setup_env.py`.
7.  **Déplacement des scripts PowerShell de la racine :**
    *   Déplacer `verify_jar_content.ps1` vers `scripts/validation/verify_jar_content.ps1`.
8.  **Consolidation des scripts de `argumentation_analysis/scripts/` :**
    *   Créer le répertoire : `scripts/argumentation_analysis_tools/` (si non existant).
    *   Pour chaque fichier (`*.py`, `__init__.py`, `README.md`) dans `argumentation_analysis/scripts/` :
        Déplacer `argumentation_analysis/scripts/[nom_fichier]` vers `scripts/argumentation_analysis_tools/[nom_fichier]`.
    *   Mettre à jour le `README.md` de `scripts/` pour refléter ce nouveau sous-répertoire et son contenu.
    *   Supprimer le répertoire : `argumentation_analysis/scripts/`.

**Phase 4: Réorganisation de la Configuration**

9.  **Consolidation des fichiers de configuration :**
    *   Déplacer `config/requirements-test.txt` vers `requirements-test.txt` (à la racine).
    *   Supprimer le fichier : `config/pytest.ini` (celui à la racine, `pytest.ini`, est conservé et devient l'unique fichier de configuration pytest).
    *   Lire le contenu de `argumentation_analysis/config/.env.template` (s'il existe).
    *   Lire le contenu de `config/.env.template` (s'il existe).
    *   Fusionner les contenus pour créer un unique `.env.template` à la racine du projet (ce fichier servira de modèle pour le `.env` non versionné).
    *   Supprimer le répertoire : `config/` (après déplacement/fusion de son contenu).
    *   Supprimer le répertoire : `argumentation_analysis/config/` (après déplacement/fusion de son contenu).
10. **Nettoyage `conftest.py` à la racine :**
    *   Supprimer le fichier : [`conftest.py`](conftest.py:1) (à la racine). Sa logique de chargement de `.env` sera gérée par des bibliothèques Python dédiées (ex: `python-dotenv`) et la gestion de `sys.path` sera moins critique avec la structure de package améliorée.

**Phase 5: Intégration de `project_core/` dans `argumentation_analysis/`**

11. **Intégration de `bootstrap.py` :**
    *   Déplacer `project_core/bootstrap.py` vers `argumentation_analysis/core/bootstrap.py` (ou renommer/intégrer sa logique si pertinent).
12. **Intégration de `dev_utils/` :**
    *   Créer le répertoire : `argumentation_analysis/utils/dev_tools/` (si non existant).
    *   Pour chaque fichier `*.py` dans `project_core/dev_utils/` :
        Déplacer `project_core/dev_utils/[nom_fichier].py` vers `argumentation_analysis/utils/dev_tools/[nom_fichier].py`.
13. **Intégration de `integration/` :**
    *   Créer le répertoire : `argumentation_analysis/core/integration/` (si non existant).
    *   Pour chaque fichier `*.py` dans `project_core/integration/` :
        Déplacer `project_core/integration/[nom_fichier].py` vers `argumentation_analysis/core/integration/[nom_fichier].py`.
14. **Intégration de `project_core/utils/` :**
    *   Pour chaque fichier `*.py` dans `project_core/utils/` :
        Déplacer `project_core/utils/[nom_fichier].py` vers `argumentation_analysis/utils/[nom_fichier].py`. (Attention : si un fichier du même nom existe déjà dans `argumentation_analysis/utils/`, une analyse de contenu et une fusion/renommage manuelle seront nécessaires).
15. **Suppression de `project_core/` :**
    *   Supprimer le répertoire : `project_core/` (après s'être assuré que tout son contenu pertinent a été déplacé).

**Phase 6: Finalisation de la Structure des Tests**

16. **Nettoyage des répertoires de tests hérités :**
    *   Vérifier si le répertoire `argumentation_analysis/tests/` existe. Si oui, et s'il contient des tests pertinents non présents dans `tests/unit/argumentation_analysis/` (ou ailleurs dans `tests/`), les déplacer vers l'emplacement approprié dans `tests/`. Ensuite, supprimer `argumentation_analysis/tests/`.
    *   Vérifier si le fichier `argumentation_analysis/run_tests.py` existe. Si oui, le supprimer (l'exécution des tests se fera via `pytest` depuis la racine).

**Phase 7: Clarification et Nettoyage de Répertoires Divers**

17. **Répertoire `examples/` :**
    *   Si le répertoire `argumentation_analysis/examples/` existe :
        Pour chaque fichier/répertoire dans `argumentation_analysis/examples/` :
        Déplacer `argumentation_analysis/examples/[item]` vers `examples/[item]` (le répertoire `examples/` à la racine).
        Supprimer le répertoire `argumentation_analysis/examples/`.
18. **Répertoire `results/` :**
    *   Si le répertoire `argumentation_analysis/results/` existe : Évaluer son contenu. Il est recommandé de le gérer manuellement ou de le supprimer si les résultats sont temporaires/obsolètes, ou de les déplacer vers un répertoire `results/` à la racine (qui devrait être dans `.gitignore`). Aucune action de déplacement automatique n'est listée ici.
19. **Répertoire `tutorials/` :**
    *   Si le répertoire `tutorials/` à la racine existe :
        Créer le répertoire `docs/tutorials/` (si non existant).
        Déplacer le contenu de `tutorials/` (à la racine) vers `docs/tutorials/`.
        Supprimer le répertoire `tutorials/` à la racine.
    *   Mettre à jour le `README.md` de `docs/` pour mentionner ce nouveau sous-répertoire.

**Phase 8: Vérification et Mise à Jour des Fichiers de Configuration et READMEs**

*   **Note :** Ces opérations sont principalement des vérifications et des mises à jour de contenu qui suivront les déplacements de fichiers.
20. **Fichiers de dépendances :**
    *   Vérifier que `requirements.txt` à la racine est complet et consolidé.
    *   Vérifier que `requirements-test.txt` à la racine est complet et consolidé.
21. **Fichier `setup.py` :**
    *   Vérifier que `setup.py` référence correctement le package `argumentation_analysis` et ses sous-modules après l'intégration de `project_core`.
22. **Fichier `.gitignore` :**
    *   S'assurer que les nouveaux emplacements de logs (s'il y en a de nouveaux), `venv_py310/` (ou autre nom de venv), `argumentation_analysis.egg-info/`, `results/` (si non versionné), et tout autre fichier généré ou temporaire sont bien ignorés.
23. **Mise à jour des `README.md` :**
    *   Mettre à jour le `README.md` principal du projet pour refléter la nouvelle structure, les instructions de configuration/démarrage, et l'emplacement des scripts d'environnement.
    *   Mettre à jour le `README.md` dans `tests/` si nécessaire.
    *   Mettre à jour le `README.md` dans `scripts/` pour refléter la nouvelle organisation (ex: `argumentation_analysis_tools/`).
    *   Mettre à jour le `README.md` dans `docs/` pour refléter la nouvelle organisation (ex: `docs/tutorials/`).

## 8. Conclusion

La réorganisation proposée, touchant à la fois la structure des fichiers et l'architecture applicative, vise à transformer la base actuelle du projet en une fondation plus solide, plus claire et plus facile à maintenir pour les développements futurs. Les propositions concernant la structure des fichiers cherchent à améliorer la clarté et la cohérence de l'organisation du projet. Celles concernant l'architecture applicative, notamment la centralisation de l'orchestration et l'évaluation d'une architecture hiérarchique, visent à adresser des faiblesses fonctionnelles et à préparer le projet à une meilleure scalabilité et maintenabilité.

Bien que la migration représente un effort certain, les avantages à long terme en termes de productivité, de réduction des erreurs, de clarté architecturale et de facilité de collaboration sont considérables.

Cette proposition consolidée est une base de discussion et peut être affinée en fonction des retours et des contraintes spécifiques du projet.