# Rapport de Diagnostic Global sur l'Instabilité du Système

**Date du rapport :** 22/06/2025

## 1. Résumé Exécutif

L'analyse consolidée de 400 commits, répartis en 20 lots, révèle que le système a traversé une phase de **refactorisation architecturale profonde et généralisée**, touchant presque tous les aspects critiques du projet : l'infrastructure de test, l'architecture du serveur web, la gestion des dépendances (notamment `semantic-kernel` et la JVM), et le moteur d'orchestration des agents.

L'instabilité actuelle du système n'est pas le fruit d'une dégradation progressive, mais plutôt l'**effet de bord attendu d'une "chirurgie à cœur ouvert"**. Des changements massifs et interdépendants ont été introduits pour payer une dette technique considérable et moderniser les fondations du projet. Bien que chaque refactorisation ait été menée avec une intention claire d'amélioration, leur superposition et leur envergure ont inévitablement créé des **conflits, des régressions temporaires et une complexité accrue**, expliquant l'état instable observé. Les efforts récents (lots 18-20) montrent une transition vers la stabilisation, mais une vigilance extrême est requise pour consolider ces nouvelles fondations.

## 2. Chronologie des Refactorisations Majeures

Le projet a évolué à travers plusieurs vagues de refactorisation intenses et souvent entrelacées.

*   **Lots 1-6 : La crise des tests et la fiabilisation de la JVM.**
    *   **Début (Lot 1) :** Le constat est brutal. Les tests unitaires provoquent un crash fatal de la JVM (`access violation`), rendant toute validation impossible. C'est le point de départ d'une longue quête de stabilité.
    *   **Solution (Lots 5-6) :** Une solution radicale et robuste est mise en place. Les tests dépendant de la JVM sont systématiquement déplacés dans des **processus isolés**. Cette refactorisation est une réussite mais introduit une nouvelle complexité dans l'infrastructure de test.

*   **Lots 3-4 & 7-8 : Modernisation du serveur Web (Flask/WSGI vers Uvicorn/ASGI).**
    *   **Problème :** Le serveur Flask se comporte mal avec les initialisations asynchrones, causant des crashs et des instabilités dans les tests E2E.
    *   **Solution :** Une refactorisation architecturale majeure est menée pour passer à une pile **ASGI** avec **Uvicorn** et **Starlette**. L'utilisation d'un `lifespan` manager résout les problèmes de démarrage, mais ce changement impacte toute la chaîne de lancement de l'application.

*   **Lots 7-9 & 14-19 : La saga de `semantic-kernel` et la refonte de l'orchestration.**
    *   **Dépendance instable (Lots 7-8, 12-13) :** La bibliothèque `semantic-kernel` est identifiée comme une source majeure d'instabilité. Une première tentative de refonte de l'orchestration échoue, conduisant à la **décision radicale de désactiver temporairement** les agents qui en dépendent (Lot 12) et de nettoyer toute la base de code de ses anciens imports.
    *   **Modernisation (Lots 14-15) :** Le projet ré-intègre `semantic-kernel` en adoptant ses nouvelles API (`Filters` au lieu de gestionnaires d'événements), ce qui nécessite une refactorisation généralisée des agents.
    *   **Nouveau Moteur d'Orchestration (Lot 17) :** L'orchestrateur monolithique est remplacé par un **moteur à base de stratégies**, plus modulaire et extensible. C'est l'un des changements les plus profonds, appliqué via un pattern "Strangler Fig" pour une migration contrôlée.

*   **Lots 16-20 : Consolidation et nettoyage.**
    *   **Unification des tests E2E (Lot 16) :** Les multiples suites de tests E2E (Python, JS) sont unifiées sous un seul runner.
    *   **Rationalisation (Lot 20) :** Un effort délibéré de nettoyage est mené pour supprimer des dizaines de scripts de validation redondants et archiver le code obsolète.

## 3. Conflits et Interférences Suspectés

L'interdépendance des refactorisations a créé plusieurs zones de friction.

1.  **Conflit Test vs. Orchestration Web :** Les efforts pour fiabiliser les tests E2E (ports dynamiques, `PlaywrightRunner`) se sont heurtés à la refactorisation de l'orchestrateur web. La communication de l'URL du frontend (allouée dynamiquement) vers les tests Playwright a nécessité une solution ad-hoc (écriture dans un fichier `logs/frontend_url.txt` - Lot 19), ce qui est un point de fragilité.

2.  **Impact de `semantic-kernel` sur l'API des Agents :** Les mises à jour successives de `semantic-kernel` ont forcé des changements cassants dans l'API de tous les agents (`invoke`, `invoke_single`, etc.). Le code a dû être adapté à plusieurs reprises (Lots 5, 8, 15, 19), créant un risque de régression si un agent n'était pas mis à jour correctement.

3.  **Refonte de l'Environnement de Lancement :** La centralisation du lancement des processus via `activate_project_env.ps1` (Lot 19) a simplifié le code Python de l'orchestrateur mais a déplacé la complexité dans un script PowerShell. Une erreur dans ce script impacte désormais l'ensemble du système (application, tests, démos), créant un point de défaillance unique mais centralisé.

## 4. Points de Risque et Dette Technique Identifiés

Malgré les efforts, plusieurs points de dette technique subsistent :

*   **Contournement OpenMP (`KMP_DUPLICATE_LIB_OK=TRUE`) (Lot 4) :** Il s'agit d'une **solution temporaire** qui masque un conflit de bibliothèques sous-jacent. Elle peut ne pas fonctionner sur toutes les machines et doit être résolue à la source.
*   **Version de TypeScript Rétrogradée (Lot 10) :** Le retour à une version antérieure de TypeScript (`4.9.5`) pour des raisons de compatibilité est un signe de friction dans l'écosystème frontend. La cause racine doit être identifiée pour permettre une mise à jour.
*   **Dépendance Radicale à `activate_project_env.ps1` (Lot 19) :** Bien que bénéfique pour la cohérence, la centralisation de toute la logique d'environnement dans ce script le rend extrêmement critique. Sa maintenance doit être rigoureuse.
*   **Code de test E2E dans l'orchestrateur (Lot 3) :** L'intégration de classes minimales "frontend/backend" directement dans l'orchestrateur pour les tests E2E a été acceptée comme une dette à court terme. Elle doit être externalisée dans un véritable harnais de test.

## 5. Conclusion sur les Causes Probables de l'Instabilité

L'instabilité actuelle n'est pas un symptôme de déclin, mais plutôt la conséquence directe et prévisible d'une **stratégie de refactorisation ambitieuse et nécessaire**.

Les causes profondes de l'état actuel sont :
1.  **L'Envergure des Changements :** Des pans entiers de l'architecture ont été remplacés simultanément.
2.  **L'Interdépendance des Chantiers :** La stabilisation des tests dépendait de la nouvelle architecture web, qui elle-même dépendait de la gestion de la JVM et des dépendances asynchrones. Cette "toile d'araignée" de dépendances a rendu chaque changement risqué.
3.  **La Volatilité des Dépendances Externes :** L'évolution rapide de `semantic-kernel` a imposé un rythme de refactorisation non planifié.

Le système est en phase de **convalescence**. Les fondations sont désormais plus saines, plus modernes et mieux testées, mais la surface d'attaque créée par ces changements massifs nécessite une phase de **stabilisation intensive**, de tests de non-régression et de surveillance avant que le système puisse être considéré comme stable.