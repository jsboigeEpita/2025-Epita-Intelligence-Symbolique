# Guide complet des tests UnifiedConfig

## Vue d'ensemble

Cette suite de tests valide complètement le système de configuration dynamique `UnifiedConfig` qui gère les paramètres de logique, niveaux de mock, taxonomie, et orchestration du système d'analyse rhétorique.

## 🏗️ Architecture des tests

### Structure des fichiers de tests

```
tests/
├── unit/
│   ├── config/
│   │   └── test_unified_config.py          # Tests unitaires UnifiedConfig
│   ├── scripts/
│   │   └── test_configuration_cli.py       # Tests intégration CLI
│   └── integration/
│       └── test_unified_config_integration.py  # Tests bout-en-bout
├── scripts/
│   └── test_unified_config_cli.ps1         # Tests PowerShell CLI
├── run_unified_config_tests.py             # Orchestrateur de tests
└── README_UNIFIED_CONFIG_TESTS.md          # Cette documentation
```

### Types de tests implémentés

| Type | Fichier | Description | Couverture |
|------|---------|-------------|------------|
| **Unitaires** | `test_unified_config.py` | Tests des classes et méthodes | >95% |
| **CLI** | `test_configuration_cli.py` | Tests mapping CLI → Config | 100% des args |
| **Intégration** | `test_unified_config_integration.py` | Tests pipeline complet | Bout-en-bout |
| **PowerShell** | `test_unified_config_cli.ps1` | Tests CLI système | Réels |
| **Performance** | Inclus dans orchestrateur | Tests vitesse/mémoire | Métriques |

## 🧪 Tests unitaires détaillés

### [`test_unified_config.py`](unit/config/test_unified_config.py)

**Couverture :** Configuration principale, énumérations, validation

#### Tests de configuration de base
```python
def test_default_configuration_loading()     # Valeurs par défaut
def test_logic_type_validation()            # FOL/PL/Modal
def test_mock_level_validation()            # NONE/PARTIAL/FULL  
def test_taxonomy_size_validation()         # 3/1000 nœuds
def test_orchestration_mode_validation()    # UNIFIED/CONVERSATION/etc.
```

#### Tests de validation avancée
```python
def test_invalid_combinations()             # Combinaisons interdites
def test_valid_combinations()               # Combinaisons validées
def test_configuration_persistence()        # Sérialisation/stockage
def test_agent_normalization()             # LOGIC → FOL_LOGIC auto
def test_authenticity_constraints()        # Contraintes authenticité
```

#### Tests des services spécialisés
```python
def test_service_configurations()          # Tweety/LLM/Taxonomie
def test_get_agent_classes()              # Mapping agents → classes
```

### Combinaisons testées

#### ✅ Combinaisons valides
| Logic | Mock | Taxonomy | Orchestration | Usage |
|-------|------|----------|---------------|-------|
| `FOL` | `NONE` | `FULL` | `UNIFIED` | **Production optimale** |
| `FOL` | `PARTIAL` | `MOCK` | `CONVERSATION` | **Développement** |
| `PL` | `FULL` | `MOCK` | `CONVERSATION` | **Test rapide** |

#### ❌ Combinaisons invalides
| Logic | Mock | Reason |
|-------|------|--------|
| `*` | `PARTIAL/FULL` + `require_real_gpt=True` | Incohérence authenticité |
| `*` | `enable_jvm=False` + `FOL_LOGIC agent` | Agent nécessite JVM |

## 🖥️ Tests CLI

### [`test_configuration_cli.py`](unit/scripts/test_configuration_cli.py)

**Couverture :** Interface CLI, conversion arguments, validation

#### Arguments CLI testés

| Argument | Valeurs testées | Mapping |
|----------|----------------|---------|
| `--logic-type` | `fol`, `pl`, `propositional`, `first_order`, `modal` | → `LogicType` |
| `--mock-level` | `none`, `partial`, `full` | → `MockLevel` |
| `--taxonomy` | `full`, `mock` | → `TaxonomySize` |
| `--orchestration` | `unified`, `conversation`, `real`, `custom` | → `OrchestrationType` |
| `--agents` | `informal,fol_logic,synthesis,pm,extract` | → `List[AgentType]` |

#### Tests de conversion CLI
```python
def test_logic_type_cli_argument()          # --logic-type mapping
def test_mock_level_cli_argument()          # --mock-level mapping  
def test_taxonomy_cli_argument()            # --taxonomy mapping
def test_orchestration_mode_cli_argument()  # --orchestration mapping
def test_agents_cli_argument()              # --agents parsing
def test_combined_cli_arguments()           # Combinaisons multiples
def test_invalid_cli_combinations()         # Détection erreurs CLI
```

