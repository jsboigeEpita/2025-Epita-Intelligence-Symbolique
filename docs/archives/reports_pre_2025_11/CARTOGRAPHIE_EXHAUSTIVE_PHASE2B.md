# CARTOGRAPHIE EXHAUSTIVE COMPLÈTE DU DÉPÔT - PHASE 2B

**Date :** 10/06/2025 12:59:00 PM  
**Status :** Synchronisation git terminée (en avance de 4 commits, working tree propre)  
**Périmètre :** Répertoires critiques restants (3 niveaux hiérarchiques)

---

## 🧪 1. TESTS ET VALIDATION

### 1.1 Tests Unitaires (`tests/unit/`) - STRUCTURE HIÉRARCHIQUE COMPLÈTE

#### **NIVEAU 1 - Modules Principaux :**
```
tests/unit/
├── argumentation_analysis/    [MODULE PRINCIPAL - 140+ fichiers]
├── authentication/           [2 fichiers - tests CLI et mocks]
├── config/                  [test_unified_config.py]
├── integration/             [test_unified_config_integration.py]
├── mocks/                   [tests numpy mocks]
├── orchestration/           [orchestration hiérarchique]
├── project_core/            [dev_utils, pipelines, utils]
├── scripts/                 [auto_env, configuration_cli, environment_manager]
└── utils/                   [validation_errors, helpers communs]
```

#### **NIVEAU 2 - Argumentation Analysis (Détail) :**
```
argumentation_analysis/
├── agents/                  [tests agents core - extract, informal, oracle, tools]
│   ├── core/               [extract, informal, oracle - 25+ tests]
│   └── tools/              [analysis - complex/contextual fallacy]
├── analytics/              [stats_calculator, text_analyzer]
├── core/                   [cluedo_oracle_state]
├── mocks/                  [15+ tests mocks avancés - argument_mining, bias_detection, etc.]
├── nlp/                    [embedding_utils]
├── orchestration/          [advanced_analyzer, analysis_runner, cluedo_enhanced]
├── pipelines/              [advanced_rhetoric, analysis, embedding, reporting]
├── reporting/              [summary_generator]
├── service_setup/          [analysis_services]
└── utils/                  [50+ tests - core_utils, dev_tools, metrics, etc.]
```

#### **NIVEAU 3 - Oracle Agent (Critique) :**
```
agents/core/oracle/
├── test_cluedo_dataset.py
├── test_dataset_access_manager.py
├── test_error_handling.py
├── test_interfaces.py
├── test_moriarty_interrogator_agent.py
├── test_new_modules_integration.py
├── test_oracle_base_agent.py (+ variations recovered/fixed)
├── test_oracle_behavior_demo.py (+ refactored)
├── test_oracle_behavior_simple.py (+ refactored)
└── test_oracle_enhanced_behavior.py
```

### 1.2 Tests Validation Sherlock Watson (`tests/validation_sherlock_watson/`)

**STRUCTURE COMPLÈTE :**
```
tests/validation_sherlock_watson/
├── test_analyse_simple.py
├── test_api_corrections_simple.py
├── test_cluedo_dataset_simple.py
├── test_diagnostic.py
├── test_final_oracle_simple.py
├── test_group1_simple.py
├── test_group2_corrections_simple.py
├── test_group3_final_validation.py
├── test_group3_simple.py
├── test_groupe2_validation_simple.py
├── test_import.py
├── test_oracle_fixes_simple.py
├── test_oracle_import.py
├── test_phase_a_personnalites_distinctes.py
├── test_phase_b_naturalite_dialogue.py
├── test_phase_b_simple.py (+ fixed)
├── test_phase_c_fluidite_transitions.py
├── test_phase_c_simple.py
├── test_phase_d_simple.py (+ fixed)
├── test_phase_d_trace_ideale.py
├── test_scenario_complexe_authentique.py
├── test_validation_integrite_apres_corrections.py
└── test_verification_fonctionnalite_oracle.py
```

**POINTS D'ENTRÉE IDENTIFIÉS :**
- **Tests Groupes :** test_group1_simple.py, test_group2_corrections_simple.py, test_group3_final_validation.py
- **Tests Phases :** test_phase_a/b/c/d (personnalités, naturalité, fluidité, trace)
- **Validation Finale :** test_validation_integrite_apres_corrections.py

### 1.3 Tests Playwright (`tests_playwright/`)

**STRUCTURE WEB INTERFACE :**
```
tests_playwright/
├── package.json, package-lock.json    [Configuration Node.js]
├── playwright.config.js               [Config principal]
├── playwright-api.config.js           [Config API]
├── playwright-phase5.config.js        [Config Phase 5]
├── test-results-phase5.json           [Résultats Phase 5]
├── data/                              [Données tests]
├── playwright-report/                 [Rapports généraux]
├── playwright-report-phase5/          [Rapports Phase 5 détaillés]
├── results/, test-results/            [Résultats tests]
└── tests/
    ├── api-backend.spec.js            [Tests API backend]
    ├── flask-interface.spec.js        [Tests interface Flask]
    └── phase5-non-regression.spec.js   [Tests non-régression Phase 5]
```

