<#
.SYNOPSIS
Wrapper pour exécuter une commande dans l'environnement Conda du projet.

.DESCRIPTION
Ce script exécute une commande dans l'environnement Conda du projet (`projet-is-roo-new`).
Il configure le PYTHONPATH, puis utilise `conda run` pour lancer la commande,
garantissant que tous les dépendances et modules sont correctement résolus.
C'est le point d'entrée privilégié pour toute commande relative au projet.

.EXAMPLE
# Exécute la suite de tests unitaires et fonctionnels
.\activate_project_env.ps1 pytest tests/unit tests/functional

.EXAMPLE
# Affiche la version de python de l'environnement
.\activate_project_env.ps1 python --version
#>
param(
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$CommandToRun
)

$ErrorActionPreference = "Stop"

# --- Initialisation de Conda ---
try {
    # Tente de trouver conda et de l'initialiser pour la session PowerShell en cours.
    $condaPath = Get-Command conda.exe | Select-Object -ExpandProperty Source
    Write-Host "[DEBUG] Conda trouvé: $condaPath" -ForegroundColor DarkGray
    conda.exe shell.powershell hook | Out-String | Invoke-Expression
}
catch {
    Write-Host "[FATAL] 'conda' introuvable. Assurez-vous qu'il est installé et dans le PATH." -ForegroundColor Red
    exit 1
}

# --- Configuration de l'environnement ---
$env:PYTHONPATH = "$PSScriptRoot;$env:PYTHONPATH"
$condaEnvName = "projet-is-roo-new"

# --- Exécution via conda run ---
# Le script agit comme un simple wrapper. Tous les arguments passés
# sont collectés dans $CommandToRun et "splattés" à 'conda run'.
# C'est la méthode la plus fiable pour passer des arguments complexes.
try {
    $condaArgs = @(
        'run',
        '--no-capture-output',
        '-n', $condaEnvName,
        '--cwd', "$PSScriptRoot"
    ) + $CommandToRun

    Write-Host "[DEBUG] Commande exécutée : conda $($condaArgs -join ' ')" -ForegroundColor DarkGray

    # Utilisation de l'opérateur d'appel `&` pour exécuter la commande
    # avec les arguments "splattés". C'est la méthode la plus fiable.
    & conda @condaArgs

    $exitCode = $LASTEXITCODE
    Write-Host "[DEBUG] Commande terminée avec le code de sortie: $exitCode" -ForegroundColor DarkGray
}
catch {
    Write-Host "[FATAL] L'exécution de la commande via conda a échoué." -ForegroundColor Red
    Write-Host $_ -ForegroundColor Red
    $exitCode = 1
}

exit $exitCode
