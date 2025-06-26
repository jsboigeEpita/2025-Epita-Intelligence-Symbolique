<#
.SYNOPSIS
Wrapper pour exécuter une commande dans l'environnement du projet.

.DESCRIPTION
Ce script est un simple "wrapper" qui délègue toute la logique de
démarrage et d'exécution au script Python multiplateforme `scripts/run_in_env.py`.

.EXAMPLE
# Exécute pytest
.\activate_project_env.ps1 python -m pytest

.EXAMPLE
# Affiche la version de python de l'environnement
.\activate_project_env.ps1 python --version
#>
param(
    [Parameter(Mandatory=$false, Position=0)]
    [string]$CommandToRun,
    
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$RemainingArgs
)

$ErrorActionPreference = "Stop"

# Détermine le chemin vers le script Python à exécuter
$childPath = "scripts\run_in_env.py"
$pythonRunner = Join-Path -Path $PSScriptRoot -ChildPath $childPath

# Détermine la commande finale à exécuter
$finalArgs = if ($PSBoundParameters.ContainsKey('CommandToRun')) {
    # Si -CommandToRun est utilisé explicitement, on prend sa valeur
    $CommandToRun
} else {
    # Sinon, on reconstruit la commande à partir de tous les arguments passés
    # Cela inclut le premier argument non nommé s'il n'y a pas de -CommandToRun
    $($CommandToRun) + $RemainingArgs -join ' '
}

$finalCommand = "python.exe `"$pythonRunner`" $finalArgs"

# Write-Host "[DEBUG] Calling: $finalCommand" -ForegroundColor Gray

# Appelle le script Python avec les arguments traités
Invoke-Expression -Command $finalCommand

# Propage le code de sortie du script python
$exitCode = $LASTEXITCODE
exit $exitCode