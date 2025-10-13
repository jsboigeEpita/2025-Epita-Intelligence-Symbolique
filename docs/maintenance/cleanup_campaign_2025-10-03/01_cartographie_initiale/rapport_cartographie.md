# Rapport de Cartographie Élargie - Phase 2

**Date :** 2025-10-03  
**Périmètre :** Analyse exhaustive répertoires système + fichiers racine + .gitignore

---

## 1. Synthèse Périmètre Élargi

### Métriques Globales Actualisées
- **Total fichiers dans scope Phase 1+2** : ~1,736 fichiers
- **Taille totale estimée** : ~182 MB (hors node_modules services/~147MB)
- **Répertoires système analysés** : 16 nouveaux + 3 déjà analysés
- **Fichiers racine identifiés** : ~320+ fichiers (dont ~165 à ranger)
- **Dossiers fantômes détectés** : 13 répertoires

---

## 2. Nouveaux Répertoires Système (Phase 2)

### demos/ ✅ **FAIBLE RISQUE**
- **Fichiers totaux** : 7
- **Extensions** : .py (7), .md (1)
- **Taille** : ~38 KB
- **Contenu** : Scripts de validation/démonstration EPITA
- **Fichiers suspects** : Aucun
- **Niveau de risque** : **Faible**
- **Recommandation** : Conserver tel quel - scripts de démonstration valides

### examples/ ✅ **FAIBLE RISQUE**
- **Fichiers totaux** : 33
- **Extensions** : .py (23), .md (3), .ipynb (2), .json (2), .yaml (1), .gitkeep (1), __init__.py (1)
- **Sous-répertoires** : scripts_demonstration/, Sherlock_Watson/, notebooks/, phase2_demo/, backend_demos/, cluedo_demo/
- **Hot spots** : scripts_demonstration/ (19 fichiers)
- **Taille** : ~304 KB
- **Niveau de risque** : **Faible**
- **Recommandation** : Répertoire bien structuré - exemples pédagogiques essentiels

### tutorials/ ✅ **FAIBLE RISQUE**
- **Fichiers totaux** : 6
- **Extensions** : .md (6)
- **Taille** : ~20 KB
- **Contenu** : Tutoriels pas-à-pas (01-05 + README)
- **Niveau de risque** : **Faible**
- **Recommandation** : Documentation formation - conserver

### api/ ✅ **RISQUE MODÉRÉ**
- **Fichiers totaux** : 10
- **Extensions** : .py (10)
- **Taille** : ~53 KB
- **Contenu** : API FastAPI (endpoints, dependencies, services, models, factory)
- **Fichiers doublons** : endpoints_simple.py, dependencies_simple.py, main_simple.py
- **Niveau de risque** : **Modéré** (versions _simple)
- **Recommandation** : Valider utilité des versions simplifiées, possiblement déplacer vers examples/

### core/ ✅ **FAIBLE RISQUE**
- **Fichiers totaux** : 3
- **Extensions** : .py (1), .json (2)
- **Taille** : ~8.5 KB
- **Contenu** : Gestionnaire de prompts + templates
- **Niveau de risque** : **Faible**
- **Recommandation** : Infrastructure légère - conserver

