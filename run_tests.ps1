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

$ErrorActionPreference = 'Stop'
$ProjectRoot = $PSScriptRoot
$ActivationScript = Join-Path $ProjectRoot "activate_project_env.ps1"

if (-not (Test-Path $ActivationScript)) {
    Write-Host "[ERREUR] Le script d'activation '$ActivationScript' est introuvable." -ForegroundColor Red
    exit 1
}

$finalCommandArgs = @()

if ($Type -eq "e2e") {
    Write-Host "[INFO] Configuration pour les tests E2E (Playwright)..." -ForegroundColor Cyan
    # La logique de nettoyage NPM est conservée car elle est spécifique à l'E2E.
    $reactAppPath = Join-Path $ProjectRoot "services/web_api/interface-web-argumentative"
    Write-Host "[INFO] Nettoyage en profondeur de l'environnement React..." -ForegroundColor Yellow
    taskkill /F /IM node.exe /T >$null 2>&1
    Push-Location -Path $reactAppPath
    npm cache clean --force
    if (Test-Path "node_modules") { Remove-Item -Recurse -Force "node_modules" }
    if (Test-Path "package-lock.json") { Remove-Item -Force "package-lock.json" }
    npm install --verbose
    if ($LASTEXITCODE -ne 0) { Write-Host "[ERREUR] L'installation NPM a échoué." -ForegroundColor Red; Pop-Location; exit $LASTEXITCODE }
    Pop-Location
    Write-Host "[INFO] Nettoyage terminé." -ForegroundColor Green

    $finalCommandArgs = @("npx", "playwright", "test", "-c", "tests/e2e/playwright.config.js")
    if ($PSBoundParameters.ContainsKey('Browser')) {
        $finalCommandArgs += "--project", $Browser
    }
    if (-not ([string]::IsNullOrEmpty($Path))) {
        $finalCommandArgs += $Path
    }
}
else { # Tous les autres tests sont gérés par Pytest
    Write-Host "[INFO] Configuration pour les tests de type '$Type' (Pytest)..." -ForegroundColor Cyan
    
    $testPaths = @{
        "unit"       = "tests/unit"
        "functional" = "tests/functional"
        "all"        = "tests"
        "e2e-python" = "tests/e2e/python"
        "integration"= "tests/integration"
    }

    $selectedPath = $testPaths[$Type]
    if ($Path) {
        $selectedPath = $Path
    }

    $finalCommandArgs = @("pytest", "-s", "-vv", $selectedPath)
    if ($PytestArgs) {
        $finalCommandArgs += $PytestArgs.Split(' ')
    }
}

Write-Host "[INFO] Lancement de la commande via le script d'activation : $($finalCommandArgs -join ' ')" -ForegroundColor Cyan

# Appel unifié au script d'activation stable
# On passe chaque partie de la commande comme un argument séparé
& $ActivationScript $finalCommandArgs

$exitCode = $LASTEXITCODE
Write-Host "[INFO] Exécution terminée avec le code de sortie : $exitCode" -ForegroundColor Cyan
exit $exitCode