---

## 🌐 2. INTERFACES ET APPLICATIONS

### 2.1 Interface Web (`interface_web/`)

**STRUCTURE FLASK :**
```
interface_web/
├── app.py                  [Application Flask principale - Point d'entrée web]
├── test_webapp.py          [Tests webapp]
└── templates/
    └── index.html          [Template principal]
```

**POINT D'ENTRÉE :** `app.py` - Interface Flask pour analyse argumentative EPITA

### 2.2 API Services (`api/`)

**STRUCTURE FASTAPI :**
```
api/
├── main.py                 [Point d'entrée FastAPI]
├── endpoints.py            [Définitions endpoints]
├── dependencies.py         [Dépendances injection]
├── models.py              [Modèles données]
└── services.py            [Services métier]
```

**POINT D'ENTRÉE :** `main.py` - API FastAPI "Argumentation Analysis API"

### 2.3 Démonstrations EPITA (`demos/`)

**STRUCTURE DÉMOS :**
```
demos/
├── demo_epita_diagnostic.py           [Diagnostic EPITA]
├── demo_one_liner_usage.py            [Usage simplifié]
├── demo_rhetorique_complete.py        [Rhétorique complète]
├── demo_rhetorique_corrige.py         [Version corrigée]
├── demo_rhetorique_simplifie.py       [Version simplifiée]
├── demo_unified_system.py             [Système unifié]
├── validation_complete_epita.py       [Validation complète]
├── rapport_final_demo_epita.md        [Rapport démo]
├── rapport_final_interface_web_epita.md [Rapport interface]
└── playwright/                        [Démos Playwright - 10+ fichiers]
    ├── demo_playwright_final.py
    ├── demo_service_manager_validated.py
    ├── run_playwright_demos.py (+ fixed)
    └── test_* [Tests variés API/interface]
```

**POINTS D'ENTRÉE EPITA :**
- **Diagnostic :** `demo_epita_diagnostic.py`
- **Usage Simple :** `demo_one_liner_usage.py`
- **Système Unifié :** `demo_unified_system.py`
- **Validation :** `validation_complete_epita.py`

---

## ⚙️ 3. CONFIGURATION ET INFRASTRUCTURE

### 3.1 Configuration (`config/`)

**STRUCTURE CONFIGURATION :**
```
config/
├── __init__.py
├── .env.example, .env.template        [Templates environnement]
├── unified_config.py                  [Configuration unifiée]
├── orchestration_config.yaml          [Config orchestration]
├── performance_config.ini             [Config performance]
├── ports.json                         [Configuration ports]
├── webapp_config.yml                  [Config webapp]
├── utf8_environment.conf              [Config UTF8]
├── pytest.ini                        [Config pytest principale]
├── README.md
├── clean/                             [Scripts validation]
│   ├── backend_validation_script.ps1
│   ├── test_environment.env
│   └── web_application_launcher.ps1
└── pytest/                           [Configurations pytest spécialisées]
    ├── pytest_jvm_only.ini
    ├── pytest_phase2.ini
    ├── pytest_phase3.ini
    ├── pytest_phase4_final.ini
    ├── pytest_recovery.ini
    ├── pytest_simple.ini
    ├── pytest_stable.ini
    └── pytest.ini
```

**POINTS D'ENTRÉE CONFIG :**
- **Configuration Unifiée :** `unified_config.py`
- **Environnement :** `.env.template`, `utf8_environment.conf`
- **Scripts Validation :** `clean/backend_validation_script.ps1`, `clean/web_application_launcher.ps1`

### 3.2 Librairies (`libs/`)

**STRUCTURE LIBRAIRIES :**
```
libs/
├── README.md
├── native/                            [Librairies natives]
├── portable_octave/                   [Octave 10.1.0 complet - MASSIF]
│   └── octave-10.1.0-w64/            [Installation complète - 1000+ fichiers]
└── tweety/                           [TweetyProject - JAR files]
    ├── .gitkeep
    ├── org.tweetyproject.*.jar       [28 JAR files - logiques, argumentation]
    └── native/                       [DLL natives - lingeling, minisat, picosat]
        ├── lingeling.dll
        ├── minisat.dll
        └── picosat.dll
```

**LIBRAIRIES CRITIQUES :**
- **TweetyProject :** 28 JARs (argumentation, logiques FOL/ML/PL, ASP, etc.)
- **Portable Octave :** Installation complète 10.1.0 (calcul scientifique)
- **Natives :** DLL solveurs SAT (lingeling, minisat, picosat)

### 3.3 JDK Portable (`portable_jdk/`)

**STATUS :** **VIDE** - Répertoire présent mais aucun contenu détecté