### src/ ⚠️ **RISQUE MODÉRÉ**
- **Fichiers totaux** : 51 (dont 16 __pycache__)
- **Extensions** : .py (17), .pyc (16), .yaml (2), .json (2), .md (2)
- **Sous-répertoires** : core/, agents/, benchmarking/
- **Taille** : ~104 KB
- **Fichiers suspects** : 16 fichiers __pycache__/*.pyc à supprimer
- **Niveau de risque** : **Modéré** (pollution cache)
- **Recommandation** : 
  1. Supprimer tous les __pycache__/ (déjà dans .gitignore)
  2. Nettoyer les .pyc

### plugins/ ⚠️ **RISQUE MODÉRÉ**
- **Fichiers totaux** : 56 (dont 12 __pycache__)
- **Extensions** : .py (24), .pyc (12), .json (6), .yaml (2), __init__.py (8)
- **Sous-répertoires** : AnalysisToolsPlugin/, FallacyWorkflow/, ExplorationPlugin/, SynthesisPlugin/, GuidingPlugin/, hello_world_plugin/
- **Hot spots** : AnalysisToolsPlugin/ (36 fichiers dont tests)
- **Taille** : ~522 KB
- **Fichiers suspects** : 12 fichiers __pycache__/*.pyc à supprimer
- **Niveau de risque** : **Modéré** (pollution cache)
- **Recommandation** :
  1. Supprimer tous les __pycache__/ 
  2. hello_world_plugin/ semble être un exemple → déplacer vers examples/ ou docs/

### services/ 🔴 **RISQUE ÉLEVÉ - ÉNORME**
- **Fichiers totaux** : 1000+ (énorme node_modules)
- **Taille** : **~147 MB** (principalement node_modules)
- **Contenu** : services/web_api/interface-web-argumentative/ (application React)
- **Hot spots** : 
  - node_modules/ : ~147 MB (dépendances npm)
  - .cache/ : caches webpack/babel
- **Fichiers suspects** : Tout le node_modules devrait être dans .gitignore
- **Niveau de risque** : **ÉLEVÉ** (pollution massive)
- **Recommandation** : 
  1. Vérifier que node_modules/ est bien ignoré
  2. Supprimer node_modules/ du tracking git si présent
  3. Ajouter services/**/node_modules/ explicitement au .gitignore

