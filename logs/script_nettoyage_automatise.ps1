# SCRIPT DE NETTOYAGE AUTOMATISÉ - 2025-Epita-Intelligence-Symbolique
# Date: 09/06/2025
# Objectif: Automatiser le nettoyage des répertoires encombrés

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("phase1", "phase2", "phase3", "all", "dry-run")]
    [string]$Action = "dry-run",
    
    [Parameter(Mandatory=$false)]
    [switch]$Force = $false
)

Write-Host "=== SCRIPT DE NETTOYAGE AUTOMATISÉ ===" -ForegroundColor Cyan
Write-Host "Action demandée: $Action" -ForegroundColor Yellow

# Fonction pour créer les répertoires cibles
function Create-TargetDirectories {
    Write-Host "`n[INFO] Création des répertoires cibles..." -ForegroundColor Green
    
    $directories = @(
        "tests/legacy_root_tests",
        "examples/demo_orphelins", 
        "scripts/validation/legacy",
        "tests/unit/argumentation_analysis/agents",
        "tests/unit/argumentation_analysis/core",
        "tests/unit/argumentation_analysis/utils",
        "tests/unit/argumentation_analysis/archived",
        "scripts/maintenance/active",
        "scripts/maintenance/archived",
        "scripts/setup/core",
        "scripts/setup/environments", 
        "scripts/setup/optional",
        "examples/archived_demos"
    )
    
    foreach ($dir in $directories) {
        if (-not (Test-Path $dir)) {
            if ($Action -ne "dry-run") {
                New-Item -ItemType Directory -Path $dir -Force
                Write-Host "✓ Créé: $dir" -ForegroundColor Green
            } else {
                Write-Host "□ À créer: $dir" -ForegroundColor Yellow
            }
        } else {
            Write-Host "✓ Existe: $dir" -ForegroundColor Gray
        }
    }
}

# PHASE 1: Déplacement des orphelins
function Execute-Phase1 {
    Write-Host "`n=== PHASE 1: DÉPLACEMENT DES ORPHELINS ===" -ForegroundColor Cyan
    
    # Tests orphelins → tests/legacy_root_tests/
    $testOrphelins = @(
        "test_integration_robust.py",
        "test_real_vs_mock_system_analysis.py", 
        "test_sherlock_watson_edge_cases_specialized.py",
        "test_sherlock_watson_synthetic_validation.py"
    )
    
    Write-Host "`n[TESTS] Déplacement vers tests/legacy_root_tests/" -ForegroundColor Green
    foreach ($file in $testOrphelins) {
        if (Test-Path $file) {
            if ($Action -ne "dry-run") {
                Move-Item $file "tests/legacy_root_tests/" -Force
                Write-Host "✓ Déplacé: $file" -ForegroundColor Green
            } else {
                Write-Host "□ À déplacer: $file" -ForegroundColor Yellow
            }
        }
    }
    
    # Demos orphelins → examples/demo_orphelins/
    $demoOrphelins = @(
        "backend_mock_demo.py",
        "demo_authentic_system.py",
        "demo_playwright_complet.py",
        "demo_playwright_robuste.py", 
        "demo_playwright_simple.py",
        "demo_real_sk_orchestration.py",
        "demo_real_sk_orchestration_fixed.py",
        "demo_retry_fix.py"
    )
    
    Write-Host "`n[DEMOS] Déplacement vers examples/demo_orphelins/" -ForegroundColor Green
    foreach ($file in $demoOrphelins) {
        if (Test-Path $file) {
            if ($Action -ne "dry-run") {
                Move-Item $file "examples/demo_orphelins/" -Force
                Write-Host "✓ Déplacé: $file" -ForegroundColor Green
            } else {
                Write-Host "□ À déplacer: $file" -ForegroundColor Yellow
            }
        }
    }
    
    # Validations orphelines → scripts/validation/legacy/
    $validationOrphelins = @(
        "audit_validation_exhaustive.py",
        "demo_system_rhetorical.py",
        "demo_validation_results_sherlock_watson.py",
        "generate_final_validation_report.py",
        "generate_validation_report.py", 
        "VALIDATION_MIGRATION_IMMEDIATE.py",
        "validation_migration_phase_2b.py",
        "validation_migration_simple.py"
    )
    
    Write-Host "`n[VALIDATIONS] Déplacement vers scripts/validation/legacy/" -ForegroundColor Green
    foreach ($file in $validationOrphelins) {
        if (Test-Path $file) {
            if ($Action -ne "dry-run") {
                Move-Item $file "scripts/validation/legacy/" -Force
                Write-Host "✓ Déplacé: $file" -ForegroundColor Green
            } else {
                Write-Host "□ À déplacer: $file" -ForegroundColor Yellow
            }
        }
    }
}

