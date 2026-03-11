# Entry Point 2: Guide des Applications Web

## 1. Contexte de la Mission

Ce document a pour but de valider, tester et documenter de manière centralisée toutes les applications web et interfaces graphiques du projet. L'objectif est de fournir un point d'entrée unique et fiable pour les développeurs souhaitant lancer, tester ou faire évoluer ces applications.

Cette analyse a été menée dans le cadre de la mission "EP2 Web Applications Validation".

## 2. Inventaire des Applications

L'exploration du code a révélé un écosystème hétérogène composé de plusieurs applications, frameworks et services.

| Application / Service | Chemin d'accès | Framework / Technologie | Statut de Lancement |
| :--- | :--- | :--- | :--- |
| **Interface Web Principale** | [`interface_web/`](./interface_web) | **Starlette / React** | ✅ **Lancée avec succès** |
| **Application Web Legacy (Simple)** | [`services/web_api/interface-simple/`](./services/web_api/interface-simple) | **Flask** | ✅ **Lancée avec succès** |
| API REST Principale | [`api/`](./api) | **FastAPI** | ✅ **Lancée avec succès** |
| Application Mobile | [`3.1.5_Interface_Mobile/`](./3.1.5_Interface_Mobile) | **Expo (React Native)** | ✅ **Lancée avec succès** |
| Orchestrateur Unifié | [`scripts/apps/webapp/`](./scripts/apps/webapp) | Python (Script) | N/A |

---

## 3. Application Principale (Starlette + React)

C'est l'application la plus moderne et la plus intégrée du projet. Elle est gérée par un orchestrateur unifié qui simplifie son lancement.

### 3.1. Architecture

