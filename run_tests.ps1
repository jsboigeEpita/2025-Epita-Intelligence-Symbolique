param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("unit", "functional", "e2e", "all", "integration", "e2e-python")]
    [string]$Type = "all",

    [string]$Path,
    
    [string]$PytestArgs,

    [ValidateSet("chromium", "firefox", "webkit")]
    [string]$Browser,

    [switch]$DebugMode
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
    
    # --- DÉBUT BLOC DE NETTOYAGE RADICAL (OPTIONNEL MAIS RECOMMANDÉ) ---
    $reactAppPath = Join-Path $ProjectRoot "services/web_api/interface-web-argumentative"
    
    Write-Host "[INFO] Nettoyage en profondeur de l'environnement React pour garantir un build frais..." -ForegroundColor Yellow

    # Tuer les serveurs node fantômes.
    Write-Host "[DEBUG] Tentative d'arrêt des serveurs de développement Node.js existants..."
    try {
        taskkill /F /IM node.exe /T >$null 2>&1
        Write-Host "[DEBUG] Processus Node.js existants arrêtés avec succès." -ForegroundColor DarkGray
    } catch {
        Write-Host "[DEBUG] Aucun processus Node.js à arrêter, ou une erreur s'est produite (ce qui est normal si rien ne tournait)." -ForegroundColor DarkGray
    }

    Push-Location -Path $reactAppPath
    
    Write-Host "[DEBUG] Nettoyage du cache npm..."
    npm cache clean --force
    
    Write-Host "[DEBUG] Suppression de node_modules..."
    if (Test-Path "node_modules") {
        Remove-Item -Recurse -Force "node_modules"
    }

    Write-Host "[DEBUG] Suppression de package-lock.json..."
    if (Test-Path "package-lock.json") {
        Remove-Item -Force "package-lock.json"
    }
    
    Write-Host "[INFO] Réinstallation des dépendances npm. Cela peut prendre un moment..."
    npm install --verbose
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERREUR] L'installation NPM a échoué." -ForegroundColor Red
        Pop-Location
        exit $LASTEXITCODE
    }

    Pop-Location
    Write-Host "[INFO] Nettoyage terminé." -ForegroundColor Green
    # --- FIN BLOC DE NETTOYAGE ---

    # On construit la commande Playwright AVANT de l'envoyer au script d'activation.
    $playwrightArgs = @("npx", "playwright", "test", "-c", "tests/e2e/playwright.config.js")

    if ($PSBoundParameters.ContainsKey('Browser')) {
        $playwrightArgs += "--project", $Browser
    }
    if (-not ([string]::IsNullOrEmpty($Path))) {
        $playwrightArgs += $Path
    }

    $finalCommand = $playwrightArgs -join " "
    
    # On exécute la commande via le script d'activation qui va charger l'environnement
    # et ensuite exécuter notre commande.
    Write-Host "[INFO] Lancement de la commande via le script d'activation : $finalCommand" -ForegroundColor Cyan
    & $ActivationScript -CommandToRun $finalCommand
    $exitCode = $LASTEXITCODE
    
    Write-Host "[INFO] Exécution de Playwright terminée avec le code de sortie : $exitCode" -ForegroundColor Cyan
    exit $exitCode
}
# Branche 2: Tous les autres types de tests via Pytest
else {
    Write-Host "[INFO] Lancement des tests de type '$Type' via Pytest..." -ForegroundColor Cyan
    
    # Désactiver OpenTelemetry pour éviter les erreurs de connexion pendant les tests
    $env:OTEL_SDK_DISABLED = "true"
    $env:OTEL_METRICS_EXPORTER = "none"
    $env:OTEL_TRACES_EXPORTER = "none"
    Write-Host "[INFO] OpenTelemetry a été désactivé pour cette session de test." -ForegroundColor Yellow
    
    $testPaths = @{
        "unit"       = "tests/unit"
        "functional" = "tests/functional"
        "all"        = "tests" # Par défaut, on lance tout sauf e2e/js
        "e2e-python" = "tests/e2e/python"
        "integration"= "tests/integration"
    }

    $selectedPath = $testPaths[$Type]
    if ($Path) {
        $selectedPath = $Path # Le chemin spécifié a la priorité
    }
    
    $pytestCommandParts = @("python", "-m", "pytest", "-s", "-vv", "`"$selectedPath`"")
    
    if ($PytestArgs) {
        $pytestCommandParts += $PytestArgs.Split(' ')
    }

    $finalCommand = $pytestCommandParts -join " "

    # Exécuter la commande via le script d'activation
    & $ActivationScript -CommandToRun $finalCommand
    $exitCode = $LASTEXITCODE
    
    Write-Host "[INFO] Exécution de Pytest terminée avec le code de sortie : $exitCode" -ForegroundColor Cyan
    exit $exitCode
}
