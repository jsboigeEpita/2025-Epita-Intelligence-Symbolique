<#
.SYNOPSIS
Lance la suite de tests du projet avec pytest.

.DESCRIPTION
Ce script est le point d'entrée unique pour exécuter les tests.
Il utilise `activate_project_env.ps1` pour s'assurer que les tests
sont exécutés dans le bon environnement Conda (`projet-is-roo-new`) et
avec le `PYTHONPATH` correctement configuré.

Toute la sortie est redirigée pour être capturée par les logs, et les
erreurs sont gérées de manière centralisée.

.PARAMETER TestArgs
Accepte une chaîne de caractères contenant tous les arguments à passer
directement à pytest. Cela permet de cibler des tests spécifiques ou
d'utiliser des options pytest.

.EXAMPLE
# Exécute tous les tests
.\run_tests.ps1

.EXAMPLE
# Exécute un fichier de test spécifique
.\run_tests.ps1 -TestPath "tests/integration/test_argument_analyzer.py"

.EXAMPLE
# Exécute un test spécifique avec l'option -s pour voir les prints
.\run_tests.ps1 -TestPath "tests/integration/test_argument_analyzer.py" -PytestArgs "-s -k test_successful_simple_argument_analysis"
#>

# --- Script Body ---
[System.Text.Encoding]::UTF8.GetPreamble()

$ErrorActionPreference = 'Stop'
$script:ProjectRoot = $PSScriptRoot
$script:globalExitCode = 0
$backendPid = $null
$backendUrl = "http://localhost:5003" # URL par défaut

# --- Fonctions ---
function Invoke-ManagedCommand {
    param(
        [string]$CommandToRun,
        [switch]$NoExitOnError
    )

    $activationScript = Join-Path $script:ProjectRoot "activate_project_env.ps1"
    if (-not (Test-Path $activationScript)) {
        throw "Script d'activation '$activationScript' introuvable!"
    }
    
    $argumentList = "-File `"$activationScript`" -CommandToRun `"$CommandToRun`""
    Write-Host "[CMD] powershell.exe $argumentList" -ForegroundColor DarkCyan

    $process = Start-Process "powershell.exe" -ArgumentList $argumentList -PassThru -NoNewWindow -Wait
    $exitCode = $process.ExitCode
    
    if ($exitCode -ne 0 -and (-not $NoExitOnError)) {
        throw "La commande déléguée via '$activationScript' a échoué avec le code de sortie: $exitCode."
    }
    
    return $exitCode
}

function Start-Backend {
    Write-Host "[INFO] Démarrage du serveur backend Uvicorn..." -ForegroundColor Yellow
    $logFile = Join-Path $script:ProjectRoot "_temp/backend_test.log"
    if (-not (Test-Path (Split-Path $logFile))) { New-Item -ItemType Directory -Path (Split-Path $logFile) | Out-Null }

    $command = "uvicorn argumentation_analysis.main:app --host 0.0.0.0 --port 5003 --log-level info"
    
    $activationScript = Join-Path $script:ProjectRoot "activate_project_env.ps1"
    $argumentList = "-File `"$activationScript`" -CommandToRun `"$command`""

    $process = Start-Process pwsh -ArgumentList $argumentList -PassThru -RedirectStandardOutput $logFile -RedirectStandardError $logFile
    $script:backendPid = $process.Id
    Write-Host "[INFO] Serveur backend démarré avec le PID: $($script:backendPid). Les logs sont dans '$logFile'." -ForegroundColor Green

    # Attendre que le serveur soit prêt
    Start-Sleep -Seconds 5
    $maxWait = 20
    $waited = 0
    $serverReady = $false
    while($waited -lt $maxWait){
        try {
            $response = Invoke-WebRequest -Uri "$($script:backendUrl)/health" -UseBasicParsing
            if($response.StatusCode -eq 200){
                Write-Host "[INFO] Serveur backend prêt." -ForegroundColor Green
                $serverReady = $true
                break
            }
        } catch {
             Write-Host "[INFO] Attente du serveur backend... ($($waited)s)" -ForegroundColor Gray
        }
        Start-Sleep -Seconds 2
        $waited += 2
    }
    if(-not $serverReady){
        throw "Le serveur backend n'a pas répondu à temps."
    }
}

