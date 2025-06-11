# Tests d'Intégration : JPype et Tweety

## Objectif

Ce répertoire contient une suite de tests d'intégration conçus pour valider la communication et l'interopérabilité entre le code Python et la bibliothèque de raisonnement formel **Tweety**, qui est écrite en Java. L'intégration est réalisée à l'aide de la bibliothèque **JPype**, qui permet d'instancier et d'interagir avec des objets de la Machine Virtuelle Java (JVM) directement depuis Python.

L'objectif principal est de s'assurer que les fonctionnalités logiques complexes de Tweety (manipulation de syntaxe, raisonnement, argumentation, etc.) peuvent être pilotées de manière fiable depuis Python, garantissant ainsi que la couche d'intégration est stable et correcte.

## Points d'Intégration Testés

Les tests couvrent plusieurs points de contact critiques entre Python et la JVM via JPype :

1.  **Cycle de Vie de la JVM :**
    *   Vérification du démarrage et de l'arrêt contrôlés de la JVM dans un environnement de test `pytest`.
    *   Tests de stabilité pour isoler les problèmes potentiels liés à la JVM elle-même ([`test_jvm_stability.py`](tests/integration/jpype_tweety/test_jvm_stability.py:1), [`test_minimal_jvm_startup.py`](tests/integration/jpype_tweety/test_minimal_jvm_startup.py:1)).

2.  **Manipulation de la Syntaxe Logique :**
    *   **Logique Propositionnelle :** Création, parsing et manipulation de formules, de bases de croyances (`PlBeliefSet`), et d'opérations ensemblistes sur les théories ([`test_logic_operations.py`](tests/integration/jpype_tweety/test_logic_operations.py:1), [`test_theory_operations.py`](tests/integration/jpype_tweety/test_theory_operations.py:1)).
    *   **Frameworks d'Argumentation :** Construction de graphes d'argumentation de Dung (`DungTheory`) par l'ajout d'arguments et de relations d'attaque ([`test_argumentation_syntax.py`](tests/integration/jpype_tweety/test_argumentation_syntax.py:1)).
    *   **Logique Booléenne Quantifiée (QBF) :** Parsing et création programmatique de formules QBF, y compris des structures imbriquées ([`test_qbf.py`](tests/integration/jpype_tweety/test_qbf.py:1)).

3.  **Validation du Raisonnement (Reasoning) :**
    *   **Sémantiques d'Argumentation :** Calcul des différentes sémantiques d'extensions (préférée, fondée, stable, etc.) sur des graphes d'argumentation pour valider les `AFReasoner` ([`test_argumentation_frameworks.py`](tests/integration/jpype_tweety/test_argumentation_frameworks.py:1)).
    *   **Raisonnement Avancé :** Intégration avec des solveurs externes pour des logiques plus complexes.
        *   **Programmation Logique (ASP) :** Utilisation de **Clingo** pour vérifier la cohérence et l'inférence sur des programmes logiques ([`test_advanced_reasoning.py`](tests/integration/jpype_tweety/test_advanced_reasoning.py:1)).
        *   **Logique Probabiliste :** Utilisation de **ProbLog** (via **Octave**) pour des requêtes de probabilité ([`test_advanced_reasoning.py`](tests/integration/jpype_tweety/test_advanced_reasoning.py:1)).
    *   **Révision des Croyances :** Test des opérateurs de l'AGM (expansion, contraction, révision) sur des bases de croyances ([`test_belief_revision.py`](tests/integration/jpype_tweety/test_belief_revision.py:1)).

4.  **Systèmes d'Agents et Dialogues :**
    *   Création d'agents logiques, configuration de leurs bases de connaissances et de leurs stratégies.
    *   Mise en place et exécution de protocoles de dialogue (ex: persuasion) entre agents ([`test_agent_integration.py`](tests/integration/jpype_tweety/test_agent_integration.py:1), [`test_dialogical_argumentation.py`](tests/integration/jpype_tweety/test_dialogical_argumentation.py:1)).

## Prérequis et Dépendances

L'exécution de ces tests nécessite la configuration d'un environnement spécifique :

*   **JVM :** Une Machine Virtuelle Java (JDK 17) est requise. Les tests sont configurés pour utiliser une version portable située dans le répertoire `libs/portable_jdk` afin de garantir la cohérence de l'environnement.
*   **Bibliothèques Tweety :** Les fichiers `.jar` de Tweety et de ses dépendances doivent être accessibles et sont inclus dans le `classpath` de la JVM lors de son démarrage par les fixtures de test.
*   **Solveurs Externes :** Certains tests de raisonnement avancé dépendent de solveurs externes qui doivent être installés et accessibles :
    *   **Clingo :** Nécessaire pour les tests de programmation logique (ASP). Le chemin vers l'exécutable peut être codé en dur dans les tests ou doit se trouver dans le `PATH` du système.
    *   **Octave :** Nécessaire pour certains tests de logique probabiliste. Une installation portable est gérée par le script `tests/support/portable_octave_installer.py`.
*   **Données de Test :** Les théories logiques, programmes et autres données d'entrée sont stockés dans le sous-répertoire [`test_data/`](tests/integration/jpype_tweety/test_data/README.md). Ce répertoire contient son propre `README.md` pour plus de détails.
