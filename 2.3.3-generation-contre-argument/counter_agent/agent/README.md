# Agent de génération de contre-arguments

Ce module contient l'implémentation principale de l'agent de génération de contre-arguments.

## Structure

- **`definitions.py`**: Définitions des structures de données utilisées par l'agent (types de contre-arguments, classes d'arguments, etc.)
- **`counter_agent.py`**: Implémentation de l'agent principal avec ses fonctionnalités d'analyse, de génération et d'évaluation
- **`parser.py`**: Parseurs pour l'analyse des arguments et l'identification des vulnérabilités
- **`strategies.py`**: Implémentation des différentes stratégies rhétoriques pour la génération de contre-arguments

## Architecture

L'agent suit une architecture en pipeline pour la génération de contre-arguments :

1. **Analyse d'arguments** : Extraction des prémisses, de la conclusion et détermination du type d'argument
2. **Identification des vulnérabilités** : Détection des faiblesses dans la structure argumentative
3. **Sélection de stratégie** : Choix de la stratégie rhétorique la plus appropriée
4. **Génération de contre-arguments** : Production de contre-arguments ciblant les vulnérabilités identifiées
5. **Évaluation de qualité** : Mesure de la pertinence, de la force logique et de la persuasion des contre-arguments

## Utilisation

Voici un exemple d'utilisation basique :

```python
from counter_agent.agent import CounterArgumentAgent, CounterArgumentType

# Créer l'agent
agent = CounterArgumentAgent()

# Analyser un argument
argument = agent.analyze_argument(
    "Tous les étudiants qui travaillent dur réussissent leurs examens. "
    "Marie travaille dur. Donc Marie réussira ses examens."
)

# Identifier les vulnérabilités
vulnerabilities = agent.identify_vulnerabilities(argument)

# Générer un contre-argument
counter_argument = agent.generate_counter_argument(
    argument, 
    CounterArgumentType.COUNTER_EXAMPLE,
    vulnerabilities
)

# Évaluer la qualité
evaluation = agent.evaluate_counter_argument(argument, counter_argument)
```

## Types de contre-arguments

L'agent peut générer plusieurs types de contre-arguments :

- **Réfutation directe** : Contredit directement la conclusion
- **Contre-exemple** : Fournit un exemple qui invalide la généralisation
- **Explication alternative** : Propose une autre explication pour les mêmes faits
- **Remise en question des prémisses** : Conteste la validité des prémisses
- **Réduction à l'absurde** : Montre que l'argument mène à des conclusions absurdes

## Stratégies rhétoriques

Différentes stratégies rhétoriques sont disponibles :

- **Questionnement socratique** : Pose des questions qui exposent les faiblesses
- **Réduction à l'absurde** : Pousse la logique de l'argument à l'extrême
- **Contre-argumentation par analogie** : Utilise des analogies pour exposer les failles
- **Appel à l'autorité** : S'appuie sur des experts ou des études
- **Évidence statistique** : Utilise des données statistiques contradictoires 