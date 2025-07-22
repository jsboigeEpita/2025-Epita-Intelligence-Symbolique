# Guide de Référence pour l'Intégration de l'Écosystème Java

Ce guide a pour but de fournir une référence complète sur l'intégration et la gestion de l'écosystème Java (JVM, JPype, Tweety) au sein de ce projet. Il est basé sur une analyse de l'historique du projet pour capitaliser sur les leçons apprises et fournir des directives claires.

## 1. Résumé de l'État Actuel et Architecture

L'intégration de la JVM via JPype est un composant sensible de notre architecture. L'état actuel est stable, mais cette stabilité a été obtenue après avoir résolu plusieurs problèmes critiques.

L'architecture actuelle repose sur des principes clés pour assurer la résilience :
*   **Gestion centralisée de la JVM** via le module `argumentation_analysis/core/jvm_setup.py`.
*   **Isolation des tests** en utilisant un framework de mock (`tests/mocks/jpype_setup.py`) pour la majorité des cas d'utilisation, limitant les tests d'intégration complets aux scénarios essentiels.
*   **Modularité des solveurs logiques** grâce à un sélecteur (`FOLHandler` refactorisé) permettant de basculer entre `tweety` (basé sur Java) et `prover9` (exécutable externe) via une variable d'environnement.

Les instabilités sont principalement liées aux interactions avec des bibliothèques externes (surtout natives) et des plugins de l'écosystème de test.

## 2. Historique des Problèmes et Solutions (Archéologie Git)

Cette section présente une analyse chronologique des problèmes rencontrés et des solutions apportées, qui ont façonné l'intégration actuelle.

### Phase 1 : Conflits de l'Écosystème de Test (Mai - Mi-Juin 2025)

*   **Problème** : Forte instabilité des tests due à des conflits entre `pytest-asyncio` et `pytest-playwright`, provoquant des erreurs `Event loop is closed`.
*   **Solution** : Application de `nest_asyncio` et utilisation d'API synchrones lorsque possible pour contourner le conflit.

### Phase 2 : Tentatives de Centralisation (Fin Juin - Début Juillet 2025)

*   **Problème** : Une première tentative de centralisation de la gestion JVM (`jpype_manager.py`) a introduit une "critical JVM startup error".
*   **Solution** : Suppression de l'approche ratée et standardisation sur `argumentation_analysis/core/jvm_setup.py`, qui est devenu le point de contrôle unique pour la configuration de la JVM.

### Phase 3 : Identification des Causes Racines de Crashs (Mi-Juillet à aujourd'hui)

Cette phase a été cruciale pour stabiliser l'environnement sous Windows.

*   **Problème** : Crash système persistant (`Windows fatal exception: access violation`).
*   **Cause Racine 1** : L'option JVM `-Djava.awt.headless=true` a été identifiée comme une cause directe du crash et a été supprimée.
*   **Cause Racine 2** : Le conflit le plus significatif venait du chargement de la **bibliothèque native Prover9 (`.dll`)** en même temps que la JVM. Sa suppression a été la clé de la stabilisation.
*   **Cause Racine 3** : Le plugin `pytest-opentelemetry` a été identifié comme une nouvelle source de crash de la JVM et a été désactivé.

## 3. Bonnes Pratiques et Dépannage

Basé sur les leçons apprises, voici les règles à suivre pour maintenir un environnement stable.

### Bonnes Pratiques

1.  **Gestion des Dépendances** : Toute nouvelle dépendance (Python ou autre) doit être testée rigoureusement pour sa compatibilité avec JPype. Soyez particulièrement méfiant envers les bibliothèques qui chargent des composants natifs (`.dll`, `.so`, `.dylib`).
2.  **Configuration de la JVM** : Ne modifiez pas les options de la JVM dans `jvm_setup.py` sans une compréhension claire de leur impact, en particulier sous Windows. Évitez les options graphiques comme `java.awt.headless`.
3.  **Plugins de Test** : L'écosystème de test `pytest` est une source potentielle de conflits. Avant d'ajouter un nouveau plugin, vérifiez s'il n'interfère pas avec les tests d'intégration Java. En cas de doute, désactivez-le temporairement pour diagnostiquer.
4.  **Isolation** : Privilégiez l'utilisation du framework de mock pour les tests unitaires et fonctionnels. Ne démarrez la JVM que lorsque c'est absolument nécessaire pour les tests d'intégration.

### Guide de Dépannage

Si vous rencontrez un crash de la JVM ou une instabilité, suivez ces étapes :

1.  **Vérifiez le dernier changement** : Le problème est-il apparu après l'ajout d'une bibliothèque ou la modification d'une configuration ? Annulez ce changement pour voir si le problème disparaît.
2.  **Examinez les plugins `pytest`** : Désactivez les plugins non essentiels dans `conftest.py` ou `pytest.ini`, en particulier ceux liés à l'instrumentation (`opentelemetry`) ou à l'asynchronisme.
3.  **Isolez le test** : Créez un test minimal qui reproduit le problème avec le moins de dépendances possible.
4.  **Vérifiez les bibliothèques natives** : Assurez-vous qu'aucune bibliothèque native n'est chargée dans le même processus que la JVM si elle n'est pas explicitement conçue pour cela.