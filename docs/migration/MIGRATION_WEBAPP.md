# Migration WebApp - PowerShell vers Python

## Vue d'ensemble

Ce guide documente la migration de l'ancien système de lancement PowerShell (`start_web_application.ps1`) vers le nouveau système Python unifié (`start_webapp.py`) avec l'UnifiedWebOrchestrator.

### Avantages de la nouvelle approche

- ✅ **Multiplateforme** : Compatible Windows, Linux, macOS
- ✅ **Gestion automatique** : Activation conda automatique
- ✅ **Orchestration unifiée** : Un seul point d'entrée pour tous les composants
- ✅ **Configuration centralisée** : Fichiers YAML pour la configuration
- ✅ **Gestion d'erreurs robuste** : Logs détaillés et récupération d'erreurs
- ✅ **Interface CLI moderne** : Argparse avec aide contextuelle

---

## Comparaison des méthodes

### Ancienne méthode vs Nouvelle méthode

| Aspect | Ancien (PowerShell) | Nouveau (Python) |
|--------|---------------------|-------------------|
| **Fichier** | `.\start_web_application.ps1` | `python start_webapp.py` |
| **Plateforme** | Windows uniquement | Multiplateforme |
| **Environnement** | `.\scripts\env\activate_project_env.ps1` | Conda automatique (`projet-is`) |
| **Backend** | Flask manuel (port 5003) | UnifiedWebOrchestrator |
| **Frontend** | React manuel (port 3000) | Intégré à l'orchestrateur |
| **Configuration** | Paramètres hardcodés | Fichier YAML (`config/webapp_config.yml`) |
| **Gestion des processus** | PowerShell Jobs | Processus Python natifs |
| **Logs** | Sortie console basique | Logging Python structuré |

### Mapping des commandes

| Ancien (PowerShell) | Nouveau (Python) | Description |
|---------------------|-------------------|-------------|
| `.\start_web_application.ps1` | `python start_webapp.py --frontend` | Lance backend + frontend |
| `.\start_web_application.ps1 -BackendOnly` | `python start_webapp.py --backend-only` | Lance seulement le backend |
| `.\start_web_application.ps1 -FrontendOnly` | `python start_webapp.py --frontend` | Lance seulement le frontend |
| `.\start_web_application.ps1 -Help` | `python start_webapp.py --help` | Affiche l'aide |
| *(Non disponible)* | `python start_webapp.py --visible` | Mode debugging (browser visible) |
| *(Non disponible)* | `python start_webapp.py --config custom.yml` | Configuration personnalisée |
| *(Non disponible)* | `python start_webapp.py --no-conda` | Lancement direct sans conda |
| *(Non disponible)* | `python start_webapp.py --verbose` | Logs détaillés |

---

## Guide de migration étape par étape

### Étape 1 : Vérification des prérequis

#### 1.1 Environnement Conda
```bash
# Vérifier que l'environnement 'projet-is' existe
conda env list | grep projet-is

# Si absent, créer l'environnement
conda env create -f environment.yml
```

#### 1.2 Vérification du nouveau script
```bash
# Tester la disponibilité du nouveau script
python start_webapp.py --help
```

### Étape 2 : Migration des workflows

#### 2.1 Scripts existants

**Avant (PowerShell):**
```powershell
# Script de déploiement
.\start_web_application.ps1 -BackendOnly
```

**Après (Python):**
```bash
# Script de déploiement
python start_webapp.py --backend-only
```

#### 2.2 Configuration CI/CD

**Avant:**
```yaml
# GitHub Actions / Azure DevOps
- name: Start Web App
  run: .\start_web_application.ps1 -BackendOnly
  shell: powershell
```

**Après:**
```yaml
# GitHub Actions / Azure DevOps  
- name: Start Web App
  run: python start_webapp.py --backend-only
  shell: bash
```

### Étape 3 : Migration de la configuration

#### 3.1 Configuration centralisée

Créer/vérifier le fichier `config/webapp_config.yml` :

```yaml
# config/webapp_config.yml
webapp:
  backend:
    host: "localhost"
    port: 5003
    debug: false
  frontend:
    host: "localhost" 
    port: 3000
    auto_open: false
  orchestrator:
    timeout: 10
    headless: true
    log_level: "INFO"
```

#### 3.2 Variables d'environnement

**Avant:** Hardcodées dans le script PowerShell
**Après:** Configurables via YAML ou variables d'environnement

```bash
# Variables optionnelles
export WEBAPP_CONFIG_PATH=config/custom_config.yml
export WEBAPP_LOG_LEVEL=DEBUG
```

### Étape 4 : Test de la migration

#### 4.1 Test basique
```bash
# Test de démarrage rapide
python start_webapp.py --backend-only --timeout 2

# Vérification santé
curl http://localhost:5003/api/health
```

#### 4.2 Test complet
```bash
# Test avec frontend
python start_webapp.py --frontend --visible

# Accès interface : http://localhost:3000
```

### Étape 5 : Mise à jour de la documentation

1. **README.md** : Mettre à jour les instructions de lancement
2. **Scripts de développement** : Remplacer les appels PowerShell
3. **Documentation d'équipe** : Former les développeurs

---

## FAQ et Troubleshooting

### Questions fréquentes

#### Q: Puis-je encore utiliser l'ancien script PowerShell ?
**R:** Oui, temporairement, mais il est recommandé de migrer vers le nouveau système qui est plus robuste et multiplateforme.

#### Q: Que faire si conda n'est pas disponible ?
**R:** Utilisez l'option `--no-conda` pour un lancement direct :
```bash
python start_webapp.py --no-conda --backend-only
```

