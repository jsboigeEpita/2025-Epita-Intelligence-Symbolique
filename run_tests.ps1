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

# --- Exécution via le gestionnaire d'environnement ---
# Créer un fichier temporaire pour la sortie de la commande
$outputFile = [System.IO.Path]::GetTempFileName()

# Préparer les arguments pour le script d'activation en utilisant le "splatting"
$activationArgs = @{
    CommandToRun      = $CommandToRun
    CommandOutputFile = $outputFile
}
if ($DebugMode) {
    $activationArgs['DebugMode'] = $true
    Write-Host "[INFO] Mode Débogage activé." -ForegroundColor Yellow
}

try {
    # Appeler le script d'activation pour qu'il écrive la commande finale dans le fichier
    # Note: On redirige la sortie d'erreur (logs de activate_project_env) vers la console
    & $ActivationScript @activationArgs 2>&1

    if ($LASTEXITCODE -ne 0) {
        throw "Le script d'activation a échoué. Voir les logs ci-dessus."
    }

    # Lire la commande finale depuis le fichier
    $finalCommand = Get-Content $outputFile
    if ([string]::IsNullOrWhiteSpace($finalCommand)) {
        throw "La commande générée par le script d'activation est vide."
    }

    Write-Host "[INFO] Commande finale à exécuter: $finalCommand" -ForegroundColor Green

    # Exécuter la commande finale
    Invoke-Expression $finalCommand
    $exitCode = $LASTEXITCODE

    Write-Host "[INFO] Exécution terminée avec le code de sortie : $exitCode" -ForegroundColor Cyan
    exit $exitCode

}
finally {
    # Nettoyer le fichier temporaire
    if (Test-Path $outputFile) {
        Remove-Item $outputFile -Force
    }
}
