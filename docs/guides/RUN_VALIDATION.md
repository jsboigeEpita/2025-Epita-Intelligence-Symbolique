# 🏃‍♂️ Guide Rapide - Runners et Validation

Guide d'accès rapide aux runners et validateurs organisés.

## 🧪 **Validation JTMS (RECOMMANDÉ)**

### **Option 1 : Raccourci Rapide**
```bash
python validate_jtms.py
```

### **Option 2 : Validateur Complet**
```bash
python validation/web_interface/validate_jtms_web_interface.py
```

## 🎯 **Autres Validations**

### **Tests Playwright Directs**
```bash
cd tests_playwright
npm run test:flask      # Interface Flask
npm run test:api        # API Backend
npm run test            # Tous les tests
```

### **Orchestrateur Web Complet**
```bash
python scripts/webapp/unified_web_orchestrator.py --integration --visible
```

## 📁 **Structure Organisée**

```
🏠 Racine/
├── validate_jtms.py                          # ⭐ Raccourci validation JTMS
├── validation/
│   ├── web_interface/
│   │   └── validate_jtms_web_interface.py    # ⭐ Validateur JTMS complet
│   ├── runners/
│   │   └── playwright_runner.py              # ⭐ Runner Playwright
│   └── README.md                             # Guide validation
├── scripts/webapp/
│   ├── unified_web_orchestrator.py           # Orchestrateur complet
│   └── playwright_runner.py                  # Runner source
└── docs/
    ├── RUNNERS_ET_VALIDATION_WEB.md          # ⭐ Guide runners
    └── GUIDE_DEMARRAGE_RAPIDE.md             # Guide démarrage
```

## 🚀 **Pour les Développeurs**

### **Ajouter un Nouveau Validateur**
1. Créer dans `validation/web_interface/`
2. Utiliser `PlaywrightRunner` comme base
3. Ajouter raccourci à la racine si nécessaire

### **Runner Personnalisé**
1. Copier depuis `scripts/webapp/`
2. Modifier dans `validation/runners/`
3. Importer dans les validateurs

## 📚 **Documentation Complète**

- **[Guide Runners Complet](./RUNNERS_ET_VALIDATION_WEB.md)**
- **[Guide Démarrage Rapide](./GUIDE_DEMARRAGE_RAPIDE_PROJET_EPITA.md)**
- **[Architecture 3 Niveaux](../architecture/ARCHITECTURE_HIERARCHIQUE_3_NIVEAUX.md)**

---

**🎉 Structure organisée le : 11/06/2025**
**✅ Prêt pour la validation JTMS Phase 1**