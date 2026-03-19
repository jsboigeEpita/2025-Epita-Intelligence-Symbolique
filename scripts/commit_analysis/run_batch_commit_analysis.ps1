<#
.SYNOPSIS
Orchestrateur pour l'analyse qualitative de commits en lots incrémentiels.

.DESCRIPTION
Ce script exécute l'analyse de commits en 3 phases successives avec validation utilisateur,
en s'appuyant sur le script Python `run_qualitative_commit_analysis.py`. Il est conçu
pour traiter un grand nombre de commits de manière contrôlée et robuste.

.PARAMETER CommitsDir
Répertoire contenant les fichiers JSON de commits. Défaut: "docs\commits_audit"

.PARAMETER Batch1Size
Taille du premier lot. Défaut: 100

.PARAMETER Batch2Size
Taille du deuxième lot. Défaut: 500

.PARAMETER NumWorkers
Nombre de workers parallèles pour le script Python. Défaut: 15

.PARAMETER PruneDiffs
Active la suppression des diffs dans les fichiers JSON après une analyse réussie.

.PARAMETER Overwrite
Force la réécriture des analyses existantes.

.PARAMETER SkipConfirmation
Ignore les confirmations utilisateur pour une exécution entièrement automatique.

.PARAMETER TestMode
Active le mode test avec des tailles de lots et un nombre de workers réduits pour une validation rapide.

.EXAMPLE
# Exécution standard avec confirmations utilisateur
.\Run-BatchCommitAnalysis.ps1

.EXAMPLE
# Exécution en mode automatique, en supprimant les diffs et avec 10 workers
.\Run-BatchCommitAnalysis.ps1 -SkipConfirmation -PruneDiffs -NumWorkers 10

.EXAMPLE
# Exécution en mode test pour valider le script
.\Run-BatchCommitAnalysis.ps1 -TestMode
#>
param(
    [string]$CommitsDir = "docs\commits_audit",
    [int]$Batch1Size = 100,
    [int]$Batch2Size = 500,
    [int]$NumWorkers = 15,
    [switch]$PruneDiffs,
    [switch]$Overwrite,
    [switch]$SkipConfirmation,
    [switch]$TestMode
)

$ErrorActionPreference = 'Stop'
$script:LogFile = $null

#region Fonctions de support et Logging

function Initialize-Logging {
    $logDir = Join-Path $PSScriptRoot "_temp\logs"
    if (-not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }
    
    $script:LogFile = Join-Path $logDir "batch_orchestrator_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
    
    "Démarrage de l'orchestrateur de lots - $(Get-Date)" | Out-File -FilePath $script:LogFile -Encoding UTF8
}

function Write-LogEntry {
    param([string]$Message, [string]$Level = "INFO")
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [$Level] $Message"
    
    if ($script:LogFile) {
        $logEntry | Out-File -FilePath $script:LogFile -Append -Encoding UTF8
    }
    
    switch ($Level) {
        "ERROR"   { Write-Host $Message -ForegroundColor Red }
        "WARN"    { Write-Host $Message -ForegroundColor Yellow }
        "SUCCESS" { Write-Host $Message -ForegroundColor Green }
        "DEBUG"   { Write-Host $Message -ForegroundColor DarkGray }
        default   { Write-Host $Message -ForegroundColor White }
    }
}

function Test-Prerequisites {
    Write-LogEntry -Message "Vérification des prérequis..."
    $errors = @()
    
    # Vérification du script d'activation
    if (-not (Test-Path (Join-Path $PSScriptRoot "activate_project_env.ps1"))) {
        $errors += "Script d'activation 'activate_project_env.ps1' non trouvé à la racine."
    }
    
    # Vérification du script Python
    if (-not (Test-Path "scripts/maintenance/run_qualitative_commit_analysis.py")) {
        $errors += "Script d'analyse 'run_qualitative_commit_analysis.py' non trouvé."
    }

    # Vérification du répertoire de commits
    if (-not (Test-Path $CommitsDir)) {
        $errors += "Répertoire de commits non trouvé : $CommitsDir"
    } else {
        $commitFiles = Get-ChildItem -Path $CommitsDir -Filter *.json
        if ($commitFiles.Count -eq 0) {
            $errors += "Aucun fichier .json trouvé dans le répertoire de commits : $CommitsDir"
        }
    }
    
    if ($errors.Count -gt 0) {
        $errorMsg = "Erreurs de prérequis critiques :`n" + ($errors -join "`n")
        Write-LogEntry -Message $errorMsg -Level "ERROR"
        throw $errorMsg
    }
    Write-LogEntry -Message "Prérequis validés avec succès." -Level "SUCCESS"
}

#endregion

#region Fonctions d'interaction et d'exécution

function Get-UserConfirmation {
    param(
        [string]$Prompt
    )
    
    if ($SkipConfirmation) {
        Write-LogEntry -Message "Confirmation automatique (SkipConfirmation activé)." -Level "WARN"
        return 'Continue'
    }

    do {
        $response = Read-Host "$Prompt (oui/non/arreter)"
        switch ($response.ToLower()) {
            'oui'     { return 'Continue' }
            'o'       { return 'Continue' }
            'non'     { return 'Stop' }
            'n'       { return 'Stop' }
            'arreter' { return 'Abort' }
            'a'       { return 'Abort' }
            default   { 
                Write-Host "Réponse invalide. Veuillez répondre 'oui', 'non' ou 'arreter'." -ForegroundColor Red 
            }
        }
    } while ($true)
}

