param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("unit", "functional", "e2e", "all", "integration", "e2e-python", "e2e-js")]
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
$TestRunnerScript = Join-Path $ProjectRoot "project_core/test_runner.py"

# Valider l'existence des scripts critiques
if (-not (Test-Path $ActivationScript)) {
    Write-Host "[ERREUR] Le script d'activation '$ActivationScript' est introuvable." -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $TestRunnerScript)) {
    Write-Host "[ERREUR] L'orchestrateur de test Python '$TestRunnerScript' est introuvable." -ForegroundColor Red
    exit 1
}

# La logique Playwright reste en PowerShell car elle appelle 'npx'
if ($Type -eq 'e2e') {
    Write-Host "[INFO] Lancement des tests E2E (Playwright)..." -ForegroundColor Cyan
    $commandParts = @("npx", "playwright", "test", "-c", "tests/e2e/playwright.config.js")
    if ($PSBoundParameters.ContainsKey('Browser')) {
        $commandParts += "--project", $Browser
    }
    if (-not ([string]::IsNullOrEmpty($Path))) {
        $commandParts += $Path
    }
    $finalCommand = $commandParts -join " "
    
    Write-Host "[INFO] Commande construite : '$finalCommand'" -ForegroundColor Cyan
    Write-Host "[INFO] Délégation de l'exécution à '$ActivationScript'..." -ForegroundColor Cyan

    & $ActivationScript -CommandToRun $finalCommand
    $exitCode = $LASTEXITCODE
    Write-Host "[INFO] Exécution Playwright terminée avec le code de sortie : $exitCode" -ForegroundColor Cyan
    exit $exitCode
}

# Tous les autres types de tests sont délégués au runner Python
$pythonRunnerType = $Type
if ($Type -in @("e2e-python", "e2e-js")) {
    $pythonRunnerType = "e2e"
}
elseif ($Type -eq "integration") {
    # Le runner python ne connait que "functional" pour ce cas
    $pythonRunnerType = "functional"
}

$runnerArgs = @(
    "python",
    $TestRunnerScript,
    "--type", $pythonRunnerType
)

if ($PSBoundParameters.ContainsKey('Path') -and -not ([string]::IsNullOrEmpty($Path))) {
    $runnerArgs += "--path", "`"$Path`"" # Encapsuler avec des guillemets doubles
}
if ($PSBoundParameters.ContainsKey('Browser')) {
    $runnerArgs += "--browser", $Browser
}
if (-not ([string]::IsNullOrEmpty($PytestArgs))) {
    # On passe les arguments supplémentaires à la fin, pour que argparse les récupère
    $runnerArgs += $PytestArgs.Split(' ')
}

$CommandToRun = $runnerArgs -join " "

Write-Host "[INFO] Commande construite pour le runner Python : '$CommandToRun'" -ForegroundColor Cyan
Write-Host "[INFO] Délégation de l'exécution à '$ActivationScript'..." -ForegroundColor Cyan

# Exécuter la commande via le script d'activation qui gère l'environnement
& $ActivationScript -CommandToRun $CommandToRun
$exitCode = $LASTEXITCODE

Write-Host "[INFO] Exécution terminée avec le code de sortie : $exitCode" -ForegroundColor Cyan
exit $exitCode
