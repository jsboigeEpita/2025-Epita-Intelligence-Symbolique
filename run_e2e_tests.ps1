<#
.SYNOPSIS
Orchestrateur pour les tests End-to-End (E2E) Python avec Playwright.

.DESCRIPTION
Ce script gère le cycle de vie complet pour les tests E2E :
1. Démarre le serveur backend (Uvicorn/Flask) en tâche de fond.
2. Démarre le serveur frontend (React) en tâche de fond.
3. Attend que les deux services soient prêts (health checks).
4. Exécute les tests pytest via `run_tests.ps1`, en passant les URLs des services.
5. S'assure d'arrêter proprement les serveurs à la fin, même en cas d'erreur.

.PARAMETER TestPath
Chemin vers un fichier de test ou un répertoire de tests spécifique à exécuter.
Par défaut, exécute tous les tests dans `tests/e2e/python`.

.PARAMETER PytestArgs
Arguments supplémentaires à passer à pytest (ex: "-s -k 'mon_test'").
#>
param(
    [string]$TestPath = "tests/e2e/python",
    [string]$PytestArgs = ""
)

$ErrorActionPreference = 'Stop'
$script:ProjectRoot = $PSScriptRoot

# --- Configuration ---
$CondaEnvName = "projet-is-new" # Nom de l'environnement Conda requis par l'application
$BackendPort = 5003
$FrontendPort = 3000
$BackendUrl = "http://localhost:$BackendPort"
$FrontendUrl = "http://localhost:$FrontendUrl"
$FrontendDir = Join-Path $script:ProjectRoot "services/web_api/interface-web-argumentative"

$backendJob = $null
$frontendJob = $null

# --- Fonctions ---
function Stop-ServersByPort {
    $ports = @($BackendPort, $FrontendPort)
    foreach ($port in $ports) {
        # Filter specifically for LISTENING states to avoid ambiguity
        $connections = netstat -ano | findstr ":$port" | findstr "LISTENING"
        if ($connections) {
            foreach ($connection in $connections) {
                $parts = $connection.Split(' ', [System.StringSplitOptions]::RemoveEmptyEntries)
                # A valid line should have at least 5 parts, with the PID being the last one
                if ($parts.Count -ge 5) {
                    $processId = $parts[4]
                    if ($processId -ne 0 -and -not [string]::IsNullOrWhiteSpace($processId)) {
                        Write-Host "[E2E Orchestrator] Tentative d'arrêt du processus LISTENING avec PID: $processId sur le port $port" -ForegroundColor Yellow
                        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
                    }
                }
            }
        }
    }
}

function Stop-Servers {
    Write-Host "[E2E Orchestrator] Nettoyage : Arrêt des serveurs..." -ForegroundColor Cyan
    if ($frontendJob) {
        Write-Host "[E2E Orchestrator] Arrêt de la tâche du serveur Frontend."
        Stop-Job -Job $frontendJob
        Remove-Job -Job $frontendJob -Force -ErrorAction SilentlyContinue
    }
    if ($backendJob) {
        Write-Host "[E2E Orchestrator] Arrêt de la tâche du serveur Backend."
        Stop-Job -Job $backendJob
        Remove-Job -Job $backendJob -Force -ErrorAction SilentlyContinue
    }
    # Sécurité supplémentaire : arrêter tout processus écoutant sur les ports
    Stop-ServersByPort
    Write-Host "[E2E Orchestrator] Nettoyage terminé."
}

