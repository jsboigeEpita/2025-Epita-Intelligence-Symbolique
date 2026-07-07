# 🏃‍♂️ Runners et Validation Web - Guide Complet

Guide complet des runners de haut niveau pour la validation web et les tests Playwright.

## 🎯 **Runners Disponibles**

### **1. PlaywrightRunner (RECOMMANDÉ)**
```bash
# Localisation
scripts/webapp/playwright_runner.py

# Usage via validateur de haut niveau
python validate_jtms_web_interface.py
```

**Fonctionnalités :**
- ✅ Exécution asynchrone non-bloquante
- ✅ Configuration runtime dynamique
- ✅ Capture screenshots et traces automatique
- ✅ Gestion modes headless/headed
- ✅ Rapports de résultats détaillés
- ✅ Intégration environnement conda

### **2. UnifiedWebOrchestrator**
```bash
# Localisation
scripts/webapp/unified_web_orchestrator.py

# Usage
python scripts/webapp/unified_web_orchestrator.py --integration --visible
```

**Fonctionnalités :**
- ✅ Orchestration complète backend/frontend
- ✅ Démarrage/arrêt automatique des services
- ✅ Failover de ports
- ✅ Nettoyage automatique des processus

## 🧪 **Validateurs Spécialisés**

### **JTMS Web Interface Validator**
```bash
# Fichier principal
validate_jtms_web_interface.py

# Exécution
python validate_jtms_web_interface.py
```

**Coverage :**
- Dashboard JTMS avec visualisation réseau
- Gestion des sessions JTMS
- Interface Sherlock/Watson
- Tutoriel interactif
- Playground JTMS
- API et communication
- Tests de performance

## 📁 **Structure Recommandée**

```
validation/
├── web_interface/
│   ├── validate_jtms_web_interface.py    # ⭐ Validateur JTMS
│   ├── validate_sherlock_watson.py       # Validateur Agents
│   └── validate_api_backend.py           # Validateur API
├── runners/
│   ├── playwright_runner.py              # ⭐ Runner Playwright
│   ├── unified_web_orchestrator.py       # Orchestrateur complet
│   └── backend_manager.py                # Gestionnaire backend
└── docs/
    ├── RUNNERS_ET_VALIDATION_WEB.md      # ⭐ Ce guide
    └── GUIDE_TESTS_PLAYWRIGHT.md         # Guide tests spécifiques
```

## 🚀 **Exemples d'Usage**

### **Validation JTMS Complète**
```python
from validation.web_interface.validate_jtms_web_interface import JTMSWebValidator

async def main():
    validator = JTMSWebValidator()
    results = await validator.validate_web_interface()
    return results['success']
```

### **Tests Playwright Directs**
```python
from scripts.webapp.playwright_runner import PlaywrightRunner

config = {
    'enabled': True,
    'headless': False,
    'test_paths': ['tests_playwright/tests/jtms-interface.spec.js']
}

runner = PlaywrightRunner(config, logger)
success = await runner.run_tests()
```

## ⚠️ **Anti-Patterns à Éviter**

### ❌ **Commands Bloquantes**
```bash
# NE PAS FAIRE
cd tests_playwright && npm run test -- tests/jtms-interface.spec.js --headed
python interface_web/app.py  # Bloque le terminal
```

### ✅ **Approche Recommandée**
```bash
# FAIRE
python validate_jtms_web_interface.py  # Asynchrone
python scripts/webapp/unified_web_orchestrator.py --integration
```

## 🔧 **Configuration**

### **Fichier de Configuration Type**
```yaml
# config/webapp_config.yml
playwright:
  enabled: true
  browser: chromium
  headless: false
  timeout_ms: 15000
  test_paths:
    - "tests_playwright/tests/jtms-interface.spec.js"
  screenshots_dir: "logs/screenshots"
  traces_dir: "logs/traces"

backend:
  ports: [5003, 5004, 5005, 5006]
  timeout_seconds: 30

frontend:
  enabled: false
  port: 3000
```

## 📊 **Monitoring et Logs**

### **Localisation des Logs**
```
logs/
├── screenshots/
│   └── jtms/              # Screenshots tests JTMS
├── traces/
│   └── jtms/              # Traces Playwright
└── webapp_integration_trace.md  # Trace orchestrateur
```

### **Analyse des Résultats**
```bash
# Rapport HTML Playwright
tests_playwright/playwright-report/index.html

# Logs détaillés
tail -f logs/uvicorn_stdout_*.log
tail -f logs/uvicorn_stderr_*.log
```

## 🎯 **Intégration CI/CD**

### **Script CI Recommandé**
```yaml
# .github/workflows/web-validation.yml
name: Web Interface Validation

on: [push, pull_request]

jobs:
  validate-web:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        cd tests_playwright && npm install
    - name: Run JTMS Web Validation
      run: python validate_jtms_web_interface.py
```

## 🔍 **Troubleshooting**

### **Problèmes Courants**

1. **Interface bloquée**
   ```bash
   # Solution : Utiliser le runner asynchrone
   python validate_jtms_web_interface.py
   ```

2. **Ports occupés**
   ```bash
   # Solution : Nettoyage automatique via orchestrateur
   python scripts/webapp/unified_web_orchestrator.py --stop
   ```

3. **Tests échouent**
   ```bash
   # Diagnostic : Mode visible
   # Dans validate_jtms_web_interface.py
   'headless': False
   ```

## 📚 **Références**

- [Guide de Démarrage Rapide](./GUIDE_DEMARRAGE_RAPIDE_PROJET_EPITA.md)
- [Architecture Hiérarchique](../architecture/ARCHITECTURE_HIERARCHIQUE_3_NIVEAUX.md)
- [Composants React](COMPOSANTS_REACT_SOPHISTIQUES.md)
- Tests Playwright

---

**🎉 Dernière mise à jour : 11/06/2025**
**✅ Validé avec : JTMS Web Interface Validation Phase 1**