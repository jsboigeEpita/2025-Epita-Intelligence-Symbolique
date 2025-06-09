#!/usr/bin/env pwsh
<#
.SYNOPSIS
Script d'activation de l'environnement projet (refactorisé avec Python)

.DESCRIPTION
Active l'environnement conda du projet et exécute optionnellement une commande.
Utilise les modules Python mutualisés pour la gestion d'environnement.

.PARAMETER CommandToRun
Commande à exécuter après activation de l'environnement

.EXAMPLE
.\activate_project_env.ps1
.\activate_project_env.ps1 -CommandToRun "python --version"

.NOTES
Refactorisé - Utilise scripts/core/environment_manager.py
#>

param(
    [string]$CommandToRun = $null
)

# Configuration
$ProjectRoot = $PSScriptRoot
$PythonModule = "scripts/core/environment_manager.py"

# Fonction de logging simple
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $color = switch ($Level) {
        "ERROR" { "Red" }
        "SUCCESS" { "Green" }
        default { "White" }
    }
    Write-Host "[$timestamp] $Message" -ForegroundColor $color
}

try {
    Write-Log "Activation environnement projet via Python..."
    
    # Construction de la commande Python
    $pythonArgs = @("python", $PythonModule)
    
    if ($CommandToRun) {
        $pythonArgs += "--command", $CommandToRun
        Write-Log "Commande à exécuter: $CommandToRun"
    }
    
    # Exécution via le module Python
    & $pythonArgs[0] $pythonArgs[1..($pythonArgs.Length-1)]
    $exitCode = $LASTEXITCODE
    
    if ($exitCode -eq 0) {
        Write-Log "Environnement activé avec succès" "SUCCESS"
    } else {
        Write-Log "Échec activation (Code: $exitCode)" "ERROR"
    }
    
    exit $exitCode
    
} catch {
    Write-Log "Erreur critique: $($_.Exception.Message)" "ERROR"
    exit 1
}