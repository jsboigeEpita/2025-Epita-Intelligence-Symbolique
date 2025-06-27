# Exemples de logique propositionnelle

## Table des matières

1. [Introduction](#introduction)
2. [Syntaxe de la logique propositionnelle](#syntaxe-de-la-logique-propositionnelle)
3. [Exemples de base](#exemples-de-base)
   - [Exemple 1: Modus Ponens](#exemple-1-modus-ponens)
   - [Exemple 2: Modus Tollens](#exemple-2-modus-tollens)
   - [Exemple 3: Syllogisme hypothétique](#exemple-3-syllogisme-hypothétique)
4. [Exemples intermédiaires](#exemples-intermédiaires)
   - [Exemple 4: Raisonnement par cas](#exemple-4-raisonnement-par-cas)
   - [Exemple 5: Réduction à l'absurde](#exemple-5-réduction-à-labsurde)
5. [Exemples avancés](#exemples-avancés)
   - [Exemple 6: Analyse d'un argument complexe](#exemple-6-analyse-dun-argument-complexe)
   - [Exemple 7: Détection de contradictions](#exemple-7-détection-de-contradictions)
6. [Cas d'utilisation réels](#cas-dutilisation-réels)
   - [Analyse de discours politique](#analyse-de-discours-politique)
   - [Évaluation d'arguments juridiques](#évaluation-darguments-juridiques)
7. [Bonnes pratiques](#bonnes-pratiques)
8. [Ressources supplémentaires](#ressources-supplémentaires)

## Introduction

Pour une implémentation complète des exemples présentés dans ce guide, vous pouvez consulter le script Python suivant : [`examples/logic_agents/propositional_logic_example.py`](../../examples/logic_agents/propositional_logic_example.py:0). Ce script montre comment initialiser l'agent, convertir du texte, exécuter des requêtes et interpréter les résultats pour divers scénarios de logique propositionnelle.

La logique propositionnelle est le type de logique le plus fondamental, permettant de représenter et d'analyser des propositions simples et leurs relations. Ce document présente des exemples concrets d'utilisation de la logique propositionnelle avec notre système d'agents logiques.

La logique propositionnelle est particulièrement adaptée pour:
- Analyser des arguments simples avec des propositions claires
- Vérifier la validité de raisonnements déductifs
- Détecter des incohérences dans un ensemble d'affirmations

## Syntaxe de la logique propositionnelle

Notre système utilise la syntaxe de TweetyProject pour la logique propositionnelle:

| Opérateur | Symbole | Description | Exemple |
|-----------|---------|-------------|---------|
| Négation | `!` | NON logique | `!p` (non p) |
| Conjonction | `&&` | ET logique | `p && q` (p et q) |
| Disjonction | `\|\|` | OU logique | `p \|\| q` (p ou q) |
| Implication | `=>` | SI...ALORS | `p => q` (si p alors q) |
| Équivalence | `<=>` | SI ET SEULEMENT SI | `p <=> q` (p si et seulement si q) |
| XOR | `^^` | OU exclusif | `p ^^ q` (soit p soit q, mais pas les deux) |

Les variables propositionnelles sont généralement représentées par des lettres minuscules (`p`, `q`, `r`, etc.) ou des identifiants plus descriptifs (`pluie`, `nuages`, etc.).

## Exemples de base

### Exemple 1: Modus Ponens

*Le code complet pour cet exemple est disponible dans [`examples/logic_agents/propositional_logic_example.py`](../../examples/logic_agents/propositional_logic_example.py:91).* 


Le Modus Ponens est une règle d'inférence fondamentale: si on a "si P alors Q" et "P", on peut conclure "Q".

**Texte original:**
```
Si le ciel est nuageux, alors il va pleuvoir.
Le ciel est nuageux.
Donc, il va pleuvoir.
```

**Conversion en ensemble de croyances:**
```python
from argumentation_analysis.agents.core.logic.logic_factory import LogicAgentFactory

# Initialiser l'agent
agent = LogicAgentFactory.create_agent("propositional", kernel, llm_service)

# Texte à convertir
text = """
Si le ciel est nuageux, alors il va pleuvoir.
Le ciel est nuageux.
"""

# Convertir en ensemble de croyances
belief_set, status_msg = agent.text_to_belief_set(text)

print(belief_set.content)
```

**Résultat (ensemble de croyances):**
```
nuageux => pluie
nuageux
```

**Requête et exécution:**
```python
# Requête: Est-ce qu'il va pleuvoir?
query = "pluie"
result, result_msg = agent.execute_query(belief_set, query)

print(f"Résultat: {result} - {result_msg}")
```

**Résultat de la requête:**
```
Résultat: True - Tweety Result: Query 'pluie' is ACCEPTED (True).
```

**Interprétation:**
```
L'argument est valide selon le Modus Ponens. Puisque nous savons que "si le ciel est nuageux, alors il va pleuvoir" et que "le ciel est nuageux", nous pouvons logiquement conclure qu'"il va pleuvoir".
```

### Exemple 2: Modus Tollens

*Le code complet pour cet exemple est disponible dans [`examples/logic_agents/propositional_logic_example.py`](../../examples/logic_agents/propositional_logic_example.py:132).* 


Le Modus Tollens est une autre règle d'inférence: si on a "si P alors Q" et "non Q", on peut conclure "non P".

**Texte original:**
```
Si un animal est un mammifère, alors il a des poils.
Ce reptile n'a pas de poils.
Donc, ce reptile n'est pas un mammifère.
```

**Conversion en ensemble de croyances:**
```python
text = """
Si un animal est un mammifère, alors il a des poils.
Ce reptile n'a pas de poils.
"""

belief_set, _ = agent.text_to_belief_set(text)
print(belief_set.content)
```

**Résultat (ensemble de croyances):**
```
mammifere => poils
!poils
```

**Requête et exécution:**
```python
# Requête: Est-ce que le reptile n'est pas un mammifère?
query = "!mammifere"
result, result_msg = agent.execute_query(belief_set, query)

print(f"Résultat: {result} - {result_msg}")
```

**Résultat de la requête:**
```
Résultat: True - Tweety Result: Query '!mammifere' is ACCEPTED (True).
```

**Interprétation:**
```
L'argument est valide selon le Modus Tollens. Puisque nous savons que "si un animal est un mammifère, alors il a des poils" et que "ce reptile n'a pas de poils", nous pouvons logiquement conclure que "ce reptile n'est pas un mammifère".
Le script [`examples/logic_agents/propositional_logic_example.py`](../../examples/logic_agents/propositional_logic_example.py:163) exécute également une requête pour "mammifere", qui retourne `False`, renforçant la conclusion.
```

### Exemple 3: Syllogisme hypothétique

*Bien qu'un exemple explicitement nommé "syllogisme hypothétique" ne soit pas présent dans [`examples/logic_agents/propositional_logic_example.py`](../../examples/logic_agents/propositional_logic_example.py:0), le principe du raisonnement chaîné est illustré dans des exemples plus complexes, comme l'analyse d'argument complexe (voir Exemple 6).*

Le syllogisme hypothétique combine des implications: si on a "si P alors Q" et "si Q alors R", on peut conclure "si P alors R".

**Texte original:**
```
Si l'économie se porte bien, alors le chômage diminue.
Si le chômage diminue, alors la satisfaction des citoyens augmente.
Donc, si l'économie se porte bien, alors la satisfaction des citoyens augmente.
```

**Conversion en ensemble de croyances:**
```python
text = """
Si l'économie se porte bien, alors le chômage diminue.
Si le chômage diminue, alors la satisfaction des citoyens augmente.
"""

belief_set, _ = agent.text_to_belief_set(text)
print(belief_set.content)
```

**Résultat (ensemble de croyances):**
```
economie_bien => chomage_diminue
chomage_diminue => satisfaction_augmente
```

**Requête et exécution:**
```python
# Requête: Si l'économie se porte bien, alors la satisfaction des citoyens augmente?
query = "economie_bien => satisfaction_augmente"
result, result_msg = agent.execute_query(belief_set, query)

print(f"Résultat: {result} - {result_msg}")
```

**Résultat de la requête:**
```
Résultat: True - Tweety Result: Query 'economie_bien => satisfaction_augmente' is ACCEPTED (True).
```

**Interprétation:**
```
L'argument est valide selon le syllogisme hypothétique. Puisque nous savons que "si l'économie se porte bien, alors le chômage diminue" et que "si le chômage diminue, alors la satisfaction des citoyens augmente", nous pouvons logiquement conclure que "si l'économie se porte bien, alors la satisfaction des citoyens augmente".
```

## Exemples intermédiaires

### Exemple 4: Raisonnement par cas

*Le script [`examples/logic_agents/propositional_logic_example.py`](../../examples/logic_agents/propositional_logic_example.py:0) ne contient pas d'exemple explicitement nommé "raisonnement par cas". Cependant, la logique sous-jacente peut être construite en utilisant les fonctionnalités de l'agent.*

Le raisonnement par cas consiste à examiner toutes les possibilités et à montrer que la même conclusion s'ensuit dans chaque cas.

**Texte original:**
```
Soit il pleut, soit il neige.
S'il pleut, alors les routes sont mouillées.
S'il neige, alors les routes sont mouillées.
Donc, les routes sont mouillées.
```

**Conversion en ensemble de croyances:**
```python
text = """
Soit il pleut, soit il neige.
S'il pleut, alors les routes sont mouillées.
S'il neige, alors les routes sont mouillées.
"""

belief_set, _ = agent.text_to_belief_set(text)
print(belief_set.content)
```

**Résultat (ensemble de croyances):**
```
pluie || neige
pluie => routes_mouillees
neige => routes_mouillees
```

**Requête et exécution:**
```python
# Requête: Les routes sont-elles mouillées?
query = "routes_mouillees"
result, result_msg = agent.execute_query(belief_set, query)

print(f"Résultat: {result} - {result_msg}")
```

**Résultat de la requête:**
```
Résultat: True - Tweety Result: Query 'routes_mouillees' is ACCEPTED (True).
```

**Interprétation:**
```
L'argument est valide selon le raisonnement par cas. Puisque nous savons qu'"il pleut ou il neige", que "s'il pleut, alors les routes sont mouillées" et que "s'il neige, alors les routes sont mouillées", nous pouvons logiquement conclure que "les routes sont mouillées" quelle que soit la situation météorologique.
```

### Exemple 5: Réduction à l'absurde

*Le code complet pour un exemple de détection de contradiction, qui utilise un raisonnement similaire, est disponible dans [`examples/logic_agents/propositional_logic_example.py`](../../examples/logic_agents/propositional_logic_example.py:212).* 


La réduction à l'absurde consiste à montrer qu'une hypothèse mène à une contradiction, prouvant ainsi que l'hypothèse est fausse.

**Texte original:**
```
Supposons que tous les politiciens sont honnêtes.
Si tous les politiciens sont honnêtes, alors il n'y a pas de corruption.
Il y a de la corruption.
Donc, tous les politiciens ne sont pas honnêtes.
```

**Conversion en ensemble de croyances:**
```python
text = """
Si tous les politiciens sont honnêtes, alors il n'y a pas de corruption.
Il y a de la corruption.
"""

belief_set, _ = agent.text_to_belief_set(text)
print(belief_set.content)
```

**Résultat (ensemble de croyances):**
```
politiciens_honnetes => !corruption
corruption
```

**Requête et exécution:**
```python
# Requête: Est-ce que tous les politiciens ne sont pas honnêtes?
query = "!politiciens_honnetes"
result, result_msg = agent.execute_query(belief_set, query)

print(f"Résultat: {result} - {result_msg}")
```

**Résultat de la requête:**
```
Résultat: True - Tweety Result: Query '!politiciens_honnetes' is ACCEPTED (True).
```

**Interprétation:**
```
L'argument est valide selon la réduction à l'absurde. Si nous supposons que "tous les politiciens sont honnêtes" et que nous savons que "si tous les politiciens sont honnêtes, alors il n'y a pas de corruption" et qu'"il y a de la corruption", nous arrivons à une contradiction. Donc, l'hypothèse "tous les politiciens sont honnêtes" est fausse, ce qui signifie que "tous les politiciens ne sont pas honnêtes".
```

## Exemples avancés

### Exemple 6: Analyse d'un argument complexe

*Le code complet pour cet exemple est disponible dans [`examples/logic_agents/propositional_logic_example.py`](../../examples/logic_agents/propositional_logic_example.py:168).* 


Analysons un argument plus complexe avec plusieurs prémisses et des relations logiques imbriquées.

**Texte original:**
```
Si le projet est rentable et techniquement faisable, alors nous l'approuverons.
Le projet est rentable.
Si nous approuvons le projet, alors nous devrons embaucher plus de personnel.
Nous n'embaucherons pas plus de personnel sauf si nous obtenons un financement supplémentaire.
Nous n'obtiendrons pas de financement supplémentaire.
Donc, le projet n'est pas techniquement faisable.
```

**Conversion en ensemble de croyances:**
```python
text = """
Si le projet est rentable et techniquement faisable, alors nous l'approuverons.
Le projet est rentable.
Si nous approuvons le projet, alors nous devrons embaucher plus de personnel.
Nous n'embaucherons pas plus de personnel sauf si nous obtenons un financement supplémentaire.
Nous n'obtiendrons pas de financement supplémentaire.
"""

belief_set, _ = agent.text_to_belief_set(text)
print(belief_set.content)
```

**Résultat (ensemble de croyances):**
```
(rentable && faisable) => approbation
rentable
approbation => embauche
embauche => financement
!financement
```

**Requête et exécution:**
```python
# Requête: Le projet est-il techniquement faisable?
query = "!faisable"
result, result_msg = agent.execute_query(belief_set, query)

print(f"Résultat: {result} - {result_msg}")
```

**Résultat de la requête:**
```
Résultat: True - Tweety Result: Query '!faisable' is ACCEPTED (True).
```

**Interprétation:**
```
L'argument est valide. Si nous supposons que le projet est techniquement faisable, alors:
1. Puisque le projet est rentable et faisable, nous l'approuverions.
2. Si nous approuvons le projet, nous devrions embaucher plus de personnel.
3. Si nous embauchons plus de personnel, nous aurions besoin d'un financement supplémentaire.
4. Mais nous n'obtiendrons pas de financement supplémentaire.

Cela crée une contradiction. Par conséquent, notre supposition que le projet est techniquement faisable doit être fausse, ce qui signifie que le projet n'est pas techniquement faisable.
```

### Exemple 7: Détection de contradictions

*Le code complet pour cet exemple est disponible dans [`examples/logic_agents/propositional_logic_example.py`](../../examples/logic_agents/propositional_logic_example.py:212).* 


Utilisons la logique propositionnelle pour détecter des contradictions dans un ensemble d'affirmations.

**Texte original:**
```
Tous les étudiants qui étudient régulièrement réussissent leurs examens.
Alice est une étudiante qui étudie régulièrement.
Alice n'a pas réussi son examen.
```

**Conversion en ensemble de croyances:**
```python
text = """
Tous les étudiants qui étudient régulièrement réussissent leurs examens.
Alice est une étudiante qui étudie régulièrement.
Alice n'a pas réussi son examen.
"""

belief_set, _ = agent.text_to_belief_set(text)
print(belief_set.content)
```

**Résultat (ensemble de croyances):**
```
etudie_regulierement => reussite
alice_etudie_regulierement
!alice_reussite
```

**Requête et exécution:**
```python
# Pour vérifier la cohérence, nous testons si des propositions contradictoires sont dérivables.
# Vérifions si alice_reussite est dérivable
query1 = "alice_reussite"
result1, result_msg1 = agent.execute_query(belief_set, query1)

# Vérifions si !alice_reussite est dérivable
query2 = "!alice_reussite"
result2, result_msg2 = agent.execute_query(belief_set, query2)

print(f"alice_reussite: {result1} - {result_msg1}")
print(f"!alice_reussite: {result2} - {result_msg2}")
```

**Résultats des requêtes:**
```
alice_reussite: True - Tweety Result: Query 'alice_reussite' is ACCEPTED (True).
!alice_reussite: True - Tweety Result: Query '!alice_reussite' is ACCEPTED (True).
```

**Interprétation:**
```
L'ensemble de croyances est incohérent (contradictoire). D'une part, nous pouvons dériver qu'Alice a réussi son examen (car elle étudie régulièrement et tous les étudiants qui étudient régulièrement réussissent). D'autre part, nous avons l'affirmation directe qu'Alice n'a pas réussi son examen. Ces deux conclusions (`alice_reussite` est VRAI et `!alice_reussite` est VRAI) sont contradictoires, ce qui indique qu'au moins une des prémisses doit être fausse. Le script [`examples/logic_agents/propositional_logic_example.py`](../../examples/logic_agents/propositional_logic_example.py:250) confirme cela en montrant que la requête `alice_reussite && !alice_reussite` est ACCEPTED (True) pour cet ensemble de croyances.
```

## Cas d'utilisation réels
# (Cette section a été intégrée dans la précédente pour plus de clarté)

### Analyse de discours politique

**Texte original (extrait d'un discours):**
```
Si nous réduisons les impôts, alors l'économie se développera.
Si l'économie se développe, alors le chômage diminuera.
Nous avons réduit les impôts au cours des quatre dernières années.
Pourtant, le chômage n'a pas diminué.
```

**Conversion en ensemble de croyances:**
```python
text = """
Si nous réduisons les impôts, alors l'économie se développera.
Si l'économie se développe, alors le chômage diminuera.
Nous avons réduit les impôts au cours des quatre dernières années.
Le chômage n'a pas diminué.
"""

belief_set, _ = agent.text_to_belief_set(text)
print(belief_set.content)
```

**Résultat (ensemble de croyances):**
```
reduction_impots => developpement_economie
developpement_economie => diminution_chomage
reduction_impots
!diminution_chomage
```

**Requête et exécution:**
```python
# Requête: L'économie s'est-elle développée?
query = "developpement_economie"
result, result_msg = agent.execute_query(belief_set, query)

print(f"Résultat: {result} - {result_msg}")
```

**Résultat de la requête:**
```
Résultat: False - Tweety Result: Query 'developpement_economie' is REJECTED (False).
```

**Interprétation:**
```
L'ensemble de croyances est incohérent. Si nous acceptons toutes les prémisses comme vraies, nous arrivons à une contradiction. Logiquement, si nous avons réduit les impôts, l'économie aurait dû se développer, et si l'économie s'était développée, le chômage aurait dû diminuer. Mais puisque le chômage n'a pas diminué, soit l'économie ne s'est pas développée (contredisant la première implication), soit la réduction des impôts n'a pas eu lieu (contredisant une prémisse explicite). Cette analyse révèle une faille dans l'argument politique présenté.
```

### Évaluation d'arguments juridiques

**Texte original (extrait d'un raisonnement juridique):**
```
Si l'accusé était présent sur la scène du crime et avait un motif, alors il est coupable.
L'accusé était présent sur la scène du crime.
L'accusé avait un motif.
Cependant, si l'accusé a un alibi solide, alors il n'est pas coupable.
L'accusé a un alibi solide.
```

**Conversion en ensemble de croyances:**
```python
text = """
Si l'accusé était présent sur la scène du crime et avait un motif, alors il est coupable.
L'accusé était présent sur la scène du crime.
L'accusé avait un motif.
Si l'accusé a un alibi solide, alors il n'est pas coupable.
L'accusé a un alibi solide.
"""

belief_set, _ = agent.text_to_belief_set(text)
print(belief_set.content)
```

**Résultat (ensemble de croyances):**
```
(present && motif) => coupable
present
motif
alibi => !coupable
alibi
```

**Requête et exécution:**
```python
# Requête: L'accusé est-il coupable?
query = "coupable"
result, result_msg = agent.execute_query(belief_set, query)

print(f"Résultat: {result} - {result_msg}")

# Requête: L'accusé n'est-il pas coupable?
query2 = "!coupable"
result2, result_msg2 = agent.execute_query(belief_set, query2)

print(f"Résultat: {result2} - {result_msg2}")
```

**Résultats des requêtes:**
```
Résultat: True - Tweety Result: Query 'coupable' is ACCEPTED (True).
Résultat: True - Tweety Result: Query '!coupable' is ACCEPTED (True).
```

**Interprétation:**
```
L'ensemble de croyances est contradictoire. D'une part, nous pouvons conclure que l'accusé est coupable car il était présent sur la scène du crime et avait un motif. D'autre part, nous pouvons conclure qu'il n'est pas coupable car il a un alibi solide. Cette contradiction indique que certaines des prémisses doivent être réexaminées. Par exemple, la présence sur la scène du crime pourrait être remise en question, ou la solidité de l'alibi pourrait être contestée. Cette analyse met en évidence la nécessité d'une enquête plus approfondie.
```

## Bonnes pratiques

1. **Simplification des propositions**:
   - Décomposez les propositions complexes en propositions atomiques
   - Utilisez des variables propositionnelles descriptives

2. **Formalisation précise**:
   - Assurez-vous que les implications sont correctement formalisées
   - Faites attention à la portée des opérateurs logiques

3. **Vérification de la cohérence**:
   - Testez toujours la cohérence de l'ensemble de croyances
   - Identifiez les sources de contradiction

4. **Exploration systématique**:
   - Générez des requêtes pour tester différentes conclusions possibles
   - Examinez les conséquences logiques inattendues

## Ressources supplémentaires

- [Guide d'utilisation des agents logiques](utilisation_agents_logiques.md)
- [Exemples de logique du premier ordre](exemples_logique_premier_ordre.md)
- [Exemples de logique modale](exemples_logique_modale.md)
- [Tutoriel interactif sur les agents logiques](../../examples/notebooks/logic_agents_tutorial.ipynb)
- [Documentation de TweetyProject sur la logique propositionnelle](http://tweetyproject.org/doc/propositional-logic.html)
- [Script d'exemples complets de logique propositionnelle](../../examples/logic_agents/propositional_logic_example.py)
- [Tests d'intégration pour les opérations logiques (JPype/Tweety)](../tests/integration/jpype_tweety/test_logic_operations.py)
- [Tutoriel interactif sur l'API logique (Notebook)](../../examples/notebooks/api_logic_tutorial.ipynb) (Note: se concentre sur une API Web, mais peut illustrer des concepts)
