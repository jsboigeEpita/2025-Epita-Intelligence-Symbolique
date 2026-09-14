# 🧱 Noyau Applicatif (`core/`)

Ce répertoire contient les classes et fonctions fondamentales partagées par l'ensemble de l'application d'analyse rhétorique. Il assure la gestion de l'état, l'interaction avec les services externes (LLM, JVM) et définit les règles d'orchestration.

[Retour au README Principal](../README.md)

## Contenu

Ce README détaille cinq modules de la racine. `core/` en compte en réalité **25 `.py`** et **six sous-répertoires** (mesuré le 2026-09-14) : la liste ci-dessous est un sous-ensemble délibéré, pas l'inventaire du paquet. Les sous-répertoires sont recensés en fin de section.

### Gestion de l'État

* **[`shared_state.py`](./shared_state.py)** : Définit la classe `RhetoricalAnalysisState`.
    * Représente l'état mutable de l'analyse (texte brut, tâches assignées, arguments identifiés, sophismes trouvés, belief sets logiques, logs de requêtes, réponses des agents, conclusion finale, prochain agent désigné).
    * Inclut des méthodes pour ajouter/modifier ces éléments et pour sérialiser/désérialiser l'état (JSON).
    * Possède un logging interne pour tracer les modifications.
    * Supporte la persistance de l'état pour la reprise d'analyse.

* **[`state_manager_plugin.py`](./state_manager_plugin.py)** : Définit la classe `StateManagerPlugin`.
    * Un plugin Semantic Kernel qui encapsule une instance de `RhetoricalAnalysisState`.
    * Expose des fonctions natives (`@kernel_function`) aux agents pour lire (`get_current_state_snapshot`) et écrire (`add_task`, `add_argument`, `add_fallacy`, `add_belief_set`, `log_query_result`, `add_answer`, `set_final_conclusion`, `designate_next_agent`) dans l'état partagé de manière contrôlée et traçable.
    * Implémente des mécanismes de validation pour garantir l'intégrité des données.

### Orchestration