function Build-PythonCommand {
    param(
        [int]$MaxCommits
    )
    
    $pythonScript = "scripts/maintenance/run_qualitative_commit_analysis.py"
    
    $baseArgs = @(
        "--commits-dir", $CommitsDir,
        "--num-workers", $NumWorkers
    )
    
    if ($PruneDiffs) { $baseArgs += "--prune-diffs" }
    if ($Overwrite)  { $baseArgs += "--overwrite" }
    if ($MaxCommits -gt 0) { $baseArgs += @("--max-commits", $MaxCommits) }

    return "python $pythonScript " + ($baseArgs -join " ")
}

function Invoke-InProjectEnvironment {
    param([string]$Command)
    
    $activateScript = Join-Path $PSScriptRoot "activate_project_env.ps1"
    
    Write-LogEntry -Message "Exécution dans l'environnement projet : $Command" -Level "DEBUG"
    
    & $activateScript -CommandToRun $Command
    
    return $LASTEXITCODE
}

function Execute-Batch {
    param(
        [int]$BatchNumber,
        [string]$BatchName,
        [int]$MaxCommits
    )
    
    $startTime = Get-Date
    Write-LogEntry -Message "Démarrage du lot $BatchNumber ($BatchName) à $startTime" -Level "SUCCESS"
    
    $command = Build-PythonCommand -MaxCommits $MaxCommits
    $exitCode = Invoke-InProjectEnvironment -Command $command
    
    $endTime = Get-Date
    $duration = $endTime - $startTime
    
    if ($exitCode -eq 0) {
        Write-LogEntry -Message "Lot $BatchNumber terminé avec succès en $($duration.TotalMinutes.ToString('F1')) minutes." -Level "SUCCESS"
    } else {
        throw "Le lot $BatchNumber a échoué avec le code de sortie $exitCode."
    }
}

#endregion

#region Logique Principale

function Start-BatchCommitAnalysis {
    Initialize-Logging
    Write-LogEntry -Message "Orchestrateur d'analyse de commits démarré."

    if ($TestMode) {
        Write-LogEntry -Message "MODE TEST ACTIVÉ - Paramètres surchargés." -Level "WARN"
        $script:Batch1Size = 5
        $script:Batch2Size = 10
        $script:NumWorkers = 2
        $script:CommitsDir = "docs\commits_audit" # Assurer un chemin valide pour les tests
    }

    Test-Prerequisites
    
    $totalFiles = (Get-ChildItem -Path $CommitsDir -Filter *.json).Count
    Write-LogEntry -Message "Total de $totalFiles fichiers de commit détectés."

    # --- LOT 1 ---
    $confirmation = Get-UserConfirmation -Prompt "Prêt à traiter le Lot 1 ($Batch1Size commits sur $totalFiles) ?"
    if ($confirmation -ne 'Continue') {
        Write-LogEntry -Message "Opération annulée par l'utilisateur avant le Lot 1." -Level "WARN"
        return
    }
    Execute-Batch -BatchNumber 1 -BatchName "$Batch1Size commits" -MaxCommits $Batch1Size

    # --- LOT 2 ---
    $processedSoFar = $Batch1Size
    $remaining = $totalFiles - $processedSoFar
    if ($remaining -le 0) {
        Write-LogEntry -Message "Tous les commits ont été traités après le premier lot." -Level "SUCCESS"
    } else {
        $confirmation = Get-UserConfirmation -Prompt "Lot 1 terminé. Prêt pour le Lot 2 ($Batch2Size commits sur $remaining restants) ?"
        if ($confirmation -ne 'Continue') {
            Write-LogEntry -Message "Opération annulée par l'utilisateur avant le Lot 2." -Level "WARN"
            return
        }
        Execute-Batch -BatchNumber 2 -BatchName "$Batch2Size commits" -MaxCommits ($Batch1Size + $Batch2Size)
    }

    # --- LOT 3 ---
    $processedSoFar = $Batch1Size + $Batch2Size
    $remaining = $totalFiles - $processedSoFar
    if ($remaining -le 0) {
        Write-LogEntry -Message "Tous les commits ont été traités après le deuxième lot." -Level "SUCCESS"
    } else {
        $confirmation = Get-UserConfirmation -Prompt "Lot 2 terminé. Prêt pour le Lot 3 (tous les $remaining commits restants) ?"
        if ($confirmation -ne 'Continue') {
            Write-LogEntry -Message "Opération annulée par l'utilisateur avant le Lot 3." -Level "WARN"
            return
        }
        Execute-Batch -BatchNumber 3 -BatchName "Tous les restants" -MaxCommits 0 # 0 ou null pour tout traiter
    }

    Write-LogEntry -Message "Analyse par lots terminée avec succès !" -Level "SUCCESS"
}

# --- Point d'entrée du script ---
try {
    Start-BatchCommitAnalysis
}
catch {
    Write-LogEntry -Message "Une erreur critique a interrompu l'orchestrateur : $($_.Exception.Message)" -Level "ERROR"
    exit 1
}
