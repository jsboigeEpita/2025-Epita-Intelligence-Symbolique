<#
.SYNOPSIS
    Script de nettoyage du depot Git Intelligence Symbolique (version compatible PowerShell)
    
.PARAMETER Mode
    preview : Affiche ce qui va etre fait
    execute : Execute les modifications  
    cleanup-only : Nettoie uniquement les temporaires
#>

param (
    [Parameter(Mandatory=$true)]
    [ValidateSet("preview", "execute", "cleanup-only")]
    [string]$Mode,
    
    [bool]$CreateBackup = $true
)

function Write-ColorText {
    param([string]$Text, [string]$Color = 'White')
    $colorMap = @{
        'Success' = 'Green'; 'Error' = 'Red'; 'Warning' = 'Yellow'; 'Info' = 'Cyan'; 'Action' = 'Magenta'
    }
    Write-Host $Text -ForegroundColor $colorMap[$Color]
}

function Write-Header {
    param([string]$Title)
    Write-Host ""
    Write-Host ("=" * 60) -ForegroundColor Green
    Write-Host " $Title" -ForegroundColor Green  
    Write-Host ("=" * 60) -ForegroundColor Green
    Write-Host ""
}

# Verification repertoire
if (-not (Test-Path "argumentation_analysis" -PathType Container)) {
    Write-ColorText "ERREUR: Executer depuis la racine du projet" "Error"
    exit 1
}

Write-Header "DEPOT CLEANUP - Intelligence Symbolique"
Write-ColorText "Mode: $Mode" "Info"

# === DEFINITIONS ===
$testsToMove = @(
    @{ Source = "test_advanced_rhetorical_enhanced.py"; Dest = "tests/integration/rhetorical/" },
    @{ Source = "test_conversation_integration.py"; Dest = "tests/integration/conversation/" },
    @{ Source = "test_final_modal_correction_demo.py"; Dest = "tests/demos/modal/" },
    @{ Source = "test_fol_demo_simple.py"; Dest = "tests/demos/fol/" },
    @{ Source = "test_fol_demo.py"; Dest = "tests/demos/fol/" },
    @{ Source = "test_intelligent_modal_correction.py"; Dest = "tests/integration/modal/" },
    @{ Source = "test_micro_orchestration.py"; Dest = "tests/integration/orchestration/" },
    @{ Source = "test_modal_correction_validation.py"; Dest = "tests/validation/modal/" },
    @{ Source = "test_modal_retry_mechanism.py"; Dest = "tests/integration/retry/" },
    @{ Source = "test_rhetorical_demo_integration.py"; Dest = "tests/demos/rhetorical/" },
    @{ Source = "test_simple_unified_pipeline.py"; Dest = "tests/integration/pipelines/" },
    @{ Source = "test_sk_retry_demo.py"; Dest = "tests/demos/retry/" },
    @{ Source = "test_source_management_integration.py"; Dest = "tests/integration/sources/" },
    @{ Source = "test_trace_analyzer_conversation_format.py"; Dest = "tests/unit/analyzers/" },
    @{ Source = "test_unified_report_generation_integration.py"; Dest = "tests/integration/reporting/" },
    @{ Source = "test_unified_text_analysis_integration.py"; Dest = "tests/integration/analysis/" },
    @{ Source = "TEST_MAPPING.md"; Dest = "docs/testing/" }
)

$reportsToMove = @(
    @{ Source = "AUDIT_AUTHENTICITE_FOL_COMPLETE.md"; Dest = "docs/audits/" },
    @{ Source = "AUDIT_REFACTORISATION_ORCHESTRATION.md"; Dest = "docs/audits/" },
    @{ Source = "CONSOLIDATION_ORCHESTRATION_REUSSIE.md"; Dest = "docs/reports/consolidation/" },
    @{ Source = "RAPPORT_ANALYSE_CORRECTION_BNF_INTELLIGENTE.md"; Dest = "docs/reports/analysis/" },
    @{ Source = "RAPPORT_EVALUATION_TESTS_SYSTEME.md"; Dest = "docs/reports/testing/" },
    @{ Source = "RAPPORT_FINAL_FOL_AUTHENTIQUE.md"; Dest = "docs/reports/fol/" },
    @{ Source = "SYNTHESE_FINALE_REFACTORISATION_UNIFIED_REPORTS.md"; Dest = "docs/reports/refactoring/" },
    @{ Source = "VALIDATION_ECOSYSTEM_FINALE.md"; Dest = "docs/validation/" }
)

