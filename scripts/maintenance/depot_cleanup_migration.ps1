<#
.SYNOPSIS
    Script de nettoyage et réorganisation du dépôt Git Intelligence Symbolique
    
.DESCRIPTION
    Ce script réorganise automatiquement :
    - Déplace les tests de la racine vers tests/
    - Réorganise les rapports vers docs/
    - Nettoie les fichiers temporaires
    - Sauvegarde avant modifications
    
.PARAMETER Mode
    preview : Affiche ce qui va être fait sans modifier
    execute : Exécute les modifications
    cleanup-only : Nettoie uniquement les fichiers temporaires
    
.PARAMETER CreateBackup
    Crée une branche de sauvegarde Git avant modifications (défaut: true)
    
.EXAMPLE
    .\scripts\maintenance\depot_cleanup_migration.ps1 -Mode preview
    .\scripts\maintenance\depot_cleanup_migration.ps1 -Mode execute -CreateBackup $true
    
.NOTES
    Auteur: Roo Code - Analyse Intelligence Symbolique
    Date: 2025-06-07
    Version: 1.0
#>

param (
    [Parameter(Mandatory=$true)]
    [ValidateSet("preview", "execute", "cleanup-only")]
    [string]$Mode,
    
    [bool]$CreateBackup = $true,
    
    [switch]$Verbose
)

# Configuration des couleurs pour l'affichage
$colors = @{
    'Title'   = 'Green'
    'Success' = 'Green' 
    'Warning' = 'Yellow'
    'Error'   = 'Red'
    'Info'    = 'Cyan'
    'Action'  = 'Magenta'
}

function Write-ColorText {
    param([string]$Text, [string]$Color = 'White')
    Write-Host $Text -ForegroundColor $colors[$Color]
}

function Write-Header {
    param([string]$Title)
    Write-Host ""
    Write-ColorText "=" * 80 "Title"
    Write-ColorText " $Title" "Title"
    Write-ColorText "=" * 80 "Title"
    Write-Host ""
}

function Show-FileAction {
    param(
        [string]$Action,
        [string]$Source, 
        [string]$Destination = "",
        [string]$Size = "",
        [string]$Reason = ""
    )
    
    $actionColor = switch ($Action) {
        "SUPPRIMER" { "Error" }
        "DÉPLACER"  { "Action" }
        "CRÉER"     { "Success" }
        default     { "Info" }
    }
    
    Write-ColorText "[$Action]" $actionColor
    Write-Host "  Source: $Source" -ForegroundColor White
    if ($Destination) {
        Write-Host "  Destination: $Destination" -ForegroundColor Gray
    }
    if ($Size) {
        Write-Host "  Taille: $Size" -ForegroundColor Gray
    }
    if ($Reason) {
        Write-Host "  Raison: $Reason" -ForegroundColor Gray
    }
    Write-Host ""
}

# Vérification que nous sommes dans le bon répertoire
$currentPath = Get-Location
if (-not (Test-Path "argumentation_analysis" -PathType Container)) {
    Write-ColorText "ERREUR: Ce script doit être exécuté depuis la racine du projet (doit contenir argumentation_analysis/)" "Error"
    exit 1
}

Write-Header "DEPOT CLEANUP MIGRATION - Intelligence Symbolique"
Write-ColorText "Mode: $Mode" "Info"
Write-ColorText "Répertoire: $currentPath" "Info"

# === INITIALISATION ET SAUVEGARDE ===
if ($Mode -eq "execute" -and $CreateBackup) {
    Write-Header "CRÉATION SAUVEGARDE GIT"
    
    $backupBranch = "backup-cleanup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    Write-ColorText "Création de la branche de sauvegarde: $backupBranch" "Info"
    
    if ($Mode -eq "execute") {
        try {
            git checkout -b $backupBranch
            git add -A
            git commit -m "Sauvegarde avant nettoyage automatique du dépôt"
            git checkout -
            Write-ColorText "✅ Sauvegarde créée avec succès!" "Success"
        } catch {
            Write-ColorText "❌ Erreur lors de la sauvegarde: $($_.Exception.Message)" "Error"
            exit 1
        }
    }
}

# === DÉFINITION DES FICHIERS À TRAITER ===

