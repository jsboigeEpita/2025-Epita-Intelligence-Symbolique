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
.\activate_project_env.ps1 -Command "pytest tests/unit tests/functional"

.EXAMPLE
# Affiche la version de python de l'environnement
.\activate_project_env.ps1 -Command "python --version"
#>
param(
    [Parameter(Mandatory=$false, Position=0)]
    [string]$Command = "",

    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$Arguments
)

$ErrorActionPreference = "Stop"

# --- Initialisation de Conda pour les sessions non-interactives ---
# Essaye de trouver la commande 'conda'. Si elle n'est pas dans le PATH,
# le script s'arrêtera, ce qui est le comportement souhaité.
try {
    $condaPath = Get-Command conda.exe | Select-Object -ExpandProperty Source
    Write-Host "[DEBUG] Conda trouvé à l'emplacement: $condaPath" -ForegroundColor DarkGray
    # Exécute le 'hook' de conda pour initialiser l'environnement dans cette session.
    # C'est la méthode recommandée pour rendre 'conda activate' et 'conda run' disponibles
    # dans les scripts et les sessions non-interactives.
    conda.exe shell.powershell hook | Out-String | Invoke-Expression
}
catch {
    Write-Host "[ERREUR FATALE] La commande 'conda' est introuvable." -ForegroundColor Red
    Write-Host "Assurez-vous que Conda (ou Miniconda/Anaconda) est installé et que son répertoire 'Scripts' ou 'condabin' est dans votre PATH." -ForegroundColor Red
    exit 1
}

# Configuration pour la compatibilité des tests et l'import de modules locaux
$env:PYTHONPATH = "$PSScriptRoot;$env:PYTHONPATH"

# Environnement conda cible
$condaEnvName = "projet-is-roo-new"

# Reconstitue la commande complète à partir du paramètre principal et des arguments restants
$fullCommand = if ($Arguments) {
    "$Command " + ($Arguments -join ' ')
} else {
    $Command
}

# Ajout pour les tests : configuration de l'environnement Java
if ($Command -eq "pytest") {
    Write-Host "[INFO] Commande 'pytest' détectée. Configuration de l'environnement de test Java..." -ForegroundColor Cyan
    # Assurez-vous que le script setup_test_env.ps1 existe et est au bon endroit
    if (Test-Path -Path ".\setup_test_env.ps1") {
        . .\setup_test_env.ps1
    } else {
        Write-Host "[WARNING] Le script 'setup_test_env.ps1' est introuvable." -ForegroundColor Yellow
    }
}

# --- Exécution de la commande ---
# La commande ne sera exécutée que si le paramètre -Command a été fourni.
if (-not [string]::IsNullOrWhiteSpace($Command)) {
    # Construit la commande finale en combinant conda run et l'appel au module python
    $moduleName = "project_core.core_from_scripts.environment_manager"
    $commandToExecute = $fullCommand
    $finalCommand = "conda run --no-capture-output -n $condaEnvName python.exe -m $moduleName run `"$commandToExecute`""

    Write-Host "[DEBUG] Calling in Conda Env '$condaEnvName': $finalCommand" -ForegroundColor Gray

    # Exécute la commande finale. Invoke-Expression est utilisé pour évaluer la chaîne complète.
    Invoke-Expression -Command $finalCommand

    # Propage le code de sortie du script python
    $exitCode = $LASTEXITCODE
    exit $exitCode
}
else {
    Write-Host "[INFO] Environnement Conda '$condaEnvName' initialisé. Aucune commande à exécuter." -ForegroundColor Cyan
}