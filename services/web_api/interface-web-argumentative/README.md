# Interface Web pour l'Analyse Argumentative

Cette interface utilisateur, développée avec React, permet d'interagir avec l'API d'analyse argumentative pour visualiser et explorer les analyses de textes, la détection de sophismes, et d'autres fonctionnalités liées.

## Démarrage Rapide (Local Development)

Pour lancer l'interface en mode développement local, suivez ces étapes :

1.  **Prérequis :**
    *   Node.js et npm (ou yarn) installés.
    *   Le backend Flask (défini dans `../../app.py` par rapport à ce README, ou [`services/web_api/app.py`](./services/web_api/app.py:1) depuis la racine du projet) doit être en cours d'exécution. Veuillez consulter le `README.md` principal du projet pour les instructions de lancement du backend.

2.  **Installer les dépendances frontend :**
    Naviguez vers le répertoire de l'interface (`services/web_api/interface-web-argumentative/`) et installez les dépendances :
    ```bash
    npm install
    ```
    (ou `yarn install` si vous utilisez yarn)

3.  **Lancer le serveur de développement frontend :**
    Une fois les dépendances installées, lancez le serveur de développement :
    ```bash
    npm start
    ```
    (ou `yarn start`)

    L'application devrait s'ouvrir automatiquement dans votre navigateur par défaut, généralement à l'adresse `http://localhost:3000`.
### Commandes One-Liner (depuis la racine du projet)

Si vous souhaitez lancer les serveurs backend et frontend rapidement depuis des terminaux positionnés à la racine du projet (`C:\dev\2025-Epita-Intelligence-Symbolique`), vous pouvez utiliser les commandes PowerShell suivantes :

*   **Pour démarrer le serveur Backend :**
    ```powershell
    powershell -Command ".\activate_project_env.ps1 -CommandToRun 'python .\argumentation_analysis\services\web_api\start_api.py --port 5003'"
    ```

*   **Pour démarrer le serveur Frontend :**
    ```powershell
    powershell -Command ".\activate_project_env.ps1 -CommandToRun 'cd services/web_api/interface-web-argumentative && npm start'"
    ```
    *(Note : Cette commande utilise `activate_project_env.ps1` pour la cohérence avec la demande, bien que l'environnement Conda ne soit pas strictement nécessaire pour `npm start`. La commande `cd` est exécutée dans le contexte de `conda run`.)*

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
## Build pour Production

Pour générer les fichiers statiques de l'application en vue d'un déploiement en production :

1.  **Exécuter la commande de build :**
    Dans le répertoire `services/web_api/interface-web-argumentative/`, lancez la commande suivante :
    ```bash
    npm run build
    ```
    (ou `yarn build`)

    Les fichiers optimisés pour la production seront générés dans le dossier `build` (ou `dist` selon la configuration de votre projet React). Ces fichiers peuvent ensuite être déployés sur un serveur web statique.
