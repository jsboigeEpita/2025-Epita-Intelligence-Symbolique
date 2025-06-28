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
    [ValidateSet("unit", "functional", "e2e", "e2e-python", "all", "validation", "integration")]
    [string]$Type = "all",

    [string]$Path,

    [ValidateSet("chromium", "firefox", "webkit")]
    [string]$Browser,

    [switch]$DebugMode,

    [string]$PytestArgs,

    [switch]$SkipOctave
)

# --- Script Body ---
$ErrorActionPreference = 'Stop'
$ProjectRoot = $PSScriptRoot
Write-Host "[DEBUG] Script Root (PSScriptRoot): $PSScriptRoot" -ForegroundColor Magenta
Write-Host "[DEBUG] Current Location: $((Get-Location).Path)" -ForegroundColor Magenta

# Le script d'activation est remplacé par le manager Python
$EnvironmentManagerPath = "project_core.core_from_scripts.environment_manager"

# Fonction pour exécuter une commande via le manager
function Invoke-ManagedCommand {
    param(
        [string]$CommandToRun
    )
    Write-Host "[CMD] python -m $EnvironmentManagerPath run `"$CommandToRun`"" -ForegroundColor DarkGray
    python -m $EnvironmentManagerPath run "$CommandToRun"
    return $LASTEXITCODE
}


# Branche 1: Tests E2E avec Playwright (JavaScript/TypeScript)
if ($Type -eq "e2e") {
    Write-Host "[INFO] Lancement des tests E2E avec Playwright..." -ForegroundColor Cyan
    
    $playwrightArgs = @("npx", "playwright", "test")
    if ($PSBoundParameters.ContainsKey('Browser')) {
        $playwrightArgs += "--project", $Browser
    }
    if (-not ([string]::IsNullOrEmpty($Path))) {
        $playwrightArgs += $Path
    }

    $command = $playwrightArgs -join " "
    $exitCode = Invoke-ManagedCommand -CommandToRun $command
    Write-Host "[INFO] Exécution de Playwright terminée avec le code de sortie : $exitCode" -ForegroundColor Cyan
    exit $exitCode
}
# Branche 2: Tests E2E avec Pytest (Python)
elseif ($Type -eq "e2e-python") {
    Write-Host "[INFO] Lancement du cycle de test E2E en trois étapes pour éviter les conflits asyncio et passer les URLs." -ForegroundColor Cyan
    $globalExitCode = 0
    $output = ""

    try {
        # --- ÉTAPE 1: Démarrer les serveurs et capturer l'output via un fichier temporaire ---
        Write-Host "[INFO] Étape 1: Démarrage des services et capture des URLs..." -ForegroundColor Yellow
        $startCommand = "python -m argumentation_analysis.webapp.orchestrator --exit-after-start --log-level INFO --frontend"
        $urlsFile = Join-Path $ProjectRoot "_temp/service_urls.json"
        
        # Créer le répertoire _temp s'il n'existe pas
        $tempDir = Split-Path $urlsFile -Parent
        if (-not (Test-Path $tempDir)) {
            New-Item -ItemType Directory -Path $tempDir | Out-Null
        }

        # Supprimer l'ancien fichier d'URLs s'il existe pour éviter de lire des informations périmées
        if (Test-Path $urlsFile) {
            Remove-Item $urlsFile
        }

        # Exécuter l'orchestrateur via le manager d'environnement
        Invoke-ManagedCommand -CommandToRun $startCommand
        
        if ($LASTEXITCODE -ne 0) {
            # L'orchestrateur gère déjà l'affichage de ses propres erreurs.
            throw "L'orchestrateur n'a pas réussi à démarrer les services."
        }
        
        # Attendre que le fichier d'URLs soit créé
        $maxWaitSeconds = 30
        $waitIntervalSeconds = 1
        $waitedSeconds = 0
        while (-not (Test-Path $urlsFile) -and $waitedSeconds -lt $maxWaitSeconds) {
            Start-Sleep -Seconds $waitIntervalSeconds
            $waitedSeconds += $waitIntervalSeconds
        }

        if (-not (Test-Path $urlsFile)) {
            throw "Timeout: Le fichier d'URLs '$urlsFile' n'a pas été créé par l'orchestrateur."
        }
        
        # Lire et parser les URLs depuis le fichier JSON
        $urlsData = Get-Content $urlsFile | ConvertFrom-Json
        $backendUrl = $urlsData.backend_url
        $frontendUrl = $urlsData.frontend_url

        if (-not $backendUrl) {
            Write-Host "[ERREUR] Contenu de la sortie de l'orchestrateur:" -ForegroundColor Red
            Write-Host $output -ForegroundColor Red
            throw "Impossible de trouver l'URL du backend dans la sortie de l'orchestrateur après analyse."
        }
        
        Write-Host "[INFO] URL Backend capturée: $backendUrl" -ForegroundColor Green
        if ($frontendUrl) {
            Write-Host "[INFO] URL Frontend capturée: $frontendUrl" -ForegroundColor Green
        }
        
        # Définir les variables d'environnement pour Pytest
        $env:BACKEND_URL = $backendUrl
        $env:FRONTEND_URL = $frontendUrl
        
        # --- ÉTAPE 2: Lancer Pytest, qui va maintenant trouver les variables d'environnement ---
        Write-Host "[INFO] Étape 2: Lancement de Pytest..." -ForegroundColor Yellow
        $pytestCommand = "python -m pytest -s -vv"
        $testPathToRun = if (-not ([string]::IsNullOrEmpty($Path))) { $Path } else { "tests/e2e/python" }
        $pytestCommand += " `"$testPathToRun`""
        
        Invoke-ManagedCommand -CommandToRun $pytestCommand
        $globalExitCode = $LASTEXITCODE
        if ($globalExitCode -ne 0) {
            Write-Host "[AVERTISSEMENT] Pytest a échoué avec le code de sortie: $globalExitCode" -ForegroundColor Yellow
        } else {
            Write-Host "[INFO] Pytest s'est terminé avec succès." -ForegroundColor Green
        }
    }
    catch {
        Write-Host "[ERREUR FATALE] Une erreur critique est survenue dans le script run_tests.ps1: $_" -ForegroundColor Red
        $globalExitCode = 1
    }
    finally {
        # --- ÉTAPE 3: Arrêter les serveurs ---
        Write-Host "[INFO] Étape 3: Arrêt des services via l'orchestrateur..." -ForegroundColor Yellow
        $stopCommand = "python -m argumentation_analysis.webapp.orchestrator --stop"
        Invoke-ManagedCommand -CommandToRun $stopCommand
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[AVERTISSEMENT] L'orchestrateur a rencontré un problème lors de l'arrêt des services." -ForegroundColor Yellow
            if ($globalExitCode -eq 0) { $globalExitCode = 1 }
        } else {
            Write-Host "[INFO] Services arrêtés proprement." -ForegroundColor Green
        }
        
        # Nettoyer le fichier d'URLs temporaire
        if (Test-Path $urlsFile) {
            Remove-Item $urlsFile
        }
    }
    
    Write-Host "[INFO] Exécution E2E (Python) terminée avec le code de sortie final: $globalExitCode" -ForegroundColor Cyan
    exit $globalExitCode
}
# Branche 3: Tests d'intégration avec gestion du backend
elseif ($Type -eq "integration") {
    Write-Host "[INFO] Lancement du cycle de test d'intégration avec gestion du backend..." -ForegroundColor Cyan
    $globalExitCode = 0
    $pidsFile = Join-Path $ProjectRoot "_temp/service_pids.json" # Fichier pour stocker les PIDs

    try {
        # --- ÉTAPE 1: Démarrer le backend et capturer l'URL (Nouvelle méthode robuste) ---
        Write-Host "[INFO] Étape 1: Démarrage du service backend en arrière-plan..." -ForegroundColor Yellow
        
        $urlsFile = Join-Path $ProjectRoot "_temp/service_urls.json"
        $pidsFile = Join-Path $ProjectRoot "_temp/service_pids.json"
        $tempDir = Split-Path $urlsFile -Parent
        if (-not (Test-Path $tempDir)) { New-Item -ItemType Directory -Path $tempDir | Out-Null }
        if (Test-Path $urlsFile) { Remove-Item $urlsFile }
        if (Test-Path $pidsFile) { Remove-Item $pidsFile }
        
        # Obtenir le nom de l'env depuis le .env (similaire à ce que fait le manager)
        $envName = (Select-String -Path "$ProjectRoot/.env" -Pattern "CONDA_ENV_NAME=").Line.Split('=')[1].Trim().Trim("'""")
        if (-not $envName) {
            throw "Impossible de lire CONDA_ENV_NAME depuis le fichier .env"
        }
        Write-Host "[INFO] Utilisation de l'environnement Conda: $envName"

        $startArguments = "-n `"$envName`" --no-capture-output python -m argumentation_analysis.webapp.orchestrator --backend-only --log-level INFO --exit-after-start"
        
        # Démarrer le processus en arrière-plan et ne pas attendre sa fin
        Write-Host "[CMD] Lancement en arrière-plan: conda run $startArguments"
        Start-Process -FilePath "conda" -ArgumentList "run $startArguments" -NoNewWindow
        
        # L'attente du fichier d'URL devient le mécanisme de synchronisation principal

        $maxWaitSeconds = 40
        $waitIntervalSeconds = 2
        $waitedSeconds = 0
        while (-not (Test-Path $urlsFile) -and $waitedSeconds -lt $maxWaitSeconds) {
            Write-Host "[INFO] Attente du fichier d'URLs... ($($waitedSeconds)s / $($maxWaitSeconds)s)" -ForegroundColor Gray
            Start-Sleep -Seconds $waitIntervalSeconds
            $waitedSeconds += $waitIntervalSeconds
        }

        if (-not (Test-Path $urlsFile)) { throw "Timeout: Le fichier d'URLs '$urlsFile' n'a pas été créé." }
        
        $urlsData = Get-Content $urlsFile | ConvertFrom-Json
        $backendUrl = $urlsData.backend_url
        if (-not $backendUrl) { throw "Impossible de trouver l'URL du backend dans '$urlsFile'." }
        
        Write-Host "[INFO] URL Backend capturée: $backendUrl" -ForegroundColor Green
        
        # Définir les variables d'environnement pour Pytest
        $env:BACKEND_URL = $backendUrl
        $env:IS_INTEGRATION_TEST = "true" # Flag pour les tests
        $env:USE_REAL_JPYPE = "true" # Pour Tweety
        $env:TWEETY_JAR_PATH = "argumentation_analysis/libs/tweety/org.tweetyproject.tweety-full-1.28-with-dependencies.jar"
        $env:JVM_MEMORY = "1024m"

        # --- ÉTAPE 2: Lancer Pytest pour les tests d'intégration ---
        Write-Host "[INFO] Étape 2: Lancement de Pytest pour les tests d'intégration..." -ForegroundColor Yellow
        $testPathToRun = if (-not ([string]::IsNullOrEmpty($Path))) { $Path } else { "tests/integration" }
        $pytestCommand = "python -m pytest -s -vv `"$testPathToRun`""
        
        If ($PytestArgs) {
             $pytestCommand += " $PytestArgs"
        }

        # Pour les tests, l'utilisation d'Invoke-ManagedCommand reste acceptable car c'est un processus qui doit se terminer.
        Invoke-ManagedCommand -CommandToRun $pytestCommand
        $globalExitCode = $LASTEXITCODE
    }
    catch {
        Write-Host "[ERREUR FATALE] $_" -ForegroundColor Red
        $globalExitCode = 1
    }
    finally {
        # --- ÉTAPE 3: Arrêter le backend ---
        Write-Host "[INFO] Étape 3: Arrêt des services..." -ForegroundColor Yellow
        $stopCommand = "python -m argumentation_analysis.webapp.orchestrator --stop"
        Invoke-ManagedCommand -CommandToRun $stopCommand
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[AVERTISSEMENT] L'orchestrateur a rencontré une erreur lors de l'arrêt." -ForegroundColor Yellow
            if ($globalExitCode -eq 0) { $globalExitCode = 1 }
        }
        
        if (Test-Path $urlsFile) { Remove-Item $urlsFile }
    }
    
    Write-Host "[INFO] Exécution des tests d'intégration terminée avec le code de sortie: $globalExitCode" -ForegroundColor Cyan
    exit $globalExitCode
}
# Branche 4: Tests Unit/Functional (Python) directs
else {
    Write-Host "[INFO] Lancement des tests de type '$Type' via le point d'entrée unifié..." -ForegroundColor Cyan

    $testPaths = @{
        "unit"       = "tests/unit"
        "functional" = "tests/functional"
        "all"        = @("tests/unit", "tests/functional") # 'integration' est maintenant géré à part
        "validation" = "tests/validation"
    }

    $selectedPaths = if ($PSBoundParameters.ContainsKey('Path') -and -not [string]::IsNullOrEmpty($Path)) {
        @($Path)
    } else {
        $testPaths[$Type]
    }

    if (-not $selectedPaths) {
        Write-Host "[ERREUR] Type de test '$Type' non valide ou non géré dans ce mode. Pour les tests d'intégration, utilisez -Type integration." -ForegroundColor Red
        exit 1
    }
    
    # Construire la commande pytest
    $pytestCommandParts = @("python", "-m", "pytest", "-s", "-vv") + $selectedPaths
    
    # Ajouter le flag pour sauter Octave si demandé
    if ($SkipOctave) {
        Write-Host "[INFO] Le flag -SkipOctave a été détecté. Le téléchargement d'Octave sera sauté." -ForegroundColor Yellow
        $pytestCommandParts += "--skip-octave"
    }

    if (-not ([string]::IsNullOrEmpty($PytestArgs))) {
        Write-Host "[DEBUG] Contenu de PytestArgs: '$PytestArgs'" -ForegroundColor Magenta
        $pytestCommandParts += $PytestArgs.Split(' ', [System.StringSplitOptions]::RemoveEmptyEntries)
    }
    $pytestFinalCommand = $pytestCommandParts -join " "

    # Exécution
    $runnerLogFile = Join-Path $ProjectRoot '_temp/test_runner.log'
    Write-Host "[INFO] Commande Pytest à exécuter: $pytestFinalCommand" -ForegroundColor Green
    Write-Host "[INFO] Les logs partiels seront visibles ici. Voir '$runnerLogFile' pour les détails complets." -ForegroundColor Yellow

    try {
        $exitCode = Invoke-ManagedCommand -CommandToRun $pytestFinalCommand
        if ($exitCode -ne 0) { throw "Pytest a échoué avec le code $exitCode" }
    }
    catch {
        Write-Host "[ERREUR] Une erreur est survenue: $_" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "[INFO] Exécution terminée avec le code de sortie : $exitCode" -ForegroundColor Cyan
    exit $exitCode
}
