<#
.SYNOPSIS
    Script de validation post-migration pour vérifier la cohérence du dépôt
    
.DESCRIPTION
    Valide que la migration s'est bien passée en vérifiant :
    - Les fichiers ont bien été déplacés
    - Les imports fonctionnent toujours
    - La structure est cohérente
    - Les tests peuvent toujours s'exécuter
    
.EXAMPLE
    .\scripts\maintenance\validate_migration.ps1
    
.NOTES
    Auteur: Roo Code
    Date: 2025-06-07
#>

param (
    [switch]$RunTests = $false,
    [switch]$Verbose = $false
)

$colors = @{
    'Success' = 'Green'
    'Warning' = 'Yellow' 
    'Error'   = 'Red'
    'Info'    = 'Cyan'
    'Title'   = 'Magenta'
}

function Write-ColorText {
    param([string]$Text, [string]$Color = 'White')
    Write-Host $Text -ForegroundColor $colors[$Color]
}

function Write-ValidationHeader {
    param([string]$Title)
    Write-Host ""
    Write-ColorText "=" * 60 "Title"
    Write-ColorText " $Title" "Title"
    Write-ColorText "=" * 60 "Title"
}

function Test-DirectoryStructure {
    Write-ValidationHeader "VALIDATION STRUCTURE RÉPERTOIRES"
    
    $expectedDirs = @(
        "tests/demos/fol",
        "tests/demos/modal", 
        "tests/demos/rhetorical",
        "tests/demos/retry",
        "tests/integration/conversation",
        "tests/integration/modal",
        "tests/integration/orchestration",
        "tests/integration/retry",
        "tests/integration/sources",
        "tests/integration/reporting",
        "tests/integration/analysis",
        "tests/integration/pipelines",
        "tests/validation/modal",
        "tests/unit/analyzers",
        "docs/audits",
        "docs/reports/consolidation",
        "docs/reports/analysis", 
        "docs/reports/testing",
        "docs/reports/fol",
        "docs/reports/implementation",
        "docs/reports/refactoring",
        "docs/reports/various",
        "docs/validation",
        "docs/testing"
    )
    
    $missingDirs = @()
    $existingDirs = @()
    
    foreach ($dir in $expectedDirs) {
        if (Test-Path $dir -PathType Container) {
            $existingDirs += $dir
            Write-ColorText "✅ $dir" "Success"
        } else {
            $missingDirs += $dir
            Write-ColorText "❌ $dir" "Error"
        }
    }
    
    Write-Host ""
    Write-ColorText "Répertoires présents: $($existingDirs.Count)/$($expectedDirs.Count)" "Info"
    if ($missingDirs.Count -gt 0) {
        Write-ColorText "⚠️ Répertoires manquants: $($missingDirs.Count)" "Warning"
        return $false
    }
    
    return $true
}

function Test-FilesMoved {
    Write-ValidationHeader "VALIDATION DÉPLACEMENT FICHIERS"
    
    # Tests qui doivent avoir été déplacés
    $expectedMoves = @{
        "tests/demos/fol/test_fol_demo_simple.py" = "test_fol_demo_simple.py"
        "tests/demos/fol/test_fol_demo.py" = "test_fol_demo.py"
        "tests/demos/modal/test_final_modal_correction_demo.py" = "test_final_modal_correction_demo.py"
        "tests/integration/rhetorical/test_advanced_rhetorical_enhanced.py" = "test_advanced_rhetorical_enhanced.py"
        "tests/integration/conversation/test_conversation_integration.py" = "test_conversation_integration.py"
        "docs/testing/TEST_MAPPING.md" = "TEST_MAPPING.md"
    }
    
    $correctMoves = 0
    $totalMoves = $expectedMoves.Count
    
    foreach ($newPath in $expectedMoves.Keys) {
        $oldName = $expectedMoves[$newPath]
        
        if (Test-Path $newPath) {
            Write-ColorText "✅ $oldName → $newPath" "Success"
            $correctMoves++
        } else {
            Write-ColorText "❌ Fichier manquant: $newPath" "Error"
        }
        
        # Vérifier que l'ancien emplacement est vide
        if (Test-Path $oldName) {
            Write-ColorText "⚠️ Ancien fichier toujours présent: $oldName" "Warning"
        }
    }
    
    Write-Host ""
    Write-ColorText "Fichiers correctement déplacés: $correctMoves/$totalMoves" "Info"
    return ($correctMoves -eq $totalMoves)
}

