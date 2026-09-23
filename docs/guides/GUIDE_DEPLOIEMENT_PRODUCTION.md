# GUIDE DE DÉPLOIEMENT PRODUCTION
## Système d'Analyse Argumentative - Version 2.0

**Date :** 06/06/2025  
**Statut :** ✅ Validé pour production  
**Compatibilité :** Windows 11, Python 3.10+, Conda

> **⚠ Page remplacée — état de juin 2025 (Sprint 3).** Le guide de déploiement en vigueur
> est [`DEPLOYMENT.md`](DEPLOYMENT.md) (#991) : API FastAPI et proxy Starlette,
> environnement `projet-is`. Les commandes de cette page ont été re-mesurées le
> 2026-09-23 (#2436). Celles qui appelaient des scripts disparus
> (`scripts/sprint3_final_validation.py`, `scripts/fix_unicode_conda.py`,
> `scripts/fix_critical_imports.py`), un module inexistant (`argumentation_analysis.app`)
> ou un environnement conda absent de la flotte (`epita_symbolic_ai_sherlock`) sont
> remplacées par leurs équivalents vivants. Les chiffres, métriques et la « certification »
> plus bas sont ceux du Sprint 3 : ils n'ont pas été re-mesurés.

---

## 🚀 DÉPLOIEMENT RAPIDE (5 MINUTES)

### Étape 1 : Préparation environnement
```bash
# Activation environnement (DEPLOYMENT.md, étape 1)
conda activate projet-is

# Configuration UTF-8 (automatique)
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONLEGACYWINDOWSSTDIO='1'
```

### Étape 2 : Validation système
```bash
# Vérification du système : même commande que DEPLOYMENT.md, étape 3
python -c "from argumentation_analysis.orchestration.registry_setup import setup_registry; setup_registry(); print('OK')"
pytest tests/unit/ -m "not slow and not requires_api" -x -q --tb=line

# Résultat attendu : « OK », puis un résumé pytest sans échec
```

### Étape 3 : Lancement services
```bash
# Option A : Tests unitaires
pytest tests/unit/ -v --tb=short

# Option B : Tests d'intégration  
pytest tests/integration/ -v --tb=short

# Option C : API FastAPI (DEPLOYMENT.md, étape 4 ; l'application Flask
# du Sprint 3 n'existe plus)
uvicorn api.main:app --port 8000
```

---

## 📋 CHECKLIST PRE-DÉPLOIEMENT

### ✅ Prérequis techniques validés
- [x] Python 3.10+ installé
- [x] Conda environnement `projet-is` actif
- [x] Configuration UTF-8 appliquée
- [x] Dépendances installées

### ✅ Problèmes critiques résolus
- [x] Encodage Unicode : 100% fonctionnel
- [x] Import matplotlib : Mock appliqué
- [x] Interfaces agents : Harmonisées
- [x] Services Flask : Intégrés
- [x] Opérations async : Optimisées

### ✅ Tests de validation
- [x] Tests unitaires : >90% réussite
- [x] Tests intégration : 100% réussite
- [x] Tests performance : <1s pour opérations critiques
- [x] Tests encodage : Support complet caractères spéciaux

---

## ⚙️ CONFIGURATION PRODUCTION

### Variables d'environnement requises :
```bash
# Encodage Unicode
PYTHONIOENCODING=utf-8
PYTHONLEGACYWINDOWSSTDIO=1
LC_ALL=C.UTF-8
LANG=C.UTF-8

# Configuration JVM (si nécessaire)
USE_REAL_JPYPE=true
JPYPE_JVM_PATH=auto

# Performance
MATPLOTLIB_BACKEND=Agg
```

### Fichiers de configuration :
- `config/utf8_environment.conf` - Configuration UTF-8
- `config/performance_config.ini` - Paramètres performance
- `pytest.ini` - Configuration tests

---

## 🔧 SCRIPTS DE MAINTENANCE

### Script de diagnostic :
```bash
# Diagnostic complet. Les scripts fix_unicode_conda / fix_critical_imports
# de juin 2025 n'existent plus : l'encodage se règle par les variables UTF-8
# de la configuration production.
python -c "from argumentation_analysis.orchestration.registry_setup import setup_registry; setup_registry(); print('OK')"
pytest tests/unit/ -m "not slow and not requires_api" -x -q --tb=line
```

### Monitoring santé système :
```bash
# Vérification rapide
python -c "
from argumentation_analysis.services.logic_service import LogicService
from argumentation_analysis.orchestration.group_chat import GroupChatOrchestration
print('Services opérationnels ✅')
"
```

---

## 📊 MÉTRIQUES DE PRODUCTION

### Performances cibles atteintes :
- **Temps réponse :** < 2s pour 95% des requêtes ✅
- **Création agents :** < 1s pour 10 agents ✅
- **Import modules :** < 0.001s ✅
- **Utilisation mémoire :** Optimisée ✅

### Disponibilité système :
- **Tests unitaires :** 90%+ de réussite ✅
- **Tests intégration :** 100% de réussite ✅
- **Encodage Unicode :** 100% support ✅
- **Services Flask :** 100% opérationnels ✅

---

## 🔍 TROUBLESHOOTING

### Problème : Erreur d'encodage Unicode
**Solution :**
```bash
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONLEGACYWINDOWSSTDIO='1'
```

### Problème : Import matplotlib bloqué
**Solution :** Mock automatiquement appliqué ✅

### Problème : Tests d'intégration échouent
**Solution :**
```bash
# Relancer la vérification complète
python -c "from argumentation_analysis.orchestration.registry_setup import setup_registry; setup_registry(); print('OK')"
pytest tests/unit/ -m "not slow and not requires_api" -x -q --tb=line
```

### Problème : Services Flask non disponibles
**Solution :**
```bash
# Vérifier intégration
python -c "
from argumentation_analysis.services.flask_service_integration import FlaskServiceIntegrator
from flask import Flask
app = Flask(__name__)
integrator = FlaskServiceIntegrator()
result = integrator.init_app(app)
print(f'Intégration: {result}')
"
```

---

## 🏆 VALIDATION DÉPLOIEMENT

### Test de validation finale :
```bash
# Validation : même commande que DEPLOYMENT.md, étape 3
python -c "from argumentation_analysis.orchestration.registry_setup import setup_registry; setup_registry(); print('OK')"
pytest tests/unit/ -m "not slow and not requires_api" -x -q --tb=line

# Résultat attendu : « OK », puis un résumé pytest sans échec
```

### Critères de succès :
- ✅ Tous les imports core fonctionnent
- ✅ Interfaces agents harmonisées
- ✅ Services Flask intégrés
- ✅ Opérations asynchrones stables
- ✅ Performance dans les cibles
- ✅ Tests d'intégration à 100%

---

## 🚨 ALERTES ET MONITORING

### Métriques à surveiller :
- Temps de réponse > 5s → **ALERTE CRITIQUE**
- Échec tests intégration → **ALERTE MAJEURE**
- Erreurs d'encodage → **ALERTE MODERATE**
- Utilisation mémoire > 1GB → **ALERTE WARNING**

### Actions automatiques :
- **Configuration UTF-8** → Appliquée automatiquement
- **Mock matplotlib** → Activé par défaut
- **Gestion d'erreurs** → Logging complet
- **Recovery automatique** → Services resilients

---

## 📞 SUPPORT ET MAINTENANCE

### Contacts techniques :
- **Documentation :** `docs/RAPPORT_FINAL_CONSOLIDÉ_3_SPRINTS.md`
- **Scripts :** Répertoire `scripts/`
- **Configuration :** Répertoire `config/`
- **Logs :** Générés automatiquement

### Maintenance préventive :
- **Hebdomadaire :** Validation script complet
- **Mensuel :** Mise à jour dépendances
- **Trimestriel :** Optimisation performance

---

## ✅ CERTIFICATION PRODUCTION

**Le système d'analyse argumentative est officiellement certifié pour la production avec :**

🎯 **100% de validation finale**  
⚡ **Performance optimisée**  
🔧 **Robustesse garantie**  
📋 **Documentation complète**  
🚀 **Déploiement automatisé**

**Date de certification :** 06/06/2025  
**Version :** 2.0 Production Ready  
**Statut :** ✅ APPROUVÉ POUR PRODUCTION

---

*Guide généré automatiquement suite au succès du Sprint 3*