* **[`strategies.py`](./strategies.py)** : Définit les stratégies d'orchestration pour `AgentGroupChat` de Semantic Kernel.
    * `SimpleTerminationStrategy` 🚦 : Arrête la conversation si `final_conclusion` est présente dans l'état ou si un nombre maximum de tours (`max_steps`) est atteint.
    * `DelegatingSelectionStrategy` 🔀 : Choisit le prochain agent. Priorise la désignation explicite (`_next_agent_designated` dans l'état). Sinon, retourne par défaut au `ProjectManagerAgent` après l'intervention d'un autre agent.
    * Supporte des stratégies avancées comme la sélection basée sur les compétences ou la charge de travail.

### Intégration Externe

* **[`jvm_setup.py`](./jvm_setup.py)** : Gère l'interaction avec l'environnement Java. 🔥☕
    * Contient la logique (`initialize_jvm`) pour :
        * Vérifier/télécharger les JARs Tweety requis et leurs binaires natifs dans `libs/`.
        * Trouver un JDK valide (via `JAVA_HOME` ou détection automatique).
        * Démarrer la JVM via JPype avec le classpath et `java.library.path` corrects.
    * Retourne un statut indiquant si la JVM est prête, essentiel pour l'agent `PropositionalLogicAgent`.
    * Gère les erreurs de configuration Java avec des messages explicatifs.

* **[`llm_service.py`](./llm_service.py)** : Gère la création du service LLM. ☁️
    * Contient la logique (`create_llm_service`) pour lire la configuration LLM depuis `.env` (OpenAI ou Azure).
    * Crée et retourne l'instance du service (`OpenAIChatCompletion` ou `AzureChatCompletion`) qui sera injectée dans le kernel et utilisée par les `ChatCompletionAgent`.
    * Supporte la configuration de paramètres avancés comme la température, le nombre de tokens maximum, etc.
    * Implémente un mécanisme de fallback en cas d'erreur de connexion.

### Sous-répertoires

`core/` n'est pas plat : six sous-répertoires portent du code, **chacun avec son propre README** (comptes `.py` mesurés le 2026-09-14).

| Sous-répertoire | `.py` | Rôle |
|---|---|---|
| [`communication/`](./communication/README.md) | 12 | Messagerie multi-canal (hiérarchique, collaboration, pub/sub, requête/réponse) et ses adaptateurs opérationnel/tactique/stratégique |
| [`integration/`](./integration/README.md) | 2 | Contournement Python/Clingo du solveur Java défectueux |
| [`interfaces/`](./interfaces/README.md) | 2 | Contrats abstraits de la composabilité Lego — **non adoptés** : `AbstractAnalysisService` n'a aucun implémenteur ni importeur (mesuré le 2026-09-14), sa docstring le dit désormais |
| [`models/`](./models/README.md) | 1 | Contrat de données Toulmin |
| [`setup/`](./setup/README.md) | 2 | Installateurs d'outils binaires externes portables |
| [`utils/`](./utils/README.md) | 22 | Assembleur d'utilitaires transverses à trois régimes : feuilles réellement consommées, façade par star-import, fossiles test-only |

### ⚠️ Risques d'Intégration Native et Leçons Apprises

L'intégration de bibliothèques natives (.dll, .so) via la JVM présente des risques de stabilité critiques si les architectures ne sont pas parfaitement alignées.

**Crash `Windows fatal exception: access violation`:**

*   **Cause :** Une analyse post-crash a démontré que cette erreur était systématiquement déclenchée lors du chargement de bibliothèques natives (spécifiquement les DLLs de Prover9) via l'argument `-Djava.library.path`. La cause est un conflit d'architecture entre la JVM (ex: 64-bit) et les bibliothèques natives chargées (ex: 32-bit).
*   **Solution de contournement :** La stabilité a été restaurée en désactivant complètement le chargement de la bibliothèque native problématique.

**Recommandations Fortes :**

1.  **Privilégier les dépendances 100% Java :** Dans la mesure du possible, utilisez des bibliothèques entièrement écrites en Java pour éviter les problèmes de compatibilité multiplateforme et d'architecture.
2.  **Validation d'architecture rigoureuse :** **N'UTILISEZ PAS** l'argument `-Djava.library.path` avant d'avoir formellement validé que l'architecture de chaque bibliothèque native (DLL) correspond exactement à celle de la JVM utilisée (32-bit vs 64-bit).
3.  **Dépendances Stables :** Pour assurer la stabilité, reportez-vous aux fichiers `requirements.txt` et à la configuration du projet pour les versions de Java et `jpype` testées.
4.  **Variable `JAVA_HOME` :** Assurez-vous toujours que la variable d'environnement `JAVA_HOME` pointe vers la racine du JDK dont l'architecture est compatible avec les bibliothèques natives que vous prévoyez de charger.

## Utilisation

### Initialisation de l'État

```python
from argumentation_analysis.core.shared_state import RhetoricalAnalysisState
from argumentation_analysis.core.state_manager_plugin import StateManagerPlugin

# Créer un nouvel état
state = RhetoricalAnalysisState()
state.raw_text = "Texte à analyser"

# Créer un plugin de gestion d'état
state_manager = StateManagerPlugin(state)
```

### Configuration du Service LLM

```python
from argumentation_analysis.core.llm_service import create_llm_service

# Créer le service LLM à partir des variables d'environnement
llm_service = create_llm_service()

# Ou avec des paramètres spécifiques
llm_service = create_llm_service(
    temperature=0.7,
    max_tokens=2000,
    model_id="gpt-4o-mini"
)
```

### Initialisation de la JVM pour Tweety

```python
from argumentation_analysis.core.jvm_setup import initialize_jvm

# Initialiser la JVM
jvm_status = initialize_jvm()

if jvm_status.is_ready:
    print("JVM initialisée avec succès")
    print(f"Version Java: {jvm_status.java_version}")
    print(f"Tweety version: {jvm_status.tweety_version}")
else:
    print(f"Erreur d'initialisation JVM: {jvm_status.error_message}")
```

## Bonnes Pratiques

- Utilisez toujours le `StateManagerPlugin` pour accéder à l'état partagé, jamais directement l'objet `RhetoricalAnalysisState`
- Initialisez la JVM une seule fois au début de l'application
- Configurez correctement les variables d'environnement dans le fichier `.env`
- Utilisez les stratégies d'orchestration fournies pour contrôler le flux de conversation
- Implémentez une gestion d'erreurs robuste pour les appels aux services externes (LLM, JVM)

## Limites connues

- Corrigé (#2107) — les **quatre exemples d'import** de ce README portaient le préfixe mort `core.`. Mesuré : `from core.shared_state import RhetoricalAnalysisState` lève `ModuleNotFoundError: No module named 'core.shared_state'` (le préfixe racine `core/` a été supprimé, cf. `CLAUDE.md`), donc **chaque copier-coller de ce README échouait**. Les trois blocs portent le préfixe canonique `argumentation_analysis.core.`.
- Corrigé (#2107) — les **six sous-répertoires** de `core/` (dont `communication/`, pourtant doté de son propre README) n'étaient mentionnés nulle part dans ce parent. Ils sont recensés ci-dessus avec leurs comptes `.py` mesurés.
- **Portée assumée** : ce README détaille 5 des **25 `.py`** de la racine. Il ne prétend plus à l'exhaustivité, mais l'inventaire des 20 autres modules n'est pas fait ici — grain distinct, pas une omission silencieuse.
- Les cinq modules décrits sont **vérifiés présents** au niveau racine de leur fichier (`ast`, 2026-09-14) : `RhetoricalAnalysisState`, `StateManagerPlugin`, `SimpleTerminationStrategy`, `DelegatingSelectionStrategy`, `initialize_jvm`, `create_llm_service`. Les descriptions de comportement de ce README n'ont en revanche **pas** été re-mesurées ligne à ligne dans ce grain.
