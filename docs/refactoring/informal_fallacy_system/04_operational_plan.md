# Plan Opérationnel de Refactorisation du Système de Sophismes

**Version:** 0.1
**Date:** 2025-07-26
**Statut:** Initialisation

## 1. Contexte, Problématique et Vision

### 1.1. Contexte : Héritage et Complexité Croissante

L'analyse du système existant, consignée dans les documents [`01_informal_fallacy_system_analysis.md`](./01_informal_fallacy_system_analysis.md) et [`02_system_legacy_and_evolution_analysis.md`](./02_system_legacy_and_evolution_analysis.md), a mis en lumière une réalité inévitable de tout projet innovant : une accumulation de strates architecturales. Le système actuel est une mosaïque fonctionnelle mais hétérogène, comprenant :
*   Une architecture principale "Plan-and-Execute", la plus aboutie.
*   Des architectures secondaires et héritées comme le pipeline "multi-niveaux" ou l'approche "one-shot".
*   Une prolifération d'outils et de services, parfois redondants, témoignant d'une R&D continue.

Cette complexité, bien que naturelle, engendre des défis en termes de maintenabilité, d'évolutivité et de clarté. L'absence d'un point d'entrée unique et la dispersion de la logique métier rendent difficile l'intégration de nouvelles capacités et l'optimisation des performances.

### 1.2. Vision Stratégique : La Consolidation Constructive

Face à ce constat, le document [`03_informal_fallacy_consolidation_plan.md`](./03_informal_fallacy_consolidation_plan.md) a établi une vision claire : non pas une refonte totale ("big bang"), mais une **consolidation constructive**. L'objectif est de fédérer le meilleur des architectures existantes au sein d'un cadre unifié, gouverné par des principes forts :
*   Un **Guichet de Service Unique** pour toutes les interactions.
*   Une **architecture de plugins à deux niveaux** (Standard et Workflows).
*   Une **externalisation complète de la personnalité des agents** et de leurs prompts.

### 1.3. Objectif de ce Plan Opérationnel

Ce document traduit cette vision stratégique en une feuille de route technique. Il décompose les 7 grandes étapes de migration définies dans le plan de consolidation en une série d'**actions concrètes, séquencées et validables**. Chaque action est conçue pour être une brique fondamentale qui nous rapproche de l'architecture cible, tout en maintenant la stabilité du système à chaque étape. Ce plan est le guide d'implémentation pour l'équipe de développement.

## 2. Référence Stratégique

-   **Document source:** [`03_informal_fallacy_consolidation_plan.md`](./03_informal_fallacy_consolidation_plan.md)
-   **Méthodologie:** SDDD (Semantic Document Driven Design)

## 3. Décomposition Opérationnelle

Cette section décompose la feuille de route stratégique en tâches granulaires, conformément au manifeste SDDD.

# Étape 1 : Fondations de la Nouvelle Architecture

Cette première phase vise à construire le socle physique et logiciel sur lequel reposera l'ensemble du système refactorisé. En établissant une arborescence de répertoires claire et en définissant les contrats d'interface fondamentaux, nous posons les fondations d'un système modulaire, robuste et extensible.

### Objectif 1 : Mettre en place la nouvelle structure de base

*   **Objectif Stratégique :** Créer le squelette de la nouvelle structure de répertoires pour le `core` et les `agents`, afin d'établir une fondation stable pour la migration incrémentale.

#### Action 1.1 : Créer la nouvelle arborescence de base

*   **Justification Stratégique :** Cette action matérialise le principe architectural fondamental de **séparation des préoccupations** défini dans le plan stratégique. En isolant physiquement le **cœur logique (`core`)** des **identités des agents (`agents`)**, nous créons un système où le comportement peut être modifié et étendu (via les personnalités) sans altérer la logique métier fondamentale. Cette structure est également conçue pour être explicitement prise en charge par les futurs `plugin_loader` et `agent_loader`, qui s'appuieront sur ces conventions de nommage pour découvrir et charger dynamiquement les composants.

*   **Checklist Narrative et Technique Détaillée :**
    *   **1. Création du Cœur Agnostique (`src/core`)**
        *   **Justification :** L'analyse ([`01_informal_fallacy_system_analysis.md`](./01_informal_fallacy_system_analysis.md)) a révélé de multiples composants logiques (outils d'analyse, services de taxonomie) utilisés par différentes architectures. Pour éviter la duplication et le couplage, le plan de consolidation ([`03_informal_fallacy_consolidation_plan.md`](./03_informal_fallacy_consolidation_plan.md)) impose la création d'un `core` agnostique.
        *   **Tâche :** Créer le répertoire `src/core`.

    *   **2. Structuration de l'Écosystème de Plugins (`src/core/plugins`)**
        *   **Justification :** Le plan de consolidation (`03_...`) définit une architecture à deux niveaux de plugins comme pilier central. Cette arborescence matérialise cette séparation cruciale.
        *   **Tâche :** Créer le répertoire `src/core/plugins`.

    *   **3. Répertoire des Plugins "Standard" (`src/core/plugins/standard`)**
        *   **Justification :** Pour concrétiser le premier niveau de l'architecture à deux niveaux. Ce répertoire hébergera les briques de base atomiques et réutilisables, comme les analyseurs "Enhanced" ou le service de taxonomie, identifiés dans l'inventaire de `01_...` et dont le plan `03_...` prévoit la migration en tant que plugins standard.
        *   **Tâche :** Créer le répertoire `src/core/plugins/standard`.

    *   **4. Répertoire des Plugins "Workflows" (`src/core/plugins/workflows`)**
        *   **Justification :** Pour matérialiser le second niveau. Ce répertoire est destiné à accueillir les orchestrateurs complexes comme `PlanAndExecuteWorkflow` ou `CounterArgumentGenerationWorkflow`. Il répond au besoin de séparer clairement la logique atomique de la logique process, un problème mis en évidence par la coexistence de multiples pipelines dans `01_...`.
        *   **Tâche :** Créer le répertoire `src/core/plugins/workflows`.

    *   **5. Création de la Racine des Agents (`src/agents`)**
        *   **Justification :** L'analyse de l'évolution ([`02_system_legacy...`](./02_system_legacy_and_evolution_analysis.md)) montre un glissement d'agents monolithiques vers des agents orchestrés. Pour formaliser cette séparation, nous créons un espace de noms dédié à tout ce qui a trait aux agents.
        *   **Tâche :** Créer le répertoire `src/agents`.

    *   **6. Centralisation des Personnalités d'Agents (`src/agents/personalities`)**
        *   **Justification :** C'est une réponse directe à la dispersion des prompts et des configurations (`prompts.py`, `informal_definitions.py`) identifiée dans `01_...`. Le plan `03_...` stipule que les personnalités (code + forêt de prompts) doivent être externalisées ici pour découpler le comportement de l'agent de la logique `core`.
        *   **Tâche :** Créer le répertoire `src/agents/personalities`.

    *   **7. Initialisation des Modules Python**
        *   **Justification :** Standard technique pour que Python reconnaisse ces nouveaux répertoires comme des modules importables par les futurs `plugin_loader.py` et `agent_loader.py`.
        *   **Tâche :** Créer les fichiers `__init__.py` dans chaque nouveau répertoire.

    *   **8. Validation et Documentation**
        *   **Tâche :** Exécuter `tree src/core src/agents` (ou équivalent) pour valider la structure.
        *   **Tâche :** Mettre à jour `docs/architecture/README.md` avec la nouvelle structure et ses justifications.
        *   **Tâche :** Rédiger le message de commit sémantique : `feat(arch): create foundational directory structure for core and agents`.

#### Point de Contrôle et Synthèse de l'Action 1.1
*À ce stade, nous aurons une arborescence de répertoires validée, prête à accueillir les composants du noyau. La validation sémantique confirmera que la documentation d'architecture est à jour.*

#### Action 1.2 : Mise en œuvre du chargeur de plugins

*   **Justification Stratégique :** Cette action est le pilier de la **consolidation constructive**. En créant un mécanisme centralisé pour découvrir, valider et charger les plugins, nous matérialisons plusieurs principes du plan de consolidation (`03_...`). L'interface `BasePlugin` agit comme un **contrat strict**, une manifestation du principe de **Guichet de Service Unique** au niveau du code, garantissant que toute capacité exposée au système est standardisée. Le chargement dynamique depuis des répertoires dédiés (`standard/`, `workflows/`) instaure la modularité et prépare le terrain pour une évolution prédictible.

*   **Checklist Opérationnelle Détaillée :**

    *   **1. Finalisation des Interfaces de Contrat (`src/core/plugins/interfaces.py`)**
        *   **Justification :** Le contrat est la pierre angulaire. Il doit être clair et non-ambigu.
        *   **Tâche :** Valider la définition de `BasePlugin` (pour l'identification) et `IWorkflowPlugin` (pour l'exécution), comme déjà esquissé.
        *   **Point de Contrôle :** Le fichier d'interfaces est créé et contient les deux classes abstraites.

    *   **2. Implémentation de la Logique de Découverte (`src/core/plugins/plugin_loader.py`)**
        *   **Justification :** Le système doit être capable de scanner son propre environnement pour trouver les capacités disponibles, ce qui le rend extensible par simple ajout de code dans les bons répertoires.
        *   **Tâche :** Créer la classe `PluginLoader`. Implémenter la méthode `discover(path)` qui parcourt récursivement le chemin des plugins.
        *   **Tâche :** Utiliser `importlib` pour charger dynamiquement les modules (`__init__.py`) trouvés dans chaque sous-répertoire de plugin.
        *   **Point de Contrôle :** Le loader peut lister les modules Python présents dans l'arborescence des plugins.

    *   **3. Mécanisme de Validation et de Conformité**
        *   **Justification :** Pour garantir la stabilité, le système ne doit charger que des plugins qui respectent le contrat défini. Un plugin défectueux ne doit pas compromettre l'ensemble du système.
        *   **Tâche :** Dans `PluginLoader`, après avoir chargé un module, inspecter son contenu (`inspect.getmembers`) pour trouver les classes.
        *   **Tâche :** Vérifier que chaque classe découverte hérite bien de `BasePlugin` (`issubclass(PluginClass, BasePlugin)`).
        *   **Tâche :** Ignorer les classes non conformes et logger un avertissement clair.
        *   **Point de Contrôle :** Seuls les plugins valides sont retenus par le loader.

    *   **4. Stratégie d'Enregistrement dans un Registre Central**
        *   **Justification :** Les composants du système (comme le Guichet de Service) ont besoin d'un point d'accès unique pour trouver et utiliser les plugins chargés. Le "registre" remplit ce rôle.
        *   **Tâche :** La méthode `discover` du `PluginLoader` retournera un dictionnaire (le "registre") où les clés sont les noms des plugins (`plugin.name`) et les valeurs sont les instances des classes de plugin.
        *   **Tâche :** Le `PluginLoader` instanciera chaque plugin valide (`PluginClass()`) pour le stocker dans le registre.
        *   **Point de Contrôle :** L'appel à `plugin_loader.discover()` retourne un dictionnaire peuplé, prêt à l'emploi.

#### Action 1.3 : Mise en œuvre du chargeur d'agents

*   **Justification Stratégique :** Cette action est la contrepartie de la 1.2 et concrétise le principe clé d'**externalisation des personnalités** du document `03`. En séparant le "qui" (la personnalité de l'agent, ses instructions) du "comment" (la logique du `core`), nous créons des entités autonomes dont le comportement peut être versionné, testé et amélioré indépendamment du code applicatif. Le `AgentLoader` est le mécanisme qui assemble dynamiquement ces personnalités.

