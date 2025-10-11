# Agents Logiques

Ce document décrit les agents logiques implémentés dans le système d'analyse argumentative.

## Vue d'ensemble

Les agents logiques sont des composants spécialisés qui permettent de manipuler et raisonner sur des formules logiques. Ils sont utilisés pour analyser la structure logique des arguments et vérifier leur validité.

Le système prend en charge trois types de logiques :
- **Logique propositionnelle** : manipulation de propositions simples et de connecteurs logiques
- **Logique du premier ordre** : ajout de quantificateurs et de prédicats
- **Logique modale** : ajout d'opérateurs de modalité (nécessité, possibilité)

## Architecture

L'architecture des agents logiques est basée sur le principe de la programmation orientée objet avec une hiérarchie de classes :

```
BaseLogicAgent (ABC)
├── PropositionalLogicAgent
├── FirstOrderLogicAgent
└── ModalLogicAgent
```

### Classe BaseLogicAgent

Classe de base abstraite **unifiée** qui définit l'interface commune pour tous les agents logiques. Elle combine les responsabilités de raisonnement formel et d'orchestration de tâches.

- `text_to_belief_set(text)` : Convertit un texte en ensemble de croyances
- `generate_queries(text, belief_set)` : Génère des requêtes logiques pertinentes
- `execute_query(belief_set, query)` : Exécute une requête logique
- `interpret_results(text, belief_set, queries, results)` : Interprète les résultats

### Classe PropositionalLogicAgent

Implémentation pour la logique propositionnelle :

- Utilise la syntaxe de TweetyProject pour les formules propositionnelles
- Prend en charge les connecteurs logiques : négation (!), conjonction (&&), disjonction (||), implication (=>), équivalence (<=>), XOR (^^)
- Utilise un raisonneur SAT pour vérifier la validité des formules

### Classe FirstOrderLogicAgent

Implémentation pour la logique du premier ordre :

- Étend la logique propositionnelle avec des quantificateurs (forall, exists) et des prédicats
- Permet de raisonner sur des domaines d'objets et leurs propriétés
- Utilise un raisonneur FOL pour vérifier la validité des formules

### Classe ModalLogicAgent

Implémentation pour la logique modale :

- Ajoute les opérateurs de modalité : nécessité ([]) et possibilité (<>)
- Permet de raisonner sur différents mondes possibles
- Utilise un raisonneur modal pour vérifier la validité des formules

## LogicAgentFactory

La classe `LogicAgentFactory` est une factory qui permet de créer des instances d'agents logiques en fonction du type de logique spécifié :

```python
agent = LogicAgentFactory.create_agent("propositional", kernel)
```

## BeliefSet

Les ensembles de croyances (`BeliefSet`) sont des conteneurs pour les formules logiques. Ils sont utilisés pour stocker les axiomes et les règles qui définissent un domaine de connaissances.

Il existe trois types d'ensembles de croyances correspondant aux trois types de logiques :
- `PropositionalBeliefSet`
- `FirstOrderBeliefSet`
- `ModalBeliefSet`

## QueryExecutor

La classe `QueryExecutor` est un utilitaire qui permet d'exécuter des requêtes logiques sur des ensembles de croyances. Elle utilise TweetyBridge pour interagir avec TweetyProject.

## TweetyBridge

La classe `TweetyBridge` est une interface entre le code Python et la bibliothèque Java TweetyProject. Elle utilise JPype pour appeler les méthodes Java depuis Python.

## Exemples d'utilisation

### Conversion de texte en ensemble de croyances

```python
from semantic_kernel import Kernel
from argumentation_analysis.agents.core.logic.logic_factory import LogicAgentFactory

# Créer un kernel
kernel = Kernel()

# Créer un agent logique
agent = LogicAgentFactory.create_agent("propositional", kernel)

# Convertir un texte en ensemble de croyances
text = "Si p est vrai, alors q est vrai. p est vrai."
belief_set, message = agent.text_to_belief_set(text)

print(belief_set.content)
# Sortie : "p => q\np"
```

### Exécution d'une requête

```python
# Exécuter une requête
result, message = agent.execute_query(belief_set, "q")

print(result)  # True ou False
print(message)  # Message formaté
```

### Génération de requêtes

```python
# Générer des requêtes pertinentes
queries = agent.generate_queries(text, belief_set)

print(queries)
# Sortie : ["p", "q", "p => q", "p && q"]
```

### Interprétation des résultats

```python
# Exécuter plusieurs requêtes
results = []
for query in queries:
    result, message = agent.execute_query(belief_set, query)
    results.append(message)

# Interpréter les résultats
interpretation = agent.interpret_results(text, belief_set, queries, results)

print(interpretation)
# Sortie : "D'après les axiomes, p est vrai et q est vrai par modus ponens..."
```

## Intégration avec l'API Web

Les agents logiques sont intégrés à l'API Web via le service `LogicService`. Ce service expose les fonctionnalités des agents logiques à travers des endpoints REST.

Voir la documentation des endpoints API pour plus de détails.