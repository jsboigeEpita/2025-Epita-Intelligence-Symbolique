# Exemples TweetyProject pour les Projets d'IA Symbolique

Ce document sert de guide pour connecter les concepts théoriques d'IA symbolique aux exemples pratiques du notebook `Tweety.ipynb`. Il est conçu pour aider les étudiants à comprendre comment les différentes fonctionnalités de la bibliothèque TweetyProject peuvent être utilisées dans leurs projets.

## Table des matières

- [Introduction](#introduction)
- [Logiques formelles et raisonnement](#logiques-formelles-et-raisonnement)
  - [Logique propositionnelle (PL)](#logique-propositionnelle-pl)
  - [Logique du premier ordre (FOL)](#logique-du-premier-ordre-fol)
  - [Logique de description (DL)](#logique-de-description-dl)
  - [Logique modale (ML)](#logique-modale-ml)
  - [Autres logiques (QBF, CL)](#autres-logiques-qbf-cl)
- [Frameworks d'argumentation](#frameworks-dargumentation)
  - [Argumentation abstraite de Dung](#argumentation-abstraite-de-dung)
  - [ASPIC+](#aspic)
  - [Defeasible Logic Programming (DeLP)](#defeasible-logic-programming-delp)
  - [Assumption-Based Argumentation (ABA)](#assumption-based-argumentation-aba)
- [Frameworks d'argumentation avancés](#frameworks-dargumentation-avancés)
- [Révision de croyances et analyse d'incohérence](#révision-de-croyances-et-analyse-dincohérence)
- [Recommandations pratiques](#recommandations-pratiques)

## Introduction

Le notebook `Tweety.ipynb` est une ressource précieuse qui illustre l'utilisation de la bibliothèque TweetyProject pour l'IA symbolique, en particulier pour la représentation des connaissances et l'argumentation computationnelle. Ce guide vous aidera à naviguer dans le notebook et à comprendre comment les exemples peuvent être appliqués à vos projets.

TweetyProject est une bibliothèque Java pour l'IA symbolique qui offre des implémentations de nombreux formalismes logiques et argumentatifs. Le notebook utilise JPype pour interfacer Python avec les classes Java de TweetyProject, permettant ainsi d'exploiter la puissance de cette bibliothèque dans un environnement Python.

> **Note**: Pour des exemples de code organisés par projet spécifique, consultez le document [Exemples TweetyProject par projet](./exemples_tweety_par_projet.md) qui présente des snippets de code directement applicables à chaque sujet de projet.
## Logiques formelles et raisonnement

Cette section présente les différentes logiques formelles implémentées dans TweetyProject et montre comment elles peuvent être utilisées pour le raisonnement automatique.

### Logique propositionnelle (PL)

**Concepts théoriques**: La logique propositionnelle est la forme la plus simple de logique formelle, manipulant des propositions qui peuvent être vraies ou fausses, combinées avec des opérateurs logiques (ET, OU, NON, IMPLIQUE).

**Exemples dans le notebook**:
- Création de formules propositionnelles
- Parsing de formules à partir de chaînes de caractères
- Vérification de satisfiabilité avec SAT4J
- Conversion en formes normales (CNF, DNF)

**Application aux projets**:
- **Projet 1.1.1 (Intégration des logiques propositionnelles avancées)**: Le notebook montre comment créer des formules propositionnelles, les parser, et utiliser des solveurs SAT. Ces exemples peuvent servir de base pour implémenter un agent PL plus sophistiqué.
- **Projet 1.4.4 (Mesures d'incohérence et résolution)**: Les exemples de satisfiabilité peuvent être étendus pour implémenter des mesures d'incohérence.

**Code exemple**:
```python
from org.tweetyproject.logics.pl.syntax import Proposition, Conjunction, Negation, PlBeliefSet
from org.tweetyproject.logics.pl.parser import PlParser
from org.tweetyproject.logics.pl.sat import Sat4jSolver, SatSolver

# Définir le solveur SAT par défaut
SatSolver.setDefaultSolver(Sat4jSolver())

# Parser une formule propositionnelle
parser = PlParser()
formula = parser.parseFormula("a && (b || !c)")

# Créer une base de croyances
belief_set = PlBeliefSet()
belief_set.add(formula)

# Vérifier la satisfiabilité
is_satisfiable = SatSolver.getDefaultSolver().isSatisfiable(belief_set)
print(f"La base de croyances est satisfiable: {is_satisfiable}")
```
### Logique du premier ordre (FOL)

**Concepts théoriques**: La logique du premier ordre étend la logique propositionnelle avec des quantificateurs (∀, ∃) et des prédicats, permettant d'exprimer des relations plus complexes.

**Exemples dans le notebook**:
- Définition de signatures FOL (types, constantes, prédicats, fonctions)
- Création de formules FOL avec quantificateurs
- Parsing de formules FOL
- Utilisation de raisonneurs FOL

**Application aux projets**:
- **Projet 1.1.2 (Logique du premier ordre)**: Les exemples du notebook montrent comment définir une signature FOL, créer des formules quantifiées, et utiliser des raisonneurs FOL.
- **Projet 1.2.4 (Argumentation basée sur les hypothèses)**: La FOL peut servir de langage sous-jacent pour ABA.

**Code exemple**:
```python
from org.tweetyproject.logics.fol.syntax import FolSignature, FolFormula, Constant, Variable, Predicate
from org.tweetyproject.logics.fol.parser import FolParser

# Créer une signature FOL
sig = FolSignature()
human = Predicate("Human", 1)
mortal = Predicate("Mortal", 1)
sig.add(human)
sig.add(mortal)
sig.add(Constant("socrates"))

# Parser une formule FOL
parser = FolParser()
parser.setSignature(sig)
formula = parser.parseFormula("forall X: (Human(X) => Mortal(X))")
assertion = parser.parseFormula("Human(socrates)")
```

### Logique de description (DL)

**Concepts théoriques**: Les logiques de description sont utilisées pour représenter des connaissances structurées sous forme de concepts, rôles et individus, particulièrement adaptées aux ontologies.

**Exemples dans le notebook**:
- Définition de concepts atomiques et de rôles
- Création d'axiomes terminologiques (TBox) et assertionnels (ABox)
- Construction de concepts complexes (union, intersection, complément)
- Raisonnement avec NaiveDlReasoner

**Application aux projets**:
- **Projet 1.1.4 (Logique de description)**: Les exemples montrent comment définir des concepts, des rôles, et des axiomes DL.
- **Projet 1.3.3 (Ontologie de l'argumentation)**: La DL est particulièrement adaptée à la création d'ontologies.

**Code exemple**:
```python
from org.tweetyproject.logics.dl.syntax import AtomicConcept, AtomicRole, Individual
from org.tweetyproject.logics.dl.syntax import EquivalenceAxiom, ConceptAssertion, RoleAssertion
from org.tweetyproject.logics.dl.syntax import DlBeliefSet, Complement
from org.tweetyproject.logics.dl.reasoner import NaiveDlReasoner

# Définir des concepts et rôles
human = AtomicConcept("Human")
male = AtomicConcept("Male")
female = AtomicConcept("Female")
fatherOf = AtomicRole("fatherOf")

# Créer des individus
bob = Individual("Bob")
alice = Individual("Alice")

# Définir des axiomes
femaleHuman = EquivalenceAxiom(female, human)
maleHuman = EquivalenceAxiom(male, human)
femaleNotMale = EquivalenceAxiom(female, Complement(male))

# Créer une base de croyances DL
dbs = DlBeliefSet()
dbs.add(femaleHuman)
dbs.add(maleHuman)
dbs.add(femaleNotMale)
```
### Logique modale (ML)

**Concepts théoriques**: Les logiques modales permettent de raisonner sur des notions comme la nécessité, la possibilité, les croyances ou les connaissances.

**Exemples dans le notebook**:
- Définition de formules modales avec opérateurs de nécessité ([]) et possibilité (<>)
- Parsing de formules modales
- Raisonnement avec SimpleMlReasoner et SPASSMlReasoner

**Application aux projets**:
- **Projet 1.1.3 (Logique modale)**: Les exemples montrent comment créer et manipuler des formules modales.
- **Projet 1.4.3 (Raisonnement non-monotone)**: La logique modale peut être utilisée pour certaines formes de raisonnement non-monotone.

**Code exemple**:
```python
from org.tweetyproject.logics.ml.syntax import MlBeliefSet
from org.tweetyproject.logics.ml.parser import MlParser
from org.tweetyproject.logics.fol.syntax import FolSignature, Predicate
from org.tweetyproject.logics.ml.reasoner import SimpleMlReasoner

# Créer une signature
sig_ml = FolSignature()
p = Predicate("p", 0); q = Predicate("q", 0); r = Predicate("r", 0)
sig_ml.add(p); sig_ml.add(q); sig_ml.add(r)

# Parser des formules modales
parser_ml = MlParser()
parser_ml.setSignature(sig_ml)
kb_ml = MlBeliefSet()
formulas_ml = ["!(<>(p))", "p || r", "!r || [](q && r)", "[](r && <>(p || q))", "!p && !q"]
for f_str in formulas_ml:
    kb_ml.add(parser_ml.parseFormula(f_str))

# Raisonnement
reasoner_ml = SimpleMlReasoner()
query = parser_ml.parseFormula("[](!p)")
result = reasoner_ml.query(kb_ml, query)
```

### Autres logiques (QBF, CL)

**Concepts théoriques**: TweetyProject implémente d'autres logiques comme les Formules Booléennes Quantifiées (QBF) et la Logique Conditionnelle (CL).

**Exemples dans le notebook**:
- QBF: Extension de la logique propositionnelle avec des quantificateurs sur les propositions
- CL: Traitement des conditionnels de la forme (B|A) signifiant "Si A est vrai, alors B est typiquement vrai"

**Application aux projets**:
- **Projet 1.1.5 (Formules booléennes quantifiées)**: Les exemples QBF montrent comment créer et manipuler des formules quantifiées.
- **Projet 1.1.6 (Logique conditionnelle)**: Les exemples CL illustrent la création de bases conditionnelles et le calcul de fonctions de classement.

**Code exemple (CL)**:
```python
from org.tweetyproject.logics.cl.syntax import ClBeliefSet, Conditional
from org.tweetyproject.logics.pl.syntax import Proposition, Negation
from org.tweetyproject.logics.cl.reasoner import SimpleCReasoner

# Création de la base CL
f = Proposition("f"); b = Proposition("b"); p = Proposition("p")
c1 = Conditional(f, b)  # (f|b) - Si b alors typiquement f
c2 = Conditional(b, p)  # (b|p) - Si p alors typiquement b
c3 = Conditional(Negation(f), p)  # (!f|p) - Si p alors typiquement !f
bs_cl = ClBeliefSet()
bs_cl.add(c1); bs_cl.add(c2); bs_cl.add(c3)

# Raisonnement
cl_reasoner = SimpleCReasoner()
kappa_model = cl_reasoner.getModel(bs_cl)  # Fonction de classement (ranking)
```
## Frameworks d'argumentation

Cette section présente les différents frameworks d'argumentation implémentés dans TweetyProject, allant des frameworks abstraits aux frameworks structurés.

### Argumentation abstraite de Dung

**Concepts théoriques**: Les frameworks d'argumentation abstraite de Dung (AF) représentent les arguments comme des entités atomiques et les attaques comme des relations binaires entre arguments.

**Exemples dans le notebook**:
- Création de frameworks d'argumentation (DungTheory)
- Définition d'arguments et d'attaques
- Calcul d'extensions selon différentes sémantiques (admissible, complète, préférée, stable, fondée)
- Traitement des cycles (sémantique CF2)
- Génération de frameworks aléatoires
- Apprentissage de frameworks à partir de labellisations

**Application aux projets**:
- **Projet 1.2.1 (Argumentation abstraite de Dung)**: Les exemples montrent comment construire et manipuler des frameworks de Dung.
- **Projet 1.2.7 (Argumentation dialogique)**: Les frameworks de Dung peuvent servir de base pour modéliser des dialogues argumentatifs.

**Code exemple**:
```python
from org.tweetyproject.arg.dung.syntax import DungTheory, Argument, Attack
from org.tweetyproject.arg.dung.reasoner import SimpleGroundedReasoner, SimplePreferredReasoner, SimpleStableReasoner

# Créer un framework d'argumentation
af = DungTheory()
a = Argument("a"); b = Argument("b"); c = Argument("c")
af.add(a); af.add(b); af.add(c)
af.add(Attack(a, b)); af.add(Attack(b, c))

# Calculer les extensions selon différentes sémantiques
grounded_reasoner = SimpleGroundedReasoner()
grounded_ext = grounded_reasoner.getModel(af)
print(f"Extension fondée: {grounded_ext}")

preferred_reasoner = SimplePreferredReasoner()
preferred_exts = preferred_reasoner.getModels(af)
print(f"Extensions préférées: {preferred_exts}")

stable_reasoner = SimpleStableReasoner()
stable_exts = stable_reasoner.getModels(af)
print(f"Extensions stables: {stable_exts}")
```

### ASPIC+

**Concepts théoriques**: ASPIC+ est un framework d'argumentation structurée qui combine la logique formelle avec des mécanismes de gestion des conflits et des préférences.

**Exemples dans le notebook**:
- Création d'une théorie ASPIC+ (AspicArgumentationTheory)
- Définition de règles strictes et défaisables
- Conversion en framework de Dung pour le raisonnement

**Application aux projets**:
- **Projet 1.2.6 (Argumentation structurée)**: Les exemples montrent comment construire des arguments structurés avec ASPIC+.
- **Projet 1.5.2 (Vérification formelle d'arguments)**: ASPIC+ peut être utilisé pour formaliser et vérifier des arguments complexes.

**Code exemple**:
```python
from org.tweetyproject.arg.aspic.syntax import AspicArgumentationTheory, DefeasibleInferenceRule
from org.tweetyproject.arg.aspic.ruleformulagenerator import PlFormulaGenerator
from org.tweetyproject.logics.pl.syntax import Proposition, Negation
from org.tweetyproject.arg.dung.reasoner import SimpleGroundedReasoner

# Créer une théorie ASPIC+
pl_formula_generator = PlFormulaGenerator()
aspic_theory = AspicArgumentationTheory(pl_formula_generator)
aspic_theory.setRuleFormulaGenerator(pl_formula_generator)

# Définir des propositions
a = Proposition("a"); b = Proposition("b"); c = Proposition("c"); d = Proposition("d")

# Créer des règles défaisables
r1 = DefeasibleInferenceRule()
r1.setConclusion(a)
r1.addPremise(b); r1.addPremise(c)
aspic_theory.addRule(r1)

r2 = DefeasibleInferenceRule()
r2.setConclusion(d)
r2.addPremise(b)
aspic_theory.addRule(r2)

# Ajouter des axiomes
aspic_theory.addAxiom(b)
aspic_theory.addAxiom(c)

# Convertir en framework de Dung et raisonner
dung_theory = aspic_theory.asDungTheory()
grounded_reasoner = SimpleGroundedReasoner()
grounded_ext = grounded_reasoner.getModel(dung_theory)
```
### Defeasible Logic Programming (DeLP)

**Concepts théoriques**: DeLP combine la programmation logique avec le raisonnement défaisable, utilisant des règles strictes et des règles défaisables pour construire des arguments.

**Exemples dans le notebook**:
- Chargement d'un programme DeLP depuis un fichier
- Définition de règles strictes et défaisables
- Évaluation de requêtes DeLP

**Application aux projets**:
- **Projet 1.2.6 (Argumentation structurée)**: DeLP est une alternative à ASPIC+ pour l'argumentation structurée.
- **Projet 1.4.3 (Raisonnement non-monotone)**: DeLP est un formalisme de raisonnement non-monotone.

**Code exemple**:
```python
from org.tweetyproject.arg.delp.parser import DelpParser
from org.tweetyproject.arg.delp.reasoner import DelpReasoner
from org.tweetyproject.arg.delp.semantics import GeneralizedSpecificity

# Charger un programme DeLP
parser = DelpParser()
delp_program = parser.parseBeliefBaseFromFile("birds.txt")

# Créer un raisonneur DeLP
reasoner = DelpReasoner(GeneralizedSpecificity())

# Évaluer des requêtes
query = parser.parseFormula("Flies(tweety)")
result = reasoner.query(delp_program, query)
print(f"Résultat de la requête: {result}")
```

### Assumption-Based Argumentation (ABA)

**Concepts théoriques**: L'argumentation basée sur les hypothèses (ABA) représente les arguments comme des déductions à partir d'hypothèses, avec des attaques définies en termes de contraires des hypothèses.

**Exemples dans le notebook**:
- Création d'un framework ABA
- Définition de règles, d'hypothèses et de contraires
- Conversion en framework de Dung pour le raisonnement

**Application aux projets**:
- **Projet 1.2.4 (Argumentation basée sur les hypothèses)**: Les exemples montrent comment construire et manipuler des frameworks ABA.
- **Projet 1.5.2 (Vérification formelle d'arguments)**: ABA peut être utilisé pour formaliser et vérifier des arguments complexes.

**Code exemple**:
```python
from org.tweetyproject.arg.aba.syntax import AbaRule, AbaTheory, InferenceRule
from org.tweetyproject.logics.pl.syntax import Proposition, Negation
from org.tweetyproject.arg.aba.reasoner import AbaReasoner

# Créer une théorie ABA
theory = AbaTheory()

# Définir des propositions
a = Proposition("a"); b = Proposition("b"); c = Proposition("c")
d = Proposition("d"); e = Proposition("e")

# Ajouter des règles
rule1 = InferenceRule()
rule1.setConclusion(a)
rule1.addPremise(b)
theory.addRule(rule1)

rule2 = InferenceRule()
rule2.setConclusion(c)
rule2.addPremise(d)
theory.addRule(rule2)

# Définir des hypothèses et leurs contraires
theory.addAssumption(b, Negation(b))
theory.addAssumption(d, e)

# Raisonnement
reasoner = AbaReasoner()
dung_theory = reasoner.getDungTheory(theory)
```
## Frameworks d'argumentation avancés

Cette section présente des frameworks d'argumentation plus avancés implémentés dans TweetyProject, qui étendent le framework de base de Dung.

### Abstract Dialectical Frameworks (ADF)

**Concepts théoriques**: Les ADF généralisent les frameworks de Dung en remplaçant la relation d'attaque simple par des conditions d'acceptation arbitraires pour chaque argument.

**Exemples dans le notebook**:
- Création d'un ADF
- Définition de conditions d'acceptation
- Calcul de modèles selon différentes sémantiques

**Application aux projets**:
- **Projet 1.2.2 (Frameworks dialectiques abstraits)**: Les exemples montrent comment construire et manipuler des ADF.
- **Projet 1.5.1 (Modélisation de débats complexes)**: Les ADF sont particulièrement adaptés pour modéliser des débats avec des relations complexes entre arguments.

**Code exemple**:
```python
from org.tweetyproject.arg.adf.syntax import Argument, Adf, acc
from org.tweetyproject.arg.adf.reasoner import AbstractDialecticalFrameworkReasoner

# Créer un ADF
a = Argument("a"); b = Argument("b"); c = Argument("c")
adf = Adf()
adf.add(a); adf.add(b); adf.add(c)

# Définir des conditions d'acceptation
adf.setAcceptanceCondition(a, acc.atom(a))  # a est accepté si a est accepté
adf.setAcceptanceCondition(b, acc.not_(acc.atom(a)))  # b est accepté si a n'est pas accepté
adf.setAcceptanceCondition(c, acc.and_(acc.atom(b), acc.not_(acc.atom(a))))  # c est accepté si b est accepté et a n'est pas accepté

# Raisonnement
reasoner = AbstractDialecticalFrameworkReasoner()
models = reasoner.getModels(adf)
```

### Frameworks bipolaires

**Concepts théoriques**: Les frameworks d'argumentation bipolaires étendent les frameworks de Dung en ajoutant une relation de support en plus de la relation d'attaque.

**Exemples dans le notebook**:
- Création d'un framework bipolaire (BipolarArgumentationFramework)
- Définition d'arguments, d'attaques et de supports
- Conversion en framework de Dung standard

**Application aux projets**:
- **Projet 1.2.3 (Argumentation bipolaire)**: Les exemples montrent comment construire et manipuler des frameworks bipolaires.
- **Projet 1.5.3 (Analyse de discours argumentatifs)**: Les frameworks bipolaires sont utiles pour analyser des discours où certains arguments se soutiennent mutuellement.

**Code exemple**:
```python
from org.tweetyproject.arg.bipolar.syntax import BipolarArgumentationFramework, Attack, Support
from org.tweetyproject.arg.dung.syntax import Argument

# Créer un framework bipolaire
baf = BipolarArgumentationFramework()
a = Argument("a"); b = Argument("b"); c = Argument("c"); d = Argument("d")
baf.add(a); baf.add(b); baf.add(c); baf.add(d)

# Ajouter des attaques et des supports
baf.addAttack(a, b)  # a attaque b
baf.addSupport(c, a)  # c supporte a
baf.addAttack(b, d)  # b attaque d
baf.addSupport(c, d)  # c supporte d

# Conversion en framework de Dung
dung_theory = baf.asDungTheory()
```

### Frameworks pondérés (WAF)

**Concepts théoriques**: Les frameworks d'argumentation pondérés associent des poids aux attaques, permettant de modéliser des attaques de forces différentes.

**Exemples dans le notebook**:
- Création d'un framework pondéré (WeightedArgumentationFramework)
- Définition d'arguments et d'attaques pondérées
- Calcul d'extensions selon différentes sémantiques

**Application aux projets**:
- **Projet 1.2.5 (Argumentation pondérée)**: Les exemples montrent comment construire et manipuler des frameworks pondérés.
- **Projet 1.5.4 (Analyse de la force des arguments)**: Les WAF sont utiles pour analyser la force relative des arguments dans un débat.

**Code exemple**:
```python
from org.tweetyproject.arg.weighted.syntax import WeightedArgumentationFramework
from org.tweetyproject.arg.dung.syntax import Argument
from org.tweetyproject.arg.weighted.reasoner import WeightedRankingReasoner

# Créer un framework pondéré
waf = WeightedArgumentationFramework()
a = Argument("a"); b = Argument("b"); c = Argument("c")
waf.add(a); waf.add(b); waf.add(c)

# Ajouter des attaques pondérées
waf.addAttack(a, b, 0.7)  # a attaque b avec un poids de 0.7
waf.addAttack(b, c, 0.5)  # b attaque c avec un poids de 0.5
waf.addAttack(c, a, 0.3)  # c attaque a avec un poids de 0.3

# Raisonnement
reasoner = WeightedRankingReasoner()
ranking = reasoner.getModel(waf)
```
### Frameworks sociaux (SAF)

**Concepts théoriques**: Les frameworks d'argumentation sociaux intègrent des aspects sociaux comme les valeurs, les préférences ou les audiences dans l'évaluation des arguments.

**Exemples dans le notebook**:
- Création d'un framework social (SocialAbstractArgumentationFramework)
- Définition d'arguments, d'attaques et de valeurs sociales
- Calcul d'extensions selon différentes audiences

**Application aux projets**:
- **Projet 1.2.5 (Argumentation pondérée)**: Les SAF peuvent être utilisés comme alternative aux WAF pour modéliser des préférences.
- **Projet 1.5.5 (Analyse de l'argumentation dans les réseaux sociaux)**: Les SAF sont particulièrement adaptés pour analyser les arguments dans un contexte social.

**Code exemple**:
```python
from org.tweetyproject.arg.social.syntax import SocialAbstractArgumentationFramework
from org.tweetyproject.arg.dung.syntax import Argument
from org.tweetyproject.arg.social.semantics import SimpleValueBasedReasoner

# Créer un framework social
saf = SocialAbstractArgumentationFramework()
a = Argument("a"); b = Argument("b"); c = Argument("c")
saf.add(a); saf.add(b); saf.add(c)

# Ajouter des attaques
saf.addAttack(a, b)
saf.addAttack(b, c)
saf.addAttack(c, a)

# Associer des valeurs aux arguments
saf.setValue(a, "économie")
saf.setValue(b, "environnement")
saf.setValue(c, "social")

# Définir un ordre de préférence sur les valeurs
pref_order = {"environnement": 3, "social": 2, "économie": 1}  # environnement > social > économie

# Raisonnement
reasoner = SimpleValueBasedReasoner(pref_order)
extensions = reasoner.getModels(saf)
```

### Set Argumentation Frameworks (SetAF)

**Concepts théoriques**: Les SetAF généralisent les frameworks de Dung en permettant à des ensembles d'arguments d'attaquer d'autres arguments, plutôt que de se limiter à des attaques binaires.

**Exemples dans le notebook**:
- Création d'un SetAF
- Définition d'arguments et d'attaques d'ensembles
- Calcul d'extensions selon différentes sémantiques

**Application aux projets**:
- **Projet 1.2.8 (Frameworks d'argumentation étendus)**: Les SetAF sont un exemple de framework étendu.
- **Projet 1.5.1 (Modélisation de débats complexes)**: Les SetAF permettent de modéliser des situations où plusieurs arguments combinés attaquent un autre argument.

**Code exemple**:
```python
from org.tweetyproject.arg.setaf.syntax import SetAf, SetAttack
from org.tweetyproject.arg.dung.syntax import Argument
from org.tweetyproject.arg.setaf.reasoner import SimpleSetAfReasoner

# Créer un SetAF
setaf = SetAf()
a = Argument("a"); b = Argument("b"); c = Argument("c"); d = Argument("d")
setaf.add(a); setaf.add(b); setaf.add(c); setaf.add(d)

# Ajouter des attaques d'ensembles
attackers1 = HashSet()
attackers1.add(a); attackers1.add(b)
setaf.addAttack(attackers1, c)  # {a,b} attaque c

attackers2 = HashSet()
attackers2.add(c)
setaf.addAttack(attackers2, d)  # {c} attaque d

# Raisonnement
reasoner = SimpleSetAfReasoner()
extensions = reasoner.getModels(setaf)
```

### Frameworks étendus (attaques sur attaques)

**Concepts théoriques**: Les frameworks étendus permettent des attaques sur des attaques, généralisant ainsi la notion d'attaque pour inclure des méta-arguments.

**Exemples dans le notebook**:
- Création d'un framework étendu (ExtendedArgumentationFramework)
- Définition d'arguments, d'attaques et d'attaques sur attaques
- Conversion en framework de Dung standard

**Application aux projets**:
- **Projet 1.2.8 (Frameworks d'argumentation étendus)**: Les exemples montrent comment construire et manipuler des frameworks étendus.
- **Projet 1.5.6 (Méta-argumentation)**: Les frameworks étendus sont particulièrement adaptés pour la méta-argumentation.

**Code exemple**:
```python
from org.tweetyproject.arg.eaf.syntax import ExtendedArgumentationFramework, EafAttack
from org.tweetyproject.arg.dung.syntax import Argument, Attack

# Créer un framework étendu
eaf = ExtendedArgumentationFramework()
a = Argument("a"); b = Argument("b"); c = Argument("c"); d = Argument("d")
eaf.add(a); eaf.add(b); eaf.add(c); eaf.add(d)

# Ajouter des attaques
## Révision de croyances et analyse d'incohérence

Cette section présente les mécanismes de raisonnement avancés pour mettre à jour des croyances face à de nouvelles informations et pour gérer les contradictions.

### Révision de croyances multi-agents (CrMas)

**Concepts théoriques**: La révision de croyances multi-agents s'intéresse à l'intégration de nouvelles informations dans une base de connaissances où chaque information est associée à un agent et où un ordre de crédibilité peut exister entre ces agents.

**Exemples dans le notebook**:
- Création d'une base de croyances multi-agents (CrMasBeliefSet)
- Définition d'un ordre de crédibilité entre agents
- Application de différents opérateurs de révision (CrMasRevisionWrapper, CrMasSimpleRevisionOperator, CrMasArgumentativeRevisionOperator)

**Application aux projets**:
- **Projet 1.4.5 (Révision de croyances multi-agents)**: Les exemples montrent comment modéliser les croyances de différents agents et simuler leur évolution.
- **Projet 1.4.2 (Révision de croyances)**: Les opérateurs de révision illustrés peuvent être adaptés pour des scénarios mono-agent.

**Code exemple**:
```python
from org.tweetyproject.beliefdynamics import InformationObject
from org.tweetyproject.beliefdynamics.mas import CrMasBeliefSet, CrMasRevisionWrapper
from org.tweetyproject.agents import DummyAgent
from org.tweetyproject.comparator import Order
from org.tweetyproject.logics.pl.parser import PlParser

# Créer des agents avec un ordre de crédibilité
agents_list = ArrayList()
agent1 = DummyAgent("A1"); agent2 = DummyAgent("A2"); agent3 = DummyAgent("A3")
agents_list.add(agent1); agents_list.add(agent2); agents_list.add(agent3)
credOrder = Order(agents_list)
credOrder.setOrderedBefore(agent1, agent2)
credOrder.setOrderedBefore(agent2, agent3)

# Créer une base de croyances multi-agents
parser = PlParser()
base = CrMasBeliefSet(credOrder, PlSignature())

# Ajouter des informations
info1 = InformationObject(parser.parseFormula("!c"), agent2)
info2 = InformationObject(parser.parseFormula("b"), agent3)
base.add(info1); base.add(info2)

# Nouvelles informations
news = HashSet()
news.add(InformationObject(parser.parseFormula("a"), agent3))

# Révision
revision_op = CrMasRevisionWrapper(levi_operator)
result = revision_op.revise(base, news)
```

### Mesures d'incohérence

**Concepts théoriques**: Les mesures d'incohérence permettent de quantifier le degré d'incohérence d'une base de connaissances propositionnelle.

**Exemples dans le notebook**:
- Utilisation de différentes mesures d'incohérence:
  - ContensionInconsistencyMeasure
  - MaInconsistencyMeasure / McscInconsistencyMeasure
  - FuzzyInconsistencyMeasure
  - DSum/DMax/DHitInconsistencyMeasure

**Application aux projets**:
- **Projet 1.4.4 (Mesures d'incohérence et résolution)**: Les exemples montrent comment quantifier l'incohérence d'une base de connaissances.
- **Projet 1.5.2 (Vérification formelle d'arguments)**: Les mesures d'incohérence peuvent être utilisées pour vérifier la cohérence des arguments.

**Code exemple**:
```python
from org.tweetyproject.logics.pl.syntax import PlBeliefSet, PlParser
from org.tweetyproject.logics.pl.analysis import ContensionInconsistencyMeasure, FuzzyInconsistencyMeasure
from org.tweetyproject.math.func.fuzzy import ProductNorm

# Créer une base de croyances incohérente
parser = PlParser()
kb = PlBeliefSet()
formulas = ["a", "!a && b", "!b", "c || a", "!c || a", "!c || d", "!d", "d", "c"]
for f_str in formulas:
    kb.add(parser.parseFormula(f_str))

# Mesurer l'incohérence avec différentes mesures
cont_measure = ContensionInconsistencyMeasure()
cont_value = cont_measure.inconsistencyMeasure(kb)
print(f"Valeur Contension: {cont_value}")

fuzzy_measure = FuzzyInconsistencyMeasure(ProductNorm(), FuzzyInconsistencyMeasure.SUMFUZZY_MEASURE)
fuzzy_value = fuzzy_measure.inconsistencyMeasure(kb)
print(f"Valeur Fuzzy: {fuzzy_value}")
```

### Énumération de MUS

**Concepts théoriques**: Un Sous-ensemble Minimal Inconsistant (MUS) d'une base de connaissances est un sous-ensemble inconsistant tel que tout sous-ensemble propre est consistant. L'énumération de MUS permet d'identifier les sources d'incohérence.

**Exemples dans le notebook**:
- Utilisation de NaiveMusEnumerator pour énumérer les MUS
- Interface avec l'outil externe MARCO pour une énumération plus efficace

**Application aux projets**:
- **Projet 1.4.4 (Mesures d'incohérence et résolution)**: L'énumération de MUS est une technique clé pour la résolution d'incohérences.
- **Projet 1.5.2 (Vérification formelle d'arguments)**: L'identification des MUS peut aider à diagnostiquer les problèmes dans les arguments formels.

**Code exemple**:
```python
from org.tweetyproject.logics.pl.syntax import PlBeliefSet, PlParser
from org.tweetyproject.logics.pl.sat import Sat4jSolver, SatSolver
from org.tweetyproject.logics.commons.analysis import NaiveMusEnumerator

# Configurer le solveur SAT
SatSolver.setDefaultSolver(Sat4jSolver())

# Créer une base de croyances incohérente
parser = PlParser()
kb = PlBeliefSet()
formulas = ["a", "!a", "!a && !b", "b", "c", "!c", "!a || !c"]
for f_str in formulas:
    kb.add(parser.parseFormula(f_str))

# Énumérer les MUS
mus_enum = NaiveMusEnumerator(SatSolver.getDefaultSolver())
all_mus = mus_enum.minimalInconsistentSubsets(kb)
print(f"Nombre de MUS: {len(all_mus)}")
for mus in all_mus:
    print(f"MUS: {mus}")
```

### MaxSAT

**Concepts théoriques**: MaxSAT est une généralisation du problème SAT qui cherche à satisfaire un maximum de clauses pondérées, tout en respectant des contraintes dures.

**Exemples dans le notebook**:
- Définition de clauses dures et molles
- Utilisation de OpenWboSolver pour résoudre des problèmes MaxSAT

**Application aux projets**:
- **Projet 1.4.4 (Mesures d'incohérence et résolution)**: MaxSAT peut être utilisé pour résoudre des incohérences en maximisant le nombre de formules satisfaites.
- **Projet 1.1.1 (Intégration des logiques propositionnelles avancées)**: MaxSAT est une extension avancée de SAT qui peut être intégrée dans un agent PL sophistiqué.

**Code exemple**:
```python
from org.tweetyproject.logics.pl.syntax import PlBeliefSet, PlParser
from org.tweetyproject.logics.pl.sat import MaxSatSolver, OpenWboSolver
from java.util import HashMap

# Clauses dures (doivent être satisfaites)
parser = PlParser()
hard_clauses = PlBeliefSet()
hard_formulas = ["!a && b", "b || c", "c || d", "f || (c && g)"]
for f_str in hard_formulas:
    hard_clauses.add(parser.parseFormula(f_str))

## Sémantiques avancées et analyse

Cette section présente des approches avancées pour l'analyse des frameworks d'argumentation.

### Sémantiques basées sur le classement (Ranking)

**Concepts théoriques**: Les sémantiques basées sur le classement attribuent des scores ou des rangs aux arguments plutôt que de simplement les accepter ou les rejeter.

**Exemples dans le notebook**:
- Utilisation de différentes sémantiques de classement:
  - CategoricalRankingSemantic
  - SimpleRankingSemantic
  - BurdenBasedRankingSemantic

**Application aux projets**:
- **Projet 1.2.9 (Sémantiques de classement)**: Les exemples montrent comment implémenter et utiliser des sémantiques de classement.
- **Projet 1.5.4 (Analyse de la force des arguments)**: Les sémantiques de classement sont particulièrement adaptées pour évaluer la force relative des arguments.

**Code exemple**:
```python
from org.tweetyproject.arg.dung.syntax import DungTheory, Argument, Attack
from org.tweetyproject.arg.dung.semantics.ranking import CategoricalRankingSemantic, SimpleRankingSemantic

# Créer un framework d'argumentation
af = DungTheory()
a = Argument("a"); b = Argument("b"); c = Argument("c"); d = Argument("d")
af.add(a); af.add(b); af.add(c); af.add(d)
af.add(Attack(a, b)); af.add(Attack(b, c)); af.add(Attack(c, d)); af.add(Attack(d, a))

# Calculer un classement avec différentes sémantiques
cat_ranking = CategoricalRankingSemantic().getRanking(af)
simple_ranking = SimpleRankingSemantic().getRanking(af)

# Comparer deux arguments
comparison = cat_ranking.compare(a, b)
if comparison < 0:
    print("a est mieux classé que b")
elif comparison > 0:
    print("b est mieux classé que a")
else:
    print("a et b sont classés de manière équivalente")
```

### Argumentation probabiliste

**Concepts théoriques**: L'argumentation probabiliste intègre des incertitudes dans les frameworks d'argumentation en associant des probabilités aux arguments ou aux attaques.

**Exemples dans le notebook**:
- Création de frameworks d'argumentation probabilistes
- Calcul de probabilités d'acceptation d'arguments
- Analyse de sensibilité

**Application aux projets**:
- **Projet 1.2.10 (Argumentation probabiliste)**: Les exemples montrent comment construire et manipuler des frameworks probabilistes.
- **Projet 1.5.7 (Analyse d'incertitude dans l'argumentation)**: L'argumentation probabiliste est particulièrement adaptée pour modéliser et analyser l'incertitude.

**Code exemple**:
```python
from org.tweetyproject.arg.prob.syntax import ProbabilisticArgumentationFramework
from org.tweetyproject.arg.dung.syntax import Argument, Attack
from org.tweetyproject.math.probability import Probability

# Créer un framework d'argumentation probabiliste
paf = ProbabilisticArgumentationFramework()
a = Argument("a"); b = Argument("b"); c = Argument("c")
paf.add(a); paf.add(b); paf.add(c)
paf.add(Attack(a, b)); paf.add(Attack(b, c))

# Associer des probabilités aux arguments
paf.setProbability(a, Probability(0.7))  # a existe avec une probabilité de 0.7
paf.setProbability(b, Probability(0.8))  # b existe avec une probabilité de 0.8
paf.setProbability(c, Probability(0.9))  # c existe avec une probabilité de 0.9

# Calculer la probabilité d'acceptation d'un argument
prob_c = paf.getProbabilityOfAcceptance(c)
print(f"Probabilité d'acceptation de c: {prob_c}")
```

## Recommandations pratiques

Cette section fournit des conseils pratiques pour utiliser TweetyProject dans vos projets.

### Configuration de l'environnement

Pour utiliser TweetyProject avec Python via JPype, suivez ces étapes:

1. **Installation de JPype**:
   ```bash
   pip install JPype1
   ```

2. **Téléchargement de TweetyProject**:
   - Téléchargez la dernière version de TweetyProject depuis [le site officiel](http://tweetyproject.org/download/)
   - Extrayez les fichiers JAR dans un dossier accessible

3. **Configuration de JPype**:
   ```python
   import jpype
   import jpype.imports
   from jpype.types import *

   # Démarrer la JVM avec le chemin vers les JAR de TweetyProject
   if not jpype.isJVMStarted():
       jpype.startJVM(classpath=['chemin/vers/tweety-full.jar'])
   ```

4. **Importation des classes Java**:
   ```python
   from org.tweetyproject.logics.pl.syntax import Proposition, PlBeliefSet
   from org.tweetyproject.arg.dung.syntax import DungTheory
   # etc.
   ```

### Bonnes pratiques d'utilisation

1. **Gestion des exceptions Java**:
   - Utilisez des blocs try/except pour capturer les exceptions Java
   - Convertissez les exceptions Java en exceptions Python pour une meilleure intégration

   ```python
   try:
       # Code utilisant TweetyProject
       result = reasoner.query(kb, formula)
   except jpype.JException as e:
       print(f"Erreur Java: {e}")
       # Gérer l'exception ou la propager
   ```

2. **Conversion entre types Java et Python**:
   - Utilisez les méthodes de conversion de JPype pour passer des données entre Python et Java
   - Pour les collections, utilisez les classes Java (ArrayList, HashSet) ou convertissez-les explicitement

   ```python
   # Conversion d'une liste Python en ArrayList Java
   java_list = jpype.JClass('java.util.ArrayList')()
   for item in python_list:
       java_list.add(item)
   ```

3. **Optimisation des performances**:
   - Réutilisez les objets lourds (parsers, raisonneurs) plutôt que de les recréer
   - Limitez les conversions entre Java et Python
   - Pour les grandes bases de connaissances, utilisez des méthodes incrémentales

### Résolution des problèmes courants

1. **Problèmes de mémoire**:
   - Augmentez la mémoire allouée à la JVM lors du démarrage:
     ```python
     jpype.startJVM(classpath=['chemin/vers/tweety-full.jar'], 
                    convertStrings=True, 
                    jvmargs=['-Xmx4g'])  # Alloue 4 Go de mémoire
     ```

2. **Problèmes de performance**:
   - Utilisez des solveurs externes plus efficaces lorsqu'ils sont disponibles
   - Simplifiez les bases de connaissances avant le raisonnement
   - Utilisez des techniques d'approximation pour les problèmes complexes

3. **Problèmes de compatibilité**:
   - Assurez-vous que la version de Java est compatible avec TweetyProject
   - Vérifiez que toutes les dépendances sont correctement installées
   - Consultez la documentation officielle pour les exigences spécifiques

4. **Débogage**:
   - Activez la journalisation Java pour obtenir plus d'informations:
     ```python
     jpype.startJVM(classpath=['chemin/vers/tweety-full.jar'], 
                    jvmargs=['-Djava.util.logging.config.file=logging.properties'])
     ```
   - Utilisez des assertions pour vérifier les préconditions et postconditions
   - Imprimez les objets Java pour inspecter leur état
# Clauses molles (avec poids/coût de violation)
soft_clauses = HashMap()
soft_clauses.put(parser.parseFormula("a || !b"), 25)  # violer coûte 25
soft_clauses.put(parser.parseFormula("!c"), 15)       # violer coûte 15

# Résolution MaxSAT
maxsat_solver = OpenWboSolver(OPENWBO_PATH)
witness = maxsat_solver.getWitness(hard_clauses, soft_clauses)
cost = maxsat_solver.costOf(witness, hard_clauses, soft_clauses)
```
attack1 = EafAttack(a, b)  # a attaque b
attack2 = EafAttack(b, c)  # b attaque c
attack3 = EafAttack(c, d)  # c attaque d
eaf.add(attack1); eaf.add(attack2); eaf.add(attack3)

# Ajouter une attaque sur une attaque
eaf.addAttack(d, attack1)  # d attaque l'attaque de a sur b

# Conversion en framework de Dung
dung_theory = eaf.asDungTheory()
```