# Exemples de code TweetyProject par projet

Ce document présente des snippets de code extraits du notebook `Tweety.ipynb` organisés par projet. Il est conçu pour aider les étudiants à trouver rapidement des exemples pertinents pour leurs projets spécifiques.

## Fondements théoriques et techniques

### 1.1 Logiques formelles et raisonnement

#### 1.1.1 Intégration des logiques propositionnelles avancées

**Exemple 1: Création et manipulation de formules propositionnelles**

```python
from org.tweetyproject.logics.pl.syntax import Proposition, Conjunction, Negation, PlBeliefSet
from org.tweetyproject.logics.pl.parser import PlParser

# Création manuelle de formules
a = Proposition("a")
b = Proposition("b")
c = Proposition("c")
formula = Conjunction(a, Negation(b))

# Parsing de formules à partir de chaînes
parser = PlParser()
formula2 = parser.parseFormula("a && (b || !c)")

# Création d'une base de croyances
belief_set = PlBeliefSet()
belief_set.add(formula)
belief_set.add(formula2)
```

**Exemple 2: Utilisation de solveurs SAT**

```python
from org.tweetyproject.logics.pl.sat import Sat4jSolver, SatSolver

# Définir le solveur SAT par défaut
SatSolver.setDefaultSolver(Sat4jSolver())

# Vérifier la satisfiabilité
is_satisfiable = SatSolver.getDefaultSolver().isSatisfiable(belief_set)
print(f"La base de croyances est satisfiable: {is_satisfiable}")

# Obtenir un modèle (si satisfiable)
if is_satisfiable:
    model = SatSolver.getDefaultSolver().getWitness(belief_set)
    print(f"Modèle: {model}")
```

**Exemple 3: Conversion en formes normales**

```python
from org.tweetyproject.logics.pl.syntax import PlFormula
from org.tweetyproject.logics.pl.util import CnfConverter, DnfConverter

# Conversion en CNF (Forme Normale Conjonctive)
cnf_converter = CnfConverter()
cnf_formula = cnf_converter.convert(formula2)
print(f"CNF: {cnf_formula}")

# Conversion en DNF (Forme Normale Disjonctive)
dnf_converter = DnfConverter()
dnf_formula = dnf_converter.convert(formula2)
print(f"DNF: {dnf_formula}")
```

#### 1.1.2 Logique du premier ordre (FOL)

**Exemple 1: Définition d'une signature FOL**

```python
from org.tweetyproject.logics.fol.syntax import FolSignature, Constant, Variable, Predicate, Function

# Créer une signature FOL
sig = FolSignature()

# Ajouter des prédicats (nom, arité)
human = Predicate("Human", 1)
mortal = Predicate("Mortal", 1)
father = Predicate("Father", 2)
sig.add(human)
sig.add(mortal)
sig.add(father)

# Ajouter des constantes
socrates = Constant("socrates")
plato = Constant("plato")
sig.add(socrates)
sig.add(plato)

# Ajouter des fonctions (nom, arité)
mother_of = Function("mother_of", 1)
sig.add(mother_of)
```

**Exemple 2: Création de formules FOL avec quantificateurs**

```python
from org.tweetyproject.logics.fol.syntax import FolFormula, ExistsQuantifiedFormula, ForallQuantifiedFormula
from org.tweetyproject.logics.fol.parser import FolParser

# Parser une formule FOL
parser = FolParser()
parser.setSignature(sig)
formula = parser.parseFormula("forall X: (Human(X) => Mortal(X))")
assertion = parser.parseFormula("Human(socrates)")

# Création manuelle de formules FOL
x = Variable("X")
y = Variable("Y")
human_x = human.apply(x)
mortal_x = mortal.apply(x)
implication = human_x.implies(mortal_x)
forall_formula = new ForallQuantifiedFormula(implication, x)
```

#### 1.1.3 Logique modale

**Exemple 1: Création de formules modales**

