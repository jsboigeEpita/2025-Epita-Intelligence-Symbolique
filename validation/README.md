# 🧪 Validation - Runners et Tests Web

Structure organisée pour la validation des interfaces web et des composants JTMS.

## 📁 **Structure**

```
validation/
├── web_interface/
│   ├── validate_jtms_web_interface.py    # ⭐ Validateur JTMS principal
│   ├── validate_sherlock_watson.py       # (À venir) Validateur Agents
│   └── validate_api_backend.py           # (À venir) Validateur API
├── runners/
│   ├── playwright_runner.py              # ⭐ Runner Playwright (copie)
│   └── unified_web_orchestrator.py       # (À venir) Orchestrateur (copie)
└── README.md                             # ⭐ Ce fichier
```

## 🚀 **Usage Rapide**

### **Validation JTMS Complète**
```bash
# Depuis la racine du projet
python validate_jtms.py

# Ou directement
python validation/web_interface/validate_jtms_web_interface.py
```

### **Runner Playwright Direct**
```bash
# Usage du runner de haut niveau
python -c "
import asyncio
from validation.runners.playwright_runner import PlaywrightRunner
# Configuration et usage...
"
```

## 🎯 **Validateurs Disponibles**

### **1. JTMS Web Interface Validator** ⭐
- **Fichier :** `web_interface/validate_jtms_web_interface.py`
- **Coverage :** Dashboard, Sessions, Sherlock/Watson, Tutoriel, Playground, API
- **Mode :** Asynchrone non-bloquant
- **Playwright :** Mode visible pour diagnostic

### **2. Sherlock/Watson Validator** (À développer)
- **Fichier :** `web_interface/validate_sherlock_watson.py`
- **Coverage :** Agents logiques, Cluedo, Einstein, Oracle Moriarty

### **3. API Backend Validator** (À développer)
- **Fichier :** `web_interface/validate_api_backend.py`
- **Coverage :** API FastAPI, endpoints JTMS, middleware

## 🏃‍♂️ **Runners Disponibles**

### **1. PlaywrightRunner** ⭐
- **Source :** `scripts/webapp/playwright_runner.py`
- **Copie :** `runners/playwright_runner.py`
- **Mode :** Asynchrone, configuration runtime, captures automatiques

### **2. UnifiedWebOrchestrator** 
- **Source :** `scripts/webapp/unified_web_orchestrator.py`
- **Features :** Orchestration complète, failover ports, nettoyage auto

## 📚 **Documentation**

- **Guide Principal :** [`docs/RUNNERS_ET_VALIDATION_WEB.md`](../docs/RUNNERS_ET_VALIDATION_WEB.md)
- **Guide Démarrage :** [`docs/GUIDE_DEMARRAGE_RAPIDE.md`](../docs/GUIDE_DEMARRAGE_RAPIDE.md)
- **Architecture :** [`docs/ARCHITECTURE_HIERARCHIQUE_3_NIVEAUX.md`](../docs/ARCHITECTURE_HIERARCHIQUE_3_NIVEAUX.md)

## ⚡ **Exemples Pratiques**

### **Test JTMS Complet**
```python
# validation/web_interface/validate_jtms_web_interface.py
from validation.runners.playwright_runner import PlaywrightRunner

validator = JTMSWebValidator()
results = await validator.validate_web_interface()
```

### **Configuration Custom**
```python
config = {
    'headless': False,  # Mode visible
    'browser': 'chromium',
    'timeout_ms': 15000,
    'test_paths': ['tests_playwright/tests/jtms-interface.spec.js']
}
```

## 🔧 **Développement**

### **Ajouter un Nouveau Validateur**
1. Créer le fichier dans `web_interface/`
2. Hériter de la structure existante
3. Utiliser `PlaywrightRunner` pour les tests
4. Mettre à jour ce README

### **Personnaliser un Runner**
1. Copier depuis `scripts/webapp/`
2. Modifier dans `runners/`
3. Adapter les imports dans les validateurs

---

**🎉 Structure créée le : 11/06/2025**
**✅ Validé avec : JTMS Web Interface Validation Phase 1**