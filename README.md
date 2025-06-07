# Projet d'Analyse d'Argumentation

Ce projet contient une application web pour l'analyse d'argumentation, composée d'un backend Flask et d'un frontend React.

## 🔒 **Sécurité et Intégrité - Mise à Jour Janvier 2025**

### ✅ **Audit d'Intégrité Récent**
Un audit de sécurité complet a été réalisé sur le système **Sherlock-Watson-Moriarty Oracle Enhanced**, aboutissant à :

- **4 violations d'intégrité** détectées et **corrigées**
- **CluedoIntegrityError** déployé pour protection anti-triche
- **Mécanismes de surveillance** temps réel intégrés
- **Couverture tests** maintenue à **100%**

Pour plus de détails, consulter :
- 📋 **[Rapport d'Audit Complet](docs/sherlock_watson/AUDIT_INTEGRITE_CLUEDO.md)**
- 🛠️ **[Guide Utilisateur Sécurisé](docs/sherlock_watson/GUIDE_UTILISATEUR_COMPLET.md)**
- 🏗️ **[Architecture Sécurité](docs/sherlock_watson/ARCHITECTURE_TECHNIQUE_DETAILLEE.md)**

## Prérequis

### Backend
- Python 3.x
- Conda (pour la gestion de l'environnement)
- Les dépendances listées dans `requirements.txt`

### Frontend
- Node.js (avec npm ou yarn)

## Configuration de l'environnement

### Backend
1.  **Créer et activer l'environnement Conda** (si ce n'est pas déjà fait) :
    ```bash
    conda create --name projet-is python=3.9  # Ou la version de Python que vous utilisez
    conda activate projet-is
    ```
2.  **Installer les dépendances Python** :
    Depuis la racine du projet :
    ```bash
    pip install -r requirements.txt
    ```
3.  **Configurer PYTHONPATH** :
    Assurez-vous que le répertoire racine du projet est dans votre `PYTHONPATH`.
    Sous PowerShell (pour la session actuelle) :
    ```powershell
    $env:PYTHONPATH = "C:\dev\2025-Epita-Intelligence-Symbolique;" + $env:PYTHONPATH 
    # Remplacez C:\dev\2025-Epita-Intelligence-Symbolique par le chemin absolu de la racine de votre projet si différent.
    ```
    Pour une configuration permanente, ajoutez ceci à votre profil PowerShell ou configurez-le via les variables d'environnement système.

    **Alternative : Utilisation des scripts d'environnement PowerShell**

    Pour simplifier la configuration de l'environnement et l'exécution de commandes, le projet fournit des scripts PowerShell.

    **1. Le script de travail principal : `scripts\env\activate_project_env.ps1`**

    Ce script est le cœur de l'automatisation de l'environnement. Voici ce qu'il fait :
    *   Il charge les variables d'environnement depuis le fichier `.env` situé à la racine du projet (par exemple, `OPENAI_API_KEY`, `JAVA_HOME`, `CONDA_ENV_NAME`).
    *   Il configure la variable d'environnement `JAVA_HOME` pour la session PowerShell actuelle si elle est définie dans `.env`.
    *   Il ajoute le répertoire `bin` de `JAVA_HOME` au `PATH` système pour la session PowerShell actuelle.
    *   **Comportement avec `-CommandToRun`** :
        *   Si vous lui passez le paramètre `-CommandToRun "<votre_commande>"` (où `<votre_commande>` n'est pas une chaîne vide) :
            *   Il exécute `<votre_commande>` en utilisant `conda run -n <nom_env_conda> --no-capture-output --live-stream <votre_commande>`. Le `<nom_env_conda>` est typiquement `projet-is` ou celui défini par `CONDA_ENV_NAME` dans votre `.env`.
            *   Cela signifie que votre commande s'exécute dans l'environnement Conda isolé, qui gère ses propres dépendances et `PYTHONPATH`. C'est la méthode recommandée pour lancer des applications Python du projet.
        *   Si `-CommandToRun` n'est pas fourni, ou si la commande est une chaîne vide :
            *   Le script N'EXÉCUTE PAS `conda run`.
            *   Il N'ACTIVE PAS l'environnement Conda dans votre session PowerShell actuelle (il ne fait pas `conda activate projet-is`).
            *   Il NE CONFIGURE PAS `PYTHONPATH` pour votre session PowerShell actuelle. Dans ce cas, si vous voulez lancer des scripts Python manuellement ensuite, vous devrez gérer l'activation de Conda et `PYTHONPATH` vous-même (voir la configuration manuelle ci-dessus).

    **2. Les scripts raccourcis à la racine du projet**

    Pour faciliter l'appel du script principal, deux raccourcis (wrappers) sont disponibles à la racine du projet :

    *   **`.\activate_project_env.ps1`**
        *   **Usage recommandé pour lancer des commandes (comme le serveur backend) :**
            ```powershell
            .\activate_project_env.ps1 -CommandToRun "python .\argumentation_analysis\services\web_api\start_api.py --port 5003"
            ```
            Cela passe l'option `-CommandToRun` au script `scripts\env\activate_project_env.ps1`, qui exécutera la commande via `conda run`.
        *   **Usage pour préparer partiellement l'environnement (sans lancer de commande via Conda) :**
            Si vous l'appelez sans `-CommandToRun` :
            ```powershell
            .\activate_project_env.ps1
            ```
            Il appelle `scripts\env\activate_project_env.ps1` sans `-CommandToRun`. Cela chargera les variables de `.env` et configurera `JAVA_HOME`/`PATH` dans votre session PowerShell actuelle. Cela n'active pas Conda ni ne configure `PYTHONPATH` pour le shell.

    *   **`.\setup_project_env.ps1`**
        *   Ce script appelle toujours `scripts\env\activate_project_env.ps1` en lui passant le paramètre `-CommandToRun`.
        *   Si vous l'appelez avec `-CommandToRun "<votre_commande>"` :
            ```powershell
            .\setup_project_env.ps1 -CommandToRun "python .\argumentation_analysis\services\web_api\start_api.py --port 5003"
            ```
            L'effet est identique à l'utilisation de `.\activate_project_env.ps1 -CommandToRun "<votre_commande>"`.
        *   Si vous l'appelez sans `-CommandToRun` :
            ```powershell
            .\setup_project_env.ps1
            ```
            Il passe `-CommandToRun ""` (une chaîne vide) à `scripts\env\activate_project_env.ps1`. L'effet est donc similaire à `.\activate_project_env.ps1` sans argument : chargement de `.env`, configuration de `JAVA_HOME`/`PATH`, mais pas d'exécution via `conda run` ni d'activation Conda/`PYTHONPATH` pour le shell.
            Le nom "setup" peut être un peu trompeur dans ce cas précis ; il est plus pertinent si vous l'utilisez avec `-CommandToRun` pour exécuter une tâche de configuration ou de lancement.

    **En résumé pour démarrer le backend :**
    La méthode recommandée utilisant les scripts est :
    ```powershell
    .\activate_project_env.ps1 -CommandToRun "python .\argumentation_analysis\services\web_api\start_api.py --port 5003"
    ```
    Cela garantit que le serveur s'exécute dans l'environnement Conda correctement configuré.

    Un script `setup_project_env.sh` est disponible pour les environnements bash/zsh, fonctionnant sur un principe similaire pour exécuter une commande dans un environnement préparé.

### Frontend
1.  **Installer les dépendances Node.js** :
    Naviguez vers le répertoire du client :
    ```bash
    cd services/web_api/interface-web-argumentative
    ```
    Puis installez les dépendances :
    ```bash
    npm install
    # ou si vous utilisez yarn:
    # yarn install
    ```
    Retournez ensuite à la racine du projet si nécessaire :
    ```bash
    cd ../../.. 
    ```

## Démarrage de l'application

Le lancement du backend et du frontend est géré par des scripts pour plus de simplicité et de cohérence.

### 1. Configurer la communication Frontend -> Backend

Avant de lancer, assurez-vous que le frontend sait comment contacter le backend.

1.  **Créez un fichier** nommé `.env` dans le répertoire du frontend, ici : `services/web_api/interface-web-argumentative/.env`
2.  **Ajoutez la ligne suivante** dans ce fichier. Le port doit correspondre à celui sur lequel vous allez lancer le backend (par exemple, 5005).

    ```
    REACT_APP_API_BASE_URL=http://localhost:5005
    ```

### 2. Lancer les serveurs

Ouvrez deux terminaux PowerShell à la racine du projet.

**Terminal 1 : Lancer le Backend**

Utilisez le script `run_backend.cmd` pour démarrer le serveur Flask. Vous pouvez spécifier un port.

```powershell
# Lance le backend sur le port 5005
.\activate_project_env.ps1 -CommandToRun "scripts\run_backend.cmd 5005"
```

**Terminal 2 : Lancer le Frontend**

Utilisez le script `run_frontend.cmd` pour démarrer le serveur React. Vous pouvez également spécifier un port.

```powershell
# Lance le frontend sur le port 3001
.\activate_project_env.ps1 -CommandToRun "scripts\run_frontend.cmd 3001"
```

L'application React s'ouvrira dans votre navigateur et communiquera avec le backend sur le port que vous avez défini dans le fichier `.env` du frontend.

## Documentation

Ce projet dispose d'une documentation complète organisée dans le répertoire `docs/`. Nous vous recommandons de consulter :

- **[Documentation complète](docs/README.md)** - Point d'entrée principal de la documentation
- **[Architecture du système](docs/architecture/README.md)** - Architecture hiérarchique et patterns d'orchestration
- **[Guides d'utilisation](docs/guides/README.md)** - Tutoriels et guides pratiques

### Guides d'Orchestration Agentique

Le projet inclut des guides avancés sur l'orchestration d'agents intelligents :

- **[Analyse des Orchestrations Sherlock/Watson](docs/architecture/analyse_orchestrations_sherlock_watson.md)** - Analyse complète des flux d'orchestration dans les conversations agentiques entre Sherlock Holmes et Dr. Watson, incluant leurs interactions, outils utilisés, et l'usage des solvers Tweety
- **[Guide des Patterns d'Orchestration](docs/guides/GUIDE_PATTERNS_ORCHESTRATION_MODES.md)** - Guide complet des patterns d'orchestration utilisés dans le projet, incluant 5 types d'orchestration distincts avec leurs templates de communication et bonnes pratiques

Ces guides sont basés sur l'analyse de sessions de développement réelles et offrent des patterns reproductibles pour l'orchestration d'agents intelligents dans des projets complexes.

