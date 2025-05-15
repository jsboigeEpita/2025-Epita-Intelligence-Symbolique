# Script PowerShell pour exécuter les tests unitaires
# Auteur: Roo
# Date: 30/04/2025

# Définir l'encodage en UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Afficher l'en-tête
Write-Host "=== Tests Unitaires - Projet d'Analyse Argumentative ===" -ForegroundColor Cyan
Write-Host ""

# Ajouter le répertoire racine du projet au chemin Python
$currentDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$parentDir = Split-Path -Parent $currentDir
$rootDir = Split-Path -Parent $parentDir
$env:PYTHONPATH = $rootDir

# Vérifier si les JARs de test sont présents
$testLibsDir = Join-Path -Path $currentDir -ChildPath "resources\libs"
$testJarsExist = Test-Path -Path $testLibsDir -PathType Container
$testJarsCount = 0
if ($testJarsExist) {
    $testJarsCount = (Get-ChildItem -Path $testLibsDir -Filter "*.jar").Count
}

if (-not $testJarsExist -or $testJarsCount -eq 0) {
    Write-Host "JARs de test non trouvés. Tentative de téléchargement..." -ForegroundColor Yellow
    try {
        $scriptPath = Join-Path -Path $parentDir -ChildPath "scripts\download_test_jars.py"
        if (Test-Path -Path $scriptPath) {
            python $scriptPath
            if ($LASTEXITCODE -ne 0) {
                Write-Host "Échec du téléchargement des JARs de test. Certains tests pourraient être sautés." -ForegroundColor Yellow
            } else {
                Write-Host "JARs de test téléchargés avec succès." -ForegroundColor Green
            }
        } else {
            Write-Host "Script de téléchargement des JARs de test non trouvé: $scriptPath" -ForegroundColor Yellow
            Write-Host "Certains tests pourraient être sautés." -ForegroundColor Yellow
        }
    } catch {
        Write-Host "Erreur lors du téléchargement des JARs de test: $_" -ForegroundColor Yellow
        Write-Host "Certains tests pourraient être sautés." -ForegroundColor Yellow
    }
}

# Vérifier si coverage est installé
$hasCoverage = $false
try {
    python -c "import coverage" 2>$null
    $hasCoverage = $true
    Write-Host "Module 'coverage' trouvé. Le rapport de couverture sera généré." -ForegroundColor Green
}
catch {
    Write-Host "Module 'coverage' non trouvé. Le rapport de couverture ne sera pas généré." -ForegroundColor Yellow
    Write-Host "Pour installer coverage: pip install coverage" -ForegroundColor Yellow
}

# Fonction pour exécuter les tests sans couverture
function Run-Tests {
    Write-Host "Exécution des tests unitaires..." -ForegroundColor Cyan
    py -m unittest discover -s $currentDir -p "test_*.py" -v
    return $LASTEXITCODE
}

# Fonction pour exécuter les tests avec couverture
function Run-Tests-With-Coverage {
    Write-Host "Exécution des tests unitaires avec couverture..." -ForegroundColor Cyan
    
    # Démarrer la couverture
    py -m coverage run --source=$parentDir --omit="*/__pycache__/*,*/tests/*,*/venv/*,*/env/*,*/site-packages/*" -m unittest discover -s $currentDir -p "test_*.py" -v
    $testResult = $LASTEXITCODE
    
    # Générer le rapport de couverture
    if ($testResult -eq 0) {
        Write-Host "`n--- Rapport de couverture ---" -ForegroundColor Green
    } else {
        Write-Host "`n--- Rapport de couverture ---" -ForegroundColor Yellow
    }
    
    py -m coverage report
    
    # Générer un rapport HTML
    $htmlcovDir = Join-Path -Path $currentDir -ChildPath "htmlcov"
    if (-not (Test-Path -Path $htmlcovDir)) {
        New-Item -ItemType Directory -Path $htmlcovDir | Out-Null
    }
    
    py -m coverage html -d $htmlcovDir
    Write-Host "`nRapport HTML généré dans $htmlcovDir" -ForegroundColor Cyan
    
    return $testResult
}

# Exécuter les tests avec ou sans couverture
if ($hasCoverage) {
    $exitCode = Run-Tests-With-Coverage
} else {
    $exitCode = Run-Tests
}

# Afficher un message de résultat
if ($exitCode -eq 0) {
    Write-Host "`nTous les tests ont réussi!" -ForegroundColor Green
} else {
    Write-Host "`nCertains tests ont échoué." -ForegroundColor Red
}

# Sortir avec le code approprié
exit $exitCode