# Tests éparpillés à la racine
$testsToMove = @(
    @{ Source = "test_advanced_rhetorical_enhanced.py"; Dest = "tests/integration/rhetorical/"; Reason = "Test d'intégration rhétorique" },
    @{ Source = "test_conversation_integration.py"; Dest = "tests/integration/conversation/"; Reason = "Test d'intégration conversation" },
    @{ Source = "test_final_modal_correction_demo.py"; Dest = "tests/demos/modal/"; Reason = "Démo de correction modale" },
    @{ Source = "test_fol_demo_simple.py"; Dest = "tests/demos/fol/"; Reason = "Démo FOL simple" },
    @{ Source = "test_fol_demo.py"; Dest = "tests/demos/fol/"; Reason = "Démo FOL" },
    @{ Source = "test_intelligent_modal_correction.py"; Dest = "tests/integration/modal/"; Reason = "Test correction modale intelligente" },
    @{ Source = "test_micro_orchestration.py"; Dest = "tests/integration/orchestration/"; Reason = "Test micro-orchestration" },
    @{ Source = "test_modal_correction_validation.py"; Dest = "tests/validation/modal/"; Reason = "Validation correction modale" },
    @{ Source = "test_modal_retry_mechanism.py"; Dest = "tests/integration/retry/"; Reason = "Test mécanisme retry" },
    @{ Source = "test_rhetorical_demo_integration.py"; Dest = "tests/demos/rhetorical/"; Reason = "Démo intégration rhétorique" },
    @{ Source = "test_simple_unified_pipeline.py"; Dest = "tests/integration/pipelines/"; Reason = "Test pipeline unifié" },
    @{ Source = "test_sk_retry_demo.py"; Dest = "tests/demos/retry/"; Reason = "Démo SK retry" },
    @{ Source = "test_source_management_integration.py"; Dest = "tests/integration/sources/"; Reason = "Test gestion sources" },
    @{ Source = "test_trace_analyzer_conversation_format.py"; Dest = "tests/unit/analyzers/"; Reason = "Test unitaire analyseur" },
    @{ Source = "test_unified_report_generation_integration.py"; Dest = "tests/integration/reporting/"; Reason = "Test intégration reporting" },
    @{ Source = "test_unified_text_analysis_integration.py"; Dest = "tests/integration/analysis/"; Reason = "Test analyse de texte" },
    @{ Source = "TEST_MAPPING.md"; Dest = "docs/testing/"; Reason = "Documentation mapping tests" }
)

# Rapports à déplacer
$reportsToMove = @(
    @{ Source = "AUDIT_AUTHENTICITE_FOL_COMPLETE.md"; Dest = "docs/audits/"; Reason = "Audit authenticité FOL" },
    @{ Source = "AUDIT_REFACTORISATION_ORCHESTRATION.md"; Dest = "docs/audits/"; Reason = "Audit refactorisation" },
    @{ Source = "CONSOLIDATION_ORCHESTRATION_REUSSIE.md"; Dest = "docs/reports/consolidation/"; Reason = "Rapport consolidation" },
    @{ Source = "RAPPORT_ANALYSE_CORRECTION_BNF_INTELLIGENTE.md"; Dest = "docs/reports/analysis/"; Reason = "Rapport analyse BNF" },
    @{ Source = "RAPPORT_EVALUATION_TESTS_SYSTEME.md"; Dest = "docs/reports/testing/"; Reason = "Évaluation tests système" },
    @{ Source = "RAPPORT_FINAL_FOL_AUTHENTIQUE.md"; Dest = "docs/reports/fol/"; Reason = "Rapport final FOL" },
    @{ Source = "RAPPORT_IMPLEMENTATION_VRAIE_SK_RETRY.md"; Dest = "docs/reports/implementation/"; Reason = "Implémentation SK retry" },
    @{ Source = "SYNTHESE_FINALE_REFACTORISATION_UNIFIED_REPORTS.md"; Dest = "docs/reports/refactoring/"; Reason = "Synthèse refactorisation" },
    @{ Source = "VALIDATION_ECOSYSTEM_FINALE.md"; Dest = "docs/validation/"; Reason = "Validation écosystème" }
)

# Ajout des autres rapports détectés
$additionalReports = Get-ChildItem -File | Where-Object { 
    $_.Name -match "^(RAPPORT_|TRACE_|VALIDATION_|rapport_)" -and 
    $_.Name -notmatch "^(DEPOT_CLEANUP_ANALYSIS|README)" 
} | ForEach-Object {
    @{ Source = $_.Name; Dest = "docs/reports/various/"; Reason = "Rapport additionnel" }
}
$reportsToMove += $additionalReports

