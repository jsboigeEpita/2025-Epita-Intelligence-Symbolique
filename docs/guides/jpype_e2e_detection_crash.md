# Résolution du Crash JVM (Access Violation) au Démarrage des Tests

## Contexte de la Panne (Mission D3.1.1)

- **Symptôme :** Un crash fatal de la JVM (`Windows fatal exception: access violation`) se produit systématiquement au démarrage de la suite de tests `pytest`.
- **Déclencheur :** Le crash survient lors de l'appel à `jpype.startJVM()` dans la fonction `pytest_sessionstart` du fichier `tests/conftest.py`.
- **Impact :** Blocage complet de l'exécution des tests, y compris les tests unitaires qui ne dépendent pas de Java.

## Diagnostic et Cause Racine

L'enquête a révélé que le crash n'était pas directement dû à `jpype` ou à la configuration de la JVM, mais à une **logique de détection de session de test E2E (End-to-End) erronée** dans `tests/conftest.py`.

1.  **Logique défaillante :** Le code vérifiait si la chaîne `"e2e"` apparaissait dans les mots-clés (`item.keywords`) de n'importe quel test collecté.
2.  **Faux Positif :** Cette condition était déclenchée par la simple présence du répertoire `tests/e2e/`, même lors d'une session de tests unitaires standard.
3.  **Conséquence :** Le système croyait à tort qu'il s'agissait d'une session E2E et tentait d'initialiser la JVM de manière inappropriée au tout début de la collecte de tests, provoquant une instabilité et le crash `access violation` avant même l'exécution du premier test.

## Solution Appliquée

Le correctif a consisté à remplacer la détection par chaîne de caractères par une méthode plus robuste et spécifique à `pytest`, qui vérifie la présence explicite du marqueur `@pytest.mark.e2e`.

**Fichier modifié :** [`tests/conftest.py`](tests/conftest.py:1)

```python
# Ligne 251
# Ancienne logique (incorrecte)
# is_e2e_session = any("e2e" in item.keywords for item in session.items)

# Nouvelle logique (correcte)
is_e2e_session = any(item.get_closest_marker("e2e") is not None for item in session.items)
```

Cette modification garantit que la JVM n'est initialisée que lorsque des tests explicitement marqués comme `e2e` sont ciblés pour l'exécution, résolvant ainsi le crash au démarrage pour toutes les autres sessions de test.