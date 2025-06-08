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

Write-Host "[ACTIVATION] Activation environnement Oracle Enhanced v2.1.0..." -ForegroundColor Green
Write-Host "[PROJET] Racine projet: $ProjectRoot" -ForegroundColor Cyan

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
    
    # Recherche et activation de l'environnement conda/venv
    $CondaActivated = $false
    $VenvActivated = $false
    
    # Tentative d'activation conda
    try {
        $CondaEnvs = & conda env list 2>$null | Where-Object { $_ -match "oracle|argum|intelligence" }
        if ($CondaEnvs) {
            $EnvName = ($CondaEnvs[0] -split '\s+')[0]
            Write-Host "[CONDA] Activation environnement conda: $EnvName" -ForegroundColor Yellow
            & conda activate $EnvName 2>$null
            $CondaActivated = $true
        }
    } catch {
        Write-Host "[ATTENTION] Conda non disponible, tentative venv..." -ForegroundColor Yellow
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
                Write-Host "[VENV] Activation environnement venv: $VenvPath" -ForegroundColor Yellow
                & $VenvPath
                $VenvActivated = $true
                break
            }
        }
    }
    
    if (!$CondaActivated -and !$VenvActivated) {
        Write-Host "[ATTENTION] Aucun environnement virtuel detecte, utilisation Python systeme" -ForegroundColor Yellow
    }
    
    # Verification de Python
    try {
        $PythonVersion = & python --version 2>&1
        Write-Host "[OK] Python detecte: $PythonVersion" -ForegroundColor Green
    } catch {
        Write-Host "[ERREUR] Python non disponible!" -ForegroundColor Red
        throw "Python non trouve dans le PATH"
    }
    
    # Execution de la commande
    Write-Host "[EXECUTION] Execution: $CommandToRun" -ForegroundColor Cyan
    Write-Host ("=" * 80) -ForegroundColor Gray
    
    # Separer la commande et ses arguments
    $CommandParts = $CommandToRun -split ' ', 2
    $Command = $CommandParts[0]
    $Arguments = if ($CommandParts.Length -gt 1) { $CommandParts[1] } else { "" }
    
    # Executer la commande
    if ($Arguments) {
        $ArgumentList = $Arguments -split ' '
        & $Command $ArgumentList
    } else {
        & $Command
    }
    
    $ExitCode = $LASTEXITCODE
    Write-Host ("=" * 80) -ForegroundColor Gray
    
    if ($ExitCode -eq 0) {
        Write-Host "[SUCCES] Commande executee avec succes (code: $ExitCode)" -ForegroundColor Green
    } else {
        Write-Host "[ECHEC] Echec de la commande (code: $ExitCode)" -ForegroundColor Red
    }
    
    return $ExitCode
    
} catch {
    Write-Host "[ERREUR] Erreur lors de l'execution: $($_.Exception.Message)" -ForegroundColor Red
    return 1
    
} finally {
    # Retour au repertoire original
    Pop-Location
}