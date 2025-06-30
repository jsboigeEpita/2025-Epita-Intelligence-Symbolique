<#
.SYNOPSIS
Lanceur de tests pytest autonome et robuste.
.DESCRIPTION
Ce script exécute pytest dans l'environnement Conda 'projet-is' en utilisant
la méthode 'conda run', qui est la plus fiable pour les scripts.
Il est conçu pour contourner les scripts d'activation du projet potentiellement instables.
#>
param(
    [string]$TestPath = "tests/integration/workers/test_worker_fol_tweety.py"
)

Write-Host "--- LANCEUR DE TEST AUTONOME (v2) ---"
Write-Host "Utilisation de 'conda run' pour une exécution propre de pytest."
Write-Host "La configuration de pythonpath est maintenant gérée par pyproject.toml."
Write-Host "Test en cours d'exécution : $TestPath"

# La méthode 'conda run' est la manière recommandée pour exécuter une commande
# dans un environnement spécifique à partir d'un script.
conda run -n projet-is python -m pytest $TestPath

$exitCode = $LASTEXITCODE
Write-Host "--- Test terminé avec le code de sortie: $exitCode ---"
exit $exitCode