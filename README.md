# Projet Intelligence Symbolique

## Introduction

Ce projet a pour but de vous permettre d'appliquer concrètement les méthodes et outils vus en cours sur l'intelligence symbolique. Vous serez amenés à résoudre des problèmes réels ou réalistes à l'aide de ces techniques en développant un projet complet, depuis la modélisation jusqu'à la solution opérationnelle.

Cette année, contrairement au cours précédent de programmation par contrainte où vous avez livré des travaux indépendants, vous travaillerez tous de concert sur ce dépôt. Un tronc commun est fourni sous la forme d'une infrastructure d'analyse argumentative multi-agents que vous pourrez explorer à travers les nombreux README du projet.

## Modalités du projet

### Livrables

Chaque groupe devra contribuer au dépôt principal via des **pull requests** régulières. Ces contributions devront être clairement identifiées et documentées, et pourront inclure :

- Le code source complet, opérationnel, documenté et maintenable (en Python, Java via JPype, ou autre).
- Le matériel complémentaire utilisé pour le projet (datasets, scripts auxiliaires, etc.).
- Les slides utilisés lors de la présentation finale.
- Un notebook explicatif détaillant les étapes du projet, les choix de modélisation, les expérimentations et les résultats obtenus.

Les pull requests devront être régulièrement mises à jour durant toute la durée du projet afin que l'enseignant puisse suivre l'avancement et éventuellement apporter des retours, et que tous les élèves puissent prendre connaissance des travaux des autres groupes avant la soutenance avec évaluation collégiale.

### Présentation

- Présentation orale finale avec support visuel (slides).
- Démonstration de la solution opérationnelle devant la classe.

### Évaluation

- Évaluation collégiale : chaque élève évaluera les autres groupes en complément de l'évaluation réalisée par l'enseignant.
- Critères : clarté, originalité, robustesse de la solution, qualité du code, pertinence des choix méthodologiques et organisation.

## Utilisation des LLMs et IA Symbolique

### Outils à disposition

Pour faciliter la réalisation du projet, vous aurez accès à plusieurs ressources avancées :

- **Plateforme Open-WebUI** : intégrant des modèles d'intelligence artificielle d'OpenAI et locaux très performants, ainsi que des plugins spécifiques et une base de connaissances complète alimentée par la bibliographie du cours.
- **Clés d'API OpenAI et locales** : mise à votre disposition pour exploiter pleinement les capacités des modèles GPT dans vos développements.
- **Notebook Agentique** : un notebook interactif permettant d'automatiser la création ou la finalisation de vos propres notebooks, facilitant ainsi la structuration et l'amélioration de vos solutions.
- **Bibliothèque Tweety** : une bibliothèque Java complète pour l'IA symbolique, intégrée via JPype, offrant de nombreux modules pour différentes logiques et raisonnements.

### Combinaison IA Générative et IA Symbolique

Le projet se concentre sur l'intégration de l'IA générative agentique orchestrée avec des techniques d'IA symbolique, notamment pour l'analyse argumentative. Cette approche hybride permet de combiner la flexibilité et la puissance des LLMs avec la rigueur et la formalisation des méthodes symboliques.

## Sujets de Projets

Les sujets proposés ci-dessous couvrent différents aspects de l'IA symbolique, avec un focus particulier sur l'argumentation et son intégration par l'IA générative agentique orchestrée. Chaque groupe devra choisir un sujet et contribuer à l'amélioration du projet global.

### Domaines Fondamentaux

#### Logiques Formelles et Argumentation

- **Intégration des logiques propositionnelles avancées** : Améliorer l'agent PL existant pour exploiter davantage les fonctionnalités du module `logics.pl` de Tweety, notamment les solveurs SAT (SAT4J interne ou solveurs externes comme Lingeling, CaDiCaL), la conversion DIMACS, et les opérations avancées sur les formules (DNF, CNF, simplification). Implémenter des requêtes plus sophistiquées comme la vérification de satisfiabilité, la recherche de modèles, et l'analyse d'implications logiques.

