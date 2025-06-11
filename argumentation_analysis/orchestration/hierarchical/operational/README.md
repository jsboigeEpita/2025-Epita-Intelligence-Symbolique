# Niveau Opérationnel de l'Architecture Hiérarchique

Ce répertoire contient l'implémentation du niveau opérationnel de l'architecture hiérarchique à trois niveaux pour le système d'analyse rhétorique.

## Vue d'ensemble

Le niveau opérationnel est responsable de l'exécution des tâches spécifiques d'analyse par des agents spécialistes. Il reçoit des tâches du niveau tactique via l'interface tactique-opérationnelle, les exécute à l'aide des agents appropriés, et renvoie les résultats au niveau tactique.

## Structure du code

- `state.py` : Définit la classe `OperationalState` qui encapsule l'état du niveau opérationnel.
- `agent_interface.py` : Définit l'interface commune `OperationalAgent` que tous les agents opérationnels doivent implémenter.
- `agent_registry.py` : Définit la classe `OperationalAgentRegistry` qui gère les agents disponibles et sélectionne l'agent approprié pour une tâche donnée.
- `manager.py` : Définit la classe `OperationalManager` qui sert d'interface entre le niveau tactique et les agents opérationnels.
- `adapters/` : Contient les adaptateurs pour les agents existants.
  - `extract_agent_adapter.py` : Adaptateur pour l'agent d'extraction.
  - `informal_agent_adapter.py` : Adaptateur pour l'agent informel.
  - `pl_agent_adapter.py` : Adaptateur pour l'agent de logique propositionnelle.

## Adaptations réalisées

### 1. État opérationnel

L'état opérationnel (`OperationalState`) a été créé pour encapsuler toutes les données pertinentes pour le niveau opérationnel, notamment :
- Les tâches assignées
- Les extraits de texte à analyser
- Les résultats d'analyse
- Les problèmes rencontrés
- Les métriques opérationnelles
- Le journal des actions

### 2. Interface commune pour les agents

Une interface commune (`OperationalAgent`) a été définie pour tous les agents opérationnels. Cette interface définit les méthodes que tous les agents doivent implémenter :
- `process_task` : Traite une tâche opérationnelle.
- `get_capabilities` : Retourne les capacités de l'agent.
- `can_process_task` : Vérifie si l'agent peut traiter une tâche donnée.

### 3. Adaptateurs pour les agents existants

Des adaptateurs ont été créés pour les agents existants afin qu'ils puissent fonctionner dans la nouvelle architecture :
- `ExtractAgentAdapter` : Adapte l'agent d'extraction existant.
- `InformalAgentAdapter` : Adapte l'agent informel existant.
- `PLAgentAdapter` : Adapte l'agent de logique propositionnelle existant.

Ces adaptateurs implémentent l'interface `OperationalAgent` et font le pont entre la nouvelle architecture et les agents existants.

### 4. Registre d'agents

Un registre d'agents (`OperationalAgentRegistry`) a été créé pour gérer les agents disponibles et sélectionner l'agent approprié pour une tâche donnée. Ce registre :
- Maintient une liste des types d'agents disponibles
- Crée et initialise les agents à la demande
- Sélectionne l'agent le plus approprié pour une tâche en fonction des capacités requises

### 5. Gestionnaire opérationnel

Un gestionnaire opérationnel (`OperationalManager`) a été créé pour servir d'interface entre le niveau tactique et les agents opérationnels. Ce gestionnaire :
- Reçoit des tâches tactiques via l'interface tactique-opérationnelle
- Les traduit en tâches opérationnelles
- Les fait exécuter par les agents appropriés
- Renvoie les résultats au niveau tactique

## Utilisation des agents dans la nouvelle architecture

### Initialisation