### Exemples de commandes testées

#### Configuration production
```bash
python scripts/main/analyze_text.py \
  --source-type simple \
  --logic-type fol \
  --mock-level none \
  --taxonomy full \
  --orchestration unified \
  --require-real-gpt \
  --require-real-tweety
```

#### Configuration développement
```bash
python scripts/main/analyze_text.py \
  --source-type simple \
  --logic-type pl \
  --mock-level partial \
  --taxonomy mock \
  --orchestration conversation \
  --no-jvm
```

## 🔗 Tests d'intégration

### [`test_unified_config_integration.py`](unit/integration/test_unified_config_integration.py)

**Couverture :** Pipeline complet, presets, compatibilité

#### Tests de presets
```python
def test_full_pipeline_with_authentic_fol_config()  # Preset production
def test_development_workflow_integration()         # Preset développement
def test_testing_configuration_isolation()          # Preset test
```

#### Tests de compatibilité
```python  
def test_configuration_compatibility_matrix()       # Matrice complète
def test_invalid_configuration_combinations()       # Échecs attendus
def test_configuration_serialization_roundtrip()    # Persistance
def test_performance_configuration_impact()         # Impact perf
```

#### Tests de migration
```python
def test_configuration_migration_compatibility()    # Rétrocompatibilité
def test_configuration_validation_comprehensive()   # Validation complète
```

## 💻 Tests PowerShell CLI

### [`test_unified_config_cli.ps1`](scripts/test_unified_config_cli.ps1)

**Couverture :** CLI système, intégration Windows, validation bout-en-bout

#### Suites de tests PowerShell

| Suite | Tests | Description |
|-------|-------|-------------|
| **Basic** | 5 tests | Arguments CLI de base |
| **Advanced** | 3 tests | Combinaisons invalides + formats |
| **Integration** | 2 tests | Variables environnement |
| **Performance** | 1 test | Vitesse d'exécution |

#### Commandes testées
```powershell
# Test configuration FOL authentique
python analyze_text.py --source-type simple --logic-type fol --mock-level none

# Test configuration développement  
python analyze_text.py --source-type simple --logic-type pl --mock-level partial

# Test formats de sortie
python analyze_text.py --source-type simple --format json --output test.json
```

#### Métriques validées
- **Temps d'exécution** : < 60s pour config rapide
- **Codes de sortie** : 0 pour succès, != 0 pour échecs
- **Fichiers de sortie** : Création et contenu validés

## 🚀 Orchestrateur de tests

### [`run_unified_config_tests.py`](run_unified_config_tests.py)

**Couverture :** Automatisation complète, rapports, métriques

#### Pipeline d'exécution
1. **Validation des fichiers** → Import UnifiedConfig
2. **Tests unitaires** → pytest avec couverture
3. **Tests d'intégration** → Validation pipeline
4. **Tests de performance** → Métriques vitesse/mémoire
5. **Tests CLI** → PowerShell système
6. **Génération rapport** → JSON + métriques

#### Utilisation
```bash
# Exécution complète
python tests/run_unified_config_tests.py

# Mode verbeux avec couverture  
python tests/run_unified_config_tests.py --verbose

# Exécution rapide (sans PowerShell)
python tests/run_unified_config_tests.py --fast --no-coverage
```

#### Métriques collectées
- **Couverture de code** : >95% cible
- **Temps d'exécution** : Par suite et total
- **Taux de réussite** : Tests passés/échoués
- **Performance** : Vitesse création/validation config

## 📊 Métriques de validation

### Objectifs de couverture

| Composant | Couverture cible | Métriques |
|-----------|------------------|-----------|
| **UnifiedConfig classe** | >95% | Toutes méthodes |
| **Énumérations** | 100% | Toutes valeurs |
| **CLI mapping** | 100% | Tous arguments |
| **Combinaisons valides** | 100% | Presets + custom |
| **Validation d'erreurs** | 100% | Tous cas invalides |

### Tests de régression

#### Configuration legacy
- ✅ Compatibilité avec anciens scripts
- ✅ Migration transparente vers UnifiedConfig
- ✅ Préservation des comportements existants

#### Performance
- ✅ Création config < 1s pour 100 instances
- ✅ Validation < 0.5s pour sérialisation
- ✅ CLI réponse < 60s pour config rapide

## 🛠️ Instructions d'exécution

### Prérequis
```bash
# Installation des dépendances de test
pip install pytest pytest-cov

# Vérification PowerShell (Windows)
powershell -Command "Get-Host"
```

