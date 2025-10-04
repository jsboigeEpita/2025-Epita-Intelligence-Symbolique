# Plan Master - Campagne de Nettoyage et Rationalisation du Dépôt

**Date de Début :** 2025-10-03  
**Status :** En Cours - Cartographie Complétée  
**Version :** 2.0 (Périmètre Élargi)

---

## Vue d'Ensemble

Cette campagne vise à rationaliser l'arborescence du dépôt Intelligence Symbolique EPITA après plusieurs mois d'intégrations successives. L'approche méthodique suit les principes **SDDD (Semantic-Documentation-Driven-Design)**.

### Découverte Critique
La cartographie exhaustive a révélé une situation beaucoup plus complexe que prévu :
- **1,736 fichiers** dans le scope (vs 1,526 estimés initialement)
- **320+ fichiers racine** dont **165+ obsolètes** (51% de pollution)
- **13 dossiers fantômes** ignorés mais présents localement
- **~147 MB** de node_modules potentiellement tracké par git
- **140+ logs vides** à la racine

---

## Périmètre

### ✅ Répertoires à Traiter (19 répertoires système)

#### Répertoires Phase 1 (Initiaux)
1. **docs/** (465 fichiers, ~25 MB) - Documentation projet
2. **scripts/** (417 fichiers, ~3 MB) - Scripts utilitaires
3. **tests/** (644 fichiers, ~4 MB) - Suite de tests

#### Répertoires Phase 2 (Élargis)
4. **demos/** (7 fichiers, ~38 KB) - Démonstrations EPITA
5. **examples/** (33 fichiers, ~304 KB) - Exemples pédagogiques
6. **tutorials/** (6 fichiers, ~20 KB) - Tutoriels formation
7. **api/** (10 fichiers, ~53 KB) - API FastAPI
8. **core/** (3 fichiers, ~8.5 KB) - Gestionnaire prompts
9. **src/** (51 fichiers, ~104 KB) - Infrastructure code ⚠️ 16 __pycache__
10. **plugins/** (56 fichiers, ~522 KB) - Extensions ⚠️ 12 __pycache__
11. **services/** (1000+ fichiers, ~147 MB) - Application React 🔴 **node_modules CRITIQUE**
12. **config/** (31 fichiers, ~109 KB) - Configuration système
13. **templates/** (1 fichier, ~0.8 KB) - Templates
14. **validation/** (3 fichiers, ~213 KB) - Rapports validation
15. **interface_web/** (13 fichiers, ~319 KB) - App web Flask
16. **libs/** (10 entrées) - Bibliothèques externes

#### Fichiers Racine (Priorité Haute)
17. **Fichiers racine** (~320+ fichiers) - 🔴 **PRIORITÉ CRITIQUE**
    - Configuration essentielle : 15 fichiers ✅
    - Scripts/outils : 20 fichiers (50% à ranger)
    - Documentation : 10 fichiers (30% à ranger)
    - **Obsolètes : ~165 fichiers** (logs vides, caches, screenshots)

#### Dossiers Fantômes (.gitignore)
18. **13 dossiers fantômes** - Ignorés mais présents localement
    - _temp_jdk_download/, _temp_prover9_install/, portable_jdk/
    - _temp_readme_restoration/, dummy_opentelemetry/
    - logs/, reports/, results/, node_modules/
    - argumentation_analysis.egg-info/

### ❌ Hors Périmètre (Projets Étudiants)
- `1_2_7_argumentation_dialogique/`, `1.4.1-JTMS/`, `2.1.6_multiagent_governance_prototype/`
- `2.3.2-detection-sophismes/`, `2.3.3-generation-contre-argument/`, `2.3.5_argument_quality/`, `2.3.6_local_llm/`
- `3.1.5_Interface_Mobile/`
- `abs_arg_dung/`, `Arg_Semantic_Index/`, `CaseAI/`, `documentation_system/`, `migration_output/`, `speech-to-text/`
- **argumentation_analysis/** ⚠️ **SOURCE PRINCIPAL** (reporté après campagne)

---

## Métriques Globales

### État Initial
- **Total fichiers scope :** ~1,736 fichiers
- **Taille totale :** ~182 MB (hors node_modules services/ ~147 MB)
- **Répertoires système :** 19 répertoires
- **Fichiers racine :** 320+ fichiers (51% pollution)
- **Dossiers fantômes :** 13 répertoires

### Objectifs Visés
- **Fichiers supprimés :** ~165+ fichiers (logs, caches, temporaires)
- **Fichiers déplacés :** ~30 fichiers (scripts, docs, screenshots)
- **Réduction taille :** ~150 MB (node_modules + caches + logs)
- **Organisation racine :** 51% → 85% (+34%)
- **Score découvrabilité :** 6.5/10 → 8.5/10 (+31%)

---

## Méthodologie Actualisée

### Approche 5 Phases (A → E)

Au lieu de l'approche initiale 3 mouvements (Descendant/Ascendant/Remontée), la cartographie a révélé la nécessité d'une approche séquencée en **5 phases** avec validation continue.

#### **PHASE A - Nettoyage Immédiat** ⚡ (Risque nul, Gain maximal)
**Priorité :** CRITIQUE - URGENT  
**Durée estimée :** 30 minutes  
**Actions :**
1. Supprimer ~140 logs vides racine (`trace_reelle_*.log`)
2. Supprimer tous les `__pycache__/` (31 fichiers)
3. Supprimer dossiers temporaires (_temp_jdk_download/, _temp_prover9_install/)
4. Vérifier node_modules NON-tracking git (CRITIQUE)
5. **Validation :** `git status` - Aucun fichier supprimé ne devrait apparaître

**Gain immédiat :** ~140 fichiers + caches, désencombrement massif

#### **PHASE B - Organisation Racine** (Risque faible)
**Priorité :** HAUTE  
**Durée estimée :** 1-2 heures  
**Actions :**
1. Déplacer 15 scripts test vers `scripts/testing/`
2. Déplacer 7 fichiers doc vers `docs/`
3. Déplacer 9 screenshots vers `.temp/screenshots/`
4. Archiver `_temp_readme_restoration/`
5. **Validation :** `pytest -v` - Tous tests passent

**Gain :** Racine 320+ → 170 fichiers (-47%)

#### **PHASE C - Nettoyage Technique** (Risque modéré)
**Priorité :** MOYENNE  
**Durée estimée :** 2-3 heures  
**Actions :**
1. Évaluer `api/*_simple.py` (déplacer vers examples/ ou supprimer)
2. Déplacer `hello_world_plugin/` vers `examples/`
3. Nettoyer dossiers fantômes (logs/, reports/, results/)
4. Optimiser `.gitignore` (supprimer redondances, ajouter patterns)
5. **Validation :** `pytest -v` + Validation manuelle dépendances

**Gain :** .gitignore optimisé, dossiers fantômes nettoyés

#### **PHASE D - Campagne Répertoires** (Post-nettoyage racine)
**Priorité :** PROGRESSIVE  
**Durée estimée :** 8-12 heures (répartis en 4 sous-phases)

**D1 - docs/ (déjà analysé Phase 1)**
- Nettoyer archives massives (~14 MB)
- Ventiler 98 fichiers racine docs/
- Créer hubs documentation
- **Validation :** Tests + Recherche sémantique

**D2 - demos/, examples/, tutorials/ (risque faible)**
- Valider structure existante
- Compléter documentation si nécessaire
- **Validation :** pytest demos/

**D3 - tests/ (Phase 1 - risque modéré)**
- Rationaliser hiérarchie `unit/argumentation_analysis/` (98 fichiers)
- Optimiser structure fixtures/mocks
- **Validation :** `pytest -v` complet

**D4 - scripts/ (Phase 1 - risque élevé)**
- Résoudre duplication `maintenance/` vs `maintenance/tools/`
- Rationaliser validation/ (61 fichiers)
- **Validation :** Tests complets + Validation scripts critiques

#### **PHASE E - Post-Campagne** (Refactoring)
**Priorité :** REPORTÉ  
**Actions :**
1. ⏸️ `argumentation_analysis/` (source principal)
2. ⏸️ Refactoring architecture si nécessaire

---

## Priorisation Détaillée

### 🔴 **PRIORITÉ 1 - HAUTE** (Gain rapide, Risque faible)

| Action | Fichiers | Gain | Risque | Complexité |
|--------|----------|------|--------|------------|
| 1.1 Logs obsolètes racine | ~140 | Désencombrement massif | Nul | Triviale |
| 1.2 Dossiers fantômes temporaires | 3+ dirs | Espace disque | Faible | Faible |
| 1.3 Caches Python __pycache__ | 31 | Nettoyage | Nul | Triviale |
| 1.4 Vérifier node_modules tracking | ~147 MB | Réduction taille repo | Faible | Modérée |

### 🟡 **PRIORITÉ 2 - MOYENNE** (Organisation)

| Action | Fichiers | Gain | Risque | Validation |
|--------|----------|------|--------|------------|
| 2.1 Scripts test → scripts/testing/ | 15 | Organisation | Modéré | pytest -v |
| 2.2 Documentation → docs/ | 7 | Consolidation | Faible | Aucune |
| 2.3 Screenshots → .temp/ | 9 (~3.3 MB) | Désencombrement | Faible | Aucune |
| 2.4 api/*_simple.py | 3 | Réduction duplication | Modéré | Tests API |

### 🟠 **PRIORITÉ 3 - MODÉRÉE** (Technique)

| Action | Gain | Risque | Validation |
|--------|------|--------|------------|
| 3.1 services/node_modules | -147 MB | Faible | git status |
| 3.2 hello_world_plugin/ → examples/ | Organisation | Faible | pytest plugins/ |
| 3.3 Optimiser .gitignore | Maintenance | Faible | Review |

### 🔵 **PRIORITÉ 4 - BASSE** (Campagne répertoires)

| Répertoire | Fichiers | Risque | Validation |
|------------|----------|--------|------------|
| docs/ | 465 | Faible | Liens + Recherche |
| demos/examples/tutorials/ | 46 | Faible | pytest |
| tests/ | 644 | Modéré | pytest -v |
| scripts/ | 417 | Élevé | Tests complets |

---

## Alertes Critiques

### 🔴 **CRITIQUE - IMMÉDIAT**
1. **services/node_modules/** (~147 MB) - Vérifier IMPÉRATIVEMENT non-tracking git
2. **Fichiers racine** (320+ dont 165+ obsolètes) - 51% pollution massive

### ⚠️ **ATTENTION - URGENT**
3. **Patterns .gitignore** - `*.txt` ligne 277 trop générique, redondances .env
4. **Caches multiples** - __pycache__/ dans 5+ répertoires, 31 fichiers .pyc

### ℹ️ **INFO - POSITIF**
5. **Structure examples/** - Bien organisée (sous-répertoires clairs)
6. **Architecture config/** - Séparation claire (pytest/, clean/, templates/)

---

## Principes SDDD Appliqués

### Avant Chaque Phase
- ✅ **Grounding sémantique** : Recherche contexte avant action
- ✅ **Cartographie** : Inventaire exhaustif fichiers/dépendances

### Pendant Chaque Phase
- ✅ **Commits fréquents** : Max 20 fichiers par commit
- ✅ **Git push régulier** : Après chaque commit
- ✅ **Checkpoints SDDD** : Recherche sémantique tous les 2-3 actions

### Après Chaque Phase
- ✅ **Validation tests** : `pytest -v` systématique
- ✅ **Recherche sémantique** : Validation découvrabilité
- ✅ **Documentation** : Mise à jour rapports + logs commits

---

## Progression

### ✅ Phase Préparation (Complétée)
- [x] Cartographie initiale docs/scripts/tests/
- [x] Cartographie élargie 16 répertoires supplémentaires
- [x] Analyse fichiers racine (320+ inventoriés)
- [x] Analyse .gitignore + dossiers fantômes
- [x] Documentation rapports complets

### 🔄 Phase Exécution (En Cours)
- [ ] **PHASE A** - Nettoyage immédiat
- [ ] **PHASE B** - Organisation racine
- [ ] **PHASE C** - Nettoyage technique
- [ ] **PHASE D1** - Traitement docs/
- [ ] **PHASE D2** - Traitement demos/examples/tutorials/
- [ ] **PHASE D3** - Traitement tests/
- [ ] **PHASE D4** - Traitement scripts/

### ⏸️ Phase Post-Campagne (Reportée)
- [ ] **PHASE E** - argumentation_analysis/ (source principal)
- [ ] Refactoring architecture

---

## Protocole Validation

### Validation Niveau 1 (Après chaque action)
```bash
git status  # Vérifier fichiers modifiés
```

### Validation Niveau 2 (Après chaque phase)
```bash
pytest -v  # Suite tests complète
```

### Validation Niveau 3 (Checkpoints SDDD)
- Recherche sémantique découvrabilité
- Vérification liens documentation
- Review manuelle structure

### Validation Niveau 4 (Post-campagne)
```bash
pytest  # Tests complets
```
- Validation utilisateur
- Grounding sémantique final

---

## Documentation Continue

### Logs Centralisés
- **03_commits_log.md** : Tous les commits avec métadonnées
- **02_phases/phase_*/**: Rapports détaillés par phase

