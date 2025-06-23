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
    [switch]$EnableVerboseLogging = $false,
    [switch]$ForceReinstall = $false,
    [int]$CondaVerboseLevel = 0,
    [switch]$LaunchWebApp = $false,
    [switch]$DebugMode = $false,
    [string]$CommandOutputFile = $null
)

# Fonction de logging simple
function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logLine = "[$timestamp] [$Level] $Message"
    # Écrire sur le flux d'erreur pour ne pas interférer avec la sortie de commande
    $Host.UI.WriteErrorLine($logLine)
}

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot

try {
    # La logique complexe de détection d'environnement est supprimée au profit
    # d'une exécution directe via `conda run`, qui est plus robuste.
    Write-Log "Script d'activation refactorisé. Utilisation de 'conda run' privilégiée."

    # Injection des variables d'environnement nécessaires aux tests
    $env:OPENAI_API_KEY = "dummy_key_for_testing_purposes"
    Write-Log "Variable injectée: OPENAI_API_KEY" "DEBUG"

    # --- PORTAGE DU CORRECTIF PYTHONPATH DEPUIS L'ANCIENNE BRANCHE ---
    # Assure que les imports python fonctionnent correctement depuis la racine
    $env:PYTHONPATH = $ProjectRoot
    Write-Log "Variable injectée: PYTHONPATH=$($env:PYTHONPATH)" "DEBUG"

    # Contournement pour le conflit OpenMP (OMP: Error #15)
    $env:KMP_DUPLICATE_LIB_OK = "TRUE"
    Write-Log "Variable injectée: KMP_DUPLICATE_LIB_OK" "DEBUG"

    # Si une commande doit être écrite dans un fichier de sortie (pour `run_tests.ps1`)
    if ($CommandOutputFile) {
         # 'conda run' est la méthode moderne et robuste.
         # --no-capture-output permet de voir la sortie de la commande en temps réel.
        $CondaCommand = "conda run --no-capture-output -n projet-is $CommandToRun"
        Write-Log "Génération de la commande pour le fichier de sortie: $CondaCommand"
        Set-Content -Path $CommandOutputFile -Value $CondaCommand
    }
    # Si aucune sortie de fichier n'est demandée, mais qu'une commande est fournie, on l'exécute directement
    elseif ($CommandToRun) {
        $CondaCommand = "conda run --no-capture-output -n projet-is $CommandToRun"
        Write-Log "Exécution directe de la commande: $CondaCommand"
        Invoke-Expression -Command $CondaCommand
        $exitCode = $LASTEXITCODE
        if ($exitCode -ne 0) {
            Write-Log "La commande a échoué avec le code de sortie: $exitCode" "ERROR"
        }
        exit $exitCode
    }
    else {
        Write-Log "Activation simple terminée. Aucun fichier de sortie ou commande à exécuter."
    }
}
catch {
    Write-Log "Erreur critique dans le script $($MyInvocation.MyCommand.Name):" "ERROR"
    $errorRecord = $_
    $line = $errorRecord.InvocationInfo.ScriptLineNumber
    $scriptName = $errorRecord.InvocationInfo.ScriptName
    Write-Log "Message: $($_.Exception.Message) à $scriptName (Ligne: $line)" "ERROR"
    exit 1
}