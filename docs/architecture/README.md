# Architecture du Système d'Analyse Argumentative

Bienvenue dans la section dédiée à l'architecture du système d'analyse argumentative. Cette collection de documents détaille la conception globale, les composants majeurs, leurs interactions, ainsi que des analyses approfondies de l'état actuel et des propositions structurantes pour l'évolution du système. Les thèmes principaux abordés incluent l'orchestration des agents, les mécanismes de communication, l'analyse de l'architecture existante, et des propositions de réorganisation et d'architecture hiérarchique.

## Documents Disponibles

### [Architecture Globale](./architecture_globale.md) <!-- TODO: Vérifier l'existence et l'emplacement du fichier architecture_globale.md. S'il n'existe pas, envisager de le retirer ou de créer le document. -->
Vue d'ensemble de l'architecture du système, décrivant les composants principaux, leurs interactions, l'état actuel du projet et les évolutions proposées.

### [Proposition d'Architecture Hiérarchique à Trois Niveaux](../architecture_hierarchique_trois_niveaux.md) <!-- Lien corrigé de ./architecture_hierarchique.md -->
Proposition détaillée de l'architecture hiérarchique à trois niveaux (stratégique, tactique, opérationnel) envisagée pour structurer le système d'analyse argumentative.

### [Système de Communication entre Agents](./communication_agents.md)
Analyse et description du système de communication inter-agents, incluant l'évolution vers une approche multi-canal gérée par un middleware de messagerie.

### [Analyse des Orchestrations Agentiques Sherlock/Watson](./analyse_orchestrations_sherlock_watson.md)
Analyse complète des flux d'orchestration dans les conversations agentiques entre Sherlock Holmes et Dr. Watson, en se concentrant sur leurs interactions, outils utilisés, et notamment l'usage des solvers Tweety par Watson. Couvre les patterns d'interaction pour les workflows Cluedo (logique informelle) et Einstein (logique formelle obligatoire).

### [Stratégies d'Argumentation Sophistiquées](./strategies/)
**NOUVEAUTÉ POST-AUDIT** : Documentation complète de l'architecture sophistiquée des stratégies d'argumentation découverte lors de l'audit anti-mock réussi (106/106 tests). Couvre les 3 stratégies authentiques intégrées avec Semantic Kernel et coordonnées par un état partagé innovant.

- **[Architecture des Stratégies](./strategies/strategies_architecture.md)** : Vue d'ensemble des 3 stratégies authentiques (SimpleTermination, DelegatingSelection, BalancedParticipation)
- **[Audit Anti-Mock](./strategies/audit_anti_mock.md)** : Validation complète 106/106 tests sans mocks critiques
- **[Intégration Semantic Kernel](./strategies/semantic_kernel_integration.md)** : Patterns avancés d'intégration SK avec innovations
- **[État Partagé](./strategies/shared_state_architecture.md)** : Architecture du hub central RhetoricalAnalysisState

### [Conception du Système de Communication Multi-Canal](../conception_systeme_communication_multi_canal.md) <!-- Lien corrigé de ./conception_multi_canal.md -->
Présentation de la conception détaillée du système de communication multi-canal, incluant le rôle du middleware et les différents types de canaux.

### [Analyse de l'Architecture d'Orchestration Actuelle](../analyse_architecture_orchestration.md) <!-- Lien corrigé de ./analyse_architecture_orchestration.md -->
Analyse détaillée de l'architecture d'orchestration actuelle du système d'analyse rhétorique, ses composants, mécanismes d'interaction, limitations et points d'amélioration identifiés en vue d'une refonte vers une architecture à trois niveaux.

### [Analyse de l'État Actuel de l'Architecture du Projet](./current_state_analysis.md) <!-- TODO: Vérifier l'existence et l'emplacement du fichier current_state_analysis.md. S'il n'existe pas, envisager de le retirer ou de créer le document. -->
Rapport d'analyse de la structure actuelle du projet, identifiant l'organisation des scripts, composants, tests, configuration et documentation, en vue d'une réorganisation et d'une meilleure cohérence.

### [État d'Avancement de l'Architecture](./etat_avancement.md) <!-- TODO: Vérifier l'existence et l'emplacement du fichier etat_avancement.md. S'il n'existe pas, envisager de le retirer ou de créer le document. -->
Présentation de l'état d'avancement de l'architecture globale du projet, couvrant les composants fonctionnels de l'architecture actuelle et le suivi de la proposition d'architecture hiérarchique à trois niveaux.

### [Rapport d'Analyse Consolidé de l'Architecture (Projet "argumentation_analysis")](./rapport_analyse_architecture.md) <!-- TODO: Vérifier l'existence et l'emplacement du fichier rapport_analyse_architecture.md. S'il n'existe pas, envisager de le retirer ou de créer le document. -->
Rapport consolidé analysant l'architecture du projet "argumentation_analysis", identifiant les problèmes structurels, d'importation, et de documentation, et proposant des recommandations ainsi qu'un plan d'implémentation.