# Fichiers temporaires à supprimer
$tempFilesToDelete = @(
    "temp_original_file.enc",
    "page_content.html",
    "scratch_tweety_interactions.py",
    "pytest_full_output.log",
    "pytest_prop_logic_*.log",
    "pytest_all_tests_*.log",
    "pytest_output*.log",
    "setup_global_output.log",
    "extract_agent.log",
    "temp_*.py",
    "temp_*.enc"
)

# === PREVIEW MODE ===
if ($Mode -eq "preview") {
    Write-Header "PREVIEW - ACTIONS QUI SERONT EFFECTUÉES"
    
    # Création des répertoires
    Write-ColorText "📁 CRÉATION DE RÉPERTOIRES" "Title"
    $dirsToCreate = @(
        "tests/demos/fol", "tests/demos/modal", "tests/demos/rhetorical", "tests/demos/retry",
        "tests/integration/conversation", "tests/integration/modal", "tests/integration/orchestration",
        "tests/integration/retry", "tests/integration/sources", "tests/integration/reporting",
        "tests/integration/analysis", "tests/integration/pipelines",
        "tests/validation/modal", "tests/unit/analyzers",
        "docs/audits", "docs/reports/consolidation", "docs/reports/analysis", "docs/reports/testing",
        "docs/reports/fol", "docs/reports/implementation", "docs/reports/refactoring",
        "docs/reports/various", "docs/validation", "docs/testing"
    )
    
    foreach ($dir in $dirsToCreate) {
        if (-not (Test-Path $dir)) {
            Show-FileAction "CRÉER" $dir "" "" "Nouveau répertoire organisationnel"
        }
    }
    
    # Tests à déplacer
    Write-ColorText "🧪 DÉPLACEMENT DES TESTS ($($testsToMove.Count) fichiers)" "Title"
    foreach ($test in $testsToMove) {
        if (Test-Path $test.Source) {
            $size = [math]::Round((Get-Item $test.Source).Length / 1KB, 1)
            Show-FileAction "DÉPLACER" $test.Source $test.Dest "${size}KB" $test.Reason
        }
    }
    
    # Rapports a deplacer
    Write-ColorText "[RAPPORTS] DEPLACEMENT DES RAPPORTS ($($reportsToMove.Count) fichiers)" "Title"
    foreach ($report in $reportsToMove) {
        if (Test-Path $report.Source) {
            $size = [math]::Round((Get-Item $report.Source).Length / 1KB, 1)
            Show-FileAction "DÉPLACER" $report.Source $report.Dest "${size}KB" $report.Reason
        }
    }
    
    # Fichiers temporaires a supprimer
    Write-ColorText "[CLEANUP] SUPPRESSION FICHIERS TEMPORAIRES" "Title"
    $actualTempFiles = @()
    foreach ($pattern in $tempFilesToDelete) {
        $matches = Get-ChildItem -File -Name $pattern -ErrorAction SilentlyContinue
        $actualTempFiles += $matches
    }
    
    foreach ($tempFile in $actualTempFiles) {
        if (Test-Path $tempFile) {
            $size = [math]::Round((Get-Item $tempFile).Length / 1KB, 1)
            Show-FileAction "SUPPRIMER" $tempFile "" "${size}KB" "Fichier temporaire"
        }
    }
    
    # Résumé
    Write-Header "RÉSUMÉ DES ACTIONS"
    Write-ColorText "Tests a deplacer: $($testsToMove.Count)" "Info"
    Write-ColorText "Rapports a deplacer: $($reportsToMove.Count)" "Info"
    Write-ColorText "Fichiers temporaires a supprimer: $($actualTempFiles.Count)" "Info"
    Write-ColorText "Repertoires a creer: $($dirsToCreate.Count)" "Info"
    Write-Host ""
    Write-ColorText "Pour executer ces actions:" "Action"
    Write-Host "  .\scripts\maintenance\depot_cleanup_migration.ps1 -Mode execute" -ForegroundColor White
    Write-Host ""
    
    exit 0
}

