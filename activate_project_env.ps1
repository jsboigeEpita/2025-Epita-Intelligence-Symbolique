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
Write-Host "[DEBUG][activate_project_env] Python runner script: $pythonRunner" -ForegroundColor Magenta
Write-Host "[DEBUG][activate_project_env] Arguments passés: $args" -ForegroundColor Magenta

# Vérifions quelle version de python est utilisée
Write-Host "[DEBUG][activate_project_env] Utilisation de python.exe trouvé à: $((Get-Command python.exe).Source)" -ForegroundColor Magenta

# Appelle le script Python en lui passant tous les arguments
# reçus par ce script wrapper.
python.exe $pythonRunner $args

# Propage le code de sortie du script python
$exitCode = $LASTEXITCODE
exit $exitCode