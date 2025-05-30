# Tests d'Intégration

Ce répertoire contient les tests d'intégration pour le projet d'analyse d'argumentation.

## Objectif

Les tests d'intégration visent à vérifier que les différents composants du système interagissent correctement ensemble. Contrairement aux tests unitaires qui se concentrent sur des modules isolés (souvent avec des mocks), les tests d'intégration utilisent autant que possible l'environnement réel et les dépendances réelles, notamment la JVM et les bibliothèques Tweety.

## Lancement des tests

Pour exécuter uniquement les tests d'intégration, utilisez le marqueur `integration` défini dans `pytest.ini`:

```bash
pytest -m integration
```

Vous pouvez également combiner ce marqueur avec d'autres options de Pytest, par exemple pour plus de verbosité :

```bash
pytest -m integration -v
```

## Gestion de la JVM

La configuration et l'initialisation de la Java Virtual Machine (JVM) pour ces tests sont gérées par le script [`argumentation_analysis/core/jvm_setup.py`](../../argumentation_analysis/core/jvm_setup.py). Ce script s'occupe de :

1.  **Détection/Configuration de `JAVA_HOME`** : Il tente de trouver une installation Java compatible (version 15 ou supérieure) ou utilise un JDK portable téléchargé automatiquement si nécessaire.
2.  **Gestion du `CLASSPATH`** : Il construit le `CLASSPATH` en incluant les JARs du projet (Tweety et autres dépendances Java) situés principalement dans le répertoire `libs/` à la racine du projet, ainsi que les JARs potentiels dans `argumentation_analysis/tests/resources/libs/`.
3.  **Bibliothèques natives** : Il configure `java.library.path` pour les solveurs natifs si présents.
4.  **Options JVM** : Il applique des options de mémoire par défaut (`-Xms256m -Xmx512m`).

Une fixture Pytest de session, `integration_jvm`, définie dans [`tests/integration/conftest.py`](conftest.py), s'assure que la fonction `initialize_jvm()` du script ci-dessus est appelée avant l'exécution des tests d'intégration. Cela garantit que la JVM est démarrée et correctement configurée.

**Considérations importantes :**

*   **Pas de mocks JPype** : Contrairement à certains tests unitaires, les tests d'intégration ne doivent PAS utiliser de mocks pour `jpype` ou la JVM. Ils doivent interagir avec la vraie JVM.
*   **Dépendances** : Assurez-vous que toutes les dépendances Java nécessaires sont présentes dans les répertoires de bibliothèques configurés (`libs/` ou `argumentation_analysis/tests/resources/libs/`). Le script `jvm_setup.py` tente de télécharger les JARs Tweety manquants.
*   **Temps d'exécution** : Les tests d'intégration peuvent être plus longs à exécuter que les tests unitaires en raison du démarrage de la JVM et de l'utilisation de composants réels.

## Ajout de nouveaux tests

Placez les nouveaux fichiers de test d'intégration directement dans ce répertoire (`tests/integration/`) ou dans des sous-répertoires si une organisation plus fine est nécessaire. Assurez-vous que les fonctions de test sont marquées avec `@pytest.mark.integration` pour qu'elles soient incluses lors de l'exécution spécifique des tests d'intégration.