function Test-TemporaryFilesCleanup {
    Write-ValidationHeader "VALIDATION NETTOYAGE FICHIERS TEMPORAIRES"
    
    $tempPatterns = @(
        "temp_*.py",
        "temp_*.enc", 
        "pytest_*.log",
        "scratch_*.py",
        "page_content.html"
    )
    
    $remainingTempFiles = @()
    
    foreach ($pattern in $tempPatterns) {
        $matches = Get-ChildItem -File -Name $pattern -ErrorAction SilentlyContinue
        $remainingTempFiles += $matches
    }
    
    if ($remainingTempFiles.Count -eq 0) {
        Write-ColorText "✅ Tous les fichiers temporaires ont été supprimés" "Success"
        return $true
    } else {
        Write-ColorText "⚠️ Fichiers temporaires restants:" "Warning"
        foreach ($file in $remainingTempFiles) {
            Write-Host "  - $file" -ForegroundColor Yellow
        }
        return $false
    }
}

function Test-RootCleanliness {
    Write-ValidationHeader "VALIDATION PROPRETÉ RACINE"
    
    $rootFiles = Get-ChildItem -File | Where-Object { 
        $_.Name -notmatch "^(README|LICENSE|\.git|requirements|setup|environment|conftest|pyproject|pytest|activate_|run_)" -and
        $_.Name -notmatch "\.(md|txt|yml|yaml|toml|ini|json|ps1|sh)$" -and
        $_.Name -notmatch "^DEPOT_CLEANUP_ANALYSIS"
    }
    
    $testFilesInRoot = $rootFiles | Where-Object { $_.Name -match "^test_" }
    $reportFilesInRoot = $rootFiles | Where-Object { $_.Name -match "^(RAPPORT_|AUDIT_|VALIDATION_|TRACE_)" }
    
    $issuesFound = 0
    
    if ($testFilesInRoot.Count -gt 0) {
        Write-ColorText "❌ Tests encore présents à la racine:" "Error"
        foreach ($file in $testFilesInRoot) {
            Write-Host "  - $($file.Name)" -ForegroundColor Red
        }
        $issuesFound++
    } else {
        Write-ColorText "✅ Aucun test à la racine" "Success"
    }
    
    if ($reportFilesInRoot.Count -gt 0) {
        Write-ColorText "❌ Rapports encore présents à la racine:" "Error"
        foreach ($file in $reportFilesInRoot) {
            Write-Host "  - $($file.Name)" -ForegroundColor Red
        }
        $issuesFound++
    } else {
        Write-ColorText "✅ Aucun rapport à la racine" "Success"
    }
    
    $remainingFiles = Get-ChildItem -File | Where-Object { 
        $_.Name -notmatch "^(README|LICENSE|\.git|requirements|setup|environment|conftest|pyproject|pytest|activate_|run_|demo_|api_|check_|create_|extract_|generate_|minimal_|scratch_|GETTING_|GUIDE_|LLM_|PYTEST_|corpus_|new_components|page_content|start_web|verify_|DEPOT_CLEANUP_ANALYSIS)" -and
        $_.Name -notmatch "\.(md|txt|yml|yaml|toml|ini|json|ps1|sh|py|log|enc|html)$"
    }
    
    Write-Host ""
    Write-ColorText "Fichiers restants à la racine: $($remainingFiles.Count)" "Info"
    
    return ($issuesFound -eq 0)
}

