<#
.SYNOPSIS
    Exécute une commande dans l'environnement Conda du projet.
.DESCRIPTION
    Ce script active dynamiquement l'environnement Conda et y exécute
    une commande spécifiée, en gérant le PATH et les dépendances.
.PARAMETER CommandToRun
    La commande à exécuter dans l'environnement Conda.
#>
param(
    [string]$CommandToRun
)

# Récupérer le nom de l'environnement
$EnvName = python -m project_core.core_from_scripts.environment_manager get-env-name
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERREUR] Impossible de récupérer le nom de l'environnement." -ForegroundColor Red
    exit 1
}

Write-Host "[INFO] Exécution de la commande dans l'environnement '$EnvName'..."
conda run -n $EnvName --no-capture-output -- $CommandToRun.Split(' ')