# Plan de Recommandations Stratégiques pour la Santé du Projet

## 1. Synthèse des Problèmes de Fond Récurrents
*   **Complexité et Fragilité de l'Outillage de Test et de Build :** Le problème le plus persistant. L'historique montre des crashs de JVM et des tests E2E instables. Actuellement, la chaîne de lancement (PowerShell, Conda, Python, Batch) est excessivement complexe, difficile à maintenir et source d'erreurs, malgré les efforts de stabilisation.
*   **Risques de Performance Non Maîtrisés :** Un thème émergent et critique. Une augmentation récente et massive (+450%) du surcoût mémoire de `CluedoOracleState` a été acceptée sans investigation approfondie. Cela représente un risque majeur pour la stabilité et la scalabilité de l'application.
*   **Instabilité des Dépendances Externes :** Le projet reste vulnérable aux services externes. Le service LLM, central pour les fonctionnalités d'IA, est actuellement instable (timeouts), ce qui bloque les tests E2E et révèle un manque de stratégie de résilience (ex: mocks, circuit breakers).
*   **Gestion Hétérogène de la Configuration :** Malgré des progrès vers la centralisation, la configuration reste dispersée. La communication de paramètres critiques (comme l'URL du frontend pour les tests) a nécessité des solutions de contournement fragiles (fichier de log, puis variables d'environnement), et la dépendance à un unique script PowerShell (`activate_project_env.ps1`) crée un point de défaillance unique.

## 2. Recommandations Stratégiques Priorisées
*Listez les actions recommandées, classées par ordre de priorité.*

| Priorité | Recommandation                                    | Problème Adressé                          |
|----------|---------------------------------------------------|-------------------------------------------|
| **P1**   | Analyser et maîtriser la consommation mémoire de `CluedoOracleState` | Risques de Performance Non Maîtrisés      |
| **P1**   | Simplifier et documenter la chaîne de tests E2E     | Complexité et Fragilité de l'Outillage    |
| **P2**   | Améliorer la Robustesse et l'Observabilité des Appels aux Services d'IA | Instabilité des Dépendances Externes      |
| **P3**   | Centraliser la configuration dans un socle d'exécution unifié | Gestion Hétérogène de la Configuration    |

## 3. Détail des Recommandations
### P1 - Analyser et maîtriser la consommation mémoire de `CluedoOracleState`
*   **Problème Adressé :** Le commit `388b333b` a révélé une augmentation non maîtrisée du seuil de tolérance mémoire pour le composant `CluedoOracleState` de 250% à 450%, sans analyse de la cause racine. Laisser cette situation perdurer expose le projet à des risques de crashs en production, de ralentissements et de coûts d'infrastructure imprévus.
*   **Plan d'Action Suggéré :**
    1.  Mettre en place un scénario de test de charge reproduisant l'utilisation de `CluedoOracleState`.
    2.  Utiliser des outils de profiling mémoire (ex: `memory-profiler` en Python) pour identifier précisément les fonctions ou objets responsables de la surconsommation.
    3.  Analyser le cycle de vie des objets pour détecter d'éventuelles fuites mémoire.
    4.  Établir un budget mémoire clair pour ce composant et mettre en place une alerte en cas de dépassement dans la CI.
*   **Bénéfices Attendus :** Prévention des pannes, amélioration des performances globales, maîtrise des coûts d'infrastructure et augmentation de la fiabilité du système.

### P1 - Simplifier et documenter la chaîne de tests E2E
*   **Problème Adressé :** La chaîne actuelle pour lancer les tests E2E est une pile complexe et fragile (PowerShell > Conda > Python > Batch) qui est difficile à déboguer et à maintenir. La communication entre ces couches (ex: passage de l'URL du frontend) a été un point de douleur récurrent.
*   **Plan d'Action Suggéré :**
    1.  Remplacer la chaîne de scripts par un unique orchestrateur de test (ex: `nox`, `tox`, ou même un script Python amélioré) qui gère l'activation de l'environnement, le lancement des services et l'exécution des tests.
    2.  Utiliser les capacités natives des frameworks de test pour la gestion des services (ex: fixtures `pytest` pour démarrer/arrêter les serveurs).
    3.  Documenter le processus de lancement des tests de manière claire et concise dans un `CONTRIBUTING.md`.
    4.  Intégrer cette commande unique et simplifiée dans le pipeline de CI.
*   **Bénéfices Attendus :** Réduction du temps de maintenance, accélération du débogage, baisse du risque d'erreurs liées à l'environnement et amélioration de l'expérience développeur.

### P2 - Améliorer la Robustesse et l'Observabilité des Appels aux Services d'IA
*   **Problème Adressé :** Notre code d'intégration avec les services LLM (OpenAI, Semantic Kernel) est fragile (timeouts, erreurs lors des tests E2E). L'objectif est de le renforcer sans engager de refactorisation risquée qui pourrait impacter les agents existants. La priorité est de rationaliser et de sécuriser les points d'entrée actuels, et non d'en créer de nouveaux.
*   **Plan d'Action Suggéré :**
    1.  **Instrumentation Non-Intrusive :** Ajouter un logging détaillé (latence, codes de retour) *autour* des appels LLM existants sans en modifier la logique interne pour mieux diagnostiquer les erreurs.
    2.  **Introduction Ciblée de Patrons de Résilience :** Envelopper les appels réseau existants dans des utilitaires ou décorateurs de "retry" (avec backoff exponentiel) pour gérer les erreurs passagères sans modifier le code des agents.
    3.  **Audit et Optimisation de la Configuration :** Analyser et ajuster la configuration des clients `semantic-kernel` et `openai` (timeouts, pool de connexions) pour optimiser les performances et la stabilité. Cette action ne modifie pas le code.
    4.  **Tests d'Intégration de Non-Régression :** Créer des tests qui valident spécifiquement le comportement actuel de la couche de communication face aux erreurs (4xx, 5xx, timeouts), afin d'établir une baseline et de garantir que les améliorations de robustesse n'introduisent pas de régressions.
*   **Bénéfices Attendus :** Augmentation de la stabilité des fonctionnalités IA sans risque de régression, meilleure visibilité sur les erreurs de communication, et réduction des échecs liés à des problèmes réseau temporaires.

### P3 - Centraliser la configuration dans un socle d'exécution unifié
*   **Problème Adressé :** La configuration (ports, URLs, chemins) est encore aujourd'hui gérée de manière éclatée, ce qui complique les déploiements et les tests dans différents environnements. La forte dépendance au script `activate_project_env.ps1` est un risque.
*   **Plan d'Action Suggéré :**
    1.  Adopter une bibliothèque de gestion de configuration centralisée (ex: `Pydantic` avec lecture de fichiers `.env`).
    2.  Migrer tous les paramètres actuellement hardcodés ou passés par des mécanismes ad-hoc vers ce système central.
    3.  Le "socle d'exécution" (cf. P1) doit charger cette configuration au démarrage et la propager de manière cohérente à tous les composants (backend, frontend, tests).
    4.  Documenter la hiérarchie de chargement de la configuration (ex: `config.default.yml` > `.env` > variables d'environnement système).
*   **Bénéfices Attendus :** Simplification radicale du déploiement, configuration cohérente entre les environnements (dev, test, prod), réduction des erreurs de configuration.