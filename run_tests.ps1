<#
.SYNOPSIS
Lance la suite de tests du projet avec pytest.

.DESCRIPTION
Ce script est le point d'entrée unique pour exécuter les tests.
Il utilise `activate_project_env.ps1` pour s'assurer que les tests
sont exécutés dans le bon environnement Conda (`projet-is-roo-new`) et
avec le `PYTHONPATH` correctement configuré.

Toute la sortie est redirigée pour être capturée par les logs, et les
erreurs sont gérées de manière centralisée.

.PARAMETER TestArgs
Accepte une chaîne de caractères contenant tous les arguments à passer
directement à pytest. Cela permet de cibler des tests spécifiques ou
d'utiliser des options pytest.

.EXAMPLE
# Exécute tous les tests
.\run_tests.ps1

.EXAMPLE
# Exécute un fichier de test spécifique
.\run_tests.ps1 "tests/agents/core/logic/test_tweety_bridge.py"

.EXAMPLE
# Exécute un test spécifique avec l'option -s pour voir les prints
.\run_tests.ps1 "tests/agents/core/logic/test_tweety_bridge.py -s"
#>
param(
    [string]$TestArgs
)

$ErrorActionPreference = "Stop"

# Le chemin vers le script d'activation
$activatorPath = Join-Path -Path $PSScriptRoot -ChildPath "activate_project_env.ps1"

# La commande de base est 'pytest'
$command = "pytest"

# Ajoute les arguments supplémentaires s'ils sont fournis
if (-not [string]::IsNullOrEmpty($TestArgs)) {
    $command = "$command $TestArgs"
}

# Construit la commande finale à exécuter
$fullCommand = "& `"$activatorPath`" $command"

Write-Host "Executing: $fullCommand" -ForegroundColor Cyan

# Exécute la commande de test et capture le code de sortie
try {
    Invoke-Expression -Command $fullCommand
}
catch {
    Write-Host "Une erreur est survenue lors de l'exécution des tests." -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    # Propage un code d'erreur non-nul
    exit 1
}

# Propage le code de sortie de pytest
$exitCode = $LASTEXITCODE
exit $exitCode