function Stop-Backend {
    if ($script:backendPid) {
        Write-Host "[INFO] Arrêt du serveur backend (PID: $($script:backendPid))..." -ForegroundColor Yellow
        Stop-Process -Id $script:backendPid -Force -ErrorAction SilentlyContinue
        Write-Host "[INFO] Serveur backend arrêté." -ForegroundColor Green
        $script:backendPid = $null
    }
}

# --- Logique Principale ---
$params = @{
    TestType = "all"
}
$remainingArgs = @()
$ pytestArgsIndex = -1

# Parsing manuel pour mieux gérer les PytestArgs
for ($i = 0; $i -lt $args.Count; $i++) {
    if ($args[$i] -eq '-PytestArgs') {
        $pytestArgsIndex = $i
        break
    }
    if ($args[$i] -match '^-([a-zA-Z0-9_]+)$') {
        $paramName = $Matches[1]
        if ((($i + 1) -lt $args.Count) -and ($args[$i+1] -notmatch '^-')) {
            $params[$paramName] = $args[$i+1]
            $i++
        } else {
            $params[$paramName] = $true
        }
    } else {
        $remainingArgs += $args[$i]
    }
}

if ($pytestArgsIndex -ne -1) {
    # Tous les arguments après -PytestArgs sont pour pytest
    $params['PytestArgs'] = $args[($pytestArgsIndex + 1)..$args.Count] -join ' '
} elseif ($remainingArgs.Count -gt 0) {
    # S'il n'y a pas de -PytestArgs, les arguments restants sont assignés à TestPath
    $params['TestPath'] = $remainingArgs -join ' '
}


$TestType = $params['TestType']
$TestPath = if ($params.ContainsKey('TestPath')) { $params['TestPath'] } else { $null }
$PytestArgs = if ($params.ContainsKey('PytestArgs')) { $params['PytestArgs'] } else { "" }

Write-Host "[INFO] Début de l'exécution des tests avec le type: '$TestType'" -ForegroundColor Green
if ($TestPath) { Write-Host "[INFO] Chemin de test spécifié: '$TestPath'" }
if ($PytestArgs) { Write-Host "[INFO] Arguments Pytest supplémentaires: '$PytestArgs'" }

# Cas "integration" modifié pour utiliser la nouvelle logique
if ($TestType -eq "integration") {
    try {
        Start-Backend
        $testPathToRun = if ($TestPath) { "`"$TestPath`"" } else { "tests/integration" }
        
        # Passer l'URL du backend à pytest
        $command = "python -m pytest -s -vv --backend-url $($script:backendUrl) $testPathToRun $PytestArgs"
        
        $script:globalExitCode = Invoke-ManagedCommand -CommandToRun $command -NoExitOnError
    }
    catch {
        Write-Host "[ERREUR FATALE] $_" -ForegroundColor Red
        $script:globalExitCode = 1
    }
    finally {
        Stop-Backend
    }
    Write-Host "[INFO] Exécution des tests d'intégration terminée avec le code de sortie: $script:globalExitCode" -ForegroundColor Cyan
    exit $script:globalExitCode
} else {
    # Logique pour les autres types de tests (unit, functional, etc.)
    $testPaths = @{
        "unit"       = "tests/unit"
        "functional" = "tests/functional"
        "all"        = "tests" 
    }
    $selectedPath = if ($TestPath) { "`"$TestPath`"" } else { $testPaths[$TestType] }
    
    if (-not $selectedPath) {
        Write-Host "[ERREUR] Type de test '$TestType' non valide ou chemin manquant." -ForegroundColor Red
        exit 1
    }

    $command = "python -m pytest -s -vv $selectedPath $PytestArgs"
    
    try {
        $script:globalExitCode = Invoke-ManagedCommand -CommandToRun $command
    }
    catch {
        Write-Host "[ERREUR FATALE] $_" -ForegroundColor Red
        $script:globalExitCode = 1
    }
    Write-Host "[INFO] Exécution des tests terminée avec le code de sortie: $script:globalExitCode" -ForegroundColor Cyan
    exit $script:globalExitCode
}