```python
from org.tweetyproject.logics.ml.syntax import MlBeliefSet, Necessity, Possibility
from org.tweetyproject.logics.ml.parser import MlParser
from org.tweetyproject.logics.fol.syntax import FolSignature, Predicate

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
```

**Exemple 2: Raisonnement avec des formules modales**

```python
from org.tweetyproject.logics.ml.reasoner import SimpleMlReasoner, SPASSMlReasoner

# Raisonnement avec SimpleMlReasoner
reasoner_ml = SimpleMlReasoner()
query = parser_ml.parseFormula("[](!p)")
result = reasoner_ml.query(kb_ml, query)
print(f"Résultat de la requête: {result}")

# Raisonnement avec SPASSMlReasoner (si SPASS est disponible)
# spass_reasoner = SPASSMlReasoner("/path/to/SPASS")
# result2 = spass_reasoner.query(kb_ml, query)
```

#### 1.1.4 Logique de description (DL)

**Exemple 1: Définition de concepts et rôles**

```python
from org.tweetyproject.logics.dl.syntax import AtomicConcept, AtomicRole, Individual
from org.tweetyproject.logics.dl.syntax import Conjunction, Disjunction, Complement, ExistentialRestriction
from org.tweetyproject.logics.dl.syntax import DlBeliefSet

# Définir des concepts atomiques
human = AtomicConcept("Human")
male = AtomicConcept("Male")
female = AtomicConcept("Female")

# Définir des rôles atomiques
hasChild = AtomicRole("hasChild")
hasParent = AtomicRole("hasParent")

# Définir des individus
bob = Individual("Bob")
alice = Individual("Alice")

# Construire des concepts complexes
parent = ExistentialRestriction(hasChild, AtomicConcept("top"))
father = Conjunction(male, parent)
mother = Conjunction(female, parent)
```

**Exemple 2: Création d'axiomes terminologiques (TBox) et assertionnels (ABox)**

```python
from org.tweetyproject.logics.dl.syntax import EquivalenceAxiom, SubsumptionAxiom
from org.tweetyproject.logics.dl.syntax import ConceptAssertion, RoleAssertion

# Créer des axiomes terminologiques (TBox)
femaleHuman = EquivalenceAxiom(female, human)
maleHuman = EquivalenceAxiom(male, human)
femaleNotMale = EquivalenceAxiom(female, Complement(male))
parentDef = EquivalenceAxiom(parent, ExistentialRestriction(hasChild, AtomicConcept("top")))

# Créer des assertions (ABox)
bobIsMale = ConceptAssertion(male, bob)
aliceIsFemale = ConceptAssertion(female, alice)
bobParentOfAlice = RoleAssertion(hasChild, bob, alice)

# Créer une base de croyances DL
dbs = DlBeliefSet()
dbs.add(femaleHuman)
dbs.add(maleHuman)
dbs.add(femaleNotMale)
dbs.add(parentDef)
dbs.add(bobIsMale)
dbs.add(aliceIsFemale)
dbs.add(bobParentOfAlice)
```

#### 1.1.5 Formules booléennes quantifiées (QBF)

**Exemple: Création et manipulation de QBF**

```python
from org.tweetyproject.logics.qbf.syntax import QbfFormula, QbfQuantifier, QbfBeliefSet
from org.tweetyproject.logics.pl.syntax import Proposition, Conjunction, Disjunction, Negation

# Créer des propositions
a = Proposition("a")
b = Proposition("b")
c = Proposition("c")

# Créer une formule QBF: ∀a ∃b (a ∨ b) ∧ (¬a ∨ ¬b)
inner_formula = Conjunction(
    Disjunction(a, b),
    Disjunction(Negation(a), Negation(b))
)
exists_b = QbfFormula(QbfQuantifier.EXISTS, b, inner_formula)
forall_a = QbfFormula(QbfQuantifier.FORALL, a, exists_b)

# Créer une base de croyances QBF
qbf_bs = QbfBeliefSet()
qbf_bs.add(forall_a)
```

#### 1.1.6 Logique conditionnelle (CL)

**Exemple: Création et évaluation de bases conditionnelles**