*   **Checklist Opérationnelle Détaillée :**

    *   **1. Définition de l'Interface de Personnalité (`src/agents/interfaces.py`)**
        *   **Justification :** Pour qu'une personnalité soit "chargeable", elle doit adhérer à un contrat.
        *   **Tâche :** Définir une interface (ou une dataclass) `IAgentPersonality` qui formalise la structure d'un agent chargé : `name`, `system_prompt`, `config`, et une liste de `plugin_references`.
        *   **Point de Contrôle :** L'interface est définie.

    *   **2. Implémentation du Chargeur d'Agents (`src/agents/agent_loader.py`)**
        *   **Justification :** Ce composant orchestre la "naissance" d'un agent en assemblant ses différentes parties.
        *   **Tâche :** Créer la classe `AgentLoader`, avec une méthode `load_personality(agent_name)`.
        *   **Tâche :** La méthode doit localiser le répertoire de la personnalité dans `src/agents/personalities/`.
        *   **Point de Contrôle :** L'Agent Loader peut cibler un répertoire de personnalité spécifique.

    *   **3. Stratégie de Chargement des Instructions et de la Configuration**
        *   **Justification :** Le comportement de l'agent (sa mission) et ses paramètres de fonctionnement doivent être chargés depuis des fichiers externes, les rendant facilement modifiables sans redéploiement. C'est l'essence de l'**externalisation des personnalités**.
        *   **Tâche :** Dans `load_personality`, lire le contenu du fichier `system.md` pour obtenir le prompt système.
        *   **Tâche :** Lire et parser le fichier `config.json` pour obtenir les paramètres de l'agent (peut inclure les `model_id`, `temperature` par défaut, et la liste des plugins requis).
        *   **Point de Contrôle :** L'Agent Loader peut lire en mémoire le prompt et la configuration d'un agent donné.

    *   **4. Injection de la Personnalité dans une Instance d'Agent**
        *   **Justification :** Les informations chargées doivent être injectées dans une instance concrète d'un Agent du `core` pour devenir actives.
        *   **Tâche :** Le `AgentLoader` prendra en dépendance une classe d'agent générique (ex: `GenericConversationalAgent` venant du `core`).
        *   **Tâche :** Après avoir chargé la personnalité, le loader instanciera cet agent générique en lui passant le `system_prompt`, la `config`, et les références aux plugins dans son constructeur.
        *   **Point de Contrôle :** La méthode `load_personality` retourne une instance d'agent pleinement configurée et prête à être utilisée par le Guichet de Service.

#### Action 1.3.1 : Standardisation via Manifeste de Plugin

*   **Justification Stratégique :** Pour atteindre une véritable modularité, le système ne doit pas se contenter de trouver du code, il doit comprendre ce que ce code peut faire sans avoir à l'exécuter. Le fichier manifeste `plugin.yaml` agit comme une "carte d'identité" pour chaque plugin, déclarant ses métadonnées, ses capacités et ses dépendances. Cela formalise le contrat entre le plugin et le système de chargement, rendant le système plus robuste et introspectable.

*   **Checklist Opérationnelle Détaillée :**
    *   **1. Définition du Format du Manifeste (`plugin.yaml`)**
        *   **Format :** YAML, pour sa lisibilité humaine.
        *   **Emplacement :** Chaque répertoire de plugin (`src/core/plugins/standard/un_plugin/`, `src/core/plugins/workflows/un_workflow/`) doit contenir un fichier `plugin.yaml` à sa racine.
        *   **Structure du Manifeste :**
            ```yaml
            # Métadonnées générales du plugin
            metadata:
              name: "analysis_tools"
              version: "1.2.0"
              author: "Core Team"
              description: "Plugin fournissant un ensemble d'outils d'analyse sémantique."

            # Spécification technique
            spec:
              # Type de plugin (permet au loader d'appliquer des logiques différentes)
              type: "standard" # ou "workflow"

              # Fichier principal contenant l'implémentation de la classe du plugin
              entrypoint: "__init__.py"
              class_name: "AnalysisToolsPlugin"

              # Dépendances externes requises par le plugin
              dependencies:
                - "pydantic>=2.0"
                - "numpy"

              # Capacités exposées par le plugin (fonctions natives)
              # Ceci est la déclaration formelle de ce que le plugin offre
              capabilities:
                - name: "analyze_context"
                  description: "Analyse un texte pour extraire le contexte et les entités."
                  input_schema:
                    type: "object"
                    properties:
                      text: { type: "string", description: "Texte à analyser." }
                    required: ["text"]
                  output_schema:
                    type: "object"
                    properties:
                      entities: { type: "array", items: { type: "string" } }
                      summary: { type: "string" }

                - name: "evaluate_severity"
                  description: "Évalue la sévérité d'un sophisme identifié."
                  input_schema:
                    type: "object"
                    properties:
                      fallacy_type: { type: "string" }
                      context: { type: "string" }
                    required: ["fallacy_type", "context"]
                  output_schema:
                    type: "object"
                    properties:
                      severity_score: { type: "number" }
            ```

    *   **2. Adaptation de la Logique du `PluginLoader`**
        *   La méthode `discover(path)` du `PluginLoader` sera modifiée.
        *   **Nouvelle Séquence de Chargement :**
            1.  Scanner le `path` pour trouver les répertoires contenant un `plugin.yaml`.
            2.  Pour chaque `plugin.yaml` trouvé :
                a.  Lire et parser le `plugin.yaml`.
                b.  Valider le manifeste par rapport à un schéma de référence pour s'assurer qu'il contient les champs requis (`metadata.name`, `spec.entrypoint`, etc.).
                c.  Utiliser `importlib` pour charger le module depuis `spec.entrypoint`.
                d.  Inspecter le module pour trouver la classe `spec.class_name`.
                e.  Vérifier que la classe est conforme à l'interface `BasePlugin`.
                f.  Enregistrer le plugin et ses métadonnées (capacités comprises) dans le registre central.
        *   **Point de Contrôle :** `plugin_loader.discover()` retourne un registre où chaque entrée contient non seulement l'instance du plugin mais aussi les métadonnées issues de son manifeste. Le système peut désormais lister toutes les `capabilities` disponibles sans instancier tous les plugins.

#### Action 1.4 : Mettre en place la structure de test unifiée

*   **Introduction Stratégique (le "Pourquoi") :** Des fondations logicielles, aussi bien conçues soient-elles, ne sont rien sans un filet de sécurité robuste. Cette action vise à établir ce filet en définissant une hiérarchie de tests claire (`unit`, `integration`, `e2e`) et en configurant les outils (`pytest`) pour garantir que chaque brique de la nouvelle architecture (loaders, interfaces) est et restera fiable.

*   **Checklist Microscopique détaillée (le "Comment") :**
    *   `[x] Principe : Organiser les tests par niveau de granularité pour une exécution et une maintenance claires.`
    *   `[x] Tâche : Créer les répertoires `tests/unit`, `tests/integration`, et `tests/e2e`.`
    *   `[x] Tâche : Créer des fichiers `__init__.py` dans chaque répertoire de test pour assurer la reconnaissance des modules.`
    *   `[x] Commentaire : Les tests unitaires valident un composant en isolation. Les tests d'intégration valident l'interaction entre plusieurs composants (ex: le `PluginLoader` chargeant un vrai `Plugin`).`
    *   `[x] Principe : Configurer l'environnement de test pour qu'il soit cohérent et reproductible.`
    *   `[x] Tâche : Créer ou mettre à jour le fichier `pytest.ini` à la racine pour définir les `testpaths` (ex: `testpaths = tests/unit tests/integration`).`
    *   `[x] Tâche : Créer un fichier `tests/conftest.py` pour y définir les fixtures `pytest` partagées, comme une fixture `tmp_path_factory` pour créer des fichiers/dossiers temporaires.`
    *   `[x] Principe : Prouver la viabilité de la nouvelle structure en y migrant un test existant.`
    *   `[x] Tâche : Identifier un test unitaire simple dans l'ancienne structure du projet.`
    *   `[x] Tâche : Déplacer et adapter ce test dans le répertoire `tests/unit` approprié.`
    *   `[x] Tâche : Exécuter `pytest` et valider que le test est bien découvert et passe avec succès.`
    *   `[x] Doc : Mettre à jour le `CONTRIBUTING.md` pour décrire la nouvelle organisation des tests et les commandes pour les lancer.`
    *   `[x] Commit : Rédiger le message de commit pour la restructuration des tests (ex: `refactor(tests): establish unified testing structure and migrate initial tests`).`

#### Point de Contrôle et Synthèse de l'Action 1.4
*À ce stade, l'architecture disposera d'un framework de test structuré et configuré. La hiérarchie des tests (`unit`, `integration`, `e2e`) sera établie, l'environnement `pytest` sera initialisé (`pytest.ini`, `conftest.py`) et la viabilité du concept aura été prouvée par la migration réussie d'un premier test. Le projet est maintenant prêt à développer de nouvelles fonctionnalités de manière sécurisée.*

# Étape 2: Framework de Benchmarking

> **Note de Régularisation :** Cette étape a été implémentée en avance de phase, en violation du protocole SDDD. Le code existant est en cours d'intégration et de documentation formelle pour aligner l'état du projet sur ce plan.

Avec les fondations de l'architecture de plugins en place, l'étape suivante consiste à construire un framework robuste pour mesurer, analyser et rapporter la performance des capacités des plugins.

### 2.1. Objectifs

*   **Mesurer la performance :** Obtenir des métriques précises (temps de réponse, succès/échec) pour chaque exécution d'une capacité.
*   **Agréger les résultats :** Calculer des statistiques (moyenne, min, max) sur des suites de tests.
*   **Fournir un point d'entrée simple :** Permettre l'exécution facile de suites de benchmarks via un script dédié.

### 2.2. Architecture et Composants

Le framework s'appuie sur trois nouveaux composants principaux qui ont été implémentés.

#### 2.2.1. Contrats de Données de Benchmark (`src/core/contracts.py`)

Les contrats existants ont été étendus avec deux nouveaux modèles Pydantic pour structurer les résultats des mesures.

*   `BenchmarkResult`: Représente le résultat d'une **unique** exécution.
    *   `request_id`: `str` - Lien vers la requête d'orchestration.
    *   `is_success`: `bool` - Statut de succès.
    *   `duration_ms`: `float` - Durée d'exécution.
    *   `output`: `Optional[Dict]` - Sortie de la capacité.
    *   `error`: `Optional[str]` - Message d'erreur.

*   `BenchmarkSuiteResult`: Agrège les résultats d'une **suite complète** de tests pour une capacité.
    *   `plugin_name`, `capability_name`: `str` - Identification.
    *   `total_runs`, `successful_runs`, `failed_runs`: `int` - Statistiques de base.
    *   `total_duration_ms`, `average_duration_ms`, `min_duration_ms`, `max_duration_ms`: `float` - Métriques de performance.
    *   `results`: `List[BenchmarkResult]` - Liste des résultats individuels.

#### 2.2.2. Service de Benchmark (`src/benchmarking/benchmark_service.py`)

Ce service constitue le cœur logique du framework.

*   **Classe `BenchmarkService`** :
    *   **Dépendance :** Prend une instance de `OrchestrationService` dans son constructeur pour pouvoir exécuter les requêtes.
    *   **Méthode `run_suite(...)` :**
        *   Prend en entrée le nom du plugin, le nom de la capacité, et une liste de requêtes à exécuter.
        *   Itère sur chaque requête, l'envoie à l'`OrchestrationService` et mesure le temps de chaque appel.
        *   Collecte chaque résultat dans un `BenchmarkResult`.
        *   Calcule les statistiques agrégées et retourne un objet `BenchmarkSuiteResult` complet.

#### 2.2.3. Script d'Exécution (`src/run_benchmark.py`)

Un point d'entrée CLI a été créé pour faciliter l'utilisation du framework.

*   **Logique du `main` :**
    1.  Initialise le `PluginLoader` et charge les plugins.
    2.  Initialise l'`OrchestrationService`.
    3.  Initialise le `BenchmarkService`.
    4.  Définit une suite de tests (par exemple, des appels à un plugin factice `hello_world`).
    5.  Appelle la méthode `run_suite(...)` du `BenchmarkService`.
    6.  Affiche les résultats agrégés et détaillés de manière lisible dans la console.

