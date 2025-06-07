# start_web_application_simple.ps1
# Script simple de lancement de l'application web d'analyse argumentative

param(
    [switch]$BackendOnly,
    [switch]$FrontendOnly,
    [switch]$Help
)

# Configuration UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Affichage de l'aide
if ($Help) {
    Write-Host "Application Web d'Analyse Argumentative - Script de Lancement Simple" -ForegroundColor Green
    Write-Host "=" * 70
    Write-Host ""
    Write-Host "USAGE:" -ForegroundColor Yellow
    Write-Host "  .\start_web_application_simple.ps1                 # Lance backend + frontend"
    Write-Host "  .\start_web_application_simple.ps1 -BackendOnly    # Lance seulement le backend"
    Write-Host "  .\start_web_application_simple.ps1 -FrontendOnly   # Lance seulement le frontend"
    Write-Host ""
    Write-Host "SERVICES:" -ForegroundColor Yellow
    Write-Host "  Backend API:  http://localhost:5003"
    Write-Host "  Frontend UI:  http://localhost:3000"
    exit 0
}

# En-tête
Write-Host ""
Write-Host "[LAUNCH] Lancement Application Web d'Analyse Argumentative" -ForegroundColor Green
Write-Host "=" * 60

# Charger l'environnement
Write-Host "[ENV] Chargement de l'environnement Python..." -ForegroundColor Blue
& .\scripts\env\activate_project_env.ps1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Erreur lors du chargement de l'environnement" -ForegroundColor Red
    exit 1
}

# Fonction pour démarrer le backend
function Start-Backend {
    Write-Host "[BACKEND] Démarrage du serveur backend Flask..." -ForegroundColor Blue
    
    if (-not (Test-Path "argumentation_analysis/services/web_api/app.py")) {
        Write-Host "[ERROR] Fichier backend non trouvé" -ForegroundColor Red
        return $false
    }
    
    Write-Host "[INFO] Activation environnement et lancement backend..." -ForegroundColor Yellow
    
    # Lancer directement avec conda dans le même processus
    Start-Process -FilePath "powershell" -ArgumentList @(
        "-NoExit",
        "-Command", 
        "& .\scripts\env\activate_project_env.ps1 -CommandToRun 'python -m argumentation_analysis.services.web_api.app'"
    ) -WindowStyle Normal
    
    Write-Host "[API] Commande backend lancée dans nouvelle fenêtre" -ForegroundColor Green
    Write-Host "[WEB] URL Backend: http://localhost:5003" -ForegroundColor Cyan
    return $true
}

# Fonction pour démarrer le frontend
function Start-Frontend {
    Write-Host "[REACT] Démarrage de l'interface React..." -ForegroundColor Blue
    
    $frontendPath = "services/web_api/interface-web-argumentative"
    if (-not (Test-Path "$frontendPath/package.json")) {
        Write-Host "[ERROR] Interface frontend non trouvée: $frontendPath" -ForegroundColor Red
        return $false
    }
    
    # Installer dépendances si nécessaire
    if (-not (Test-Path "$frontendPath/node_modules")) {
        Write-Host "[NPM] Installation des dépendances..." -ForegroundColor Yellow
        Push-Location $frontendPath
        npm install
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[ERROR] Erreur installation npm" -ForegroundColor Red
            Pop-Location
            return $false
        }
        Pop-Location
    }
    
    Write-Host "[INFO] Lancement React dev server..." -ForegroundColor Yellow
    
    # Lancer React dans nouvelle fenêtre
    Start-Process -FilePath "powershell" -ArgumentList @(
        "-NoExit",
        "-Command",
        "cd '$frontendPath'; npm start"
    ) -WindowStyle Normal
    
    Write-Host "[REACT] Interface React lancée dans nouvelle fenêtre" -ForegroundColor Green
    Write-Host "[WEB] URL Frontend: http://localhost:3000" -ForegroundColor Cyan
    return $true
}

# Lancement des services
$success = $true

if (-not $FrontendOnly) {
    $backendResult = Start-Backend
    if (-not $backendResult) {
        $success = $false
        Write-Host "[ERROR] Échec démarrage backend" -ForegroundColor Red
    }
}

if (-not $BackendOnly) {
    $frontendResult = Start-Frontend  
    if (-not $frontendResult) {
        $success = $false
        Write-Host "[ERROR] Échec démarrage frontend" -ForegroundColor Red
    }
}

if (-not $success) {
    Write-Host "[ERROR] Échec de démarrage des services" -ForegroundColor Red
    exit 1
}

# Attente pour que les services démarrent
Write-Host ""
Write-Host "[WAIT] Attente démarrage des services (30 secondes)..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

# Test des services
Write-Host "[TEST] Vérification des services..." -ForegroundColor Blue

if (-not $FrontendOnly) {
    try {
        $backendTest = Invoke-WebRequest -Uri "http://localhost:5003/api/health" -TimeoutSec 5
        Write-Host "[OK] Backend opérationnel" -ForegroundColor Green
    } catch {
        Write-Host "[WARNING] Backend pas encore prêt (normal si démarrage en cours)" -ForegroundColor Yellow
    }
}

if (-not $BackendOnly) {
    try {
        $frontendTest = Invoke-WebRequest -Uri "http://localhost:3000" -TimeoutSec 5
        Write-Host "[OK] Frontend opérationnel" -ForegroundColor Green
    } catch {
        Write-Host "[WARNING] Frontend pas encore prêt (normal si démarrage en cours)" -ForegroundColor Yellow
    }
}

# Informations finales
Write-Host ""
Write-Host "[SUCCESS] Services en cours de démarrage!" -ForegroundColor Green
Write-Host "=" * 60

if (-not $BackendOnly) {
    Write-Host "[ACCESS] Interface Web: http://localhost:3000" -ForegroundColor Cyan
}

if (-not $FrontendOnly) {
    Write-Host "[ACCESS] API Backend: http://localhost:5003" -ForegroundColor Cyan
    Write-Host "[ACCESS] Health Check: http://localhost:5003/api/health" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "[INFO] Les services démarrent dans des fenêtres séparées" -ForegroundColor Blue
Write-Host "[INFO] Patientez quelques instants pour le démarrage complet" -ForegroundColor Blue
Write-Host "[INFO] Fermez les fenêtres PowerShell pour arrêter les services" -ForegroundColor Blue