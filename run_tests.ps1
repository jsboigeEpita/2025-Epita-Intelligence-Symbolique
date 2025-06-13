<#
.SYNOPSIS
Lance les tests du projet en utilisant le m&#233;canisme d'activation d'environnement centralis&#233;.

.DESCRIPTION
Ce script est un raccourci pour ex&#233;cuter tous les tests (unitaires et d'int&#233;gration)
via le script `setup_project_env.ps1`, qui garantit que l'environnement Conda
'projet-is' est correctement activ&#233; avant de lancer pytest.

.EXAMPLE
.\run_tests.ps1
#>

param()

$ProjectRoot = $PSScriptRoot
$SetupScript = Join-Path $ProjectRoot "setup_project_env.ps1"
$PytestCommand = "python -m pytest"

if (-not (Test-Path $SetupScript)) {
    Write-Host "[ERREUR] Le script de configuration '$SetupScript' est introuvable." -ForegroundColor Red
    exit 1
}

Write-Host "[INFO] Lancement des tests via $SetupScript..." -ForegroundColor Cyan

& $SetupScript -CommandToRun $PytestCommand
exit $LASTEXITCODE