# Charger les variables d'environnement du projet
Write-Host "Chargement des variables d'environnement via .\activate_project_env.ps1"
.\activate_project_env.ps1 
# Ce script devrait définir $env:CONDA_ENV_NAME.

# Définir les variables spécifiques au test APRÈS le chargement initial
$env:PYTHONIOENCODING = "utf-8"
$env:USE_REAL_JPYPE = "true" # Mettre à true pour tester avec la vraie JVM

# Récupérer le nom de l'environnement Conda
$condaEnvName = $env:CONDA_ENV_NAME
if (-not $condaEnvName) {
    $condaEnvName = "projet-is" 
    Write-Warning "CONDA_ENV_NAME n'a pas été définie explicitement. Utilisation de la valeur par défaut: '$condaEnvName'"
} else {
    Write-Host "Utilisation de CONDA_ENV_NAME provenant de l'environnement: '$condaEnvName'"
}

Write-Host "Configuration pour l'exécution des tests:"
Write-Host "PYTHONPATH: $env:PYTHONPATH" # Devrait être géré par conda run
Write-Host "JAVA_HOME: $env:JAVA_HOME"
Write-Host "USE_REAL_JPYPE: $env:USE_REAL_JPYPE"

# Chemin vers le fichier de test
$testFilePath = "tests\agents\core\logic\test_tweety_bridge.py"

# Construire la commande pour exécuter pytest directement via conda run
# conda run exécute la commande spécifiée dans l'environnement Conda donné.
# --no-capture-output est utile pour voir la sortie en direct.
# -vv pour une verbosité maximale de pytest.
$pytestCommand = "python -m pytest -vv --color=yes '$testFilePath'"
$fullCondaRunCommand = "conda run -n '$condaEnvName' --no-capture-output $pytestCommand"

Write-Host "Tentative d'exécution de pytest via conda run: $fullCondaRunCommand"
Invoke-Expression -Command $fullCondaRunCommand

# Si pytest n'est pas directement utilisé et que Pester est requis,
# il faudrait s'assurer que Pester est invoqué *après* que l'environnement Conda
# est pleinement et correctement activé dans la session PowerShell.
# Les tentatives précédentes montrent que c'est difficile à faire de manière fiable
# via des scripts appelant d'autres scripts d'activation.