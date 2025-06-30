<#
.SYNOPSIS
    Exécute un simple test pour vérifier que l'environnement est fonctionnel.
.DESCRIPTION
    Ce script utilise le manager d'environnement pour lancer pytest sur un test spécifique.
.EXAMPLE
    .\scripts\testing\run_simple_test.ps1
#>
$ErrorActionPreference = 'Stop'

# Le chemin est relatif au dossier 'scripts/testing', donc on remonte de deux niveaux pour la racine du projet.
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$EnvironmentManagerModule = "project_core.core_from_scripts.environment_manager"
$TestCommand = "pytest tests/unit/test_simple.py"

try {
    # On s'assure de l'exécuter depuis la racine du projet pour que les imports python fonctionnent
    Set-Location -Path $ProjectRoot

    Write-Host "[INFO] Exécution via le manager: python -m $EnvironmentManagerModule run `"$TestCommand`"" -ForegroundColor Cyan
    python -m $EnvironmentManagerModule run "$TestCommand"
    $exitCode = $LASTEXITCODE
}
catch {
    Write-Host "[ERREUR] L'exécution du test simple via le manager a échoué. $_" -ForegroundColor Red
    $exitCode = 1
}

exit $exitCode