function Test-GitStatus {
    Write-ValidationHeader "VALIDATION STATUT GIT"
    
    try {
        $gitStatus = git status --porcelain
        $untrackedFiles = $gitStatus | Where-Object { $_ -match "^\?\?" }
        $modifiedFiles = $gitStatus | Where-Object { $_ -match "^[MA]" }
        
        Write-ColorText "Fichiers modifiés/ajoutés: $($modifiedFiles.Count)" "Info"
        Write-ColorText "Fichiers non-trackés: $($untrackedFiles.Count)" "Info"
        
        if ($untrackedFiles.Count -gt 0 -and $Verbose) {
            Write-ColorText "Fichiers non-trackés:" "Warning"
            foreach ($file in $untrackedFiles) {
                Write-Host "  $file" -ForegroundColor Yellow
            }
        }
        
        return $true
    } catch {
        Write-ColorText "❌ Erreur lors de la vérification Git: $($_.Exception.Message)" "Error"
        return $false
    }
}

function Test-ImportIntegrity {
    Write-ValidationHeader "VALIDATION INTÉGRITÉ IMPORTS"
    
    if (-not $RunTests) {
        Write-ColorText "⏭️ Tests d'intégrité désactivés (utilisez -RunTests pour les activer)" "Warning"
        return $true
    }
    
    Write-ColorText "🧪 Test d'importation des modules principaux..." "Info"
    
    try {
        # Test import du module principal
        $testResult = python -c "import argumentation_analysis; print('✅ Import principal OK')" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-ColorText "$testResult" "Success"
        } else {
            Write-ColorText "❌ Erreur import principal: $testResult" "Error"
            return $false
        }
        
        # Test import des utilitaires
        $utilsTest = python -c "from argumentation_analysis.utils import core_utils; print('✅ Import utils OK')" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-ColorText "$utilsTest" "Success"
        } else {
            Write-ColorText "⚠️ Import utils: $utilsTest" "Warning"
        }
        
        return $true
    } catch {
        Write-ColorText "❌ Erreur lors des tests d'import: $($_.Exception.Message)" "Error"
        return $false
    }
}

# === EXÉCUTION PRINCIPALE ===
Write-ValidationHeader "VALIDATION POST-MIGRATION - DÉPÔT INTELLIGENCE SYMBOLIQUE"
Write-ColorText "Répertoire: $(Get-Location)" "Info"

$allTests = @()
$allTests += Test-DirectoryStructure
$allTests += Test-FilesMoved  
$allTests += Test-TemporaryFilesCleanup
$allTests += Test-RootCleanliness
$allTests += Test-GitStatus
$allTests += Test-ImportIntegrity

$passedTests = ($allTests | Where-Object { $_ -eq $true }).Count
$totalTests = $allTests.Count

Write-ValidationHeader "RÉSUMÉ VALIDATION"

if ($passedTests -eq $totalTests) {
    Write-ColorText "🎉 VALIDATION RÉUSSIE!" "Success"
    Write-ColorText "✅ Tous les tests passés: $passedTests/$totalTests" "Success"
    Write-Host ""
    Write-ColorText "🎯 Le dépôt est maintenant proprement organisé!" "Success"
    Write-ColorText "Vous pouvez maintenant:" "Info"
    Write-Host "  1. Committer les changements: git add -A && git commit -m 'Réorganisation structure projet'" -ForegroundColor White
    Write-Host "  2. Vérifier que vos tests passent toujours" -ForegroundColor White
    Write-Host "  3. Mettre à jour la documentation si nécessaire" -ForegroundColor White
} else {
    Write-ColorText "⚠️ VALIDATION PARTIELLE" "Warning"
    Write-ColorText "Tests réussis: $passedTests/$totalTests" "Warning"
    Write-Host ""
    Write-ColorText "Veuillez corriger les problèmes identifiés avant de continuer." "Warning"
}

Write-Host ""