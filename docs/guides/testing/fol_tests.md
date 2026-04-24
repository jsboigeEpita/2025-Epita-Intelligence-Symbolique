# Tests pour FirstOrderLogicAgent (FOL)

## 📋 Vue d'ensemble

Cette suite de tests valide complètement l'agent `FirstOrderLogicAgent` qui remplace le `ModalLogicAgent` problématique. L'agent FOL génère une syntaxe FOL valide et s'intègre parfaitement avec le solveur Tweety sans erreurs de parsing.

## 🎯 Objectifs de validation

### **Métriques critiques**
- ✅ **100%** des formules FOL générées valides
- ✅ **0** erreur de parsing Tweety avec syntaxe FOL  
- ✅ **>95%** compatibilité avec sophismes existants
- ✅ **Temps réponse** ≤ Modal Logic précédent
- ✅ **>90%** couverture tests pour FirstOrderLogicAgent

### **Fonctionnalités validées**
- 🔧 Génération syntaxe FOL : `∀x(P(x) → Q(x))`, `∃x(F(x) ∧ G(x))`
- 🔧 Intégration Tweety sans erreurs de parsing
- 🔧 Configuration dynamique via `UnifiedConfig`
- 🔧 Utilisation dans orchestrations unifiées

## 📁 Structure des tests

```
tests/
├── unit/agents/
│   └── test_fol_logic_agent.py           # Tests unitaires complets
├── integration/
│   └── test_fol_tweety_integration.py    # Tests intégration Tweety
├── validation/
│   └── test_fol_complete_validation.py   # Validation avec métriques
├── migration/
│   └── test_modal_to_fol_migration.py    # Tests migration Modal→FOL
└── README_FOL_TESTS.md                   # Cette documentation
```

## 🧪 Tests unitaires (`test_fol_logic_agent.py`)

### **Classes de test**

#### `TestFOLLogicAgentInitialization`
- ✅ `test_agent_initialization_with_fol_config()` - Création avec config FOL
- ✅ `test_unified_config_fol_mapping()` - Mapping depuis `UnifiedConfig.logic_type='FOL'`
- ✅ `test_agent_parameters_configuration()` - Paramètres agent (expertise, style)
- ✅ `test_fol_configuration_validation()` - Validation configuration FOL

#### `TestFOLSyntaxGeneration`
- ✅ `test_quantifier_universal_generation()` - Tests `∀x(P(x) → Q(x))`
- ✅ `test_quantifier_existential_generation()` - Tests `∃x(F(x) ∧ G(x))`
- ✅ `test_complex_predicate_generation()` - Tests `∀x∀y(R(x,y) → S(y,x))`
- ✅ `test_logical_connectors_validation()` - Tests `∧`, `∨`, `→`, `¬`, `↔`

#### `TestFOLTweetyIntegration`
- ✅ `test_tweety_integration_fol()` - Compatibilité syntaxe Tweety
- ✅ `test_tweety_validation_formulas()` - Validation avant envoi Tweety
- ✅ `test_tweety_error_handling_fol()` - Gestion erreurs Tweety
- ✅ `test_tweety_results_analysis_fol()` - Analyse résultats Tweety

#### `TestFOLAnalysisPipeline`
- ✅ `test_sophism_analysis_with_fol()` - Analyse sophismes avec FOL
- ✅ `test_fol_report_generation()` - Génération rapport avec formules FOL
- ✅ `test_tweety_error_analyzer_integration()` - Intégration `TweetyErrorAnalyzer`
- ✅ `test_performance_analysis()` - Tests performance

### **Syntaxe FOL validée**

```fol
# Quantificateurs de base
∀x(Human(x) → Mortal(x))
∃x(Student(x) ∧ Intelligent(x))

# Prédicats complexes  
∀x∀y(Loves(x,y) → Cares(x,y))
∃x∃y(Friend(x,y) ∧ Trust(x,y))

# Connecteurs logiques complets
∀x((P(x) ∧ Q(x)) → (R(x) ∨ S(x)))
∃x(¬Bad(x) ↔ Good(x))
```

## 🔗 Tests d'intégration (`test_fol_tweety_integration.py`)

### **Validation Tweety authentique**

#### `TestFOLTweetyCompatibility`
- ✅ `test_fol_formula_tweety_compatibility()` - Formules acceptées par Tweety réel
- ✅ `test_fol_predicate_declaration_validation()` - Validation déclaration prédicats
- ✅ `test_fol_quantifier_binding_validation()` - Validation liaison quantificateurs

#### `TestRealTweetyFOLAnalysis`
- ✅ `test_real_tweety_fol_syllogism_analysis()` - Analyse syllogisme avec Tweety réel
- ✅ `test_real_tweety_fol_inconsistency_detection()` - Détection incohérence
- ✅ `test_real_tweety_fol_inference_generation()` - Génération inférences