# === EXECUTE MODE ===
if ($Mode -eq "execute") {
    Write-Header "EXECUTION - NETTOYAGE DU DEPOT"
    
    $successCount = 0
    $errorCount = 0
    
    # Creation des repertoires
    Write-ColorText "[REPERTOIRES] Creation des repertoires..." "Info"
    $dirsToCreate = @(
        "tests/demos/fol", "tests/demos/modal", "tests/demos/rhetorical", "tests/demos/retry",
        "tests/integration/conversation", "tests/integration/modal", "tests/integration/orchestration", 
        "tests/integration/retry", "tests/integration/sources", "tests/integration/reporting",
        "tests/integration/analysis", "tests/integration/pipelines",
        "tests/validation/modal", "tests/unit/analyzers",
        "docs/audits", "docs/reports/consolidation", "docs/reports/analysis", "docs/reports/testing",
        "docs/reports/fol", "docs/reports/implementation", "docs/reports/refactoring",
        "docs/reports/various", "docs/validation", "docs/testing"
    )
    
    foreach ($dir in $dirsToCreate) {
        if (-not (Test-Path $dir)) {
            try {
                New-Item -ItemType Directory -Path $dir -Force | Out-Null
                Write-ColorText "[OK] Cree: $dir" "Success"
                $successCount++
            } catch {
                Write-ColorText "[ERREUR] Creation $dir : $($_.Exception.Message)" "Error"
                $errorCount++
            }
        }
    }
    
    # Deplacement des tests
    Write-ColorText "[TESTS] Deplacement des tests..." "Info"
    foreach ($test in $testsToMove) {
        if (Test-Path $test.Source) {
            try {
                $destFile = Join-Path $test.Dest (Split-Path $test.Source -Leaf)
                Move-Item $test.Source $destFile -Force
                Write-ColorText "[OK] Deplace: $($test.Source) -> $destFile" "Success"
                $successCount++
            } catch {
                Write-ColorText "[ERREUR] Deplacement $($test.Source): $($_.Exception.Message)" "Error"
                $errorCount++
            }
        }
    }
    
    # Deplacement des rapports
    Write-ColorText "[RAPPORTS] Deplacement des rapports..." "Info"
    foreach ($report in $reportsToMove) {
        if (Test-Path $report.Source) {
            try {
                $destFile = Join-Path $report.Dest (Split-Path $report.Source -Leaf)
                Move-Item $report.Source $destFile -Force
                Write-ColorText "[OK] Deplace: $($report.Source) -> $destFile" "Success"
                $successCount++
            } catch {
                Write-ColorText "[ERREUR] Deplacement $($report.Source): $($_.Exception.Message)" "Error"
                $errorCount++
            }
        }
    }
    
    # Suppression fichiers temporaires
    Write-ColorText "[CLEANUP] Suppression des fichiers temporaires..." "Info"
    foreach ($pattern in $tempFilesToDelete) {
        $matches = Get-ChildItem -File -Name $pattern -ErrorAction SilentlyContinue
        foreach ($tempFile in $matches) {
            try {
                Remove-Item $tempFile -Force
                Write-ColorText "[OK] Supprime: $tempFile" "Success"
                $successCount++
            } catch {
                Write-ColorText "[ERREUR] Suppression $tempFile : $($_.Exception.Message)" "Error"
                $errorCount++
            }
        }
    }
    
    # Resume final
    Write-Header "RESUME DE L'EXECUTION"
    Write-ColorText "[OK] Operations reussies: $successCount" "Success"
    if ($errorCount -gt 0) {
        Write-ColorText "[ERREUR] Erreurs rencontrees: $errorCount" "Error"
    }
    
    Write-ColorText "[ACTION] Prochaines etapes recommandees:" "Action"
    Write-Host "  1. Vérifiez le résultat avec: git status" -ForegroundColor White
    Write-Host "  2. Testez les imports dans les fichiers déplacés" -ForegroundColor White
    Write-Host "  3. Committez les changements: git add -A && git commit -m 'Reorganisation structure projet'" -ForegroundColor White
    Write-Host ""
}

# === CLEANUP-ONLY MODE ===
if ($Mode -eq "cleanup-only") {
    Write-Header "NETTOYAGE UNIQUEMENT - FICHIERS TEMPORAIRES"
    
    $cleanupCount = 0
    foreach ($pattern in $tempFilesToDelete) {
        $matches = Get-ChildItem -File -Name $pattern -ErrorAction SilentlyContinue
        foreach ($tempFile in $matches) {
            if (Test-Path $tempFile) {
                $size = [math]::Round((Get-Item $tempFile).Length / 1KB, 1)
                try {
                    Remove-Item $tempFile -Force
                    Write-ColorText "[OK] Supprime: $tempFile (${size}KB)" "Success"
                    $cleanupCount++
                } catch {
                    Write-ColorText "[ERREUR] $tempFile - $($_.Exception.Message)" "Error"
                }
            }
        }
    }
    
    Write-ColorText "[OK] $cleanupCount fichiers temporaires supprimes" "Success"
}

Write-ColorText "Script terminé." "Info"
