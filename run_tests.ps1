<#
.SYNOPSIS
    Point d'entrée unifié pour lancer tous les types de tests du projet.

.DESCRIPTION
    Ce script orchestre l'exécution des tests.
    Pour les tests E2E, il lance directement Playwright.
    Pour les autres tests, il utilise l'orchestrateur Python.

.PARAMETER Type
    Spécifie le type de tests à exécuter.
    Valeurs possibles : "unit", "functional", "e2e", "all".

.PARAMETER Path
    (Optionnel) Spécifie un chemin vers un fichier ou un répertoire de test spécifique.

.PARAMETER Browser
    (Optionnel) Spécifie le navigateur à utiliser pour les tests Playwright (e2e).
    Valeurs possibles : "chromium", "firefox", "webkit".

.EXAMPLE
    # Lancer les tests End-to-End avec Chromium
    .\run_tests.ps1 -Type e2e -Browser chromium

.EXAMPLE
    # Lancer les tests unitaires
    .\run_tests.ps1 -Type unit
#>
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("unit", "functional", "e2e", "all", "validation")]
    [string]$Type,

    [string]$Path,

    [ValidateSet("chromium", "firefox", "webkit")]
    [string]$Browser,

    [switch]$DebugMode,

    [string]$PytestArgs
)

# --- Script Body ---
$ProjectRoot = $PSScriptRoot

# Si le type est 'e2e', on lance Playwright directement.
if ($Type -eq "e2e") {
    Write-Host "[INFO] Lancement des tests E2E avec Playwright..." -ForegroundColor Cyan
    
    # Activer l'environnement pour que npx soit disponible si nécessaire
    $ActivationScript = Join-Path $ProjectRoot "activate_project_env.ps1"
    if (-not (Test-Path $ActivationScript)) {
        Write-Host "[ERREUR] Le script d'activation '$ActivationScript' est introuvable." -ForegroundColor Red
        exit 1
    }
    # On active simplement, sans passer de commande
    & $ActivationScript
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERREUR] L'activation de l'environnement a échoué." -ForegroundColor Red
        exit $LASTEXITCODE
    }

    $playwrightArgs = @("npx", "playwright", "test")
    if ($PSBoundParameters.ContainsKey('Browser')) {
        $playwrightArgs += "--project", $Browser
    }
    if ($PSBoundParameters.ContainsKey('Path') -and -not ([string]::IsNullOrEmpty($Path))) {
        $playwrightArgs += $Path
    }

    $command = $playwrightArgs -join " "
    Write-Host "[INFO] Exécution: $command" -ForegroundColor Green
    
    Invoke-Expression -Command $command
    $exitCode = $LASTEXITCODE
    Write-Host "[INFO] Exécution de Playwright terminée avec le code de sortie : $exitCode" -ForegroundColor Cyan
    exit $exitCode
}

# Pour les autres types de tests (unit, functional, all), on utilise l'ancienne méthode via le test_runner.
$ActivationScript = Join-Path $ProjectRoot "activate_project_env.ps1"
$TestRunnerScript = Join-Path $ProjectRoot "project_core/test_runner.py"

if (-not (Test-Path $ActivationScript)) {
    Write-Host "[ERREUR] Le script d'activation '$ActivationScript' est introuvable." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $TestRunnerScript)) {
    Write-Host "[ERREUR] L'orchestrateur de test '$TestRunnerScript' est introuvable." -ForegroundColor Red
    exit 1
}

# Construire la liste d'arguments pour le test_runner.py (qui est maintenant simplifié)
$runnerArgs = @(
    $TestRunnerScript,
    "--type", $Type
)
if ($PSBoundParameters.ContainsKey('Path') -and -not [string]::IsNullOrEmpty($Path)) {
    $runnerArgs += "--path", $Path
}
# Le paramètre browser n'est plus géré par le runner python mais directement par playwright
# On peut le garder ici si des tests fonctionnels en ont besoin, sinon le supprimer.
if ($PSBoundParameters.ContainsKey('Browser')) {
    $runnerArgs += "--browser", $Browser
}
if (-not [string]::IsNullOrEmpty($PytestArgs)) {
    $pytestArgsArray = $PytestArgs.Split(' ', [System.StringSplitOptions]::RemoveEmptyEntries)
    $runnerArgs += $pytestArgsArray
}

$CommandToRun = "python $($runnerArgs -join ' ')"

Write-Host "[INFO] Commande à exécuter : $CommandToRun" -ForegroundColor Cyan
Write-Host "[INFO] Lancement des tests via $ActivationScript..." -ForegroundColor Cyan

# Préparer les arguments pour le script d'activation
$TempFile = [System.IO.Path]::GetTempFileName()
$activationArgs = @{
    CommandToRun = $CommandToRun
    CommandOutputFile = $TempFile
}
if ($DebugMode) { $activationArgs['DebugMode'] = $true }

# Le script d'activation génère la commande complète dans un fichier temporaire
& $ActivationScript @activationArgs
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERREUR] Le script d'activation a échoué." -ForegroundColor Red
    Remove-Item $TempFile -ErrorAction SilentlyContinue
    exit 1
}

$FinalCommand = Get-Content $TempFile
Remove-Item $TempFile -ErrorAction SilentlyContinue

if (-not $FinalCommand) {
    Write-Host "[ERREUR] Le script d'activation n'a pas généré de commande." -ForegroundColor Red
    exit 1
}

Write-Host "[INFO] Exécution de la commande finale : $FinalCommand" -ForegroundColor Green
Invoke-Expression -Command $FinalCommand

$exitCode = $LASTEXITCODE
Write-Host "[INFO] Exécution terminée avec le code de sortie : $exitCode" -ForegroundColor Cyan
exit $exitCode