# Niveau Tactique de l'Architecture Hiérarchique

Ce répertoire contient les composants du niveau tactique de l'architecture hiérarchique, responsables de la coordination entre agents, de la décomposition des objectifs en tâches concrètes et du suivi de l'avancement.

## Vue d'ensemble

Le niveau tactique représente la couche intermédiaire de l'architecture hiérarchique à trois niveaux. Il sert de pont entre le niveau stratégique (qui définit les objectifs globaux) et le niveau opérationnel (qui exécute les tâches spécifiques). Le niveau tactique est responsable de :

- Traduire les objectifs stratégiques en tâches opérationnelles concrètes
- Coordonner l'exécution des tâches entre les différents agents opérationnels
- Surveiller l'avancement des tâches et identifier les problèmes potentiels
- Résoudre les conflits et contradictions dans les résultats d'analyse
- Agréger les résultats opérationnels pour les remonter au niveau stratégique

Ce niveau assure la cohérence et l'efficacité de l'exécution des plans stratégiques, tout en adaptant dynamiquement les tâches en fonction des retours du niveau opérationnel.

## Composants principaux

### TaskCoordinator

Le Coordinateur de Tâches est le composant central du niveau tactique, responsable de :

- Décomposer les objectifs stratégiques en tâches opérationnelles spécifiques
- Assigner les tâches aux agents opérationnels appropriés
- Gérer les dépendances entre les tâches et leur ordonnancement
- Adapter dynamiquement le plan d'exécution en fonction des résultats intermédiaires
- Coordonner la communication entre les agents opérationnels

Le TaskCoordinator orchestre l'exécution des tâches et assure que les agents opérationnels travaillent de manière cohérente vers les objectifs définis.

### ProgressMonitor

Le Moniteur de Progression est responsable du suivi de l'avancement des tâches, notamment :

- Suivre l'avancement des tâches en temps réel
- Identifier les retards, blocages ou déviations
- Collecter les métriques de performance
- Générer des rapports de progression pour le niveau stratégique
- Déclencher des alertes en cas de problèmes significatifs

Le ProgressMonitor fournit une visibilité sur l'état d'avancement du processus d'analyse et permet d'identifier rapidement les problèmes potentiels.

### ConflictResolver

Le Résolveur de Conflits est spécialisé dans la gestion des contradictions et incohérences :

- Détecter et analyser les contradictions dans les résultats
- Arbitrer entre différentes interprétations ou analyses
- Appliquer des heuristiques de résolution de conflits
- Maintenir la cohérence globale de l'analyse
- Escalader les conflits non résolus au niveau stratégique

Le ConflictResolver assure que les résultats d'analyse sont cohérents et fiables, même lorsque différents agents produisent des résultats contradictoires.

### TacticalState

L'état tactique maintient les informations partagées entre les composants du niveau tactique, notamment :

- Les tâches actuelles et leur état d'avancement
- Les résultats intermédiaires des agents opérationnels
- Les métriques de performance et les indicateurs de progression
- Les conflits identifiés et leur statut de résolution

## Flux de travail typique

1. Le niveau stratégique transmet un objectif au niveau tactique via l'interface stratégique-tactique
2. Le TaskCoordinator analyse l'objectif et le décompose en tâches opérationnelles
3. Les tâches sont assignées aux agents opérationnels via l'interface tactique-opérationnelle
4. Le ProgressMonitor commence à suivre l'avancement des tâches
5. Les agents opérationnels exécutent les tâches et remontent leurs résultats
6. Le ConflictResolver analyse les résultats pour détecter et résoudre les contradictions
7. Le TaskCoordinator adapte le plan d'exécution en fonction des résultats et des problèmes identifiés
8. Une fois toutes les tâches complétées, les résultats sont agrégés et remontés au niveau stratégique

## Utilisation

Pour utiliser les composants du niveau tactique :

```python
# Initialisation des composants tactiques
from argumentation_analysis.orchestration.hierarchical.tactical.coordinator import TaskCoordinator
from argumentation_analysis.orchestration.hierarchical.tactical.monitor import ProgressMonitor
from argumentation_analysis.orchestration.hierarchical.tactical.resolver import ConflictResolver
from argumentation_analysis.orchestration.hierarchical.tactical.state import TacticalState

# Création de l'état partagé
tactical_state = TacticalState()

# Initialisation des composants
coordinator = TaskCoordinator(tactical_state)
monitor = ProgressMonitor(tactical_state)
resolver = ConflictResolver(tactical_state)

# Réception d'un objectif stratégique
strategic_objective = {
    "id": "obj-123",
    "type": "analyze_fallacies",
    "text_source": "source_document.txt",
    "parameters": {...}
}

# Traitement de l'objectif
tasks = coordinator.decompose_objective(strategic_objective)
coordinator.assign_tasks(tasks)

# Suivi de l'avancement
progress_report = monitor.generate_progress_report()

# Résolution des conflits
conflicts = resolver.detect_conflicts()
resolved_results = resolver.resolve_conflicts(conflicts)

# Agrégation des résultats
final_results = coordinator.aggregate_results()
```

## Communication avec les autres niveaux

Le niveau tactique communique avec :

- Le niveau stratégique via l'interface stratégique-tactique, pour recevoir des objectifs et remonter des résultats agrégés
- Le niveau opérationnel via l'interface tactique-opérationnelle, pour assigner des tâches et recevoir des résultats spécifiques

Cette position intermédiaire permet au niveau tactique de servir de médiateur entre la vision globale du niveau stratégique et l'exécution concrète du niveau opérationnel.

## Voir aussi

- [Documentation des interfaces hiérarchiques](../interfaces/README.md)
- [Documentation du niveau stratégique](../strategic/README.md)
- [Documentation du niveau opérationnel](../operational/README.md)