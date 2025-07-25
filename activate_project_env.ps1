<#
.SYNOPSIS
Point d'entrée pour exécuter une commande de test via le nouvel exécuteur Python.

.DESCRIPTION
Ce script délègue l'exécution de la commande de test au script `scripts/test_executor.py`.
Il sert de simple point d'entrée pour maintenir la compatibilité avec les appels existants.

.PARAMETER CommandToRun
La commande complète à exécuter (ex: "pytest -m jvm_test").

.EXAMPLE
.\activate_project_env.ps1 -CommandToRun "pytest -m jvm_test"
#>
param(
    [Parameter(Mandatory=$true)]
    [string]$CommandToRun
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = $PSScriptRoot
$ExecutorScript = Join-Path $ProjectRoot "scripts/test_executor.py"

Write-Host "[INFO] Délégation de l'exécution au nouveau script : $ExecutorScript" -ForegroundColor Cyan

# Construit la commande pour appeler le script Python
# On passe la commande originale comme un seul argument entre guillemets.
$commandArgs = @(
    $ExecutorScript,
    "--original-command",
    "`"$CommandToRun`""
)

Write-Host "[DEBUG] Commande d'appel : python $($commandArgs -join ' ')" -ForegroundColor Gray

try {
    # Exécute le script Python et attend qu'il se termine.
    # L'utilisation de `&` avec `python` est simple et robuste.
    python $ExecutorScript --original-command $CommandToRun
    
    # Récupère le code de sortie du processus Python
    $exitCode = $LASTEXITCODE
}
catch {
    Write-Host "[ERREUR FATALE] Le script 'test_executor.py' a échoué." -ForegroundColor Red
    Write-Host $_
    # Assigne un code d'erreur non-nul en cas d'échec du script PowerShell lui-même
    $exitCode = 1
}

Write-Host "[INFO] Script terminé avec le code de sortie : $exitCode" -ForegroundColor Cyan
exit $exitCode
