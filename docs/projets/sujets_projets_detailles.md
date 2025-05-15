# Sujets de Projets Détaillés

Les sujets proposés ci-dessous couvrent différents aspects de l'IA symbolique, avec un focus particulier sur l'argumentation et son intégration par l'IA générative agentique orchestrée. Chaque groupe devra choisir un sujet et contribuer à l'amélioration du projet global dans un délai d'un mois.

Plusieurs projets proposés s'appuient sur **TweetyProject**, une bibliothèque Java open-source pour l'intelligence artificielle symbolique. TweetyProject offre un ensemble riche de modules pour la représentation de connaissances et l'argumentation computationnelle, permettant aux étudiants de travailler avec des formalismes logiques variés (propositionnelle, premier ordre, description, modale) et des frameworks d'argumentation (Dung, ASPIC+, ABA, etc.) sans avoir à les implémenter de zéro. L'utilisation de TweetyProject via JPype permet de combiner la puissance des implémentations Java avec la flexibilité de Python pour le prototypage rapide et l'expérimentation.

## Organisation des Sujets

Les projets sont organisés en trois catégories principales :
1. **[Fondements théoriques et techniques](./fondements_theoriques.md)** : Projets centrés sur les aspects formels, logiques et théoriques de l'argumentation
2. **[Développement système et infrastructure](./developpement_systeme.md)** : Projets axés sur l'architecture, l'orchestration et les composants techniques
3. **[Expérience utilisateur et applications](./experience_utilisateur.md)** : Projets orientés vers les interfaces, visualisations et cas d'usage concrets

Ces catégories se déclinent en 16 domaines spécifiques :
1. Logiques formelles et raisonnement
2. Frameworks d'argumentation
3. Taxonomies et classification
4. Maintenance de la vérité et révision de croyances
5. Planification et vérification formelle
6. Architecture et orchestration
7. Gestion des sources et données
8. Moteur agentique et agents spécialistes
9. Indexation sémantique
10. Automatisation et intégration MCP
11. Interfaces utilisateurs
12. Projets intégrateurs
13. Ingénierie des connaissances
14. Smart Contracts
15. Conduite de projet
16. Développement d'interfaces avancées

Chaque sujet est présenté avec une structure standardisée :
- **Contexte** : Présentation du domaine et de son importance
- **Objectifs** : Ce que le projet vise à accomplir
- **Technologies clés** : Outils, frameworks et concepts essentiels
- **Niveau de difficulté** : ⭐ (Accessible) à ⭐⭐⭐⭐ (Avancé)
- **Estimation d'effort** : Temps de développement estimé en semaines-personnes (maximum 4 semaines)
- **Interdépendances** : Liens avec d'autres sujets de projets
- **Références** : Sources et documentation pour approfondir
- **Livrables attendus** : Résultats concrets à produire

## Catégories de projets

### [1. Fondements théoriques et techniques](./fondements_theoriques.md)

Cette catégorie comprend les projets centrés sur les aspects formels, logiques et théoriques de l'argumentation, notamment :
- Logiques formelles et raisonnement
- Frameworks d'argumentation
- Taxonomies et classification
- Maintenance de la vérité et révision de croyances
- Planification et vérification formelle

[Voir les projets de fondements théoriques et techniques](./fondements_theoriques.md)

### [2. Développement système et infrastructure](./developpement_systeme.md)

Cette catégorie comprend les projets axés sur l'architecture, l'orchestration et les composants techniques, notamment :
- Architecture et orchestration
- Gestion des sources et données
- Moteur agentique et agents spécialistes
- Indexation sémantique
- Automatisation et intégration MCP

[Voir les projets de développement système et infrastructure](./developpement_systeme.md)

### [3. Expérience utilisateur et applications](./experience_utilisateur.md)

Cette catégorie comprend les projets orientés vers les interfaces, visualisations et cas d'usage concrets, notamment :
- Interfaces utilisateurs
- Projets intégrateurs

[Voir les projets d'expérience utilisateur et applications](./experience_utilisateur.md)

## Ressources générales sur TweetyProject

### Documentation et tutoriels
- **Site officiel** : [TweetyProject](https://tweetyproject.org/) - Documentation, téléchargements et exemples
- **GitHub** : [TweetyProjectTeam/TweetyProject](https://github.com/TweetyProjectTeam/TweetyProject) - Code source, issues et contributions
- **Tutoriel JPype** : Guide d'utilisation de Tweety avec Python via JPype (voir notebook Tweety.ipynb)

### Modules principaux
- **Logiques formelles** :
  * `logics.pl` - Logique propositionnelle, solveurs SAT, analyse d'incohérence
  * `logics.fol` - Logique du premier ordre, signatures, quantificateurs
  * `logics.ml` - Logique modale, opérateurs de nécessité et possibilité
  * `logics.dl` - Logique de description, concepts, rôles, TBox/ABox
  * `logics.cl` - Logique conditionnelle, fonctions de classement (OCF)
  * `logics.qbf` - Formules booléennes quantifiées
  * `logics.pcl` - Logique conditionnelle probabiliste
  * `logics.rcl` - Logique conditionnelle relationnelle
  * `logics.mln` - Markov Logic Networks
  * `logics.bpm` - Business Process Management

- **Argumentation computationnelle** :
  * `arg.dung` - Frameworks d'argumentation abstraite de Dung
  * `arg.bipolar` - Frameworks d'argumentation bipolaire (support/attaque)
  * `arg.weighted` - Frameworks d'argumentation pondérée
  * `arg.social` - Frameworks d'argumentation sociale
  * `arg.prob` - Argumentation probabiliste
  * `arg.aspic` - Argumentation structurée ASPIC+
  * `arg.aba` - Argumentation basée sur les hypothèses (ABA)
  * `arg.delp` - Defeasible Logic Programming (DeLP)
  * `arg.deductive` - Argumentation déductive
  * `arg.adf` - Abstract Dialectical Frameworks
  * `arg.setaf` - Set Argumentation Frameworks
  * `arg.rankings` - Sémantiques basées sur le classement
  * `arg.extended` - Frameworks étendus (attaques sur attaques)

- **Autres modules** :
  * `beliefdynamics` - Révision de croyances multi-agents
  * `agents` - Modélisation d'agents et dialogues
  * `action` - Planification et langages d'action
  * `math` - Utilitaires mathématiques
  * `commons` - Classes et interfaces communes

### Configuration et utilisation
- **Prérequis** : Java Development Kit (JDK 11+), Python 3.x, JPype
- **Installation** : Téléchargement des JARs Tweety et configuration du classpath
- **Intégration avec outils externes** : Solveurs SAT (Lingeling, CaDiCaL), prouveurs FOL (EProver, SPASS), solveurs ASP (Clingo)

### Exemples d'applications
- Analyse formelle d'arguments et détection de sophismes
- Modélisation de débats et évaluation de la qualité argumentative
- Révision de croyances et gestion de l'incohérence
- Raisonnement avec incertitude et information incomplète
- Aide à la décision basée sur l'argumentation