# Fondements théoriques et techniques

Cette section présente les projets centrés sur les aspects formels, logiques et théoriques de l'argumentation.

> **Note importante pour les étudiants**: Pour chaque projet ci-dessous, vous trouverez une référence à des exemples de code spécifiques à la fin de la description du projet. Ces exemples sont extraits du notebook `Tweety.ipynb` et organisés dans le document [Exemples TweetyProject par projet](./exemples_tweety_par_projet.md). Ils vous fourniront un point de départ concret pour implémenter votre projet.

## 1.1 Logiques formelles et raisonnement

### 1.1.1 Intégration des logiques propositionnelles avancées
- **Contexte** : La logique propositionnelle constitue la base de nombreux systèmes de raisonnement automatique. Le module `logics.pl` de Tweety offre des fonctionnalités avancées encore peu exploitées dans le projet. Ce module permet non seulement de représenter et manipuler des formules propositionnelles, mais aussi d'effectuer des opérations complexes comme la conversion en formes normales (DNF/CNF), la simplification, et l'utilisation de solveurs SAT pour le raisonnement efficace.
- **Objectifs** : Améliorer l'agent PL existant pour exploiter davantage les fonctionnalités du module, notamment les solveurs SAT (SAT4J interne ou solveurs externes comme Lingeling, CaDiCaL), la conversion DIMACS, et les opérations avancées sur les formules (DNF, CNF, simplification). Implémenter des requêtes plus sophistiquées comme la vérification de satisfiabilité, la recherche de modèles, et l'analyse d'implications logiques.
- **Technologies clés** :
  * Tweety `logics.pl` (syntaxe, sémantique, parsing)
  * Solveurs SAT modernes (SAT4J interne, intégration avec Lingeling, CaDiCaL)
  * Format DIMACS pour l'échange avec solveurs externes
  * Java-Python bridge via JPype
- **Niveau de difficulté** : ⭐⭐⭐
- **Estimation d'effort** : 3-4 semaines-personnes
- **Portée ajustée** : Se concentrer sur l'intégration d'un seul solveur SAT et la conversion DNF/CNF
- **Interdépendances** : Base pour les projets de maintenance de la vérité (1.4) et d'argumentation formelle (1.2)
- **Références** :
  - "SAT_SMT_by_example.pdf" (2023)
  - "Handbook of Satisfiability, Second Edition" (2021)
  - "Artificial Intelligence: A Modern Approach" (4ème édition, 2021)
- **Livrables attendus** :
  - Agent PL amélioré avec support pour les solveurs SAT externes
  - Fonctions pour la manipulation avancée de formules (conversion DNF/CNF, simplification)
  - Documentation et exemples d'utilisation
  - Tests unitaires et d'intégration

