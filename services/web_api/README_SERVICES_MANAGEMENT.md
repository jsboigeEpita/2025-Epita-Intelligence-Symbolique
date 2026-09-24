# 🚀 Gestion des Services Web - Scripts Python Cross-Platform

## Vue d'ensemble

Cette solution remplace les anciens scripts PowerShell par des **scripts Python cross-platform** qui utilisent l'infrastructure existante `UnifiedWebOrchestrator` pour une gestion professionnelle des services backend/frontend.

## 📁 Scripts disponibles

### 1. `start_full_system.py` - Système complet Backend + Frontend
```bash
# Démarrage complet (backend api.main:app + frontend React) et tests d'intégration
python services/web_api/start_full_system.py

# Mode visible pour debugging
python services/web_api/start_full_system.py --visible

# Sans tests automatiques
python services/web_api/start_full_system.py --skip-tests
```

Le script délègue à `python -m argumentation_analysis.webapp.orchestrator --frontend`.
Les ports viennent de `argumentation_analysis/webapp/config/webapp_config.yml`
(les options `--backend-port` / `--frontend-port` ont été retirées, #2529).

**Fonctionnalités :**
- ✅ Démarrage automatique du backend `api.main:app` (port 5003, avec repli)
- ✅ Démarrage automatique frontend React (port 3000)
- ✅ Gestion du timing et des dépendances
- ✅ Tests d'intégration automatiques
- ✅ Surveillance continue avec health checks
- ✅ Ouverture optionnelle du navigateur

### 2. `start_simple_only.py` - Backend seul
```bash
# Backend api.main:app seul, sans frontend React
python services/web_api/start_simple_only.py

# Port personnalisé
python services/web_api/start_simple_only.py --port 5004

# Redémarrage automatique quand le code change
python services/web_api/start_simple_only.py --reload
```

**Fonctionnalités :**
- ✅ Sert le backend de `webapp_config.yml` (`api.main:app`) avec uvicorn
- ✅ Port par défaut : le `start_port` de la configuration (5003)

L'interface simple Flask que ce script démarrait a été archivée sous #322
(`docs/archives/web_api_legacy_317/interface-simple`) ; les options `--debug` et
`--skip-servicemanager-check` ont été retirées avec elle (#2529).

### 3. `stop_all_services.py` - Arrêt propre de tous les services
```bash
# Arrêt propre (SIGTERM puis SIGKILL si nécessaire)
python services/web_api/stop_all_services.py

# Arrêt forcé immédiat (SIGKILL)
python services/web_api/stop_all_services.py --force

# Ports spécifiques
python services/web_api/stop_all_services.py --ports 3000 5000 8080
```

**Fonctionnalités :**
- ✅ Détection automatique des processus par ports
- ✅ Détection des processus webapp par mots-clés
- ✅ Arrêt propre avec fallback forcé
- ✅ Nettoyage des fichiers PID
- ✅ Utilisation du `ProcessCleaner` existant
- ✅ Vérification finale

### 4. `health_check.py` - Monitoring et diagnostics
```bash
# Check de santé standard
python services/web_api/health_check.py

# Check détaillé avec métriques
python services/web_api/health_check.py --detailed

# Surveillance continue
python services/web_api/health_check.py --continuous --interval 30

# Sauvegarde du rapport
python services/web_api/health_check.py --detailed --save-report
```

**Fonctionnalités :**
- ✅ Vérification des processus sur ports standards
- ✅ Tests des endpoints (/status, /analyze, etc.)
- ✅ Vérification ServiceManager et analyseurs
- ✅ Métriques de performance (CPU, RAM, temps de réponse)
- ✅ Mode surveillance continue
- ✅ Rapports JSON exportables

## 🔄 Workflows typiques

### Démarrage pour développement
```bash
# 1. Démarrage système complet
python services/web_api/start_full_system.py --visible

# 2. Vérification santé
python services/web_api/health_check.py --detailed

# 3. Arrêt propre quand terminé
python services/web_api/stop_all_services.py
```

### Test du backend seul
```bash
# 1. Backend seul
python services/web_api/start_simple_only.py --reload

# 2. Surveillance continue
python services/web_api/health_check.py --continuous

# 3. Arrêt
python services/web_api/stop_all_services.py
```

### Production/Intégration continue
```bash
# 1. Démarrage headless sans tests
python services/web_api/start_full_system.py --skip-tests

# 2. Health check avec rapport
python services/web_api/health_check.py --save-report

# 3. Arrêt forcé si nécessaire
python services/web_api/stop_all_services.py --force
```

## 🏗️ Architecture technique

### Réutilisation de l'infrastructure existante
- **`UnifiedWebOrchestrator`** : Orchestrateur principal
- **`BackendManager`** : Gestion du backend ServiceManager
- **`FrontendManager`** : Gestion du frontend React
- **`PlaywrightRunner`** : Tests d'intégration automatiques
- **`ProcessCleaner`** : Nettoyage des processus

### Gestion des ports intelligente
- **Détection automatique** des ports libres
- **Fallback** sur ports alternatifs si occupation
- **Support ports personnalisés** via paramètres

### Monitoring avancé
- **Health checks** avec métriques temps réel
- **Surveillance continue** avec alertes
- **Rapports JSON** exportables
- **Intégration psutil** pour métriques système

## 🚨 Gestion d'erreurs et fallbacks

### ServiceManager indisponible
- ✅ **Mode dégradé automatique** pour interface simple
- ✅ **Fallback analyseurs basiques** si sophismes indisponibles
- ✅ **Messages clairs** sur les limitations

### Ports occupés
- ✅ **Détection automatique** ports libres
- ✅ **Suggestions alternatives** (3001, 5001, etc.)
- ✅ **Configuration flexible** via paramètres

### Processus orphelins
- ✅ **Détection intelligente** par ports et mots-clés
- ✅ **Nettoyage automatique** avec ProcessCleaner
- ✅ **Arrêt gracieux** puis forcé si nécessaire

## 📊 Logs et monitoring

### Fichiers générés
- `logs/health_report_YYYYMMDD_HHMMSS.json` : Rapports santé
- `scripts/webapp/logs/webapp_integration_trace.md` : Traces intégration
- `scripts/webapp/backend_info.json` : Infos backend actuel

### Surveillance temps réel
```bash
# Surveillance continue avec intervalle personnalisé
python services/web_api/health_check.py --continuous --interval 15

# Sortie exemple :
[15:30:45] Port 3000: ✅ | Port 5000: ✅
[15:31:00] Port 3000: ✅ | Port 5000: ✅
```

## 🔧 Intégration avec l'écosystème existant

### Scripts unifiés compatibility
Ces scripts sont **100% compatibles** avec l'écosystème Python existant :
- ✅ `scripts/run_webapp_integration.py`
- ✅ `scripts/migrate_to_unified.py`
- ✅ Configuration centralisée YAML
- ✅ Gestionnaire de ports centralisé

### Commandes de migration depuis PowerShell

| Ancien PowerShell | Nouveau Python |
|-------------------|----------------|
| `start_full_system.ps1` | `python services/web_api/start_full_system.py` |
| `start_simple_only.ps1` | `python services/web_api/start_simple_only.py` |
| `stop_all_services.ps1` | `python services/web_api/stop_all_services.py` |
| `health_check.ps1` | `python services/web_api/health_check.py` |

## 🎯 Avantages de cette approche

### ✅ Cross-platform natif
- **Windows, Linux, macOS** sans modification
- **Pas de dépendance PowerShell** 
- **Réutilisation infrastructure Python** existante

### ✅ Maintenance simplifiée  
- **Un seul langage** pour tout l'écosystème
- **Réutilisation code** au lieu de duplication
- **Tests intégrés** dans l'infrastructure existante

### ✅ Robustesse professionnelle
- **Gestion d'erreurs avancée** avec fallbacks intelligents
- **Monitoring temps réel** avec métriques détaillées
- **Intégration continue** compatible

### ✅ Developer Experience
- **Paramètres flexibles** pour tous les cas d'usage
- **Messages clairs** et documentation intégrée
- **Debugging facilité** avec modes verbose

---

**Cette solution remplace complètement les anciens scripts PowerShell tout en offrant plus de fonctionnalités et une meilleure intégration avec l'écosystème Python existant.**