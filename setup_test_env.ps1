# Script PowerShell pour configurer un environnement de test pour le projet argumentation_analysis

function Write-Step {
    param (
        [string]$Message
    )
    
    Write-Host "`n" -NoNewline
    Write-Host ("=" * 80) -ForegroundColor Cyan
    Write-Host "  $Message" -ForegroundColor Cyan
    Write-Host ("=" * 80) -ForegroundColor Cyan
}

# Vérifier le répertoire courant
$projectDir = Get-Location
Write-Step "Configuration de l'environnement de test dans $projectDir"

# Vérifier si un environnement virtuel existe déjà
$venvDir = Join-Path -Path $projectDir -ChildPath "venv_test"
if (Test-Path $venvDir) {
    Write-Step "Suppression de l'ancien environnement virtuel"
    Remove-Item -Path $venvDir -Recurse -Force
}

# Créer un nouvel environnement virtuel
Write-Step "Création d'un nouvel environnement virtuel"
python -m venv venv_test
if (-not $?) {
    Write-Host "Échec de la création de l'environnement virtuel." -ForegroundColor Red
    exit 1
}

# Activer l'environnement virtuel
Write-Step "Activation de l'environnement virtuel"
$activateScript = Join-Path -Path $venvDir -ChildPath "Scripts\Activate.ps1"
try {
    & $activateScript
} catch {
    Write-Host "Échec de l'activation de l'environnement virtuel." -ForegroundColor Red
    Write-Host "Erreur: $_" -ForegroundColor Red
    exit 1
}

# Mettre à jour pip
Write-Step "Mise à jour de pip"
python -m pip install --upgrade pip
if (-not $?) {
    Write-Host "Échec de la mise à jour de pip." -ForegroundColor Red
    exit 1
}

# Installer les dépendances de test
Write-Step "Installation des dépendances de test"
$requirementsFile = Join-Path -Path $projectDir -ChildPath "requirements-test.txt"
python -m pip install -r $requirementsFile
if (-not $?) {
    Write-Host "Échec de l'installation des dépendances de test." -ForegroundColor Red
    exit 1
}

# Installer le package en mode développement
Write-Step "Installation du package en mode développement"
python -m pip install -e .
if (-not $?) {
    Write-Host "Échec de l'installation du package en mode développement." -ForegroundColor Red
    exit 1
}

# Vérifier les importations problématiques
Write-Step "Vérification des importations problématiques"

# Vérifier numpy
Write-Host "Vérification de numpy..." -ForegroundColor Yellow
python -c "import numpy; print('Numpy importé avec succès:', numpy.__version__)"

# Vérifier jpype
Write-Host "Vérification de jpype..." -ForegroundColor Yellow
python -c "import jpype; print('JPype importé avec succès:', jpype.__version__)"

# Vérifier cffi
Write-Host "Vérification de cffi..." -ForegroundColor Yellow
python -c "import cffi; print('CFFI importé avec succès:', cffi.__version__)"

# Vérifier cryptography
Write-Host "Vérification de cryptography..." -ForegroundColor Yellow
python -c "import cryptography; print('Cryptography importé avec succès:', cryptography.__version__)"

# Exécuter un test simple pour vérifier l'environnement
Write-Step "Exécution d'un test simple pour vérifier l'environnement"
$testFile = "argumentation_analysis/tests/test_async_communication_fixed.py"
python -m unittest $testFile

if ($?) {
    Write-Step "Configuration de l'environnement de test terminée avec succès"
    Write-Host "`nPour activer l'environnement de test dans une nouvelle session:" -ForegroundColor Green
    Write-Host "    .\venv_test\Scripts\Activate.ps1" -ForegroundColor Green
    
    Write-Host "`nPour exécuter les tests:" -ForegroundColor Green
    Write-Host '    python -m unittest discover -s argumentation_analysis/tests -p "test_*.py" -v' -ForegroundColor Green
} else {
    Write-Step "Des problèmes subsistent dans l'environnement de test"
}