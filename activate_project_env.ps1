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
    [string]$CommandToRun,

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
# Concatène la commande et ses arguments en une seule chaîne.
# --- Logique de commande ---
$fullCommand = ($CommandToRun + " " + ($RemainingArgs -join ' ')).Trim()

# --- Exécution via conda run ---
# Utilisation de Start-Process pour un appel plus stable que Invoke-Expression
$argumentList = "run --no-capture-output -n $condaEnvName --cwd `"$PSScriptRoot`" $fullCommand"

Write-Host "[DEBUG] Commande d'exécution via Start-Process :" -ForegroundColor Gray
Write-Host "conda.exe $argumentList" -ForegroundColor Gray

try {
    # On récupère le chemin complet de conda.exe pour être sûr
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
