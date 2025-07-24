# Archéologie de la Gestion de l'Environnement de Test

Ce document retrace l'évolution de la gestion de l'environnement de test du projet, en se basant sur l'analyse de l'historique `git` des fichiers clés. Il met en lumière les défis rencontrés et les solutions architecturales adoptées pour stabiliser une chaîne d'outils complexe.

## Acte I : L'Ère des Scripts PowerShell (Débuts - Mi-Juin 2025)

Au commencement, la gestion de l'environnement reposait sur des scripts PowerShell (`activate_project_env.ps1`, `run_tests.ps1`).

*   **Approche initiale :** Des scripts simples pour activer un environnement virtuel Python (`venv`) et lancer `pytest`.
*   **Complexification rapide :** Avec l'introduction de `Conda` pour gérer des dépendances plus complexes (notamment liées à la data science), les scripts ont commencé à s'alourdir. Ils devaient dynamiquement trouver le nom de l'environnement, gérer les chemins, et passer des arguments de plus en plus nombreux.
*   **Problèmes rencontrés :**
    *   **Fragilité :** Logique dupliquée, gestion des chemins d'accès peu robuste (surtout sur Windows), et difficulté à gérer les guillemets et les espaces dans les commandes passées en argument.
    *   **Manque de portabilité :** Fortement liés à PowerShell, rendant difficile une exécution sur d'autres systèmes.
    *   **Opacité :** La logique métier était noyée dans des détails d'implémentation de script, rendant le débogage difficile. Les erreurs de `pytest` étaient souvent masquées par des erreurs de script.

## Acte II : L'Intégration de la JVM et le Chaos des Fixtures (Fin-Juin - Mi-Juillet 2025)

L'introduction de la technologie Java via `JPype` pour l'intégration de `TweetyProject` a marqué un tournant majeur et une source considérable de problèmes.

*   **Le champ de bataille `conftest.py` :** Ce fichier est devenu le centre névralgique de la configuration des tests. Son historique est un témoignage des luttes pour :
    *   **Gérer le cycle de vie de la JVM :** De nombreuses tentatives pour démarrer et arrêter la JVM correctement, en utilisant des fixtures `pytest` avec différentes portées (`session`, `function`). Des crashs fréquents (`Windows fatal exception: access violation`) ont été attribués à des initialisations multiples ou à des conflits avec d'autres bibliothèques (Prover9, OpenTelemetry).
    *   **Mocker les dépendances lourdes :** Des mocks complexes pour `NumPy`, `Pandas`, et `JPype` lui-même ont été introduits pour accélérer les tests unitaires et isoler les composants. Maintenir ces mocks s'est avéré être une tâche complexe.
    *   **Conflits de plugins `pytest` :** L'utilisation simultanée de `pytest-asyncio` et `pytest-playwright` a provoqué des conflits de boucle d'événements, nécessitant des refactorisations majeures (passage de tests `async` à `sync` avec `asyncio.run()`).

*   **`run_tests.ps1` en chef d'orchestre :** Le script de lancement des tests est devenu extrêmement complexe, tentant d'orchestrer le démarrage de services backend (Flask/Uvicorn) et frontend (Node.js) avant de lancer les tests E2E. Des mécanismes de communication inter-processus fragiles (fichiers temporaires comme `_temp/service_urls.json`, variables d'environnement) ont été mis en place, source de nombreux échecs non déterministes.

## Acte III : La Centralisation en Python et la Stabilisation (Depuis mi-Juillet 2025)

Face à l'instabilité chronique, une décision architecturale clé a été prise : **centraliser la logique de gestion de l'environnement dans un module Python dédié.**

*   **La naissance de `environment_manager.py` :** Ce module est devenu le cerveau de l'opération. Les scripts PowerShell ont été drastiquement simplifiés pour n'être plus que de minces "lanceurs" qui délèguent toute la complexité à ce manager Python.
*   **Responsabilités du manager :**
    *   **Source de vérité unique :** Lecture de la configuration depuis les fichiers `.env` et `environment.yml`.
    *   **Gestion de Conda :** Activation, exécution de commandes dans l'environnement (`conda run`).
    *   **Provisionnement d'outils :** Téléchargement et installation automatiques d'outils portables comme le JDK ou Node.js.
    *   **Gestion du Classpath :** Configuration dynamique du `PYTHONPATH` et du classpath Java.
    *   **Réparation de dépendances :** Implémentation de stratégies sophistiquées (allant jusqu'à l'installation de wheels pré-compilés) pour corriger les environnements corrompus.
    *   **CLI :** Exposition de ses fonctionnalités via une interface en ligne de commande pour la maintenance.

## Conclusion et Leçons Apprises

L'historique de ces fichiers raconte l'histoire classique d'un projet dont la complexité a dépassé les capacités de ses outils initiaux.

1.  **Les scripts shell ont leurs limites :** Pour une logique complexe, la centralisation dans un langage de plus haut niveau (Python ici) est indispensable pour la maintenabilité, la robustesse et la portabilité.
2.  **L'enfer des environnements hétérogènes :** L'intégration de technologies différentes (Python, Java, Node.js) dans une même chaîne de tests est une source majeure de complexité. La gestion du cycle de vie de la JVM a été le problème le plus persistant.
3.  **L'importance d'une façade claire :** L'architecture finale, avec des scripts PowerShell simples agissant comme une façade devant un manager Python puissant, est une solution robuste. Elle sépare clairement les préoccupations : le lancement (shell) et la logique (Python).
4.  **Tester, c'est aussi tester l'environnement :** Une part significative de l'effort n'a pas été de tester le code applicatif lui-même, mais de réussir à construire et stabiliser un environnement dans lequel les tests pouvaient s'exécuter de manière fiable.