# PHASE 2: Nettoyage __pycache__ et fichiers temporaires
function Execute-Phase2 {
    Write-Host "`n=== PHASE 2: NETTOYAGE FICHIERS TEMPORAIRES ===" -ForegroundColor Cyan
    
    # Suppression __pycache__
    $pycacheDirectories = Get-ChildItem -Path . -Recurse -Directory -Name "__pycache__"
    foreach ($dir in $pycacheDirectories) {
        if ($Action -ne "dry-run") {
            Remove-Item $dir -Recurse -Force
            Write-Host "✓ Supprimé: $dir" -ForegroundColor Green
        } else {
            Write-Host "□ À supprimer: $dir" -ForegroundColor Yellow
        }
    }
    
    # Suppression fichiers .pyc
    $pycFiles = Get-ChildItem -Path . -Recurse -Filter "*.pyc"
    foreach ($file in $pycFiles) {
        if ($Action -ne "dry-run") {
            Remove-Item $file -Force
            Write-Host "✓ Supprimé: $($file.FullName)" -ForegroundColor Green
        } else {
            Write-Host "□ À supprimer: $($file.FullName)" -ForegroundColor Yellow
        }
    }
}

# PHASE 3: Audit des doublons
function Execute-Phase3 {
    Write-Host "`n=== PHASE 3: AUDIT DES DOUBLONS ===" -ForegroundColor Cyan
    
    Write-Host "`n[AUDIT] Comparaison scripts/demo/ vs examples/scripts_demonstration/" -ForegroundColor Green
    if (Test-Path "scripts/demo") {
        $scriptsDemos = Get-ChildItem -Path "scripts/demo" -Filter "*.py" | Select-Object -ExpandProperty Name
        $examplesDemos = Get-ChildItem -Path "examples/scripts_demonstration" -Filter "*.py" | Select-Object -ExpandProperty Name
        
        $commonFiles = Compare-Object $scriptsDemos $examplesDemos -IncludeEqual | Where-Object { $_.SideIndicator -eq "==" }
        
        if ($commonFiles) {
            Write-Host "⚠️ Fichiers potentiellement dupliqués:" -ForegroundColor Red
            foreach ($file in $commonFiles) {
                Write-Host "  - $($file.InputObject)" -ForegroundColor Yellow
            }
        } else {
            Write-Host "✓ Aucun doublon détecté entre scripts/demo/ et examples/scripts_demonstration/" -ForegroundColor Green
        }
    }
}

# Génération du rapport final
function Generate-CleanupReport {
    $reportPath = "logs/rapport_nettoyage_execution_$(Get-Date -Format 'yyyyMMdd_HHmmss').md"
    
    $report = @"
# RAPPORT D'EXÉCUTION DU NETTOYAGE
**Date d'exécution :** $(Get-Date -Format 'dd/MM/yyyy HH:mm:ss')
**Action exécutée :** $Action
**Mode Force :** $Force

## Actions réalisées
- Phase 1: Déplacement des orphelins
- Phase 2: Nettoyage fichiers temporaires  
- Phase 3: Audit des doublons

## Statistiques
- Fichiers déplacés: [À compléter]
- Répertoires créés: [À compléter]
- Espace récupéré: [À compléter]

## Prochaines étapes recommandées
1. Vérifier l'intégrité des tests après déplacement
2. Mettre à jour les imports si nécessaire
3. Valider que les scripts fonctionnent depuis leur nouvelle location
4. Commit des changements avec message descriptif
"@

    if ($Action -ne "dry-run") {
        $report | Out-File -FilePath $reportPath -Encoding UTF8
        Write-Host "`n✓ Rapport généré: $reportPath" -ForegroundColor Green
    } else {
        Write-Host "`n□ Rapport serait généré: $reportPath" -ForegroundColor Yellow
    }
}

# Exécution principale
switch ($Action) {
    "phase1" {
        Create-TargetDirectories
        Execute-Phase1
        Generate-CleanupReport
    }
    "phase2" {
        Execute-Phase2
        Generate-CleanupReport
    }
    "phase3" {
        Execute-Phase3
        Generate-CleanupReport
    }
    "all" {
        Create-TargetDirectories
        Execute-Phase1
        Execute-Phase2
        Execute-Phase3
        Generate-CleanupReport
    }
    "dry-run" {
        Write-Host "`n[DRY-RUN] Simulation des actions sans modification" -ForegroundColor Magenta
        Create-TargetDirectories
        Execute-Phase1
        Execute-Phase2
        Execute-Phase3
        Write-Host "`n[DRY-RUN] Pour exécuter réellement, utilisez -Action 'all' ou spécifiez une phase" -ForegroundColor Magenta
    }
}

Write-Host "`n=== NETTOYAGE TERMINÉ ===" -ForegroundColor Cyan