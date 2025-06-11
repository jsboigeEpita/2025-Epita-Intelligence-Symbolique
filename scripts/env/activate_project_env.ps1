<#
.SYNOPSIS
Script d'activation de l'environnement Oracle Enhanced v2.1.0

.DESCRIPTION
Active l'environnement Python du projet et execute une commande specifiee.
Gere automatiquement l'activation de conda/venv et la configuration des paths.

.PARAMETER CommandToRun
Commande a executer dans l'environnement active

.EXAMPLE
powershell -File .\scripts\env\activate_project_env.ps1 -CommandToRun "python -m scripts.maintenance.analyze_obsolete_documentation --full-analysis"
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$CommandToRun
)

# Configuration
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$LogsDir = Join-Path $ProjectRoot "logs"

# Creer le dossier logs s'il n'existe pas
if (!(Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
}

Write-Host "🚀 =====================================================================" -ForegroundColor Green
Write-Host "🚀 ACTIVATION ENVIRONNEMENT DÉDIÉ - Oracle Enhanced v2.1.0" -ForegroundColor Green
Write-Host "🚀 =====================================================================" -ForegroundColor Green
Write-Host "[PROJET] Racine projet: $ProjectRoot" -ForegroundColor Cyan
Write-Host "[INFO] Script d'activation: $PSCommandPath" -ForegroundColor Gray

# Changer vers la racine du projet
Push-Location $ProjectRoot

try {
    # Definir les variables d'environnement Python
    $paths = @(
        $ProjectRoot,
        (Join-Path $ProjectRoot "project_core"),
        (Join-Path $ProjectRoot "libs"),
        (Join-Path $ProjectRoot "argumentation_analysis")
    )
    $env:PYTHONPATH = ($paths -join ";") + ";$env:PYTHONPATH"
    $env:PYTHONIOENCODING = "utf-8"
    # Définir un drapeau pour que les scripts Python sachent qu'ils sont exécutés par ce script
    $env:IS_ACTIVATION_SCRIPT_RUNNING = "true"
    # Recherche et activation de l'environnement conda/venv
    $CondaActivated = $false
    $VenvActivated = $false
    
    # Tentative d'activation conda
    $PythonExecutable = $null
    try {
        # Approche robuste : trouver le chemin de l'environnement via `conda info`
        Write-Host "[INFO] Recherche de l'environnement Conda 'projet-is' via JSON..." -ForegroundColor Gray
        $conda_info_json = conda info --envs --json | ConvertFrom-Json
        $projet_is_path = $conda_info_json.envs | Where-Object { $_ -like '*\projet-is' } | Select-Object -First 1

        if ($projet_is_path) {
            $CondaActivated = $true # Marqueur pour le logging
            Write-Host "✅ [CONDA] Environnement 'projet-is' localisé: $projet_is_path" -ForegroundColor Green
            $PythonExecutable = Join-Path $projet_is_path "python.exe"
            
            if (-not (Test-Path $PythonExecutable)) {
                Write-Host "❌ [PYTHON] Exécutable introuvable: $PythonExecutable. Utilisation de 'python' par défaut." -ForegroundColor Red
                $PythonExecutable = $null # Annuler pour permettre fallback
            }
        } else {
            Write-Host "⚠️ [CONDA] Environnement 'projet-is' introuvable via `conda info --json`." -ForegroundColor Yellow
        }
    } catch {
        Write-Host "⚠️ [ERREUR] Impossible de parser la sortie JSON de Conda. $($_.Exception.Message)" -ForegroundColor Yellow
    }
    
    # Tentative d'activation venv si conda echoue
    if (!$CondaActivated) {
        $VenvPaths = @(
            (Join-Path $ProjectRoot "venv\Scripts\Activate.ps1"),
            (Join-Path $ProjectRoot "env\Scripts\Activate.ps1"),
            (Join-Path $ProjectRoot ".venv\Scripts\Activate.ps1")
        )
        foreach ($VenvPath in $VenvPaths) {
            if (Test-Path $VenvPath) {
                Write-Host "[VENV] Activation environnement local: $VenvPath" -ForegroundColor Green
                & $VenvPath
                $VenvActivated = $true
                Write-Host "[INFO] Environnement venv local active (recommande: conda 'projet-is')" -ForegroundColor Cyan
                break
            }
        }
    }
    
    if (!$CondaActivated -and !$VenvActivated) {
        Write-Host "[ATTENTION] PYTHON SYSTEME UTILISE!" -ForegroundColor Red
        Write-Host "⚠️  Aucun environnement virtuel détecté." -ForegroundColor Yellow
        Write-Host "⚠️  Recommandation: conda env create -f environment.yml" -ForegroundColor Yellow
        Write-Host "⚠️  Puis: conda activate projet-is" -ForegroundColor Yellow
    }
    
    # Verification de Python
    try {
        $PythonVersion = & python --version 2>&1
        $PythonPath = & python -c "import sys; print(sys.executable)" 2>&1
        Write-Host "[PYTHON] Version: $PythonVersion" -ForegroundColor Green
        Write-Host "[PYTHON] Executable: $PythonPath" -ForegroundColor Cyan
        
        # Diagnostic rapide environnement
        $EnvType = if ($CondaActivated) { "CONDA" } elseif ($VenvActivated) { "VENV" } else { "SYSTEME" }
        Write-Host "[ENVIRONNEMENT] Type: $EnvType" -ForegroundColor $(if ($EnvType -eq "SYSTEME") { "Yellow" } else { "Green" })
        
    } catch {
        Write-Host "[ERREUR] Python non disponible!" -ForegroundColor Red
        throw "Python non trouve dans le PATH"
    }
    
    # Execution de la commande
    Write-Host ""
    Write-Host "[EXECUTION] Lancement de la commande..." -ForegroundColor Cyan
    Write-Host "[COMMANDE] $CommandToRun" -ForegroundColor Cyan
    Write-Host ("=" * 80) -ForegroundColor Gray
    
    # Déterminer la commande finale à exécuter
    $FinalCommand = $CommandToRun
    if ($PythonExecutable -and $CommandToRun.StartsWith("python ")) {
        # Remplacer "python" par le chemin complet et absolu de l'exécutable
        $CommandArgs = $CommandToRun.Substring(7)
        # Envelopper le chemin de l'exécutable dans des guillemets pour gérer les espaces
        $FinalCommand = "& `"$PythonExecutable`" $CommandArgs"
        Write-Host "[INFO] Exécution avec le Python de l'environnement: $PythonExecutable" -ForegroundColor Green
    } else {
        # Exécution standard si ce n'est pas une commande python ou si l'exécutable n'a pas été trouvé
        $FinalCommand = $CommandToRun
    }
    
    # Exécuter la commande finale en utilisant Invoke-Expression pour une gestion robuste des arguments
    Invoke-Expression $FinalCommand
    
    $ExitCode = $LASTEXITCODE
    Write-Host ("=" * 80) -ForegroundColor Gray
    
    if ($ExitCode -eq 0) {
        Write-Host "[SUCCES] Commande executee avec succes (code: $ExitCode)" -ForegroundColor Green
    } else {
        Write-Host "[ECHEC] Echec de la commande (code: $ExitCode)" -ForegroundColor Red
        Write-Host "[AIDE] Verifiez l'environnement avec:" -ForegroundColor Yellow
        Write-Host "       .\setup_project_env.ps1 -CommandToRun 'python scripts/env/diagnose_environment.py'" -ForegroundColor Yellow
    }
    
    return $ExitCode
    
} catch {
    Write-Host "[ERREUR] Erreur lors de l'execution: $($_.Exception.Message)" -ForegroundColor Red
    return 1
    
} finally {
    # Retour au repertoire original
    Pop-Location
}