#### `TestFOLErrorHandling`
- ✅ `test_fol_predicate_declaration_error_handling()` - Gestion erreurs déclaration
- ✅ `test_fol_syntax_error_recovery()` - Récupération erreurs syntaxe
- ✅ `test_fol_timeout_handling()` - Gestion timeouts

### **Exigences Tweety**
- 🔧 `USE_REAL_JPYPE=true` pour tests authentiques
- 🔧 JAR Tweety authentique requis
- 🔧 Parsing sans erreurs validé
- 🔧 Résultats cohérents garantis

## 📊 Validation complète (`test_fol_complete_validation.py`)

### **Métriques automatisées**

La classe `FOLCompleteValidator` exécute une validation exhaustive :

#### **Critères validés**
- 📈 **100%** formules FOL syntaxiquement valides
- 📈 **0** erreur parsing Tweety  
- 📈 **>95%** compatibilité sophismes existants
- 📈 **Performance** acceptable (< 10s moyenne)
- 📈 **Gestion erreurs** complète et gracieuse

#### **Tests d'échantillons**
- 🔍 **Syntaxe FOL** : Quantificateurs, prédicats, connecteurs
- 🔍 **Sophismes** : Syllogismes, sophismes classiques, contradictions
- 🔍 **Argumentation complexe** : Philosophie, science, déontique
- 🔍 **Cas d'erreur** : Texte vide, non-logique, caractères spéciaux

### **Rapport automatique**
```json
{
  "overall_success": true,
  "metrics": {
    "fol_syntax_validity_rate": 1.0,
    "tweety_parsing_success_rate": 1.0,
    "sophism_compatibility": 0.98,
    "avg_analysis_time": 3.2,
    "avg_confidence": 0.85
  },
  "recommendations": ["✅ Agent FOL prêt pour production"]
}
```

## 🔄 Tests de migration (`test_modal_to_fol_migration.py`)

### **Validation remplacement Modal Logic**

#### `TestModalToFOLInterface`
- ✅ `test_interface_compatibility()` - Interface identique
- ✅ `test_configuration_migration_transparency()` - Migration config transparente
- ✅ `test_result_structure_compatibility()` - Structure résultats compatible

#### `TestFunctionalReplacement`
- ✅ `test_sophism_analysis_migration()` - Migration analyse sophismes
- ✅ `test_error_handling_improvement()` - Amélioration gestion erreurs

#### `TestPerformanceComparison`
- ✅ `test_performance_parity_or_improvement()` - Performance équivalente/meilleure
- ✅ `test_stability_improvement()` - Stabilité améliorée

### **Améliorations vs Modal Logic**
- 🚀 **Stabilité** : Moins de crashes et erreurs
- 🚀 **Performance** : Temps réponse équivalent ou meilleur
- 🚀 **Compatibilité** : Même interface, meilleurs résultats
- 🚀 **Intégration** : Fonctionne avec orchestrations existantes

## 🚀 Exécution des tests

### **Script d'exécution automatisé**
```bash
# Tous les tests
python scripts/run_fol_tests.py --all

# Tests unitaires seulement
python scripts/run_fol_tests.py --unit-only

# Tests intégration avec Tweety réel
python scripts/run_fol_tests.py --integration --real-tweety

# Validation complète avec métriques
python scripts/run_fol_tests.py --validation

# Tests migration Modal → FOL
python scripts/run_fol_tests.py --migration
```

### **Prérequis pour tests complets**
```bash
# Variables d'environnement
export USE_REAL_JPYPE=true
export TWEETY_JAR_PATH=libs/tweety-full.jar
export JVM_MEMORY=1024m
export UNIFIED_LOGIC_TYPE=fol
export UNIFIED_MOCK_LEVEL=none

# Installation dépendances
pip install pytest pytest-asyncio pytest-json-report
```

### **Tests par niveau**

#### **Niveau 1 : Tests unitaires (sans Tweety)**
```bash
python scripts/run_fol_tests.py --unit-only
# ✅ Validation syntaxe FOL
# ✅ Configuration UnifiedConfig  
# ✅ Interface agent
# ✅ Pipeline analyse (mocked)
```

#### **Niveau 2 : Tests intégration (avec Tweety simulé)**
```bash
python scripts/run_fol_tests.py --integration
# ✅ Compatibilité syntaxe (simulée)
# ✅ Gestion erreurs
# ✅ Performance
```

#### **Niveau 3 : Tests authentiques (Tweety réel)**
```bash
python scripts/run_fol_tests.py --integration --real-tweety
# ✅ Parsing Tweety authentique
# ✅ Analyse syllogismes réels
# ✅ Détection incohérences réelles
# ✅ Inférences Tweety valides
```

