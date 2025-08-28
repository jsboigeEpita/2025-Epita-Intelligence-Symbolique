# Stratégie de Gestion de la JVM dans les Tests

Ce document explique comment la JVM est gérée dans notre suite de tests `pytest` pour garantir la stabilité, en particulier sous Windows où les conflits de cycle de vie de la JVM peuvent causer des crashs fatals (`Windows fatal exception: access violation`).

## Le Problème : Conflit de Cycle de Vie de la JVM

Le cœur du problème réside dans le fait que `JPype` ne permet de démarrer la JVM **qu'une seule fois** par processus. Toute tentative de redémarrage ou de démarrage d'une seconde JVM dans un sous-processus qui a hérité de l'état du parent mène à un crash.

Nos tests se divisent en deux catégories principales :

1.  **Tests d'Intégration (`@pytest.mark.jvm_test`)**: Ces tests importent directement des composants qui dépendent de la JVM (ex: `TweetyBridge`). Ils nécessitent qu'une JVM soit active dans le processus `pytest` principal.
2.  **Tests End-to-End (`@pytest.mark.e2e`)**: Ces tests valident l'application complète. Ils utilisent la fixture `e2e_servers` qui démarre le serveur backend dans un **sous-processus**. Ce serveur backend est lui-même responsable de démarrer et de gérer sa propre JVM.

Le conflit survient lorsqu'un test E2E est exécuté dans une session `pytest` où la JVM a déjà été démarrée pour des tests d'intégration. Le sous-processus du serveur E2E hérite d'un état invalide et crashe en tentant d'initialiser sa propre JVM.

## La Solution : Isolation Stricte

Pour résoudre ce problème, nous avons implémenté une stratégie d'isolation stricte :

1.  **Fixture de Session `jvm_session`**:
    *   Une fixture `jvm_session` avec `scope="session"` et `autouse=True` est définie dans `tests/conftest.py`.
    *   Elle est responsable de démarrer la JVM **une unique fois** pour tous les tests qui en ont besoin (principalement les tests d'intégration).

2.  **Désactivation pour les Tests E2E**:
    *   Les tests qui utilisent la fixture `e2e_servers` **ne doivent pas** avoir de JVM active dans le processus `pytest` principal.
    *   Pour garantir cela, tous les tests E2E doivent être marqués avec `@pytest.mark.no_jvm_session`.
    *   Ce marqueur indique à la fixture `jvm_session` de ne pas s'exécuter pour ce test.
    *   De plus, une assertion de sécurité a été ajoutée au début de la fixture `e2e_servers` pour vérifier que `jpype.isJVMStarted()` est `False`. Si ce n'est pas le cas, le test échoue avec un message d'erreur explicite, empêchant le crash fatal.

## Comment Exécuter les Tests

*   **Pour exécuter tous les tests sauf les E2E (recommandé pour le développement rapide)**:
    ```bash
    python -m pytest -m "not e2e"
    ```

*   **Pour exécuter uniquement les tests E2E**:
    Il est **crucial** d'utiliser le marqueur pour s'assurer que la JVM de session n'est pas démarrée.
    ```bash
    python -m pytest -m e2e
    ```
    (La configuration actuelle des marqueurs devrait gérer l'isolation automatiquement).

*   **Pour exécuter un fichier de test E2E spécifique**:
    Assurez-vous que le test est marqué avec `@pytest.mark.no_jvm_session`.
    ```bash
    python -m pytest tests/test_mon_fichier_e2e.py
    ```

Cette approche garantit que les deux types de tests peuvent coexister dans la même suite de tests sans provoquer d'instabilité liée à la JVM.