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

    # Si une commande est fournie, la décomposer et l'exécuter séquentiellement
    # Chaque commande sera passée à environment_manager.py pour être exécutée DANS l'environnement activé.
    if ($CommandToRun) {
        Write-Log "Commandes à exécuter séquentiellement: $CommandToRun"
        $commands = $CommandToRun.Split(';') | ForEach-Object {$_.Trim()}
        
        foreach ($cmd in $commands) {
            if (-not [string]::IsNullOrWhiteSpace($cmd)) {
                Write-Log "Exécution de la sous-commande: $cmd"
                $pythonExecArgs = @("python", $pythonScriptPath, "--command", $cmd)
                
                # Exécution via le module Python
                & $pythonExecArgs[0] $pythonExecArgs[1..($pythonExecArgs.Length-1)]
                $exitCode = $LASTEXITCODE
                
                if ($exitCode -ne 0) {
                    Write-Log "Échec de la sous-commande '$cmd' (Code: $exitCode)" "ERROR"
                    exit $exitCode # Arrêter si une sous-commande échoue
                }
                Write-Log "Sous-commande '$cmd' exécutée avec succès." "SUCCESS"
            }
        }
        Write-Log "Toutes les sous-commandes exécutées." "SUCCESS"
        exit 0 # Succès global si toutes les sous-commandes ont réussi
    } else {
        # Si aucune commande n'est fournie, juste activer l'environnement
        Write-Log "Activation simple de l'environnement (pas de commande à exécuter)."
        $pythonActivateOnlyArgs = @("python", $pythonScriptPath)
        & $pythonActivateOnlyArgs[0] $pythonActivateOnlyArgs[1..($pythonActivateOnlyArgs.Length-1)]
        $exitCode = $LASTEXITCODE
        if ($exitCode -eq 0) {
            Write-Log "Environnement activé avec succès (sans commande)." "SUCCESS"
        } else {
            Write-Log "Échec de l'activation de l'environnement (sans commande) (Code: $exitCode)." "ERROR"
        }
        exit $exitCode
    }
    
} catch {
    Write-Log "Erreur critique: $($_.Exception.Message)" "ERROR"
    exit 1
}