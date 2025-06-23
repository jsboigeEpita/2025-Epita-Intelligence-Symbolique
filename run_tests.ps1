<#
.SYNOPSIS
    Point d'entrée unifié pour lancer tous les types de tests du projet.

.DESCRIPTION
    Ce script orchestre l'exécution des tests.
    Il gère différents types de tests, y compris les tests unitaires, fonctionnels,
    E2E avec Playwright (JS/TS) et E2E avec Pytest (Python).

.PARAMETER Type
    Spécifie le type de tests à exécuter.
    Valeurs possibles : "unit", "functional", "e2e", "e2e-python", "all", "validation".

.PARAMETER Path
    (Optionnel) Spécifie un chemin vers un fichier ou un répertoire de test spécifique.

.PARAMETER Browser
    (Optionnel) Spécifie le navigateur à utiliser pour les tests Playwright (e2e).
    Valeurs possibles : "chromium", "firefox", "webkit".

.EXAMPLE
    # Lancer les tests End-to-End avec Playwright et Chromium
    .\run_tests.ps1 -Type e2e -Browser chromium

.EXAMPLE
    # Lancer un test E2E spécifique avec Pytest
    .\run_tests.ps1 -Type e2e-python -Path tests/e2e/python/test_argument_analyzer.py

.EXAMPLE
    # Lancer les tests unitaires
    .\run_tests.ps1 -Type unit
#>
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("unit", "functional", "e2e", "e2e-python", "all", "validation")]
    [string]$Type,

    [string]$Path,

    [ValidateSet("chromium", "firefox", "webkit")]
    [string]$Browser,

    [switch]$DebugMode,

    [string]$PytestArgs
)

# --- Script Body ---
$ErrorActionPreference = 'Stop'
$ProjectRoot = $PSScriptRoot
$ActivationScript = Join-Path $ProjectRoot "activate_project_env.ps1"

# Valider l'existence du script d'activation en amont
if (-not (Test-Path $ActivationScript)) {
    Write-Host "[ERREUR] Le script d'activation '$ActivationScript' est introuvable." -ForegroundColor Red
    exit 1
}

