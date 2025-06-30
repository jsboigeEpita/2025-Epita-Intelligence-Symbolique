<#
.SYNOPSIS
Wrapper pour exécuter une commande dans l'environnement Conda du projet.

.DESCRIPTION
Ce script délègue l'exécution de commandes au gestionnaire d'environnement Python
`project_core/core_from_scripts/environment_manager.py`.
Il assure que les commandes sont lancées dans le bon environnement Conda (`epita_symbolic_ai`)
avec la méthode 'conda run', qui est la plus robuste.

.EXAMPLE
# Exécute pytest pour un test spécifique
.\activate_project_env.ps1 pytest tests/integration/some_test.py

.EXAMPLE
# Affiche la version de python de l'environnement
.\activate_project_env.ps1 python --version
#>
param(
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$CommandAndArgs
)

$ErrorActionPreference = "Stop"

# Configuration pour la compatibilité des tests et l'import de modules locaux
$env:PYTHONPATH = "$PSScriptRoot;$env:PYTHONPATH"

# Chemin vers le nouveau gestionnaire d'environnement
$childPath = "project_core\core_from_scripts\environment_manager.py"
$pythonRunner = Join-Path -Path $PSScriptRoot -ChildPath $childPath

# Environnement conda cible (corrigé pour correspondre aux attentes des tests)
$condaEnvName = "projet-is-roo-new"

# --- Logique de Commande ---

# Si aucune commande n'est fournie, on exécute pytest par défaut.
# Sinon, on prend la commande passée en argument.
$commandToExecute = ""
if ($CommandAndArgs.Count -eq 0) {
    Write-Host "[INFO] Aucune commande spécifiée. Lancement de pytest par défaut." -ForegroundColor Yellow
    # La commande par défaut pour exécuter une suite de tests pertinente.
    $commandToExecute = "pytest -s -vv tests/unit tests/functional"
} else {
    $commandToExecute = $CommandAndArgs -join ' '
}


# Construit la commande finale pour appeler le nouveau gestionnaire d'environnement.
$finalCommand = "python.exe `"$pythonRunner`" run `"$commandToExecute`""

Write-Host "[DEBUG] Calling: $finalCommand" -ForegroundColor Gray

# Appelle le script Python avec les arguments traités.
# la commande est déjà dans le bon environnement grâce au script `run_tests.ps1` ou équivalent
Invoke-Expression -Command $finalCommand

# Propage le code de sortie du script python
$exitCode = $LASTEXITCODE
exit $exitCode