# 🧱 Noyau Applicatif (`core/`)

Ce répertoire contient les classes et fonctions fondamentales partagées par l'ensemble de l'application d'analyse rhétorique. Il assure la gestion de l'état, l'interaction avec les services externes (LLM, JVM) et définit les règles d'orchestration.

[Retour au README Principal](../README.md)

## Contenu

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

## Utilisation

### Initialisation de l'État

```python
from core.shared_state import RhetoricalAnalysisState
from core.state_manager_plugin import StateManagerPlugin

# Créer un nouvel état
state = RhetoricalAnalysisState()
state.raw_text = "Texte à analyser"

# Créer un plugin de gestion d'état
state_manager = StateManagerPlugin(state)
```

### Configuration du Service LLM

```python
from core.llm_service import create_llm_service

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
from core.jvm_setup import initialize_jvm

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