```python
from org.tweetyproject.logics.cl.syntax import ClBeliefSet, Conditional
from org.tweetyproject.logics.pl.syntax import Proposition, Negation
from org.tweetyproject.logics.cl.reasoner import SimpleCReasoner

# Création de propositions
f = Proposition("f")  # f = "peut voler"
b = Proposition("b")  # b = "est un oiseau"
p = Proposition("p")  # p = "est un pingouin"

# Création de conditionnels
c1 = Conditional(f, b)  # (f|b) - Si b alors typiquement f
c2 = Conditional(b, p)  # (b|p) - Si p alors typiquement b
c3 = Conditional(Negation(f), p)  # (!f|p) - Si p alors typiquement !f

# Création d'une base conditionnelle
bs_cl = ClBeliefSet()
bs_cl.add(c1)
bs_cl.add(c2)
bs_cl.add(c3)

# Raisonnement avec SimpleCReasoner
cl_reasoner = SimpleCReasoner()
kappa_model = cl_reasoner.getModel(bs_cl)  # Fonction de classement (ranking)
```

### 1.2 Frameworks d'argumentation

#### 1.2.1 Argumentation abstraite de Dung

**Exemple 1: Création d'un framework d'argumentation**

```python
from org.tweetyproject.arg.dung.syntax import DungTheory, Argument, Attack

# Créer un framework d'argumentation
af = DungTheory()

# Créer des arguments
a = Argument("a")
b = Argument("b")
c = Argument("c")
d = Argument("d")

# Ajouter les arguments au framework
af.add(a)
af.add(b)
af.add(c)
af.add(d)

# Ajouter des attaques
af.add(Attack(a, b))  # a attaque b
af.add(Attack(b, c))  # b attaque c
af.add(Attack(c, d))  # c attaque d
af.add(Attack(d, c))  # d attaque c
```

**Exemple 2: Calcul d'extensions selon différentes sémantiques**

```python
from org.tweetyproject.arg.dung.reasoner import SimpleGroundedReasoner, SimplePreferredReasoner
from org.tweetyproject.arg.dung.reasoner import SimpleStableReasoner, SimpleCompleteReasoner

# Calculer l'extension fondée (grounded)
grounded_reasoner = SimpleGroundedReasoner()
grounded_ext = grounded_reasoner.getModel(af)
print(f"Extension fondée: {grounded_ext}")

# Calculer les extensions préférées
preferred_reasoner = SimplePreferredReasoner()
preferred_exts = preferred_reasoner.getModels(af)
print(f"Extensions préférées: {preferred_exts}")

# Calculer les extensions stables
stable_reasoner = SimpleStableReasoner()
stable_exts = stable_reasoner.getModels(af)
print(f"Extensions stables: {stable_exts}")

# Calculer les extensions complètes
complete_reasoner = SimpleCompleteReasoner()
complete_exts = complete_reasoner.getModels(af)
print(f"Extensions complètes: {complete_exts}")
```

#### 1.2.2 Frameworks dialectiques abstraits (ADF)

**Exemple: Création et manipulation d'un ADF**

```python
from org.tweetyproject.arg.adf.syntax import Argument, Adf, acc
from org.tweetyproject.arg.adf.reasoner import AbstractDialecticalFrameworkReasoner

# Créer un ADF
a = Argument("a")
b = Argument("b")
c = Argument("c")
adf = Adf()
adf.add(a)
adf.add(b)
adf.add(c)

# Définir des conditions d'acceptation
adf.setAcceptanceCondition(a, acc.atom(a))  # a est accepté si a est accepté
adf.setAcceptanceCondition(b, acc.not_(acc.atom(a)))  # b est accepté si a n'est pas accepté
adf.setAcceptanceCondition(c, acc.and_(acc.atom(b), acc.not_(acc.atom(a))))  # c est accepté si b est accepté et a n'est pas accepté

# Raisonnement
reasoner = AbstractDialecticalFrameworkReasoner()
models = reasoner.getModels(adf)
```

#### 1.2.3 Argumentation bipolaire

