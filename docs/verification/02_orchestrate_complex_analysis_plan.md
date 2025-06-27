# Plan de Vérification : `orchestrate_complex_analysis.py`

Ce document décrit le plan de test (défini rétrospectivement) pour la validation du script `scripts/orchestration/orchestrate_complex_analysis.py` et de son environnement de configuration.

## 1. Objectifs de la Vérification

L'objectif principal est de s'assurer que le script d'orchestration complexe peut être configuré et exécuté de manière fiable, sans erreur bloquante, et qu'il produit le rapport d'analyse attendu.

## 2. Périmètre de Test

*   **Gestion de l'environnement Conda** : Création, configuration et activation.
*   **Installation des dépendances** : Téléchargement et installation des packages requis, y compris les dépendances externes comme le JDK.
*   **Exécution du script** : Lancement et exécution complète du script `orchestrate_complex_analysis.py`.
*   **Génération des artefacts** : Production du rapport d'analyse final.
*   **Intégrité de l'environnement de développement** : Propreté de l'arbre Git après exécution.

## 3. Scénarios de Test

| ID | Scénario de Test | Critères de Succès |
|---|---|---|
| **ENV-01** | Installation de l'environnement Conda | L'environnement `arg_orga_env` est créé et activé sans erreur de timeout lors du `conda create`. |
| **ENV-02** | Propreté des dépendances | L'exécution du script ne génère aucun avertissement de dépréciation (`deprecation warnings`). |
| **ENV-03** | Téléchargement des dépendances externes | Le script télécharge et installe correctement le JDK depuis l'URL spécifiée. |
| **GIT-01** | Propreté de l'arbre Git | L'exécution du script ne modifie/crée aucun fichier suivi par Git (ex: pas de `_temp_jdk_download` ajouté au suivi). L'état de `git status` reste propre. |
| **CONF-01** | Nom de l'environnement Conda | Le script utilise le nom d'environnement `arg_orga_env` et non un nom incorrect comme `arg_orga_env_wrong`. |
| **EXEC-01** | Exécution complète du script | Le script s'exécute jusqu'à la fin sans interruption et génère le rapport d'analyse final dans le répertoire attendu. |