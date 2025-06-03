# Interfaces de l'Architecture Hiérarchique

Ce répertoire contient les composants responsables de la communication entre les différents niveaux de l'architecture hiérarchique (stratégique, tactique, opérationnel), y compris les mécanismes de délégation, de reporting et d'escalade.

## Vue d'ensemble

L'architecture hiérarchique du système est organisée en trois niveaux distincts :

1. **Niveau Stratégique** : Responsable de la planification globale, de l'allocation des ressources et des décisions de haut niveau.
2. **Niveau Tactique** : Responsable de la coordination des tâches, de la résolution des conflits et de la supervision des agents opérationnels.
3. **Niveau Opérationnel** : Responsable de l'exécution des tâches spécifiques et de l'interaction directe avec les données et les outils d'analyse.

Les interfaces définies dans ce répertoire assurent une communication fluide et structurée entre ces niveaux, permettant une orchestration efficace du processus d'analyse argumentative.

## Composants principaux

### StrategicTacticalInterface

L'interface entre les niveaux stratégique et tactique est responsable de :

- Traduire les objectifs stratégiques en directives tactiques
- Transmettre le contexte global nécessaire au niveau tactique
- Remonter les rapports de progression du niveau tactique au niveau stratégique
- Remonter les résultats agrégés du niveau tactique au niveau stratégique

Cette interface utilise les adaptateurs de communication stratégiques et tactiques pour faciliter l'échange de messages entre ces deux niveaux.

### TacticalOperationalInterface

L'interface entre les niveaux tactique et opérationnel est responsable de :

- Traduire les tâches tactiques en tâches opérationnelles spécifiques
- Transmettre le contexte local nécessaire aux agents opérationnels
- Remonter les résultats d'analyse du niveau opérationnel au niveau tactique
- Remonter les métriques d'exécution du niveau opérationnel au niveau tactique

Cette interface utilise les adaptateurs de communication tactiques et opérationnels pour faciliter l'échange de messages entre ces deux niveaux.

## Flux de communication

Le flux de communication typique dans l'architecture hiérarchique suit ce schéma :

1. Le niveau stratégique définit des objectifs et des plans globaux
2. Ces objectifs sont transmis au niveau tactique via la `StrategicTacticalInterface`
3. Le niveau tactique décompose ces objectifs en tâches spécifiques
4. Ces tâches sont transmises au niveau opérationnel via la `TacticalOperationalInterface`
5. Les agents opérationnels exécutent les tâches et génèrent des résultats
6. Les résultats sont remontés au niveau tactique via la `TacticalOperationalInterface`
7. Le niveau tactique agrège et analyse ces résultats
8. Les résultats agrégés sont remontés au niveau stratégique via la `StrategicTacticalInterface`

## Utilisation

Pour utiliser ces interfaces dans le cadre de l'orchestration hiérarchique :

```python
# Exemple d'utilisation de l'interface stratégique-tactique
from argumentation_analysis.orchestration.hierarchical.interfaces.strategic_tactical import StrategicTacticalInterface

# Initialisation de l'interface
strategic_state = StrategicState()
tactical_state = TacticalState()
st_interface = StrategicTacticalInterface(strategic_state, tactical_state)

# Transmission d'un objectif stratégique au niveau tactique
objective = {"type": "analyze_argumentation", "parameters": {...}}
st_interface.delegate_objective(objective)

# Remontée des résultats du niveau tactique au niveau stratégique
results = tactical_state.get_aggregated_results()
st_interface.report_results(results)
```

## Intégration avec le système de communication

Les interfaces utilisent le système de communication core pour structurer les échanges entre les différents niveaux. Elles s'appuient sur :

- Les adaptateurs spécifiques à chaque niveau (`StrategicAdapter`, `TacticalAdapter`, `OperationalAdapter`)
- Les middlewares de message pour le traitement et la transformation des messages
- Les canaux de communication pour la transmission asynchrone des messages

## Voir aussi

- [Documentation du niveau stratégique](../strategic/README.md)
- [Documentation du niveau tactique](../tactical/README.md)
- [Documentation du niveau opérationnel](../operational/README.md)
- [Documentation du système de communication](../../../../core/communication/README.md)