#### **Niveau 4 : Validation complète**
```bash
python scripts/run_fol_tests.py --validation --real-tweety
# ✅ Métriques toutes validées
# ✅ Critères 100% respectés
# ✅ Rapport détaillé généré
# ✅ Recommandations produites
```

## 📋 Rapport de validation

### **Exemple de rapport réussi**
```
📋 RAPPORT VALIDATION AGENT FOL
================================================================================

🕐 Temps total: 45.67s
🎯 Succès global: ✅ OUI
📊 Taux réussite: 100% (4/4)

📋 Résultats par suite:
  ✅ Unit: 12.34s
  ✅ Integration: 18.45s  
  ✅ Validation: 8.92s
  ✅ Migration: 5.96s

📏 Conformité critères:
  ✅ 100% formules FOL valides
  ✅ 0 erreur parsing Tweety
  ✅ >95% compatibilité sophismes
  ✅ Performance acceptable
  ✅ Gestion erreurs complète

📈 Métriques clés:
  • Syntaxe FOL valide: 100%
  • Parsing Tweety: 100%
  • Compatibilité sophismes: 98%
  • Temps analyse moyen: 3.20s
  • Confiance moyenne: 0.85

💡 Recommandations:
  • ✅ Tous les tests réussis - Agent FOL prêt pour production

🎉 Agent FOL validé avec succès!
```

## 🔧 Configuration et environnement

### **Configuration UnifiedConfig pour FOL**
```python
# Configuration authentique FOL
config = PresetConfigs.authentic_fol()
assert config.logic_type == LogicType.FOL
assert config.mock_level == MockLevel.NONE
assert config.require_real_tweety == True
assert AgentType.FOL_LOGIC in config.agents

# Utilisation en orchestration
agent_classes = config.get_agent_classes()
assert agent_classes["fol_logic"] == "FirstOrderLogicAgent"
```

### **Mapping automatique Modal → FOL**
```python
# Configuration legacy automatiquement migrée
config = UnifiedConfig(logic_type=LogicType.FOL)
# AgentType.LOGIC automatiquement remplacé par AgentType.FOL_LOGIC
assert AgentType.FOL_LOGIC in config.agents
```

## 📚 Documentation technique

### **Syntaxe FOL supportée**
- **Quantificateurs** : `∀x`, `∃x`, `∀x∀y`, `∃x∃y`
- **Prédicats** : `P(x)`, `Q(x,y)`, `R(x,y,z)`
- **Connecteurs** : `∧` (et), `∨` (ou), `→` (implique), `¬` (non), `↔` (équivalent)
- **Variables** : `x`, `y`, `z` (liées par quantificateurs)
- **Constantes** : `a`, `b`, `c`, `socrate`, etc.

### **Intégration Tweety**
- **Initialisation** : `TweetyBridge.initialize_fol_reasoner()`
- **Validation** : `check_consistency(formulas)`
- **Inférences** : `derive_inferences(formulas)` 
- **Modèles** : `generate_models(formulas)`

### **Gestion d'erreurs**
- **TweetyErrorAnalyzer** : Analyse erreurs avec feedback BNF
- **Récupération gracieuse** : Aucun crash sur erreurs
- **Logging détaillé** : Traces complètes pour debugging

## 🎯 Critères de succès

### **Critères obligatoires (PASS/FAIL)**
- [ ] **100%** formules FOL syntaxiquement valides
- [ ] **0** erreur parsing Tweety avec syntaxe FOL
- [ ] **>95%** compatibilité avec sophismes existants
- [ ] **Performance** ≤ Modal Logic précédent
- [ ] **>90%** couverture tests
- [ ] **Migration** transparente depuis Modal Logic

### **Critères d'amélioration**
- [ ] **Stabilité** améliorée (moins d'erreurs vs Modal Logic)
- [ ] **Confiance** moyenne > 70%
- [ ] **Gestion erreurs** gracieuse sur tous cas de test
- [ ] **Documentation** complète et exemples

## 🚦 Prochaines étapes

1. **Exécution initiale** : `python scripts/run_fol_tests.py --unit-only`
2. **Validation progressive** : Ajouter `--integration` puis `--real-tweety`
3. **Validation finale** : `python scripts/run_fol_tests.py --all --real-tweety`
4. **Déploiement** : Si tous critères validés
5. **Migration production** : Remplacement Modal Logic par FOL

---

**✅ Agent FOL validé** = Prêt pour remplacement de Modal Logic en production  
**⚠️ Validation partielle** = Corrections nécessaires avant déploiement  
**❌ Validation échouée** = Retour développement requis
