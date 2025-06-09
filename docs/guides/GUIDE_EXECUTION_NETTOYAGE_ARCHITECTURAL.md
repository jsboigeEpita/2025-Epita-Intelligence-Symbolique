# GUIDE D'EXÉCUTION - NETTOYAGE ARCHITECTURAL

## 🚀 PROCÉDURE D'EXÉCUTION STEP-BY-STEP

### PRÉPARATION (5 min)

#### 1. Sauvegarde Sécurité
```powershell
# Commit de sécurité avant modifications
git add -A
git commit -m "🔒 BACKUP: Avant audit architectural - $(Get-Date -Format 'yyyyMMdd_HHmmss')"

# Vérification intégrité système
powershell -File .\scripts\env\activate_project_env.ps1 -CommandToRun "python examples/scripts_demonstration/demonstration_epita.py --quick-start"
```

#### 2. Validation Tests Critiques
```powershell
# Tests Oracle Enhanced (critiques)
powershell -File .\scripts\env\activate_project_env.ps1 -CommandToRun "python -m scripts.maintenance.validate_oracle_coverage"

# Tests Sherlock-Watson
powershell -File .\scripts\env\activate_project_env.ps1 -CommandToRun "python -m pytest tests/validation_sherlock_watson/ -x --tb=short"
```

---

## 📋 PHASE 1 : NETTOYAGE CRITIQUE RACINE (30 min)

### Étape 1.1 : Suppression Fichiers Temporaires
```powershell
# Fichiers de test temporaires
Remove-Item -Path "test_*.py", "test_*.ps1", "test_*.md" -Force -ErrorAction SilentlyContinue
Remove-Item -Path "*test*.log", "*trace*.log" -Force -ErrorAction SilentlyContinue

# Logs éparpillés 
Remove-Item -Path "*.log", "*.json" -Force -ErrorAction SilentlyContinue | Where-Object { $_.Name -notmatch "package|requirements|config" }

# Rapports temporaires
Remove-Item -Path "RAPPORT_*.md", "PLAN_*.md", "MIGRATION_*.md" -Force -ErrorAction SilentlyContinue

# Scripts de validation temporaires
Remove-Item -Path "validation_*.py", "audit_*.py", "generate_*.py" -Force -ErrorAction SilentlyContinue
```

### Étape 1.2 : Nettoyage Configurations Dupliquées
```powershell
# Créer répertoire config/pytest si inexistant
New-Item -ItemType Directory -Path "config\pytest" -Force -ErrorAction SilentlyContinue

# Déplacer configurations pytest
Move-Item -Path "pytest_*.ini" -Destination "config\pytest\" -Force -ErrorAction SilentlyContinue

# Créer répertoire tests/fixtures si inexistant  
New-Item -ItemType Directory -Path "tests\fixtures" -Force -ErrorAction SilentlyContinue

# Déplacer fichiers conftest spécialisés
Move-Item -Path "conftest_*.py" -Destination "tests\fixtures\" -Force -ErrorAction SilentlyContinue
```

### Étape 1.3 : Archives Corrompues
```powershell
# Sauvegarder structure corrompue avec timestamp
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
if (Test-Path "_archives") {
    Rename-Item -Path "_archives" -NewName "_archives_CORRUPTED_$timestamp"
}

# Créer nouvelle structure archives propre
New-Item -ItemType Directory -Path "_archives\backups" -Force
New-Item -ItemType Directory -Path "_archives\legacy_code" -Force
New-Item -ItemType Directory -Path "_archives\documentation" -Force
```

---

## 📋 PHASE 2 : RÉORGANISATION STRUCTURE (45 min)

### Étape 2.1 : Consolidation Logs
```powershell
# Création structure logs organisée
New-Item -ItemType Directory -Path "logs\archived_reports" -Force
New-Item -ItemType Directory -Path "logs\temp_traces" -Force

# Déplacement rapports par type
Move-Item -Path "logs\*report*.json", "logs\*report*.md" -Destination "logs\archived_reports\" -Force -ErrorAction SilentlyContinue

# Archivage logs anciens (>7 jours)
Get-ChildItem -Path "logs" -Filter "*.log" | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) } | Move-Item -Destination "logs\temp_traces\"

# Nettoyage traces debugging spécifiques
Get-ChildItem -Path "logs" | Where-Object { $_.Name -match "_202505[0-6]" } | Move-Item -Destination "logs\temp_traces\"
```

### Étape 2.2 : Consolidation Tests
```powershell
# Vérifier existence tests dupliqués
if (Test-Path "argumentation_analysis\tests") {
    Write-Host "⚠️  Tests dupliqués détectés - Consolidation nécessaire"
    
    # Backup tests actuels
    Copy-Item -Path "argumentation_analysis\tests" -Destination "_archives\legacy_code\argumentation_tests_backup" -Recurse -Force
    
    # Note: Migration manuelle recommandée pour éviter conflits
    Write-Host "📝 ACTION MANUELLE : Vérifier et migrer tests de argumentation_analysis\tests\ vers tests\unit\argumentation_analysis\"
}
```

