<#
.SYNOPSIS
    Exécute une commande spécifiée dans l'environnement Conda du projet.
.DESCRIPTION
    Ce script sert de wrapper pour lancer une commande via le manager d'environnement
    centralisé, qui gère l'activation et l'exécution dans le bon environnement Conda.
.PARAMETER Command
    La commande à exécuter.
.EXAMPLE
    .\run_in_env.ps1 -Command "python --version"
#>
param(
    [Parameter(Mandatory=$true)]
    [string]$Command
)

$ErrorActionPreference = 'Stop'
$EnvironmentManagerModule = "project_core.core_from_scripts.environment_manager"

try {
    Write-Host "[INFO] Exécution via le manager: python -m $EnvironmentManagerModule run `"$Command`"" -ForegroundColor Cyan
    python -m $EnvironmentManagerModule run "$Command"
    $exitCode = $LASTEXITCODE
}
catch {
    Write-Host "[ERREUR] L'exécution de la commande via le manager a échoué. $_" -ForegroundColor Red
    $exitCode = 1
}

exit $exitCode