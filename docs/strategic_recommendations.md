# Plan de Recommandations Stratégiques pour la Santé du Projet

## 1. Synthèse des Problèmes de Fond Récurrents

Basé sur l'ensemble des analyses, les 3 thèmes de problèmes les plus persistants qui transcendent les différentes phases du projet sont :

*   **Complexité et Fragilité de la Chaîne d'Outillage de Test :** L'historique du projet montre la construction progressive d'une chaîne de test complexe (PowerShell, Conda, Python, processus isolés) pour répondre à des défis techniques (crashs JVM, asynchronisme). Bien que des efforts récents aient visé à la stabiliser (centralisation, variables d'environnement), elle reste un point central de fragilité, difficile à maintenir et source potentielle d'erreurs.
*   **Volatilité des Dépendances Externes et Manque de Robustesse du Mocking :** Le projet a été fortement impacté par l'instabilité de dépendances clés (ex: `semantic-kernel`), forçant des refactorisations réactives. Ce problème persiste aujourd'hui avec les tests E2E qui sont invalidés par les timeouts d'un service LLM, révélant une stratégie de "mock" insuffisante pour garantir des tests CI/CD fiables et déterministes.
*   **Risques de Performance et Dette Technique masquée :** Des signaux d'alerte clairs indiquent des risques de performance. Le plus critique est l'augmentation massive du seuil de tolérance mémoire pour le composant `CluedoOracleState` (+450%), signalant une potentielle fuite ou une consommation excessive non maîtrisée. Des contournements passés (ex: `KMP_DUPLICATE_LIB_OK`) montrent aussi une tendance à masquer des problèmes de fond liés à l'environnement.

## 2. Recommandations Stratégiques Priorisées

| Priorité | Recommandation                                               | Problème Adressé                                         |
|----------|--------------------------------------------------------------|----------------------------------------------------------|
| **P1**   | Analyser et optimiser la consommation mémoire de `CluedoOracleState` | Risques de Performance et Dette Technique masquée        |
| **P1**   | Industrialiser la stratégie de mock pour les services externes (LLM) | Volatilité des Dépendances Externes et Mocking           |
| **P2**   | Simplifier et documenter la chaîne d'outillage de test E2E      | Complexité et Fragilité de la Chaîne d'Outillage         |
| **P3**   | Auditer et résoudre les contournements techniques restants   | Risques de Performance et Dette Technique masquée        |

## 3. Détail des Recommandations

### P1 - Analyser et optimiser la consommation mémoire de `CluedoOracleState`
*   **Problème Adressé :** Le commit `388b333b` a révélé une augmentation non soutenable du seuil de tolérance mémoire pour ce composant. L'ignorer pourrait mener à des crashs en production ou à une dégradation sévère des performances globales.
*   **Plan d'Action Suggéré :**
    1.  Mettre en place un scénario de test d'intégration isolé qui reproduit la charge sur `CluedoOracleState`.
    2.  Utiliser des outils de profilage mémoire (ex: `memory-profiler` en Python) pour identifier précisément les objets et les allocations responsables de cette consommation.
    3.  Analyser le code du composant pour trouver la cause racine (ex: fuite mémoire, cache non borné, structures de données inefficaces).
    4.  Implémenter une correction et valider avec le même test de profilage que la consommation est maîtrisée.
*   **Bénéfices Attendus :** Stabilité accrue, prévention des erreurs de type "Out of Memory", meilleure performance et prédictibilité du système.

### P1 - Industrialiser la stratégie de mock pour les services externes (LLM)
*   **Problème Adressé :** La dépendance des tests E2E à des services externes (LLM) qui sont sujets à des timeouts les rend non fiables, ce qui bloque les pipelines de CI/CD et ralentit la validation des changements. Le "mock" actuel est un contournement temporaire et non une solution pérenne.
*   **Plan d'Action Suggéré :**
    1.  Créer une bibliothèque de "mocks" dédiée pour les services d'IA, simulant différents scénarios de réponse (succès, échec, contenu spécifique, temps de réponse variables).
    2.  Intégrer cette bibliothèque dans la chaîne de test E2E pour qu'elle soit activée par défaut en environnement de CI.
    3.  Permettre aux développeurs de lancer facilement les tests en mode "mock" ou en mode "réel" pour des tests de bout en bout complets.
*   **Bénéfices Attendus :** Tests CI/CD fiables et rapides, vélocité des développeurs accrue, capacité à tester des cas d'erreur sans dépendre de l'état du service externe.

### P2 - Simplifier et documenter la chaîne d'outillage de test E2E
*   **Problème Adressé :** La complexité actuelle (mélange de PowerShell, Python, Conda, .bat) rend le débogage des tests difficile, l'intégration de nouveaux développeurs lente et augmente le risque d'erreurs d'environnement. Le script `activate_project_env.ps1` est un point de défaillance unique et critique.
*   **Plan d'Action Suggéré :**
    1.  Rédiger une documentation claire (ex: dans un `README.md` à la racine des tests) qui explique l'architecture de la chaîne de test, le rôle de chaque script et la manière de lancer et déboguer les tests.
    2.  Explorer des alternatives pour réduire la dépendance à des scripts multiples. Par exemple, utiliser un orchestrateur de tâches comme `Invoke` (en Python) ou `Makefile` pour unifier les commandes.
    3.  Refactoriser le script `activate_project_env.ps1` pour le rendre plus modulaire et ajouter des tests de validation sur ses sorties.
*   **Bénéfices Attendus :** Maintenance simplifiée, réduction du temps de débogage des échecs de test, onboarding plus rapide pour les nouveaux membres de l'équipe.

### P3 - Auditer et résoudre les contournements techniques restants
*   **Problème Adressé :** Des contournements comme la version rétrogradée de TypeScript (`4.9.5`) indiquent une dette technique qui, si elle n'est pas traitée, peut entraîner des problèmes de compatibilité, de sécurité ou bloquer des évolutions futures.
*   **Plan d'Action Suggéré :**
    1.  Créer une liste exhaustive des "hacks" et contournements connus dans le code.
    2.  Pour chaque point, investiguer la cause racine (ex: pourquoi la mise à jour de TypeScript échoue-t-elle ?).
    3.  Planifier la résolution de chaque problème dans le backlog, en commençant par ceux qui présentent le plus grand risque.
*   **Bénéfices Attendus :** Base de code plus saine et plus maintenable, réduction des risques de sécurité, capacité à utiliser les dernières versions des librairies et frameworks.