# Branche 1: Tests E2E avec Playwright (JavaScript/TypeScript)
if ($Type -eq "e2e") {
    Write-Host "[INFO] Lancement des tests E2E avec Playwright..." -ForegroundColor Cyan
    & $ActivationScript # Active l'environnement pour rendre npx disponible
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERREUR] L'activation de l'environnement pour Playwright a échoué." -ForegroundColor Red
        exit $LASTEXITCODE
    }

    $playwrightArgs = @("npx", "playwright", "test")
    if ($PSBoundParameters.ContainsKey('Browser')) {
        $playwrightArgs += "--project", $Browser
    }
    if (-not ([string]::IsNullOrEmpty($Path))) {
        $playwrightArgs += $Path
    }

    $command = $playwrightArgs -join " "
    Write-Host "[INFO] Exécution: $command" -ForegroundColor Green
    Invoke-Expression -Command $command
    $exitCode = $LASTEXITCODE
    Write-Host "[INFO] Exécution de Playwright terminée avec le code de sortie : $exitCode" -ForegroundColor Cyan
    exit $exitCode
}
# Branche 2: Tests E2E avec Pytest (Python)
elseif ($Type -eq "e2e-python") {
    Write-Host "[INFO] Lancement des tests E2E avec Pytest..." -ForegroundColor Cyan
    $pidFile = Join-Path $ProjectRoot '_temp/backend.pid'
    $backendLauncher = Join-Path $ProjectRoot "project_core/core_from_scripts/start_backend_for_test.py"
    $pytestLogFile = Join-Path $ProjectRoot '_temp/pytest_e2e.log'

    if (-not (Test-Path $backendLauncher)) {
        Write-Host "[ERREUR] Le script de lancement du backend '$backendLauncher' est introuvable." -ForegroundColor Red
        exit 1
    }

    try {
        # 1. Lancer le backend en arrière-plan
        Write-Host "[INFO] Lancement du backend en arrière-plan..." -ForegroundColor Yellow
        $commandToRun = "python `"$backendLauncher`""
        & $ActivationScript -CommandToRun $commandToRun
        if ($LASTEXITCODE -ne 0) {
            throw "Le lancement du backend a échoué."
        }
        
        Write-Host "[INFO] Attente de 10 secondes pour que le backend se stabilise..." -ForegroundColor Yellow
        Start-Sleep -Seconds 10

        if (-not (Test-Path $pidFile)) {
            throw "Le backend n'a pas démarré correctement (fichier PID '$pidFile' introuvable)."
        }
        
        # 2. Construire la commande pytest en utilisant `python -m pytest` pour robustesse
        $pytestCommandParts = @("python", "-m", "pytest", "-v", "-s", "--backend-url", "http://localhost:8003")
        if ($DebugMode) {
             $pytestCommandParts += "--log-cli-level=DEBUG"
        }
        if (-not [string]::IsNullOrEmpty($Path)) {
            $pytestCommandParts += $Path
        } else {
            # Si aucun chemin n'est fourni, on cible le répertoire des tests e2e python par défaut.
            $pytestCommandParts += "tests/e2e/python/"
        }
        if (-not [string]::IsNullOrEmpty($PytestArgs)) {
            $pytestCommandParts += $PytestArgs.Split(' ', [System.StringSplitOptions]::RemoveEmptyEntries)
        }
        
        $pytestFinalCommand = $pytestCommandParts -join " "
        
        # 3. Exécuter les tests via le script d'activation
        Write-Host "[INFO] Exécution de Pytest: $pytestFinalCommand" -ForegroundColor Green
        
        # Le pipe (redirection) doit être exécuté dans un sous-shell pour que le runner le comprenne.
        # On passe directement la commande python, le sous-shell est implicite à cause du pipe.
        $commandToRunPytest = "$pytestFinalCommand *>&1 | Tee-Object -FilePath `"$pytestLogFile`" -Append"
        & $ActivationScript -CommandToRun "powershell -Command `"$commandToRunPytest`""
        $exitCode = $LASTEXITCODE

        if ($exitCode -ne 0) {
            Write-Host "[ERREUR] Les tests Pytest ont échoué avec le code $exitCode. Consultez '$pytestLogFile' pour les détails." -ForegroundColor Red
        } else {
            Write-Host "[INFO] Tests Pytest réussis." -ForegroundColor Green
        }
        exit $exitCode

    }
    finally {
        # 4. Nettoyer et arrêter le backend
        if (Test-Path $pidFile) {
            $pidToKill = Get-Content $pidFile
            Write-Host "[INFO] Arrêt du processus backend (PID: $pidToKill)..." -ForegroundColor Yellow
            Stop-Process -Id $pidToKill -Force -ErrorAction SilentlyContinue
            Remove-Item $pidFile -ErrorAction SilentlyContinue
        }
    }
}
# Branche 3: Tests Unit/Functional (Python) via test_runner.py
else {
    Write-Host "[INFO] Lancement des tests de type '$Type' via le test runner Python..." -ForegroundColor Cyan
    $TestRunnerScript = Join-Path $ProjectRoot "project_core/test_runner.py"
    if (-not (Test-Path $TestRunnerScript)) {
        Write-Host "[ERREUR] L'orchestrateur de test '$TestRunnerScript' est introuvable." -ForegroundColor Red
        exit 1
    }

    # Construire la liste d'arguments pour le test_runner.py
    $runnerArgs = @( "python", $TestRunnerScript, "--type", $Type )
    if ($PSBoundParameters.ContainsKey('Path') -and -not [string]::IsNullOrEmpty($Path)) {
        $runnerArgs += "--path", $Path
    }
    if ($PSBoundParameters.ContainsKey('Browser')) {
        $runnerArgs += "--browser", $Browser
    }
    if (-not [string]::IsNullOrEmpty($PytestArgs)) {
        $pytestArgsArray = $PytestArgs.Split(' ', [System.StringSplitOptions]::RemoveEmptyEntries)
        $runnerArgs += $pytestArgsArray
    }
    
    $CommandToRun = $runnerArgs -join ' '
    
    Write-Host "[INFO] Commande à exécuter : $CommandToRun" -ForegroundColor Cyan
    
    # Exécuter la commande via le script d'activation
    & $ActivationScript -CommandToRun $CommandToRun
    $exitCode = $LASTEXITCODE
    
    Write-Host "[INFO] Exécution terminée avec le code de sortie : $exitCode" -ForegroundColor Cyan
    exit $exitCode
}
