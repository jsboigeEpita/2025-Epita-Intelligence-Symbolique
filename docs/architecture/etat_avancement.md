# État d'Avancement de l'Architecture et de la Proposition d'Architecture Hiérarchique

Ce document suit l'état d'avancement de l'architecture globale du projet, y compris les composants fonctionnels de l'architecture actuelle et l'évolution de la proposition majeure d'une architecture hiérarchique à trois niveaux. Pour une analyse détaillée de l'état actuel, référez-vous à [`current_state_analysis.md`](./current_state_analysis.md:1). La proposition d'architecture hiérarchique est détaillée dans [`architecture_hierarchique.md`](./architecture_hierarchique.md:1).

## 1. Architecture Actuelle Fonctionnelle et Bases pour la Proposition Hiérarchique

Les composants suivants de l'architecture actuelle sont implémentés et fonctionnels, certains servant également de fondation ou de preuve de concept pour la proposition d'architecture hiérarchique.

### 1.1. Communication Inter-Agents
*   **`MessageMiddleware`** ([`../../argumentation_analysis/core/communication/middleware.py`](../../argumentation_analysis/core/communication/middleware.py:19)) : Fonctionnel et central. Il gère de multiples canaux de communication spécialisés :
    *   `HierarchicalChannel` ([`../../argumentation_analysis/core/communication/hierarchical_channel.py`](../../argumentation_analysis/core/communication/hierarchical_channel.py:20)) : Pour les communications structurées envisagées entre niveaux.
    *   `DataChannel` ([`../../argumentation_analysis/core/communication/data_channel.py`](../../argumentation_analysis/core/communication/data_channel.py:253)) : Pour le transfert de données volumineuses.
    *   `CollaborationChannel` ([`../../argumentation_analysis/core/communication/collaboration_channel.py`](../../argumentation_analysis/core/communication/collaboration_channel.py:140)) : Pour la communication horizontale entre agents.
    *   (Voir [`communication_agents.md`](./communication_agents.md:1) pour plus de détails).
*   **Adaptateurs d'Agents** ([`../../argumentation_analysis/core/communication/adapters.py`](../../argumentation_analysis/core/communication/adapters.py:1)) : Permettent aux agents d'interagir avec le `MessageMiddleware`.
*   **Protocoles de Communication de Base** : Support pour Request-Response ([`../../argumentation_analysis/core/communication/request_response.py`](../../argumentation_analysis/core/communication/request_response.py:1)) et Publish-Subscribe ([`../../argumentation_analysis/core/communication/pub_sub.py`](../../argumentation_analysis/core/communication/pub_sub.py:1)).

### 1.2. Orchestration (Architecture Plate Actuelle)
*   **Framework Semantic Kernel** : Utilisé pour l'orchestration de base, notamment via `AgentGroupChat` pour la collaboration entre agents. (Détails dans [`analyse_architecture_orchestration.md`](./analyse_architecture_orchestration.md:58)).
*   **Gestion de l'État Partagé** :
    *   `RhetoricalAnalysisState` ([`../../argumentation_analysis/core/shared_state.py`](../../argumentation_analysis/core/shared_state.py:12)) : Centralise les données de l'analyse.
    *   `StateManagerPlugin` ([`../../argumentation_analysis/core/state_manager_plugin.py`](../../argumentation_analysis/core/state_manager_plugin.py:16)) : Expose les fonctionnalités de gestion de l'état aux agents.
*   **Stratégies d'Orchestration** ([`../../argumentation_analysis/core/strategies.py`](../../argumentation_analysis/core/strategies.py:1)) :
    *   `SimpleTerminationStrategy` : Gère la fin de la conversation.
    *   `BalancedParticipationStrategy` : Sélectionne le prochain agent à intervenir.

### 1.3. Agents Spécialisés (Fonctionnant au Niveau Opérationnel de fait)
*   Les agents suivants sont fonctionnels et effectuent les tâches d'analyse principales :
    *   `ProjectManagerAgent` ([`../../argumentation_analysis/agents/core/pm/pm_agent.py`](../../argumentation_analysis/agents/core/pm/pm_agent.py:1))
    *   `InformalAnalysisAgent` ([`../../argumentation_analysis/agents/core/informal/informal_agent.py`](../../argumentation_analysis/agents/core/informal/informal_agent.py:1))
    *   `PropositionalLogicAgent` ([`../../argumentation_analysis/agents/core/logic/propositional_logic_agent.py`](../../argumentation_analysis/agents/core/logic/propositional_logic_agent.py:1))
    *   `ExtractAgent` ([`../../argumentation_analysis/agents/core/extract/extract_agent.py`](../../argumentation_analysis/agents/core/extract/extract_agent.py:1))

