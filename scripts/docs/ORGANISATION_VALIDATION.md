# Organisation des Scripts de Validation
## Projet Intelligence Symbolique EPITA 2025

### 📁 Structure Organisée

```
scripts/
├── validation/          # Scripts de validation finaux et utiles
├── archived/           # Scripts obsolètes et doublons
├── temp/               # Scripts temporaires/tests
└── core/               # Scripts fondamentaux (auto_env, environment_manager)
```

### ✅ Scripts Conservés (`validation/`)

| Script | Description | Usage |
|--------|-------------|--------|
| `validation_environnement_simple.py` | ✨ **PRINCIPAL** - Validation d'environnement simplifiée | Test environnement conda, .env, Java JDK17 |
| `validation_cluedo_final_fixed.py` | ✨ **FINAL** - Validation Cluedo corrigée | Démos Cluedo avec traces authentiques |
| `validation_einstein_traces.py` | 🧠 Validation Einstein avec traces | Démos Einstein/logique |
| `validation_traces_master_fixed.py` | 🔧 **CORRIGÉ** - Validation master Sherlock/Watson | Version corrigée du master |
| `validation_finale_success_demonstration.py` | 🎯 Démonstration finale de succès | Démo complète du système |
| `validation_complete_donnees_fraiches.py` | 📊 Validation données fraîches complète | Tests avec données réelles |
| `validation_donnees_fraiches_simple.py` | 📊 Validation données fraîches simple | Version simplifiée |
| `validation_reelle_systemes.py` | 🔍 Validation réelle des systèmes | Validation authentique |

### 📁 Scripts Archivés (`archived/`)

| Script | Raison de l'archivage | Remplacé par |
|--------|----------------------|--------------|
| `validation_environnement.py` | Version complexe obsolète | `validation_environnement_simple.py` |
| `validation_cluedo_simple.py` | Version intermédiaire | `validation_cluedo_final_fixed.py` |
| `validation_cluedo_real_authentic.py` | Version intermédiaire | `validation_cluedo_final_fixed.py` |
| `validation_cluedo_traces.py` | Fonctionnalité intégrée | `validation_cluedo_final_fixed.py` |
| `validation_traces_master.py` | Version non corrigée | `validation_traces_master_fixed.py` |

### 🚀 Usage Recommandé

#### Test Environnement
```bash
python scripts/validation/validation_environnement_simple.py
```

#### Démo Cluedo
```bash
python scripts/validation/validation_cluedo_final_fixed.py
```

#### Validation Complète
```bash
python scripts/validation/validation_finale_success_demonstration.py
```

### 📝 Historique de Nettoyage

**Date:** 10/06/2025 19:06  
**Action:** Nettoyage et organisation des scripts de validation suite aux tâches Cluedo  
**Résultat:** 
- ✅ 8 scripts utiles conservés dans `validation/`
- 📁 5 scripts obsolètes archivés dans `archived/`
- 🗑️ 0 scripts supprimés (sécurité)

### 🔧 Maintenance

- **Scripts à maintenir:** Ceux dans `validation/`
- **Scripts à ignorer:** Ceux dans `archived/` (conservation historique)
- **Nouveaux scripts:** Ajouter dans `validation/` ou `temp/` selon le statut

---
*Dernière mise à jour: 10/06/2025 - Nettoyage post-validation Cluedo*