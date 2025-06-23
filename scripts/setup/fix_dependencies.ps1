# Script PowerShell pour résoudre les problèmes de dépendances pour les tests

# Vérifier si Python est installé
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCommand) {
    Write-Host "Python n'est pas installé ou n'est pas dans le PATH. Veuillez installer Python et réessayer." -ForegroundColor Red
    exit 1
}

# Chemin vers le script Python
$scriptPath = Join-Path $PSScriptRoot "fix_dependencies.py"
$projectRoot = (Get-Item $PSScriptRoot).Parent.Parent.FullName
$requirementsFilePath = Join-Path $projectRoot "requirements.txt"

# Vérifier si le script Python existe
if (-not (Test-Path $scriptPath)) {
    Write-Host "Le script Python fix_dependencies.py n'existe pas dans le répertoire $PSScriptRoot." -ForegroundColor Red
    exit 1
}

Write-Host "Résolution des problèmes de dépendances pour les tests..." -ForegroundColor Cyan

# Exécuter le script Python
try {
    # On passe le fichier requirements.txt en argument
    python $scriptPath $requirementsFilePath
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Tous les problèmes de dépendances ont été résolus avec succès." -ForegroundColor Green
    } else {
        Write-Host "Certains problèmes de dépendances n'ont pas pu être résolus." -ForegroundColor Red
        exit $LASTEXITCODE
    }
} catch {
    Write-Host "Erreur lors de l'exécution du script Python: $_" -ForegroundColor Red
    exit 1
}

# Toute la logique venv ci-dessous est obsolète car le projet est basé sur Conda.
# Elle est conservée pour l'instant pour éviter de casser d'autres workflows potentiels,
# mais elle devrait être nettoyée.