# Guide de démarrage des projets étudiants "argumentiation_analysis"

## 0. Support et Accompagnement (NOUVEAU)

Pour des conseils, la liste des problèmes connus et des ressources centralisées pour vous aider durant votre projet, consultez :

- **Guide d'Accompagnement des Étudiants** : [`projets/ACCOMPAGNEMENT_ETUDIANTS.md`](projets/ACCOMPAGNEMENT_ETUDIANTS.md)

---
> **NOUVEAU : Pour un démarrage rapide et une vue d'ensemble, consultez notre [Synthèse d'Accueil pour les Étudiants](projets/ACCUEIL_ETUDIANTS_SYNTHESE.md) !**

Bienvenue dans le projet "argumentiation_analysis" ! Ce document a pour but de vous aider à naviguer dans les ressources disponibles et à choisir votre sujet de projet.

## 1. Comprendre le Projet Global

Avant de plonger dans les sujets spécifiques, nous vous recommandons de lire attentivement le message d'annonce qui détaille les objectifs pédagogiques, les modalités de travail, les livrables attendus et les critères d'évaluation :

- **Message d'annonce aux étudiants** : [`projets/message_annonce_etudiants.md`](projets/message_annonce_etudiants.md)

## 2. Explorer les Sujets de Projets

Les sujets de projets sont organisés en trois grandes catégories. Chaque catégorie est détaillée dans un document spécifique :

- **Fondements théoriques et techniques** : Explorez les aspects formels, logiques et théoriques de l'argumentation.
  - Détails : [`projets/fondements_theoriques.md`](projets/fondements_theoriques.md)

- **Développement système et infrastructure** : Travaillez sur l'architecture, l'orchestration et les composants techniques du système.
  - Détails : [`projets/developpement_systeme.md`](projets/developpement_systeme.md)

- **Expérience utilisateur et applications** : Concentrez-vous sur les interfaces, les visualisations et les cas d'usage concrets.
  - Détails : [`projets/experience_utilisateur.md`](projets/experience_utilisateur.md)

Pour une **synthèse thématique** qui regroupe les projets par grands domaines et met en évidence les synergies possibles, consultez :
- **Synthèse Thématique des Projets** : [`projets/SYNTHESE_THEMATIQUE_PROJETS.md`](projets/SYNTHESE_THEMATIQUE_PROJETS.md)

Pour une vue d'ensemble de tous les sujets avec leur structure standardisée (contexte, objectifs, technologies, difficulté, etc.), consultez :

- **Sujets de Projets Détaillés** : [`projets/sujets_projets_detailles.md`](projets/sujets_projets_detailles.md)

## 3. Ressources Techniques : Exemples de Code et Tests

Pour vous aider à démarrer techniquement et à comprendre le fonctionnement du projet, de nombreuses ressources sont à votre disposition. Celles-ci incluent des scripts d'exemple, des notebooks didactiques, des données de test, ainsi que des tests unitaires et d'intégration qui illustrent l'utilisation des différents composants du projet.

- **Exemples de scripts d'intégration et d'utilisation d'API** :
  - Explorez les scripts dans [`examples/logic_agents/`](examples/logic_agents/) (par exemple, [`api_integration_example.py`](examples/logic_agents/api_integration_example.py:0)) pour voir comment interagir avec les agents logiques.
- **Scripts de démonstration** :
  - Les scripts situés dans [`examples/scripts_demonstration/`](examples/scripts_demonstration/) (comme [`demo_tweety_interaction_simple.py`](examples/scripts_demonstration/demo_tweety_interaction_simple.py:0)) offrent des démonstrations concrètes de fonctionnalités spécifiques.
- **Notebooks Jupyter didactiques** :
  - Pour une approche plus interactive, consultez les notebooks dans [`examples/notebooks/`](examples/notebooks/) (par exemple, [`api_logic_tutorial.ipynb`](examples/notebooks/api_logic_tutorial.ipynb:0)) qui vous guideront à travers divers aspects du projet.
- **Données d'exemple** :
  - Des jeux de données pour tester et expérimenter sont disponibles dans [`examples/test_data/`](examples/test_data/).
- **Scripts d'exécution et de test** :
  - Les répertoires [`scripts/execution/`](scripts/execution/) et [`scripts/testing/`](scripts/testing/) contiennent des scripts utiles pour exécuter des parties du projet ou des batteries de tests.
- **Tests unitaires** :
  - Pour comprendre comment les composants individuels sont testés et comment les utiliser, parcourez les tests unitaires dans [`tests/unit/`](tests/unit/) (par exemple, [`tests/unit/project_core/utils/test_file_utils.py`](tests/unit/project_core/utils/test_file_utils.py:0)).
- **Tests d'intégration** :
  - Les tests d'intégration dans [`tests/integration/`](tests/integration/) (comme [`tests/integration/test_logic_agents_integration.py`](tests/integration/test_logic_agents_integration.py:0) et le répertoire [`tests/integration/jpype_tweety/`](tests/integration/jpype_tweety/)) montrent comment les différentes parties du projet fonctionnent ensemble.
- **Exemples spécifiques à TweetyProject (orientés fondements théoriques)** :
  - Pour les projets touchant directement à la bibliothèque TweetyProject, consultez : [`projets/exemples_tweety_par_projet.md`](projets/exemples_tweety_par_projet.md).

## 4. Démarrage Rapide

Consultez la section "Démarrage rapide" du [message d'annonce](./projets/message_annonce_etudiants.md#démarrage-rapide) pour les étapes initiales (fork, clone, installation, etc.).

Nous vous souhaitons bonne chance dans vos projets !