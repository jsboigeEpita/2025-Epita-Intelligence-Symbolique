# Script PowerShell pour résoudre les problèmes de dépendances pour les tests

# Vérifier si Python est installé
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCommand) {
    Write-Host "Python n'est pas installé ou n'est pas dans le PATH. Veuillez installer Python et réessayer." -ForegroundColor Red
    exit 1
}

# Chemin vers le script Python
$scriptPath = Join-Path $PSScriptRoot "fix_dependencies.py"

# Vérifier si le script Python existe
if (-not (Test-Path $scriptPath)) {
    Write-Host "Le script Python fix_dependencies.py n'existe pas dans le répertoire $PSScriptRoot." -ForegroundColor Red
    exit 1
}

Write-Host "Résolution des problèmes de dépendances pour les tests..." -ForegroundColor Cyan

# Exécuter le script Python
try {
    python $scriptPath
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

# Créer un environnement virtuel pour les tests si nécessaire
$venvPath = Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) "venv_test"
if (-not (Test-Path $venvPath)) {
    Write-Host "Création d'un environnement virtuel pour les tests..." -ForegroundColor Cyan
    try {
        python -m venv $venvPath
        Write-Host "Environnement virtuel créé avec succès." -ForegroundColor Green
    } catch {
        Write-Host "Erreur lors de la création de l'environnement virtuel: $_" -ForegroundColor Red
        exit 1
    }
}

# Activer l'environnement virtuel et installer les dépendances
Write-Host "Activation de l'environnement virtuel et installation des dépendances..." -ForegroundColor Cyan
$activateScript = Join-Path $venvPath "Scripts\Activate.ps1"
if (Test-Path $activateScript) {
    try {
        & $activateScript
        
        # Installer les dépendances de test
        $requirementsPath = Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) "requirements-test.txt"
        if (Test-Path $requirementsPath) {
            python -m pip install -r $requirementsPath
            Write-Host "Dépendances de test installées avec succès." -ForegroundColor Green
        } else {
            Write-Host "Le fichier requirements-test.txt n'existe pas." -ForegroundColor Yellow
        }
        
        # Exécuter à nouveau le script de résolution des dépendances dans l'environnement virtuel
        python $scriptPath
        
        Write-Host "Configuration de l'environnement de test terminée." -ForegroundColor Green
    } catch {
        Write-Host "Erreur lors de l'activation de l'environnement virtuel ou de l'installation des dépendances: $_" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "Le script d'activation de l'environnement virtuel n'existe pas." -ForegroundColor Red
    exit 1
}

Write-Host "Vous pouvez maintenant exécuter les tests avec la commande:" -ForegroundColor Cyan
Write-Host "cd $(Split-Path -Parent (Split-Path -Parent $PSScriptRoot))" -ForegroundColor Yellow
Write-Host ".\venv_test\Scripts\activate" -ForegroundColor Yellow
Write-Host "pytest" -ForegroundColor Yellow