# Guide de Nettoyage du Dépôt Git
## Intelligence Symbolique - Restructuration Automatisée

---

## 📋 Vue d'Ensemble

Ce guide détaille la procédure complète de nettoyage et réorganisation du dépôt Intelligence Symbolique, incluant :

- **17 tests éparpillés** à déplacer de la racine vers `tests/`
- **28+ rapports** à organiser dans `docs/`
- **Fichiers temporaires** volumineux à supprimer (2.4MB)
- **Structure documentaire** à optimiser

## 🛠️ Scripts Disponibles

### 1. Script Principal : `depot_cleanup_migration.ps1`
**Emplacement :** `scripts/maintenance/depot_cleanup_migration.ps1`

#### Modes d'Exécution

```powershell
# PREVIEW - Voir ce qui va être fait (RECOMMANDÉ EN PREMIER)
.\scripts\maintenance\depot_cleanup_migration.ps1 -Mode preview

# EXECUTE - Exécuter la migration complète  
.\scripts\maintenance\depot_cleanup_migration.ps1 -Mode execute

# CLEANUP-ONLY - Nettoyer uniquement les fichiers temporaires
.\scripts\maintenance\depot_cleanup_migration.ps1 -Mode cleanup-only
```

#### Options Avancées

```powershell
# Exécuter sans sauvegarde Git (non recommandé)
.\scripts\maintenance\depot_cleanup_migration.ps1 -Mode execute -CreateBackup $false

# Mode verbose pour plus de détails
.\scripts\maintenance\depot_cleanup_migration.ps1 -Mode preview -Verbose
```

### 2. Script de Validation : `validate_migration.ps1`
**Emplacement :** `scripts/maintenance/validate_migration.ps1`

```powershell
# Validation basique post-migration
.\scripts\maintenance\validate_migration.ps1

# Validation avec tests d'imports Python
.\scripts\maintenance\validate_migration.ps1 -RunTests

# Mode verbose pour plus de détails
.\scripts\maintenance\validate_migration.ps1 -Verbose
```

---

## 🚀 Procédure Complète Recommandée

### Étape 1 : Préparation
```powershell
# Vérifier l'état actuel du dépôt
git status

# S'assurer d'être à la racine du projet
cd d:\2025-Epita-Intelligence-Symbolique-4

# Sauvegarder les modifications en cours
git add -A
git commit -m "Sauvegarde avant nettoyage automatique"
```

### Étape 2 : Preview (OBLIGATOIRE)
```powershell
# Voir exactement ce qui va être fait
.\scripts\maintenance\depot_cleanup_migration.ps1 -Mode preview
```

**Exemple de sortie attendue :**
```
===============================================================================
 PREVIEW - ACTIONS QUI SERONT EFFECTUÉES
===============================================================================

📁 CRÉATION DE RÉPERTOIRES
[CRÉER] tests/demos/fol
        Raison: Nouveau répertoire organisationnel

🧪 DÉPLACEMENT DES TESTS (17 fichiers)
[DÉPLACER] test_fol_demo_simple.py → tests/demos/fol/
           Taille: 5.6KB
           Raison: Démo FOL simple

📋 DÉPLACEMENT DES RAPPORTS (28 fichiers)  
[DÉPLACER] AUDIT_AUTHENTICITE_FOL_COMPLETE.md → docs/audits/
           Taille: 3.4KB
           Raison: Audit authenticité FOL

🗑️ SUPPRESSION FICHIERS TEMPORAIRES
[SUPPRIMER] temp_original_file.enc
            Taille: 2032.7KB
            Raison: Fichier temporaire
```

### Étape 3 : Exécution
```powershell
# Exécuter la migration (crée automatiquement une sauvegarde)
.\scripts\maintenance\depot_cleanup_migration.ps1 -Mode execute
```

### Étape 4 : Validation
```powershell
# Valider que tout s'est bien passé
.\scripts\maintenance\validate_migration.ps1 -RunTests
```

### Étape 5 : Finalisation
```powershell
# Vérifier les changements Git
git status

# Ajouter tous les changements
git add -A

# Committer la réorganisation
git commit -m "Réorganisation structure projet - migration automatique

- Déplacement 17 tests racine → tests/[domain]/
- Organisation 28 rapports → docs/reports/
- Suppression fichiers temporaires (2.4MB)
- Création structure répertoires thématiques"

# Optionnel : Supprimer la branche de sauvegarde si tout va bien
git branch -d backup-cleanup-YYYYMMDD-HHMMSS
```

---

## 📁 Nouvelle Structure Créée

### Tests Organisés
```
tests/
├── demos/
│   ├── fol/                    # Démos First Order Logic
│   ├── modal/                  # Démos logique modale
│   ├── rhetorical/            # Démos analyse rhétorique
│   └── retry/                 # Démos mécanismes retry
├── integration/
│   ├── conversation/          # Tests intégration conversation
│   ├── modal/                 # Tests intégration modale
│   ├── orchestration/         # Tests micro-orchestration
│   ├── retry/                 # Tests mécanismes retry
│   ├── sources/               # Tests gestion sources
│   ├── reporting/             # Tests génération rapports
│   ├── analysis/              # Tests analyse de texte
│   └── pipelines/             # Tests pipelines unifiés
├── validation/
│   └── modal/                 # Tests validation modale
└── unit/
    └── analyzers/             # Tests unitaires analyseurs
```

### Documentation Organisée
```
docs/
├── audits/                    # Audits techniques
├── reports/
│   ├── analysis/             # Rapports d'analyse
│   ├── consolidation/        # Rapports consolidation
│   ├── fol/                  # Rapports FOL spécifiques
│   ├── implementation/       # Rapports implémentation
│   ├── refactoring/          # Rapports refactorisation
│   ├── testing/              # Rapports de tests
│   └── various/              # Autres rapports
├── testing/                  # Documentation tests
└── validation/               # Rapports validation
```

