<#
.SYNOPSIS
Point d'entrée pour exécuter une commande dans l'environnement projet correctement configuré.

.DESCRIPTION
Ce script exécute une commande donnée directement dans l'environnement Conda du projet,
en s'assurant que les variables d'environnement actuelles sont propagées.

.PARAMETER CommandToRun
La commande complète à exécuter (ex: "pytest tests/unit").

.PARAMETER RemainingArgs
Arguments supplémentaires pour la commande.

.EXAMPLE
# Exécute la suite de tests unitaires
.\activate_project_env.ps1 "pytest tests/unit"
#>
param(
    [string]$CommandToRun,
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$RemainingArgs
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = $PSScriptRoot

# Le module Python est le SEUL responsable de la logique pour obtenir le nom de l'env.
$moduleName = "project_core.core_from_scripts.environment_manager"

# Étape 1: Récupérer le nom de l'environnement Conda
Write-Host "[INFO] Récupération du nom de l'environnement Conda..." -ForegroundColor Cyan
try {
    # On exécute python directement, car conda n'est peut-être pas encore activé.
    # Le shebang ou le PATH système devrait trouver une version de Python.
    $envName = python -m $moduleName get-env-name
    if (-not $envName) {
        throw "Le nom de l'environnement Conda n'a pas pu être déterminé."
    }
    Write-Host "[INFO] Nom de l'environnement Conda détecté : '$envName'" -ForegroundColor Green
}
catch {
    Write-Host "[ERREUR FATALE] Impossible de récupérer le nom de l'environnement Conda. Assurez-vous que Python est dans le PATH." -ForegroundColor Red
    Write-Host $_
    exit 1
}

# Étape 2: Construire la commande à exécuter
$fullCommand = ($CommandToRun + " " + ($RemainingArgs -join ' ')).Trim()
if (-not $fullCommand) {
    Write-Host "[ERREUR] Aucune commande fournie." -ForegroundColor Red
    exit 1
}

# Étape 3: Exécution via 'conda run' qui propage l'environnement.
# C'est la méthode la plus robuste pour s'assurer que les variables du shell
# (y compris celles chargées depuis .env.test) sont disponibles pour la commande.
Write-Host "[INFO] Délégation de l'exécution à 'conda run'..." -ForegroundColor Cyan
Write-Host "[INFO] Commande : $fullCommand" -ForegroundColor Gray

try {
    # --no-capture-output et --live-stream sont essentiels pour voir les logs en temps réel.
    # Le '&' de PowerShell est utilisé pour exécuter la commande.
    & conda run -n $envName --no-capture-output --live-stream pwsh -Command $fullCommand
    $exitCode = $LASTEXITCODE
}
catch {
    Write-Host "[FATAL] L'exécution de la commande via 'conda run' a échoué." -ForegroundColor Red
    Write-Host $_ -ForegroundColor Red
    $exitCode = 1
}

Write-Host "[INFO] Script terminé avec le code de sortie : $exitCode" -ForegroundColor Cyan
exit $exitCode
