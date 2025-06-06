# start_web_application.ps1
# Script de lancement de l'application web d'analyse argumentative
# 
# Usage:
#   .\start_web_application.ps1                     # Lance backend + frontend
#   .\start_web_application.ps1 -BackendOnly        # Lance seulement le backend
#   .\start_web_application.ps1 -FrontendOnly       # Lance seulement le frontend
#   .\start_web_application.ps1 -Help               # Affiche l'aide

param(
    [switch]$BackendOnly,
    [switch]$FrontendOnly,
    [switch]$Help
)

# Configuration UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Affichage de l'aide
if ($Help) {
    Write-Host "Application Web d'Analyse Argumentative - Script de Lancement" -ForegroundColor Green
    Write-Host "=" * 70
    Write-Host ""
    Write-Host "USAGE:" -ForegroundColor Yellow
    Write-Host "  .\start_web_application.ps1                 # Lance backend + frontend"
    Write-Host "  .\start_web_application.ps1 -BackendOnly    # Lance seulement le backend"
    Write-Host "  .\start_web_application.ps1 -FrontendOnly   # Lance seulement le frontend"
    Write-Host "  .\start_web_application.ps1 -Help           # Affiche cette aide"
    Write-Host ""
    Write-Host "SERVICES:" -ForegroundColor Yellow
    Write-Host "  Backend API:  http://localhost:5003"
    Write-Host "  Frontend UI:  http://localhost:3000"
    Write-Host ""
    Write-Host "ARRÊT:" -ForegroundColor Yellow
    Write-Host "  Utilisez Ctrl+C pour arrêter les services"
    exit 0
}

# Validation des paramètres
if ($BackendOnly -and $FrontendOnly) {
    Write-Host "[ERROR] Impossible d'utiliser -BackendOnly et -FrontendOnly ensemble" -ForegroundColor Red
    exit 1
}

# En-tête
Write-Host ""
Write-Host "[LAUNCH] Lancement de l'Application Web d'Analyse Argumentative" -ForegroundColor Green
Write-Host "=" * 60

# Charger l'environnement
Write-Host "[ENV] Chargement de l'environnement Python..." -ForegroundColor Blue
& .\scripts\env\activate_project_env.ps1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Erreur lors du chargement de l'environnement" -ForegroundColor Red
    exit 1
}

# Fonction pour lancer le backend
function Start-Backend {
    Write-Host "[BACKEND] Démarrage du serveur backend Flask..." -ForegroundColor Blue
    
    # Vérifier que le backend existe
    if (-not (Test-Path "argumentation_analysis/services/web_api/app.py")) {
        Write-Host "[ERROR] Fichier backend non trouvé: argumentation_analysis/services/web_api/app.py" -ForegroundColor Red
        return $false
    }
    
    # Lancer le backend en arrière-plan
    $backendJob = Start-Job -ScriptBlock {
        param($projectPath)
        Set-Location $projectPath
        & .\scripts\env\activate_project_env.ps1 -CommandToRun "python -m argumentation_analysis.services.web_api.app"
    } -ArgumentList (Get-Location).Path -Name "Backend"
    
    Write-Host "[API] Backend Flask démarré (Job ID: $($backendJob.Id))" -ForegroundColor Green
    Write-Host "[WEB] URL Backend: http://localhost:5003" -ForegroundColor Cyan
    
    return $backendJob
}

# Fonction pour lancer le frontend
function Start-Frontend {
    Write-Host "[REACT] Démarrage de l'interface React..." -ForegroundColor Blue
    
    # Vérifier que le frontend existe
    $frontendPath = "services/web_api/interface-web-argumentative"
    if (-not (Test-Path "$frontendPath/package.json")) {
        Write-Host "[ERROR] Interface frontend non trouvée: $frontendPath" -ForegroundColor Red
        return $false
    }
    
    # Installer les dépendances si nécessaire
    Push-Location $frontendPath
    if (-not (Test-Path "node_modules")) {
        Write-Host "[NPM] Installation des dépendances npm..." -ForegroundColor Yellow
        npm install
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[ERROR] Erreur lors de l'installation npm" -ForegroundColor Red
            Pop-Location
            return $false
        }
    }
    
    # Lancer le frontend en arrière-plan
    $frontendJob = Start-Job -ScriptBlock {
        param($frontendPath)
        Set-Location $frontendPath
        npm start
    } -ArgumentList (Get-Location) -Name "Frontend"
    
    Pop-Location
    
    Write-Host "[REACT] Interface React démarrée (Job ID: $($frontendJob.Id))" -ForegroundColor Green
    Write-Host "[WEB] URL Frontend: http://localhost:3000" -ForegroundColor Cyan
    
    return $frontendJob
}