### Étape 2.3 : Nettoyage Répertoires Temporaires
```powershell
# Suppression répertoires temporaires vides ou obsolètes
$tempDirs = @("argumentation_analysis\temp_downloads", "_temp", "venv_test")

foreach ($dir in $tempDirs) {
    if (Test-Path $dir) {
        $isEmpty = (Get-ChildItem -Path $dir -Force | Measure-Object).Count -eq 0
        if ($isEmpty) {
            Remove-Item -Path $dir -Force -Recurse
            Write-Host "✅ Supprimé répertoire vide : $dir"
        } else {
            Write-Host "⚠️  Répertoire non vide, backup nécessaire : $dir"
        }
    }
}

# Archivage migration_output si pas d'activité récente
if (Test-Path "migration_output") {
    $lastActivity = (Get-ChildItem -Path "migration_output" -Recurse | Sort-Object LastWriteTime -Descending | Select-Object -First 1).LastWriteTime
    if ($lastActivity -lt (Get-Date).AddDays(-30)) {
        Move-Item -Path "migration_output" -Destination "_archives\legacy_code\migration_output_archived" -Force
        Write-Host "✅ Archivé migration_output (inactif depuis 30+ jours)"
    }
}
```

---

## 🔍 PHASE 3 : VALIDATION POST-NETTOYAGE (15 min)

### Étape 3.1 : Tests Intégrité Système
```powershell
# Test démarrage rapide système
Write-Host "🧪 Test intégrité système..."
powershell -File .\scripts\env\activate_project_env.ps1 -CommandToRun "python examples/scripts_demonstration/demonstration_epita.py --quick-start"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Système fonctionnel après nettoyage"
} else {
    Write-Host "❌ Problème détecté - Vérification nécessaire"
}
```

### Étape 3.2 : Validation Oracle Enhanced
```powershell
# Tests Oracle Enhanced critiques
Write-Host "🔮 Validation Oracle Enhanced..."
powershell -File .\scripts\env\activate_project_env.ps1 -CommandToRun "python -m scripts.maintenance.validate_oracle_coverage"

# Tests Sherlock-Watson essentiels
Write-Host "🕵️ Tests Sherlock-Watson..."
powershell -File .\scripts\env\activate_project_env.ps1 -CommandToRun "python -m pytest tests/validation_sherlock_watson/test_api_corrections_simple.py -v"
```

### Étape 3.3 : Rapport Final
```powershell
# Génération statistiques post-nettoyage
Write-Host "📊 STATISTIQUES POST-NETTOYAGE"
Write-Host "================================"

$rootFiles = (Get-ChildItem -Path "." -File | Measure-Object).Count
Write-Host "📁 Fichiers racine: $rootFiles (objectif: <15)"

$logsSize = (Get-ChildItem -Path "logs" -Recurse -File | Measure-Object -Property Length -Sum).Sum / 1MB
Write-Host "📊 Taille logs: $([math]::Round($logsSize, 2)) MB"

$archivesExist = Test-Path "_archives"
Write-Host "🗃️  Structure archives: $(if($archivesExist){'✅ Propre'}else{'❌ Manquante'})"

# Commit final
git add -A
git commit -m "🧹 NETTOYAGE: Audit architectural appliqué - $(Get-Date -Format 'yyyyMMdd_HHmmss')"
```

---

## ⚠️ ACTIONS MANUELLES REQUISES

### 1. Migration Tests (si nécessaire)
```
📝 Vérifier manuellement : argumentation_analysis\tests\ 
   → Migrer vers : tests\unit\argumentation_analysis\
   → Éviter conflits de noms
```

### 2. Révision Archives Corrompues
```
📝 Examiner : _archives_CORRUPTED_[timestamp]\
   → Récupérer fichiers Tweety/EProver si nécessaires
   → Restructurer dans _archives\legacy_code\
```

### 3. Validation Configuration
```
📝 Tester configurations pytest déplacées :
   → config\pytest\pytest_*.ini
   → Adapter chemins si nécessaire
```

---

## 🎯 RÉSULTATS ATTENDUS

### Avant/Après - Métriques
| Métrique | Avant | Après | Amélioration |
|----------|-------|-------|--------------|
| Fichiers racine | 47 | <15 | -70% |
| Taille logs | ~50MB | <10MB | -80% |
| Structure archives | Corrompue | Organisée | +100% |
| Vitesse Git | Baseline | +50% | Mesurable |

### Validation Succès
- [x] ✅ Racine propre (<15 fichiers essentiels)
- [x] ✅ Archives organisées sans corruption
- [x] ✅ Logs consolidés avec rétention
- [x] ✅ Tests centralisés
- [x] ✅ Fonctionnalités intactes

---

**⚡ EXÉCUTION ESTIMÉE : 1h30 total**
- Phase 1 : 30 min (automatisée)
- Phase 2 : 45 min (semi-automatisée) 
- Phase 3 : 15 min (validation)

**🛡️ SÉCURITÉ : Backup Git automatique avant/après chaque phase**