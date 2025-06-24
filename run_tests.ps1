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
    Write-Host "[INFO] Lancement du cycle de test E2E via le point d'entrée centralisé..." -ForegroundColor Cyan
    
    $ActivationScriptPath = Join-Path $PSScriptRoot "activate_project_env.ps1"

    # Construire la commande Python pour appeler l'orchestrateur en tant que chaîne de caractères
    $OrchestratorCommand = "python -m argumentation_analysis.webapp.orchestrator --integration --log-level INFO"
    if (-not ([string]::IsNullOrEmpty($Path))) {
        # Important: bien mettre les guillemets autour du chemin pour gérer les espaces
        $OrchestratorCommand += " --tests `"$Path`""
    }
    if ($DebugMode) {
        $OrchestratorCommand = $OrchestratorCommand.Replace("INFO", "DEBUG")
    }

    Write-Host "[INFO] Commande passée à l'activateur: $OrchestratorCommand" -ForegroundColor Green

    # Appeler le script d'activation avec la commande à exécuter
    # Le script d'activation gère lui-même l'appel à `conda run`
    try {
        & $ActivationScriptPath -CommandToRun $OrchestratorCommand
        $exitCode = $LASTEXITCODE

        if ($exitCode -ne 0) {
            # Le script d'activation devrait déjà afficher une erreur. Ceci est une confirmation.
            throw "L'orchestration des tests via le script d'activation a échoué avec le code de sortie: $exitCode"
        } else {
            Write-Host "[INFO] La suite de tests s'est terminée avec succès." -ForegroundColor Green
        }
    }
    catch {
        Write-Host "[ERREUR] Une erreur est survenue lors de l'appel au script d'activation. $_" -ForegroundColor Red
        # Le code de sortie de l'échec est déjà $LASTEXITCODE, mais on utilise 1 pour signaler une erreur de ce script-ci.
        exit 1
    }
    
    Write-Host "[INFO] Exécution E2E (Python) terminée avec le code de sortie: $exitCode" -ForegroundColor Cyan
    exit $exitCode
}
# Branche 3: Tests Unit/Functional (Python) directs
else {
    Write-Host "[INFO] Lancement des tests de type '$Type' via le point d'entrée unifié..." -ForegroundColor Cyan

    $testPaths = @{
        "unit"       = "tests/unit"
        "functional" = "tests/functional"
        "all"        = @("tests/unit", "tests/functional")
        "validation" = "tests/validation"
    }

    $selectedPaths = if ($PSBoundParameters.ContainsKey('Path') -and -not [string]::IsNullOrEmpty($Path)) {
        # Important: bien mettre les guillemets autour du chemin pour gérer les espaces
        @("`"$Path`"")
    } else {
        # Les chemins multiples sont déjà un tableau
        $testPaths[$Type]
    }

    if (-not $selectedPaths) {
        Write-Host "[ERREUR] Type de test '$Type' non valide." -ForegroundColor Red
        exit 1
    }

    # Construire la commande pytest
    $pytestCommandParts = @("python", "-m", "pytest", "-s", "-vv") + $selectedPaths
    if (-not [string]::IsNullOrEmpty($PytestArgs)) {
        $pytestCommandParts += $PytestArgs.Split(' ', [System.StringSplitOptions]::RemoveEmptyEntries)
    }
    $pytestFinalCommand = $pytestCommandParts -join " "

    # Exécution via le script d'activation pour une meilleure robustesse
    $ActivationScriptPath = Join-Path $PSScriptRoot "activate_project_env.ps1"
    $runnerLogFile = Join-Path $ProjectRoot '_temp/test_runner.log'
    
    Write-Host "[INFO] Commande Pytest à exécuter: $pytestFinalCommand" -ForegroundColor Green
    Write-Host "[INFO] Les logs seront enregistrés dans '$runnerLogFile'" -ForegroundColor Yellow

    # On encapsule l'appel dans une commande qui sera exécutée par le script d'activation
    # La redirection est gérée ici.
    $CommandToRunInShell = "$pytestFinalCommand > `"$runnerLogFile`" 2>&1"

    try {
        # Appeler le script d'activation avec la commande complète, y compris la redirection
        # Note: ceci est une façon de faire. L'idéal serait que activate_project_env.ps1 gère lui-même les logs.
        # Pour l'instant, on encapsule dans un powershell -Command pour s'assurer que la redirection se fait
        # *après* l'activation de l'environnement par `conda run`.
        $FullActivationCommand = "powershell -Command `"`& '$ActivationScriptPath' -CommandToRun '$CommandToRunInShell'`""
        
        # Pour le débogage, affichons la structure de l'appel
        # Write-Host "[DEBUG] Commande d'activation complète: $FullActivationCommand" -ForegroundColor DarkGray

        # Exécutons la commande
        & $ActivationScriptPath -CommandToRun $pytestFinalCommand *>&1 | Tee-Object -FilePath $runnerLogFile

        $exitCode = $LASTEXITCODE

        if ($exitCode -ne 0) {
            throw "L'exécution des tests via le script d'activation a échoué avec le code de sortie: $exitCode"
        } else {
            Write-Host "[INFO] La suite de tests s'est terminée avec succès." -ForegroundColor Green
        }
    }
    catch {
        Write-Host "[ERREUR] Une erreur est survenue lors de l'appel au script d'activation. Consultez '$runnerLogFile' pour plus de détails. $_" -ForegroundColor Red
        exit 1
    }

    # Afficher un résumé du log
    if (Test-Path $runnerLogFile) {
        Write-Host "--- Début du résumé des logs ($runnerLogFile) ---" -ForegroundColor Yellow
        Get-Content $runnerLogFile -Tail 50 | Write-Host
        Write-Host "--- Fin du résumé des logs ---" -ForegroundColor Yellow
    }

    if ($exitCode -ne 0) {
        Write-Host "[ERREUR] Les tests Pytest ont échoué avec le code $exitCode. Consultez '$runnerLogFile' pour les détails complets." -ForegroundColor Red
    }
    
    Write-Host "[INFO] Exécution terminée avec le code de sortie : $exitCode" -ForegroundColor Cyan
    exit $exitCode
}
