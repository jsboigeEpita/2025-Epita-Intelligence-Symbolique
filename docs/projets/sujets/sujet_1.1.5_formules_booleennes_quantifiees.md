# 1.1.5 Analyse et Résolution de Formules Booléennes Quantifiées (QBF)

**Étudiants :** À assigner
**Niveau :** Avancé
**Prérequis :** Logique propositionnelle, Bases de la théorie de la complexité, Programmation Python, Connaissance de TweetyProject (ou volonté de l'acquérir).

## Table des Matières

- [1.1.5 Analyse et Résolution de Formules Booléennes Quantifiées (QBF)](#115-analyse-et-résolution-de-formules-booléennes-quantifiées-qbf)
  - [Table des Matières](#table-des-matières)
  - [1. Introduction aux Formules Booléennes Quantifiées (QBF)](#1-introduction-aux-formules-booléennes-quantifiées-qbf)
  - [2. TweetyProject et les QBF](#2-tweetyproject-et-les-qbf)
  - [3. Objectifs du Projet : Agent Spécialiste QBF](#3-objectifs-du-projet--agent-spécialiste-qbf)
  - [4. Implémentation avec Python et `jpype`](#4-implémentation-avec-python-et-jpype)
  - [5. Tests Unitaires et Validation](#5-tests-unitaires-et-validation)
  - [6. Livrables Attendus](#6-livrables-attendus)
  - [7. Défis et Pistes d'Exploration (Optionnel)](#7-défis-et-pistes-dexploration-optionnel)
  - [8. Conseils de Démarrage](#8-conseils-de-démarrage)

## 1. Introduction aux Formules Booléennes Quantifiées (QBF)

*   **Définition des QBF :**
    *   Syntaxe : Extension de la logique propositionnelle avec des quantificateurs universels (∀) et existentiels (∃) sur les variables booléennes.
    *   Sémantique : Interprétation des formules quantifiées, notion de vérité d'une QBF.
*   **Importance et applications :**
    *   Planification (ex: planification contingente).
    *   Vérification formelle de systèmes matériels et logiciels.
    *   Intelligence Artificielle (représentation de connaissances, raisonnement).
*   **Problème de la décision QBF (QSAT) :**
    *   Déterminer si une QBF close (sans variables libres) est vraie.
    *   Complexité : QSAT est le problème prototypique pour la classe de complexité PSPACE-complet, ce qui le rend plus difficile que SAT (NP-complet).

## 2. TweetyProject et les QBF

*   **Fonctionnalités de TweetyProject pour les QBF :**
    *   TweetyProject offre des structures de données pour représenter les QBF.
    *   Il peut s'interfacer avec des solveurs QBF externes ou intégrés (à vérifier spécifiquement dans la version actuelle de Tweety).
    *   Capacité à manipuler, analyser et potentiellement transformer des QBF.
*   **Rappel sur `jpype` :**
    *   Le projet utilise la bibliothèque `jpype` pour permettre au code Python d'interagir avec les bibliothèques Java de TweetyProject.
    *   Ceci est crucial pour accéder aux fonctionnalités QBF de TweetyProject depuis l'agent Python à développer.

## 3. Objectifs du Projet : Agent Spécialiste QBF

*   **Développement d'un agent spécialiste :**
    *   L'objectif principal est de créer un agent en Python capable d'analyser et de résoudre des Formules Booléennes Quantifiées.
    *   Cet agent doit servir d'interface Pythonique aux capacités de TweetyProject relatives aux QBF.
*   **Fonctionnalités attendues de l'agent :**
    *   **Prise en entrée d'une QBF :**
        *   Support du format DIMACS (standard pour les solveurs QBF).
        *   Support du format symbolique interne de TweetyProject.
    *   **Validation de la syntaxe :** Vérifier si la formule fournie est bien formée.
    *   **Détermination de la satisfiabilité :** Indiquer si la QBF est vraie ou fausse (truth value).
    *   **Extraction de modèles ou de certificats :** Si le solveur sous-jacent le permet, extraire un modèle (assignation des variables existentielles) pour une QBF vraie, ou un certificat de fausseté.
    *   **Transformations de formules (potentiellement) :**
        *   Mise en forme prénexe.
        *   Conversion en Forme Normale Conjonctive (CNF) quantifiée (QCNF).

## 4. Implémentation avec Python et `jpype`

*   **Exemples de Code Clairs :**
    *   Fournir des snippets de code Python illustrant comment utiliser les classes et méthodes QBF de TweetyProject via `jpype`.
    *   **Instanciation d'une formule QBF :**
        ```python
        from jpype import JClass

        # Initialisation de JPype (doit être fait une seule fois)
        # import jpype.runtime
        # if not jpype.runtime.isStarted():
        #     jpype.startJVM(classpath=['path/to/tweety/libs/*']) # Adapter le classpath

        QbfFormula = JClass("org.tweetyproject.logics.qbf.syntax.QbfFormula")
        QuantifiedFormula = JClass("org.tweetyproject.logics.qbf.syntax.QuantifiedFormula")
        Quantifier = JClass("org.tweetyproject.logics.qbf.syntax.Quantifier")
        Proposition = JClass("org.tweetyproject.logics.propositional.syntax.Proposition")
        Conjunction = JClass("org.tweetyproject.logics.propositional.syntax.Conjunction")
        Disjunction = JClass("org.tweetyproject.logics.propositional.syntax.Disjunction")
        Negation = JClass("org.tweetyproject.logics.propositional.syntax.Negation")

        # Exemple: ∃x ∀y (x ∧ ¬y)
        x = Proposition("x")
        y = Proposition("y")

        # (x ∧ ¬y)
        matrix = Conjunction(x, Negation(y))

        # ∀y (x ∧ ¬y)
        formula_forall_y = QuantifiedFormula(Quantifier.FORALL, y, matrix)

        # ∃x ∀y (x ∧ ¬y)
        qbf_formula_exists_x = QuantifiedFormula(Quantifier.EXISTS, x, formula_forall_y)

        print(f"Formule QBF construite: {qbf_formula_exists_x}")
        ```
    *   **Appel d'un solveur QBF :**
        ```python
        # Supposons l'existence d'une classe SolverWrapper dans TweetyProject
        # QbfSolver = JClass("org.tweetyproject.logics.qbf.solver.SomeQbfSolverWrapper")
        # solver = QbfSolver() # Ou une factory pour obtenir un solveur
        # result = solver.isSatisfiable(qbf_formula_exists_x)
        # print(f"La formule est satisfiable: {result}")

        # NOTE: Le code ci-dessus est illustratif.
        # L'étudiant devra rechercher les classes exactes et les méthodes
        # pour l'interaction avec les solveurs QBF dans TweetyProject.
        # Se référer à la documentation de TweetyProject et aux tests existants.
        ```
    *   **Récupération et interprétation des résultats :**
        ```python
        # if result:
        #     # Tenter d'extraire un modèle si possible
        #     model = solver.getModel(qbf_formula_exists_x) # Méthode hypothétique
        #     if model:
        #         print(f"Modèle trouvé: {model}")
        # else:
        #     # Tenter d'extraire un certificat si possible
        #     certificate = solver.getCertificate(qbf_formula_exists_x) # Méthode hypothétique
        #     if certificate:
        #         print(f"Certificat de fausseté: {certificate}")
        ```
*   **Gestion de la JVM `jpype` :**
    *   Rappeler l'importance de démarrer et d'arrêter correctement la JVM via `jpype` pour éviter les fuites de ressources ou les erreurs.
    *   Typiquement, `jpype.startJVM()` au début et `jpype.shutdownJVM()` à la fin, si l'application n'est pas un simple script.
*   **Référence aux tests unitaires existants :**
    *   Le fichier [`tests/integration/jpype_tweety/test_qbf.py`](tests/integration/jpype_tweety/test_qbf.py) contient des exemples concrets d'utilisation des fonctionnalités QBF de TweetyProject via `jpype`.
    *   Encourager les étudiants à étudier ce fichier pour comprendre comment interagir avec les classes Java, instancier des formules, et potentiellement appeler des solveurs.

## 5. Tests Unitaires et Validation

*   **Impératif des tests unitaires :**
    *   Souligner que le développement d'une suite de tests unitaires robuste est crucial.
    *   Ces tests valideront non seulement la logique de l'agent spécialiste mais aussi l'exactitude du portage `jpype` des fonctionnalités QBF.
*   **Couverture des tests :**
    *   Les tests devront couvrir une variété de formules QBF :
        *   Formules satisfiables.
        *   Formules insatisfiables.
        *   Formules avec différents niveaux d'alternance de quantificateurs (ex: ∃∀, ∀∃, ∃∀∃).
        *   Cas limites et formules complexes.
*   **Sources d'exemples :**
    *   Encourager l'utilisation d'exemples de QBF issus de la littérature scientifique.
    *   Explorer le dépôt de TweetyProject pour des exemples de tests ou des benchmarks QBF.

## 6. Livrables Attendus

*   **L'agent spécialiste QBF :** Un module Python fonctionnel et bien structuré.
*   **Documentation de l'agent :**
    *   Une API claire décrivant comment utiliser l'agent.
    *   Des exemples d'utilisation.
*   **Suite de tests unitaires :** Complète, avec une bonne couverture, et tous les tests passant.
*   **Rapport de projet :**
    *   Description de la conception de l'agent.
    *   Choix d'implémentation et justifications.
    *   Résultats des tests et analyse des performances (si pertinent).
    *   Difficultés rencontrées et solutions apportées.

## 7. Défis et Pistes d'Exploration (Optionnel)

*   **Gestion des performances :**
    *   Comment l'agent se comporte-t-il avec des formules QBF volumineuses ou complexes ?
    *   Optimisation des appels `jpype` si nécessaire.
*   **Interface avec d'autres agents :**
    *   Explorer la possibilité pour l'agent QBF d'interagir avec d'autres agents, par exemple un agent de planification qui générerait des QBF à résoudre.
*   **Visualisation :**
    *   Développer des outils simples pour visualiser la structure des formules QBF.
    *   Potentiellement, visualiser certaines étapes du processus de résolution (si le solveur expose ces informations).

## 8. Conseils de Démarrage

*   **Documentation TweetyProject :** Commencer par se familiariser en profondeur avec la section QBF de la documentation de TweetyProject.
*   **Étude des exemples existants :**
    *   Analyser attentivement les exemples de code et les tests unitaires fournis dans le projet, notamment dans le répertoire [`tests/integration/jpype_tweety/`](tests/integration/jpype_tweety/).
    *   Le fichier [`tests/integration/jpype_tweety/test_qbf.py`](tests/integration/jpype_tweety/test_qbf.py) est une ressource clé.
*   **Approche itérative :**
    *   Commencer par implémenter les fonctionnalités de base (ex: instanciation d'une formule simple, appel à un solveur pour une formule triviale).
    *   Ajouter progressivement des fonctionnalités plus complexes et les tests correspondants.
*   **Environnement de développement :**
    *   Il est conseillé de démarrer le développement de l'agent dans un dossier de projet dédié, avec son propre environnement virtuel Python pour gérer les dépendances.