---

## 🎯 Mapping des Déplacements

### Tests Principaux
| Ancien Emplacement | Nouvel Emplacement | Type |
|-------------------|-------------------|------|
| `test_fol_demo_simple.py` | `tests/demos/fol/` | Démo FOL |
| `test_advanced_rhetorical_enhanced.py` | `tests/integration/rhetorical/` | Test intégration |
| `test_conversation_integration.py` | `tests/integration/conversation/` | Test intégration |
| `test_micro_orchestration.py` | `tests/integration/orchestration/` | Test orchestration |
| `test_modal_correction_validation.py` | `tests/validation/modal/` | Validation |

### Rapports Clés  
| Ancien Emplacement | Nouvel Emplacement | Catégorie |
|-------------------|-------------------|-----------|
| `AUDIT_AUTHENTICITE_FOL_COMPLETE.md` | `docs/audits/` | Audit technique |
| `RAPPORT_EVALUATION_TESTS_SYSTEME.md` | `docs/reports/testing/` | Tests système |
| `SYNTHESE_FINALE_REFACTORISATION_UNIFIED_REPORTS.md` | `docs/reports/refactoring/` | Refactorisation |

---

## 🛡️ Sécurité et Sauvegarde

### Sauvegardes Automatiques
Le script crée automatiquement :
- **Branche Git** : `backup-cleanup-YYYYMMDD-HHMMSS`
- **Commit automatique** des changements en cours
- **Retour possible** avec `git checkout backup-cleanup-*`

### Récupération en Cas de Problème
```powershell
# Lister les branches de sauvegarde
git branch | grep backup-cleanup

# Revenir à l'état avant migration
git checkout backup-cleanup-20250607-165230

# Récupérer des fichiers spécifiques
git checkout backup-cleanup-20250607-165230 -- test_fol_demo.py
```

---

## 🔍 Validation et Tests

### Vérifications Automatiques
Le script de validation vérifie :

- ✅ **Structure répertoires** : Tous les dossiers créés
- ✅ **Fichiers déplacés** : Aucun fichier perdu  
- ✅ **Nettoyage temporaires** : Suppression confirmée
- ✅ **Propreté racine** : Plus de tests/rapports éparpillés
- ✅ **Statut Git** : Changements trackés
- ✅ **Intégrité imports** : Modules Python fonctionnels

### Tests Manuels Recommandés
Après migration, tester :

```powershell
# Test environnement projet
powershell -File .\scripts\env\activate_project_env.ps1 -CommandToRun "python -c 'import argumentation_analysis; print(\"Import OK\")'"

# Test d'un fichier déplacé
powershell -File .\scripts\env\activate_project_env.ps1 -CommandToRun "python tests/demos/fol/test_fol_demo_simple.py"

# Tests unitaires généraux
powershell -File .\scripts\env\activate_project_env.ps1 -CommandToRun "python -m pytest tests/unit/ -v"
```

---

## 📊 Impact Attendu

| Métrique | Avant | Après | Amélioration |
|----------|-------|-------|--------------|
| **Fichiers racine** | 95 | ~15 | -84% |
| **Tests organisés** | 0% | 100% | +++++ |
| **Docs structurées** | 20% | 95% | +++++ |
| **Temps navigation** | Lent | Rapide | +++++ |
| **Maintenabilité** | Difficile | Excellente | +++++ |

---

## 🆘 Support et Dépannage

### Erreurs Courantes

**Erreur : "impossible de déplacer le fichier"**
```powershell
# Vérifier les permissions
Get-Acl test_fol_demo.py

# Forcer la fermeture des fichiers ouverts dans VS Code
# Puis relancer le script
```

**Erreur : "répertoire inexistant"**
```powershell
# Le script crée automatiquement les répertoires
# Si erreur persiste, créer manuellement :
New-Item -ItemType Directory -Path "tests/demos/fol" -Force
```

**Imports Python cassés après migration**
```powershell
# Vérifier les chemins Python
powershell -File .\scripts\env\activate_project_env.ps1 -CommandToRun "python -c 'import sys; print(\"\n\".join(sys.path))'"

# Réinstaller le package en mode développement
powershell -File .\scripts\env\activate_project_env.ps1 -CommandToRun "pip install -e ."
```

### Obtenir de l'Aide

1. **Preview first** : Toujours utiliser `-Mode preview` avant exécution
2. **Logs détaillés** : Utiliser `-Verbose` pour plus d'informations  
3. **Validation** : Exécuter `validate_migration.ps1` après chaque migration
4. **Sauvegarde** : Les branches backup permettent un retour rapide

---

## 📝 Maintenance Future

### Règles de Bonnes Pratiques
- ✅ **Tests** → Toujours dans `tests/[type]/[domain]/`
- ✅ **Rapports** → Toujours dans `docs/reports/[category]/`
- ✅ **Docs** → Structure thématique dans `docs/`
- ❌ **Éviter** les fichiers temporaires à la racine
- ❌ **Éviter** les tests éparpillés hors de `tests/`

### Script de Maintenance Préventive
```powershell
# Vérification mensuelle de la propreté
.\scripts\maintenance\validate_migration.ps1 -Verbose

# Nettoyage préventif des temporaires
.\scripts\maintenance\depot_cleanup_migration.ps1 -Mode cleanup-only
```

---

**✨ Avec cette restructuration, votre dépôt Intelligence Symbolique sera parfaitement organisé et maintenable !**
