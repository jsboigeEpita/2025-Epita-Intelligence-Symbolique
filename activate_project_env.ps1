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
    [Parameter(Mandatory=$true, ValueFromRemainingArguments=$true)]
    [string[]]$CommandArgs
)

$ErrorActionPreference = "Stop"

# --- Initialisation de Conda pour les sessions non-interactives ---
# Essaye de trouver la commande 'conda'. Si elle n'est pas dans le PATH,
# le script s'arrêtera, ce qui est le comportement souhaité.
try {
    $condaExecutable = Get-Command conda.exe | Select-Object -ExpandProperty Source
    Write-Host "[DEBUG] Conda trouvé à l'emplacement: $condaExecutable" -ForegroundColor DarkGray
    # L'initialisation via 'hook' est supprimée car elle est instable dans les sessions 'pwsh -c'.
    # On se repose directement sur 'conda run', qui est conçu pour fonctionner sans activation préalable.
}
catch {
    Write-Host "[ERREUR FATALE] La commande 'conda' est introuvable." -ForegroundColor Red
    Write-Host "Assurez-vous que Conda (ou Miniconda/Anaconda) est installé et que son répertoire 'Scripts' ou 'condabin' est dans votre PATH." -ForegroundColor Red
    exit 1
}

# Configuration pour la compatibilité des tests et l'import de modules locaux
$env:PYTHONPATH = "$PSScriptRoot;$env:PYTHONPATH"

# Environnement conda cible
$condaEnvName = "projet-is"

# Construit la liste d'arguments pour `conda run`.
$condaArgs = @("run", "--no-capture-output", "-n", $condaEnvName) + $CommandArgs

Write-Host "[DEBUG] Calling Conda with: & '$condaExecutable' $($condaArgs -join ' ')" -ForegroundColor Gray

# Exécute la commande directement en utilisant l'opérateur d'appel `&`.
# C'est la méthode la plus propre et la plus robuste, qui évite Invoke-Expression et le hook.
& $condaExecutable $condaArgs

# Propage le code de sortie du script python
$exitCode = $LASTEXITCODE
exit $exitCode