**Exemple: Création d'un framework bipolaire**

```python
from org.tweetyproject.arg.bipolar.syntax import BipolarArgumentationFramework, Attack, Support
from org.tweetyproject.arg.dung.syntax import Argument

# Créer un framework bipolaire
baf = BipolarArgumentationFramework()
a = Argument("a")
b = Argument("b")
c = Argument("c")
d = Argument("d")
baf.add(a)
baf.add(b)
baf.add(c)
baf.add(d)

# Ajouter des attaques et des supports
baf.addAttack(a, b)  # a attaque b
baf.addSupport(c, a)  # c supporte a
baf.addAttack(b, d)  # b attaque d
baf.addSupport(c, d)  # c supporte d

# Conversion en framework de Dung
dung_theory = baf.asDungTheory()
```

#### 1.2.4 Argumentation basée sur les hypothèses (ABA)

**Exemple: Création d'un framework ABA**

```python
from org.tweetyproject.arg.aba.syntax import AbaRule, AbaTheory, InferenceRule
from org.tweetyproject.logics.pl.syntax import Proposition, Negation
from org.tweetyproject.arg.aba.reasoner import AbaReasoner

# Créer une théorie ABA
theory = AbaTheory()

# Définir des propositions
a = Proposition("a")
b = Proposition("b")
c = Proposition("c")
d = Proposition("d")
e = Proposition("e")

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

#### 1.2.5 Argumentation pondérée (WAF)

**Exemple: Création d'un framework pondéré**

```python
from org.tweetyproject.arg.weighted.syntax import WeightedArgumentationFramework
from org.tweetyproject.arg.dung.syntax import Argument
from org.tweetyproject.arg.weighted.reasoner import WeightedRankingReasoner

# Créer un framework pondéré
waf = WeightedArgumentationFramework()
a = Argument("a")
b = Argument("b")
c = Argument("c")
waf.add(a)
waf.add(b)
waf.add(c)

# Ajouter des attaques pondérées
waf.addAttack(a, b, 0.7)  # a attaque b avec un poids de 0.7
waf.addAttack(b, c, 0.5)  # b attaque c avec un poids de 0.5
waf.addAttack(c, a, 0.3)  # c attaque a avec un poids de 0.3

# Raisonnement
reasoner = WeightedRankingReasoner()
ranking = reasoner.getModel(waf)
```

### 1.4 Maintenance de la vérité et révision de croyances

#### 1.4.4 Mesures d'incohérence et résolution

**Exemple 1: Mesures d'incohérence**

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

**Exemple 2: Énumération de MUS**

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

#### 1.4.5 Révision de croyances multi-agents

**Exemple: Révision de croyances multi-agents**

```python
from org.tweetyproject.beliefdynamics import InformationObject
from org.tweetyproject.beliefdynamics.mas import CrMasBeliefSet, CrMasRevisionWrapper
from org.tweetyproject.agents import DummyAgent
from org.tweetyproject.comparator import Order
from org.tweetyproject.logics.pl.parser import PlParser

# Créer des agents avec un ordre de crédibilité
agents_list = ArrayList()
agent1 = DummyAgent("A1")
agent2 = DummyAgent("A2")
agent3 = DummyAgent("A3")
agents_list.add(agent1)
agents_list.add(agent2)
agents_list.add(agent3)
credOrder = Order(agents_list)
credOrder.setOrderedBefore(agent1, agent2)
credOrder.setOrderedBefore(agent2, agent3)

# Créer une base de croyances multi-agents
parser = PlParser()
base = CrMasBeliefSet(credOrder, PlSignature())

# Ajouter des informations
info1 = InformationObject(parser.parseFormula("!c"), agent2)
info2 = InformationObject(parser.parseFormula("b"), agent3)
base.add(info1)
base.add(info2)

# Nouvelles informations
news = HashSet()
news.add(InformationObject(parser.parseFormula("a"), agent3))

# Révision
revision_op = CrMasRevisionWrapper(levi_operator)
result = revision_op.revise(base, news)