# Fonction pour attendre que les serveurs soient prêts
function Wait-ForServers {
    param($CheckBackend = $true, $CheckFrontend = $true)
    
    Write-Host "[WAIT] Attente du démarrage des serveurs..." -ForegroundColor Yellow
    
    $maxAttempts = 30
    $attempt = 0
    
    while ($attempt -lt $maxAttempts) {
        $attempt++
        $backendReady = $true
        $frontendReady = $true
        
        if ($CheckBackend) {
            try { $response = Invoke-WebRequest -Uri "http://localhost:5003/api/health" -TimeoutSec 2 -ErrorAction SilentlyContinue; $backendReady = $true } catch { $backendReady = $false }
        }
        if ($CheckFrontend) {
            try { $response = Invoke-WebRequest -Uri "http://localhost:3000" -TimeoutSec 2 -ErrorAction SilentlyContinue; $frontendReady = $true } catch { $frontendReady = $false }
        }
        
        if ($backendReady -and $frontendReady) {
            Write-Host "[OK] Tous les serveurs sont opérationnels!" -ForegroundColor Green
            return $true
        }
        
        $status = "Tentative $attempt/$maxAttempts"
        if ($CheckBackend) { $status += " | Backend: $(if($backendReady){'[OK]'}else{'[WAIT]'})" }
        if ($CheckFrontend) { $status += " | Frontend: $(if($frontendReady){'[OK]'}else{'[WAIT]'})" }
        Write-Host $status -ForegroundColor Yellow
        
        Start-Sleep -Seconds 2
    }
    
    Write-Host "[TIMEOUT] Timeout lors de l'attente des serveurs" -ForegroundColor Red
    return $false
}

# Lancement des services
$jobs = @()

# Lancer backend si demandé
if (-not $FrontendOnly) {
    $backendJob = Start-Backend
    if ($backendJob) {
        $jobs += $backendJob
    } else {
        Write-Host "[ERROR] Impossible de démarrer le backend" -ForegroundColor Red
        exit 1
    }
}

# Lancer frontend si demandé
if (-not $BackendOnly) {
    $frontendJob = Start-Frontend
    if ($frontendJob) {
        $jobs += $frontendJob
    } else {
        Write-Host "[ERROR] Impossible de démarrer le frontend" -ForegroundColor Red
        exit 1
    }
}

# Vérifier qu'au moins un service a été lancé
if ($jobs.Count -eq 0) {
    Write-Host "[ERROR] Aucun service n'a pu être démarré" -ForegroundColor Red
    exit 1
}

# Attendre que les serveurs soient prêts
Wait-ForServers -CheckBackend (-not $FrontendOnly) -CheckFrontend (-not $BackendOnly)

# Affichage des informations finales
Write-Host ""
Write-Host "[SUCCESS] Application Web lancée avec succès!" -ForegroundColor Green
Write-Host "=" * 60
Write-Host "[STATUS] Services actifs:" -ForegroundColor Blue

foreach ($job in $jobs) {
    $status = if ($job.State -eq "Running") { "[ACTIF]" } else { "[ARRETE]" }
    Write-Host "  • $($job.Name): $status" -ForegroundColor White
}

if (-not $BackendOnly) {
    Write-Host ""
    Write-Host "[WEB] Accès à l'interface:" -ForegroundColor Blue
    Write-Host "  Frontend: http://localhost:3000" -ForegroundColor Cyan
}

if (-not $FrontendOnly) {
    Write-Host "  Backend:  http://localhost:5003" -ForegroundColor Cyan
    Write-Host "  Health:   http://localhost:5003/api/health" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "[INFO] Instructions:" -ForegroundColor Blue
Write-Host "  • Utilisez Ctrl+C pour arrêter les services" -ForegroundColor White
Write-Host "  • Les services fonctionnent en arrière-plan" -ForegroundColor White
Write-Host ""

# Attendre l'interruption de l'utilisateur
try {
    Write-Host "[RUNNING] Services en cours d'exécution. Appuyez sur Ctrl+C pour arrêter..." -ForegroundColor Green
    
    # Boucle infinie jusqu'à interruption
    while ($true) {
        Start-Sleep -Seconds 5
        
        # Vérifier l'état des jobs
        $runningJobs = $jobs | Where-Object { $_.State -eq "Running" }
        if ($runningJobs.Count -eq 0) {
            Write-Host "[WARNING] Tous les services se sont arrêtés" -ForegroundColor Yellow
            break
        }
    }
} finally {
    # Nettoyage des jobs à l'arrêt
    Write-Host ""
    Write-Host "[CLEANUP] Arrêt des services..." -ForegroundColor Yellow
    
    foreach ($job in $jobs) {
        if ($job.State -eq "Running") {
            Stop-Job $job -Force
            Write-Host "  [OK] $($job.Name) arrêté" -ForegroundColor Green
        }
        Remove-Job $job -Force
    }
    
    Write-Host "[DONE] Application arrêtée proprement" -ForegroundColor Green
}