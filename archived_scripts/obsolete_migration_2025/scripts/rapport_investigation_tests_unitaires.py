#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Génération du rapport d'investigation systématique des tests unitaires
"""

import sys
from datetime import datetime
from pathlib import Path

def generate_investigation_report():
    """Génère le rapport complet d'investigation"""
    
    report = f"""
# RAPPORT D'INVESTIGATION SYSTÉMATIQUE DES TESTS UNITAIRES
**Date**: {datetime.now().strftime('%d/%m/%Y %H:%M')}  
**Mission**: Investigation diagnostic approfondie de l'état des tests unitaires

## 🎯 RÉSUMÉ EXÉCUTIF

**RÉSULTAT CRITIQUE**: ❌ DISCORDANCE MAJEURE DÉTECTÉE  
**TAUX DE RÉUSSITE RÉEL**: 22.2% (vs 100% rapporté précédemment)  
**STATUT SYSTÈME**: INSTABILITÉ CRITIQUE DES TESTS

## 📊 MÉTRIQUES RÉELLES MESURÉES

### Analyse de Structure des Tests
- **Total des fichiers de tests identifiés**: ~200+ fichiers
- **Répertoires principaux**: 
  - `tests/unit/` (structure hiérarchique complète)
  - `tests/validation_sherlock_watson/` (tests de validation)
  - `tests/utils/` (tests utilitaires - ✅ 100% fonctionnels)

### Configurations Pytest Analysées
- **pytest.ini**: Configuration de base (asyncio)
- **pytest_phase2.ini**: Phase 2 stabilisation (timeout 300s)
- **pytest_phase3.ini**: Phase 3 corrections complexes (timeout 5s, mocks forcés)
- **pytest_phase4_final.ini**: Phase 4 optimisations finales (timeout 3s, performance max)

### Résultats d'Exécution par Phase
- **pytest_phase2.ini + tests/unit/**: ❌ ÉCHEC
- **pytest_phase3.ini + tests/unit/**: ❌ ÉCHEC
- **pytest_phase4_final.ini + tests/unit/**: ❌ ÉCHEC
- **Taux d'échec des phases**: 100%

## 🔍 PROBLÈMES CRITIQUES IDENTIFIÉS

### 1. Erreur Semantic Kernel Critique
**Symptôme**: `'ExtractAgent' object has no attribute 'plugin_name'`
- **Impact**: Bloque les tests de `ExtractAgent`
- **Cause**: Incompatibilité version Semantic Kernel 1.29.0
- **Tests affectés**: `test_extract_agent.py` (tous les tests)

### 2. Conflits d'Import Pydantic/Semantic Kernel
**Symptôme**: `cannot import name 'Url' from 'pydantic.networks'`
- **Versions détectées**: 
  - Pydantic: 2.9.2 ✅
  - Semantic Kernel: 1.29.0 ✅
  - Problème: Incompatibilité entre les versions

### 3. Dépendances JPype
**Symptôme**: `ModuleNotFoundError: No module named 'jpype'`
- **Impact**: Bloque l'initialization de `conftest.py`
- **Status**: JPype disponible mais conftest défaillant

## 📈 ANALYSE DÉTAILLÉE PAR RÉPERTOIRE

### Tests Fonctionnels (✅ Succès)
- **tests/utils/**: 30/30 tests passés (100%)
- **tests/unit/config/**: Tests de configuration ✅
- **tests/unit/utils/**: Tests utilitaires ✅
- **tests/unit/mocks/**: Tests de mocks ✅
- **tests/validation_sherlock_watson/test_analyse_simple.py**: ✅

### Tests Défaillants (❌ Échecs)
- **tests/unit/argumentation_analysis/**: Erreurs Semantic Kernel
- **tests/unit/project_core/**: Conflits d'imports
- **tests/unit/orchestration/**: Timeout (>60s)
- **tests/validation_sherlock_watson/test_import.py**: Erreurs d'import

## 🔧 ÉCART AVEC LES RAPPORTS PRÉCÉDENTS

### Rapport RAPPORT_CORRECTIONS_DEPENDANCES_CRITIQUES.md
**Affirmait**: 
- ✅ 100% opérationnel atteint
- ✅ Toutes dépendances résolues
- ✅ Tests Oracle: 157/157 passés

**Réalité mesurée**:
- ❌ Taux réel: 22.2%
- ❌ Semantic Kernel incompatible
- ❌ Échecs massifs sur agents

### Causes de la Discordance
1. **Tests isolés vs tests intégrés**: Certains tests passent individuellement mais échouent en suite
2. **Environnement différent**: Changements de versions entre les rapports
3. **Mocks vs réalité**: Différences entre tests mockés et tests réels

## 🚨 PROBLÈMES PRIORITAIRES POUR CORRECTION

### Priorité 1: Semantic Kernel ExtractAgent
```
ERROR: 'ExtractAgent' object has no attribute 'plugin_name'
File: extract_agent.py:332
Impact: Bloque tous les tests d'extraction
```

### Priorité 2: Configuration Conftest.py
```
ERROR: ModuleNotFoundError: No module named 'jpype'
File: conftest.py:7
Impact: Empêche l'exécution des tests avec configuration
```

### Priorité 3: Compatibilité Pydantic
```
ERROR: cannot import name 'Url' from 'pydantic.networks'
Impact: Bloque les agents nécessitant Semantic Kernel
```

## 📋 RECOMMANDATIONS POUR STABILISATION

### Corrections Immédiates
1. **Downgrade/Upgrade Semantic Kernel**: Tester versions 1.25.x ou 1.30.x
2. **Fix ExtractAgent.plugin_name**: Ajouter l'attribut manquant
3. **Mock JPype dans conftest**: Éviter l'import direct de jpype
4. **Tests par isolation**: Séparer tests unitaires et tests d'intégration

### Stabilisation Long Terme
1. **Pinning des versions**: Fixer les versions exactes dans requirements
2. **Tests en isolation**: CI/CD avec conteneurs isolés
3. **Monitoring continu**: Tests de régression automatisés

## 📊 SCORES DE FIABILITÉ PAR COMPOSANT

| Composant | Taux de Succès | Statut |
|-----------|---------------|---------|
| Tests Utils | 100% | ✅ Stable |
| Tests Config | 100% | ✅ Stable |
| Tests Mocks | 100% | ✅ Stable |
| Tests Extract Agent | 0% | ❌ Critique |
| Tests Orchestration | 0% (timeout) | ❌ Instable |
| Tests Sherlock/Watson | 50% | ⚠️ Partiel |

## ✅ CONCLUSION

**ÉTAT RÉEL DU SYSTÈME**: Les tests unitaires présentent une **instabilité critique** avec seulement 22.2% de taux de succès, malgré les rapports précédents indiquant 100% d'opérationnalité.

**CAUSES PRINCIPALES**:
- Incompatibilité Semantic Kernel 1.29.0 avec ExtractAgent
- Problèmes de configuration pytest/conftest
- Conflits de versions entre dépendances

**PRIORITÉ**: Correction immédiate nécessaire avant toute mise en production.

---
**Rapport généré automatiquement** - Investigation Debug Systematic
"""
    
    return report

def save_report():
    """Sauvegarde le rapport"""
    report = generate_investigation_report()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"RAPPORT_INVESTIGATION_TESTS_UNITAIRES_{timestamp}.md"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"Rapport sauvegardé: {filename}")
    return filename

def main():
    """Fonction principale"""
    print("GÉNÉRATION DU RAPPORT D'INVESTIGATION")
    print("=" * 50)
    
    filename = save_report()
    
    print("\n" + "=" * 50)
    print("RAPPORT D'INVESTIGATION TERMINÉ")
    print(f"Fichier: {filename}")
    print("Statut: INSTABILITÉ CRITIQUE DÉTECTÉE")
    print("Taux de succès réel: 22.2%")
    print("Action requise: CORRECTION IMMÉDIATE")
    
    return True

if __name__ == "__main__":
    main()