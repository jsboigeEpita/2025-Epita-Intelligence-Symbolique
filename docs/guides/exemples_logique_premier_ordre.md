# Exemples de logique du premier ordre

## Table des matières

1. [Introduction](#introduction)
2. [Syntaxe de la logique du premier ordre](#syntaxe-de-la-logique-du-premier-ordre)
3. [Exemples de base](#exemples-de-base)
   - [Exemple 1: Syllogisme catégorique](#exemple-1-syllogisme-catégorique)
   - [Exemple 2: Raisonnement avec quantificateurs mixtes](#exemple-2-raisonnement-avec-quantificateurs-mixtes)
   - [Exemple 3: Relations et propriétés](#exemple-3-relations-et-propriétés)
4. [Exemples intermédiaires](#exemples-intermédiaires)
   - [Exemple 4: Raisonnement avec égalité](#exemple-4-raisonnement-avec-égalité)
   - [Exemple 5: Composition de relations](#exemple-5-composition-de-relations)
5. [Exemples avancés](#exemples-avancés)
   - [Exemple 6: Analyse d'un argument complexe](#exemple-6-analyse-dun-argument-complexe)
   - [Exemple 7: Formalisation de définitions](#exemple-7-formalisation-de-définitions)
6. [Cas d'utilisation réels](#cas-dutilisation-réels)
   - [Analyse de textes scientifiques](#analyse-de-textes-scientifiques)
   - [Raisonnement juridique](#raisonnement-juridique)
7. [Bonnes pratiques](#bonnes-pratiques)
8. [Ressources supplémentaires](#ressources-supplémentaires)

## Introduction

La logique du premier ordre (ou logique des prédicats) étend la logique propositionnelle en permettant de représenter des objets, des propriétés et des relations, ainsi que des quantificateurs. Elle offre un pouvoir expressif bien plus grand que la logique propositionnelle, ce qui la rend particulièrement adaptée pour formaliser des raisonnements complexes.

La logique du premier ordre est particulièrement utile pour:
- Analyser des arguments qui impliquent des généralisations ("tous", "certains")
- Formaliser des relations entre objets
- Représenter des définitions et des concepts complexes
- Modéliser des domaines de connaissances structurés

## Syntaxe de la logique du premier ordre

Notre système utilise la syntaxe de TweetyProject pour la logique du premier ordre:

| Élément | Syntaxe | Description | Exemple |
|---------|---------|-------------|---------|
| Constantes | Lettres minuscules | Objets spécifiques | `a`, `b`, `socrate` |
| Variables | Lettres minuscules | Objets génériques | `x`, `y`, `z` |
| Prédicats | Lettres majuscules | Propriétés ou relations | `Humain(x)`, `PlusGrand(x,y)` |
| Fonctions | Lettres minuscules | Mappages vers des objets | `pere(x)`, `somme(x,y)` |
| Quantificateur universel | `forall x:` | Pour tout x | `forall x: (Humain(x) => Mortel(x))` |
| Quantificateur existentiel | `exists x:` | Il existe un x | `exists x: (Humain(x) && Immortel(x))` |
| Négation | `!` | NON logique | `!Mortel(x)` |
| Conjonction | `&&` | ET logique | `Humain(x) && Mortel(x)` |
| Disjonction | `\|\|` | OU logique | `Homme(x) \|\| Femme(x)` |
| Implication | `=>` | SI...ALORS | `Humain(x) => Mortel(x)` |
| Équivalence | `<=>` | SI ET SEULEMENT SI | `Carre(x) <=> Rectangle(x) && CotesEgaux(x)` |
| Égalité | `=` | Identité | `pere(pere(x)) = grand_pere(x)` |

Pour voir ces concepts en action et des exemples d'utilisation de l'agent de logique du premier ordre avec la syntaxe décrite, consultez le script suivant :
- Code source : [`examples/logic_agents/first_order_logic_example.py`](../../examples/logic_agents/first_order_logic_example.py)

## Exemples de base

Les exemples qui suivent (Syllogisme, Quantificateurs mixtes, Relations) sont illustrés par des implémentations concrètes dans le script [`first_order_logic_example.py`](../../examples/logic_agents/first_order_logic_example.py). Vous y trouverez notamment les fonctions `process_syllogism_example`, `process_quantifiers_example`, et `process_relations_example` qui correspondent aux Exemples 1, 2 et 3 ci-dessous.

### Exemple 1: Syllogisme catégorique

Le syllogisme catégorique est un type de raisonnement déductif qui utilise des propositions catégoriques.

**Texte original:**
```
Tous les hommes sont mortels.
Socrate est un homme.
Donc, Socrate est mortel.
```

**Conversion en ensemble de croyances:**
```python
from argumentation_analysis.agents.core.logic.logic_factory import LogicAgentFactory

# Initialiser l'agent
agent = LogicAgentFactory.create_agent("first_order", kernel, llm_service)

# Texte à convertir
text = """
Tous les hommes sont mortels.
Socrate est un homme.
"""

# Convertir en ensemble de croyances
belief_set, status_msg = agent.text_to_belief_set(text)

print(belief_set.content)
```

**Résultat (ensemble de croyances):**
```
forall x: (Homme(x) => Mortel(x));
Homme(socrate);
```

**Requête et exécution:**
```python
# Requête: Socrate est-il mortel?
query = "Mortel(socrate)"
result, result_msg = agent.execute_query(belief_set, query)

print(f"Résultat: {result} - {result_msg}")
```

**Résultat de la requête:**
```
Résultat: True - Tweety Result: FOL Query 'Mortel(socrate)' is ACCEPTED (True).
```

**Interprétation:**
```
L'argument est valide. Puisque tous les hommes sont mortels (forall x: (Homme(x) => Mortel(x))) et que Socrate est un homme (Homme(socrate)), nous pouvons logiquement conclure que Socrate est mortel (Mortel(socrate)).
```

### Exemple 2: Raisonnement avec quantificateurs mixtes

Cet exemple illustre l'utilisation combinée des quantificateurs universel et existentiel.

**Texte original:**
```
Tous les étudiants suivent au moins un cours.
Aucun cours n'est facile.
Donc, tous les étudiants suivent au moins un cours qui n'est pas facile.
```

**Conversion en ensemble de croyances:**
```python
text = """
Tous les étudiants suivent au moins un cours.
Aucun cours n'est facile.
"""

belief_set, _ = agent.text_to_belief_set(text)
print(belief_set.content)
```

**Résultat (ensemble de croyances):**
```
forall x: (Etudiant(x) => exists y: (Cours(y) && Suit(x,y)));
forall z: (Cours(z) => !Facile(z));
```

**Requête et exécution:**
```python
# Requête: Tous les étudiants suivent-ils au moins un cours qui n'est pas facile?
query = "forall x: (Etudiant(x) => exists y: (Cours(y) && Suit(x,y) && !Facile(y)))"
result, result_msg = agent.execute_query(belief_set, query)

print(f"Résultat: {result} - {result_msg}")
```

**Résultat de la requête:**
```
Résultat: True - Tweety Result: FOL Query 'forall x: (Etudiant(x) => exists y: (Cours(y) && Suit(x,y) && !Facile(y)))' is ACCEPTED (True).
```

**Interprétation:**
```
L'argument est valide. Puisque tous les étudiants suivent au moins un cours et qu'aucun cours n'est facile, il s'ensuit logiquement que tous les étudiants suivent au moins un cours qui n'est pas facile.
```

### Exemple 3: Relations et propriétés

Cet exemple montre comment représenter et raisonner avec des relations entre objets.

**Texte original:**
```
Tous les parents aiment leurs enfants.
Marie est la mère de Jean.
Donc, Marie aime Jean.
```

**Conversion en ensemble de croyances:**
```python
text = """
Tous les parents aiment leurs enfants.
Marie est la mère de Jean.
"""

belief_set, _ = agent.text_to_belief_set(text)
print(belief_set.content)
```

**Résultat (ensemble de croyances):**
```
forall x: forall y: (Parent(x,y) => Aime(x,y));
Mere(marie,jean);
forall x: forall y: (Mere(x,y) => Parent(x,y));
```

**Requête et exécution:**
```python
# Requête: Marie aime-t-elle Jean?
query = "Aime(marie,jean)"
result, result_msg = agent.execute_query(belief_set, query)

print(f"Résultat: {result} - {result_msg}")
```

**Résultat de la requête:**
```
Résultat: True - Tweety Result: FOL Query 'Aime(marie,jean)' is ACCEPTED (True).
```

**Interprétation:**
```
L'argument est valide. Puisque tous les parents aiment leurs enfants, que Marie est la mère de Jean, et que toute mère est un parent, nous pouvons logiquement conclure que Marie aime Jean.
```

## Exemples intermédiaires

### Exemple 4: Raisonnement avec égalité

Cet exemple illustre l'utilisation de l'égalité en logique du premier ordre.

**Texte original:**
```
Le directeur de l'entreprise est Pierre.
Le président du conseil d'administration est aussi Pierre.
Tous les employés respectent le directeur de l'entreprise.
Jean est un employé.
Donc, Jean respecte le président du conseil d'administration.
```

**Conversion en ensemble de croyances:**
```python
text = """
Le directeur de l'entreprise est Pierre.
Le président du conseil d'administration est aussi Pierre.
Tous les employés respectent le directeur de l'entreprise.
Jean est un employé.
"""

belief_set, _ = agent.text_to_belief_set(text)
print(belief_set.content)
```

**Résultat (ensemble de croyances):**
```
directeur = pierre;
president = pierre;
forall x: (Employe(x) => Respecte(x,directeur));
Employe(jean);
```

**Requête et exécution:**
```python
# Requête: Jean respecte-t-il le président du conseil d'administration?
query = "Respecte(jean,president)"
result, result_msg = agent.execute_query(belief_set, query)

print(f"Résultat: {result} - {result_msg}")
```

**Résultat de la requête:**
```
Résultat: True - Tweety Result: FOL Query 'Respecte(jean,president)' is ACCEPTED (True).
```

**Interprétation:**
```
L'argument est valide. Puisque le directeur et le président sont la même personne (Pierre), que tous les employés respectent le directeur, et que Jean est un employé, nous pouvons logiquement conclure que Jean respecte le président.
```

### Exemple 5: Composition de relations

Cet exemple montre comment raisonner avec des compositions de relations.

**Texte original:**
```
Si une personne est l'ancêtre d'une autre, alors elle est soit son parent, soit l'ancêtre de son parent.
Alice est la mère de Bob.
Bob est le père de Charlie.
Donc, Alice est l'ancêtre de Charlie.
```

**Conversion en ensemble de croyances:**
```python
text = """
forall x: forall y: (Ancetre(x,y) <=> Parent(x,y) || exists z: (Parent(x,z) && Ancetre(z,y)))
Mere(alice,bob)
Pere(bob,charlie)
forall x: forall y: (Mere(x,y) => Parent(x,y))
forall x: forall y: (Pere(x,y) => Parent(x,y))
"""

belief_set, _ = agent.text_to_belief_set(text)
print(belief_set.content)
```

**Requête et exécution:**
```python
# Requête: Alice est-elle l'ancêtre de Charlie?
query = "Ancetre(alice,charlie)"
result, result_msg = agent.execute_query(belief_set, query)

print(f"Résultat: {result} - {result_msg}")
```

**Résultat de la requête:**
```
Résultat: True - Tweety Result: FOL Query 'Ancetre(alice,charlie)' is ACCEPTED (True).
```

**Interprétation:**
```
L'argument est valide. Alice est la mère de Bob, donc elle est son parent. Bob est le père de Charlie, donc il est son parent. Selon la définition d'ancêtre, Alice est l'ancêtre de Charlie car elle est l'ancêtre (en fait, le parent) de Bob, qui est lui-même le parent de Charlie.
```

## Exemples avancés

L'Exemple 6 ("Analyse d'un argument complexe") présenté ci-dessous est également implémenté dans la fonction `process_complex_example` du script [`first_order_logic_example.py`](../../examples/logic_agents/first_order_logic_example.py).

### Exemple 6: Analyse d'un argument complexe

Analysons un argument plus complexe avec plusieurs prémisses et des relations imbriquées.

**Texte original:**
```
Tous les mammifères sont des vertébrés.
Tous les chats sont des mammifères.
Tous les vertébrés ont un cœur.
Félix est un chat.
Donc, Félix a un cœur.
```

**Conversion en ensemble de croyances:**
```python
text = """
Tous les mammifères sont des vertébrés.
Tous les chats sont des mammifères.
Tous les vertébrés ont un cœur.
Félix est un chat.
"""

belief_set, _ = agent.text_to_belief_set(text)
print(belief_set.content)
```

**Résultat (ensemble de croyances):**
```
forall x: (Mammifere(x) => Vertebre(x));
forall x: (Chat(x) => Mammifere(x));
forall x: (Vertebre(x) => ACœur(x));
Chat(felix);
```

**Requête et exécution:**
```python
# Requête: Félix a-t-il un cœur?
query = "ACœur(felix)"
result, result_msg = agent.execute_query(belief_set, query)

print(f"Résultat: {result} - {result_msg}")
```

**Résultat de la requête:**
```
Résultat: True - Tweety Result: FOL Query 'ACœur(felix)' is ACCEPTED (True).
```

**Interprétation:**
```
L'argument est valide. Félix est un chat, donc un mammifère. Tous les mammifères sont des vertébrés, donc Félix est un vertébré. Tous les vertébrés ont un cœur, donc Félix a un cœur.
```

### Exemple 7: Formalisation de définitions

Cet exemple montre comment formaliser et utiliser des définitions complexes.

**Texte original:**
```
Un nombre premier est un entier naturel supérieur à 1 qui n'est divisible que par 1 et par lui-même.
2 est un entier naturel supérieur à 1.
2 n'est divisible que par 1 et par lui-même.
Donc, 2 est un nombre premier.
```

**Conversion en ensemble de croyances:**
```python
text = """
Un nombre premier est un entier naturel supérieur à 1 qui n'est divisible que par 1 et par lui-même.
2 est un entier naturel supérieur à 1.
2 n'est divisible que par 1 et par lui-même.
"""

belief_set, _ = agent.text_to_belief_set(text)
print(belief_set.content)
```

**Résultat (ensemble de croyances):**
```
forall x: (Premier(x) <=> EntierNaturel(x) && Superieur(x,1) && forall y: (Divise(y,x) => (y = 1 || y = x)));
EntierNaturel(2);
Superieur(2,1);
forall y: (Divise(y,2) => (y = 1 || y = 2));
```

**Requête et exécution:**
```python
# Requête: 2 est-il un nombre premier?
query = "Premier(2)"
result, result_msg = agent.execute_query(belief_set, query)

print(f"Résultat: {result} - {result_msg}")
```

**Résultat de la requête:**
```
Résultat: True - Tweety Result: FOL Query 'Premier(2)' is ACCEPTED (True).
```

**Interprétation:**
```
L'argument est valide. Selon la définition formalisée d'un nombre premier, 2 satisfait toutes les conditions: c'est un entier naturel supérieur à 1 qui n'est divisible que par 1 et par lui-même. Par conséquent, 2 est un nombre premier.
```

## Cas d'utilisation réels

### Analyse de textes scientifiques

**Texte original (extrait d'un article scientifique):**
```
Toutes les cellules eucaryotes possèdent un noyau.
Toutes les cellules qui possèdent un noyau contiennent de l'ADN.
Les cellules bactériennes ne possèdent pas de noyau.
Donc, les cellules bactériennes ne sont pas des cellules eucaryotes.
```

**Conversion en ensemble de croyances:**
```python
text = """
Toutes les cellules eucaryotes possèdent un noyau.
Toutes les cellules qui possèdent un noyau contiennent de l'ADN.
Les cellules bactériennes ne possèdent pas de noyau.
"""

belief_set, _ = agent.text_to_belief_set(text)
print(belief_set.content)
```

**Résultat (ensemble de croyances):**
```
forall x: (Eucaryote(x) => PossedeNoyau(x));
forall x: (PossedeNoyau(x) => ContientADN(x));
forall x: (Bacterienne(x) => !PossedeNoyau(x));
```

**Requête et exécution:**
```python
# Requête: Les cellules bactériennes ne sont-elles pas des cellules eucaryotes?
query = "forall x: (Bacterienne(x) => !Eucaryote(x))"
result, result_msg = agent.execute_query(belief_set, query)

print(f"Résultat: {result} - {result_msg}")
```

**Résultat de la requête:**
```
Résultat: True - Tweety Result: FOL Query 'forall x: (Bacterienne(x) => !Eucaryote(x))' is ACCEPTED (True).
```

**Interprétation:**
```
L'argument est valide. Puisque toutes les cellules eucaryotes possèdent un noyau et que les cellules bactériennes ne possèdent pas de noyau, il s'ensuit logiquement que les cellules bactériennes ne sont pas des cellules eucaryotes. Cette analyse confirme la validité du raisonnement scientifique présenté.
```

### Raisonnement juridique

**Texte original (extrait d'un raisonnement juridique):**
```
Toute personne qui commet un crime avec préméditation est coupable de meurtre au premier degré.
Toute personne coupable de meurtre au premier degré encourt une peine d'emprisonnement à perpétuité.
L'accusé a commis un crime avec préméditation.
Donc, l'accusé encourt une peine d'emprisonnement à perpétuité.
```

**Conversion en ensemble de croyances:**
```python
text = """
Toute personne qui commet un crime avec préméditation est coupable de meurtre au premier degré.
Toute personne coupable de meurtre au premier degré encourt une peine d'emprisonnement à perpétuité.
L'accusé a commis un crime avec préméditation.
"""

belief_set, _ = agent.text_to_belief_set(text)
print(belief_set.content)
```

**Résultat (ensemble de croyances):**
```
forall x: (Personne(x) && CommetCrimePremeditation(x) => CoupableMeurtrePremierDegre(x));
forall x: (Personne(x) && CoupableMeurtrePremierDegre(x) => EncourtPerpetuite(x));
Personne(accuse);
CommetCrimePremeditation(accuse);
```

**Requête et exécution:**
```python
# Requête: L'accusé encourt-il une peine d'emprisonnement à perpétuité?
query = "EncourtPerpetuite(accuse)"
result, result_msg = agent.execute_query(belief_set, query)

print(f"Résultat: {result} - {result_msg}")
```

**Résultat de la requête:**
```
Résultat: True - Tweety Result: FOL Query 'EncourtPerpetuite(accuse)' is ACCEPTED (True).
```

**Interprétation:**
```
L'argument est valide. Puisque l'accusé est une personne qui a commis un crime avec préméditation, il est coupable de meurtre au premier degré. Et puisque toute personne coupable de meurtre au premier degré encourt une peine d'emprisonnement à perpétuité, l'accusé encourt une telle peine. Cette analyse confirme la validité du raisonnement juridique présenté.
```

## Bonnes pratiques

1. **Choix des prédicats et des constantes**:
   - Utilisez des noms significatifs pour les prédicats et les constantes
   - Maintenez une convention de nommage cohérente (par exemple, prédicats en majuscules)
   - Évitez les prédicats trop génériques ou ambigus

2. **Gestion des quantificateurs**:
   - Soyez attentif à l'ordre des quantificateurs, qui peut changer le sens
   - Limitez la portée des quantificateurs pour améliorer la lisibilité
   - Utilisez des variables différentes pour des quantificateurs différents

3. **Formalisation des définitions**:
   - Utilisez des équivalences (`<=>`) pour les définitions
   - Décomposez les définitions complexes en parties plus simples
   - Assurez-vous que les définitions sont complètes et précises

4. **Optimisation des requêtes**:
   - Commencez par des requêtes simples avant de passer à des requêtes complexes
   - Décomposez les requêtes complexes en sous-requêtes
   - Vérifiez la cohérence de l'ensemble de croyances avant d'exécuter des requêtes

## Ressources supplémentaires

- [Guide d'utilisation des agents logiques](utilisation_agents_logiques.md)
- [Exemples de logique propositionnelle](exemples_logique_propositionnelle.md)
- [Exemples de logique modale](exemples_logique_modale.md)
- [Tutoriel interactif sur les agents logiques](../../examples/notebooks/logic_agents_tutorial.ipynb)
- [Documentation de TweetyProject sur la logique du premier ordre](http://tweetyproject.org/doc/first-order-logic.html)
- Script d'exemples complets pour l'agent de Logique du Premier Ordre : [`examples/logic_agents/first_order_logic_example.py`](../../examples/logic_agents/first_order_logic_example.py)
- Tutoriel interactif via API (incluant une section LPO) : [`examples/notebooks/api_logic_tutorial.ipynb`](../../examples/notebooks/api_logic_tutorial.ipynb) (voir section 4.2)