### 2.3. Validation de l'Étape 2

La réussite de cette étape sera validée par l'exécution réussie du script `src/run_benchmark.py` et l'affichage d'un rapport de performance cohérent, démontrant l'intégration réussie de tous les nouveaux composants.

### Étape 3 : Implémentation du Guichet de Service et du Mode "Analyse Directe"

*   **Objectif Stratégique :** Activer la première capacité de bout en bout du système consolidé. Le "Guichet de Service" (`OrchestrationService`) doit être capable de recevoir une requête, de la comprendre et d'invoquer directement un plugin standard pour fournir une réponse. Cela valide l'architecture de base et fournit une valeur immédiate.

#### Action 3.1 : Implémentation de la classe `OrchestrationService` (Guichet de Service)

*   **Justification Stratégique :** Conformément au plan (`03_...`), la création de l'`OrchestrationService` est l'action la plus critique pour résoudre le problème de **dispersion de la logique métier** identifié dans l'analyse (`01_...`). Il centralise toutes les demandes entrantes et agit comme le cerveau orchestrateur, masquant la complexité interne.

*   **Checklist Opérationnelle Détaillée et Spécifications Techniques :**

    *   **1. Définition de la Classe et Dépendances (`src/core/services/orchestration_service.py`) :**
        *   Le service dépendra du `PluginRegistry` (pour accéder aux capacités) et potentiellement d'un `StateManager` pour gérer le contexte conversationnel.
        *   **Signature du Constructeur :**
            ```python
            class OrchestrationService:
                def __init__(self, plugin_registry: dict, state_manager: StateManager):
                    self.plugin_registry = plugin_registry
                    self.state_manager = state_manager
            ```

    *   **2. API Interne et Contrat de Données de la Méthode `handle_request` :**
        *   C'est la porte d'entrée unique et asynchrone du service.
        *   **Contrat d'Entrée (Modèle Pydantic `OrchestrationRequest`) :**
            ```python
            from pydantic import BaseModel, Field
            from typing import Dict, Any, Literal

            class OrchestrationRequest(BaseModel):
                mode: Literal["direct_plugin_call", "workflow_execution"] = Field(..., description="Le mode opérationnel souhaité.")
                target: str = Field(..., description="Le nom du plugin ou du workflow à exécuter (ex: 'analysis_tools.analyze_context' ou 'informal_fallacy_workflow').")
                payload: Dict[str, Any] = Field(..., description="Les arguments à passer à la cible.")
                session_id: str | None = Field(None, description="Identifiant de session pour le suivi d'état.")
            ```
        *   **Contrat de Sortie (Modèle Pydantic `OrchestrationResponse`) :**
            ```python
            class OrchestrationResponse(BaseModel):
                status: Literal["success", "error"]
                result: Dict[str, Any] | None = None
                error_message: str | None = None
            ```

    *   **3. Logique de Dispatch Interne (Pseudo-code) :**
        *   La méthode `handle_request` agit comme un aiguilleur basé sur le champ `mode`.
            ```python
            async def handle_request(self, request: OrchestrationRequest) -> OrchestrationResponse:
                if request.mode == "direct_plugin_call":
                    return await self._handle_direct_plugin_call(request)
                elif request.mode == "workflow_execution":
                    return await self._handle_workflow_execution(request)
                else:
                    return OrchestrationResponse(status="error", error_message=f"Mode '{request.mode}' non supporté.")
            ```

    *   **4. Logique du Handler `_handle_direct_plugin_call` (Pseudo-code) :**
        *   Ce handler trouve et exécute une fonction native d'un plugin standard.
            ```python
            async def _handle_direct_plugin_call(self, request: OrchestrationRequest) -> OrchestrationResponse:
                try:
                    plugin_name, function_name = request.target.split('.')
                    if plugin_name not in self.plugin_registry:
                        raise ValueError(f"Plugin '{plugin_name}' non trouvé.")

                    plugin_instance = self.plugin_registry[plugin_name]
                    if not hasattr(plugin_instance, function_name):
                        raise ValueError(f"Fonction '{function_name}' non trouvée dans le plugin '{plugin_name}'.")

                    # Invocation dynamique de la fonction du plugin
                    function_to_call = getattr(plugin_instance, function_name)
                    result = await function_to_call(**request.payload)

                    return OrchestrationResponse(status="success", result=result)
                except Exception as e:
                    return OrchestrationResponse(status="error", error_message=str(e))
            ```

#### Action 3.2 : Mise en place du `Service Bus` (Point d'Entrée API)

*   **Justification Stratégique :** Pour être accessible par des clients externes, l'`OrchestrationService` doit être exposé via un protocole standard. Pour cette première itération, nous utilisons un patron **API Gateway** via une API REST (FastAPI) pour sa simplicité de mise en œuvre. Le terme `Service Bus` est conservé pour marquer l'intention d'évoluer potentiellement vers des patrons asynchrones (Pub/Sub) à l'avenir.

