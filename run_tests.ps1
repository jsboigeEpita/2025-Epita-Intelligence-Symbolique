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
    [Parameter(Mandatory=$false)]
    [ValidateSet("unit", "functional", "e2e", "e2e-python", "all", "validation")]
    [string]$Type = "all",

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
        & $ActivationScript -CommandToRun $pytestFinalCommand *>&1 | Tee-Object -FilePath "$pytestLogFile" -Append
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
# Branche 3: Tests Unit/Functional (Python) directs
else {
    Write-Host "[INFO] Lancement des tests de type '$Type' via appel Pytest direct..." -ForegroundColor Cyan

    $testPaths = @{
        "unit"       = "tests/unit"
        "functional" = "tests/functional"
        "all"        = @("tests/unit", "tests/functional")
        "validation" = "tests/validation"
    }

    $selectedPaths = if ($PSBoundParameters.ContainsKey('Path') -and -not [string]::IsNullOrEmpty($Path)) {
        $Path
    } else {
        $testPaths[$Type]
    }

    if (-not $selectedPaths) {
        Write-Host "[ERREUR] Type de test '$Type' non valide pour l'exécution directe de pytest." -ForegroundColor Red
        exit 1
    }
    
    # Construire la commande pytest
    $pytestCommandParts = @("python", "-m", "pytest", "-s", "-vv") + $selectedPaths
    if (-not [string]::IsNullOrEmpty($PytestArgs)) {
        $pytestCommandParts += $PytestArgs.Split(' ', [System.StringSplitOptions]::RemoveEmptyEntries)
    }
    $pytestFinalCommand = $pytestCommandParts -join " "

    # Exécution avec redirection de fichiers pour la robustesse
    $runnerLogFile = Join-Path $ProjectRoot '_temp/test_runner.log'
    Write-Host "[INFO] Commande Pytest: $pytestFinalCommand" -ForegroundColor Green
    Write-Host "[INFO] Les logs seront enregistrés dans '$runnerLogFile'" -ForegroundColor Yellow

    # Utilisation de 'conda run' pour une exécution fiable dans l'environnement.
    # C'est la méthode la plus robuste pour s'assurer que le bon interpréteur Python et les bonnes dépendances sont utilisés.
    $FullCommand = "conda run -n projet-is $pytestFinalCommand > `"$runnerLogFile`" 2>&1"
    
    # On exécute la commande via un sous-shell pour que la redirection fonctionne.
    powershell -Command "& { $FullCommand }"
    $exitCode = $LASTEXITCODE

    # Afficher les logs après l'exécution
    if (Test-Path $runnerLogFile) {
        Write-Host "--- Début du log des tests ($runnerLogFile) ---" -ForegroundColor Yellow
        Get-Content $runnerLogFile | Write-Host
        Write-Host "--- Fin du log des tests ---" -ForegroundColor Yellow
    }

    if ($exitCode -ne 0) {
        Write-Host "[ERREUR] Les tests Pytest ont échoué avec le code $exitCode. Consultez '$runnerLogFile' pour les détails." -ForegroundColor Red
    }
    
    Write-Host "[INFO] Exécution terminée avec le code de sortie : $exitCode" -ForegroundColor Cyan
    exit $exitCode
}
