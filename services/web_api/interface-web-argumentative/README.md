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

## Build pour Production

Pour générer les fichiers statiques de l'application en vue d'un déploiement en production :

1.  **Exécuter la commande de build :**
    Dans le répertoire `services/web_api/interface-web-argumentative/`, lancez la commande suivante :
    ```bash
    npm run build
    ```
    (ou `yarn build`)

    Les fichiers optimisés pour la production seront générés dans le dossier `build` (ou `dist` selon la configuration de votre projet React). Ces fichiers peuvent ensuite être déployés sur un serveur web statique.
