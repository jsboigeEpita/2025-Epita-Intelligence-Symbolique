# Web API Service

## Description

Ce service expose une API web qui sert de point d'entrée principal pour interagir avec les fonctionnalités d'analyse d'argumentation du projet. Il gère les requêtes HTTP, orchestre les appels aux services principaux (analyse, logique, etc.) et sert une interface utilisateur front-end en React.

## Prérequis

Pour lancer et utiliser ce service, vous devez vous assurer que votre environnement Conda `projet-is` est activé. Cet environnement contient toutes les dépendances Python et les configurations nécessaires.

```bash
conda activate projet-is
```

## Lancement

Le service est géré via le script wrapper `scripts/launch_webapp_background.py`, qui permet de le lancer en arrière-plan, de vérifier son statut et de l'arrêter proprement.

**Pour démarrer le serveur :**
```bash
python scripts/launch_webapp_background.py start
```

**Pour vérifier le statut du serveur :**
Le script interrogera l'endpoint `/api/health` pour s'assurer que le service est non seulement démarré, mais aussi pleinement opérationnel.
```bash
python scripts/launch_webapp_background.py status
```

**Pour arrêter le serveur :**
Cette commande trouvera et terminera le processus du serveur Uvicorn.
```bash
python scripts/launch_webapp_background.py kill
```

## Configuration

### Port Personnalisé

Par défaut, l'API est lancée sur le port `5003`. Vous pouvez spécifier un port différent en définissant la variable d'environnement `WEB_API_PORT` avant de lancer le script.

Sur Windows (Command Prompt):
```batch
set WEB_API_PORT=8000
python scripts/launch_webapp_background.py start
```

Sur Windows (PowerShell):
```powershell
$env:WEB_API_PORT="8000"
python scripts/launch_webapp_background.py start
```

Sur Linux/macOS:
```bash
export WEB_API_PORT=8000
python scripts/launch_webapp_background.py start
```

## Endpoints Clés

### `/api/health`

Cet endpoint est essentiel pour le monitoring du service. Il ne se contente pas de confirmer que le serveur web est en ligne, mais il effectue également une vérification interne pour s'assurer que les services critiques sont initialisés, y compris une validation de la disponibilité de la **JVM (Java Virtual Machine)**, qui est une dépendance cruciale pour certaines fonctionnalités d'analyse.

Une réponse `200 OK` de cet endpoint garantit que l'application est prête à traiter les requêtes.