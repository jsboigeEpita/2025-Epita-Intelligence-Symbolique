# Script PowerShell pour exécuter les tests unitaires
# Auteur: Roo
# Date: 30/04/2025

# Définir l'encodage en UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Afficher l'en-tête
Write-Host "=== Tests Unitaires - Projet d'Analyse Argumentative ===" -ForegroundColor Cyan
Write-Host ""

# Ajouter le répertoire parent au chemin Python
$currentDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$parentDir = Split-Path -Parent $currentDir
$env:PYTHONPATH = $parentDir

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
    python -m unittest discover -s $currentDir -p "test_*.py" -v
    return $LASTEXITCODE
}

# Fonction pour exécuter les tests avec couverture
function Run-Tests-With-Coverage {
    Write-Host "Exécution des tests unitaires avec couverture..." -ForegroundColor Cyan
    
    # Démarrer la couverture
    python -m coverage run --source=$parentDir --omit="*/__pycache__/*,*/tests/*,*/venv/*,*/env/*,*/site-packages/*" -m unittest discover -s $currentDir -p "test_*.py" -v
    $testResult = $LASTEXITCODE
    
    # Générer le rapport de couverture
    if ($testResult -eq 0) {
        Write-Host "`n--- Rapport de couverture ---" -ForegroundColor Green
    } else {
        Write-Host "`n--- Rapport de couverture ---" -ForegroundColor Yellow
    }
    
    python -m coverage report
    
    # Générer un rapport HTML
    $htmlcovDir = Join-Path -Path $currentDir -ChildPath "htmlcov"
    if (-not (Test-Path -Path $htmlcovDir)) {
        New-Item -ItemType Directory -Path $htmlcovDir | Out-Null
    }
    
    python -m coverage html -d $htmlcovDir
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