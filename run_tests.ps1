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

param(
    [string]$TestPath = ""
)

$ProjectRoot = $PSScriptRoot
$ActivationScript = Join-Path $ProjectRoot "activate_project_env.ps1"
$PytestCommand = "python -m pytest $TestPath"

if (-not (Test-Path $ActivationScript)) {
    Write-Host "[ERREUR] Le script d'activation '$ActivationScript' est introuvable." -ForegroundColor Red
    exit 1
}

Write-Host "[INFO] Lancement des tests via $ActivationScript..." -ForegroundColor Cyan

& $ActivationScript -CommandToRun $PytestCommand
exit $LASTEXITCODE