*   **Checklist Opérationnelle Détaillée et Spécifications Techniques :**

    *   **1. Patron de Communication (Itération 1) : API Gateway Synchrone**
        *   **Justification :** Un simple appel HTTP POST synchrone est suffisant pour les premiers cas d'usage (analyse directe, exécution de workflow simple) et plus facile à déboguer. L'évolution vers un Bus asynchrone (RabbitMQ, Kafka) sera envisagée lorsque des workflows de longue durée ou des notifications "fan-out" seront nécessaires.

    *   **2. Endpoint de l'API (`src/api/main.py`)**
        *   **Endpoint :** `POST /v1/execute`
        *   **Description :** Point d'entrée unique pour toutes les requêtes adressées au système.

    *   **3. Contrats de Données (Format des Messages - `src/api/models.py`)**
        *   **Requête (`ApiRequest`) :** Ce modèle encapsule la `OrchestrationRequest` et y ajoute des métadonnées propres à l'API.
            *   **Exemple JSON d'une Requête :**
                ```json
                {
                  "event_id": "evt_cf7a213e-605b-4c63-9523-1d22b4e54a1b",
                  "timestamp": "2025-07-27T14:30:00Z",
                  "source_client": "web_interface_v2",
                  "request_data": {
                    "mode": "direct_plugin_call",
                    "target": "analysis_tools.analyze_context",
                    "payload": {
                      "text_to_analyze": "L'argument de mon adversaire est invalide car il est chauve."
                    },
                    "session_id": "session_xyz789"
                  }
                }
                ```
        *   **Réponse (`ApiResponse`) :**
            *   **Exemple JSON d'une Réponse (Succès) :**
                ```json
                {
                  "request_event_id": "evt_cf7a213e-605b-4c63-9523-1d22b4e54a1b",
                  "status": "success",
                  "response_data": {
                    "analysis_summary": "L'argument est un Ad Hominem.",
                    "severity": "high"
                  }
                }
                ```

    *   **4. Vision pour les Futurs Topics/Queues (Plan d'Évolution)**
        *   Bien que non implémentés dans l'immédiat, les sujets suivants sont identifiés pour une future architecture asynchrone :
            *   `workflow_requests`: File d'attente pour les demandes d'exécution de workflows longs.
            *   `plugin_results`: Topic où les plugins publient leurs résultats intermédiaires.
            *   `system_audits`: Topic pour les événements de logging et de monitoring.
            *   `user_notifications`: Topic pour notifier les clients d'événements importants.

#### Action 3.3 : Validation par les Tests d'Intégration
*   **Justification Stratégique :** Garantir que l'ensemble de la chaîne, du client HTTP au plugin, fonctionne comme prévu.
*   **Test à créer :** Un test dans `tests/integration/test_api.py` utilisera le `TestClient` de FastAPI pour simuler un appel POST sur `/analyze` et valider que la réponse est correcte.

### Étapes 4 à 7 : ...

-   *À détailler lors des phases ultérieures par l'Orchestrateur.*

---

## Étape 2: Migration des Composants Hérités

Cette étape majeure se concentre sur la migration des composants logiques identifiés dans l'architecture héritée. Chaque composant sera transformé en un plugin standard ou un workflow, respectant les nouveaux contrats d'interface et les principes de découplage.

### 2.1. Migration du plugin 'informal_fallacy'

*   **Objectif Stratégique :** Transformer le `FallacyWorkflowPlugin` hérité, qui incarne l'approche "one-shot", en un plugin de workflow moderne, configurable et testable, parfaitement intégré à la nouvelle architecture. Cette migration est emblématique car elle valide la capacité de la nouvelle structure à absorber la logique métier existante tout en corrigeant ses défauts architecturaux.

#### 2.1.1. Analyse de l'Existant (Synthèse du Grounding)

*   **Composant Source :** `argumentation_analysis/agents/plugins/fallacy_workflow_plugin.py`.
*   **Architecture "Legacy" :** Le plugin implémente une logique "one-shot". Sa méthode principale `run_guided_analysis` construit un unique prompt massif contenant le texte à analyser et l'intégralité de la taxonomie des sophismes.
*   **Problématiques Identifiées :**
    1.  **Monolithisme :** La logique, la construction du prompt et l'invocation du Kernel sont dans une seule méthode.
    2.  **Prompts et Configuration en Dur :** Le prompt système et le chemin vers la taxonomie sont codés en dur, rendant toute modification complexe.
    3.  **Dépendances Fortes :** Le plugin dépend d'un `ResultParsingPlugin` pour structurer la sortie, une approche que la nouvelle architecture remplace par des modèles Pydantic plus robustes.
    4.  **Gestion Inefficace des Ressources :** Une instance de Kernel est créée "à la volée" pour chaque analyse, ce qui est sous-optimal.

#### 2.1.2. Plan de Développement Détaillé

*   **Tâche 1 : Analyse d'Impact et Identification des Références**
    *   **Objectif :** Localiser toutes les utilisations du `FallacyWorkflowPlugin` hérité pour préparer sa migration.
    *   **Commande d'analyse :**
        ```bash
        # Rechercher toutes les occurrences du nom du plugin et de son fichier
        rg "FallacyWorkflowPlugin|fallacy_workflow_plugin" .
        ```

*   **Tâche 2 : Opérations sur les Fichiers (Migration et Nettoyage)**
    *   **Objectif :** Déplacer les fichiers sources vers la nouvelle structure et créer les artefacts de configuration requis.
    *   **Checklist des Commandes :**
        ```bash
        # Déplacer le fichier du plugin vers son nouvel emplacement de workflow
        git mv argumentation_analysis/agents/plugins/fallacy_workflow_plugin.py src/core/plugins/workflows/informal_fallacy/plugin.py

        # Créer le manifeste du plugin
        touch src/core/plugins/workflows/informal_fallacy/plugin.yaml

        # Créer le fichier d'initialisation Python
        touch src/core/plugins/workflows/informal_fallacy/__init__.py
        ```

*   **Tâche 3 : Refactoring du Code**
    *   **Objectif :** Adapter le code du plugin pour qu'il respecte les nouveaux contrats de l'architecture.
    *   **Checklist des modifications (`src/core/plugins/workflows/informal_fallacy/plugin.py`) :**
        1.  Changer la déclaration de la classe en `class InformalFallacyWorkflowPlugin(BasePlugin, IWorkflowPlugin):` (en supposant l'existence de ces interfaces dans `src/core/plugins/interfaces.py`).
        2.  Le constructeur doit accepter `OrchestrationService` par injection de dépendances : `def __init__(self, orchestration_service: OrchestrationService):`.
        3.  Remplacer l'ancienne méthode `run_guided_analysis` par une méthode `run_analysis(self, text: str)` conforme à l'interface de workflow.
        4.  Supprimer toute logique de construction de prompt. Le prompt est maintenant géré par les plugins `standard` appelés.
        5.  Supprimer l'instanciation locale du Kernel. Les appels LLM sont délégués.
        6.  Remplacer la logique monolithique par une séquence d'appels à l'`OrchestrationService` (ex: `self.orchestration_service.call(...)`) pour invoquer les plugins standards (`guiding`, `exploration`, `synthesis`).
        7.  Supprimer la dépendance au `ResultParsingPlugin`. La sortie est formatée directement par les plugins `standard` appelés, en utilisant leurs `output_schema` Pydantic.

*   **Tâche 4 : Commit Sémantique**
    *   **Objectif :** Enregistrer cette migration de manière atomique et descriptive.
    *   **Message de Commit :**
        ```
        refactor(plugins): migrate FallacyWorkflowPlugin to new architecture

        Migrates the legacy 'one-shot' FallacyWorkflowPlugin to the new
        architecture as a modern workflow plugin.

        - Moves source file to 'src/core/plugins/workflows/informal_fallacy/'.
        - Creates the 'plugin.yaml' manifest.
        - Refactors the class to implement BasePlugin and IWorkflowPlugin.
        - Replaces monolithic logic with calls to OrchestrationService.
        - Removes dependency on the obsolete ResultParsingPlugin.
        ```


### 2.2. Démantèlement du plugin 'result_parsing' (Obsolète)

> **Statut (2025-07-30) :** ✅ **TERMINÉ**. Cette opération a été exécutée avec succès. Le plugin a été supprimé, ses références nettoyées, et les tests de non-régression ont validé l'opération.

*   **Objectif Stratégique :** Éliminer le `ResultParsingPlugin` hérité. Ce composant est devenu obsolète avec l'adoption de modèles Pydantic et de capacités de parsing directement intégrées dans le Kernel sémantique. Son démantèlement simplifie l'architecture, réduit le couplage inutile et supprime du code mort.

#### 2.2.1. Analyse de l'Existant (Synthèse du Grounding)

*   **Composant Source :** `argumentation_analysis/agents/plugins/result_parsing_plugin.py`.
*   **Architecture "Legacy" :** Le plugin exposait une unique fonction `parse_and_return_fallacy` qui retournait simplement son entrée. Il ne réalisait aucune véritable opération de parsing, agissant comme un relai.
*   **Problématiques Identifiées :**
    1.  **Responsabilité Nulle :** Le plugin ne remplit aucune fonction utile dans la nouvelle architecture. L'analyse et la validation des sorties LLM sont maintenant gérées par des `output_parsers` basés sur Pydantic, qui sont plus robustes et fiables.
    2.  **Couplage Inutile :** Sa simple existence forçait les anciens workflows à dépendre d'un composant superflu.
    3.  **Code Mort :** Il représente une dette technique et une source de confusion pour les nouveaux développeurs.

#### 2.2.2. Plan de Développement Détaillé

*   **Tâche 1 : Analyse d'Impact et Identification des Références**
    *   **Objectif :** Localiser toutes les parties du code qui importent ou tentent d'utiliser le `ResultParsingPlugin` pour assurer un retrait complet.
    *   **Commande d'analyse :**
        ```bash
        # Rechercher toutes les occurrences du nom du plugin et de son fichier
        rg "ResultParsingPlugin|result_parsing_plugin" .
        ```

*   **Tâche 2 : Opérations sur les Fichiers (Migration et Nettoyage)**
    *   **Objectif :** Supprimer de manière définitive tous les fichiers associés à ce plugin obsolète.
    *   **Checklist des Commandes :**
        ```bash
        # Supprimer le fichier source du plugin
        git rm argumentation_analysis/agents/plugins/result_parsing_plugin.py

        # Supprimer le test associé (le chemin peut varier)
        # Supposons l'existence d'un test unitaire pour ce plugin
        git rm tests/unit/legacy/test_result_parsing_plugin.py
        ```

*   **Tâche 3 : Refactoring du Code**
    *   **Objectif :** Supprimer les dépendances à l'ancien plugin dans le code appelant.
    *   **Checklist des modifications (principalement dans l'ancien `FallacyWorkflowPlugin` avant sa migration) :**
        1.  Localiser tous les fichiers identifiés par la `Tâche 1`.
        2.  Supprimer les lignes `import` faisant référence à `ResultParsingPlugin`.
        3.  Supprimer toute logique qui instancie ou appelle le plugin.
        4.  Le code qui utilisait le plugin doit maintenant s'attendre à recevoir des objets Pydantic directement des appels LLM ou des appels à d'autres plugins, rendant le parsing explicite inutile.

*   **Tâche 4 : Commit Sémantique**
    *   **Objectif :** Enregistrer la suppression de ce composant de manière claire.
    *   **Message de Commit :**
        ```
        refactor(core): dismantle obsolete ResultParsingPlugin

        Removes the ResultParsingPlugin which is now obsolete. Its functionality
        is replaced by Pydantic output parsers integrated within the core
        plugins and the semantic kernel, simplifying the architecture and
        removing dead code.
        ```
### 2.3. Migration des Plugins du cycle "Guide-Explore-Synthesize"

> **Statut (2025-07-31) :** ✅ **TERMINÉ**. Cette opération a été exécutée avec succès. Les trois plugins ont été migrés vers la nouvelle architecture standard, leurs consommateurs ont été refactorisés, et les tests de non-régression ont validé l'opération.

*   **Objectif Stratégique :**
    Transformer le trio de plugins `GuidingPlugin`, `ExplorationPlugin`, et `SynthesisPlugin` en plugins **standard** robustes et indépendants. Cette migration est critique car elle préserve une capacité d'analyse avancée et délibérative du système, où un problème est d'abord "trié" (Guide), puis "investigué" en parallèle (Explore), et enfin "résumé" (Synthesize). C'est le cœur d'une approche non-monolithique de l'analyse, rendue explicite et configurable.

#### 2.3.1. Analyse de l'Existant (Synthèse du Grounding)

*   **Composants Source :** `argumentation_analysis/plugins/GuidingPlugin/`, `argumentation_analysis/plugins/ExplorationPlugin/`, `argumentation_analysis/plugins/SynthesisPlugin/`.
*   **Architecture "Legacy" :** Ces plugins fonctionnaient de concert, mais leur orchestration était implicite, gérée par un code client externe non standardisé.
*   **Problématiques Identifiées :**
    1.  **Couplage Implicite :** Le succès du cycle dépendait de l'ordre d'appel correct par un client externe.
    2.  **Manque de Standardisation :** Pas de `plugin.yaml`, pas de contrat d'interface formel via `BasePlugin`.
    3.  **Réutilisabilité Limitée :** Difficile d'utiliser un seul de ces plugins (par exemple, juste le `GuidingPlugin`) de manière fiable.

#### 2.3.2. Plan de Développement Détaillé

*   **Stratégie Générale :** Chacun des trois composants sera migré en un **Plugin Standard** atomique. Un `workflow` dédié (ex: `GuidedAnalysisWorkflow`) pourra ensuite les orchestrer, rendant la séquence d'appels explicite et robuste.

*   **1. Migration du `GuidingPlugin`**
    *   **Tâche 1 : Analyse d'Impact et Identification des Références**
        *   **Commande d'analyse :** `rg "GuidingPlugin"`
    *   **Tâche 2 : Opérations sur les Fichiers**
        *   **Commandes :**
            ```bash
            git mv argumentation_analysis/plugins/GuidingPlugin/GuidingPlugin.py src/core/plugins/standard/guiding_plugin/plugin.py
            touch src/core/plugins/standard/guiding_plugin/plugin.yaml
            touch src/core/plugins/standard/guiding_plugin/__init__.py
            ```
    *   **Tâche 3 : Refactoring du Code**
        *   Adapter la classe pour hériter de `BasePlugin`.
        *   Externaliser le prompt dans un fichier `system.md` dédié.
        *   Remplacer l'instanciation du Kernel par des appels à un client LLM injecté.
    *   **Tâche 4 : Commit Sémantique**
        *   **Message :** `feat(plugins): migrate GuidingPlugin to a standard plugin`

*   **2. Migration du `ExplorationPlugin`**
    *   **Tâche 1 : Analyse d'Impact et Identification des Références**
        *   **Commande d'analyse :** `rg "ExplorationPlugin"`
    *   **Tâche 2 : Opérations sur les Fichiers**
        *   **Commandes :**
            ```bash
            git mv argumentation_analysis/plugins/ExplorationPlugin/ExplorationPlugin.py src/core/plugins/standard/exploration_plugin/plugin.py
            touch src/core/plugins/standard/exploration_plugin/plugin.yaml
            touch src/core/plugins/standard/exploration_plugin/__init__.py
            ```
    *   **Tâche 3 : Refactoring du Code**
        *   Adapter la classe pour hériter de `BasePlugin`.
        *   Externaliser le prompt.
        *   Remplacer les appels directs au `Taxonomy` par une invocation de `TaxonomyExplorerPlugin` via `OrchestrationService`.
    *   **Tâche 4 : Commit Sémantique**
        *   **Message :** `feat(plugins): migrate ExplorationPlugin to a standard plugin`

*   **3. Migration du `SynthesisPlugin`**
    *   **Tâche 1 : Analyse d'Impact et Identification des Références**
        *   **Commande d'analyse :** `rg "SynthesisPlugin"`
    *   **Tâche 2 : Opérations sur les Fichiers**
        *   **Commandes :**
            ```bash
            git mv argumentation_analysis/plugins/SynthesisPlugin/SynthesisPlugin.py src/core/plugins/standard/synthesis_plugin/plugin.py
            touch src/core/plugins/standard/synthesis_plugin/plugin.yaml
            touch src/core/plugins/standard/synthesis_plugin/__init__.py
            ```
    *   **Tâche 3 : Refactoring du Code**
        *   Adapter la classe pour hériter de `BasePlugin`.
        *   Externaliser le prompt de synthèse.
    *   **Tâche 4 : Commit Sémantique**
        *   **Message :** `feat(plugins): migrate SynthesisPlugin to a standard plugin`

### 2.4. Migration des Services Fondamentaux

*   **Objectif Stratégique :**
    Consolider les services de bas niveau, qui sont les piliers de la connaissance et des capacités transverses du système, en Plugins `Standard` unifiés et robustes. Cette migration vise à éliminer la redondance, à clarifier les responsabilités et à fournir des "boîtes à outils" fiables et réutilisables.

#### 2.4.1. Analyse de l'Existant (Synthèse du Grounding)

*   **Composants Source :** `fallacy_taxonomy_service.py`, `fallacy_family_definitions.py`, `fact_verification_service.py`.
*   **Architecture "Legacy" :** Des services dispersés, avec des responsabilités qui se chevauchent (`taxonomy` et `family_definitions`).
*   **Problématiques Identifiées :**
    1.  **Dispersion de la Connaissance :** La taxonomie était séparée des définitions des "familles", complexifiant la maintenance.
    2.  **Contrat Flou :** Le service de vérification des faits n'avait pas d'interface formelle.
    3.  **Dépendances Directes :** Le code appelant était fortement couplé aux implémentations.

#### 2.4.2. Plan de Développement Détaillé

*   **1. Création du `TaxonomyExplorerPlugin`**
    *   **Stratégie :** Fusionner `fallacy_taxonomy_service.py` et `fallacy_family_definitions.py` en un seul Plugin `Standard`.
    *   **Tâche 1 : Analyse d'Impact**
        *   **Commande :** `rg "fallacy_taxonomy_service|fallacy_family_definitions"`
    *   **Tâche 2 : Opérations sur les Fichiers**
        *   **Commandes :**
            ```bash
            # Créer la nouvelle structure
            mkdir -p src/core/plugins/standard/taxonomy_explorer
            touch src/core/plugins/standard/taxonomy_explorer/plugin.yaml
            touch src/core/plugins/standard/taxonomy_explorer/__init__.py
            # Les anciens fichiers seront supprimés après la migration du code
            ```
    *   **Tâche 3 : Refactoring du Code**
        *   Créer la classe `TaxonomyExplorerPlugin` héritant de `BasePlugin`.
        *   Migrer et fusionner la logique des deux services dans les méthodes du plugin (`get_definition`, `get_children`, etc.).
        *   Charger les définitions depuis des fichiers de configuration externes.
        *   Supprimer les anciens fichiers `fallacy_taxonomy_service.py` et `fallacy_family_definitions.py` avec `git rm`.
    *   **Tâche 4 : Commit Sémantique**
        *   **Message :** `feat(plugins): create TaxonomyExplorerPlugin from legacy services`

*   **2. Création du `ExternalVerificationPlugin`**
    *   **Stratégie :** Transformer `fact_verification_service.py` en un Plugin `Standard` avec un contrat clair.
    *   **Tâche 1 : Analyse d'Impact**
        *   **Commande :** `rg "fact_verification_service"`
    *   **Tâche 2 : Opérations sur les Fichiers**
        *   **Commandes :**
            ```bash
            git mv fact_verification_service.py src/core/plugins/standard/external_verification/plugin.py
            touch src/core/plugins/standard/external_verification/plugin.yaml
            touch src/core/plugins/standard/external_verification/__init__.py
            ```
    *   **Tâche 3 : Refactoring du Code**
        *   Adapter la classe en `ExternalVerificationPlugin(BasePlugin)`.
        *   Standardiser la méthode `verify_claim` et son modèle de retour `VerificationResult`.
        *   Rendre le plugin extensible avec un système de "providers".
    *   **Tâche 4 : Commit Sémantique**
        *   **Message :** `feat(plugins): migrate fact_verification_service to ExternalVerificationPlugin`
### 2.5. Consolidation des Outils d'Analyse

*   **Objectif Stratégique :**
    Rationaliser la collection hétérogène d'outils d'analyse pour ne conserver que les plus performants, éliminer la dette technique et les exposer comme des capacités claires et standardisées.

#### 2.5.1. Analyse de l'Existant (Synthèse du Grounding)

*   **Composants Source :** Répertoires `.../tools/analysis/` (Base), `.../tools/analysis/enhanced/`, `.../tools/analysis/new/`.
*   **Architecture "Legacy" :** Trois générations d'outils coexistent, créant confusion et dette technique.
*   **Problématiques Identifiées :**
    1.  **Redondance et Confusion :** Difficile de savoir quelle est la version "officielle" d'un analyseur.
    2.  **Dette Technique :** Les outils "Base" sont obsolètes.
    3.  **Manque d'Évaluation :** Le bénéfice des outils "New" par rapport aux "Enhanced" n'est pas formalisé.

#### 2.5.2. Plan de Développement Détaillé

*   **1. Consolidation des Outils "Enhanced" dans `AnalysisToolsPlugin`**
    *   **Stratégie Cible :** Les outils `complex_fallacy_analyzer.py`, `contextual_fallacy_analyzer.py` et `fallacy_severity_evaluator.py` seront les fonctions natives du **Plugin `Standard` `AnalysisToolsPlugin`**.
    *   **Tâche 1 : Analyse d'Impact**
        *   **Commande :** `rg "complex_fallacy_analyzer|contextual_fallacy_analyzer|fallacy_severity_evaluator"`
    *   **Tâche 2 : Opérations sur les Fichiers**
        *   **Commandes :**
            ```bash
            # Créer la nouvelle structure
            mkdir -p src/core/plugins/standard/analysis_tools
            touch src/core/plugins/standard/analysis_tools/plugin.yaml
            touch src/core/plugins/standard/analysis_tools/__init__.py
            # Le code sera migré dans un seul fichier plugin.py, les anciens seront supprimés
            touch src/core/plugins/standard/analysis_tools/plugin.py
            ```
    *   **Tâche 3 : Refactoring du Code**
        *   Créer la classe `AnalysisToolsPlugin(BasePlugin)`.
        *   Migrer la logique de chaque outil "Enhanced" dans sa propre méthode (`analyze_complex`, `analyze_contextual`, etc.) au sein du plugin.
        *   Supprimer les anciens fichiers avec `git rm`.
    *   **Tâche 4 : Commit Sémantique**
        *   **Message :** `feat(plugins): create AnalysisToolsPlugin from enhanced tools`

*   **2. Démantèlement des Outils "Base" (Obsolètes)**
    *   **Stratégie Cible :** Suppression complète après analyse d'impact.
    *   **Tâche 1 : Analyse d'Impact**
        *   **Commande :** `rg -l "from argumentation_analysis.agents.tools.analysis import"`
    *   **Tâche 2 : Opérations sur les Fichiers**
        *   **Commande :** `git rm argumentation_analysis/agents/tools/analysis/*.py`
    *   **Tâche 3 : Refactoring du Code**
        *   Supprimer toutes les références trouvées lors de l'analyse d'impact.
    *   **Tâche 4 : Commit Sémantique**
        *   **Message :** `refactor(tools): remove obsolete 'base' analysis tools`

*   **3. Gel et Évaluation des Outils "New" (Obsolètes Temporairement)**
    *   **Stratégie Cible :** Ne pas migrer, mais planifier une évaluation formelle.
    *   **Tâche 1 : Création d'une Tâche de R&D**
        *   **Action :** Ajouter un ticket au backlog avec le titre "R&D: Évaluer l'intégration des outils d'analyse 'New' vs 'Enhanced'".
    *   **Tâche 2 : Isolation du Code**
        *   **Action :** S'assurer que les fichiers sous `.../tools/analysis/new/` ne sont pas package, par exemple en utilisant un `.dockerignore`.
    *   **Tâche 3 : Commit Sémantique**
        *   **Message :** `chore(tools): freeze 'new' analysis tools pending formal evaluation`
## Étape 3: Validation et Tests

Cette étape cruciale formalise la stratégie pour garantir la qualité, la non-régression et la performance du système refactorisé. Elle s'appuie sur une pyramide de tests granulaires pour valider chaque aspect du système, du composant individuel au workflow complet.

### 3.1. Tests Unitaires (TU)

L'objectif des tests unitaires est de valider chaque composant en isolation totale. Ils seront placés dans `tests/unit/` et utiliseront intensivement des mocks pour isoler les dépendances.

#### 3.1.1. `OrchestrationService` (`tests/unit/core/services/test_orchestration_service.py`)

*   **TU-OS-01 : Enregistrement d'un plugin**
    *   **Scénario :** Vérifier que le service peut enregistrer un plugin valide fourni par un `PluginRegistry` mocké.
    *   **Assertions :**
        *   Le plugin est présent dans l'état interne du service.
*   **TU-OS-02 : Exécution d'un workflow simple (1 plugin)**
    *   **Scénario :** Simuler un `OrchestrationRequest` pour un appel direct à une capacité de plugin.
    *   **Dépendances Mockées :** `PluginRegistry` avec un faux plugin.
    *   **Assertions :**
        *   La méthode `handle_request` appelle la bonne méthode du bon plugin.
        *   Le `payload` est transmis correctement.
        *   La `OrchestrationResponse` est formatée avec le statut `success` et le résultat du plugin.
*   **TU-OS-03 : Gestion d'une dépendance manquante (plugin non trouvé)**
    *   **Scénario :** Tenter d'exécuter une capacité d'un plugin qui n'est pas dans le registre.
    *   **Assertions :**
        *   Le service retourne une `OrchestrationResponse` avec le statut `error`.
        *   Le `error_message` indique clairement que le plugin est introuvable.
*   **TU-OS-04 : Validation du contrat d'entrée**
    *   **Scénario :** Envoyer une requête avec un `payload` qui ne correspond pas au `input_schema` de la capacité du plugin.
    *   **Assertions :**
        *   Le service doit intercepter l'erreur (idéalement via une validation Pydantic) et retourner une réponse `error`.
        *   Le message d'erreur doit spécifier l'inadéquation du contrat.

#### 3.1.2. `PluginLoader` (`tests/unit/core/plugins/test_plugin_loader.py`)

*   **TU-PL-01 : Chargement d'un plugin valide**
    *   **Scénario :** Utiliser une fixture `pytest` pour créer une structure de répertoire temporaire avec un plugin valide (code + `plugin.yaml`).
    *   **Assertions :**
        *   Le loader découvre et charge le plugin.
        *   Le registre retourné contient une instance du plugin.
*   **TU-PL-02 : Rejet d'un plugin avec manifeste `plugin.yaml` invalide**
    *   **Scénario :** Créer un `plugin.yaml` avec des champs manquants (ex: `metadata.name`).
    *   **Assertions :**
        *   Le loader ignore le plugin.
        *   Un avertissement (log `WARNING`) est généré.
        *   Le plugin n'est pas présent dans le registre retourné.
*   **TU-PL-03 : Détection de dépendances cycliques (avancé)**
    *   **Scénario :** Créer deux plugins factices où A dépend de B et B dépend de A via leur manifeste.
    *   **Assertions :**
        *   Le `PluginLoader` doit lever une exception `CyclicDependencyError` explicite.

#### 3.1.3. `BenchmarkService` (`tests/unit/benchmarking/test_benchmark_service.py`)

*   **TU-BS-01 : Mesure de la latence d'une fonction**
    *   **Scénario :** Exécuter une suite de benchmarks sur une capacité mockée qui a un temps de sommeil (`time.sleep`) défini.
    *   **Dépendances Mockées :** `OrchestrationService`.
    *   **Assertions :**
        *   Le `BenchmarkSuiteResult` retourné contient des `duration_ms` cohérentes avec le temps de sommeil.
        *   Les statistiques agrégées (moyenne, min, max) sont calculées correctement.
*   **TU-BS-02 : Enregistrement correct des métriques**
    *   **Scénario :** Exécuter une suite de tests avec des succès et des échecs (l'appel mocké à l'`OrchestrationService` lève une exception).
    *   **Assertions :**
        *   Le `BenchmarkSuiteResult` reporte précisément le nombre de `successful_runs` et `failed_runs`.
        *   Les `BenchmarkResult` individuels contiennent le statut `is_success` et le message `error` corrects.

### 3.2. Tests d'Intégration (TI)

Les tests d'intégration valident l'interaction entre les différents composants réels du système. Ils seront situés dans `tests/integration/` et utiliseront une base de données de test et des plugins réels mais sur des données contrôlées.

#### 3.2.1. `TI-Workflow-Standard`

*   **Scénario :** Un client envoie une requête HTTP à l'API (`/v1/execute`) pour une analyse de sophisme simple.
*   **Flux Système :** API (FastAPI `TestClient`) -> `OrchestrationService` -> `fallacy_analysis_plugin` (instance réelle).
*   **Plugins impliqués :**
    *   `fallacy_analysis_plugin`: Plugin `standard` qui prend un texte et retourne une analyse.
*   **Assertions :**
    1.  La requête HTTP retourne un code de statut 200.
    2.  L'`OrchestrationService` sélectionne et appelle correctement le `fallacy_analysis_plugin`.
    3.  La réponse JSON finale est conforme au `output_schema` défini pour la capacité d'analyse, validant le contrat de bout en bout.

#### 3.2.2. `TI-Workflow-Complexe`

*   **Scénario :** Un client demande une génération de contre-argument guidée via l'API, un processus nécessitant l'enchaînement de plusieurs plugins.
*   **Flux Système :** API -> `OrchestrationService` -> `CounterArgumentWorkflow` (plugin de `workflow`).
*   **Plugins impliqués :**
    *   `CounterArgumentWorkflow`: Le workflow qui orchestre la séquence.
    *   `guiding_plugin`: Identifie la stratégie de contre-argument.
    *   `exploration_plugin`: Recherche des exemples ou des données pertinentes.
    *   `synthesis_plugin`: Construit le contre-argument final.
*   **Assertions :**
    1.  Le `CounterArgumentWorkflow` est bien appelé.
    2.  Les logs ou un état interne observable montrent que les plugins `guiding`, `exploration`, et `synthesis` sont appelés dans le bon ordre.
    3.  Les données de sortie d'un plugin (ex: la stratégie du `guiding_plugin`) sont correctement transmises comme données d'entrée au plugin suivant.
    4.  La réponse finale est une synthèse cohérente produite par le `synthesis_plugin`.

#### 3.2.3. `TI-Benchmark-Complet`

*   **Scénario :** Exécuter le script `src/run_benchmark.py` configuré pour lancer les deux workflows (`TI-Workflow-Standard` et `TI-Workflow-Complexe`) en mode benchmark.
*   **Flux Système :** `run_benchmark.py` -> `BenchmarkService` -> `OrchestrationService` -> (Plugins réels).
*   **Assertions :**
    1.  Le script s'exécute jusqu'à la fin sans erreur.
    2.  Des rapports de benchmark (ex: fichiers JSON ou sorties console) sont générés.
    3.  Les rapports contiennent des métriques de performance (latence, nombre de runs) pour chaque plugin et chaque capacité exécutée dans les workflows.

### 3.3. Tests de Contrat

Ces tests garantissent la stabilité des interfaces de données, qui sont le fondement de la communication inter-services.

*   **Objectif :** Valider que chaque modèle Pydantic de requête et de réponse dans `src/core/contracts.py` est bien formé et rejette les données invalides.
*   **Stratégie d'implémentation (`tests/unit/core/test_contracts.py`) :**
    1.  Pour chaque `*Request` (ex: `OrchestrationRequest`):
        *   Créer un test qui l'instancie avec des données valides et vérifier que l'objet est créé.
        *   Créer des tests qui tentent de l'instancier avec des données invalides (type incorrect, champ manquant) et vérifier qu'une exception `pydantic.ValidationError` est levée.
    2.  Pour chaque `*Response` (ex: `OrchestrationResponse`):
        *   Assurer la validation de la structure de la même manière.
    *   Ces tests agissent comme une documentation vivante et un garde-fou contre les changements cassants accidentels sur les API de données.

## Étape 4: Stratégie de Déploiement et d'Opérationnalisation
#### Plan d'Implémentation Détaillé

Cette section traduit la stratégie de déploiement en tâches techniques concrètes et actionnables.

**Tâche 1 : Configuration de l'Environnement de Production avec Docker**

*   **Objectif :** Créer des artéfacts Docker reproductibles et optimisés pour la production.
*   **Checklist Technique :**
    *   **1. Création du `Dockerfile` pour l'application principale :**
        *   Utiliser une approche **multi-stage build** pour minimiser la taille de l'image finale.
        *   **Stage 1 (`builder`) :** Installer les dépendances (y compris de développement) et construire les éventuels artéfacts.
        *   **Stage 2 (`runtime`) :** Partir d'une image Python "slim", copier uniquement les dépendances de production et le code source de l'application depuis le stage `builder`.
        *   Définir un utilisateur non-root pour l'exécution du service.
    *   **2. Création du `docker-compose.prod.yml` :**
        *   Définir le service de l'application principale, en s'appuyant sur le `Dockerfile` créé.
        *   Orchestrer les services dépendants (ex: une instance de Redis pour la gestion d'état, une base de données, etc.).
        *   Gérer les variables d'environnement et les secrets de manière sécurisée (ex: via des fichiers `.env` ou des secrets Docker).

**Tâche 2 : Implémentation du Pipeline CI/CD avec GitHub Actions**

*   **Objectif :** Mettre en place un pipeline automatisé à 4 étages pour le build, le test et le déploiement.
*   **Checklist Technique :**
    *   **1. Création du fichier de workflow `.github/workflows/ci-cd.yml` :**
    *   **2. Implémentation de l'étage "Build" :**
        *   **`job: build`**:
        *   Construire l'image Docker en utilisant le `Dockerfile`.
        *   Tagger l'image avec l'identifiant du commit (`github.sha`) et le tag `latest`.
        *   Pousser l'image vers un registre de conteneurs (ex: GitHub Container Registry).
    *   **3. Implémentation de l'étage "Test" :**
        *   **`job: test`** (dépendant de `build`) :
        *   Lancer un conteneur basé sur l'image fraîchement construite.
        *   Exécuter les tests unitaires et d'intégration à l'intérieur de ce conteneur pour valider l'artéfact lui-même.
    *   **4. Implémentation de l'étage "Staging (Déploiement Blue)" :**
        *   **`job: deploy-staging`** (dépendant de `test`) :
        *   Créer un script de déploiement (ex: `scripts/deploy.sh`).
        *   Ce script se connectera au serveur de staging, tirera la nouvelle image Docker, et lancera la nouvelle version de l'application sur un port différent ou avec un nom de conteneur identifié comme "blue". L'ancienne version "green" continue de servir le trafic.
    *   **5. Implémentation de l'étage "Production (Go-Live Green)" :**
        *   **`job: deploy-production`** (dépendant de `deploy-staging`) :
        *   Déclenché manuellement via `workflow_dispatch` pour un contrôle maximal.
        *   Le même script `scripts/deploy.sh` sera utilisé, mais il ciblera l'environnement de production.
        *   La tâche principale de cette étape est de **basculer le trafic** (ex: en reconfigurant un reverse proxy comme Nginx ou en changeant une route au niveau du load balancer) de l'ancienne version ("green") vers la nouvelle ("blue"). La version "blue" devient alors la nouvelle version "green".

**Tâche 3 : Formalisation de la Procédure de Rollback**

*   **Objectif :** Disposer d'une procédure claire et rapide pour revenir à la version stable précédente en cas d'incident.
*   **Checklist Technique :**
    *   **1. Capitaliser sur le versioning des images Docker :**
        *   La stratégie de tagging des images Docker avec l'identifiant de commit Git (`github.sha`) est cruciale. Elle permet d'identifier sans ambiguïté la version de code associée à chaque image.
    *   **2. Création d'une action de Rollback dans le pipeline GitHub Actions :**
        *   Ajouter un nouveau `job` manuel (`workflow_dispatch`) dans `ci-cd.yml` nommé `rollback-production`.
        *   Ce job prendra en entrée un **identifiant de commit** de la version stable précédente à redéployer.
        *   Le script de déploiement sera invoqué avec un paramètre spécifique pour le rollback, lui indiquant de tirer l'image Docker tagguée avec l'identifiant de commit fourni et de la définir comme la version "green" active.


#### Plan d'Implémentation Détaillé

*   **Tâche 1 : Installation et Configuration de `pytest-benchmark`.**
    *   **Objectif :** Intégrer l'outil de benchmark de base dans l'environnement de développement et de CI.
    *   **Checklist Technique :**
        *   Ajouter `pytest-benchmark` dans le fichier de dépendances de développement (ex: `requirements-dev.txt`).
        *   Dans `pytest.ini`, configurer les options souhaitées, comme le format de sortie `json` et un chemin pour les rapports.
        *   Exemple de configuration `pytest.ini` :
            ```ini
            [pytest]
            benchmark_output_dir = benchmarking/reports
            benchmark_json_path = benchmarking/reports/latest.json
            ```
    *   **Validation :** Créer un test de benchmark simple qui utilise la fixture `benchmark` pour s'assurer que l'intégration fonctionne.

*   **Tâche 2 : Création du Scénario de Benchmark Comparatif.**
    *   **Objectif :** Développer un script de test qui mesure et compare objectivement la performance de l'ancienne et de la nouvelle architecture sur une tâche identique.
    *   **Checklist Technique :**
        *   Créer un nouveau répertoire `benchmarking/`.
        *   Créer un script `benchmarking/benchmark_legacy_vs_new.py`.
        *   Ce script définira deux fonctions de test `pytest` : `test_benchmark_legacy_workflow` et `test_benchmark_new_workflow`.
        *   Chacune de ces fonctions recevra la fixture `benchmark` et exécutera une tâche d'analyse complète sur le même texte d'entrée, une fois avec l'ancien `FallacyWorkflowPlugin`, une fois avec le nouveau.
        *   La sortie du benchmark comparera directement les métriques (latence, etc.) des deux systèmes.

*   **Tâche 3 : Développement du Décorateur de Suivi de Tokens.**
    *   **Objectif :** Créer un outil réutilisable pour mesurer la métrique la plus coûteuse : la consommation de tokens des LLMs.
    *   **Checklist Technique :**
        *   Créer un nouveau module : `src/core/utils/benchmarking.py`.
        *   Y développer un décorateur `@track_token_usage`.
        *   Ce décorateur interceptera les appels aux fonctions qu'il décore. Il devra inspecter les arguments pour trouver le `prompt` d'entrée et la `completion` de sortie.
        *   Il utilisera une bibliothèque de `tokenization` (ex: `tiktoken`) pour compter les tokens d'entrée et de sortie.
        *   Les résultats (nombre de tokens in/out, fonction appelée) seront loggués dans un format structuré ou stockés pour analyse.
    *   **Validation :** Un test unitaire pour le décorateur validera qu'il compte correctement les tokens pour un exemple d'entrée/sortie donné.
Cette nouvelle section définit l'épine dorsale opérationnelle du système. Elle décrit comment les nouvelles fonctionnalités seront intégrées, testées, déployées et surveillées de manière automatisée et fiable, garantissant ainsi la stabilité et la maintenabilité du système à long terme.

### 4.1. Pipeline d'Intégration et de Déploiement Continus (CI/CD)

Le pipeline CI/CD est le mécanisme automatisé qui transforme le code source en un service fonctionnel en production. Il est conçu pour être robuste, rapide et transparent.

*   **Technologie Cible :** GitHub Actions, pour son intégration native avec le dépôt de code.
*   **Déclenchement du Pipeline :**
    *   `on: push` sur la branche `main` : Déclenche le déploiement complet vers la production.
    *   `on: pull_request` vers la branche `main` : Déclenche les étapes de build et de test pour valider la contribution avant la fusion.

**Étapes du Pipeline :**

1.  **Étape 1 : Build & Analyse Statique**
    *   **Objectif :** Valider la qualité et la conformité du code.
    *   `job: build-and-lint`
    *   **Actions :**
        *   Installation de l'environnement Python.
        *   Installation des dépendances du projet (ex: `pip install -r requirements.txt`).
        *   Exécution d'un linter (ex: `flake8`) pour garantir le respect des conventions de style.
        *   Exécution d'un analyseur de sécurité (ex: `bandit`) pour détecter les vulnérabilités courantes.

2.  **Étape 2 : Tests Automatisés**
    *   **Objectif :** Garantir la non-régression et la correction fonctionnelle du code.
    *   `job: test` (dépend de `build-and-lint`)
    *   **Actions :**
        *   Exécution de la suite de **tests unitaires** (`pytest tests/unit`).
        *   Exécution de la suite de **tests d'intégration** (`pytest tests/integration`).
        *   (Optionnel) Exécution de la suite de **tests de bout en bout** (`pytest tests/e2e`).
        *   Génération d'un rapport de couverture de code (`pytest-cov`).
        *   Archivage des résultats des tests et du rapport de couverture comme artéfacts du pipeline pour analyse.

3.  **Étape 3 : Packaging de l'Application**
    *   **Objectif :** Créer un artéfact de déploiement portable et reproductible.
    *   `job: package` (dépend de `test`)
    *   **Actions :**
        *   Création d'une image Docker contenant l'application FastAPI et ses dépendances.
        *   Le `Dockerfile` s'assurera que l'ensemble du répertoire `src` est inclus pour permettre la découverte dynamique des plugins.
        *   Tag de l'image Docker avec l'identifiant du commit Git (`${{ github.sha }}`).
        *   Publication de l'image sur un registre de conteneurs (ex: GitHub Container Registry, Docker Hub).

4.  **Étape 4 : Déploiement par Environnement**
    *   **Objectif :** Déployer l'application de manière sécurisée et contrôlée.
    *   `job: deploy-staging` (dépend de `package`, s'exécute uniquement sur `pull_request`)
        *   **Actions :** Déploiement de l'image Docker sur un environnement de `Staging` (pré-production).
        *   Permet une validation manuelle ou des tests automatisés supplémentaires dans un environnement quasi-réel.
    *   `job: deploy-production` (dépend de `package`, s'exécute uniquement sur `push` à `main`)
        *   **Actions :** Déploiement de l'image Docker sur l'environnement de `Production`.
        *   **Contrôle d'Accès :** Cette étape peut être protégée par une approbation manuelle requise via les environnements GitHub Actions pour éviter les déploiements accidentels.
## 4. Prochaines Étapes

1.  **Transition:** Passage du rôle `Architect` au rôle `Orchestrator` pour la planification détaillée.
2.  **Détailler Étape 1:** L'Orchestrateur doit valider, affiner et préparer les tâches de l'Étape 1 pour l'exécution.
3.  **Implémentation:** Lancement de la phase de codage.
### 4.2. Stratégie de Logging, Monitoring et Alerting

Une fois le système déployé, il est crucial de surveiller son comportement pour garantir sa fiabilité, ses performances et son coût.

**1. Politique de Logging :**

*   **Format :** Les logs seront structurés en **JSON**. Ce format facilite le parsing et l'indexation par les systèmes de gestion de logs (ex: ELK Stack, Splunk, Datadog).
*   **Niveaux de Log :** Utilisation des niveaux standards (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`). Le niveau de log sera configurable par environnement (ex: `INFO` en Production, `DEBUG` en Staging).
*   **Informations Clés à Inclure :**
    *   `timestamp`: Horodatage UTC de l'événement.
    *   `level`: Niveau du log.
    *   `message`: Description de l'événement.
    *   `transaction_id`: Un identifiant unique pour tracer une requête à travers tous les services.
    *   `service_name`: Nom du service émetteur (ex: `OrchestrationService`).
    *   `plugin_name`: Si applicable, nom du plugin ou du workflow exécuté.

**2. Métriques de Monitoring Clés (KPIs) :**

Un tableau de bord centralisé (ex: Grafana, Datadog) affichera les métriques suivantes :

*   **Métriques Techniques (Santé du Système) :**
    *   **Latence des appels API :** Distribution (moyenne, p95, p99) du temps de réponse du `Service Bus`.
    *   **Taux d'erreur :** Pourcentage de requêtes API retournant des erreurs 5xx.
    *   **Consommation CPU/Mémoire :** Utilisation des ressources par les conteneurs de l'application.
    *   **Disponibilité du service :** Uptime du `Service Bus`.

*   **Métriques Fonctionnelles (Performance Métier) :**
    *   **Nombre de workflows exécutés :** Volume d'analyses traitées, ventilé par type de workflow.
    *   **Performance par type de plugin :** Latence et taux d'erreur spécifiques à chaque plugin majeur.
    *   **Taux de succès des analyses :** Pourcentage d'analyses se terminant sans erreur fonctionnelle.
    *   **Coût estimé des appels LLM :** Suivi de la consommation de tokens et estimation des coûts, si applicable.

**3. Stratégie d'Alerting :**

Les alertes proactives permettent de détecter les problèmes avant qu'ils n'impactent les utilisateurs.

*   **Conditions de Déclenchement des Alertes :**
    *   **Seuils d'erreur :** Taux d'erreur API dépassant X% sur une période de Y minutes.
    *   **Latence anormale :** Latence p99 dépassant un seuil critique.
    *   **Panne de service :** Le `Service Bus` ne répond plus aux health checks.
    *   **Ressources Critiques :** Utilisation de CPU ou de mémoire dépassant 90% pendant une période prolongée.
*   **Canaux de Notification :**
    *   **Alertes Critiques :** Notification immédiate sur un canal dédié (ex: Slack `#alerts-prod`, PagerDuty) pour une intervention rapide.
    *   **Avertissements (Warnings) :** Notification sur un canal moins urgent (ex: Slack `#warnings-prod`, email) pour investigation.
## Étape 5: Gouvernance du Projet, Planification et Gestion des Risques

Cette section finale établit le cadre de gestion nécessaire pour piloter cette refactorisation complexe. Elle ne se contente pas de définir le "quoi" et le "comment" techniques, mais aussi le "qui", le "quand" et le "comment" nous gérons les imprévus. C'est le plan d'exécution qui garantit que la vision technique se traduit en une réalité livrée dans les temps, dans le budget et avec la qualité requise.
### 5.1. Plan de Phasage Macro

Le projet sera exécuté en quatre grandes phases séquentielles, avec des activités qui peuvent se dérouler en parallèle au sein de chaque phase. Cette approche permet de livrer de la valeur de manière incrémentale tout en maîtrisant la complexité.

**Phase 1 : Fondations et Industrialisation Initiale (Dépendante de l'Étape 1)**
*   **Objectif :** Construire le squelette technique et les autoroutes du déploiement.
*   **Livrables Clés :**
    *   Nouvelle arborescence de répertoires (`core`, `agents`).
    *   `PluginLoader` et `AgentLoader` fonctionnels et testés unitairement.
    *   Pipeline CI/CD de base (Build, Lint, Tests Unitaires) opérationnel.
*   **Pré-requis :** Aucun. C'est le point de départ.

**Phase 2 : Migration des Services Cœur et Validation Continue (Dépendante des Étapes 2 & 3)**
*   **Objectif :** Migrer les briques logicielles fondamentales et valider leur intégration.
*   **Livrables Clés :**
    *   `TaxonomyExplorerPlugin`, `AnalysisToolsPlugin` et autres plugins standard migrés et testés.
    *   `OrchestrationService` (Guichet de Service) implémenté, capable d'invoquer les plugins standard.
    *   `Service Bus` (API) exposant un premier endpoint fonctionnel.
    *   Tests d'intégration validant la chaîne de communication.
*   **Pré-requis :** Phase 1 terminée.

**Phase 3 : Migration des Workflows et Premiers Déploiements (Dépendante des Étapes 2, 3 & 4)**
*   **Objectif :** Migrer la logique métier complexe et commencer à servir des analyses complètes.
*   **Livrables Clés :**
    *   `InformalFallacyWorkflowPlugin` et autres workflows migrés.
    *   Packaging de l'application (image Docker).
    *   Déploiement sur un environnement de Staging.
*   **Pré-requis :** Phase 2 terminée. Les plugins standard dont dépendent les workflows doivent être disponibles.

**Phase 4 : Opérationnalisation et Benchmarking (Dépendante des Étapes 3 & 4)**
*   **Objectif :** Stabiliser le système, surveiller ses performances et le préparer pour la production.
*   **Livrables Clés :**
    *   Framework de benchmarking implémenté et premiers rapports comparatifs.
    *   Système de logging et de monitoring configuré.
    *   Déploiement en production.
*   **Pré-requis :** Phase 3 terminée.
### 5.2. Analyse des Risques et Stratégies de Mitigation

Un projet de cette ampleur comporte des risques inhérents. Les identifier en amont permet de mettre en place des stratégies pour en minimiser l'impact.

**Risques Techniques**

1.  **Risque : Régression de performance.**
    *   *Description :* La nouvelle architecture, bien que plus modulaire, pourrait introduire une latence supérieure à celle du système "one-shot" hérité.
    *   *Mitigation :* Mise en place d'un **framework de benchmarking (Étape 3.2)** dès le début du projet. Des tests de performance comparatifs seront exécutés à chaque migration majeure pour garantir une performance au moins équivalente.

2.  **Risque : Complexité de migration sous-estimée.**
    *   *Description :* La logique interne de certains composants hérités pourrait se révéler plus complexe ou plus couplée que prévu, ralentissant leur migration.
    *   *Mitigation :* L'approche de migration est **itérative**. Chaque plugin est migré et testé individuellement. Un **PoC (Proof of Concept)** sera réalisé sur le workflow le plus complexe (`InformalFallacyWorkflowPlugin`) pour valider l'approche avant de généraliser.

**Risques Organisationnels / Humains**

3.  **Risque : Résistance au changement.**
    *   *Description :* L'équipe pourrait être réticente à adopter la nouvelle structure et les nouveaux patterns, préférant les anciennes méthodes.
    *   *Mitigation :* **Documentation claire et vivante** (ce plan, `CONTRIBUTING.md`). Organisation de **sessions de revue de code en pair** et de **démos internes** régulières pour acculturer l'équipe à la nouvelle architecture. L'automatisation via la **CI/CD (Étape 4.1)** contraindra également l'adoption des nouvelles normes de qualité.

4.  **Risque : Perte de connaissance implicite.**
    *   *Description :* Une partie de la logique et du comportement du système hérité n'est pas documentée et réside uniquement dans la connaissance des développeurs.
    *   *Mitigation :* Le processus de migration lui-même sert de **catalyseur de documentation**. En transformant le code en plugins, nous sommes forcés d'expliciter les contrats, les dépendances et les configurations, qui sont ensuite inscrits dans le code et les fichiers de personnalité.

**Risques de Planification**

5.  **Risque : Dépendances externes non satisfaites.**
    *   *Description :* Un changement d'API d'un service LLM externe ou d'une autre dépendance pourrait bloquer une partie de la migration.
    *   *Mitigation :* **Architecture découplée**. La logique métier est isolée des clients d'API externes. Des **tests d'intégration** réguliers dans la CI/CD permettront de détecter rapidement une rupture de contrat avec un service externe.

6.  **Risque : "Effet tunnel" et retards en cascade.**
    *   *Description :* Les phases étant séquentielles, un retard sur une phase initiale pourrait décaler l'ensemble du projet.
    *   *Mitigation :* **Phasage macro** avec des livrables clairs à la fin de chaque phase. Les **rituels de projet (voir 5.3)** comme les stand-ups quotidiens et les revues de sprint permettront d'identifier les blocages très tôt et de réagir rapidement.
### 5.3. Modèle de Gouvernance et de Prise de Décision

Une structure claire de rôles, de rituels et de processus décisionnels est essentielle pour assurer l'alignement et la vélocité de l'équipe.

**Rôles et Responsabilités Clés**

*   **Product Owner :**
    *   *Responsabilité :* Définit la vision fonctionnelle, priorise le backlog de migration et valide que les fonctionnalités livrées répondent aux besoins métier. Il est le garant du "quoi".
*   **Architecte / Tech Lead :**
    *   *Responsabilité :* Gardien de la vision technique définie dans ce plan. S'assure de la cohérence de l'architecture, de la qualité du code et de la pertinence des choix techniques. Il est le garant du "comment".
*   **Équipe de Développement :**
    *   *Responsabilité :* Implémente, teste et documente les composants du système. Participe activement aux rituels pour assurer la transparence et la collaboration.

**Rituels de Projet**

Le projet adoptera un cadre de travail inspiré de Scrum pour favoriser un rythme de développement itératif et prédictible.

*   **Daily Stand-ups (15 min) :**
    *   *Fréquence :* Quotidienne.
    *   *Objectif :* Synchronisation rapide de l'équipe pour partager les progrès, les obstacles et les objectifs de la journée.
*   **Sprint Planning (2 heures) :**
    *   *Fréquence :* Toutes les deux semaines.
    *   *Objectif :* L'équipe sélectionne les tâches du backlog à réaliser pour le sprint à venir, en se basant sur les priorités du Product Owner et la capacité de l'équipe.
*   **Sprint Review / Demo (1 heure) :**
    *   *Fréquence :* À la fin de chaque sprint.
    *   *Objectif :* L'équipe présente les fonctionnalités terminées aux parties prenantes pour recueillir des retours.
*   **Revues d'Architecture (1 heure) :**
    *   *Fréquence :* Ad-hoc, selon les besoins.
    *   *Objectif :* Discuter et valider les décisions d'architecture importantes (ex: choix d'une nouvelle technologie, modification d'une interface centrale) avant implémentation.

**Processus de Prise de Décision**

*   **Décisions Techniques Courantes :** Prises de manière autonome par l'équipe de développement, en accord avec les principes de ce plan.
*   **Décisions Techniques Structurantes :** Discutées et validées lors des **Revues d'Architecture**, sous la direction du Tech Lead.
*   **Arbitrages Fonctionnels vs Techniques :** Si un choix technique a un impact significatif sur le périmètre fonctionnel ou le planning, la décision est prise conjointement par le **Product Owner** et le **Tech Lead**. La priorité est donnée à la solution qui préserve le mieux les objectifs à long terme du projet tout en répondant aux besoins immédiats.

### 5.4 Plan d'Implémentation Détaillé de la Gouvernance

Cette section traduit les concepts stratégiques de gouvernance en tâches techniques concrètes, prêtes à être intégrées dans un backlog de projet.

**Tâche 1 : Mise en Œuvre du Logging Structuré**

*   **Objectif :** Standardiser la collecte de logs pour permettre un monitoring et un débogage efficaces.
*   **Checklist Technique :**
    *   **1.1. Définir le Schéma de Log JSON :** Le format de log suivant est adopté comme standard pour tous les services.
        ```json
        {
          "timestamp": "2025-07-27T15:30:00.123Z",
          "level": "INFO",
          "service_name": "OrchestrationService",
          "request_id": "req-d0b5e3f8-c2a1-4e7d-9d4a-5f1b6a2c3d4e",
          "plugin_name": "analysis_tools.analyze_context",
          "duration_ms": 125,
          "token_in": 512,
          "token_out": 256,
          "error_details": null
        }
        ```
    *   **1.2. Configurer le Logger Central :**
        *   **Tâche :** Dans `src/core/utils/logging.py`, configurer `structlog` pour qu'il formate automatiquement tous les logs selon le schéma JSON défini ci-dessus.
        *   **Tâche :** S'assurer que le logger est initialisé au démarrage de l'application et qu'une instance est facilement accessible pour tous les composants via une fonction (ex: `get_logger()`).

**Tâche 2 : Configuration du Monitoring et des Alertes**

*   **Objectif :** Mettre en place une visibilité en temps réel sur la santé et la performance du système.
*   **Checklist Technique :**
    *   **2.1. Lister les KPIs Clés à Monitorer :**
        *   **Latence (par service/plugin) :** moyenne, p95, p99.
        *   **Taux d'erreur (par service/plugin) :** pourcentage de requêtes échouées.
        *   **Coût par Appel (par service/plugin) :** Calculé en agrégeant `token_in` et `token_out`, et en appliquant les tarifs du modèle LLM.
    *   **2.2. Créer le Tableau de Bord Principal :**
        *   **Outil :** Grafana (ou équivalent comme Datadog).
        *   **Tâche :** Créer un nouveau tableau de bord "System Health" affichant les KPIs listés ci-dessus.
        *   **Visualisations :** Graphiques temporels pour la latence et les erreurs, compteurs pour les coûts.
    *   **2.3. Définir les Règles d'Alerting :**
        *   **Tâche :** Configurer les règles suivantes dans l'outil de monitoring.
        *   `[P1 - CRITICAL]` Si le taux d'erreur du `Service Bus` > 5% sur 5 minutes.
        *   `[P1 - CRITICAL]` Si la latence p99 de `OrchestrationService` > 1000ms sur 5 minutes.
        *   `[P2 - WARNING]` Si le coût par appel pour un plugin spécifique augmente de >20% sur une heure.

**Tâche 3 : Initialisation de la Gestion de Projet**

*   **Objectif :** Mettre en place l'outil de gestion de projet et peupler le backlog initial pour lancer le développement.
*   **Checklist Technique :**
    *   **3.1. Configurer le Tableau de Bord de Projet :**
        *   **Outil :** GitHub Projects.
        *   **Tâche :** Créer un nouveau tableau de bord de projet nommé "Refactorisation Système Sophismes".
        *   **Colonnes :** `Backlog`, `À faire (Sprint)`, `En cours`, `En revue`, `Terminé`.
    *   **3.2. Peupler le Backlog Initial :**
        *   **Tâche :** Créer un script ou une procédure manuelle pour transformer chaque tâche définie dans les sections "Plan d'Implémentation Détaillé" des Étapes 1 à 5 de ce document en une Tâche ou une User Story dans le tableau de bord GitHub Projects.
        *   **Exemple de transformation :** La "Tâche 1 : Mise en Œuvre du Logging Structuré" devient une User Story "En tant que développeur, je veux des logs structurés en JSON pour pouvoir déboguer les requêtes efficacement." avec ses sous-tâches techniques.

---



### Étape 4: Gouvernance du Code et Intégration Continue (CI/CD)

Cette section établit les processus de gouvernance et d'intégration continue qui garantiront la qualité, la cohérence et la stabilité du code tout au long du projet de refactorisation. Elle vise à créer un cadre de travail rigoureux mais agile, où chaque contribution est validée avant son intégration.

#### Stratégie de Branches (GitFlow)

Pour organiser le développement et sécuriser le code de production, le projet adoptera une stratégie de branches basée sur le modèle GitFlow. Ce modèle fournit un cadre robuste pour la gestion des développements parallèles, des versions et des correctifs urgents.

*   **`main`**:
    *   **Rôle :** Branche de production. Le code sur `main` est considéré comme stable, testé et déployable à tout moment.
    *   **Règles :** Tout commit sur `main` doit correspondre à une version de production (taguée `vX.X.X`). La branche `main` ne peut être mise à jour que par un merge depuis la branche `develop` après une validation complète. Les commits directs y sont proscrits.

*   **`develop`**:
    *   **Rôle :** Branche d'intégration principale. C'est la branche qui reflète l'état le plus à jour du développement. Toutes les nouvelles fonctionnalités y sont fusionnées avant d'être considérées pour la production.
    *   **Règles :** C'est la branche cible pour toutes les Pull Requests de fonctionnalités. Elle doit toujours rester dans un état stable et compilable.

*   **`feature/<nom-feature>`**:
    *   **Rôle :** Branches de développement pour de nouvelles fonctionnalités. Chaque tâche de développement, comme la migration d'un plugin ou l'ajout d'une nouvelle capacité, doit avoir sa propre branche de feature.
    *   **Exemples :** `feature/plugin-fallacy-analysis`, `feature/refactor-orchestration-service`.
    *   **Cycle de vie :**
        1.  Créée à partir de `develop`.
        2.  Le développement a lieu sur cette branche avec des commits réguliers.
        3.  Une fois la fonctionnalité terminée et testée localement, une Pull Request (PR) est ouverte pour merger la branche de feature vers `develop`.
        4.  Après la revue de code et la validation de la CI, la PR est mergée dans `develop` et la branche de feature est supprimée.

#### Processus de Revue de Code (Pull Request)

Aucun code ne sera intégré à la branche `develop` sans une revue formelle. Ce processus garantit une qualité de code élevée et favorise le partage des connaissances au sein de l'équipe.

*   **Déclenchement :** Toute modification de code doit faire l'objet d'une Pull Request (PR) depuis une branche `feature/*` vers la branche `develop`.
*   **Requisiteurs :** Chaque PR doit être revue et approuvée par **au moins un autre développeur** que l'auteur du code.
*   **Points de Vérification Clés :**
    *   **Respect des Conventions :** Le code adhère-t-il aux standards de style définis pour le projet (ex: **PEP 8** pour Python) ? Est-il lisible et bien commenté ?
    *   **Clarté et Simplicité :** La logique est-elle facile à comprendre ? N'y a-t-il pas de complexité inutile ?
    *   **Pertinence des Tests :** La PR inclut-elle des tests unitaires et/ou d'intégration pertinents qui valident la nouvelle fonctionnalité et protègent contre les régressions ?
    *   **Performance :** Le code introduit-il des goulots d'étranglement potentiels ?
    *   **Sécurité :** La modification expose-t-elle le système à de nouvelles vulnérabilités ?
*   **Templates de Pull Request :** Pour standardiser les demandes de revue, un template de PR sera utilisé. Il obligera l'auteur à décrire clairement le "quoi" (objectif de la PR), le "pourquoi" (justification métier/technique), et le "comment" (détails d'implémentation et stratégie de test).

#### Pipeline d'Intégration Continue (CI)

Un pipeline d'intégration continue sera configuré pour s'exécuter automatiquement à chaque push sur une Pull Request ciblant `develop`. Ce pipeline agit comme un gardien automatisé de la qualité du code. Le merge de la PR sera bloqué tant que toutes les étapes du pipeline n'auront pas réussi.

*   **Déclenchement :** Automatique à chaque `push` sur une branche `feature/*` ayant une PR ouverte vers `develop`.

*   **Job 1: Linting & Analyse Statique**
    *   **Objectif :** Vérifier la conformité du code aux standards sans l'exécuter.
    *   **Étapes :**
        *   **Linting du Style (`flake8`)**: Analyse le code Python pour s'assurer qu'il respecte les conventions de style PEP 8.
        *   **Analyse de Typage Statique (`mypy`)**: Vérifie la cohérence des types pour prévenir les erreurs d'exécution liées aux types de données.
    *   **Condition de Blocage :** Le job échoue si `flake8` ou `mypy` rapporte des erreurs.

*   **Job 2: Tests Unitaires & d'Intégration**
    *   **Objectif :** Valider le comportement fonctionnel du code et prévenir les régressions.
    *   **Étapes :**
        *   **Exécution des Tests (`pytest`)**: Lance l'ensemble de la suite de tests (unitaires et intégration).
        *   **Rapport de Couverture de Code**: Un rapport de couverture de code est généré (par exemple avec `pytest-cov`). **La Pull Request sera bloquée si la couverture globale du code diminue**, forçant l'ajout de tests pour toute nouvelle logique.
    *   **Condition de Blocage :** Le job échoue si un seul test échoue ou si le seuil de couverture de code n'est pas maintenu.

Le merge vers la branche `develop` est techniquement impossible si l'un de ces jobs échoue, assurant ainsi que la base de code principale reste toujours dans un état stable, testé et conforme aux standards.


### Étape 5: Validation Finale et Conformité SDDD

Cette étape finale formalise le processus de validation qui garantit que le produit logiciel livré est en stricte conformité avec les exigences et l'architecture décrites dans ce plan opérationnel, conformément au protocole SDDD. Elle sert de "contrat de sortie" pour le projet de refactoring.

#### Processus de Validation

1.  **Audit Final du Code :**
    *   Une fois que l'ensemble du développement est terminé et que toutes les fonctionnalités ont été mergées dans la branche `develop`, un audit final et complet du code sera mené.
    *   Cet audit consistera en une comparaison systématique de l'architecture du code final avec l'architecture cible spécifiée dans ce document. L'objectif est de vérifier que les principes de modularité, de découplage et les contrats d'interface ont été respectés.

2.  **Vérification de la Traçabilité (Commit-Tâche) :**
    *   Chaque commit présent dans l'historique de la branche `develop` depuis le début du projet de refactoring devra être explicitement traçable à une tâche spécifique décrite dans les "Plans de Développement Détaillés" (Étape 2).
    *   Cette vérification garantit que chaque modification apportée au code a une justification métier ou technique claire et documentée.

3.  **Production du Rapport de Conformité SDDD :**
    *   Le livrable final et la preuve de conformité de ce projet sera un rapport Markdown.
    *   **Nom du Fichier :** `docs/refactoring/informal_fallacy_system/reports/YYYYMMDD_sddd_compliance_report.md` (où YYYYMMDD est la date de génération).
    *   **Contenu du Rapport :** Ce document listera chaque exigence et chaque tâche de migration de ce plan opérationnel et fournira la preuve de sa réalisation dans le code, incluant des liens vers les commits Git correspondants ou les sections de code pertinentes.

#### Critères d'Acceptation

Pour que le projet soit considéré comme terminé, les critères suivants devront être intégralement remplis :

1.  Toutes les migrations détaillées dans l'**Étape 2** sont complétées et validées.
2.  Tous les tests automatisés décrits dans l'**Étape 3** passent avec succès.
3.  Le pipeline CI/CD configuré dans l'**Étape 4** est stable et affiche un statut "vert" sur la branche `develop`.
4.  Le rapport de conformité SDDD, tel que défini dans cette **Étape 5**, est produit, revu et validé.