-   **Backend**: Une application [Starlette](https://www.starlette.io/) située dans [`interface_web/app.py`](./interface_web/app.py) qui sert une API et les fichiers statiques du frontend.
-   **Frontend**: Une application [React](https://reactjs.org/) (initialisée avec `create-react-app`) dont le code source se trouve dans `services/web_api/interface-web-argumentative/`. Les fichiers buildés sont servis par le backend Starlette.
-   **Orchestration**: Le script [`unified_web_orchestrator.py`](./scripts/apps/webapp/unified_web_orchestrator.py) gère le cycle de vie complet : activation de l'environnement, installation des dépendances, nettoyage des ports, lancement des serveurs backend et frontend, et surveillance de leur état.

### 3.2. Procédure de Lancement

Le lancement de l'application a été réalisé avec succès à l'aide de l'orchestrateur.

1.  **Prérequis**: Avoir un environnement Conda nommé `epita_env` correctement configuré.
2.  **Commande de lancement**:
    ```bash
    python scripts/apps/webapp/unified_web_orchestrator.py
    ```
3.  **Résultat**:
    -   Le backend Starlette est accessible sur `http://localhost:8098`.
    -   Le frontend React est accessible sur `http://localhost:8085`.

### 3.3. Dépannage et Corrections

Lors du premier lancement, deux problèmes ont été identifiés et corrigés :

1.  **Erreur `TypeError` sur `ServiceManager`**:
    -   **Symptôme**: Le script échouait avec une erreur `TypeError: OrchestrationServiceManager.__init__() got an unexpected keyword argument 'config'`.
    -   **Cause**: L'instanciation de `ServiceManager` dans [`interface_web/app.py`](./interface_web/app.py:165) utilisait un ancien format avec un paramètre `config`.
    -   **Solution**: La ligne a été modifiée pour appeler `ServiceManager()` sans argument, conformément à sa nouvelle définition.

2.  **Erreur `404 Not Found` sur le Health Check**:
    -   **Symptôme**: L'orchestrateur démarrait le backend puis l'arrêtait immédiatement car le health check sur `/api/health` échouait.
    -   **Cause**: L'application exposait un endpoint `/api/status` mais l'orchestrateur était configuré pour interroger `/api/health`.
    -   **Solution**: Un alias a été ajouté dans [`interface_web/app.py`](./interface_web/app.py:186) pour que la route `/api/health` pointe vers le même endpoint que `/api/status`.

Avec ces deux corrections, l'application est désormais stable et peut être lancée de manière fiable.

---

## 4. Application Legacy (Flask)

Une application Flask autonome a été découverte dans `services/web_api/interface-simple/`. Elle semble être une version plus ancienne ou une démo technique. Elle ne sert pas de frontend React, mais expose des endpoints d'API.

### 4.1. Architecture

- **Backend**: Une application [Flask](https://flask.palletsprojects.com/) simple définie dans [`app.py`](./services/web_api/interface-simple/app.py).
- **Dépendances**: L'application s'appuie sur le `ServiceManager` global du projet, ce qui indique une intégration avec l'écosystème d'analyse d'argumentation.

### 4.2. Procédure de Lancement

Le lancement nécessite l'activation de l'environnement Conda du projet via le script wrapper prévu à cet effet.

1.  **Prérequis**: Environnement Conda `projet-is` configuré.
2.  **Commande de lancement**:
    ```powershell
    # À la racine du projet
    ./activate_project_env.ps1 -CommandToRun 'python services/web_api/interface-simple/app.py'
    ```
3.  **Résultat**:
    -   Le serveur Flask démarre et est accessible sur `http://localhost:3000`.

### 4.3. Dépannage et Corrections

Un bug critique, identique à celui trouvé dans l'application Starlette, a été corrigé pour permettre le lancement :

1.  **Erreur `TypeError` sur `ServiceManager`**:
    -   **Symptôme**: L'application ne démarrait pas, levant une `TypeError: OrchestrationServiceManager.__init__() got an unexpected keyword argument 'config'`.
    -   **Cause**: L'instanciation de `ServiceManager` dans [`services/web_api/interface-simple/app.py`](./services/web_api/interface-simple/app.py) était obsolète.
    -   **Solution**: L'appel a été corrigé pour utiliser `ServiceManager()`, sans argument, ce qui a résolu l'erreur et permis au serveur de démarrer.

---

## 5. API REST Principale (FastAPI)

Une API REST basée sur FastAPI a été identifiée dans le répertoire `api/`. Elle semble conçue pour exposer les fonctionnalités d'analyse du projet de manière plus directe et moderne que l'application Flask.

### 5.1. Architecture

- **Backend**: Une application [FastAPI](https://fastapi.tiangolo.com/) définie dans [`main_simple.py`](./api/main_simple.py). Le serveur est lancé via [Uvicorn](https://www.uvicorn.org/).
- **Intégration**: L'application est conçue pour être exécutée comme un module Python (`python -m api.main_simple`), ce qui assure que les imports relatifs au projet fonctionnent correctement.

### 5.2. Procédure de Lancement

Le lancement de l'API s'effectue, comme pour les autres composants, en utilisant le script d'environnement du projet.

1.  **Prérequis**: Environnement Conda `projet-is` configuré.
2.  **Commande de lancement**:
    ```powershell
    # À la racine du projet
    ./activate_project_env.ps1 -CommandToRun 'python -m api.main_simple'
    ```
3.  **Résultat**:
    -   Le serveur Uvicorn démarre et l'API est accessible sur `http://0.0.0.0:8000`.

### 5.3. Dépannage et Observations

-   **Succès du premier coup**: Contrairement aux autres applications web, l'API FastAPI a démarré sans nécessiter de correction de code. Cela indique qu'elle est probablement mieux maintenue ou d'une conception plus récente.
-   **Erreur de manipulation initiale**: Une première tentative de lancement a échoué car la commande n'était pas exécutée depuis le répertoire racine du projet, empêchant le script `activate_project_env.ps1` d'être trouvé. Il est crucial de toujours lancer les commandes depuis la racine (`c:\dev\2025-Epita-Intelligence-Symbolique`).

---

## 6. Application Mobile (Expo)

Le projet inclut une application mobile développée avec Expo et React Native. Grâce à `react-native-web`, elle peut également être lancée comme une application web standard pour un développement et des tests simplifiés.

### 6.1. Architecture

- **Framework**: [Expo (React Native)](https://expo.dev/) utilisant TypeScript. Le code source est situé dans [`3.1.5_Interface_Mobile/`](./3.1.5_Interface_Mobile).
- **Environnement**: L'application est autonome et repose sur l'écosystème Node.js/NPM. Elle n'a pas de dépendance directe avec l'environnement Conda du projet.
- **Gestion des dépendances**: Un fichier [`package.json`](./3.1.5_Interface_Mobile/package.json) définit les dépendances et les scripts de lancement.

### 6.2. Procédure de Lancement (Mode Web)

Le lancement en mode web est la méthode la plus directe pour valider le fonctionnement de l'application depuis un poste de développement.

1.  **Installation des dépendances**:
    ```bash
    # Depuis le répertoire 3.1.5_Interface_Mobile/
    npm install
    ```
2.  **Lancement du serveur de développement**:
    ```bash
    # Depuis le répertoire 3.1.5_Interface_Mobile/
    npm run web
    ```
3.  **Résultat**:
    -   Le serveur de développement Metro Bundler démarre.
    -   L'application est accessible dans le navigateur web à l'adresse `http://localhost:8081`.

### 6.3. Observations

- Le lancement s'est déroulé avec succès sans aucune modification du code.
- Des avertissements concernant des dépendances dépréciées et des vulnérabilités de bas niveau ont été rapportés par `npm install`. Ceux-ci devraient être examinés dans le futur mais ne sont pas bloquants.
- Des avertissements sur l'utilisation de `shadow*` dans les styles ont été affichés dans la console. C'est une dépréciation d'API qui devrait être corrigée pour maintenir la qualité du code.