# Ajouter autres rapports detectes
$additionalReports = Get-ChildItem -File | Where-Object { 
    $_.Name -match "^(RAPPORT_|TRACE_|VALIDATION_|rapport_)" -and 
    $_.Name -notmatch "^(DEPOT_CLEANUP_ANALYSIS|README)" 
} | ForEach-Object {
    @{ Source = $_.Name; Dest = "docs/reports/various/" }
}
$reportsToMove += $additionalReports

$tempFiles = @("temp_original_file.enc", "page_content.html", "scratch_tweety_interactions.py", 
               "pytest_full_output.log", "pytest_prop_logic_*.log", "pytest_all_tests_*.log",
               "pytest_output*.log", "setup_global_output.log", "extract_agent.log", "temp_*.py")

$dirsToCreate = @(
    "tests/demos/fol", "tests/demos/modal", "tests/demos/rhetorical", "tests/demos/retry",
    "tests/integration/conversation", "tests/integration/modal", "tests/integration/orchestration",
    "tests/integration/retry", "tests/integration/sources", "tests/integration/reporting",
    "tests/integration/analysis", "tests/integration/pipelines", "tests/validation/modal",
    "tests/unit/analyzers", "docs/audits", "docs/reports/consolidation", "docs/reports/analysis",
    "docs/reports/testing", "docs/reports/fol", "docs/reports/implementation", 
    "docs/reports/refactoring", "docs/reports/various", "docs/validation", "docs/testing"
)

# === PREVIEW MODE ===
if ($Mode -eq "preview") {
    Write-Header "PREVIEW - ACTIONS PREVUES"
    
    Write-ColorText "[REPERTOIRES] Creation de nouveaux repertoires" "Info"
    foreach ($dir in $dirsToCreate) {
        if (-not (Test-Path $dir)) {
            Write-Host "  [CREER] $dir" -ForegroundColor Yellow
        }
    }
    
    Write-ColorText "[TESTS] Deplacement des tests ($($testsToMove.Count) fichiers)" "Info"
    foreach ($test in $testsToMove) {
        if (Test-Path $test.Source) {
            $size = [math]::Round((Get-Item $test.Source).Length / 1KB, 1)
            Write-Host "  [DEPLACER] $($test.Source) -> $($test.Dest) (${size}KB)" -ForegroundColor Cyan
        }
    }
    
    Write-ColorText "[RAPPORTS] Deplacement des rapports ($($reportsToMove.Count) fichiers)" "Info"
    foreach ($report in $reportsToMove) {
        if (Test-Path $report.Source) {
            $size = [math]::Round((Get-Item $report.Source).Length / 1KB, 1)
            Write-Host "  [DEPLACER] $($report.Source) -> $($report.Dest) (${size}KB)" -ForegroundColor Cyan
        }
    }
    
    Write-ColorText "[CLEANUP] Suppression fichiers temporaires" "Info"
    $actualTempFiles = @()
    foreach ($pattern in $tempFiles) {
        $matches = Get-ChildItem -File -Name $pattern -ErrorAction SilentlyContinue
        $actualTempFiles += $matches
    }
    foreach ($tempFile in $actualTempFiles) {
        if (Test-Path $tempFile) {
            $size = [math]::Round((Get-Item $tempFile).Length / 1KB, 1)
            Write-Host "  [SUPPRIMER] $tempFile (${size}KB)" -ForegroundColor Red
        }
    }
    
    Write-Header "RESUME PREVIEW"
    Write-ColorText "Tests a deplacer: $($testsToMove.Count)" "Info"
    Write-ColorText "Rapports a deplacer: $($reportsToMove.Count)" "Info"
    Write-ColorText "Fichiers temporaires: $($actualTempFiles.Count)" "Info"
    Write-ColorText "Repertoires a creer: $($dirsToCreate.Count)" "Info"
    Write-Host ""
    Write-ColorText "Pour executer:" "Action"
    Write-Host "  .\scripts\maintenance\depot_cleanup_migration_simple.ps1 -Mode execute"
    exit 0
}

