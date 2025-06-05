# Projet d'Analyse d'Argumentation

Ce projet contient une application web pour l'analyse d'argumentation, composée d'un backend Flask et d'un frontend React.

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

    **Alternative : Utilisation du script d'environnement**

    Vous pouvez également utiliser le script fourni à la racine du projet pour activer l'environnement Conda et configurer PYTHONPATH pour la session PowerShell actuelle :
    ```powershell
    .\setup_project_env.ps1
    ```
    Pour exécuter une commande spécifique directement après l'activation (par exemple, démarrer le serveur) :
    ```powershell
    .\setup_project_env.ps1 -CommandToRun "python .\argumentation_analysis\services\web_api\start_api.py --port 5003"
    ```
    Il existe également un script `setup_project_env.sh` pour les environnements bash/zsh.

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

Vous devez démarrer le backend PUIS le frontend dans des terminaux séparés.

### 1. Démarrer le Backend (Serveur Flask)
Assurez-vous que votre environnement Conda (`projet-is`) est activé et que `PYTHONPATH` est correctement configuré (voir section Configuration).

Depuis la **racine du projet** (`C:\dev\2025-Epita-Intelligence-Symbolique`), exécutez :
```bash
python .\argumentation_analysis\services\web_api\start_api.py --port 5003
```
Le serveur backend devrait démarrer sur `http://localhost:5003`.

### 2. Démarrer le Frontend (Client React)
Depuis le répertoire **client** (`C:\dev\2025-Epita-Intelligence-Symbolique\services\web_api\interface-web-argumentative\`), exécutez :
```bash
npm start
```
L'application React devrait s'ouvrir automatiquement dans votre navigateur à l'adresse `http://localhost:3000` (ou un autre port si 3000 est occupé). L'interface client communiquera avec le backend sur le port 5003.

## Parcours de test de l'interface

Cette section décrit un parcours de test simple pour vérifier les fonctionnalités de base de l'application.

### 1. Accès à l'application
1.  Assurez-vous que le backend et le frontend sont démarrés (voir la section "Démarrage de l'application").
2.  Ouvrez votre navigateur et accédez à l'URL du frontend (généralement `http://localhost:3000`).

    *   **Résultat attendu :** La page d'accueil de l'application d'analyse d'argumentation s'affiche sans erreur. L'interface est prête à recevoir une entrée.

### 2. Soumettre un texte pour analyse (Exemple de fonctionnalité)
1.  Localisez la zone de saisie de texte sur l'interface.
2.  Entrez un texte argumentatif simple. Par exemple :
    `"Les énergies renouvelables sont cruciales pour l'avenir. Elles réduisent notre dépendance aux fossiles et combattent le changement climatique."`
3.  Cliquez sur le bouton "Analyser" ou "Soumettre".

    *   **Résultat attendu :**
        *   L'interface envoie le texte au backend.
        *   Après un court instant, les résultats de l'analyse s'affichent.
        *   Cela pourrait inclure :
            *   L'identification des prémisses et de la conclusion.
            *   Une visualisation des arguments.
            *   Un score de cohérence ou de force argumentative (selon les fonctionnalités implémentées).
        *   Aucun message d'erreur ne doit apparaître.

### 3. Interaction avec les résultats (Exemple de fonctionnalité)
1.  Si l'analyse affiche des éléments cliquables ou des options de filtrage :
    *   Essayez de cliquer sur un argument identifié.
    *   Si des filtres sont disponibles, essayez de les appliquer.

    *   **Résultat attendu :**
        *   L'interface réagit de manière appropriée aux interactions.
        *   Cliquer sur un argument pourrait afficher plus de détails ou le mettre en évidence.
        *   Les filtres modifient la présentation des résultats comme attendu.

*(N.B. : Ce parcours est un exemple. Veuillez l'adapter et le compléter avec les fonctionnalités spécifiques de votre application et les résultats précis que vous attendez pour votre démo.)*
