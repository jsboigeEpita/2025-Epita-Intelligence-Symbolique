<#
.SYNOPSIS
    Point d'entrée unifié pour lancer tous les types de tests du projet.

.DESCRIPTION
    Ce script orchestre l'exécution des tests en utilisant l'orchestrateur Python centralisé.
    Il gère l'activation de l'environnement Conda et transmet les arguments à l'orchestrateur.

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

.EXAMPLE
    # Lancer un test fonctionnel spécifique
    .\run_tests.ps1 -Type functional -Path "tests/functional/specific_feature"
#>
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("unit", "functional", "e2e", "all", "validation")]
    [string]$Type,

    [string]$Path,

    [ValidateSet("chromium", "firefox", "webkit")]
    [string]$Browser,

    [switch]$DebugMode
)

# --- Script Body ---
$ProjectRoot = $PSScriptRoot
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

# Construire la liste d'arguments pour le test_runner.py
$runnerArgs = @(
    $TestRunnerScript,
    "--type", $Type
)
if ($PSBoundParameters.ContainsKey('Path')) {
    $runnerArgs += "--path", $Path
}
if ($PSBoundParameters.ContainsKey('Browser')) {
    $runnerArgs += "--browser", $Browser
}

$CommandToRun = "python $($runnerArgs -join ' ')"

if ($Type -eq "validation") {
    $CommandToRun = "python tests/e2e/web_interface/validate_jtms_web_interface.py; python -m tests.functional.test_phase3_web_api_authentic"
}

Write-Host "[INFO] Commande à exécuter : $CommandToRun" -ForegroundColor Cyan
Write-Host "[INFO] Lancement des tests via $ActivationScript..." -ForegroundColor Cyan

# Préparer les arguments pour le script d'activation en utilisant le "splatting"
$activationArgs = @{
   CommandToRun = $CommandToRun
}
if ($DebugMode) {
   $activationArgs['DebugMode'] = $true
   Write-Host "[INFO] Mode Débogage activé." -ForegroundColor Yellow
}

# Le script d'activation génère maintenant la commande finale sur sa sortie standard.
# Les logs sont sur stderr, donc on peut capturer stdout sans être pollué.
Write-Host "[INFO] Génération de la commande d'exécution via le script d'activation..."
$FinalCommand = & $ActivationScript @activationArgs
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
   Write-Host "[ERREUR] Le script d'activation a échoué. Voir les logs ci-dessus." -ForegroundColor Red
   exit $exitCode
}

if (-not $FinalCommand) {
   Write-Host "[ERREUR] Le script d'activation n'a pas retourné de commande à exécuter." -ForegroundColor Red
   exit 1
}

Write-Host "[INFO] Commande finale à exécuter :" -ForegroundColor Green
Write-Host $FinalCommand -ForegroundColor Green

# Exécution de la commande générée. Invoke-Expression est nécessaire pour
# interpréter correctement la chaîne de commande complexe retournée.
# À ce stade, $FinalCommand peut contenir plusieurs lignes de sortie.
# On ne garde que la ligne qui contient la commande python.exe
$CommandString = $FinalCommand | Where-Object { $_ -like '*python.exe*' } | ForEach-Object { $_.Trim() }

if (-not $CommandString) {
   Write-Host "[ERREUR] Impossible d'isoler la commande d'exécution finale depuis la sortie du script d'activation." -ForegroundColor Red
   exit 1
}

Invoke-Expression -Command $CommandString

$exitCode = $LASTEXITCODE
Write-Host "[INFO] Exécution terminée avec le code de sortie : $exitCode" -ForegroundColor Cyan
exit $exitCode