# Démarre le serveur backend en utilisant le UnifiedWebOrchestrator, qui est le point d'entrée canonique.
function Start-BackendServer {
    Write-Host "[E2E Orchestrator] Démarrage des serveurs via un 'PowerShell Runner' pour UnifiedWebOrchestrator..." -ForegroundColor Cyan
    $logFile = Join-Path $script:ProjectRoot "_temp/logs/e2e_backend.log"
    $tempRunnerPath = Join-Path $script:ProjectRoot "_temp/orchestrator_runner.ps1"

    if (-not (Test-Path (Split-Path $logFile))) { New-Item -ItemType Directory -Path (Split-Path $logFile) -Force | Out-Null }
    Clear-Content -Path $logFile -ErrorAction SilentlyContinue

    $orchestratorScript = Join-Path $script:ProjectRoot "argumentation_analysis/webapp/orchestrator.py"
    $orchestratorConfig = Join-Path $script:ProjectRoot "argumentation_analysis/webapp/config/webapp_config.yml"

    # Création d'un script PowerShell temporaire pour éviter les problèmes de parsing/quoting.
    # Utilisation d'un "here-string" littéral (@'...') pour que les '$' ne soient pas interprétés.
    $runnerScriptContent = @'
param(
    [string]$pythonScriptPath,
    [string]$configPath,
    [string]$condaEnvName
)
# Correction clé: forcer la variable d'environnement pour que la validation interne de l'application réussisse.
$env:CONDA_DEFAULT_ENV = $condaEnvName
Write-Host "Vérification: CONDA_DEFAULT_ENV a été défini sur: $env:CONDA_DEFAULT_ENV"

# Utiliser le "splatting" avec un tableau d'arguments est plus robuste que de construire une longue chaîne.
$commandArgs = @(
    "--config", "`"$configPath`"",
    "--start",
    # "--frontend", # Désactivé car la configuration gère déjà ce cas et le test n'a pas besoin du frontend.
    "--exit-after-start",
    "--no-trace",
    "--log-level", "DEBUG"
)

Write-Host "Exécution de la commande: python `"$pythonScriptPath`" $($commandArgs -join ' ')"

try {
    # Exécute python avec les arguments "splattés".
    & python "`"$pythonScriptPath`"" @commandArgs
} catch {
    Write-Output "Erreur dans le runner de l'orchestrateur: $_"
    exit 1
}
'@
    Set-Content -Path $tempRunnerPath -Value $runnerScriptContent -Encoding UTF8 -Force

    $scriptBlock = {
        param($runnerPs1, $orchScript, $orchConfig, $logFileArg, $envName)
        
        # Exécuter le runner script via conda. C'est plus propre que les commandes complexes.
        # Les arguments sont passés au script temporaire.
        conda run --no-capture-output -n $envName powershell.exe -ExecutionPolicy Bypass -File $runnerPs1 -pythonScriptPath $orchScript -configPath $orchConfig -condaEnvName $envName *>&1 | Add-Content -Path $logFileArg
    }

    $job = Start-Job -ScriptBlock $scriptBlock -ArgumentList $tempRunnerPath, $orchestratorScript, $orchestratorConfig, $logFile, $CondaEnvName
    return $job
}


# La fonction Start-FrontendServer est maintenant obsolète car l'orchestrateur
# gère à la fois le backend et le frontend.


function Wait-For-Server {
    param(
        [string]$Url,
        [string]$ServerName,
        [int]$TimeoutSeconds = 120
    )
    Write-Host "[E2E Orchestrator] Attente de $ServerName sur $Url..." -ForegroundColor Yellow
    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    while ($stopwatch.Elapsed.TotalSeconds -lt $TimeoutSeconds) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -eq 200) {
                Write-Host "[E2E Orchestrator] [OK] $ServerName est prêt !" -ForegroundColor Green
                return $true
            }
        } catch {
            # Ignore les erreurs de connexion pendant l'attente
        }
        Start-Sleep -Seconds 2
    }
    Write-Host "[E2E Orchestrator] [ERREUR] Timeout en attendant $ServerName." -ForegroundColor Red
    return $false
}

trap {
    Write-Host "Une erreur est survenue. Nettoyage des processus..." -ForegroundColor Red
    Stop-Servers
    exit 1
}

Clear-Host
Write-Host "Démarrage de l'orchestrateur de tests E2E..." -ForegroundColor Cyan

# --- Logique Principale ---
try {
    # 0. Nettoyage initial pour s'assurer que les ports sont libres
    Write-Host "[E2E Orchestrator] Nettoyage initial des processus sur les ports $BackendPort et $FrontendPort..." -ForegroundColor DarkCyan
    Stop-ServersByPort

    # 1. Démarrer les serveurs via l'orchestrateur
    # Note: Start-BackendServer lance maintenant l'orchestrateur qui gère les deux services.
    # L'argument --frontend doit être ajouté à la commande dans la fonction pour activer le frontend.
    # Pour l'instant, on suppose que la fonction est correctement configurée pour le faire.
    $serverJob = Start-BackendServer
   
    Write-Host "[E2E Orchestrator] Tâche des serveurs (via orchestrateur) démarrée (ID: $($serverJob.Id))"

    # 2. Attendre que les serveurs soient prêts
    # L'orchestrateur choisit les ports, nous devons donc attendre qu'ils soient connus.
    # On va lire le fichier de log de l'orchestrateur pour trouver les URLs.
    $urlsFile = Join-Path $script:ProjectRoot "_temp/service_urls.json"
    $maxWaitSeconds = 120
    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    $urlsFound = $false

    while ($stopwatch.Elapsed.TotalSeconds -lt $maxWaitSeconds) {
        if (Test-Path $urlsFile) {
            try {
                $urlsContent = Get-Content $urlsFile -Raw | ConvertFrom-Json
                # Le test E2E ne dépend que du backend. Le frontend est optionnel.
                if ($urlsContent.backend_url) {
                    $Global:BackendUrl = $urlsContent.backend_url
                    # Le frontend_url peut être null, c'est un état valide.
                    $Global:FrontendUrl = $urlsContent.frontend_url
                    $urlsFound = $true
                    $frontendDisplay = if ([string]::IsNullOrEmpty($Global:FrontendUrl)) { 'non-défini' } else { $Global:FrontendUrl }
                    Write-Host "[E2E Orchestrator] URLs trouvées: Backend=> $Global:BackendUrl, Frontend=> $frontendDisplay" -ForegroundColor Green
                    break
                }
            } catch {
                # Le fichier peut être en cours d'écriture, on ignore les erreurs de parsing.
            }
        }
        Start-Sleep -Seconds 2
    }

    if (-not $urlsFound) { throw "Les URLs des services n'ont pas pu être déterminées après $maxWaitSeconds secondes." }
    
    # Maintenant, on attend que les serveurs sur les URLs découvertes soient prêts.
    if (-not (Wait-For-Server -Url "$Global:BackendUrl/api/health" -ServerName "Backend")) { throw "Le serveur backend n'a pas démarré." }
    # On ne lance le health check du frontend que si une URL a été fournie par l'orchestrateur.
    if ($Global:FrontendUrl -and (-not (Wait-For-Server -Url $Global:FrontendUrl -ServerName "Frontend"))) {
        throw "Le serveur frontend était configuré mais n'a pas démarré."
    }

    # 3. Exécuter les tests en passant les URLs
    Write-Host "[E2E Orchestrator] Tous les serveurs sont prêts. Démarrage des tests..." -ForegroundColor Green
   
    $testScriptPath = Join-Path $script:ProjectRoot "tests/e2e/run_tests.ps1"
    
    # La méthode la plus fiable consiste à construire un tableau d'arguments simple.
    $pwshArgs = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $testScriptPath,
        "-TestPath", $TestPath,
        "-BackendUrl", $Global:BackendUrl
    )

    if ($Global:FrontendUrl) {
        $pwshArgs += @("-FrontendUrl", $Global:FrontendUrl)
    }
    if (-not [string]::IsNullOrEmpty($PytestArgs)) {
        $pwshArgs += @("-PytestArgs", $PytestArgs)
    }
    
    Write-Host "[E2E Orchestrator] Exécution de: pwsh $($pwshArgs -join ' ')" -ForegroundColor DarkGray

    # On utilise un tableau plat d'arguments, ce qui est la méthode la plus robuste pour Start-Process.
    $process = Start-Process pwsh -ArgumentList $pwshArgs -Wait -PassThru -NoNewWindow
    
    if ($null -ne $process) {
        $exitCode = $process.ExitCode
    } else {
        throw "Échec critique du démarrage du processus de test (pwsh)."
    }
} catch {
    Write-Host "[E2E Orchestrator] [ERREUR FATALE] Une erreur est survenue dans l'orchestrateur: $_" -ForegroundColor Red
    $exitCode = 1
} finally {
    Stop-Servers
}

exit $exitCode
