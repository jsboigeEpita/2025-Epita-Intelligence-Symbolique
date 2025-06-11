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
    
    # Recherche et activation de l'environnement conda/venv
    $CondaActivated = $false
    $VenvActivated = $false
    
    # Tentative d'activation conda
    try {
        # Trouver l'executable conda
        $CondaExe = Get-Command conda -ErrorAction SilentlyContinue
        if (!$CondaExe) {
            # Chercher dans les chemins courants si ce n'est pas dans le PATH
            $CondaPaths = @(
                "$env:USERPROFILE\Miniconda3\Scripts\conda.exe",
                "$env:USERPROFILE\Anaconda3\Scripts\conda.exe",
                "C:\ProgramData\Miniconda3\Scripts\conda.exe",
                "C:\ProgramData\Anaconda3\Scripts\conda.exe"
            )
            $CondaExe = $CondaPaths | Where-Object { Test-Path $_ } | Select-Object -First 1
        }
        
        if ($CondaExe) {
            $EnvName = "projet-is"
            Write-Host "✅ [CONDA] Utilisation de l'environnement '$EnvName'" -ForegroundColor Green
            $CondaActivated = $true
        } else {
            Write-Host "[ATTENTION] Conda non trouvé." -ForegroundColor Yellow
        }
    } catch {
        Write-Host "[ATTENTION] Erreur lors de la recherche de Conda: $($_.Exception.Message)" -ForegroundColor Red
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
    
    # Separer la commande et ses arguments
    $CommandParts = $CommandToRun -split ' ', 2
    $Command = $CommandParts[0]
    $Arguments = if ($CommandParts.Length -gt 1) { $CommandParts[1] } else { "" }
    
    # Executer la commande
    if ($CondaActivated) {
        $CommandParts = $CommandToRun.Split(' ', 2)
        $Command = $CommandParts[0]
        $Arguments = if ($CommandParts.Length -gt 1) { $CommandParts[1] } else { "" }
        $condaRunCommand = "conda run -n $EnvName --no-capture-output $Command $Arguments"
        Write-Host "[INFO] Commande CONDA: $condaRunCommand" -ForegroundColor Gray
        Invoke-Expression $condaRunCommand
    } else {
         if ($Arguments) {
            $ArgumentList = $Arguments -split ' '
            & $Command $ArgumentList
        } else {
            & $Command
        }
    }
    
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