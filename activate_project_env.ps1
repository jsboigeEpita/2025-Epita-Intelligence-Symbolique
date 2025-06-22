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
    [string]$CommandToRun = $null,
    [string]$PythonScriptPath = $null,
    [switch]$Verbose = $false,
    [switch]$ForceReinstall = $false,
    [int]$CondaVerboseLevel = 0
)

# Fonction de logging simple
function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )
    # On écrit tout sur le flux d'erreur (stderr) pour ne pas polluer le stdout
    # qui est utilisé pour récupérer le résultat JSON des scripts Python.
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logLine = "[$timestamp] [$Level] $Message"
    $Host.UI.WriteErrorLine($logLine)
}

# --- LA CONFIGURATION JAVA EST DÉLÉGUÉE AU SCRIPT PYTHON ---
# Le script 'environment_manager.py' est maintenant entièrement responsable
# de la détection, validation, et auto-installation du JDK via le fichier .env.
# Cela centralise la logique et la rend plus robuste.
Write-Log "La configuration de JAVA_HOME est déléguée à environment_manager.py." "INFO"

# Configuration
Write-Log "Activating environment..." "DEBUG"
$ProjectRoot = $PSScriptRoot
$PythonModule = "project_core/core_from_scripts/environment_manager.py"

try {
    # Si un chemin de script Python est fourni, on construit la commande à exécuter
    # Cela offre un raccourci pratique par rapport à --CommandToRun "python ..."
    if ($PythonScriptPath) {
        $FullScriptPath = Join-Path $ProjectRoot $PythonScriptPath
        if (-not (Test-Path $FullScriptPath)) {
            Write-Log "Le fichier Python spécifié via -PythonScriptPath est introuvable: $FullScriptPath" "ERROR"
            exit 1
        }
        # On met la commande entre guillemets pour gérer les espaces dans les chemins
        $CommandToRun = "python `"$FullScriptPath`""
        Write-Log "Commande à exécuter définie via -PythonScriptPath: $CommandToRun"
    }

    Write-Log "Activation environnement projet via Python..."
    
    # Chemin vers le script Python environment_manager.py
    $pythonScriptPath = Join-Path $ProjectRoot $PythonModule

    # Commande 1: Activer l'environnement (sans exécuter de commande interne pour l'instant)
    # $pythonActivateArgs = @("python", $pythonScriptPath)
    # Write-Log "Activation initiale de l'environnement..."
    # & $pythonActivateArgs[0] $pythonActivateArgs[1..($pythonActivateArgs.Length-1)]
    # if ($LASTEXITCODE -ne 0) {
    #     Write-Log "Échec de l'activation initiale de l'environnement." "ERROR"
    #     exit 1
    # }
    # Write-Log "Activation initiale réussie." "SUCCESS"

    # Construction dynamique des arguments pour le script Python
    $pythonArgs = @($pythonScriptPath)

    if ($ForceReinstall) {
        Write-Log "Option -ForceReinstall détectée. L'environnement Conda sera forcé à la réinstallation." "INFO"
        $pythonArgs += "--reinstall", "conda"
    }

    if ($CommandToRun) {
        Write-Log "Commandes à exécuter: $CommandToRun"
        # Le script Python gère maintenant la décomposition des commandes si nécessaire
        $pythonArgs += "--command", $CommandToRun
    } else {
         Write-Log "Aucune commande à exécuter. Activation simple de l'environnement." "INFO"
    }
    
    if ($Verbose) {
        $pythonArgs += "--verbose"
    }

    if ($CondaVerboseLevel -gt 0) {
        Write-Log "Niveau de verbosité Conda: $CondaVerboseLevel" "INFO"
        $pythonArgs += "--conda-verbose-level", $CondaVerboseLevel
    }

    Write-Log "Exécution du script environment_manager.py avec les arguments: $($pythonArgs -join ' ')" "DEBUG"

    # Exécution de la commande finale
    & python $pythonArgs
    $exitCode = $LASTEXITCODE

    if ($exitCode -eq 0) {
        Write-Log "Script de gestion de l'environnement exécuté avec succès." "SUCCESS"
    } else {
        Write-Log "Le script de gestion de l'environnement a échoué avec le code: $exitCode." "ERROR"
    }
    exit $exitCode
    
} catch {
    Write-Log "Erreur critique: $($_.Exception.Message)" "ERROR"
    exit 1
}
Write-Log "Environment script finished." "DEBUG"