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
    Write-Host "[INFO] Lancement du cycle de test E2E via l'orchestrateur unifié et 'conda run'..." -ForegroundColor Cyan
    
    $CondaEnvName = "projet-is"

    # Construire la commande Python pour appeler l'orchestrateur
    $OrchestratorArgs = @(
        "python",
        "-m", "argumentation_analysis.webapp.orchestrator",
        "--integration",
        "--log-level", "INFO"
    )
    if (-not ([string]::IsNullOrEmpty($Path))) {
        $OrchestratorArgs += "--tests", $Path
    }
    if ($DebugMode) {
        $OrchestratorArgs[-1] = "DEBUG"
    }

    # Préparer la commande complète pour `conda run`
    # --no-capture-output est essentiel pour voir les logs du serveur en temps réel
    $CondaCommand = @(
        "conda", "run", "-n", $CondaEnvName, "--no-capture-output"
    ) + $OrchestratorArgs
    
    $commandString = $CondaCommand -join ' '
    Write-Host "[INFO] Commande complète d'exécution construite :" -ForegroundColor Green
    Write-Host $commandString -ForegroundColor Green

    try {
        # Exécuter directement la commande `conda run`
        & $CondaCommand[0] $CondaCommand[1..($CondaCommand.Length-1)]
        $exitCode = $LASTEXITCODE
        
        if ($exitCode -ne 0) {
            # L'erreur est déjà affichée par le sous-processus grâce à --no-capture-output
            throw "L'orchestrateur (via conda run) a terminé avec un code d'erreur: $exitCode"
        }
        Write-Host "[INFO] L'orchestrateur (via conda run) a terminé avec succès." -ForegroundColor Green
    }
    catch {
        Write-Host "[ERREUR] L'exécution via conda run a échoué. $_" -ForegroundColor Red
        exit 1
    }
    exit $LASTEXITCODE
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
