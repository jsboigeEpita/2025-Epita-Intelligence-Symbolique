---
**Objectif Global :** Transformer une suite de tests d'intégration non fonctionnelle, bloquée par des erreurs et des timeouts, en un filet de sécurité robuste et fiable pour le projet.

Le projet a été mené à bien en trois phases critiques :

**Phase 1 : Remplacement des Mocks par la Logique Métier Réelle**

Le premier constat était que les tests, même lorsqu'ils passaient, ne validaient aucune logique métier réelle. Ils reposaient sur des services "mock" qui retournaient des réponses pré-définies.
*   **Action Clé :** Le `FrameworkService` factice a été remplacé par une intégration complète avec la bibliothèque Java `TweetyProject` via `JPype`. Les tests de logique formelle valident désormais le véritable code de production.

**Phase 2 : Refactorisation de l'Isolation des Tests**

Il a été découvert que les services réels et les services "mock" (notamment pour les appels LLM) étaient activés de manière implicite et imprévisible.
*   **Action Clé :** Le système d'injection de dépendances a été profondément revu. Désormais, les tests unitaires doivent *explicitement* injecter des mocks, tandis que les tests d'intégration utilisent *obligatoirement* les vrais services, nécessitant une configuration d'environnement valide (ex: `OPENAI_API_KEY`). Cette séparation stricte a clarifié l'intention de chaque type de test.

**Phase 3 : Débogage et Stabilisation de l'Environnement de Test E2E**

Après avoir intégré les vrais services, la suite de tests E2E s'est avérée instable, révélant une série de problèmes complexes liés à l'interaction entre `pytest`, les sous-processus, `JPype` et le système d'exploitation.
*   **Actions Clés :**
    1.  **Gestion de la Fermeture de la JVM :** Un crash violent de la JVM a été résolu en implémentant un hook `atexit` dans l'application Flask ([`services/web_api_from_libs/app.py`](services/web_api_from_libs/app.py:119)), garantissant un arrêt propre et ordonné de la JVM à la fin des tests.
    2.  **Fiabilisation des Chemins de Fichiers :** Des erreurs `file or directory not found` sous Windows ont été éliminées en modifiant le [runner Playwright](scripts/apps/webapp/playwright_runner.py) pour qu'il convertisse systématiquement les chemins en format POSIX, assurant leur interprétation correcte par tous les outils de la chaîne.
    3.  **Nettoyage de l'Environnement :** Les mocks LLM indésirables ont été désactivés en nettoyant les variables d'environnement (`PYTEST_CURRENT_TEST`) propagées aux sous-processus de test.

**Résultat Final :**
La suite de tests d'intégration et End-to-End est désormais **stable, fiable et s'exécute jusqu'à son terme sans erreur ni crash**. Les correctifs ont tous été documentés et intégrés à la branche principale, fournissant une base solide pour les développements futurs et garantissant que les régressions seront détectées de manière fiable.
---