- **Logique du premier ordre (FOL)** : Développer un nouvel agent utilisant le module `logics.fol` de Tweety pour analyser des arguments plus complexes impliquant des quantificateurs et des prédicats. Cet agent pourrait traduire des phrases en formules FOL, définir des signatures avec types/sorts, constantes et prédicats, et utiliser des raisonneurs comme SimpleFolReasoner ou EFOLReasoner (avec intégration optionnelle d'EProver). Les défis incluent la gestion des variables liées et la traduction naturel-FOL.

- **Logique modale** : Créer un agent spécialisé utilisant le module `logics.ml` de Tweety pour raisonner sur des modalités comme la nécessité (`[]`), la possibilité (`<>`), les croyances ou les connaissances. Cet agent pourrait analyser des arguments impliquant des notions de possibilité, nécessité, obligation ou permission, en utilisant SimpleMlReasoner ou SPASSMlReasoner (avec intégration de SPASS). Les applications incluent l'analyse d'arguments déontiques, épistémiques ou temporels.

- **Logique de description (DL)** : Développer un agent utilisant le module `logics.dl` de Tweety pour modéliser des connaissances structurées sous forme de concepts, rôles et individus. Cet agent pourrait construire des TBox (axiomes terminologiques) et ABox (assertions sur les individus), et raisonner sur la subsomption, l'instanciation et la consistance. Applications possibles pour la modélisation d'ontologies argumentatives.

- **Formules booléennes quantifiées (QBF)** : Explorer l'utilisation du module `logics.qbf` de Tweety pour modéliser et résoudre des problèmes PSPACE-complets. Cet agent pourrait traiter des problèmes de planification conditionnelle, de jeux à deux joueurs, ou de vérification formelle qui dépassent la portée de SAT.

- **Logique conditionnelle (CL)** : Implémenter un agent utilisant le module `logics.cl` de Tweety pour raisonner sur des conditionnels de la forme "Si A est vrai, alors B est typiquement vrai". Applications pour le raisonnement non-monotone et la modélisation des défauts dans l'argumentation.

- **Cadres d'argumentation abstraits (Dung)** : Développer un agent utilisant le module `arg.dung` de Tweety pour modéliser et analyser des structures argumentatives abstraites. Cet agent pourrait construire des graphes d'attaque, calculer différentes sémantiques (admissible, complète, préférée, stable, fondée, CF2), et déterminer l'acceptabilité des arguments. Extensions possibles vers la génération et l'apprentissage de cadres.

- **Argumentation structurée (ASPIC+)** : Créer un agent utilisant le module `arg.aspic` de Tweety pour construire des arguments à partir de règles strictes et défaisables. Cet agent pourrait modéliser des bases de connaissances avec axiomes et règles, gérer les préférences entre règles, et analyser les attaques (rebutting, undercutting, undermining).

- **Programmation logique défaisable (DeLP)** : Implémenter un agent utilisant le module `arg.delp` de Tweety pour raisonner avec des règles strictes et défaisables dans un cadre de programmation logique. Applications pour la résolution de conflits et le raisonnement dialectique.

- **Argumentation basée sur les hypothèses (ABA)** : Développer un agent utilisant le module `arg.aba` de Tweety pour modéliser l'argumentation où certains littéraux sont désignés comme hypothèses. Cet agent pourrait analyser les attaques entre arguments dérivés de ces hypothèses et déterminer leur acceptabilité.

- **Argumentation déductive** : Créer un agent utilisant le module `arg.deductive` de Tweety pour construire des arguments comme des paires (Support, Conclusion) où le support est un sous-ensemble minimal et consistant de la base de connaissances qui implique logiquement la conclusion.

- **Answer Set Programming (ASP)** : Développer un agent utilisant le module `lp.asp` de Tweety pour modéliser et résoudre des problèmes combinatoires complexes. Cet agent pourrait intégrer Clingo pour le raisonnement ASP et l'appliquer à des problèmes d'argumentation.

#### Frameworks d'Argumentation Avancés

- **Abstract Dialectical Frameworks (ADF)** : Implémenter un agent utilisant le module `arg.adf` de Tweety pour modéliser des cadres où chaque argument a une condition d'acceptation exprimée comme une formule propositionnelle. Applications pour des structures argumentatives plus expressives que les AAF de Dung.

- **Frameworks bipolaires** : Développer un agent utilisant le module `arg.bipolar` de Tweety pour modéliser des cadres avec relations d'attaque et de support. Variantes possibles: EAF (support simple), PEAF (support probabiliste), Evidential AF, Necessity AF.

- **Frameworks pondérés (WAF)** : Créer un agent utilisant le module `arg.weighted` de Tweety pour modéliser des cadres où les attaques ont des poids/forces. Cet agent pourrait utiliser différents semi-anneaux (WeightedSemiring, FuzzySemiring, ProbabilisticSemiring) et raisonneurs pondérés.

- **Frameworks sociaux (SAF)** : Implémenter un agent utilisant le module `arg.social` de Tweety pour modéliser des cadres où les arguments reçoivent des votes (positifs/négatifs). Applications pour l'analyse d'arguments dans des contextes sociaux ou collaboratifs.

- **Set Argumentation Frameworks (SetAF)** : Développer un agent utilisant le module `arg.setaf` de Tweety pour modéliser des cadres où des ensembles d'arguments attaquent collectivement d'autres arguments.

- **Frameworks étendus (attaques sur attaques)** : Créer un agent utilisant le module `arg.extended` de Tweety pour modéliser des cadres où les arguments peuvent attaquer des attaques (EAF) ou récursivement des attaques sur des attaques (REAF).

- **Sémantiques basées sur le classement** : Implémenter un agent utilisant le module `arg.rankings` de Tweety pour établir un ordre entre les arguments (du plus acceptable au moins acceptable) plutôt qu'une simple acceptation/rejet. Approches possibles: Categorizer, Burden-Based, Discussion-Based, Tuples*, Strategy-Based, Counting, Propagation.

- **Argumentation probabiliste** : Développer un agent utilisant le module `arg.prob` de Tweety pour modéliser l'incertitude dans les cadres d'argumentation, soit sur l'existence des arguments/attaques, soit sur leur acceptabilité. Applications pour la prise de décision sous incertitude via les loteries d'argumentation.

#### Planification et Raisonnement

- **Intégration d'un planificateur symbolique** : Développer un agent capable de générer des plans d'action basés sur des objectifs argumentatifs, en explorant le module `action` de Tweety pour la modélisation des actions et la planification.

- **Logiques sociales et planification** : Explorer l'intégration du module `arg.social` de Tweety avec des techniques de planification pour modéliser des interactions argumentatives multi-agents, en utilisant la sémantique ISS (Iterated Schema Semantics) pour calculer des scores d'acceptabilité évolutifs.

#### Ingénierie des Connaissances

- **Intégration d'ontologies AIF.owl** : Développer un moteur sémantique basé sur l'ontologie AIF (Argument Interchange Format) pour structurer les arguments, en utilisant potentiellement le module `logics.dl` de Tweety pour la modélisation ontologique.

- **Classification des arguments fallacieux** : Corriger et intégrer l'ontologie du projet Argumentum pour la classification des sophismes, en exploitant les capacités de modélisation ontologique de Tweety.

- **Knowledge Graph argumentatif** : Remplacer la structure JSON actuelle de l'état partagé par un graphe de connaissances plus expressif et interrogeable, en s'inspirant des structures de graphe utilisées dans les différents frameworks d'argumentation de Tweety.

#### Maintenance de la Vérité

- **Intégration des modules de maintenance de la vérité** : Résoudre les problèmes d'import des modules `beliefdynamics` de Tweety et les intégrer au système. Ces modules permettent la révision de croyances (via des opérateurs comme LeviMultipleBaseRevisionOperator), la contraction (KernelContractionOperator), et la gestion des incohérences.

- **Révision de croyances multi-agents** : Développer un agent utilisant le module `beliefdynamics.mas` de Tweety pour modéliser la révision de croyances dans un contexte multi-agents, où chaque information est associée à un agent source et où un ordre de crédibilité existe entre les agents. Implémenter différents opérateurs de révision: CrMasRevisionWrapper (priorisé), CrMasSimpleRevisionOperator (non-priorisé), CrMasArgumentativeRevisionOperator (basé sur l'argumentation).

- **Mesures d'incohérence** : Intégrer les mesures d'incohérence de Tweety (`logics.pl.analysis`) pour quantifier le degré d'incohérence des bases de connaissances propositionnelles. Approches possibles: ContensionInconsistencyMeasure, FuzzyInconsistencyMeasure, DSumInconsistencyMeasure, DMaxInconsistencyMeasure, DHitInconsistencyMeasure.

- **Énumération de MUS (Minimal Unsatisfiable Subsets)** : Implémenter un agent capable d'identifier les sous-ensembles minimaux inconsistants d'une base de connaissances, en utilisant NaiveMusEnumerator ou MarcoMusEnumerator (avec intégration de MARCO).

- **MaxSAT pour la résolution d'incohérences** : Développer un agent utilisant les capacités MaxSAT de Tweety (via OpenWboSolver) pour trouver des assignations qui satisfont toutes les clauses "dures" et minimisent le coût des clauses "molles" violées, permettant ainsi de résoudre des incohérences de manière optimale.

#### Smart Contracts

- **Formalisation de contrats argumentatifs** : Explorer l'utilisation de smart contracts pour formaliser et exécuter des protocoles d'argumentation, en s'appuyant sur les différents formalismes d'argumentation disponibles dans Tweety.

- **Vérification formelle d'arguments** : Développer des méthodes de vérification formelle pour garantir la validité des arguments dans un contexte contractuel, en utilisant potentiellement les capacités QBF ou FOL de Tweety.

### Développements Transversaux

#### Gestion des Sources

- **Amélioration du moteur d'extraction** : Perfectionner le système actuel qui combine paramétrage d'extraits et sources correspondantes.
- **Support de formats étendus** : Étendre les capacités du moteur d'extraction pour supporter davantage de formats de fichiers et de sources web.
- **Sécurisation des données** : Améliorer le système de chiffrement des sources et configurations d'extraits pour garantir la confidentialité.

#### Moteur Agentique

- **Abstraction du moteur agentique** : Créer une couche d'abstraction permettant d'utiliser différents frameworks agentiques (au-delà de Semantic Kernel).
- **Orchestration avancée** : Développer des stratégies d'orchestration plus sophistiquées pour la collaboration entre agents.
- **Mécanismes de résolution de conflits** : Implémenter des méthodes pour résoudre les désaccords entre agents lors de l'analyse argumentative.

#### Intégration MCP (Model Context Protocol)

- **Développement d'un serveur MCP** : Publier le travail collectif sous forme d'un serveur MCP utilisable dans des applications comme Roo, Claude Desktop ou Semantic Kernel.
- **Outils MCP pour l'analyse argumentative** : Créer des outils MCP spécifiques pour l'analyse et la manipulation d'arguments.

#### Agents Spécialistes

- **Agents de logique formelle** : Développer de nouveaux agents spécialisés utilisant différentes parties de Tweety.
- **Agent de détection de sophismes** : Améliorer la détection et la classification des sophismes dans les textes.
- **Agent de génération de contre-arguments** : Créer un agent capable de générer des contre-arguments pertinents.

#### Indexation Sémantique

- **Index sémantique d'arguments** : Indexer les définitions, exemples et instances d'arguments fallacieux pour permettre des recherches par proximité sémantique.
- **Vecteurs de types d'arguments** : Définir par assemblage des vecteurs de types d'arguments fallacieux pour faciliter la découverte de nouvelles instances.

#### Automatisation

- **Automatisation de l'analyse** : Développer des outils pour lancer l'équivalent du notebook d'analyse dans le cadre d'automates longs sur des corpus.
- **Pipeline de traitement** : Créer un pipeline complet pour l'ingestion, l'analyse et la visualisation des résultats d'analyse argumentative.

### Projets Intégrateurs

- **Système de débat assisté par IA** : Développer une application complète permettant à des utilisateurs de débattre avec l'assistance d'agents IA qui analysent et améliorent leurs arguments.
- **Plateforme d'éducation à l'argumentation** : Créer un outil éducatif pour enseigner les principes de l'argumentation et aider à identifier les sophismes.
- **Système d'aide à la décision argumentative** : Développer un système qui aide à la prise de décision en analysant et évaluant les arguments pour et contre différentes options.

## Ressources et Documentation

Pour vous aider dans la réalisation de votre projet, vous trouverez dans ce dépôt :

- Des README détaillés pour chaque composant du système
- Des notebooks explicatifs et interactifs
- Des exemples d'utilisation des différentes bibliothèques
- Une documentation sur l'architecture du système

N'hésitez pas à explorer les différents répertoires du projet pour mieux comprendre son fonctionnement et identifier les opportunités d'amélioration.
