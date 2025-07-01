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
    [Parameter(Mandatory=$false, Position=0)]
    [string]$Command,

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
$env:PYTHONPATH = "$PSScriptRoot;$env:PYTHONPATH"
$condaEnvName = "projet-is-new"

# --- Logique de commande ---
# Concatène la commande et ses arguments en une seule chaîne.
$fullCommand = ($Command + " " + ($RemainingArgs -join ' ')).Trim()

# Si aucune commande n'est passée, le script active simplement l'environnement et se termine.
if ([string]::IsNullOrWhiteSpace($fullCommand)) {
    Write-Host "[INFO] Environnement Conda '$condaEnvName' initialisé pour la session PowerShell actuelle." -ForegroundColor Cyan
    Write-Host "[INFO] Aucune commande fournie, le script se termine. Vous pouvez maintenant exécuter des commandes manuellement." -ForegroundColor Cyan
    conda activate $condaEnvName
    exit 0
}

# --- Exécution via conda run ---
# La commande est directement passée à `conda run`.
# Utilisation de -u pour un output non bufferisé, essentiel pour les logs.
$finalCommand = "conda run --no-capture-output -n $condaEnvName --cwd '$PSScriptRoot' $fullCommand"

Write-Host "[DEBUG] Commande d'exécution : $finalCommand" -ForegroundColor Gray

# Exécution et propagation du code de sortie
Invoke-Expression -Command $finalCommand
$exitCode = $LASTEXITCODE
exit $exitCode