---

## 🎯 4. ANALYSE DES POINTS D'ENTRÉE

### 4.1 Scripts Principaux Identifiés

**AUTO_ENV ET ORCHESTRATEURS :**
- `scripts/auto_env.py` (cartographié Phase 2A)
- `argumentation_analysis/orchestration/enhanced_pm_analysis_runner.py`
- `argumentation_analysis/orchestration/cluedo_extended_orchestrator.py`

**APPLICATIONS WEB ACTIVES :**
- `interface_web/app.py` - Interface Flask EPITA
- `api/main.py` - API FastAPI

**SCRIPTS DEMO EPITA :**
- `demos/demo_epita_diagnostic.py`
- `demos/demo_unified_system.py`
- `demos/validation_complete_epita.py`

### 4.2 Configurations Critiques

**ENVIRONNEMENT :**
- `config/unified_config.py` - Configuration centralisée
- `config/.env.template` - Template variables environnement
- `config/utf8_environment.conf` - Configuration UTF8

**PYTEST SPÉCIALISÉ :**
- `config/pytest/pytest_phase4_final.ini` - Configuration tests finaux
- `config/pytest/pytest_stable.ini` - Configuration stable
- `config/pytest/pytest_jvm_only.ini` - Tests JVM uniquement

**INFRASTRUCTURE :**
- `config/orchestration_config.yaml` - Configuration orchestration
- `config/ports.json` - Mapping ports services
- `config/webapp_config.yml` - Configuration webapp

---

## 📊 5. SYNTHÈSE ORGANISÉE

### 5.1 Complexité par Répertoire

| Répertoire | Fichiers | Niveaux | Criticité | Status |
|------------|----------|---------|-----------|---------|
| `tests/unit/` | 200+ | 3 | **HAUTE** | ✅ Mappé |
| `tests/validation_sherlock_watson/` | 23 | 1 | **HAUTE** | ✅ Mappé |
| `tests_playwright/` | 20+ | 2 | **MOYENNE** | ✅ Mappé |
| `interface_web/` | 4 | 2 | **MOYENNE** | ✅ Mappé |
| `api/` | 5 | 1 | **MOYENNE** | ✅ Mappé |
| `demos/` | 25+ | 2 | **HAUTE** | ✅ Mappé |
| `config/` | 20+ | 2 | **CRITIQUE** | ✅ Mappé |
| `libs/` | 1000+ | 3 | **CRITIQUE** | ✅ Mappé |
| `portable_jdk/` | 0 | 0 | **VIDE** | ⚠️ Vide |

### 5.2 Points d'Entrée Critiques Identifiés

**INFRASTRUCTURE :**
- Configuration : `config/unified_config.py`
- Auto-env : `scripts/auto_env.py`
- Orchestration : `argumentation_analysis/orchestration/enhanced_pm_analysis_runner.py`

**APPLICATIONS :**
- Interface Web : `interface_web/app.py`
- API : `api/main.py`
- Démo EPITA : `demos/demo_unified_system.py`

**TESTS CRITIQUES :**
- Validation Sherlock : `tests/validation_sherlock_watson/test_group3_final_validation.py`
- Playwright : `tests_playwright/tests/phase5-non-regression.spec.js`
- Unit Oracle : `tests/unit/argumentation_analysis/agents/core/oracle/`

### 5.3 Dépendances Infrastructure

**LIBRAIRIES ESSENTIELLES :**
- TweetyProject (28 JARs) - Logiques argumentation
- Portable Octave - Calcul scientifique
- DLL Natives - Solveurs SAT

**CONFIGURATIONS REQUISES :**
- `.env` configuré selon template
- UTF8 environment setup
- Ports mapping (ports.json)
- Pytest configurations par phase

---

## ✅ 6. CONCLUSION ET PROCHAINES ÉTAPES

### 6.1 Mission Phase 2B - ACCOMPLIE

✅ **Cartographie exhaustive 3 niveaux réalisée**  
✅ **Points d'entrée critiques identifiés**  
✅ **Infrastructure documentée**  
✅ **Configurations inventoriées**  

### 6.2 Observations Critiques

⚠️ **portable_jdk/ VIDE** - JDK 17 manquant  
🔍 **libs/ MASSIF** - Octave 10.1.0 complet (1000+ fichiers)  
🎯 **Tests Sherlock Watson** - 23 tests validation spécialisés  
🏗️ **Configuration riche** - Multiple configurations pytest par phase  

### 6.3 Recommandations Analyse Suite

1. **Analyser config/unified_config.py** - Configuration centralisée
2. **Vérifier portable_jdk/** - JDK 17 requis pour TweetyProject
3. **Examiner tests Sherlock Watson** - Validation critique
4. **Cartographier services/** - Répertoire restant non analysé

---

**CARTOGRAPHIE PHASE 2B TERMINÉE**  
**Prêt pour analyses spécialisées et déploiement infrastructure**