### 1.4. Éléments Précurseurs pour l'Architecture Hiérarchique
*   **Interfaces Hiérarchiques (Conceptuelles/Ébauches)** : Des interfaces comme `StrategicTacticalInterface` ([`../../argumentation_analysis/orchestration/hierarchical/interfaces/strategic_tactical.py`](../../argumentation_analysis/orchestration/hierarchical/interfaces/strategic_tactical.py:22)) et `TacticalOperationalInterface` ([`../../argumentation_analysis/orchestration/hierarchical/interfaces/tactical_operational.py`](../../argumentation_analysis/orchestration/hierarchical/interfaces/tactical_operational.py:22)) existent et utilisent le `MessageMiddleware`. Elles représentent des travaux exploratoires pour la proposition hiérarchique.
*   **Structure de Base pour la Hiérarchie** : Le répertoire `argumentation_analysis/orchestration/hierarchical/` contient des ébauches et implémentations partielles (organisation des répertoires, classes d'état de base pour les niveaux, adaptateurs pour agents existants) qui constituent des prototypes pour la proposition d'architecture hiérarchique.

## 2. Proposition d'Architecture Hiérarchique : État Actuel (Étude/Conception/PoC)

L'architecture hiérarchique à trois niveaux (Stratégique, Tactique, Opérationnel) est une **proposition active** détaillée dans [`architecture_hierarchique.md`](./architecture_hierarchique.md:1). Son implémentation n'est pas complète et de nombreux composants sont encore au stade de concept ou de prototype.

*   **Statut Général** : La proposition est en phase d'étude et de validation. Un Proof of Concept (PoC) est une prochaine étape clé.
*   **Agents Hiérarchiques Spécifiques** (`StrategicAgent`, `TacticalAgent`) : Ces agents, tels que décrits dans la proposition, sont **conceptuels** et non implémentés.
*   **Gestion d'État Hiérarchique** : Le partitionnement de `RhetoricalAnalysisState` en états distincts par niveau est une refactorisation majeure **non encore réalisée**.

### 2.1. Niveau Tactique (Concept/Prototype)
*   **Coordinateur de tâches** : Implémentation partielle/prototype dans le cadre de la proposition.
*   **Moniteur de progression** : Prototype.
*   **Résolveur de conflits** : Conception.

### 2.2. Niveau Stratégique (Concept)
*   **Gestionnaire stratégique** : Conception.
*   **Planificateur stratégique** : Non commencé.
*   **Allocateur de ressources** : Non commencé.

### 2.3. Orchestration Globale pour la Hiérarchie (Concept/Prototype)
*   **Mécanismes de synchronisation entre niveaux** : Prototype.
*   **Gestion des exceptions et escalade** : Conception.

## 3. Prochaines Étapes

### 3.1. Consolidation de l'Architecture Actuelle
*   Poursuivre la rationalisation de la structure des fichiers et des configurations (voir recommandations dans [`current_state_analysis.md`](./current_state_analysis.md:165)).
*   Clarifier et documenter la gestion de la JVM.

### 3.2. Avancement de la Proposition d'Architecture Hiérarchique
*   **Validation et Raffinement** : Finaliser la discussion et valider la proposition architecturale hiérarchique.
*   **Développement d'un Proof of Concept (PoC)** :
    *   Implémenter une version simplifiée des agents pour chaque niveau.
    *   Tester l'utilisation du `HierarchicalChannel` et du `MessageMiddleware` pour les interactions inter-niveaux du PoC.
    *   Valider les mécanismes de base de la gestion d'état partitionnée pour le PoC.
*   **Planification de la Refactorisation de l'État** : Établir un plan pour la refactorisation de `RhetoricalAnalysisState`.
*   **Implémentation Progressive** : Si le PoC est concluant, planifier une implémentation itérative des niveaux et des fonctionnalités de l'architecture hiérarchique.
*   **Tests et Évaluation Continus** : Définir et mettre en place des tests spécifiques pour l'architecture hiérarchique.

### 3.3. Fonctionnalités Architecturales Futures
*   **Service d'Orchestration Centralisé** : Étudier la pertinence et la conception d'un `orchestration_service.py` dédié, comme suggéré dans [`current_state_analysis.md`](./current_state_analysis.md:164).
*   **Persistance Avancée** : Planifier l'intégration de mécanismes de persistance plus robustes pour l'état et les résultats d'analyse.
*   **Sécurité** : Définir et implémenter des mesures de sécurité adaptées si le système évolue vers des environnements moins contrôlés.
*   **Gestion Fine des Erreurs** : Améliorer les mécanismes de détection, de rapport et de récupération des erreurs à tous les niveaux de l'architecture.

## 4. Points d'Attention pour l'Avancement

*   **Orchestration Actuelle vs. Proposition Hiérarchique** : L'orchestration actuelle est fonctionnelle mais "plate", ce qui peut limiter la scalabilité. La proposition hiérarchique vise à adresser ce point. La coexistence des deux approches (l'actuelle en production, la proposition en étude/PoC) doit être gérée clairement.
*   **Décision sur l'Architecture Cible** : Une décision formelle sur l'adoption complète et le plan de migration vers l'architecture hiérarchique est nécessaire pour guider les développements futurs à long terme.
*   **Service d'Orchestration** : L'absence actuelle d'un `orchestration_service.py` explicite signifie que la logique d'orchestration est répartie (principalement dans [`../../argumentation_analysis/orchestration/analysis_runner.py`](../../argumentation_analysis/orchestration/analysis_runner.py:1) et les stratégies de `AgentGroupChat`).

## 5. Correspondance avec la Conception

L'implémentation actuelle dans le répertoire `argumentation_analysis/orchestration/hierarchical/` correspond à des travaux exploratoires et des prototypes pour la **proposition** d'architecture hiérarchique décrite dans [`architecture_hierarchique.md`](./architecture_hierarchique.md:1). Ces éléments ne représentent pas une implémentation complète ou entièrement fonctionnelle de ladite proposition.

L'architecture fonctionnelle actuelle est mieux décrite par les analyses de [`current_state_analysis.md`](./current_state_analysis.md:1), [`communication_agents.md`](./communication_agents.md:1) et [`analyse_architecture_orchestration.md`](./analyse_architecture_orchestration.md:1).

Des différences et simplifications existent par rapport à la vision complète de la proposition hiérarchique, qui reste l'objectif à long terme si elle est adoptée.