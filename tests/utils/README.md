# Tests des Utilitaires

Ce répertoire contient les tests pour les modules utilitaires du projet.

## Modules Testés

-   **`FetchService` (dans [`test_fetch_service_errors.py`](test_fetch_service_errors.py:1))**: Ce module teste la gestion des erreurs réseau lors de la récupération de contenu à partir d'URLs. Il couvre divers scénarios tels que les timeouts, les erreurs DNS, les erreurs HTTP (404, 403, 500), les problèmes SSL, etc.