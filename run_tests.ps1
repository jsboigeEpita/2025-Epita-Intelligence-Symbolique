<#
.SYNOPSIS
Wrapper pour lancer des tests via pytest en utilisant l'environnement du projet.

.DESCRIPTION
Ce script agit comme un simple transmetteur d'arguments vers pytest.
Il utilise `activate_project_env.ps1` pour garantir que l'environnement Conda
est correctement activé, puis passe tous les arguments qu'il reçoit
directement à la commande `pytest`.

C'est la méthode recommandée pour exécuter tous types de tests, en
permettant une flexibilité maximale pour spécifier des fichiers,
des marqueurs ou toute autre option de pytest.

.EXAMPLE
# Exécute tous les tests
.\run_tests.ps1

.EXAMPLE
# Exécute un fichier de test spécifique en mode verbeux
.\run_tests.ps1 -v tests/integration/test_argument_analyzer.py

.EXAMPLE
# Exécute tous les tests marqués comme "real_llm"
.\run_tests.ps1 -m "real_llm"

.EXAMPLE
# Exécute un test spécifique par son nom dans un fichier
.\run_tests.ps1 "tests/integration/test_analysis_service.py::TestAnalysisService::test_analyze_complex_argumentative_text"
#>
param(
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$PytestArgs
)

$ErrorActionPreference = 'Stop'

# Le script d'activation est le point d'entrée pour toutes les commandes
# qui doivent s'exécuter dans l'environnement du projet.
$activationScript = Join-Path $PSScriptRoot "activate_project_env.ps1"

if (-not (Test-Path $activationScript)) {
    Write-Host "[FATAL] Script d'activation '$activationScript' introuvable!" -ForegroundColor Red
    exit 1
}

try {
    # Construit la liste d'arguments à passer au script d'activation.
    # La commande à exécuter est `python -m pytest`, suivie de tous
    # les arguments passés à run_tests.ps1.
    $argumentsToForward = @("python", "-m", "pytest") + $PytestArgs
    
    Write-Host "[DEBUG] Exécution: $activationScript $($argumentsToForward -join ' ')" -ForegroundColor DarkGray
    
    # Exécute le script d'activation et lui passe la commande et les arguments
    # de pytest. L'opérateur de "splatting" @ est crucial ici.
    & $activationScript @argumentsToForward
    
    $exitCode = $LASTEXITCODE
    Write-Host "[INFO] Commande de test terminée avec le code de sortie: $exitCode" -ForegroundColor Cyan
}
catch {
    Write-Host "[FATAL] Une erreur est survenue lors de l'exécution des tests." -ForegroundColor Red
    Write-Host $_ -ForegroundColor Red
    $exitCode = 1
}

exit $exitCode
