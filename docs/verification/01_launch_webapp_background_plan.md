# Plan de Vérification : `launch_webapp_background.py`

Ce document décrit le plan de test pour valider le fonctionnement du script `scripts/apps/webapp/launch_webapp_background.py`.

## 1. Objectifs de Test

L'objectif est de vérifier de manière autonome les fonctionnalités suivantes :
1.  **Lancement réussi** : Le script peut démarrer le serveur web Uvicorn en arrière-plan sans erreur.
2.  **Accessibilité de l'application** : Une fois démarrée, l'application est accessible via son endpoint de health-check.
3.  **Gestion d'erreur (Port déjà utilisé)** : Le script gère correctement le cas où le port est déjà occupé. Bien que le script actuel tue les processus existants, nous simulerons ce cas pour assurer la robustesse.
4.  **Vérification du statut** : La commande `status` reflète correctement l'état de l'application.
5.  **Arrêt du serveur** : La commande `kill` arrête bien le ou les processus du serveur.

## 2. Procédure de Test

Les tests seront exécutés séquentiellement.

### Test 1 : Lancement et Accessibilité

*   **Description :** Vérifie que le script peut démarrer le serveur et qu'il est accessible.
*   **Commande :**
    1.  `python ./scripts/apps/webapp/launch_webapp_background.py start`
    2.  `Start-Sleep -Seconds 15`
    3.  `Invoke-WebRequest -Uri http://127.0.0.1:5003/api/health`
*   **Critère de succès :**
    *   La commande de lancement retourne un code de sortie 0.
    *   `Invoke-WebRequest` retourne un code de statut 200.

### Test 2 : Gestion du port utilisé

*   **Description :** Vérifie le comportement lorsque le serveur est lancé une seconde fois. Le comportement attendu est que l'ancien processus soit tué et qu'un nouveau démarre correctement.
*   **Commande :**
    1. (Après le Test 1 réussi) `python ./scripts/apps/webapp/launch_webapp_background.py start`
    2. `Start-Sleep -Seconds 15`
    3. `Invoke-WebRequest -Uri http://127.0.0.1:5003/api/health`
*   **Critère de succès :**
    *   La commande de lancement retourne un code de sortie 0.
    *   `Invoke-WebRequest` retourne un code de statut 200.

### Test 3 : Vérification du statut

*   **Description :** Vérifie que la commande `status` fonctionne.
*   **Commande :**
    1. (Après le Test 2 réussi) `python ./scripts/apps/webapp/launch_webapp_background.py status`
*   **Critère de succès :**
    *   Le script retourne un code de sortie 0 et indique que le backend est OK.

### Test 4 : Arrêt du serveur

*   **Description :** Vérifie que la commande `kill` arrête le serveur.
*   **Commande :**
    1.  `python ./scripts/apps/webapp/launch_webapp_background.py kill`
    2.  `Start-Sleep -Seconds 5`
    3.  `python ./scripts/apps/webapp/launch_webapp_background.py status`
*   **Critère de succès :**
    *   La commande `kill` retourne un code de sortie 0.
    *   La commande `status` subséquente retourne un code de sortie 1 (Backend KO).