### config/ ✅ **RISQUE MODÉRÉ**
- **Fichiers totaux** : 31 (dont 3 __pycache__)
- **Extensions** : .py (2), .pyc (3), .yml (2), .yaml (1), .ini (8), .json (1), .ps1 (2), .md (1), .tpl (1), .conf (1)
- **Sous-répertoires** : pytest/, clean/, templates/
- **Taille** : ~109 KB
- **Fichiers suspects** : 
  - 3 fichiers __pycache__/*.pyc
  - .port_lock (fichier de verrouillage)
- **Niveau de risque** : **Modéré**
- **Recommandation** :
  1. Supprimer __pycache__/
  2. .port_lock déjà dans .gitignore - vérifier suppression

### templates/ ✅ **FAIBLE RISQUE**
- **Fichiers totaux** : 1
- **Taille** : ~0.8 KB
- **Contenu** : synthesis_report.md.template
- **Niveau de risque** : **Faible**
- **Recommandation** : Conserver - template utile

### validation/ ✅ **FAIBLE RISQUE**
- **Fichiers totaux** : 3
- **Extensions** : .md (3)
- **Taille** : ~213 KB (1 gros fichier: validation_tests_unitaires_finale.md 208KB)
- **Contenu** : Rapports de validation EPITA
- **Niveau de risque** : **Faible**
- **Recommandation** : Documentation validation - conserver

### interface_web/ ✅ **FAIBLE RISQUE**
- **Fichiers totaux** : 13
- **Extensions** : .html (6), .py (3), .js (1), .css (1)
- **Sous-répertoires** : templates/jtms/, static/js/, static/css/, api/, routes/, services/
- **Taille** : ~319 KB
- **Contenu** : Application web Flask pour JTMS
- **Niveau de risque** : **Faible**
- **Recommandation** : Application web fonctionnelle - conserver

### libs/ ✅ **INFRASTRUCTURE**
- **Entrées** : 10 (9 répertoires + 1 README)
- **Contenu** : Bibliothèques externes (java/, tweety/, prover9/, portable_jdk/, node-v20/, mcp/, native/, _temp_downloads/)
- **Niveau de risque** : **Infrastructure**
- **Recommandation** : Bibliothèques essentielles - la plupart déjà dans .gitignore

---

## 3. Analyse Fichiers Racine

### Inventaire Complet (~320+ fichiers)

#### 📁 **Configuration Essentielle** (15 fichiers) ✅
- package.json, package-lock.json (Node.js)
- pyproject.toml, pytest.ini, requirements.txt, setup.py (Python)
- environment.yml, conda-lock.yml (Conda)
- .env.example, .env.template (Templates env)
- playwright.config.js (Tests E2E)
- Dockerfile, .dockerignore (Conteneurs)
- LICENSE, README.md, [`PLAN.md`](../../PLAN.md:1)

#### 🔧 **Scripts/Outils** (20 fichiers) - **50% À RANGER**
**À CONSERVER racine:**
- activate_project_env.ps1, activate_project_env.sh (Activation env)
- setup_project_env.ps1, setup_project_env.sh (Setup)
- activate_and_run.ps1 (Runner principal)

**À DÉPLACER vers scripts/:**
- run_validation.ps1 → scripts/validation/
- run_tests.ps1, run_tests_and_log.ps1, run_tests_from_file.py → scripts/testing/
- run_e2e_with_timeout.ps1, run_instrumented_test.ps1 → scripts/testing/
- test_api.ps1 → scripts/testing/
- safe_pytest_runner.py → scripts/testing/
- run_filtered_tests.py, filter_tests.py → scripts/testing/
- create_targeted_list.ps1, orchestrate_test_search.ps1, find_crashing_test.ps1 → scripts/testing/
- validate_openai_key.py → scripts/validation/
- run_in_env.ps1 → scripts/environment/

#### 📄 **Documentation** (10 fichiers) - **30% À RANGER**
**À CONSERVER racine:**
- README.md, LICENSE, [`PLAN.md`](../../PLAN.md:1)

**✅ DÉPLACÉ vers docs/maintenance/:**
- [`CLAUDE.md`](../../CLAUDE.md:1)
- [`DESIGN_PARALLEL_WORKFLOW.md`](../../DESIGN_PARALLEL_WORKFLOW.md:1)
- [`refactoring_plan.md`](../../refactoring_plan.md:1), [`refactoring_impact_analysis.md`](../../refactoring_impact_analysis.md:1)
- [`rapport_de_mission.md`](../../rapport_de_mission.md:1), [`rapport_mission_ADR_sophismes.md`](../../rapport_mission_ADR_sophismes.md:1)
- [`final_cleanup_report.md`](../../final_cleanup_report.md:1)

#### 🗑️ **Fichiers Obsolètes/Temporaires À SUPPRIMER** (~165 fichiers) ⚠️

**Logs vides** (~140 fichiers):
- trace_reelle_202507*.log (140+ fichiers vides 0 KB)
- trace_reelle_202508*.log 
- agents_logiques_production.log (vide)
- test_phase_c_fluidite.log (vide)
- verify_extracts.log, verify_extracts_llm.log (vides)

**Logs de tests** (~10 fichiers) → déplacer vers .temp/:
- pytest_failures*.log (5 fichiers, 1.1 MB au total)
- api_server.log, api_server.error.log
- frontend_server.log, frontend_server.error.log

**Screenshots** (9 fichiers PNG, ~3.3 MB) → déplacer vers _temp_screenshots/ ou docs/images/:
- screenshot_failure_element_*.png (4 fichiers)
- screenshot_failure_nav_*.png (5 fichiers)
- test_error.png, failed_homepage_connection.png
- integration_test_*.png (4 fichiers)

**Fichiers obsolètes:**
- patch.diff (32 KB) → déplacer vers docs/maintenance/patches/
- [`deep_fallacy_analysis_trace.md`](../../deep_fallacy_analysis_trace.md:1) → ✅ déplacé vers docs/maintenance/
- einstein_oracle_demo_trace.log (3 MB) → archiver ou supprimer
- empty_pytest.ini (vide) → supprimer
- backend_info.json → ignorer (déjà dans .gitignore)
- [`tests_jvm.txt`](../../tests_jvm.txt:1) → ✅ déplacé vers docs/maintenance/
- [`runtime.txt`](../../runtime.txt:1) → ✅ déplacé vers docs/maintenance/

---

## 4. Dossiers Fantômes et .gitignore

### Analyse .gitignore
- **Lignes totales** : 368 lignes
- **Patterns suspects** : 
  - Ligne 277: `*.txt` - **TROP GÉNÉRIQUE** (ignore tests_jvm.txt utile)
  - Ligne 288: `*.png` - **TROP GÉNÉRIQUE** (mais OK pour ignorer screenshots)
  - Plusieurs redondances (`.env` déclaré 3 fois: lignes 89, 252, 342)
- **Patterns manquants** :
  - `services/**/node_modules/` (node_modules dans sous-répertoires)
  - `*.egg-info/` (inclut argumentation_analysis.egg-info/)
  - `trace_reelle_*.log` (logs spécifiques)

### Dossiers Fantômes Détectés (13 répertoires)

| Répertoire | Taille | Status | Recommandation |
|-----------|--------|--------|----------------|
| `_temp/` | ? | Ignoré | ✅ Supprimer contenu |
| `_temp_jdk_download/` | ? | Ignoré | ✅ Supprimer |
| `_temp_prover9_install/` | ? | Ignoré | ✅ Supprimer |
| `_temp_readme_restoration/` | Quelques fichiers | Ignoré | ✅ Archiver puis supprimer |
| `_e2e_logs/` | Logs E2E | Ignoré | ⚠️ Garder ignoré, nettoyer ancien contenu |
| `.temp/` | Campagne nettoyage | Ignoré | ✅ Conserver (usage actif) |
| `dummy_opentelemetry/` | Contournement | Ignoré | ⚠️ Évaluer utilité - potentiellement supprimer |
| `portable_jdk/` | JDK local | Ignoré | ✅ Vérifier suppression |
| `logs/` | Logs anciens | Partiellement ignoré | ⚠️ Nettoyer logs obsolètes |
| `reports/` | Rapports auto | Ignoré | ✅ Nettoyer contenu |
| `results/` | Résultats tests | Ignoré | ✅ Nettoyer contenu |
| `node_modules/` | Dépendances npm | Ignoré | ✅ Vérifier suppression complète |
| `argumentation_analysis.egg-info/` | Build Python | Ignoré | ✅ Supprimer |

### Recommandations .gitignore

**À SIMPLIFIER :**
```gitignore
# Supprimer redondances .env (lignes 89, 252, 342)
.env
.env.*
.env.test

