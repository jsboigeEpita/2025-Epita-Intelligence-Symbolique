# Guide d'utilisation des agents logiques

## Table des matières

1. [Introduction](#introduction)
2. [Concepts fondamentaux](#concepts-fondamentaux)
   - [Ensembles de croyances (Belief Sets)](#ensembles-de-croyances-belief-sets)
   - [Types de logiques supportés](#types-de-logiques-supportés)
   - [Requêtes logiques](#requêtes-logiques)
3. [Architecture du système](#architecture-du-système)
   - [Composants principaux](#composants-principaux)
   - [Flux de travail](#flux-de-travail)
4. [Utilisation des agents logiques](#utilisation-des-agents-logiques)
   - [Initialisation](#initialisation)
   - [Conversion de texte en ensemble de croyances](#conversion-de-texte-en-ensemble-de-croyances)
   - [Génération de requêtes](#génération-de-requêtes)
   - [Exécution de requêtes](#exécution-de-requêtes)
   - [Interprétation des résultats](#interprétation-des-résultats)
5. [Intégration avec d'autres composants](#intégration-avec-dautres-composants)
6. [Bonnes pratiques](#bonnes-pratiques)
7. [Dépannage](#dépannage)
8. [Ressources supplémentaires](#ressources-supplémentaires)

## Introduction

Les agents logiques constituent un composant essentiel du système d'analyse argumentative, permettant d'évaluer la validité et la cohérence des arguments à l'aide de différents formalismes logiques. Ce guide vous explique comment utiliser efficacement les agents logiques dans vos analyses.

Le système d'agents logiques est conçu pour être:
- **Flexible**: supporte plusieurs types de logiques (propositionnelle, premier ordre, modale)
- **Extensible**: architecture modulaire permettant d'ajouter de nouveaux types de logiques
- **Intégrable**: s'intègre facilement avec d'autres composants du système d'analyse
- **Accessible**: interface simple et cohérente pour tous les types de logiques

## Concepts fondamentaux

### Ensembles de croyances (Belief Sets)

Un ensemble de croyances (Belief Set) est une représentation formelle d'un ensemble de propositions logiques. Dans notre système, les ensembles de croyances sont extraits à partir de textes en langage naturel et servent de base pour l'évaluation logique des arguments.

Chaque ensemble de croyances possède:
- Un **type de logique** (propositionnelle, premier ordre, modale)
- Un **contenu** exprimé dans la syntaxe appropriée pour le type de logique
- Un **identifiant unique** pour référence ultérieure

### Types de logiques supportés

Le système prend en charge trois types de logiques:

1. **Logique propositionnelle**: Utilise des variables propositionnelles et des connecteurs logiques (ET, OU, NON, IMPLIQUE, etc.) pour représenter des propositions simples.
   - Syntaxe: Utilise les opérateurs `!` (négation), `||` (disjonction), `&&` (conjonction), `=>` (implication), `<=>` (équivalence), `^^` (XOR).
   - Exemple: `(p && q) => r`

2. **Logique du premier ordre**: Étend la logique propositionnelle avec des quantificateurs (∀, ∃) et des prédicats.
   - Syntaxe: Utilise `forall` et `exists` pour les quantificateurs, et des prédicats comme `P(x)`.
   - Exemple: `forall x: (Humain(x) => Mortel(x))`

3. **Logique modale**: Ajoute des opérateurs modaux pour exprimer des notions comme la nécessité (□) et la possibilité (◇).
   - Syntaxe: Utilise `[]` pour la nécessité et `<>` pour la possibilité.
   - Exemple: `[](p => q)` (il est nécessaire que p implique q)

### Requêtes logiques

Les requêtes logiques permettent d'interroger un ensemble de croyances pour vérifier si certaines propositions sont des conséquences logiques de l'ensemble. Une requête peut:
- Vérifier si une formule est une conséquence logique de l'ensemble de croyances
- Tester la cohérence de l'ensemble de croyances
- Évaluer des implications entre différentes propositions

## Architecture du système

### Composants principaux

Le système d'agents logiques est composé des éléments suivants:

1. **AbstractLogicAgent**: Classe abstraite définissant l'interface commune à tous les agents logiques.
2. **Agents spécifiques**: Implémentations concrètes pour chaque type de logique:
   - `PropositionalLogicAgent`: Pour la logique propositionnelle
   - `FirstOrderLogicAgent`: Pour la logique du premier ordre
   - `ModalLogicAgent`: Pour la logique modale
3. **LogicFactory**: Factory pour créer les agents appropriés selon le type de logique.
4. **BeliefSet**: Représentation des ensembles de croyances.
5. **TweetyBridge**: Interface avec la bibliothèque TweetyProject pour le raisonnement logique.
6. **QueryExecutor**: Exécuteur de requêtes logiques.

### Flux de travail

Le flux de travail typique pour l'utilisation des agents logiques est le suivant:

1. **Création de l'agent**: Utilisation de `LogicFactory` pour créer l'agent approprié.
2. **Conversion du texte**: Transformation d'un texte en ensemble de croyances.
3. **Génération de requêtes**: Création de requêtes pertinentes basées sur le texte et l'ensemble de croyances.
4. **Exécution des requêtes**: Évaluation des requêtes sur l'ensemble de croyances.
5. **Interprétation des résultats**: Analyse et explication des résultats des requêtes.

## Utilisation des agents logiques

### Initialisation

Pour initialiser un agent logique, utilisez la factory:

```python
from semantic_kernel import Kernel
from argumentation_analysis.agents.core.logic.logic_factory import LogicAgentFactory

# Créer un kernel Semantic Kernel
kernel = Kernel()

# Initialiser un service LLM (exemple avec OpenAI)
llm_service = kernel.add_service("gpt-4", "openai")

# Créer un agent logique propositionnelle
agent = LogicAgentFactory.create_agent("propositional", kernel, llm_service)
```

### Conversion de texte en ensemble de croyances

Pour convertir un texte en ensemble de croyances:

```python
text = """
Si le ciel est nuageux, alors il va pleuvoir.
Le ciel est nuageux.
"""

belief_set, status_msg = agent.text_to_belief_set(text)

if belief_set:
    print(f"Ensemble de croyances créé: {belief_set.content}")
else:
    print(f"Erreur: {status_msg}")
```

### Génération de requêtes

Pour générer des requêtes pertinentes:

```python
queries = agent.generate_queries(text, belief_set)
print(f"Requêtes générées: {queries}")
```

### Exécution de requêtes

Pour exécuter une requête sur un ensemble de croyances:

```python
query = "il va pleuvoir"
result, result_msg = agent.execute_query(belief_set, query)

if result is not None:
    print(f"Résultat: {result} - {result_msg}")
else:
    print(f"Erreur: {result_msg}")
```

### Interprétation des résultats

Pour interpréter les résultats de plusieurs requêtes:

```python
interpretation = agent.interpret_results(text, belief_set, queries, results)
print(f"Interprétation: {interpretation}")
```

## Intégration avec d'autres composants

Les agents logiques peuvent être intégrés avec d'autres composants du système d'analyse argumentative:

### Intégration avec l'orchestrateur

```python
# Dans un agent d'orchestration
def analyze_argument(text):
    # Créer un agent logique
    logic_agent = LogicAgentFactory.create_agent("propositional", self.kernel, self.llm_service)
    
    # Convertir le texte en ensemble de croyances
    belief_set, _ = logic_agent.text_to_belief_set(text)
    
    # Générer et exécuter des requêtes
    queries = logic_agent.generate_queries(text, belief_set)
    results = []
    
    for query in queries:
        result, result_msg = logic_agent.execute_query(belief_set, query)
        results.append(result_msg)
    
    # Interpréter les résultats
    interpretation = logic_agent.interpret_results(text, belief_set, queries, results)
    
    return interpretation
```

### Intégration avec l'API Web

Les agents logiques sont exposés via l'API Web, permettant leur utilisation à distance:

- Endpoint `/api/logic/belief-set`: Convertit un texte en ensemble de croyances
- Endpoint `/api/logic/query`: Exécute une requête sur un ensemble de croyances
- Endpoint `/api/logic/generate-queries`: Génère des requêtes pertinentes
- Endpoint `/api/logic/interpret`: Interprète les résultats des requêtes

## Bonnes pratiques

### Optimisation des ensembles de croyances

- **Simplicité**: Gardez les ensembles de croyances aussi simples que possible
- **Cohérence**: Assurez-vous que les ensembles de croyances sont cohérents
- **Pertinence**: Incluez uniquement les propositions pertinentes pour l'analyse

### Formulation des requêtes

- **Spécificité**: Formulez des requêtes précises et ciblées
- **Progressivité**: Commencez par des requêtes simples avant de passer à des requêtes plus complexes
- **Diversité**: Explorez différents aspects de l'argument avec des requêtes variées

### Performance

- **Limitation**: Limitez le nombre de requêtes pour les ensembles de croyances complexes
- **Mise en cache**: Réutilisez les ensembles de croyances pour plusieurs analyses
- **Parallélisation**: Exécutez les requêtes en parallèle lorsque c'est possible

## Dépannage

### Problèmes courants

1. **Erreurs de syntaxe dans les ensembles de croyances**:
   - Vérifiez que la syntaxe est correcte pour le type de logique utilisé
   - Utilisez la méthode `validate_belief_set` de TweetyBridge pour valider la syntaxe

2. **Requêtes non valides**:
   - Assurez-vous que les requêtes utilisent la même syntaxe que l'ensemble de croyances
   - Utilisez la méthode `validate_formula` de TweetyBridge pour valider les requêtes

3. **Résultats indéterminés**:
   - Certaines requêtes peuvent être indéterminées si l'ensemble de croyances n'est pas assez contraint
   - Ajoutez plus d'informations à l'ensemble de croyances ou reformulez la requête

4. **Problèmes de performance**:
   - La logique du premier ordre et la logique modale peuvent être coûteuses en calcul
   - Limitez la complexité des ensembles de croyances et des requêtes

### Journalisation

Le système utilise un système de journalisation détaillé pour faciliter le dépannage:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Ressources supplémentaires

- [Exemples de logique propositionnelle](exemples_logique_propositionnelle.md)
- [Exemples de logique du premier ordre](exemples_logique_premier_ordre.md)
- [Exemples de logique modale](exemples_logique_modale.md)
- [Guide d'intégration avec l'API Web](integration_api_web.md)
- [Documentation de TweetyProject](http://tweetyproject.org/doc/)
- [Tutoriel interactif sur les agents logiques](../../examples/notebooks/logic_agents_tutorial.ipynb)