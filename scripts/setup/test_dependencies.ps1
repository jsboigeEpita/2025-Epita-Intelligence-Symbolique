# Script PowerShell pour tester les dépendances

# Vérifier si Python est installé
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCommand) {
    Write-Host "Python n'est pas installé ou n'est pas dans le PATH. Veuillez installer Python et réessayer." -ForegroundColor Red
    exit 1
}

# Chemin vers le script Python
$scriptPath = Join-Path $PSScriptRoot "test_dependencies.py"

# Vérifier si le script Python existe
if (-not (Test-Path $scriptPath)) {
    Write-Host "Le script Python test_dependencies.py n'existe pas dans le répertoire $PSScriptRoot." -ForegroundColor Red
    exit 1
}

Write-Host "Vérification des dépendances..." -ForegroundColor Cyan

# Vérifier si un environnement virtuel existe
$venvPath = Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) "venv_test"
if (Test-Path $venvPath) {
    # Activer l'environnement virtuel et exécuter le script Python
    Write-Host "Utilisation de l'environnement virtuel pour les tests..." -ForegroundColor Cyan
    $activateScript = Join-Path $venvPath "Scripts\Activate.ps1"
    if (Test-Path $activateScript) {
        try {
            & $activateScript
            python $scriptPath
            if ($LASTEXITCODE -eq 0) {
                Write-Host "Toutes les dépendances sont correctement installées et fonctionnelles." -ForegroundColor Green
            } else {
                Write-Host "Certaines dépendances ne sont pas correctement installées ou fonctionnelles." -ForegroundColor Red
                
                # Proposer de résoudre les problèmes de dépendances
                $fixDependencies = Read-Host "Voulez-vous essayer de résoudre les problèmes de dépendances ? (O/N)"
                if ($fixDependencies -eq "O" -or $fixDependencies -eq "o") {
                    $fixScript = Join-Path $PSScriptRoot "fix_dependencies.ps1"
                    if (Test-Path $fixScript) {
                        & $fixScript
                    } else {
                        Write-Host "Le script fix_dependencies.ps1 n'existe pas dans le répertoire $PSScriptRoot." -ForegroundColor Red
                    }
                }
                
                exit $LASTEXITCODE
            }
        } catch {
            Write-Host "Erreur lors de l'activation de l'environnement virtuel: $_" -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "Le script d'activation de l'environnement virtuel n'existe pas." -ForegroundColor Yellow
        Write-Host "Exécution du script Python sans environnement virtuel..." -ForegroundColor Cyan
        python $scriptPath
        exit $LASTEXITCODE
    }
} else {
    # Exécuter le script Python sans environnement virtuel
    Write-Host "Aucun environnement virtuel trouvé. Exécution du script Python sans environnement virtuel..." -ForegroundColor Cyan
    python $scriptPath
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Toutes les dépendances sont correctement installées et fonctionnelles." -ForegroundColor Green
    } else {
        Write-Host "Certaines dépendances ne sont pas correctement installées ou fonctionnelles." -ForegroundColor Red
        
        # Proposer de créer un environnement virtuel et de résoudre les problèmes de dépendances
        $createVenv = Read-Host "Voulez-vous créer un environnement virtuel et résoudre les problèmes de dépendances ? (O/N)"
        if ($createVenv -eq "O" -or $createVenv -eq "o") {
            $fixScript = Join-Path $PSScriptRoot "fix_dependencies.ps1"
            if (Test-Path $fixScript) {
                & $fixScript
            } else {
                Write-Host "Le script fix_dependencies.ps1 n'existe pas dans le répertoire $PSScriptRoot." -ForegroundColor Red
            }
        }
        
        exit $LASTEXITCODE
    }
}