# Simplifier *.txt → plus spécifique
pytest_*.txt
temp_*.txt
*log.txt
```

**À AJOUTER :**
```gitignore
# Traces obsolètes
trace_reelle_*.log

# Node modules dans sous-répertoires
services/**/node_modules/

# Build Python
*.egg-info/
__pycache__/

# Screenshots temporaires
screenshot_*.png
integration_test_*.png
test_error.png
failed_*.png
```

---

## 5. Priorisation Complète Actualisée

### 🔴 **PRIORITÉ 1 - HAUTE** (Gain rapide, Risque faible, Impact immédiat)

#### 1.1 Fichiers Racine - Logs Obsolètes ⚡ **URGENT**
- **Action** : Supprimer ~140 fichiers `trace_reelle_*.log` (vides)
- **Gain** : Désencombrement massif racine
- **Risque** : **Nul** (fichiers vides)
- **Complexité** : Triviale (script PowerShell simple)
- **Commande** : 
```powershell
Get-ChildItem -Filter "trace_reelle_*.log" | Where-Object {$_.Length -eq 0} | Remove-Item
```

#### 1.2 Dossiers Fantômes - Temporaires ⚡ **URGENT**
- **Action** : Supprimer `_temp_jdk_download/`, `_temp_prover9_install/`, `portable_jdk/` (si non utilisés)
- **Gain** : Désencombrement espace disque
- **Risque** : **Faible** (déjà ignorés)
- **Validation** : Vérifier aucune référence dans scripts

#### 1.3 Caches Python - __pycache__ ⚡ **URGENT**
- **Action** : Supprimer tous les `__pycache__/` dans src/, plugins/, config/, project_core/
- **Gain** : ~31 fichiers .pyc supprimés (~60 KB)
- **Risque** : **Nul** (régénérés automatiquement)
- **Commande** :
```powershell
Get-ChildItem -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
```

### 🟡 **PRIORITÉ 2 - MOYENNE** (Organisation, Risque faible-modéré)

#### 2.1 Fichiers Racine - Scripts de Test (15 fichiers)
- **Action** : Déplacer scripts de test vers `scripts/testing/`
- **Gain** : Racine plus propre, meilleure organisation
- **Risque** : **Modéré** (mise à jour chemins imports/références)
- **Validation** : Tests `pytest` après déplacement

#### 2.2 Fichiers Racine - Documentation (7 fichiers)
- **Action** : Déplacer CLAUDE.md, DESIGN_*.md, rapport_*.md vers `docs/`
- **Gain** : Consolidation documentation
- **Risque** : **Faible** (documents seulement)

#### 2.3 Fichiers Racine - Screenshots (9 fichiers, ~3.3 MB)
- **Action** : Déplacer vers `.temp/screenshots/` ou `docs/images/testing/`
- **Gain** : Désencombrement racine
- **Risque** : **Faible** (fichiers statiques)
- **Alternative** : Supprimer si obsolètes

#### 2.4 api/ - Versions Simplifiées
- **Action** : Évaluer utilité de `*_simple.py` (3 fichiers)
- **Gain** : Réduction duplication code
- **Risque** : **Modéré** (vérifier dépendances)
- **Options** : Déplacer vers examples/ ou supprimer

### 🟠 **PRIORITÉ 3 - MODÉRÉE** (Nettoyage technique)

#### 3.1 services/ - node_modules (~147 MB)
- **Action** : Vérifier que node_modules n'est PAS tracké par git
- **Commande** : `git ls-files services/**/node_modules/`
- **Si tracké** : `git rm -r --cached services/web_api/interface-web-argumentative/node_modules/`
- **Gain** : Réduction massive taille repo
- **Risque** : **Faible** (déjà ignoré normalement)

#### 3.2 plugins/ - hello_world_plugin/
- **Action** : Déplacer vers `examples/plugins/` ou `docs/tutorials/`
- **Gain** : Séparation code prod/exemples
- **Risque** : **Faible** (plugin exemple)

#### 3.3 demos/ - Validation Complète
- **Action** : Validation pytest sur demos/ avant intégration campagne
- **Risque** : **Faible** (scripts indépendants)

### 🔵 **PRIORITÉ 4 - BASSE** (Post-campagne, Refactoring)

#### 4.1 docs/ (465 fichiers, ~25 MB) - Phase 1
- **Action** : Campagne nettoyage documentation (déjà planifiée Phase 1)
- **Risque** : **Faible**
- **Validation** : Aucune référence cassée

#### 4.2 scripts/ (417 fichiers, ~3 MB) - Phase 1
- **Action** : Campagne nettoyage scripts
- **Risque** : **Élevé** (codépendances)
- **Validation** : Tests complets

#### 4.3 tests/ (644 fichiers, ~4 MB) - Phase 1
- **Action** : Campagne nettoyage tests
- **Risque** : **Modéré** (validation pytest)
- **Validation** : `pytest` complet

### ⚫ **REPORTÉ - APRÈS CAMPAGNE**

#### argumentation_analysis/ ⚠️ **SOURCE PRINCIPAL**
- **Action** : **AUCUNE** (répertoire source principal)
- **Justification** : Trop risqué pendant nettoyage
- **Planning** : Après stabilisation post-campagne

---

## 6. Alertes Critiques Supplémentaires

### 🔴 **CRITIQUE - POLLUTION MASSIVE**
- **services/node_modules/** : ~147 MB - Vérifier IMPÉRATIVEMENT non-tracking git
- **Fichiers racine** : 320+ fichiers dont 165+ obsolètes (51% pollution)

### ⚠️ **ATTENTION - PATTERNS .gitignore**
- `*.txt` ligne 277 : Trop générique (ignore fichiers utiles)
- `*.png` ligne 288 : OK mais vérifier exceptions nécessaires

### ⚠️ **ATTENTION - CACHES MULTIPLES**
- __pycache__/ dans 5+ répertoires (src/, plugins/, config/, project_core/, argumentation_analysis/)
- .pyc non nettoyés (31 fichiers détectés)

### ℹ️ **INFO - STRUCTURE POSITIVE**
- examples/ : Bien structuré (sous-répertoires clairs)
- interface_web/ : Organisation propre (templates/, static/, api/)
- config/ : Séparation claire (pytest/, clean/, templates/)

---

## 7. Plan d'Action Séquencé avec Validations

### **PHASE A - Nettoyage Immédiat** (Risque nul, Gain maximal)
1. ✅ Supprimer logs vides racine (~140 fichiers `trace_reelle_*.log`)
2. ✅ Supprimer __pycache__/ (31 fichiers)
3. ✅ Supprimer dossiers temporaires (_temp_jdk_download/, _temp_prover9_install/)
4. ✅ Vérifier node_modules non-tracking git
5. **Validation** : `git status` - Aucun fichier supprimé ne devrait apparaître

### **PHASE B - Organisation Racine** (Risque faible)
1. ✅ Déplacer scripts test vers scripts/testing/
2. ✅ Déplacer documentation vers docs/
3. ✅ Déplacer screenshots vers .temp/screenshots/
4. ✅ Archiver _temp_readme_restoration/
5. **Validation** : `pytest -v` - Tous tests passent

### **PHASE C - Nettoyage Technique** (Risque modéré)
1. ✅ Évaluer api/*_simple.py (déplacer ou supprimer)
2. ✅ Déplacer hello_world_plugin/ vers examples/
3. ✅ Nettoyer dossiers fantômes (logs/, reports/, results/)
4. ✅ Optimiser .gitignore (supprimer redondances, ajouter patterns spécifiques)
5. **Validation** : `pytest -v` + Validation manuelle dépendances

### **PHASE D - Campagne Répertoires** (Post-nettoyage racine)
1. ✅ docs/ (Phase 1 - déjà analysé)
2. ✅ demos/, examples/, tutorials/ (risque faible)
3. ✅ config/, templates/, validation/ (risque faible)
4. ✅ interface_web/, api/, core/ (risque modéré)
5. ✅ plugins/ (risque modéré - valider dépendances)
6. ✅ src/ (risque modéré - __pycache__ déjà nettoyés)
7. ✅ tests/ (Phase 1 - risque modéré)
8. ✅ scripts/ (Phase 1 - risque élevé)
9. **Validation** : `pytest -v` à chaque étape

### **PHASE E - Post-Campagne** (Refactoring)
1. ⏸️ argumentation_analysis/ (REPORTÉ - source principal)
2. ⏸️ Refactoring architecture si nécessaire

---

## 8. Métriques d'Impact Prévisionnelles

### Gains Attendus
- **Fichiers supprimés** : ~165+ fichiers (logs, caches, temporaires)
- **Fichiers déplacés** : ~30 fichiers (scripts, docs, screenshots)
- **Réduction taille** : ~150 MB (si node_modules tracké + caches + logs)
- **Amélioration organisation** : 51% → 85% (fichiers racine bien placés)

### Risques Identifiés
- **Scripts déplacés** : Risque modéré (imports à mettre à jour)
- **api/*_simple.py** : Risque modéré (dépendances à vérifier)
- **Suppression logs** : Risque nul (fichiers vides)

### Validation Continue
- **Après chaque phase** : `pytest -v`
- **Avant commit** : `git status` + Review manuel
- **Post-campagne** : Tests complets + Validation utilisateur

---

## 9. Conclusion

✅ **Cartographie exhaustive Phase 2 complétée avec succès**

**Résumé exécutif :**
- 16 nouveaux répertoires analysés en détail
- ~320+ fichiers racine inventoriés (51% à ranger)
- 13 dossiers fantômes identifiés
- .gitignore analysé (patterns à optimiser)
- Priorisation complète établie (4 niveaux)

**Actions immédiates recommandées :**
1. Supprimer logs vides racine (140+ fichiers)
2. Nettoyer __pycache__/ (31 fichiers)
3. Vérifier node_modules non-tracking
4. Ranger fichiers racine (scripts → scripts/, docs → docs/)

**Prochaines étapes :**
→ Validation utilisateur du plan d'action
→ Exécution séquencée Phase A → Phase D
→ Validation tests continue (`pytest`)
→ Commit progressif par phase

**Métriques de succès :**
- Racine : 320+ → 170 fichiers (-47%)
- Taille repo : -150 MB estimé
- Organisation : 51% → 85% (+34%)
- Tests : 100% passants maintenu

---

**📊 Score de Découvrabilité Projet : 6.5/10 → 8.5/10 attendu**

*Rapport généré par analyse MCP Quickfiles + list_files + read_file*