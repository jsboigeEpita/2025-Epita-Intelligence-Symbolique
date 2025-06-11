# Guide Administrateur : Système d'Analyse d'Argumentation JTMS

**Version :** 1.0  
**Date :** 11 Juin 2025  
**Public Cible :** Administrateurs Système, Équipe Technique EPITA

---

## 1. Introduction

Ce guide fournit les instructions nécessaires pour déployer, configurer et maintenir le système d'analyse d'argumentation JTMS. Une connaissance de base de Python, des serveurs web (Flask/FastAPI), de `git` et de la gestion d'environnements est requise.

---

## 2. Installation et Déploiement

Le processus d'installation se déroule en 5 étapes clés.

### Étape 1 : Prérequis
-   Serveur Linux (Ubuntu 22.04 LTS recommandé)
-   Python 3.10+
-   Git

### Étape 2 : Récupération du Code
Clonez le dépôt Git du projet :
```bash
git clone [URL_DU_DEPOT_GIT]
cd [NOM_DU_REPERTOIRE]
```

### Étape 3 : Création de l'Environnement Python
Il est fortement recommandé d'utiliser un environnement virtuel.
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Étape 4 : Configuration
La configuration se gère via des variables d'environnement. Créez un fichier `.env` à la racine du projet.

**Fichier `.env` minimal :**
```dotenv
# Clé API pour le service LLM (OpenAI, Azure, etc.)
OPENAI_API_KEY="sk-..."

# Modèle LLM à utiliser
OPENAI_MODEL_NAME="gpt-4o-mini"

# Mode de déploiement (development ou production)
APP_ENV="production"

# Secret key pour les sessions Flask
FLASK_SECRET_KEY="une_cle_secrete_tres_longue_et_aleatoire"
```
**Important :** En mode `production`, le mode debug des serveurs sera désactivé.

### Étape 5 : Lancement des Services
Pour un déploiement en production, il est recommandé d'utiliser un serveur web robuste comme `gunicorn` pour les applications Flask/FastAPI.

**Lancer le serveur API (FastAPI) :**
```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker argumentation_analysis.api.main:app -b 0.0.0.0:8000
```
(Le serveur API tourne sur le port 8000)

**Lancer le serveur Web (Flask) :**
```bash
gunicorn interface_web.app:app -b 0.0.0.0:5000
```
(L'interface web est accessible sur le port 5000)

Il est conseillé de gérer ces processus avec un gestionnaire de services comme `systemd` pour garantir qu'ils redémarrent automatiquement.

---

## 3. Monitoring et Logs

### Logs d'Application
-   Les applications Flask et FastAPI logguent leurs activités sur la sortie standard/erreur.
-   Lorsque vous utilisez `gunicorn` et `systemd`, configurez `systemd` pour rediriger ces logs vers des fichiers dédiés dans `/var/log/jtms/` ou via `journalctl`.

### Traces d'Interaction
-   Les interactions significatives des agents (comme les démos) génèrent des fichiers de trace Markdown dans le dossier `traces/`.
-   Ces fichiers sont précieux pour le débogage et l'analyse post-mortem des sessions d'investigation. Pensez à mettre en place une politique de rotation ou d'archivage pour ce dossier.

---

## 4. Maintenance et Mises à Jour

### Sauvegarde
-   **Base de Données des Sessions :** Le `JTMSService` peut être configuré pour persister les sessions (actuellement en mémoire, mais extensible). Si une base de données (ex: `redis`, `sqlite`) est ajoutée, sa sauvegarde devient critique.
-   **Fichiers de Configuration :** Sauvegardez le fichier `.env`.
-   **Logs :** Mettre en place une rotation des logs via `logrotate`.

### Mises à Jour
La mise à jour de l'application suit un processus standard :
```bash
# Se placer dans le répertoire du projet
git pull origin main  # Récupérer les dernières modifications

# Activer l'environnement virtuel
source venv/bin/activate

# Mettre à jour les dépendances
pip install -r requirements.txt

# Redémarrer les services
sudo systemctl restart jtms-api
sudo systemctl restart jtms-web
```

---

## 5. Sécurité

-   **Ne jamais commiter le fichier `.env` sur Git.** Assurez-vous que `.env` est bien présent dans votre fichier `.gitignore`.
-   **`FLASK_SECRET_KEY` :** Utilisez une clé longue et aléatoire pour sécuriser les sessions utilisateur.
-   **Dépendances :** Utilisez des outils comme `pip-audit` pour scanner régulièrement vos dépendances à la recherche de vulnérabilités connues.
-   **Exposition Réseau :** Exposez uniquement les ports nécessaires au public (généralement le port 443 via un reverse proxy comme Nginx ou Caddy, qui servira l'application web sur le port 5000). Le port de l'API (8000) ne devrait être accessible que par le serveur web.