#### Q: Comment personnaliser la configuration ?
**R:** Créez un fichier YAML personnalisé et utilisez `--config` :
```bash
python start_webapp.py --config config/production.yml
```

#### Q: L'ancien frontend React fonctionne-t-il toujours ?
**R:** Oui, mais il est intégré dans l'UnifiedWebOrchestrator. Utilisez `--frontend` pour l'activer.

### Problèmes courants

#### 1. Erreur d'environnement conda

**Symptôme:**
```
❌ Environnement conda 'projet-is' non trouvé
```

**Solution:**
```bash
# Option 1: Créer l'environnement
conda env create -f environment.yml

# Option 2: Lancement direct
python start_webapp.py --no-conda
```

#### 2. Erreur d'importation UnifiedWebOrchestrator

**Symptôme:**
```
❌ Import impossible: No module named 'scripts.webapp.unified_web_orchestrator'
```

**Solution:**
```bash
# Vérifier la structure du projet
ls scripts/webapp/unified_web_orchestrator.py

# Vérifier le PYTHONPATH
export PYTHONPATH=$PWD:$PYTHONPATH
python start_webapp.py
```

#### 3. Port déjà utilisé

**Symptôme:**
```
[ERROR] Port 5003 already in use
```

**Solution:**
```bash
# Tuer les processus existants
# Windows
netstat -ano | findstr :5003
taskkill /PID <PID> /F

# Linux/macOS  
lsof -ti:5003 | xargs kill -9

# Ou modifier la configuration
python start_webapp.py --config config/custom_ports.yml
```

#### 4. Problèmes d'encodage Unicode

**Symptôme:**
```
UnicodeEncodeError: 'charmap' codec can't encode...
```

**Solution:**
Le nouveau script gère automatiquement l'UTF-8. Si le problème persiste :
```bash
# Windows
set PYTHONIOENCODING=utf-8
python start_webapp.py

# Linux/macOS
export LANG=en_US.UTF-8
python start_webapp.py
```

#### 5. Problèmes de permissions

**Symptôme:**
```
PermissionError: [Errno 13] Permission denied
```

**Solution:**
```bash
# Vérifier les permissions du répertoire
chmod +x start_webapp.py

# Ou lancer avec python explicite
python ./start_webapp.py
```

---

## Architecture technique

### Comparaison architecturale

#### Ancien système (PowerShell)

```
start_web_application.ps1
├── activate_project_env.ps1
├── Start-Backend (PowerShell Job)
│   └── Flask App (port 5003)
├── Start-Frontend (PowerShell Job)  
│   └── React Dev Server (port 3000)
└── Job Management & Cleanup
```

#### Nouveau système (Python)

```
start_webapp.py
├── Conda Environment Activation
├── UnifiedWebOrchestrator
│   ├── Backend Components
│   │   ├── Flask API
│   │   ├── Service Manager
│   │   └── Health Monitoring
│   ├── Frontend Components (optionnel)
│   │   ├── React Build/Serve
│   │   └── Static Assets
│   └── Orchestration Logic
│       ├── Process Management
│       ├── Configuration Loading
│       └── Error Recovery
```

### Avantages architecturaux

1. **Modularité** : Composants séparés et réutilisables
2. **Extensibilité** : Facile d'ajouter de nouveaux services
3. **Robustesse** : Gestion d'erreurs et récupération automatique
4. **Observabilité** : Logs structurés et monitoring intégré
5. **Configuration** : Système de configuration centralisé et flexible

### Points d'intégration

#### Configuration partagée
```yaml
# config/webapp_config.yml
shared:
  log_level: INFO
  timeout: 300
  
backend:
  api_routes: "/api"
  cors_origins: ["http://localhost:3000"]
  
frontend:
  api_base_url: "http://localhost:5003"
  theme: "default"
```

#### Services communs
- **Service Manager** : Gestion unifiée des services
- **Configuration Manager** : Chargement et validation config
- **Health Monitor** : Surveillance de santé des composants
- **Error Handler** : Gestion centralisée des erreurs

---

## Prochaines étapes recommandées

### Immédiat (Semaine 1)
1. ✅ Tester le nouveau script sur l'environnement de dev
2. ✅ Mettre à jour les scripts de développement locaux
3. ✅ Former l'équipe aux nouvelles commandes

### Court terme (Semaine 2-3)
1. 🔄 Migrer les scripts CI/CD
2. 🔄 Mettre à jour la documentation
3. 🔄 Configurer les environnements de test

### Moyen terme (Mois 1)
1. 📋 Déprécier l'ancien script PowerShell
2. 📋 Optimiser la configuration pour la production
3. 📋 Mettre en place le monitoring avancé

### Long terme (Mois 2+)
1. 🎯 Supprimer complètement l'ancien système
2. 🎯 Intégrer des fonctionnalités avancées
3. 🎯 Documentation complète du nouveau système

---

## Ressources et liens utiles

### Documentation
- [Configuration Guide](config/README.md)
- [UnifiedWebOrchestrator API](docs/api/unified_web_orchestrator.md)
- [Troubleshooting Guide](docs/troubleshooting.md)

### Scripts utiles
- **Validation environnement** : `python -c "import scripts.webapp.unified_web_orchestrator; print('✅ Import OK')"`
- **Test configuration** : `python start_webapp.py --config config/test.yml --timeout 1`
- **Diagnostic complet** : `python start_webapp.py --verbose --no-conda`

### Support
- **Issues GitHub** : [Créer un ticket](../../issues)
- **Documentation équipe** : [Wiki interne](../../wiki)
- **Contact** : equipe-dev@projet-is.fr

---

*Guide mis à jour le 08/06/2025 - Version 1.0.0*