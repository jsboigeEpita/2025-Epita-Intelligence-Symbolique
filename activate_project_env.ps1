<#
.SYNOPSIS
Wrapper pour exécuter une commande dans l'environnement du projet.

.DESCRIPTION
Ce script est un simple "wrapper" qui délègue toute la logique de
démarrage et d'exécution au script Python multiplateforme `scripts/run_in_env.py`.

.EXAMPLE
# Exécute pytest
.\activate_project_env.ps1 python -m pytest

# Affiche la version de python de l'environnement
.\activate_project_env.ps1 python --version
#>

$ErrorActionPreference = "Stop"

# Détermine le chemin vers le script Python à exécuter
# Syntaxe alternative pour Join-Path pour essayer de contourner un problème de parsing.
$childPath = "scripts\run_in_env.py"
$pythonRunner = Join-Path -Path $PSScriptRoot -ChildPath $childPath

# Affiche la commande qui va être exécutée pour le débogage
# Write-Host "[DEBUG] Calling: python $pythonRunner $args" -ForegroundColor Gray

# Appelle le script Python en lui passant tous les arguments
# reçus par ce script wrapper.
python.exe $pythonRunner $args

# Propage le code de sortie du script python
$exitCode = $LASTEXITCODE
exit $exitCode