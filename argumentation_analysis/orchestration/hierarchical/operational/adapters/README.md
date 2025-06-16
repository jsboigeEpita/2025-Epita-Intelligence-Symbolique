# Adaptateurs pour Agents Opérationnels

Ce répertoire contient les adaptateurs qui permettent aux agents existants de fonctionner comme des agents opérationnels dans l'architecture hiérarchique.

## Vue d'ensemble

Les adaptateurs jouent un rôle crucial dans l'intégration des agents spécialisés au sein de l'architecture hiérarchique. Ils servent de "ponts" entre :

- Les agents spécialisés existants (développés indépendamment)
- L'interface standardisée des agents opérationnels de l'architecture hiérarchique

Cette approche basée sur le pattern Adapter permet de :

- Réutiliser les agents existants sans modifier leur code source
- Standardiser les interactions avec le niveau tactique
- Faciliter l'ajout de nouveaux agents à l'architecture
- Isoler les changements dans l'implémentation des agents

## Adaptateurs disponibles

### ExtractAgentAdapter

Cet adaptateur permet à l'agent d'extraction existant de fonctionner comme un agent opérationnel dans l'architecture hiérarchique. L'agent d'extraction est responsable de l'identification et de l'extraction des éléments argumentatifs dans un texte.

L'adaptateur :
- Traduit les tâches opérationnelles en appels à l'API de l'agent d'extraction
- Convertit les résultats d'extraction au format attendu par le niveau tactique
- Gère le cycle de vie de l'agent d'extraction dans le contexte hiérarchique

### InformalAgentAdapter

Cet adaptateur permet à l'agent d'analyse informelle de fonctionner comme un agent opérationnel. L'agent informel est responsable de l'analyse des sophismes et des structures argumentatives informelles.

L'adaptateur :
- Intègre l'agent informel avec les outils d'analyse rhétorique améliorés
- Traduit les tâches opérationnelles en séquences d'analyse informelle
- Convertit les résultats d'analyse au format standardisé
- Gère les interactions avec le Semantic Kernel et les services LLM

### PLAgentAdapter

Cet adaptateur permet à l'agent de logique propositionnelle (PL) de fonctionner comme un agent opérationnel. L'agent PL est responsable de l'analyse formelle des arguments en utilisant la logique propositionnelle.

L'adaptateur :
- Traduit les tâches opérationnelles en formules et requêtes de logique propositionnelle
- Gère les interactions avec les solveurs SAT et les outils de vérification formelle
- Convertit les résultats formels en insights exploitables par le niveau tactique

## Architecture des adaptateurs

Chaque adaptateur implémente l'interface `OperationalAgent` définie dans le module `agent_interface.py` du niveau opérationnel. Cette interface standardisée comprend des méthodes comme :

- `execute_task(task)` : Exécute une tâche opérationnelle spécifique
- `get_capabilities()` : Retourne les capacités de l'agent
- `get_status()` : Retourne l'état actuel de l'agent
- `handle_feedback(feedback)` : Traite les retours du niveau tactique

En interne, l'adaptateur :
1. Reçoit une tâche du niveau tactique
2. Traduit cette tâche en appels à l'API de l'agent spécialisé
3. Surveille l'exécution de l'agent
4. Collecte et transforme les résultats
5. Retourne les résultats au niveau tactique dans un format standardisé

## Utilisation

Pour utiliser un adaptateur dans le contexte de l'architecture hiérarchique :

```python
# Import de l'adaptateur
from argumentation_analysis.orchestration.hierarchical.operational.adapters import ExtractAgentAdapter

# Création de l'adaptateur
extract_adapter = ExtractAgentAdapter()

# Enregistrement de l'adaptateur auprès du registre des agents opérationnels
from argumentation_analysis.orchestration.hierarchical.operational.agent_registry import AgentRegistry
registry = AgentRegistry()
registry.register_agent("extract", extract_adapter)

# Utilisation via le niveau tactique (généralement fait automatiquement)
task = {
    "id": "task-123",
    "type": "extract_arguments",
    "text": "Le texte à analyser...",
    "parameters": {...}
}
results = extract_adapter.execute_task(task)
```

## Création d'un nouvel adaptateur

Pour intégrer un nouvel agent spécialisé à l'architecture hiérarchique, créez un nouvel adaptateur en suivant ces étapes :

1. Créez une nouvelle classe qui hérite de `OperationalAgent`
2. Implémentez les méthodes requises par l'interface
3. Dans ces méthodes, traduisez les appels en interactions avec votre agent spécialisé
4. Ajoutez votre adaptateur à `__init__.py` pour l'exposer au reste du système

Exemple de structure pour un nouvel adaptateur :

```python
from argumentation_analysis.orchestration.hierarchical.operational.agent_interface import OperationalAgent

class MyNewAgentAdapter(OperationalAgent):
    def __init__(self):
        super().__init__()
        # Initialiser votre agent spécialisé ici
        
    def execute_task(self, task):
        # Traduire la tâche pour votre agent
        # Exécuter votre agent
        # Transformer et retourner les résultats
        
    def get_capabilities(self):
        return {
            "task_types": ["my_specialized_task_type"],
            "parameters": {...}
        }
```

## Voir aussi

- [Documentation du niveau opérationnel](../README.md)
- [Interface des agents opérationnels](../agent_interface.py)
- [Documentation des agents spécialisés](../../../../agents/core/README.md)