### [Proposition de Réorganisation de l'Architecture du Projet](./reorganization_proposal.md) <!-- TODO: Vérifier l'existence et l'emplacement du fichier reorganization_proposal.md. S'il n'existe pas, envisager de le retirer ou de créer le document. -->
Proposition détaillée pour la réorganisation de la structure du projet et de son architecture applicative, visant à adresser les incohérences identifiées et à établir une base plus cohérente, maintenable et alignée sur les bonnes pratiques.

### [Analyse de l'Impact de l'Architecture sur les Projets Étudiants](./analyse_impact_architecture_sur_projets_etudiants.md) <!-- TODO: Vérifier si le fichier analyse_impact_architecture_sur_projets_etudiants.md est le bon document et son emplacement correct. S'il s'agit de docs/guides/analyse_impact_guides_sur_projets_etudiants.md, le lien devrait être ../guides/analyse_impact_guides_sur_projets_etudiants.md et la pertinence en tant que document d'architecture principal doit être évaluée. S'il n'existe pas, envisager de le retirer ou de créer le document. -->
Analyse de l'impact de la documentation d'architecture sur les documents de projets étudiants, identifiant les points d'enrichissement et les désynchronisations potentielles.

### [Structure du Projet](../structure_projet.md) <!-- Document ajouté -->
Description de l'organisation globale des répertoires et des fichiers du projet, définissant les conventions et la localisation des différents types d'artefacts.
<!-- TODO: Évaluer si docs/api_outils_rhetorique.md doit être listé ici. Si oui, ajouter une entrée avec description et lien ../api_outils_rhetorique.md -->
<!-- TODO: Évaluer si docs/integration_outils_rhetorique.md doit être listé ici. Si oui, ajouter une entrée avec description et lien ../integration_outils_rhetorique.md -->

### Structure des Répertoires `src`

Pour améliorer la modularité et la clarté du code source, une nouvelle organisation des répertoires a été mise en place dans le dossier `src`. Cette structure distingue clairement les composants fondamentaux du système des modules plus spécifiques liés aux agents.

- **`src/core`**: Ce répertoire contient les composants de base, réutilisables et agnostiques de toute personnalité ou logique métier spécifique. Il est conçu pour héberger le "cœur" de l'application.
    - **`plugins/standard`**: Contient des plugins standards offrant des fonctionnalités génériques.
    - **`plugins/workflows`**: Contient des plugins qui définissent des enchaînements d'opérations ou des flux de travail complexes.

- **`src/agents`**: Ce répertoire est dédié aux "personnalités" des agents, c'est-à-dire les implémentations spécifiques, les configurations et les logiques qui définissent le comportement d'un agent particulier.
    - **`personalities`**: Contient les différentes personnalités des agents, encapsulant leur logique et leurs capacités uniques.

## Diagrammes et Schémas

Les diagrammes et schémas d'architecture sont disponibles dans le répertoire [images](../images/). <!-- Lien corrigé de ./images/ -->

- [Architecture de Communication des Agents](../images/architecture_communication.png) <!-- TODO: Vérifier l'existence et le nom exact du fichier (ex: .png, .svg, .md) pour architecture_communication. Le lien actuel suppose une image .png dans docs/images/. Si c'est un .md, ajuster le lien et la description. -->: Illustre l'architecture de communication hiérarchique.
- [Architecture Multi-Canal Proposée](../images/architecture_multi_canal.png) <!-- TODO: Vérifier l'existence et le nom exact du fichier (ex: .png, .svg, .md) pour architecture_multi_canal. Le lien actuel suppose une image .png dans docs/images/. Si c'est un .md, ajuster le lien et la description. -->: Présente le diagramme de l'architecture de communication multi-canal.

## Principes Architecturaux

Le système d'analyse argumentative repose sur plusieurs principes architecturaux fondamentaux :

1.  **Séparation des préoccupations** : Distinction claire entre les niveaux stratégique, tactique et opérationnel.
2.  **Modularité** : Composants indépendants et interchangeables.
3.  **Communication structurée** : Protocoles de communication bien définis entre les agents, facilités par un middleware.
4.  **État partagé hiérarchique** : Partitionnement de l'état selon les niveaux de responsabilité (concept en cours d'intégration).
5.  **Extensibilité** : Facilité d'ajout de nouveaux agents et fonctionnalités.

## Évolution de l'Architecture

L'architecture du système a évolué depuis sa conception initiale pour répondre aux besoins croissants en termes de scalabilité, de modularité et de robustesse. Les documents de cette section présentent l'état actuel de l'architecture, les analyses menées, ainsi que les propositions et perspectives d'évolution future.