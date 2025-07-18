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
if ($Type -in @('e2e', 'e2e-js')) {
    Write-Host "[INFO] Préparation de l'environnement pour les tests E2E (Playwright)..." -ForegroundColor Cyan

    # Étape 1 : Nettoyage forcé de l'environnement NPM pour garantir un état propre
    $npmPath = Get-Command npm -ErrorAction SilentlyContinue
    if ($npmPath) {
        $e2eDir = Join-Path $ProjectRoot "services/web_api/interface-web-argumentative"
        $nodeModulesDir = Join-Path $e2eDir "node_modules"
        $playwrightReportDir = Join-Path $ProjectRoot "playwright-report"

        if (Test-Path $nodeModulesDir) {
            Write-Host "[INFO] Nettoyage des anciens modules NPM..." -ForegroundColor Yellow
            Remove-Item -Recurse -Force $nodeModulesDir
        }
        if (Test-Path $playwrightReportDir) {
            Write-Host "[INFO] Nettoyage des anciens rapports Playwright..." -ForegroundColor Yellow
            Remove-Item -Recurse -Force $playwrightReportDir
        }

        Write-Host "[INFO] Réinstallation des dépendances NPM..." -ForegroundColor Cyan
        Push-Location $e2eDir
        npm install
        Pop-Location
    } else {
        Write-Host "[WARN] 'npm' non trouvé. Le nettoyage et l'installation des dépendances sont ignorés." -ForegroundColor Yellow
    }

    # Étape 2 : Lancement des tests via le runner Python
    $env:E2E_TESTING_MODE = "1"
    Write-Host "[INFO] Lancement des tests E2E (Playwright)..." -ForegroundColor Cyan
    $commandParts = @("python", "-m", "project_core.test_runner", "--type", "e2e")
    if ($PSBoundParameters.ContainsKey('Browser')) {
        $commandParts += "--project", $Browser
    }
    if (-not ([string]::IsNullOrEmpty($Path))) {
        $commandParts += $Path
    }
    
    Write-Host "[INFO] Commande construite : '$($commandParts -join ' ')'" -ForegroundColor Cyan
    Write-Host "[INFO] Délégation de l'exécution à '$ActivationScript'..." -ForegroundColor Cyan

    # Appel direct avec les arguments, géré par le nouveau script d'activation
    & $ActivationScript $commandParts
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
    $runnerArgs += "--path", "`"$Path`"" # Encapsuler avec des guillemets doubles
}
if ($PSBoundParameters.ContainsKey('Browser')) {
    $runnerArgs += "--browser", $Browser
}
if (-not ([string]::IsNullOrEmpty($PytestArgs))) {
    # On passe les arguments supplémentaires à la fin, pour que argparse les récupère
    $runnerArgs += $PytestArgs.Split(' ')
}

Write-Host "[INFO] Commande construite pour le runner Python : '$($runnerArgs -join ' ')'" -ForegroundColor Cyan
Write-Host "[INFO] Délégation de l'exécution à '$ActivationScript'..." -ForegroundColor Cyan

# Exécuter la commande via le script d'activation qui gère l'environnement
& $ActivationScript $runnerArgs
$exitCode = $LASTEXITCODE

Write-Host "[INFO] Exécution terminée avec le code de sortie : $exitCode" -ForegroundColor Cyan
exit $exitCode
