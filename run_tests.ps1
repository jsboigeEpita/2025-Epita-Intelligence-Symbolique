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
# Force l'initialisation de Conda pour la session en cours.
try {
    if (-not (Get-Command conda.exe -ErrorAction SilentlyContinue)) {
        $condaPath = (Get-Command -Name conda -CommandType Application).Source
        $condaDir = Split-Path $condaPath -Parent
        $env:Path = "$condaDir;$env:Path"
        conda.exe shell.powershell hook | Out-String | Invoke-Expression
        Write-Host "Conda initialisé pour la session." -ForegroundColor Green
    }
}
catch {
    Write-Host "[FATAL] 'conda' introuvable ou impossible à initialiser." -ForegroundColor Red
    exit 1
}

$ErrorActionPreference = 'Stop'
$ProjectRoot = $PSScriptRoot
$ActivationScript = Join-Path $ProjectRoot "activate_project_env.ps1"

# Valider l'existence du script d'activation en amont (même si on ne l'utilise plus partout, il reste utile)
if (-not (Test-Path $ActivationScript)) {
    Write-Host "[ERREUR] Le script d'activation '$ActivationScript' est introuvable." -ForegroundColor Red
    exit 1
}

# Branche 1: Tests E2E avec backend Python
if ($Type -eq "e2e-python" -or $Type -eq "integration" -or $Type -eq "e2e-js") {
    Write-Host "[INFO] Lancement des tests avec backend ($Type)..." -ForegroundColor Cyan
    $pidFile = Join-Path $ProjectRoot '_temp/backend.pid'
    $backendLauncher = Join-Path $ProjectRoot "project_core/core_from_scripts/start_backend_for_test.py"
    $exitCode = 1

    if (-not (Test-Path $backendLauncher)) {
        Write-Host "[ERREUR] Le script de lancement du backend '$backendLauncher' est introuvable." -ForegroundColor Red
        exit 1
    }

    try {
        # 1. Démarrer le backend en arrière-plan
        Write-Host "[INFO] Démarrage du backend en arrière-plan..." -ForegroundColor Yellow

        # On récupère le nom de l'environnement depuis le manager python.
        $envName = (python -m project_core.core_from_scripts.environment_manager get-env-name).Trim()
        if (-not $envName) {
            throw "Impossible de récupérer le nom de l'environnement Conda via le environment_manager."
        }
        Write-Host "[DEBUG] Environnement Conda à utiliser: $envName" -ForegroundColor DarkGray

        # Commande à exécuter pour lancer le backend
        $backendCommand = "python `"$backendLauncher`""
        # Arguments pour 'conda run'
        $condaArgs = "run -n $envName --no-capture-output --live-stream -- $backendCommand"

        # On exécute 'conda.exe run ...' directement dans le job, c'est plus fiable que d'activer.
        $job = Start-Job -ScriptBlock {
            param($condaExecutable, $arguments)
            & $condaExecutable $arguments
        } -ArgumentList @((Get-Command conda.exe).Source, $condaArgs)

        Write-Host "[INFO] Backend en cours de démarrage (Job ID: $($job.Id))... Attente de 20 secondes..."
        Start-Sleep -Seconds 20
        
        if (-not (Test-Path $pidFile)) {
            Write-Host "[ERREUR] Le backend n'a pas démarré correctement (fichier PID '$pidFile' introuvable)." -ForegroundColor Red
            $stderrLog = Join-Path $ProjectRoot '_temp/backend_stderr.log'
            if (Test-Path $stderrLog) {
                Write-Host "[DEBUG] Contenu de _temp/backend_stderr.log:" -ForegroundColor DarkGray
                Get-Content $stderrLog | Write-Host
            }
            throw "Le backend n'a pas démarré correctement."
        }
        Write-Host "[INFO] Fichier PID trouvé. Le backend est présumé démarré." -ForegroundColor Green

        # 2. Exécuter les tests pytest
        $testPaths = @{
            "e2e-python"  = "tests/e2e/python"
            "integration" = "tests/integration"
            "e2e-js"      = "tests/e2e"
        }
        $selectedPath = if ($Path) { $Path } else { $testPaths[$Type] }
        
        $pytestCommandParts = @()
        if ($PytestArgs) {
            $pytestCommandParts += $PytestArgs.Split(' ')
        }
        
        Write-Host "[INFO] Exécution de Pytest..." -ForegroundColor Green
        
        $pytestCommand = "pytest -s -vv `"$selectedPath`""
        if ($Type -eq "e2e-python" -or $Type -eq "e2e-js") {
            $pytestCommand += " --frontend-url=http://localhost:3000 --backend-url=http://localhost:8004"
        }
        if ($PytestArgs) {
            $pytestCommand += " $PytestArgs"
        }

        # On délègue l'exécution à notre script d'activation qui gère l'environnement
        & $ActivationScript -CommandToRun $pytestCommand
        $exitCode = $LASTEXITCODE
    }
    finally {
        # 3. Arrêter le backend
        if (Test-Path $pidFile) {
            $pidToKill = Get-Content $pidFile
            Write-Host "[INFO] Arrêt du processus backend (PID: $pidToKill)..." -ForegroundColor Yellow
            Stop-Process -Id $pidToKill -Force -ErrorAction SilentlyContinue
            Remove-Item $pidFile -ErrorAction SilentlyContinue
        } else {
            Write-Host "[WARN] Fichier PID introuvable, impossible d'arrêter le backend. Un nettoyage manuel peut être requis." -ForegroundColor Yellow
        }
        # Nettoyer le job
        if ($job) {
            Remove-Job $job -Force
        }
    }
    Write-Host "[INFO] Exécution des tests de type '$Type' terminée avec le code de sortie : $exitCode" -ForegroundColor Cyan
    exit $exitCode
}
else {
    # Logique pour les autres types de tests (unit, functional, playwright, all)
    # Cette partie utilise déjà `activate_project_env.ps1`, on la laisse telle quelle pour l'instant
    # pour ne pas tout casser. La refacto peut se poursuivre plus tard.
    $commandParts = @()
    if ($Type -eq "e2e") {
        Write-Host "[INFO] Lancement des tests E2E (Playwright)..." -ForegroundColor Cyan
        $commandParts = @("npx", "playwright", "test", "-c", "tests/e2e/playwright.config.js")
        if ($PSBoundParameters.ContainsKey('Browser')) {
            $commandParts += "--project", $Browser
        }
        if (-not ([string]::IsNullOrEmpty($Path))) {
            $commandParts += $Path
        }
    } else {
        Write-Host "[INFO] Lancement des tests de type '$Type' via Pytest..." -ForegroundColor Cyan
        $pytestCachePath = Join-Path $ProjectRoot ".pytest_cache"
        if (Test-Path $pytestCachePath) {
            Write-Host "[INFO] Nettoyage du cache de pytest..." -ForegroundColor Yellow
            Remove-Item -Recurse -Force $pytestCachePath
        }
        $testPaths = @{
            "unit"       = "tests/unit"
            "functional" = "tests/functional"
            "all"        = "tests"
        }
        $selectedPath = $testPaths[$Type]
        if (-not $selectedPath) {
            Write-Host "[ERREUR] Type de test '$Type' non valide." -ForegroundColor Red
            exit 1
        }
        if ($Path) {
            $selectedPath = $Path
        }
        $commandParts = @("pytest", "-s", "-vv", "`"$selectedPath`"")
        if ($PytestArgs) {
            $commandParts += $PytestArgs.Split(' ')
        }
    }
    
    $finalCommand = $commandParts -join " "
    Write-Host "[INFO] Commande construite : '$finalCommand'" -ForegroundColor Cyan
    Write-Host "[INFO] Délégation de l'exécution à '$ActivationScript'..." -ForegroundColor Cyan

    & $ActivationScript -CommandToRun $finalCommand
    $exitCode = $LASTEXITCODE

    Write-Host "[INFO] Exécution terminée avec le code de sortie : $exitCode" -ForegroundColor Cyan
    exit $exitCode
}