### Rapports Techniques
- **01_cartographie_initiale/rapport_cartographie.md** : Cartographie exhaustive (493 lignes)
- **04_rapport_final.md** : Rapport clôture campagne

---

## Commandes Clés

### Phase A - Nettoyage Immédiat
```powershell
# Supprimer logs vides
Get-ChildItem -Filter "trace_reelle_*.log" | Where-Object {$_.Length -eq 0} | Remove-Item

# Supprimer __pycache__
Get-ChildItem -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force

# Vérifier node_modules tracking
git ls-files services/**/node_modules/
```

### Phase B+ - Validation Continue
```bash
# Tests après chaque déplacement
pytest -v

# Vérifier git status
git status

# Commit progressif
git add .
git commit -m "type(scope): message"
git push
```

---

## Métriques de Succès

| Métrique | Avant | Objectif | Gain |
|----------|-------|----------|------|
| **Fichiers racine** | 320+ | 170 | -47% |
| **Taille repo** | ~182 MB | ~32 MB | -150 MB |
| **Organisation** | 51% | 85% | +34% |
| **Score découvrabilité** | 6.5/10 | 8.5/10 | +31% |
| **Tests passants** | 100% | 100% | Maintenu |

---

## Historique Versions

| Version | Date | Changement |
|---------|------|------------|
| 1.0 | 2025-10-03 | Plan initial (3 répertoires) |
| 2.0 | 2025-10-03 | Périmètre élargi (19 répertoires + racine + .gitignore) |

---

**📊 Plan Master Actualisé - Campagne Prête**  
**🎯 Prochaine Étape : Commit Initial puis PHASE A**  
**📅 Dernière mise à jour : 2025-10-03 18:58 CET**