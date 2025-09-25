param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("unit", "functional", "e2e", "all", "integration", "e2e-python", "e2e-js")]
    [string]$Type = "all",

    [string]$Path,
    
    [string]$PytestArgs,

    [string]$LogFile,

    [ValidateSet("chromium", "firefox", "webkit")]
    [string]$Browser,

    [switch]$DebugMode
)

# --- Script Body ---
# Le script délègue désormais entièrement la gestion de l'environnement à 'activate_project_env.ps1'
# qui utilise 'conda run'. Toute initialisation manuelle est donc supprimée.

$ErrorActionPreference = 'Stop'
$ProjectRoot = $PSScriptRoot

# --- Chargement de l'environnement de test ---
# Si un fichier .env.test existe, charge ses variables pour les tests E2E.
# Cela permet de surcharger la configuration (ex: clés API) sans altérer les .env standards.
$TestEnvFile = Join-Path $ProjectRoot ".env.test"
if (Test-Path $TestEnvFile) {
    Write-Host "[INFO] Fichier .env.test trouvé, chargement des variables..." -ForegroundColor Cyan
    Get-Content $TestEnvFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -and !$line.StartsWith("#")) {
            $key, $value = $line -split '=', 2
            if ($key -and $value) {
                # Supprime les guillemets autour de la valeur, s'ils existent
                $value = $value -replace '^"|"$'
                [System.Environment]::SetEnvironmentVariable($key.Trim(), $value.Trim())
                Write-Host "  - Variable '$($key.Trim())' chargée." -ForegroundColor Gray
            }
        }
    }
}
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
    # On définit une variable d'environnement pour que les sous-scripts sachent
    # qu'on est en mode test E2E et puissent adapter leur comportement (ex: désactiver
    # certaines vérifications d'environnement strictes).
    $env:E2E_TESTING_MODE = "1"

    Write-Host "[INFO] Lancement des tests E2E avec le nouvel orchestrateur asynchrone..." -ForegroundColor Cyan
    $NewOrchestratorPath = Join-Path $ProjectRoot "scripts/orchestration/run_e2e_tests.py"
    if (-not (Test-Path $NewOrchestratorPath)) {
        Write-Host "[ERREUR] Le nouvel orchestrateur '$NewOrchestratorPath' est introuvable." -ForegroundColor Red
        exit 1
    }
    # Le nouvel orchestrateur est autonome et ne prend pas d'arguments pour l'instant.
    $finalCommand = "python `"$NewOrchestratorPath`""
    
    Write-Host "[INFO] Commande construite : '$finalCommand'" -ForegroundColor Cyan
    Write-Host "[INFO] Délégation de l'exécution à '$ActivationScript'..." -ForegroundColor Cyan

    & $ActivationScript -CommandToRun $finalCommand
    $exitCode = $LASTEXITCODE
    Write-Host "[INFO] Exécution Playwright terminée avec le code de sortie : $exitCode" -ForegroundColor Cyan
    exit $exitCode
}

# Pour tous les tests basés sur Python, on désactive OpenTelemetry
$env:OTEL_SDK_DISABLED = "true"
$env:OTEL_METRICS_EXPORTER = "none"
$env:OTEL_TRACES_EXPORTER = "none"
Write-Host "[INFO] OpenTelemetry a été désactivé pour cette session de test." -ForegroundColor Yellow


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
    $runnerArgs += "--path", $Path
}
if ($PSBoundParameters.ContainsKey('Browser')) {
    $runnerArgs += "--browser", $Browser
}
if (-not ([string]::IsNullOrEmpty($PytestArgs))) {
    # On passe les arguments supplémentaires à la fin, pour que argparse les récupère
    $runnerArgs += $PytestArgs.Split(' ')
}
if (-not ([string]::IsNullOrEmpty($LogFile))) {
    $runnerArgs += "--log-file=$LogFile"
}

$CommandToRun = $runnerArgs -join " "

Write-Host "[INFO] Commande construite pour le runner Python : '$CommandToRun'" -ForegroundColor Cyan
Write-Host "[INFO] Délégation de l'exécution à '$ActivationScript'..." -ForegroundColor Cyan

# Exécuter la commande via le script d'activation qui gère l'environnement
& $ActivationScript -CommandToRun $CommandToRun
$exitCode = $LASTEXITCODE

Write-Host "[INFO] Exécution terminée avec le code de sortie : $exitCode" -ForegroundColor Cyan
exit $exitCode