```python
from argumentation_analysis.orchestration.hierarchical.operational.state import OperationalState
from argumentation_analysis.orchestration.hierarchical.operational.manager import OperationalManager
from argumentation_analysis.orchestration.hierarchical.interfaces.tactical_operational import TacticalOperationalInterface
from argumentation_analysis.orchestration.hierarchical.tactical.state import TacticalState

# Créer les états
tactical_state = TacticalState()
operational_state = OperationalState()

# Créer l'interface tactique-opérationnelle
interface = TacticalOperationalInterface(tactical_state, operational_state)

# Créer le gestionnaire opérationnel
manager = OperationalManager(operational_state, interface)
await manager.start()
```

### Traitement d'une tâche

```python
# Créer une tâche tactique
tactical_task = {
    "id": "task-extract-1",
    "description": "Extraire les segments de texte contenant des arguments potentiels",
    "objective_id": "obj-1",
    "estimated_duration": "short",
    "required_capabilities": ["text_extraction"],
    "priority": "high"
}

# Ajouter la tâche à l'état tactique
tactical_state.add_task(tactical_task)

# Traiter la tâche
result = await manager.process_tactical_task(tactical_task)

# Afficher le résultat
print(f"Résultat: {json.dumps(result, indent=2)}")
```

### Arrêt du gestionnaire

```python
# Arrêter le gestionnaire
await manager.stop()
```

## Exemple complet

Un exemple complet d'utilisation des agents dans la nouvelle architecture est disponible dans le fichier `argumentation_analysis/examples/hierarchical_architecture_example.py`.

## Tests d'intégration

Des tests d'intégration pour valider le fonctionnement des agents adaptés sont disponibles dans le fichier `../../../../tests/unit/argumentation_analysis/test_operational_agents_integration.py`.

## Capacités des agents

### Agent d'extraction (ExtractAgent)
- `text_extraction` : Extraction de segments de texte pertinents.
- `preprocessing` : Prétraitement des extraits de texte.
- `extract_validation` : Validation des extraits.

### Agent informel (InformalAgent)
- `argument_identification` : Identification des arguments informels.
- `fallacy_detection` : Détection des sophismes.
- `fallacy_attribution` : Attribution de sophismes à des arguments.
- `fallacy_justification` : Justification de l'attribution de sophismes.
- `informal_analysis` : Analyse informelle des arguments.

### Agent de logique propositionnelle (PLAgent)
- `formal_logic` : Formalisation des arguments en logique propositionnelle.
- `propositional_logic` : Manipulation de formules de logique propositionnelle.
- `validity_checking` : Vérification de la validité des arguments formalisés.
- `consistency_analysis` : Analyse de la cohérence des ensembles de formules.

## Flux de données

1. Le niveau tactique crée une tâche et la transmet au niveau opérationnel via l'interface tactique-opérationnelle.
2. Le gestionnaire opérationnel reçoit la tâche et la traduit en tâche opérationnelle.
3. Le registre d'agents sélectionne l'agent approprié pour la tâche.
4. L'agent exécute la tâche et produit un résultat.
5. Le gestionnaire opérationnel renvoie le résultat au niveau tactique via l'interface tactique-opérationnelle.

## Extensibilité

Pour ajouter un nouvel agent opérationnel :

1. Créer une nouvelle classe qui hérite de `OperationalAgent`.
2. Implémenter les méthodes requises : `process_task`, `get_capabilities`, `can_process_task`.
3. Enregistrer la classe dans le registre d'agents.

Exemple :

```python
from argumentation_analysis.orchestration.hierarchical.operational.agent_interface import OperationalAgent

class NewAgent(OperationalAgent):
    def get_capabilities(self) -> List[str]:
        return ["new_capability"]
    
    def can_process_task(self, task: Dict[str, Any]) -> bool:
        required_capabilities = task.get("required_capabilities", [])
        return "new_capability" in required_capabilities
    
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        # Traitement de la tâche
        return result

# Enregistrement de l'agent
registry.register_agent_class("new", NewAgent)