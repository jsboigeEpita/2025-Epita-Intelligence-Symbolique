# Tests Unitaires pour la Configuration des Services

## Objectif

Ce répertoire contient les tests unitaires pour les modules chargés de la configuration et de l'initialisation des services fondamentaux nécessaires à l'analyse d'argumentation. Ces services incluent la Machine Virtuelle Java (JVM) et le service de modèle de langage (LLM).

L'objectif est de garantir que la séquence d'initialisation est robuste, gère correctement les dépendances externes et les configurations, et se comporte de manière prévisible en cas de succès ou d'échec d'une des étapes.

## Fonctionnalités Testées

### `analysis_services`

-   **Orchestration de l'Initialisation (`initialize_analysis_services`)** :
    -   **Chargement de l'Environnement** : Vérifie que la fonction tente de trouver et de charger les variables d'environnement à partir d'un fichier `.env`.
    -   **Initialisation de la JVM** : Valide que la fonction `initialize_jvm` est appelée avec le chemin correct vers le répertoire des bibliothèques (`LIBS_DIR`). Teste le comportement lorsque ce chemin est fourni via la configuration ou importé depuis une constante du projet.
    -   **Création du Service LLM** : Valide que la fonction `create_llm_service` est appelée pour instancier le client du modèle de langage.
    -   **Agrégation des Services** : S'assure que les services initialisés (ou leur état) sont correctement retournés dans un dictionnaire.
    -   **Gestion des Échecs** :
        -   Teste le cas où l'initialisation de la JVM échoue (la fonction doit continuer et retourner un état `jvm_ready: False`).
        -   Teste les cas où la création du service LLM échoue, que ce soit en retournant `None` ou en levant une exception (le service doit être `None` dans le dictionnaire final et une erreur doit être journalisée).
        -   Valide la gestion d'un chemin `LIBS_DIR` non configuré.

## Dépendances Clés

-   **`pytest`** : Utilisé comme framework de test.
-   **`unittest.mock`** : Essentiel pour ces tests, car toutes les fonctions externes et potentiellement coûteuses sont mockées.
    -   Les fonctions `load_dotenv` et `find_dotenv` sont mockées pour simuler la présence ou l'absence d'un fichier `.env` sans dépendre du système de fichiers.
    -   La fonction `initialize_jvm` est mockée pour simuler le succès ou l'échec du démarrage de la JVM.
    -   La fonction `create_llm_service` est mockée pour simuler la création du client LLM, évitant ainsi des appels réseau ou des chargements de modèles lourds.
-   **`logging` (via `caplog`)** : La fixture `caplog` de `pytest` est utilisée pour capturer et vérifier les messages de log (information, avertissement, erreur) émis par le processus d'initialisation.