### Tests unitaires seuls
```bash
# Tests UnifiedConfig
pytest tests/unit/config/test_unified_config.py -v

# Tests CLI
pytest tests/unit/scripts/test_configuration_cli.py -v

# Tests intégration
pytest tests/unit/integration/test_unified_config_integration.py -v
```

### Tests CLI PowerShell
```bash
# Windows PowerShell
powershell -ExecutionPolicy Bypass -File tests/scripts/test_unified_config_cli.ps1

# Tests spécifiques
powershell -File tests/scripts/test_unified_config_cli.ps1 -TestSuite Basic
```

### Suite complète automatisée
```bash
# Exécution complète
python tests/run_unified_config_tests.py

# Avec options
python tests/run_unified_config_tests.py --verbose --no-coverage
```

## 📋 Matrice de compatibilité

### Configurations validées

| Preset | Logic | Mock | Taxonomy | Agents | JVM | Usage |
|--------|-------|------|----------|--------|-----|-------|
| **authentic_fol** | FOL | NONE | FULL | informal+fol_logic+synthesis | ✓ | Production |
| **authentic_pl** | PL | NONE | FULL | informal+fol_logic+synthesis | ✓ | Production rapide |
| **development** | FOL | PARTIAL | MOCK | informal+fol_logic+synthesis | ✗ | Développement |
| **testing** | PL | FULL | MOCK | informal+synthesis | ✗ | Tests auto |

### Combinaisons personnalisées supportées

#### Authentiques (production)
```python
# FOL authentique maximal
UnifiedConfig(
    logic_type=LogicType.FOL,
    mock_level=MockLevel.NONE,
    taxonomy_size=TaxonomySize.FULL,
    require_real_gpt=True,
    require_real_tweety=True
)

# PL authentique rapide  
UnifiedConfig(
    logic_type=LogicType.PL,
    mock_level=MockLevel.NONE,
    taxonomy_size=TaxonomySize.FULL
)
```

#### Développement
```python
# Développement avec mocks
UnifiedConfig(
    logic_type=LogicType.FOL,
    mock_level=MockLevel.PARTIAL,
    taxonomy_size=TaxonomySize.MOCK,
    enable_jvm=False,
    require_real_gpt=False
)
```

## 🐛 Débogage et diagnostics

### Tests échoués

#### Erreurs fréquentes
1. **Import Error** : Vérifier `PYTHONPATH` et installation
2. **Mock Incompatibility** : Vérifier `mock_level` vs `require_real_*`
3. **JVM Error** : Vérifier agents vs `enable_jvm`
4. **PowerShell Error** : Vérifier disponibilité et policy

#### Diagnostics
```bash
# Test import basic
python -c "from config.unified_config import UnifiedConfig; print('OK')"

# Test CLI basic  
python scripts/main/analyze_text.py --help

# Test PowerShell
powershell -Command "Get-ExecutionPolicy"
```

### Logs et rapports

#### Structure des rapports
```json
{
  "summary": {
    "timestamp": "2025-01-07T14:30:00",
    "tests_run": 15,
    "tests_passed": 14,
    "tests_failed": 1,
    "total_duration": 45.2
  },
  "detailed_results": {
    "unit_tests": {"success": true, "duration": 12.1},
    "cli_tests": {"success": false, "error": "PowerShell timeout"}
  }
}
```

#### Localisation des rapports
- **HTML Coverage** : `tests/reports/coverage_html/index.html`
- **JSON Reports** : `tests/reports/unified_config_test_report_*.json`
- **Test Outputs** : `tests/test_results/`

## ✅ Checklist de validation

### Avant commit
- [ ] Tous les tests unitaires passent
- [ ] Couverture >95% pour UnifiedConfig
- [ ] Tests CLI PowerShell passent
- [ ] Aucune régression de performance
- [ ] Documentation à jour

### Avant release
- [ ] Suite complète passe sur environnement propre
- [ ] Tests d'intégration bout-en-bout validés
- [ ] Métriques de performance respectées
- [ ] Compatibilité rétrograde confirmée
- [ ] Rapports de test archivés

---

## 📞 Support et maintenance

### Mise à jour des tests

Lors d'ajout de nouvelles fonctionnalités à `UnifiedConfig` :

1. **Ajouter tests unitaires** dans `test_unified_config.py`
2. **Ajouter arguments CLI** dans `test_configuration_cli.py` 
3. **Mettre à jour intégration** dans `test_unified_config_integration.py`
4. **Tester PowerShell** si nouvel argument CLI
5. **Mettre à jour documentation** dans ce fichier

### Contact
- **Tests techniques** : Équipe développement core
- **Tests CLI** : Équipe interface utilisateur  
- **Performance** : Équipe architecture

---

*Documentation générée automatiquement - Version 1.0*