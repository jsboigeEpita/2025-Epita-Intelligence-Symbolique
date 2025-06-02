# Niveau Stratégique de l'Architecture Hiérarchique

Ce répertoire contient les composants du niveau stratégique de l'architecture hiérarchique, responsables de la planification stratégique, de la définition des objectifs globaux et de l'allocation des ressources.

## Vue d'ensemble

Le niveau stratégique représente la couche supérieure de l'architecture hiérarchique à trois niveaux. Il est responsable de :

- Définir les objectifs globaux de l'analyse argumentative
- Élaborer des plans stratégiques pour atteindre ces objectifs
- Allouer les ressources nécessaires aux différentes parties de l'analyse
- Évaluer les résultats finaux et formuler des conclusions globales
- Interagir avec l'utilisateur pour recevoir des directives et présenter les résultats

Ce niveau prend des décisions de haut niveau qui guident l'ensemble du processus d'analyse, sans s'impliquer dans les détails d'exécution qui sont délégués aux niveaux inférieurs (tactique et opérationnel).

## Composants principaux

### StrategicManager

Le Gestionnaire Stratégique est l'agent principal du niveau stratégique, responsable de :

- La coordination globale entre les agents stratégiques
- L'interface principale avec l'utilisateur et le niveau tactique
- La prise de décisions finales concernant la stratégie d'analyse
- L'évaluation des résultats finaux et la formulation de la conclusion globale

Le StrategicManager orchestre les autres composants stratégiques et maintient une vue d'ensemble du processus d'analyse.

### ResourceAllocator

L'Allocateur de Ressources est responsable de la gestion des ressources du système, notamment :

- Gérer l'allocation des ressources computationnelles et cognitives
- Déterminer quels agents opérationnels doivent être activés
- Établir les priorités entre les différentes tâches d'analyse
- Optimiser l'utilisation des capacités des agents
- Ajuster l'allocation en fonction des besoins émergents

Le ResourceAllocator assure une utilisation efficace des ressources disponibles pour maximiser la performance du système.

### StrategicPlanner

Le Planificateur Stratégique est spécialisé dans la création de plans d'analyse structurés :

- Créer des plans d'analyse structurés
- Décomposer les objectifs globaux en sous-objectifs cohérents
- Établir les dépendances entre les différentes parties de l'analyse
- Définir les critères de succès pour chaque objectif
- Ajuster les plans en fonction des feedbacks du niveau tactique

Le StrategicPlanner traduit les objectifs généraux en plans concrets qui peuvent être exécutés par les niveaux inférieurs.

### StrategicState

L'état stratégique maintient les informations partagées entre les composants du niveau stratégique, notamment :

- Les objectifs globaux actuels
- L'état d'avancement des différentes parties du plan
- Les ressources disponibles et leur allocation
- Les résultats agrégés remontés du niveau tactique

## Flux de travail typique

1. L'utilisateur définit un objectif global d'analyse argumentative
2. Le StrategicManager reçoit cet objectif et initialise le processus
3. Le StrategicPlanner décompose l'objectif en sous-objectifs et crée un plan
4. Le ResourceAllocator détermine les ressources à allouer à chaque partie du plan
5. Le StrategicManager délègue les sous-objectifs au niveau tactique via l'interface stratégique-tactique
6. Le niveau tactique exécute les tâches et remonte les résultats
7. Le StrategicManager évalue les résultats et ajuste la stratégie si nécessaire
8. Une fois l'analyse complétée, le StrategicManager formule une conclusion globale
9. Les résultats finaux sont présentés à l'utilisateur

## Utilisation

Pour utiliser les composants du niveau stratégique :

```python
# Initialisation des composants stratégiques
from argumentation_analysis.orchestration.hierarchical.strategic.manager import StrategicManager
from argumentation_analysis.orchestration.hierarchical.strategic.planner import StrategicPlanner
from argumentation_analysis.orchestration.hierarchical.strategic.allocator import ResourceAllocator
from argumentation_analysis.orchestration.hierarchical.strategic.state import StrategicState

# Création de l'état partagé
strategic_state = StrategicState()

# Initialisation des composants
manager = StrategicManager(strategic_state)
planner = StrategicPlanner(strategic_state)
allocator = ResourceAllocator(strategic_state)

# Définition d'un objectif global
objective = {
    "type": "analyze_argumentation",
    "text": "texte_à_analyser.txt",
    "focus": "fallacies",
    "depth": "comprehensive"
}

# Exécution du processus stratégique
manager.set_objective(objective)
plan = planner.create_plan(objective)
resource_allocation = allocator.allocate_resources(plan)
manager.execute_plan(plan, resource_allocation)

# Récupération des résultats
results = manager.get_final_results()
```

## Communication avec les autres niveaux

Le niveau stratégique communique principalement avec le niveau tactique via l'interface stratégique-tactique. Cette communication comprend :

- La délégation des sous-objectifs au niveau tactique
- La réception des rapports de progression du niveau tactique
- La réception des résultats agrégés du niveau tactique
- L'envoi de directives d'ajustement au niveau tactique

## Voir aussi

- [Documentation des interfaces hiérarchiques](../interfaces/README.md)
- [Documentation du niveau tactique](../tactical/README.md)
- [Documentation du niveau opérationnel](../operational/README.md)