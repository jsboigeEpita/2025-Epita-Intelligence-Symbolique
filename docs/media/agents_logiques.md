# Agents Logiques : Présentation Générale

## Introduction

Les agents logiques sont des composants logiciels spécialisés qui permettent de représenter, manipuler et raisonner sur des connaissances exprimées dans différents systèmes de logique formelle. Ils constituent un élément fondamental de notre architecture pour l'intelligence symbolique.

## Types d'agents logiques

Notre système prend en charge trois types principaux d'agents logiques, chacun spécialisé dans un système de logique particulier :

### 1. Agent de logique propositionnelle

- **Domaine** : Raisonnement sur des propositions simples (vraies ou fausses)
- **Capacités** : Évaluation de formules, vérification de cohérence, déduction logique
- **Utilisations** : Systèmes experts simples, validation de règles métier, analyse de conditions

### 2. Agent de logique du premier ordre

- **Domaine** : Raisonnement sur des objets, leurs propriétés et relations
- **Capacités** : Quantification universelle et existentielle, unification, résolution
- **Utilisations** : Représentation de connaissances complexes, bases de connaissances, systèmes d'inférence

### 3. Agent de logique modale

- **Domaine** : Raisonnement sur des modalités (nécessité, possibilité, croyance, etc.)
- **Capacités** : Évaluation dans différents mondes possibles, raisonnement sur les croyances
- **Utilisations** : Modélisation de connaissances incertaines, systèmes multi-agents, raisonnement temporel

## Architecture des agents logiques

Tous nos agents logiques partagent une architecture commune :

```
┌─────────────────────────┐
│     BaseLogicAgent      │
└─────────────────────────┘
            ▲
            │
  ┌─────────┼─────────┐
  │         │         │
┌─┴──┐    ┌─┴──┐    ┌─┴──┐
│Prop│    │FOL │    │Modal│
└────┘    └────┘    └────┘
```

### Composants clés

1. **Interface commune unifiée** : Tous les agents héritent de `BaseLogicAgent`, qui définit l'interface pour le raisonnement ET l'orchestration de tâches.
2. **Ensembles de croyances** : Représentation formelle des connaissances (`BeliefSet`)
3. **Moteur d'inférence** : Mécanismes de raisonnement adaptés à chaque type de logique
4. **TweetyBridge** : Interface avec la bibliothèque TweetyProject pour les opérations logiques complexes
5. **LogicFactory** : Fabrique pour créer l'agent approprié selon le type de logique

## Fonctionnalités principales

### 1. Création d'ensembles de croyances

Les agents peuvent créer des ensembles de croyances à partir de :
- Texte en langage naturel
- Formules logiques formelles
- Combinaison d'ensembles de croyances existants

### 2. Exécution de requêtes

Les agents peuvent répondre à des requêtes comme :
- Vérifier si une formule est vraie dans un ensemble de croyances
- Trouver des modèles satisfaisant un ensemble de croyances
- Vérifier la cohérence d'un ensemble de croyances

### 3. Génération de requêtes pertinentes

Les agents peuvent générer automatiquement des requêtes pertinentes pour un ensemble de croyances donné, facilitant l'exploration des connaissances.

### 4. Interprétation des résultats

Les agents peuvent fournir des explications détaillées sur les résultats des requêtes, rendant le raisonnement logique plus accessible.

## Intégration avec l'API Web

Tous les agents logiques sont accessibles via une API Web RESTful, permettant :
- L'utilisation à distance des capacités de raisonnement logique
- L'intégration facile dans des applications tierces
- Le développement d'interfaces utilisateur conviviales

## Cas d'utilisation

1. **Analyse de textes juridiques** : Extraction et vérification de règles et conditions
2. **Systèmes d'aide à la décision** : Modélisation de problèmes complexes et évaluation de solutions
3. **Validation de spécifications** : Vérification de cohérence et complétude
4. **Éducation** : Outils pédagogiques pour l'apprentissage de la logique formelle

## Conclusion

Les agents logiques constituent une infrastructure puissante pour le raisonnement symbolique, offrant :
- Une représentation formelle des connaissances
- Des mécanismes de raisonnement rigoureux
- Une flexibilité pour différents types de logique
- Une intégration facile via l'API Web

Ils forment la base de notre système d'intelligence symbolique, permettant de combiner la rigueur de la logique formelle avec la flexibilité des interfaces modernes.