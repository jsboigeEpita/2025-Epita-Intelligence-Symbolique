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
.\activate_project_env.ps1 pytest tests/unit
#>
param(
    [string]$CommandToRun,
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$RemainingArgs
)

$ErrorActionPreference = "Stop"

# --- DEBUGGING START ---
$debugLogFile = Join-Path $PSScriptRoot "_temp/debug_activate_script.log"
"--- Starting activate_project_env.ps1 at $(Get-Date) ---" | Out-File -FilePath $debugLogFile -Encoding utf8 -Append
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

# Étape 2: Construire la commande à exécuter
$fullCommand = ($CommandToRun + " " + ($RemainingArgs -join ' ')).Trim()
if (-not $fullCommand) {
    Write-Host "[ERREUR] Aucune commande fournie." -ForegroundColor Red
    exit 1
}

# Étape 3: Exécution via Start-Process pour plus de robustesse
Write-Host "[INFO] Délégation au gestionnaire d'environnement Python via Conda..." -ForegroundColor Cyan

# On passe la commande complète au script python qui saura la parser.
# Les guillemets autour de "$fullCommand" sont cruciaux pour les commandes avec espaces
$commandToExecuteInsideEnv = "python -m $moduleName run `"$fullCommand`""
$argumentList = "run -n $envName --no-capture-output --live-stream -- $commandToExecuteInsideEnv"

Write-Host "[DEBUG] Commande d'exécution via Start-Process :" -ForegroundColor Gray
Write-Host "conda.exe $argumentList" -ForegroundColor Gray

try {
    $condaExecutable = Get-Command conda.exe | Select-Object -ExpandProperty Source
    $process = Start-Process -FilePath $condaExecutable -ArgumentList $argumentList -Wait -PassThru -NoNewWindow
    $exitCode = $process.ExitCode
}
catch {
    Write-Host "[FATAL] L'exécution de la commande via conda a échoué." -ForegroundColor Red
    Write-Host $_ -ForegroundColor Red
    $exitCode = 1
}

exit $exitCode