# === EXECUTE MODE ===
if ($Mode -eq "execute") {
    Write-Header "EXECUTION - MIGRATION"
    
    if ($CreateBackup) {
        $backupBranch = "backup-cleanup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
        Write-ColorText "Creation sauvegarde: $backupBranch" "Info"
        try {
            git checkout -b $backupBranch
            git add -A
            git commit -m "Sauvegarde avant nettoyage automatique"
            git checkout -
            Write-ColorText "[OK] Sauvegarde creee" "Success"
        } catch {
            Write-ColorText "[ERREUR] Sauvegarde: $($_.Exception.Message)" "Error"
            exit 1
        }
    }
    
    $successCount = 0
    $errorCount = 0
    
    # Creation repertoires
    Write-ColorText "[REPERTOIRES] Creation..." "Info"
    foreach ($dir in $dirsToCreate) {
        if (-not (Test-Path $dir)) {
            try {
                New-Item -ItemType Directory -Path $dir -Force | Out-Null
                Write-ColorText "[OK] Cree: $dir" "Success"
                $successCount++
            } catch {
                Write-ColorText "[ERREUR] $dir : $($_.Exception.Message)" "Error"
                $errorCount++
            }
        }
    }
    
    # Deplacement tests
    Write-ColorText "[TESTS] Deplacement..." "Info"
    foreach ($test in $testsToMove) {
        if (Test-Path $test.Source) {
            try {
                $destFile = Join-Path $test.Dest (Split-Path $test.Source -Leaf)
                Move-Item $test.Source $destFile -Force
                Write-ColorText "[OK] $($test.Source) -> $destFile" "Success"
                $successCount++
            } catch {
                Write-ColorText "[ERREUR] $($test.Source): $($_.Exception.Message)" "Error"
                $errorCount++
            }
        }
    }
    
    # Deplacement rapports
    Write-ColorText "[RAPPORTS] Deplacement..." "Info"
    foreach ($report in $reportsToMove) {
        if (Test-Path $report.Source) {
            try {
                $destFile = Join-Path $report.Dest (Split-Path $report.Source -Leaf)
                Move-Item $report.Source $destFile -Force
                Write-ColorText "[OK] $($report.Source) -> $destFile" "Success"
                $successCount++
            } catch {
                Write-ColorText "[ERREUR] $($report.Source): $($_.Exception.Message)" "Error"
                $errorCount++
            }
        }
    }
    
    # Suppression temporaires
    Write-ColorText "[CLEANUP] Suppression..." "Info"
    foreach ($pattern in $tempFiles) {
        $matches = Get-ChildItem -File -Name $pattern -ErrorAction SilentlyContinue
        foreach ($tempFile in $matches) {
            try {
                Remove-Item $tempFile -Force
                Write-ColorText "[OK] Supprime: $tempFile" "Success"
                $successCount++
            } catch {
                Write-ColorText "[ERREUR] ${tempFile}: $($_.Exception.Message)" "Error"
                $errorCount++
            }
        }
    }
    
    Write-Header "RESUME EXECUTION"
    Write-ColorText "[OK] Operations reussies: $successCount" "Success"
    if ($errorCount -gt 0) {
        Write-ColorText "[ERREUR] Erreurs: $errorCount" "Error"
    }
    
    Write-ColorText "[ACTION] Prochaines etapes:" "Action"
    Write-Host "  1. git status"
    Write-Host "  2. Tester les imports"
    Write-Host "  3. git add -A && git commit -m 'Reorganisation structure'"
}

# === CLEANUP-ONLY ===
if ($Mode -eq "cleanup-only") {
    Write-Header "NETTOYAGE TEMPORAIRES UNIQUEMENT"
    
    $cleanupCount = 0
    foreach ($pattern in $tempFiles) {
        $matches = Get-ChildItem -File -Name $pattern -ErrorAction SilentlyContinue
        foreach ($tempFile in $matches) {
            if (Test-Path $tempFile) {
                try {
                    $size = [math]::Round((Get-Item $tempFile).Length / 1KB, 1)
                    Remove-Item $tempFile -Force
                    Write-ColorText "[OK] Supprime: $tempFile (${size}KB)" "Success"
                    $cleanupCount++
                } catch {
                    Write-ColorText "[ERREUR] ${tempFile}: $($_.Exception.Message)" "Error"
                }
            }
        }
    }
    
    Write-ColorText "[OK] $cleanupCount fichiers temporaires supprimes" "Success"
}

Write-ColorText "Script termine." "Info"