> **Exemple de code**: Voir [Exemples TweetyProject par projet](./exemples_tweety_par_projet.md#111-intégration-des-logiques-propositionnelles-avancées) pour des snippets sur la création de formules propositionnelles, l'utilisation de solveurs SAT et la conversion en formes normales.
### 1.1.2 Logique du premier ordre (FOL)
- **Contexte** : La logique du premier ordre permet d'exprimer des relations plus complexes que la logique propositionnelle, avec des quantificateurs et des prédicats. Le module `logics.fol` de Tweety fournit une implémentation complète pour définir des signatures logiques (types/sorts, constantes, prédicats, fonctions), construire des formules quantifiées, et raisonner sur ces formules via des prouveurs intégrés ou externes.
- **Objectifs** : Développer un nouvel agent utilisant le module `logics.fol` de Tweety pour analyser des arguments plus complexes impliquant des quantificateurs (`∀`, `∃`) et des prédicats. Cet agent pourrait tenter de traduire des arguments exprimés en langage naturel (avec quantificateurs) en formules FOL, définir des signatures logiques (types/sorts, constantes, prédicats, fonctions), et utiliser les raisonneurs intégrés.
- **Technologies clés** :
  * Tweety `logics.fol` (signatures, formules, parsing)
  * Prouveurs FOL modernes (intégration avec Vampire, E-prover, Z3)
  * Techniques de traduction langage naturel vers FOL
  * Manipulation de formules quantifiées
- **Niveau de difficulté** : ⭐⭐⭐
- **Estimation d'effort** : 4 semaines-personnes
- **Portée ajustée** : Se concentrer sur la traduction d'arguments simples en FOL sans intégration de prouveurs externes
- **Interdépendances** : Extension de 1.1.1, base pour 1.2.4 (ABA)
- **Références** :
  - "Automated Theorem Proving: Theory and Practice" (2022)
  - "Handbook of Practical Logic and Automated Reasoning" (2023)
  - "From Natural Language to First-Order Logic: Mapping Techniques and Challenges" (2021)
- **Livrables attendus** :
  - Agent FOL pour l'analyse d'arguments quantifiés
  - Module de traduction langage naturel vers FOL
  - Intégration avec au moins un prouveur externe
  - Documentation et exemples d'utilisation

> **Exemple de code**: Voir [Exemples TweetyProject par projet](./exemples_tweety_par_projet.md#112-logique-du-premier-ordre-fol) pour des snippets sur la définition de signatures FOL et la création de formules avec quantificateurs.

### 1.1.3 Logique modale
- **Contexte** : Les logiques modales permettent de raisonner sur des notions comme la nécessité, la possibilité, les croyances ou les connaissances. Le module `logics.ml` de Tweety implémente les concepts fondamentaux des logiques modales, permettant de représenter et raisonner avec des opérateurs modaux comme la nécessité (`[]`) et la possibilité (`<>`), ainsi que d'utiliser différents systèmes modaux (K, T, S4, S5).
- **Objectifs** : Créer un agent spécialisé utilisant le module `logics.ml` de Tweety pour raisonner sur des modalités comme la nécessité (`[]`), la possibilité (`<>`), les croyances ou les connaissances. Cet agent pourrait analyser des arguments impliquant des notions de possibilité, nécessité, obligation ou permission.
- **Technologies clés** :
  * Tweety `logics.ml`
  * Raisonneurs modaux (SPASS-XDB, MleanCoP)
  * Sémantique des mondes possibles de Kripke
- **Niveau de difficulté** : ⭐⭐⭐
- **Estimation d'effort** : 4 semaines-personnes
- **Portée ajustée** : Se concentrer sur la représentation des modalités de base (nécessité, possibilité) sans intégration de raisonneurs externes
- **Interdépendances** : Peut être combiné avec 1.4 (maintenance de la vérité)
- **Références** :
  - "Handbook of Modal Logic" (2022)
  - "Modal Logic for Open Minds" (2023)
  - "Reasoning About Knowledge" (2021)
- **Livrables attendus** :
  - Agent de logique modale
  - Intégration avec SPASS ou autre raisonneur modal
  - Documentation et exemples d'utilisation
  - Tests unitaires et d'intégration

> **Exemple de code**: Voir [Exemples TweetyProject par projet](./exemples_tweety_par_projet.md#113-logique-modale) pour des snippets sur la création de formules modales et le raisonnement avec SimpleMlReasoner.
### 1.1.4 Logique de description (DL)
- **Contexte** : Les logiques de description sont utilisées pour représenter des connaissances structurées sous forme de concepts, rôles et individus. Le module `logics.dl` de Tweety permet de définir des TBox (axiomes terminologiques) et ABox (assertions sur les individus), et de raisonner sur la subsomption, l'instanciation et la consistance. Cette logique est particulièrement pertinente pour les ontologies et le web sémantique.
- **Objectifs** : Développer un agent utilisant le module `logics.dl` de Tweety pour modéliser des connaissances structurées. Cet agent pourrait construire des TBox (axiomes terminologiques) et ABox (assertions sur les individus), et raisonner sur la subsomption, l'instanciation et la consistance.
- **Technologies clés** :
  * Tweety `logics.dl`
  * Ontologies OWL
  * Raisonneurs DL (HermiT, ELK, Pellet)
- **Niveau de difficulté** : ⭐⭐⭐
- **Estimation d'effort** : 4 semaines-personnes
- **Portée ajustée** : Se concentrer sur la définition de TBox et ABox simples sans intégration de raisonneurs externes
- **Interdépendances** : Peut être combiné avec 1.3 (taxonomies de sophismes)
- **Références** :
  - "The Description Logic Handbook" (2022)
  - "OWL 2 Web Ontology Language Primer" (2023)
  - "Description Logic: A Practical Introduction" (2023)
- **Livrables attendus** :
  - Agent de logique de description
  - Intégration avec au moins un raisonneur DL
  - Documentation et exemples d'utilisation
  - Tests unitaires et d'intégration

> **Exemple de code**: Voir [Exemples TweetyProject par projet](./exemples_tweety_par_projet.md#114-logique-de-description-dl) pour des snippets sur la définition de concepts, rôles et axiomes DL.

### 1.1.5 Formules booléennes quantifiées (QBF)
- **Contexte** : Les QBF étendent la logique propositionnelle avec des quantificateurs, permettant de modéliser des problèmes PSPACE-complets.
- **Objectifs** : Explorer l'utilisation du module `logics.qbf` de Tweety pour modéliser et résoudre des problèmes PSPACE-complets. Cet agent pourrait traiter des problèmes de planification conditionnelle, de jeux à deux joueurs, ou de vérification formelle qui dépassent la portée de SAT.
- **Technologies clés** :
  * Tweety `logics.qbf`
  * Solveurs QBF
  * Format QDIMACS
- **Niveau de difficulté** : ⭐⭐⭐⭐
- **Estimation d'effort** : 4 semaines-personnes
- **Portée ajustée** : Se concentrer sur la modélisation de problèmes simples sans intégration de solveurs externes
- **Interdépendances** : Extension de 1.1.1, peut être utilisé dans 1.5.2 (vérification formelle)
- **Références** :
  - "SAT_SMT_by_example.pdf" (2023)
  - "Handbook of Satisfiability"
  - Documentation Tweety `logics.qbf`
- **Livrables attendus** :
  - Agent QBF pour la modélisation et résolution de problèmes complexes
  - Intégration avec au moins un solveur QBF
  - Documentation et exemples d'utilisation

> **Exemple de code**: Voir [Exemples TweetyProject par projet](./exemples_tweety_par_projet.md#115-formules-booléennes-quantifiées-qbf) pour des snippets sur la création et manipulation de formules QBF.
### 1.1.6 Logique conditionnelle (CL)
- **Contexte** : Les logiques conditionnelles permettent de raisonner sur des énoncés de la forme "Si A est vrai, alors B est typiquement vrai". Elles constituent un formalisme puissant pour représenter des connaissances incertaines et des règles par défaut. Le module `logics.cl` de Tweety implémente les fonctions de classement (ranking) ou OCF (Ordinal Conditional Functions) pour évaluer ces conditionnels et raisonner de manière non-monotone.
- **Objectifs** : Implémenter un agent utilisant le module `logics.cl` de Tweety pour raisonner sur des conditionnels. Le notebook Tweety démontre comment créer une base conditionnelle avec des conditionnels comme (f|b), (b|p), (¬f|p), et comment calculer une fonction de classement (ranking) pour évaluer ces conditionnels. L'agent devra permettre la création de bases de connaissances conditionnelles, l'évaluation de requêtes conditionnelles, et la visualisation des fonctions de classement.
- **Technologies clés** :
  * Tweety `logics.cl`
  * Raisonnement non-monotone
  * Fonctions de classement (ranking) ou OCF (Ordinal Conditional Functions)
  * Sémantique des mondes possibles
- **Niveau de difficulté** : ⭐⭐⭐
- **Estimation d'effort** : 4 semaines-personnes
- **Portée ajustée** : Se concentrer sur la création de bases conditionnelles simples et l'évaluation de requêtes basiques
- **Interdépendances** : Peut être combiné avec 1.2 (frameworks d'argumentation) et 1.4.3 (raisonnement non-monotone)
- **Références** :
  - "Conditionals in Nonmonotonic Reasoning and Belief Revision" de Gabriele Kern-Isberner (2001)
  - "A Ranking Semantics for First-Order Conditionals" de Wilhelm Kötter et al. (2019)
  - "Reasoning-with-probabilistic-and-deterministic-graphical-models-exact-algorithms" (2013)
  - Documentation Tweety `logics.cl`
- **Livrables attendus** :
  - Agent de logique conditionnelle
  - Fonctions pour la création et l'évaluation de bases conditionnelles
  - Visualisation des fonctions de classement (OCF)
  - Interface pour la formulation de requêtes conditionnelles
  - Documentation et exemples d'utilisation
  - Tests unitaires et d'intégration

> **Exemple de code**: Voir [Exemples TweetyProject par projet](./exemples_tweety_par_projet.md#116-logique-conditionnelle-cl) pour des snippets sur la création et l'évaluation de bases conditionnelles.

## 1.2 Frameworks d'argumentation

### 1.2.1 Argumentation abstraite de Dung
- **Contexte** : Les frameworks d'argumentation abstraite de Dung (AF) fournissent un cadre mathématique pour représenter et évaluer des arguments en conflit. Le module `arg.dung` de Tweety offre une implémentation complète de ce formalisme, permettant de construire des graphes d'arguments et d'attaques (`DungTheory`), et de calculer l'acceptabilité des arguments selon différentes sémantiques (admissible, complète, préférée, stable, fondée, idéale, semi-stable, CF2, etc.).
- **Objectifs** : Implémenter un agent spécialisé utilisant le module `arg.dung` de Tweety pour représenter et évaluer des arguments abstraits. Cet agent devrait permettre de construire des graphes d'arguments et d'attaques (`DungTheory`), et surtout de calculer l'acceptabilité des arguments selon différentes sémantiques (admissible, complète, préférée, stable, fondée, idéale, semi-stable, CF2...).
- **Technologies clés** :
  * Tweety `arg.dung` (construction, manipulation, visualisation)
  * Algorithmes de calcul d'extensions pour différentes sémantiques
  * Techniques d'apprentissage et de génération de frameworks
  * Visualisation de graphes d'argumentation
- **Niveau de difficulté** : ⭐⭐⭐
- **Estimation d'effort** : 3-4 semaines-personnes
- **Portée ajustée** : Se concentrer sur les sémantiques principales (admissible, complète, préférée) et une visualisation simple
- **Interdépendances** : Base pour les autres frameworks d'argumentation (1.2.x)
- **Références** :
  - "On the Acceptability of Arguments and its Fundamental Role in Nonmonotonic Reasoning" (Dung, 1995)
  - "Abstract Argumentation Frameworks" (2022)
  - "Computational Problems in Abstract Argumentation" (2023)
- **Livrables attendus** :
  - Agent d'argumentation abstraite
  - Implémentation des principales sémantiques d'acceptabilité
  - Visualisation des graphes d'argumentation
  - Documentation et exemples d'utilisation
  - Cas d'étude démontrant l'application à un problème concret

> **Exemple de code**: Voir [Exemples TweetyProject par projet](./exemples_tweety_par_projet.md#121-argumentation-abstraite-de-dung) pour des snippets sur la création de frameworks d'argumentation et le calcul d'extensions selon différentes sémantiques.
### 1.2.2 Argumentation bipolaire
- **Contexte** : L'argumentation bipolaire étend les frameworks de Dung en distinguant deux types de relations entre arguments : l'attaque et le support. Le module `arg.bipolar` de Tweety implémente plusieurs variantes de frameworks bipolaires, avec différentes interprétations du support (déductif, nécessaire, évidentiel) et leurs sémantiques associées. Ces frameworks permettent de modéliser des relations plus nuancées entre arguments.
- **Objectifs** : Développer un agent utilisant le module `arg.bipolar` de Tweety pour représenter et évaluer des arguments avec relations d'attaque et de support. Comprendre les différentes interprétations du support (déductif, nécessaire, évidentiel...) et les sémantiques associées proposées dans la littérature et implémentées dans Tweety.
- **Technologies clés** :
  * Tweety `arg.bipolar`
  * Sémantiques pour l'argumentation bipolaire
  * Extraction de relations de support
- **Niveau de difficulté** : ⭐⭐⭐
- **Estimation d'effort** : 3-4 semaines-personnes
- **Portée ajustée** : Se concentrer sur une seule interprétation du support (déductif ou nécessaire)
- **Interdépendances** : Extension de 1.2.1 (Dung AF)
- **Références** :
  - "Bipolar Argumentation Frameworks" (2022)
  - "A Logical Account of Formal Argumentation" (2023)
  - "Semantics for Support Relations in Abstract Argumentation" (2022)
- **Livrables attendus** :
  - Agent d'argumentation bipolaire
  - Implémentation des principales sémantiques pour BAF
  - Visualisation des graphes bipolaires
  - Documentation et exemples d'utilisation

> **Exemple de code**: Voir [Exemples TweetyProject par projet](./exemples_tweety_par_projet.md#123-argumentation-bipolaire) pour des snippets sur la création de frameworks bipolaires avec relations d'attaque et de support.

### 1.2.3 Argumentation pondérée
- **Contexte** : L'argumentation pondérée associe des poids numériques aux arguments ou aux attaques pour représenter leur force relative. Les modules `arg.prob` et `arg.social` de Tweety permettent de manipuler des frameworks d'argumentation avec poids, en utilisant différents semi-anneaux (WeightedSemiring, FuzzySemiring, ProbabilisticSemiring) pour l'agrégation des poids et le calcul de l'acceptabilité.
- **Objectifs** : Créer un agent utilisant le module `arg.prob` ou `arg.social` de Tweety pour manipuler des frameworks d'argumentation avec poids. Cet agent pourrait utiliser différents semi-anneaux (WeightedSemiring, FuzzySemiring, ProbabilisticSemiring) et raisonneurs pondérés.
- **Technologies clés** :
  * Tweety `arg.prob` et `arg.social`
  * Méthodes d'agrégation de poids
  * Estimation automatique de la force des arguments
- **Niveau de difficulté** : ⭐⭐⭐
- **Estimation d'effort** : 4 semaines-personnes
- **Portée ajustée** : Se concentrer sur un seul type de semi-anneau (WeightedSemiring ou ProbabilisticSemiring)
- **Interdépendances** : Extension de 1.2.1 (Dung AF)
- **Références** :
  - "Weighted Argument Systems" (2022)
  - "Gradual Argumentation: A Comprehensive Survey" (2023)
  - "Learning Weights in Abstract Argumentation" (2022)
- **Livrables attendus** :
  - Agent d'argumentation pondérée
  - Implémentation de différents semi-anneaux et raisonneurs
  - Visualisation des graphes pondérés
  - Documentation et exemples d'utilisation

> **Exemple de code**: Voir [Exemples TweetyProject par projet](./exemples_tweety_par_projet.md#125-argumentation-pondérée-waf) pour des snippets sur la création de frameworks pondérés avec attaques de différentes forces.

### 1.2.4 Argumentation basée sur les hypothèses (ABA)
- **Contexte** : L'argumentation basée sur les hypothèses (ABA) est un framework qui représente les arguments comme des déductions à partir d'hypothèses.
- **Objectifs** : Développer un agent utilisant le module `arg.aba` de Tweety pour représenter et évaluer des arguments basés sur des hypothèses. Cet agent pourrait analyser les attaques entre arguments dérivés de ces hypothèses et déterminer leur acceptabilité.
- **Technologies clés** :
  * Tweety `arg.aba`
  * Logiques non-monotones
  * Traduction langage naturel vers ABA
- **Niveau de difficulté** : ⭐⭐⭐⭐
- **Estimation d'effort** : 4 semaines-personnes
- **Portée ajustée** : Se concentrer sur des cas simples d'ABA sans traduction depuis le langage naturel
- **Interdépendances** : Lié à 1.1.2 (FOL) et 1.2.1 (Dung AF)
- **Références** :
  - "Assumption-Based Argumentation" (2022)
  - "Computational Aspects of Assumption-Based Argumentation" (2023)
  - "ABA+: Assumption-Based Argumentation with Preferences" (2022)
- **Livrables attendus** :
  - Agent ABA
  - Module de traduction langage naturel vers ABA
  - Documentation et exemples d'utilisation

> **Exemple de code**: Voir [Exemples TweetyProject par projet](./exemples_tweety_par_projet.md#124-argumentation-basée-sur-les-hypothèses-aba) pour des snippets sur la création de frameworks ABA avec règles, hypothèses et contraires.
### 1.2.5 Argumentation basée sur les valeurs (VAF)
- **Contexte** : L'argumentation basée sur les valeurs (VAF) étend les frameworks abstraits en associant des valeurs aux arguments.
- **Objectifs** : Créer un agent spécialisé pour représenter et évaluer des arguments basés sur des valeurs. Cet agent devrait permettre de modéliser des préférences sur les valeurs et d'évaluer l'acceptabilité des arguments en fonction de ces préférences.
- **Technologies clés** :
  * Frameworks d'argumentation basés sur les valeurs
  * Identification automatique de valeurs
  * Modélisation de préférences sur les valeurs
- **Niveau de difficulté** : ⭐⭐⭐
- **Estimation d'effort** : 4 semaines-personnes
- **Portée ajustée** : Se concentrer sur la modélisation de préférences simples sur les valeurs
- **Interdépendances** : Extension de 1.2.1 (Dung AF)
- **Références** :
  - "Argumentation Based on Value" (2022)
  - "Value-Based Argumentation Frameworks" (2023)
  - "Ethical Argumentation" (2022)
- **Livrables attendus** :
  - Agent VAF
  - Module d'identification de valeurs dans les arguments
  - Visualisation des graphes VAF
  - Documentation et exemples d'utilisation

### 1.2.6 Argumentation structurée (ASPIC+)
- **Contexte** : ASPIC+ est un framework d'argumentation structurée qui combine la logique formelle avec des mécanismes de gestion des conflits et des préférences.
- **Objectifs** : Développer un agent implémentant le framework ASPIC+ pour construire et évaluer des arguments structurés. Cet agent pourrait modéliser des bases de connaissances avec axiomes et règles, gérer les préférences entre règles, et analyser les attaques (rebutting, undercutting, undermining).
- **Technologies clés** :
  * Framework ASPIC+
  * Règles strictes et défaisables
  * Gestion des préférences
- **Niveau de difficulté** : ⭐⭐⭐⭐
- **Estimation d'effort** : 4 semaines-personnes
- **Portée ajustée** : Se concentrer sur un sous-ensemble du framework avec des règles strictes uniquement
- **Interdépendances** : Lié à 1.1 (logiques formelles) et 1.2.1 (Dung AF)
- **Références** :
  - "ASPIC+: An Argumentation Framework for Structured Argumentation" (2022)
  - "Rationality Postulates for Structured Argumentation" (2023)
  - "From Natural Language to ASPIC+" (2022)
- **Livrables attendus** :
  - Agent ASPIC+
  - Module de traduction langage naturel vers ASPIC+
  - Visualisation des arguments structurés
  - Documentation et exemples d'utilisation

### 1.2.7 Argumentation dialogique
- **Contexte** : L'argumentation dialogique modélise les débats comme des échanges structurés entre participants, avec des règles spécifiques.
- **Objectifs** : Créer un agent capable de participer à des dialogues argumentatifs suivant différents protocoles. Cet agent devrait pouvoir générer des arguments, des contre-arguments, et des questions critiques en fonction du contexte du dialogue.
- **Technologies clés** :
  * Protocoles de dialogue argumentatif
  * Stratégies argumentatives
  * Apprentissage par renforcement
- **Niveau de difficulté** : ⭐⭐⭐
- **Estimation d'effort** : 4 semaines-personnes
- **Portée ajustée** : Se concentrer sur un seul protocole de dialogue simple
- **Interdépendances** : Peut utiliser n'importe quel framework d'argumentation (1.2.x)
- **Références** :
  - "Dialogue-Based Argumentation" (2022)
  - "Protocols for Argumentative Dialogue" (2023)
  - "Strategic Argumentation" (2022)
- **Livrables attendus** :
  - Agent de dialogue argumentatif
  - Implémentation de plusieurs protocoles de dialogue
  - Interface pour l'interaction avec l'agent
  - Documentation et exemples d'utilisation

> **📖 Guide pédagogique détaillé** : [1.2.7 Argumentation Dialogique](./sujets/1.2.7_Argumentation_Dialogique.md)

### 1.2.8 Abstract Dialectical Frameworks (ADF)
- **Contexte** : Les ADF généralisent les AAF de Dung en associant à chaque argument une condition d'acceptation. Le module `arg.adf` de Tweety implémente ce formalisme avancé où chaque argument est associé à une formule propositionnelle (sa condition d'acceptation) qui détermine son statut en fonction de l'état des autres arguments. Cette approche permet de modéliser des dépendances complexes comme le support, l'attaque conjointe, ou des combinaisons arbitraires de relations.
- **Objectifs** : Implémenter un agent utilisant le module `arg.adf` de Tweety. Les ADF généralisent les AAF de Dung en associant à chaque argument une condition d'acceptation (une formule propositionnelle sur l'état des autres arguments), permettant de modéliser des dépendances plus complexes que la simple attaque (ex: support, attaque conjointe).
- **Technologies clés** :
  * Tweety `arg.adf`
  * Solveurs SAT incrémentaux
  * Formules propositionnelles
- **Niveau de difficulté** : ⭐⭐⭐⭐
- **Estimation d'effort** : 4 semaines-personnes
- **Portée ajustée** : Se concentrer sur des ADF simples avec des conditions d'acceptation basiques
- **Interdépendances** : Extension de 1.2.1 (Dung), utilise 1.1.1 (logique propositionnelle)
- **Références** :
  - Article fondateur de Brewka et al. (2013) "Abstract Dialectical Frameworks"
  - "Implementing KR Approaches with Tweety" (2018)
  - Documentation Tweety `arg.adf`
- **Livrables attendus** :
  - Agent ADF
  - Intégration avec solveurs SAT incrémentaux
  - Visualisation des ADF
  - Documentation et exemples d'utilisation

> **Exemple de code**: Voir [Exemples TweetyProject par projet](./exemples_tweety_par_projet.md#122-frameworks-dialectiques-abstraits-adf) pour des snippets sur la création d'ADF avec conditions d'acceptation personnalisées.

### 1.2.9 Analyse probabiliste d'arguments
- **Contexte** : L'argumentation probabiliste permet de gérer l'incertitude dans les frameworks d'argumentation. Le module `arg.prob` de Tweety implémente l'approche de Li, Hunter et Thimm, où des probabilités sont associées aux arguments ou aux sous-ensembles d'arguments. Cette approche permet d'évaluer la robustesse des conclusions face à l'incertitude et de calculer des degrés de croyance dans l'acceptabilité des arguments.
- **Objectifs** : Développer un agent utilisant le module `arg.prob` de Tweety pour analyser des arguments avec incertitude. Implémenter différentes distributions de probabilité sur les arguments, calculer des degrés d'acceptabilité, et visualiser l'impact de l'incertitude sur les conclusions argumentatives.
- **Technologies clés** :
  * Tweety `arg.prob`
  * Distributions de probabilité sur les arguments
  * Calcul de degrés d'acceptabilité
  * Visualisation de l'incertitude argumentative
- **Niveau de difficulté** : ⭐⭐⭐
- **Estimation d'effort** : 4 semaines-personnes
- **Portée ajustée** : Se concentrer sur un modèle probabiliste simple avec visualisation basique
- **Interdépendances** : Extension de 1.2.1 (Dung AF) et 1.2.3 (Argumentation pondérée)
- **Références** :
  - "A Probabilistic Framework for Modelling Legal Argument" (2022)
  - "Probabilistic Argumentation: An Approach Based on a Conditional Logics" (2023)
  - "Handling Uncertainty in Argumentation Frameworks" (2022)
- **Livrables attendus** :
  - Agent d'argumentation probabiliste
  - Implémentation de différentes distributions de probabilité
  - Visualisation des degrés d'acceptabilité
  - Documentation et exemples d'utilisation
  - Tests unitaires et d'intégration
## 1.3 Taxonomies et classification

### 1.3.1 Taxonomie des schémas argumentatifs
- **Contexte** : Les schémas argumentatifs sont des modèles récurrents de raisonnement utilisés dans l'argumentation quotidienne.
- **Objectifs** : Développer une taxonomie complète des schémas argumentatifs, en s'appuyant sur les travaux de Walton et d'autres chercheurs. Cette taxonomie devrait inclure les questions critiques associées à chaque schéma et des exemples concrets.
- **Technologies clés** :
  * Schémas argumentatifs de Walton
  * Classification automatique de schémas
  * Questions critiques associées aux schémas
- **Niveau de difficulté** : ⭐⭐⭐
- **Estimation d'effort** : 3-4 semaines-personnes
- **Portée ajustée** : Se concentrer sur un sous-ensemble de schémas argumentatifs courants
- **Interdépendances** : Base pour 2.3.1 (extraction d'arguments)
- **Références** :
  - "Argumentation Schemes" de Walton, Reed & Macagno (édition mise à jour, 2022)
  - "Automatic Identification of Argument Schemes" (2023)
  - "A Computational Model of Argument Schemes" (2022)
- **Livrables attendus** :
  - Taxonomie structurée des schémas argumentatifs
  - Base de données d'exemples pour chaque schéma
  - Module de classification automatique
  - Documentation et guide d'utilisation

### 1.3.2 Classification des sophismes
- **Contexte** : Les sophismes sont des erreurs de raisonnement qui peuvent sembler valides mais qui violent les principes de la logique.
- **Objectifs** : Enrichir et structurer la taxonomie des sophismes utilisée dans le projet, en intégrant des classifications historiques et contemporaines. Cette taxonomie devrait inclure des définitions précises, des exemples, et des méthodes de détection pour chaque type de sophisme.
- **Technologies clés** :
  * Taxonomies de sophismes
  * Détection automatique de sophismes
  * Apprentissage automatique pour la classification
- **Niveau de difficulté** : ⭐⭐⭐
- **Estimation d'effort** : 3-4 semaines-personnes
- **Portée ajustée** : Se concentrer sur une catégorie spécifique de sophismes
- **Interdépendances** : Base pour 2.3.2 (détection de sophismes)
- **Références** :
  - "Fallacies: Classical and Contemporary Readings" (édition mise à jour, 2022)
  - "Logical Fallacies: The Definitive Guide" (2023)
  - "Automated Detection of Fallacies in Arguments" (2022)
- **Livrables attendus** :
  - Taxonomie structurée des sophismes
  - Base de données d'exemples pour chaque sophisme
  - Module de détection automatique
  - Documentation et guide d'utilisation

### 1.3.3 Ontologie de l'argumentation
- **Contexte** : Une ontologie formelle de l'argumentation permet de structurer et d'interconnecter les concepts liés à l'analyse argumentative.
- **Objectifs** : Développer une ontologie complète de l'argumentation, intégrant les différents frameworks, schémas, et taxonomies. Cette ontologie devrait être formalisée en OWL et permettre des inférences sur les structures argumentatives.
- **Technologies clés** :
  * Ontologies OWL
  * Protégé
  * Raisonneurs ontologiques
- **Niveau de difficulté** : ⭐⭐⭐
- **Estimation d'effort** : 4 semaines-personnes
- **Portée ajustée** : Se concentrer sur une ontologie simple couvrant les concepts de base
- **Interdépendances** : Intègre 1.1.4 (DL), 1.3.1 (schémas), 1.3.2 (sophismes)
- **Références** :
  - "Building Ontologies with Basic Formal Ontology" (2022)
  - "The Argument Interchange Format" (2023)
  - "Ontological Foundations for Argumentation" (2022)
- **Livrables attendus** :
  - Ontologie OWL de l'argumentation
  - Documentation de l'ontologie
  - Exemples d'utilisation et de requêtes
  - Intégration avec les agents d'analyse argumentative
## 1.4 Maintenance de la vérité et révision de croyances

### 1.4.1 Systèmes de maintenance de la vérité (TMS)
- **Contexte** : Les TMS permettent de gérer les dépendances entre croyances et de maintenir la cohérence lors de l'ajout ou du retrait d'informations.
- **Objectifs** : Implémenter un système de maintenance de la vérité pour gérer les dépendances entre arguments et assurer la cohérence des conclusions. Ce système devrait pouvoir gérer les justifications des croyances et propager les changements de manière efficace.
- **Technologies clés** :
  * JTMS (Justification-based TMS)
  * ATMS (Assumption-based TMS)
  * Graphes de dépendances
- **Niveau de difficulté** : ⭐⭐⭐
- **Estimation d'effort** : 4 semaines-personnes
- **Portée ajustée** : Se concentrer sur l'implémentation d'un JTMS simple
- **Interdépendances** : Peut être combiné avec 1.1 (logiques formelles) et 1.2 (frameworks d'argumentation)
- **Références** :
  - "Building Problem Solvers" (édition mise à jour, 2022)
  - "Truth Maintenance Systems: A New Perspective" (2023)
  - "Dependency-Directed Reasoning for Complex Knowledge Bases" (2022)
- **Livrables attendus** :
  - Implémentation d'un TMS (JTMS ou ATMS)
  - Intégration avec l'état partagé du système
  - Documentation et exemples d'utilisation
  - Tests unitaires et d'intégration

> **📖 Guide pédagogique détaillé** : [1.4.1 Systèmes de Maintenance de la Vérité (TMS)](./sujets/1.4.1_Systemes_Maintenance_Verite_TMS.md)

### 1.4.2 Révision de croyances
- **Contexte** : La révision de croyances étudie comment mettre à jour un ensemble de croyances de manière cohérente face à de nouvelles informations.
- **Objectifs** : Développer des mécanismes de révision de croyances pour adapter les conclusions argumentatives face à de nouvelles informations. Implémenter différents opérateurs de révision et contraction basés sur la théorie AGM.
- **Technologies clés** :
  * AGM (Alchourrón-Gärdenfors-Makinson)
  * Opérateurs de révision et contraction
  * Ordres épistémiques
- **Niveau de difficulté** : ⭐⭐⭐
- **Estimation d'effort** : 4 semaines-personnes
- **Portée ajustée** : Se concentrer sur un opérateur de révision simple
- **Interdépendances** : Lié à 1.4.1 (TMS) et 1.2 (frameworks d'argumentation)
- **Références** :
  - "Belief Revision" (Gärdenfors, édition mise à jour, 2022)
  - "Knowledge in Flux" (2023)
  - "Belief Change: A Computational Approach" (2022)
- **Livrables attendus** :
  - Implémentation d'opérateurs de révision et contraction
  - Intégration avec l'état partagé du système
  - Documentation et exemples d'utilisation
  - Tests unitaires et d'intégration

### 1.4.3 Raisonnement non-monotone
- **Contexte** : Le raisonnement non-monotone permet de tirer des conclusions provisoires qui peuvent être révisées à la lumière de nouvelles informations. Contrairement à la logique classique où l'ajout d'informations préserve les conclusions (monotonie), le raisonnement non-monotone permet de modéliser des situations où de nouvelles informations peuvent invalider des conclusions précédentes.
- **Objectifs** : Implémenter des mécanismes de raisonnement non-monotone pour gérer l'incertitude et l'incomplétude dans l'analyse argumentative. Explorer différentes approches comme la logique par défaut, la circonscription, la logique autoépistémique, et les conditionnels non-monotones basés sur les fonctions de classement (OCF).
- **Technologies clés** :
  * Logique par défaut (Reiter)
  * Circonscription (McCarthy)
  * Logique autoépistémique (Moore)
  * Fonctions de classement (OCF) de Spohn
  * Module `logics.cl` de TweetyProject
- **Niveau de difficulté** : ⭐⭐⭐⭐
- **Estimation d'effort** : 4 semaines-personnes
- **Portée ajustée** : Se concentrer sur une approche spécifique (logique par défaut ou conditionnels)
- **Interdépendances** : Lié à 1.1 (logiques formelles), 1.1.6 (logique conditionnelle) et 1.4.2 (révision de croyances)
- **Références** :
  - "Nonmonotonic Reasoning: Logical Foundations of Commonsense" (2022)
  - "Default Logic and Its Applications" (2023)
  - "Autoepistemic Logic and Its Applications" (2022)
  - "Ordinal conditional functions: a dynamic theory of epistemic states" de W. Spohn (1988)
  - "A Comparative Study of Nonmonotonic Inference Systems" de Brewka et al. (2019)
- **Livrables attendus** :
  - Implémentation d'au moins une approche de raisonnement non-monotone
  - Comparaison des différentes approches sur des exemples classiques (Yale Shooting Problem, Nixon Diamond, etc.)
  - Visualisation des processus de raisonnement non-monotone
  - Intégration avec l'état partagé du système
  - Documentation et exemples d'utilisation
  - Tests unitaires et d'intégration

### 1.4.4 Mesures d'incohérence et résolution
- **Contexte** : Quantifier et résoudre les incohérences est crucial pour maintenir la qualité des bases de connaissances.
- **Objectifs** : Intégrer les mesures d'incohérence de Tweety (`logics.pl.analysis`) pour quantifier le degré d'incohérence d'un ensemble d'informations, et implémenter des méthodes de résolution comme l'énumération de MUS (Minimal Unsatisfiable Subsets) et MaxSAT.
- **Technologies clés** :
  * Tweety `logics.pl.analysis`
  * MUS (Minimal Unsatisfiable Subsets)
  * MaxSAT
- **Niveau de difficulté** : ⭐⭐⭐⭐
- **Estimation d'effort** : 4 semaines-personnes
- **Portée ajustée** : Se concentrer sur l'implémentation d'une mesure d'incohérence simple
- **Interdépendances** : Utilise 1.1.1 (logique propositionnelle), lié à 1.4.1 (maintenance de la vérité)
- **Références** :
  - Survey de Hunter et Konieczny sur les mesures d'incohérence
  - "Reasoning-with-probabilistic-and-deterministic-graphical-models-exact-algorithms" (2013)
  - "SAT_SMT_by_example.pdf" (2023)
- **Livrables attendus** :
  - Implémentation de plusieurs mesures d'incohérence
  - Algorithmes d'énumération de MUS
  - Résolution d'incohérences via MaxSAT
  - Documentation et exemples d'utilisation

> **Exemple de code**: Voir [Exemples TweetyProject par projet](./exemples_tweety_par_projet.md#144-mesures-dincohérence-et-résolution) pour des snippets sur l'utilisation de mesures d'incohérence et l'énumération de MUS.

### 1.4.5 Révision de croyances multi-agents
- **Contexte** : La révision de croyances multi-agents étudie comment plusieurs agents peuvent mettre à jour leurs croyances de manière cohérente face à de nouvelles informations, potentiellement contradictoires. Le module `beliefdynamics` de Tweety fournit des outils pour modéliser ce processus, en permettant de représenter les croyances de différents agents et de simuler leur évolution au fil du temps et des interactions.
- **Objectifs** : Développer un système de révision de croyances multi-agents basé sur le module `beliefdynamics` de Tweety. Implémenter différentes stratégies de révision (crédulité, scepticisme, consensus) et analyser leur impact sur la convergence des croyances dans un groupe d'agents.
- **Technologies clés** :
  * Tweety `beliefdynamics`
  * Stratégies de révision multi-agents
  * Modèles de confiance entre agents
  * Visualisation de l'évolution des croyances
- **Niveau de difficulté** : ⭐⭐⭐
- **Estimation d'effort** : 4 semaines-personnes
- **Portée ajustée** : Se concentrer sur un scénario simple avec deux agents
- **Interdépendances** : Lié à 1.4.2 (Révision de croyances) et 2.1.6 (Gouvernance multi-agents)
- **Références** :
  - "Belief Revision in Multi-Agent Systems" (2022)
  - "Social Choice Theory and Belief Merging" (2023)
  - "Trust-Based Belief Revision in Multi-Agent Settings" (2022)
- **Livrables attendus** :
  - Système de révision de croyances multi-agents
  - Implémentation de différentes stratégies de révision
  - Visualisation de l'évolution des croyances
  - Documentation et exemples d'utilisation

> **Exemple de code**: Voir [Exemples TweetyProject par projet](./exemples_tweety_par_projet.md#145-révision-de-croyances-multi-agents) pour des snippets sur la création de bases de croyances multi-agents et l'application d'opérateurs de révision.
## 1.5 Planification et vérification formelle

### 1.5.1 Intégration d'un planificateur symbolique
- **Contexte** : La planification automatique permet de générer des séquences d'actions pour atteindre des objectifs.
- **Objectifs** : Développer un agent capable de générer des plans d'action basés sur des objectifs argumentatifs, en explorant le module `action` de Tweety pour la modélisation des actions et la planification. Cet agent pourrait générer des plans pour atteindre des objectifs comme "faire accepter un argument spécifique" ou "réfuter un ensemble d'arguments adverses".
- **Technologies clés** :
  * Tweety `action`
  * Planification automatique
  * PDDL (Planning Domain Definition Language)
- **Niveau de difficulté** : ⭐⭐⭐
- **Estimation d'effort** : 4 semaines-personnes
- **Portée ajustée** : Se concentrer sur un domaine de planification simple
- **Interdépendances** : Peut utiliser 1.1.5 (QBF) pour la planification conditionnelle
- **Références** :
  - "Automated planning" (2010)
  - "Automated planning and acting - book" (2016)
  - "Integrated Task and motion planning" (2020)
- **Livrables attendus** :
  - Agent de planification symbolique
  - Modélisation PDDL des domaines argumentatifs
  - Documentation et exemples d'utilisation
  - Tests unitaires et d'intégration

### 1.5.2 Vérification formelle d'arguments
- **Contexte** : La vérification formelle permet de garantir que les arguments respectent certaines propriétés.
- **Objectifs** : Développer des méthodes de vérification formelle pour garantir la validité des arguments dans un contexte contractuel, en utilisant potentiellement les capacités QBF ou FOL de Tweety. L'objectif est d'assurer que les arguments utilisés dans un contrat respectent certaines propriétés formelles (cohérence, non-circularité, etc.) avant leur exécution.
- **Technologies clés** :
  * Vérification formelle
  * Model checking
  * Prouveurs de théorèmes
- **Niveau de difficulté** : ⭐⭐⭐⭐
- **Estimation d'effort** : 4 semaines-personnes
- **Portée ajustée** : Se concentrer sur la vérification de propriétés simples
- **Interdépendances** : Utilise 1.1.1-1.1.5 (logiques formelles), lié à 1.5.3 (contrats argumentatifs)
- **Références** :
  - "The Lean theorem prover" (2015)
  - "The Lean 4 Theorem Prover and Programming Language" (2021)
  - "SAT_SMT_by_example.pdf" (2023)
- **Livrables attendus** :
  - Méthodes de vérification formelle pour arguments
  - Intégration avec au moins un prouveur de théorèmes
  - Documentation et exemples d'utilisation
  - Cas d'étude démontrant l'application à un problème concret

### 1.5.3 Formalisation de contrats argumentatifs
- **Contexte** : Les smart contracts peuvent être utilisés pour formaliser et exécuter des protocoles d'argumentation.
- **Objectifs** : Explorer l'utilisation de smart contracts pour formaliser et exécuter des protocoles d'argumentation, en s'appuyant sur les différents formalismes d'argumentation disponibles dans Tweety. Cette approche permettrait d'automatiser l'exécution de débats structurés ou de processus de résolution de conflits selon des règles prédéfinies et vérifiables.
- **Technologies clés** :
  * Smart contracts
  * Blockchain
  * Protocoles d'argumentation
- **Niveau de difficulté** : ⭐⭐⭐
- **Estimation d'effort** : 4 semaines-personnes
- **Portée ajustée** : Se concentrer sur un protocole d'argumentation simple
- **Interdépendances** : Lié à 1.2 (frameworks d'argumentation) et 1.5.2 (vérification formelle)
- **Références** :
  - "Bitcoin and Beyond - Cryptocurrencies, blockchain and global governance" (2018)
  - "Survey on blockchain based smart contracts - Applications, opportunities and challenges" (2021)
  - Documentation sur les plateformes de smart contracts (Ethereum, etc.)
- **Livrables attendus** :
  - Modèles de contrats argumentatifs
  - Implémentation d'au moins un protocole d'argumentation
  - Documentation et exemples d'utilisation
  - Démonstration d'exécution sur une blockchain de test