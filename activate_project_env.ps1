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
    # Le command à exécuter. Privilégié pour les appels programmatiques.
    [string]$CommandToRun = "",

    # Maintenu pour la compatibilité avec l'usage direct en ligne de commande.
    # ex: .\activate_project_env.ps1 pytest tests
    [string]$Command = "",

    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$RemainingArgs
)

$ErrorActionPreference = "Stop"

# --- Initialisation de Conda ---
try {
    $condaPath = Get-Command conda.exe | Select-Object -ExpandProperty Source
    Write-Host "[DEBUG] Conda trouvé: $condaPath" -ForegroundColor DarkGray
    conda.exe shell.powershell hook | Out-String | Invoke-Expression
}
catch {
    Write-Host "[FATAL] 'conda' introuvable. Assurez-vous qu'il est installé et dans le PATH." -ForegroundColor Red
    exit 1
}

# --- Configuration de l'environnement ---
# Ajoute le répertoire du code source et le répertoire racine au PYTHONPATH
$env:PYTHONPATH = "$PSScriptRoot\2.3.3-generation-contre-argument;$PSScriptRoot;$env:PYTHONPATH"
$condaEnvName = "projet-is-new"

# --- Logique de commande ---
$executableCommand = ""
if (-not [string]::IsNullOrWhiteSpace($CommandToRun)) {
    # Priorité 1: Le paramètre nommé -CommandToRun est utilisé.
    $executableCommand = $CommandToRun
}
elseif (-not [string]::IsNullOrWhiteSpace($Command)) {
    # Priorité 2: Des arguments positionnels sont utilisés.
    $executableCommand = ($Command + " " + ($RemainingArgs -join ' ')).Trim()
}

# Si aucune commande n'est passée, le script active simplement l'environnement et se termine.
if ([string]::IsNullOrWhiteSpace($executableCommand)) {
    Write-Host "[INFO] Environnement Conda '$condaEnvName' initialisé pour la session PowerShell actuelle." -ForegroundColor Cyan
    Write-Host "[INFO] Aucune commande fournie, le script se termine. Vous pouvez maintenant exécuter des commandes manuellement." -ForegroundColor Cyan
    conda activate $condaEnvName
    exit 0
}

# --- Exécution via conda run ---
# La commande est directement passée à `conda run`.
# Utilisation de -u pour un output non bufferisé, essentiel pour les logs.
$finalCommand = "conda run --no-capture-output -n $condaEnvName --cwd '$PSScriptRoot' $executableCommand"

Write-Host "[DEBUG] Commande d'exécution : $finalCommand" -ForegroundColor Gray

# Exécution et propagation du code de sortie
Invoke-Expression -Command $finalCommand
$exitCode = $LASTEXITCODE
exit $exitCode
