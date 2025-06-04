# Architecture du Système d'Analyse Argumentative

Bienvenue dans la section dédiée à l'architecture du système d'analyse argumentative. Cette collection de documents détaille la conception globale, les composants majeurs, leurs interactions, ainsi que des analyses approfondies de l'état actuel et des propositions structurantes pour l'évolution du système. Les thèmes principaux abordés incluent l'orchestration des agents, les mécanismes de communication, l'analyse de l'architecture existante, et des propositions de réorganisation et d'architecture hiérarchique.

## Documents Disponibles

### [Architecture Globale](./architecture_globale.md)
Vue d'ensemble de l'architecture du système, décrivant les composants principaux, leurs interactions, l'état actuel du projet et les évolutions proposées.

### [Proposition d'Architecture Hiérarchique à Trois Niveaux](./architecture_hierarchique.md)
Proposition détaillée de l'architecture hiérarchique à trois niveaux (stratégique, tactique, opérationnel) envisagée pour structurer le système d'analyse argumentative.

### [Système de Communication entre Agents](./communication_agents.md)
Analyse et description du système de communication inter-agents, incluant l'évolution vers une approche multi-canal gérée par un middleware de messagerie.

### [Conception du Système de Communication Multi-Canal](./conception_multi_canal.md)
Présentation de la conception détaillée du système de communication multi-canal, incluant le rôle du middleware et les différents types de canaux.

### [Analyse de l'Architecture d'Orchestration Actuelle](./analyse_architecture_orchestration.md)
Analyse détaillée de l'architecture d'orchestration actuelle du système d'analyse rhétorique, ses composants, mécanismes d'interaction, limitations et points d'amélioration identifiés en vue d'une refonte vers une architecture à trois niveaux.

### [Analyse de l'État Actuel de l'Architecture du Projet](./current_state_analysis.md)
Rapport d'analyse de la structure actuelle du projet, identifiant l'organisation des scripts, composants, tests, configuration et documentation, en vue d'une réorganisation et d'une meilleure cohérence.

### [État d'Avancement de l'Architecture](./etat_avancement.md)
Présentation de l'état d'avancement de l'architecture globale du projet, couvrant les composants fonctionnels de l'architecture actuelle et le suivi de la proposition d'architecture hiérarchique à trois niveaux.

### [Rapport d'Analyse Consolidé de l'Architecture (Projet "argumentation_analysis")](./rapport_analyse_architecture.md)
Rapport consolidé analysant l'architecture du projet "argumentation_analysis", identifiant les problèmes structurels, d'importation, et de documentation, et proposant des recommandations ainsi qu'un plan d'implémentation.

### [Proposition de Réorganisation de l'Architecture du Projet](./reorganization_proposal.md)
Proposition détaillée pour la réorganisation de la structure du projet et de son architecture applicative, visant à adresser les incohérences identifiées et à établir une base plus cohérente, maintenable et alignée sur les bonnes pratiques.

### [Analyse de l'Impact de l'Architecture sur les Projets Étudiants](./analyse_impact_architecture_sur_projets_etudiants.md)
Analyse de l'impact de la documentation d'architecture sur les documents de projets étudiants, identifiant les points d'enrichissement et les désynchronisations potentielles.
## Diagrammes et Schémas

Les diagrammes et schémas d'architecture sont disponibles dans le répertoire [images](./images/) :

- [Architecture de Communication des Agents](./images/architecture_communication.md): Illustre l'architecture de communication hiérarchique.
- [Architecture Multi-Canal Proposée](./images/architecture_multi_canal.md): Présente le diagramme de l'architecture de communication multi-canal.

## Principes Architecturaux

Le système d'analyse argumentative repose sur plusieurs principes architecturaux fondamentaux :

1.  **Séparation des préoccupations** : Distinction claire entre les niveaux stratégique, tactique et opérationnel.
2.  **Modularité** : Composants indépendants et interchangeables.
3.  **Communication structurée** : Protocoles de communication bien définis entre les agents, facilités par un middleware.
4.  **État partagé hiérarchique** : Partitionnement de l'état selon les niveaux de responsabilité (concept en cours d'intégration).
5.  **Extensibilité** : Facilité d'ajout de nouveaux agents et fonctionnalités.

## Évolution de l'Architecture

L'architecture du système a évolué depuis sa conception initiale pour répondre aux besoins croissants en termes de scalabilité, de modularité et de robustesse. Les documents de cette section présentent l'état actuel de l'architecture, les analyses menées, ainsi que les propositions et perspectives d'évolution future.