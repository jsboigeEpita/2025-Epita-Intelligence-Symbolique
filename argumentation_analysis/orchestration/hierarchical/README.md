# Architecture Hiérarchique d'Orchestration

Ce répertoire contient l'implémentation de l'architecture hiérarchique à trois niveaux pour l'orchestration du système d'analyse argumentative.

## Vue d'ensemble

L'architecture hiérarchique organise le système d'analyse argumentative en trois niveaux distincts :

1. **Niveau Stratégique** : Responsable de la planification globale, de l'allocation des ressources et des décisions de haut niveau.
2. **Niveau Tactique** : Responsable de la coordination des tâches, de la résolution des conflits et de la supervision des agents opérationnels.
3. **Niveau Opérationnel** : Responsable de l'exécution des tâches spécifiques et de l'interaction directe avec les données et les outils d'analyse.

Cette architecture permet une séparation claire des responsabilités, une meilleure gestion de la complexité et une orchestration efficace du processus d'analyse argumentative.

## Structure du répertoire

- [`interfaces/`](./interfaces/README.md) : Composants responsables de la communication entre les différents niveaux de l'architecture
- [`strategic/`](./strategic/README.md) : Composants du niveau stratégique (planification, allocation des ressources)
- [`tactical/`](./tactical/README.md) : Composants du niveau tactique (coordination, résolution de conflits)
- [`operational/`](./operational/README.md) : Composants du niveau opérationnel (exécution des tâches)
  - [`adapters/`](./operational/adapters/README.md) : Adaptateurs pour les agents spécialistes existants
- [`templates/`](./templates/README.md) : Templates pour la création de nouveaux composants

## Flux de travail typique

Le flux de travail typique dans l'architecture hiérarchique suit ce schéma :

1. Le niveau stratégique définit des objectifs et des plans globaux
2. Ces objectifs sont transmis au niveau tactique via la `StrategicTacticalInterface`
3. Le niveau tactique décompose ces objectifs en tâches spécifiques
4. Ces tâches sont transmises au niveau opérationnel via la `TacticalOperationalInterface`
5. Les agents opérationnels exécutent les tâches et génèrent des résultats
6. Les résultats sont remontés au niveau tactique via la `TacticalOperationalInterface`
7. Le niveau tactique agrège et analyse ces résultats
8. Les résultats agrégés sont remontés au niveau stratégique via la `StrategicTacticalInterface`
9. Le niveau stratégique évalue les résultats et ajuste la stratégie si nécessaire

## Intégration avec les outils d'analyse rhétorique

L'architecture hiérarchique s'intègre avec les outils d'analyse rhétorique via les adaptateurs du niveau opérationnel. Ces adaptateurs permettent d'utiliser :

- Les [outils d'analyse rhétorique de base](../../agents/tools/analysis/README.md)
- Les [outils d'analyse rhétorique améliorés](../../agents/tools/analysis/enhanced/README.md)
- Les [nouveaux outils d'analyse rhétorique](../../agents/tools/analysis/new/README.md)

Cette intégration permet d'exploiter pleinement les capacités d'analyse rhétorique dans le cadre d'une orchestration structurée et efficace.

## Utilisation

Pour utiliser l'architecture hiérarchique dans votre projet :

```python
# Importation des composants nécessaires
from argumentation_analysis.orchestration.hierarchical.strategic.manager import StrategicManager
from argumentation_analysis.orchestration.hierarchical.strategic.state import StrategicState
from argumentation_analysis.orchestration.hierarchical.tactical.coordinator import TaskCoordinator
from argumentation_analysis.orchestration.hierarchical.tactical.state import TacticalState
from argumentation_analysis.orchestration.hierarchical.operational.manager import OperationalManager
from argumentation_analysis.orchestration.hierarchical.operational.state import OperationalState
from argumentation_analysis.orchestration.hierarchical.interfaces.strategic_tactical import StrategicTacticalInterface
from argumentation_analysis.orchestration.hierarchical.interfaces.tactical_operational import TacticalOperationalInterface

# Création des états
strategic_state = StrategicState()
tactical_state = TacticalState()
operational_state = OperationalState()

# Création des interfaces
st_interface = StrategicTacticalInterface(strategic_state, tactical_state)
to_interface = TacticalOperationalInterface(tactical_state, operational_state)

# Création des composants principaux
strategic_manager = StrategicManager(strategic_state, st_interface)
tactical_coordinator = TaskCoordinator(tactical_state, st_interface, to_interface)
operational_manager = OperationalManager(operational_state, to_interface)

# Définition d'un objectif global
objective = {
    "type": "analyze_argumentation",
    "text": "texte_à_analyser.txt",
    "focus": "fallacies",
    "depth": "comprehensive"
}

# Exécution du processus d'analyse
strategic_manager.set_objective(objective)
strategic_manager.execute()

# Récupération des résultats
results = strategic_manager.get_final_results()
```

## Développement

Pour étendre l'architecture hiérarchique :

1. **Ajouter un nouvel agent opérationnel** : Créez un adaptateur dans le répertoire `operational/adapters/` qui implémente l'interface `OperationalAgent`.
2. **Ajouter une nouvelle stratégie** : Créez une nouvelle classe dans le répertoire `strategic/` qui étend les fonctionnalités existantes.
3. **Ajouter un nouveau mécanisme de coordination** : Étendez les fonctionnalités du `TaskCoordinator` dans le répertoire `tactical/`.

## Tests

Des tests unitaires et d'intégration sont disponibles dans le répertoire `tests/` pour valider le fonctionnement de l'architecture hiérarchique.

## Voir aussi

- [Documentation du système d'orchestration](../README.md)
- [Documentation des agents spécialistes](../../agents/README.md)
- [Documentation des outils d'analyse rhétorique](../../agents/tools/analysis/README.md)
- [Documentation de l'architecture globale](../../../docs/architecture/architecture_hierarchique.md)