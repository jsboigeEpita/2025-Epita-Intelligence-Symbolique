# ORCHESTRATION CONVERSATIONNELLE UNIFIÉE

## 🎯 Objectif

Ce script **`orchestration_conversation_unified.py`** consolide et remplace tous les scripts éparpillés d'orchestration conversationnelle d'analyse rhétorique.

## 📋 Scripts Remplacés

### ✅ Scripts Consolidés
| Script Original | Fonctionnalité | Status |
|---|---|---|
| `test_trace_analyzer_conversation_format.py` | Test format conversation | ✅ **REMPLACÉ** par mode `trace` |
| `test_micro_orchestration.py` | Orchestration légère | ✅ **REMPLACÉ** par mode `micro` |
| `demo/demo_conversation_capture_complete.py` | Capture complète | ✅ **REMPLACÉ** par mode `demo` |
| `demo/run_analysis_with_complete_trace.py` | Analyse avec trace | ✅ **REMPLACÉ** par mode `demo` |
| `demo/test_enhanced_pm_components.py` | Test PM amélioré | ✅ **REMPLACÉ** par mode `enhanced` |

### 🔄 Migration Simple
```bash
# AVANT (5 scripts différents)
python test_micro_orchestration.py
python demo/demo_conversation_capture_complete.py
python test_trace_analyzer_conversation_format.py
python demo/test_enhanced_pm_components.py
python demo/run_analysis_with_complete_trace.py

# APRÈS (1 script unifié)
python orchestration_conversation_unified.py --mode micro
python orchestration_conversation_unified.py --mode demo
python orchestration_conversation_unified.py --mode trace
python orchestration_conversation_unified.py --mode enhanced
```

## 🚀 Utilisation

### Modes Disponibles

#### 1. Mode MICRO (Ultra-léger)
```bash
python orchestration_conversation_unified.py --mode micro --save
```
- **Contraintes :** < 1000ms, 8 messages max, 6 outils max
- **Agents :** InformalAgent + ModalLogicAgent
- **Usage :** Tests rapides, validation basique

#### 2. Mode DEMO (Démonstration complète)
```bash
python orchestration_conversation_unified.py --mode demo --save
```
- **Contraintes :** Normales (20 messages, 15 outils)
- **Agents :** InformalAgent + ModalLogicAgent + SynthesisAgent
- **Usage :** Démonstrations, présentations

#### 3. Mode TRACE (Test du traçage)
```bash
python orchestration_conversation_unified.py --mode trace --save
```
- **Focus :** Validation du système de capture
- **Usage :** Debug, développement du traçage

#### 4. Mode ENHANCED (Composants PM améliorés)
```bash
python orchestration_conversation_unified.py --mode enhanced --save
```
- **Focus :** Test des composants Project Manager
- **Usage :** Validation architecture PM

### Options

```bash
python orchestration_conversation_unified.py [OPTIONS]

OPTIONS:
  --mode {micro,demo,trace,enhanced}  Mode d'orchestration (défaut: demo)
  --text "Texte à analyser"           Texte d'entrée (défaut: exemple Ukraine)
  --save                              Sauvegarder le rapport markdown
  --help                              Afficher l'aide
```

## 📊 Exemples d'Utilisation

### Test Rapide (Mode Micro)
```bash
python orchestration_conversation_unified.py --mode micro
```

**Sortie attendue :**
```
[OK] Performance mode micro: <1000ms
[OK] Messages conversationnels: 7 capturés
[OK] Appels d'outils: 5 capturés
[OK] Orchestration complète: OUI
```

### Démonstration Complète
```bash
python orchestration_conversation_unified.py --mode demo --text "Votre texte argumentatif ici" --save
```

**Générera :** `logs/orchestration_conversationnelle_demo_YYYYMMDD_HHMMSS.md`

## 🏗️ Architecture Unifiée

### Composants Centralisés

#### `UnifiedConversationLogger`
- Capture messages conversationnels
- Log appels d'outils avec troncature intelligente
- Snapshots d'état configurable selon mode

#### `UnifiedAnalysisState`
- État partagé unifié entre tous les agents
- Métriques consolidées (score, sophismes, propositions)
- Suivi de progression par phase

#### `SimulatedAgent`
- Agents simulés pour tous les modes
- Types : informal, modal, synthesis
- Messages conversationnels réalistes

#### `UnifiedOrchestrator`
- Orchestration adaptée au mode sélectionné
- Coordination PM centralisée
- Génération rapports markdown

## 📈 Avantages de l'Unification

### ✅ Consolidation
- **5 scripts → 1 script unifié**
- Maintenance simplifiée
- Code dédupliqué

### ⚡ Performance
- Mode micro : < 1000ms garanti
- Troncature intelligente automatique
- Limites configurables par mode

### 📋 Consistency
- Format de rapport uniforme
- Messages conversationnels standardisés
- API unifié pour tous les modes

### 🔧 Maintenabilité
- Un seul point de maintenance
- Configuration centralisée
- Tests unifiés

## 🧪 Validation

### Tests Automatiques
```bash
# Test de tous les modes
for mode in micro demo trace enhanced; do
    echo "Testing mode: $mode"
    python orchestration_conversation_unified.py --mode $mode
done
```

### Métriques de Performance
- **Mode micro :** < 1000ms, < 120 lignes rapport
- **Mode demo :** < 5000ms, < 300 lignes rapport
- **Tous modes :** 0 erreur, rapport markdown valide

## 📚 Comparaison Formats

### Format Conversation Agentielle
```markdown
## [CONVERSATION] Messages Agentiels

### [0.0ms] **ProjectManager** (coordination)
> *"Démarrage de l'orchestration d'analyse rhétorique..."*

### [15.2ms] **InformalAgent** (informal_analysis)  
> *"Je vais analyser ce texte pour détecter les sophismes..."*
```

### Format Appels d'Outils
```markdown
## [TOOLS] Appels d'Outils

### [15.2ms] [OK] **InformalAgent** -> `detect_sophisms_from_taxonomy`
**Arguments:** {'text': "L'Ukraine a été...", 'branches': ['logical'...]}
**Résultat:** [{'type': 'Historical Rewriting', 'confidence': 0.85}...]
```

## 🎯 Prochaines Étapes

1. **Migration complète :** Déplacer anciens scripts vers `/legacy`
2. **Tests d'intégration :** Valider avec vrais agents
3. **Configuration YAML :** Externaliser paramètres
4. **Templates personnalisés :** Formats de rapport modulaires

---

**Status :** ✅ **OPÉRATIONNEL**  
**Dernière mise à jour :** 2025-06-07  
**Auteur :** Système de refactorisation orchestration conversationnelle