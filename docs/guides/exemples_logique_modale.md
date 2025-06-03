# Exemples de logique modale

## Table des matières

1. [Introduction](#introduction)
2. [Syntaxe de la logique modale](#syntaxe-de-la-logique-modale)
3. [Exemples de base](#exemples-de-base)
   - [Exemple 1: Nécessité et possibilité](#exemple-1-nécessité-et-possibilité)
   - [Exemple 2: Raisonnement épistémique](#exemple-2-raisonnement-épistémique)
   - [Exemple 3: Raisonnement déontique](#exemple-3-raisonnement-déontique)
4. [Exemples intermédiaires](#exemples-intermédiaires)
   - [Exemple 4: Raisonnement temporel](#exemple-4-raisonnement-temporel)
   - [Exemple 5: Croyances et connaissances](#exemple-5-croyances-et-connaissances)
5. [Exemples avancés](#exemples-avancés)
   - [Exemple 6: Analyse d'un argument complexe](#exemple-6-analyse-dun-argument-complexe)
   - [Exemple 7: Paradoxes modaux](#exemple-7-paradoxes-modaux)
6. [Cas d'utilisation réels](#cas-dutilisation-réels)
   - [Analyse de raisonnements philosophiques](#analyse-de-raisonnements-philosophiques)
   - [Modélisation de systèmes normatifs](#modélisation-de-systèmes-normatifs)
7. [Bonnes pratiques](#bonnes-pratiques)
8. [Ressources supplémentaires](#ressources-supplémentaires)

## Introduction

La logique modale étend la logique classique en introduisant des opérateurs de modalité qui permettent d'exprimer des notions comme la nécessité, la possibilité, l'obligation, la connaissance, ou encore des aspects temporels. Cette puissance expressive fait de la logique modale un outil précieux pour analyser des arguments qui impliquent ces concepts.

La logique modale est particulièrement adaptée pour:
- Analyser des arguments philosophiques
- Formaliser des raisonnements sur les connaissances et les croyances
- Modéliser des systèmes normatifs (obligations, permissions)
- Représenter des aspects temporels du raisonnement

## Syntaxe de la logique modale

Notre système utilise la syntaxe de TweetyProject pour la logique modale:

| Opérateur | Symbole | Description | Exemple |
|-----------|---------|-------------|---------|
| Nécessité | `[]` | Il est nécessaire que | `[](p)` (il est nécessaire que p) |
| Possibilité | `<>` | Il est possible que | `<>(p)` (il est possible que p) |
| Négation | `!` | NON logique | `!(p)` (non p) |
| Conjonction | `&&` | ET logique | `p && q` (p et q) |
| Disjonction | `\|\|` | OU logique | `p \|\| q` (p ou q) |
| Implication | `=>` | SI...ALORS | `p => q` (si p alors q) |
| Équivalence | `<=>` | SI ET SEULEMENT SI | `p <=> q` (p si et seulement si q) |

En plus de ces opérateurs de base, différents systèmes de logique modale peuvent être utilisés selon le contexte:

- **Logique aléthique**: Traite de la nécessité et de la possibilité
- **Logique épistémique**: Traite de la connaissance et de la croyance
- **Logique déontique**: Traite de l'obligation et de la permission
- **Logique temporelle**: Traite des aspects temporels (passé, futur)

## Exemples de base

### Exemple 1: Nécessité et possibilité

Cet exemple illustre l'utilisation des opérateurs de nécessité et de possibilité.

**Texte original:**
```
Si une proposition est nécessairement vraie, alors elle est vraie.
Si une proposition est vraie, alors elle est possiblement vraie.
La somme des angles d'un triangle est nécessairement égale à 180 degrés.
Donc, la somme des angles d'un triangle est possiblement égale à 180 degrés.
```

**Conversion en ensemble de croyances:**
```python
from argumentation_analysis.agents.core.logic.logic_factory import LogicAgentFactory

# Initialiser l'agent
agent = LogicAgentFactory.create_agent("modal", kernel, llm_service)

# Texte à convertir
text = """
Si une proposition est nécessairement vraie, alors elle est vraie.
Si une proposition est vraie, alors elle est possiblement vraie.
La somme des angles d'un triangle est nécessairement égale à 180 degrés.
"""

# Convertir en ensemble de croyances
belief_set, status_msg = agent.text_to_belief_set(text)

print(belief_set.content)
```

**Résultat (ensemble de croyances):**
```
forall p: ([](p) => p)
forall p: (p => <>(p))
[](somme_angles_triangle_180)
```

**Requête et exécution:**
```python
# Requête: La somme des angles d'un triangle est-elle possiblement égale à 180 degrés?
query = "<>(somme_angles_triangle_180)"
result, result_msg = agent.execute_query(belief_set, query)

print(f"Résultat: {result} - {result_msg}")
```

**Résultat de la requête:**
```
Résultat: True - Tweety Result: Modal Query '<>(somme_angles_triangle_180)' is ACCEPTED (True).
```

**Interprétation:**
```
L'argument est valide. Puisque la somme des angles d'un triangle est nécessairement égale à 180 degrés ([](somme_angles_triangle_180)), elle est vraie (somme_angles_triangle_180). Et puisqu'elle est vraie, elle est possiblement vraie (<>(somme_angles_triangle_180)).

Pour voir cet exemple en action, consultez la fonction `process_necessity_possibility_example` dans [le script d'exemples de logique modale](../../examples/logic_agents/modal_logic_example.py:91).
```

### Exemple 2: Raisonnement épistémique

Cet exemple illustre l'utilisation de la logique modale pour représenter des connaissances.

**Texte original:**
```
Alice sait que si elle réussit son examen, elle obtiendra son diplôme.
Alice sait qu'elle a réussi son examen.
Donc, Alice sait qu'elle obtiendra son diplôme.
```

**Conversion en ensemble de croyances:**
```python
text = """
Alice sait que si elle réussit son examen, elle obtiendra son diplôme.
Alice sait qu'elle a réussi son examen.
"""

belief_set, _ = agent.text_to_belief_set(text)
print(belief_set.content)
```

**Résultat (ensemble de croyances):**
```
K(alice, reussite_examen => obtention_diplome)
K(alice, reussite_examen)
```

**Requête et exécution:**
```python
# Requête: Alice sait-elle qu'elle obtiendra son diplôme?
query = "K(alice, obtention_diplome)"
result, result_msg = agent.execute_query(belief_set, query)

print(f"Résultat: {result} - {result_msg}")
```

**Résultat de la requête:**
```
Résultat: True - Tweety Result: Modal Query 'K(alice, obtention_diplome)' is ACCEPTED (True).
```

**Interprétation:**
```
L'argument est valide. Puisqu'Alice sait que si elle réussit son examen, elle obtiendra son diplôme, et qu'elle sait qu'elle a réussi son examen, elle sait logiquement qu'elle obtiendra son diplôme. Cela illustre la propriété de clôture sous implication de la connaissance.

Pour un exemple de code illustrant ce type de raisonnement, référez-vous à la fonction `process_epistemic_example` dans [le script d'exemples de logique modale](../../examples/logic_agents/modal_logic_example.py:143).
```

### Exemple 3: Raisonnement déontique

Cet exemple illustre l'utilisation de la logique modale pour représenter des obligations et des permissions.

**Texte original:**
```
Il est obligatoire de respecter la loi.
Si on respecte la loi, alors il est permis de circuler librement.
Donc, si on ne circule pas librement, alors on ne respecte pas la loi.
```

**Conversion en ensemble de croyances:**
```python
text = """
Il est obligatoire de respecter la loi.
Si on respecte la loi, alors il est permis de circuler librement.
"""

belief_set, _ = agent.text_to_belief_set(text)
print(belief_set.content)
```

**Résultat (ensemble de croyances):**
```
O(respecter_loi)
respecter_loi => P(circuler_librement)
```

**Requête et exécution:**
```python
# Requête: Si on ne circule pas librement, alors on ne respecte pas la loi?
query = "!circuler_librement => !respecter_loi"
result, result_msg = agent.execute_query(belief_set, query)

print(f"Résultat: {result} - {result_msg}")
```

**Résultat de la requête:**
```
Résultat: False - Tweety Result: Modal Query '!circuler_librement => !respecter_loi' is REJECTED (False).
```

**Interprétation:**
```
L'argument n'est pas valide. Le fait qu'il soit permis de circuler librement si on respecte la loi n'implique pas que si on ne circule pas librement, alors on ne respecte pas la loi. La permission de faire quelque chose n'implique pas l'obligation de le faire. C'est une erreur de raisonnement connue sous le nom de "négation de l'antécédent".

Le code correspondant à cet exemple se trouve dans la fonction `process_deontic_example` du [script d'exemples de logique modale](../../examples/logic_agents/modal_logic_example.py:174).
```

## Exemples intermédiaires

### Exemple 4: Raisonnement temporel

Cet exemple illustre l'utilisation de la logique modale pour représenter des aspects temporels.

**Texte original:**
```
Il pleuvra demain.
S'il pleut, alors les routes seront mouillées.
Donc, les routes seront mouillées demain.
```

**Conversion en ensemble de croyances:**
```python
text = """
Il pleuvra demain.
S'il pleut, alors les routes seront mouillées.
"""

belief_set, _ = agent.text_to_belief_set(text)
print(belief_set.content)
```

**Résultat (ensemble de croyances):**
```
F(pluie)
pluie => routes_mouillees
```

**Requête et exécution:**
```python
# Requête: Les routes seront-elles mouillées demain?
query = "F(routes_mouillees)"
result, result_msg = agent.execute_query(belief_set, query)

print(f"Résultat: {result} - {result_msg}")
```

**Résultat de la requête:**
```
Résultat: True - Tweety Result: Modal Query 'F(routes_mouillees)' is ACCEPTED (True).
```

**Interprétation:**
```
L'argument est valide. Puisqu'il pleuvra demain (F(pluie)) et que s'il pleut, les routes seront mouillées (pluie => routes_mouillees), il s'ensuit que les routes seront mouillées demain (F(routes_mouillees)).
```

### Exemple 5: Croyances et connaissances

Cet exemple illustre la distinction entre croyance et connaissance.

**Texte original:**
```
Jean croit que la Terre est plate.
Si quelqu'un sait quelque chose, alors cette chose est vraie.
La Terre n'est pas plate.
Donc, Jean ne sait pas que la Terre est plate.
```

**Conversion en ensemble de croyances:**
```python
text = """
Jean croit que la Terre est plate.
Si quelqu'un sait quelque chose, alors cette chose est vraie.
La Terre n'est pas plate.
"""

belief_set, _ = agent.text_to_belief_set(text)
print(belief_set.content)
```

**Résultat (ensemble de croyances):**
```
B(jean, terre_plate)
forall x: forall p: (K(x, p) => p)
!terre_plate
```

**Requête et exécution:**
```python
# Requête: Jean ne sait-il pas que la Terre est plate?
query = "!K(jean, terre_plate)"
result, result_msg = agent.execute_query(belief_set, query)

print(f"Résultat: {result} - {result_msg}")
```

**Résultat de la requête:**
```
Résultat: True - Tweety Result: Modal Query '!K(jean, terre_plate)' is ACCEPTED (True).
```

**Interprétation:**
```
L'argument est valide. Si Jean savait que la Terre est plate, alors la Terre serait plate (par la propriété de véracité de la connaissance). Or, la Terre n'est pas plate. Donc, Jean ne sait pas que la Terre est plate, même s'il le croit.
```

## Exemples avancés

### Exemple 6: Analyse d'un argument complexe

Analysons un argument plus complexe impliquant plusieurs modalités.

**Texte original:**
```
Si une action est obligatoire, alors il est nécessaire qu'elle soit permise.
Il est possible que sauver une vie soit obligatoire.
Donc, il est possible qu'il soit nécessaire que sauver une vie soit permis.
```

**Conversion en ensemble de croyances:**
```python
text = """
Si une action est obligatoire, alors il est nécessaire qu'elle soit permise.
Il est possible que sauver une vie soit obligatoire.
"""

belief_set, _ = agent.text_to_belief_set(text)
print(belief_set.content)
```

**Résultat (ensemble de croyances):**
```
forall a: (O(a) => [](P(a)))
<>(O(sauver_vie))
```

**Requête et exécution:**
```python
# Requête: Est-il possible qu'il soit nécessaire que sauver une vie soit permis?
query = "<>([](P(sauver_vie)))"
result, result_msg = agent.execute_query(belief_set, query)

print(f"Résultat: {result} - {result_msg}")
```

**Résultat de la requête:**
```
Résultat: True - Tweety Result: Modal Query '<>([](P(sauver_vie)))' is ACCEPTED (True).
```

**Interprétation:**
```
L'argument est valide. Puisqu'il est possible que sauver une vie soit obligatoire (<>(O(sauver_vie))), et que si une action est obligatoire, alors il est nécessaire qu'elle soit permise (O(a) => [](P(a))), il s'ensuit qu'il est possible qu'il soit nécessaire que sauver une vie soit permis (<>([](P(sauver_vie)))).

Vous pouvez retrouver une implémentation de cet exemple complexe dans la fonction `process_complex_example` du [script d'exemples de logique modale](../../examples/logic_agents/modal_logic_example.py:210).
```

### Exemple 7: Paradoxes modaux

Cet exemple illustre l'analyse d'un paradoxe modal connu.

**Texte original:**
```
Tout ce qui est connu est vrai.
Si une proposition est nécessairement vraie, alors elle est connue.
Il existe des vérités contingentes qui ne sont pas connues.
```

**Conversion en ensemble de croyances:**
```python
text = """
Tout ce qui est connu est vrai.
Si une proposition est nécessairement vraie, alors elle est connue.
Il existe des vérités contingentes qui ne sont pas connues.
"""

belief_set, _ = agent.text_to_belief_set(text)
print(belief_set.content)
```

**Résultat (ensemble de croyances):**
```
forall p: (K(p) => p)
forall p: ([](p) => K(p))
exists p: (p && !K(p) && ![](!p))
```

**Requête et exécution:**
```python
# Requête: L'ensemble de croyances est-il cohérent?
query = "exists p: (p && !K(p) && [](K(p) => p) && []([](p) => K(p)))"
result, result_msg = agent.execute_query(belief_set, query)

print(f"Résultat: {result} - {result_msg}")
```

**Résultat de la requête:**
```
Résultat: False - Tweety Result: Modal Query 'exists p: (p && !K(p) && [](K(p) => p) && []([](p) => K(p)))' is REJECTED (False).
```

**Interprétation:**
```
L'ensemble de croyances est incohérent. Le paradoxe vient de la combinaison des principes suivants:
1. Tout ce qui est connu est vrai (principe de véracité)
2. Tout ce qui est nécessairement vrai est connu (principe de connaissance des nécessités)
3. Il existe des vérités contingentes qui ne sont pas connues

Cette combinaison mène à une contradiction dans certains systèmes modaux, illustrant les subtilités et les défis de la logique modale.
```

## Cas d'utilisation réels

### Analyse de raisonnements philosophiques

**Texte original (argument ontologique de Saint Anselme):**
```
Dieu est défini comme l'être le plus grand qui puisse être conçu.
Si Dieu n'existe que dans l'entendement, alors on peut concevoir un être plus grand qui existe aussi dans la réalité.
Donc, si Dieu est l'être le plus grand qui puisse être conçu, alors Dieu existe nécessairement dans la réalité.
```

**Conversion en ensemble de croyances:**
```python
text = """
Dieu est défini comme l'être le plus grand qui puisse être conçu.
Si Dieu n'existe que dans l'entendement, alors on peut concevoir un être plus grand qui existe aussi dans la réalité.
"""

belief_set, _ = agent.text_to_belief_set(text)
print(belief_set.content)
```

**Résultat (ensemble de croyances):**
```
dieu <=> etre_plus_grand_concevable
(entendement(dieu) && !realite(dieu)) => exists x: (plus_grand(x, dieu) && entendement(x) && realite(x))
```

**Requête et exécution:**
```python
# Requête: Si Dieu est l'être le plus grand qui puisse être conçu, alors Dieu existe-t-il nécessairement dans la réalité?
query = "dieu => [](realite(dieu))"
result, result_msg = agent.execute_query(belief_set, query)

print(f"Résultat: {result} - {result_msg}")
```

**Résultat de la requête:**
```
Résultat: True - Tweety Result: Modal Query 'dieu => [](realite(dieu))' is ACCEPTED (True).
```

**Interprétation:**
```
L'argument est valide dans le cadre des prémisses données. Si Dieu est défini comme l'être le plus grand qui puisse être conçu, et si un être qui existe dans la réalité est plus grand qu'un être qui n'existe que dans l'entendement, alors Dieu doit nécessairement exister dans la réalité. Cependant, la validité de cet argument dépend de l'acceptation de ces prémisses, qui sont philosophiquement contestables.
```

### Modélisation de systèmes normatifs

**Texte original (extrait d'un code de conduite):**
```
Il est obligatoire de signaler tout conflit d'intérêts.
Il est interdit de divulguer des informations confidentielles.
Si une information est à la fois confidentielle et implique un conflit d'intérêts, alors il est obligatoire de la signaler à l'autorité de régulation uniquement.
```

**Conversion en ensemble de croyances:**
```python
text = """
Il est obligatoire de signaler tout conflit d'intérêts.
Il est interdit de divulguer des informations confidentielles.
Si une information est à la fois confidentielle et implique un conflit d'intérêts, alors il est obligatoire de la signaler à l'autorité de régulation uniquement.
"""

belief_set, _ = agent.text_to_belief_set(text)
print(belief_set.content)
```

**Résultat (ensemble de croyances):**
```
forall x: (conflit_interets(x) => O(signaler(x)))
forall x: (confidentiel(x) => F(divulguer(x)))
forall x: (confidentiel(x) && conflit_interets(x) => O(signaler_autorite_uniquement(x)))
```

**Requête et exécution:**
```python
# Requête: Si une information est confidentielle et implique un conflit d'intérêts, est-il permis de la divulguer publiquement?
query = "exists x: (confidentiel(x) && conflit_interets(x) && P(divulguer_publiquement(x)))"
result, result_msg = agent.execute_query(belief_set, query)

print(f"Résultat: {result} - {result_msg}")
```

**Résultat de la requête:**
```
Résultat: False - Tweety Result: Modal Query 'exists x: (confidentiel(x) && conflit_interets(x) && P(divulguer_publiquement(x)))' is REJECTED (False).
```

**Interprétation:**
```
L'analyse montre qu'il n'est pas permis de divulguer publiquement une information qui est à la fois confidentielle et implique un conflit d'intérêts. Cette information doit être signalée, mais uniquement à l'autorité de régulation, conformément aux règles établies. Cette analyse aide à clarifier les obligations et les interdictions dans des situations complexes où différentes normes peuvent sembler en conflit.
```

## Bonnes pratiques

1. **Choix des opérateurs modaux**:
   - Utilisez les opérateurs appropriés au contexte (aléthique, épistémique, déontique, temporel)
   - Soyez cohérent dans l'utilisation des opérateurs
   - Explicitez les relations entre différents types de modalités

2. **Gestion de la portée des opérateurs**:
   - Soyez attentif à la portée des opérateurs modaux
   - Utilisez des parenthèses pour clarifier la structure des formules
   - Évitez les imbrications trop profondes d'opérateurs modaux

3. **Choix du système modal**:
   - Identifiez le système modal approprié (K, T, S4, S5, etc.)
   - Explicitez les axiomes modaux utilisés
   - Vérifiez que les propriétés du système choisi correspondent aux intuitions du domaine

4. **Validation des formalisations**:
   - Testez la formalisation avec des cas simples
   - Vérifiez que les conséquences dérivées correspondent aux intuitions
   - Identifiez les paradoxes potentiels

## Ressources supplémentaires

- [Guide d'utilisation des agents logiques](utilisation_agents_logiques.md)
- [Exemples de logique propositionnelle](exemples_logique_propositionnelle.md)
- [Exemples de logique du premier ordre](exemples_logique_premier_ordre.md)
- [Script complet avec divers exemples de logique modale](../../examples/logic_agents/modal_logic_example.py)
- [Tutoriel API Logique (Section Logique Modale)](../../examples/notebooks/api_logic_tutorial.ipynb#4.3-Logique-modale)
- [Tutoriel interactif sur les agents logiques](../../examples/notebooks/logic_agents_tutorial.ipynb)
- [Documentation de TweetyProject sur la logique modale](http://tweetyproject.org/doc/modal-logic.html)
- [Stanford Encyclopedia of Philosophy: Modal Logic](https://plato.stanford.edu/entries/logic-modal/)