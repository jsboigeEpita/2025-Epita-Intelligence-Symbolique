<#
.SYNOPSIS
Point d'entrée pour exécuter une commande dans l'environnement projet correctement configuré.

.DESCRIPTION
Ce script délègue la gestion de l'environnement et l'exécution de commandes
à un gestionnaire Python centralisé (`project_core/core_from_scripts/environment_manager.py`).
C'est la méthode à privilégier pour garantir que toutes les commandes (tests, scripts, etc.)
s'exécutent avec le bon environnement Conda, le bon PYTHONPATH, et les bonnes variables
d'environnement (comme JAVA_HOME).

.PARAMETER CommandToRun
La commande complète à exécuter (ex: "pytest tests/unit").

.EXAMPLE
# Exécute la suite de tests unitaires
.\activate_project_env.ps1 -CommandToRun "pytest tests/unit"
#>
param(
    [Parameter(Mandatory=$true)]
    [string]$CommandToRun
)

$ErrorActionPreference = "Stop"

# --- DEBUGGING START ---
$debugLogFile = Join-Path $PSScriptRoot "_temp/debug_activate_script.log"
"--- Starting activate_project_env.ps1 at $(Get-Date) ---" | Out-File -FilePath $debugLogFile -Encoding utf8 -Append
Get-Command conda | Out-File -FilePath $debugLogFile -Encoding utf8 -Append
$env:PATH | Out-File -FilePath $debugLogFile -Encoding utf8 -Append
# --- DEBUGGING END ---

# Le module Python est le SEUL responsable de la logique.
$moduleName = "project_core.core_from_scripts.environment_manager"

# Étape 1: Récupérer le nom de l'environnement Conda de manière fiable
Write-Host "[INFO] Récupération du nom de l'environnement Conda depuis .env..." -ForegroundColor Cyan
try {
    $envName = python -m $moduleName get-env-name
    if (-not $envName) {
        throw "Le nom de l'environnement Conda n'a pas pu être déterminé."
    }
    Write-Host "[INFO] Nom de l'environnement Conda détecté : '$envName'" -ForegroundColor Green
}
catch {
    Write-Host "[ERREUR FATALE] Impossible de récupérer le nom de l'environnement Conda." -ForegroundColor Red
    Write-Host $_
    exit 1
}

# Étape 2: Construire la commande finale pour l'exécuter avec `conda run`
# On utilise --no-capture-output pour s'assurer que stdout/stderr du processus enfant
# sont directement streamés, ce qui est crucial pour le logging des tests.
$condaCommand = "conda"
$commandToExecuteInsideEnv = "python -m $moduleName run $CommandToRun"
# Correction: suppression du séparateur '--' qui n'est pas géré correctement par le shell sous-jacent.
$finalCommand = "$condaCommand run -n $envName --no-capture-output --live-stream $commandToExecuteInsideEnv"

Write-Host "[INFO] Délégation au gestionnaire d'environnement Python via Conda..." -ForegroundColor Cyan
Write-Host "[DEBUG] Commande finale: $finalCommand" -ForegroundColor Gray

# Étape 3: Exécution et propagation du code de sortie
try {
    Invoke-Expression -Command $finalCommand
    $exitCode = $LASTEXITCODE
}
catch {
    Write-Host "[ERREUR FATALE] Échec lors de l'exécution de la commande via 'conda run'." -ForegroundColor Red
    Write-Host $_
    $exitCode = 1
}

exit $exitCode
