#!/usr/bin/env pwsh
<#
.SYNOPSIS
Script de lancement de l'application web d'analyse argumentative

.DESCRIPTION
Ce script lance automatiquement le serveur backend Flask et l'interface frontend React
pour l'application d'analyse argumentative.

.PARAMETER BackendOnly
Lance uniquement le serveur backend

.PARAMETER FrontendOnly  
Lance uniquement l'interface frontend

.PARAMETER Help
Affiche l'aide

.EXAMPLE
.\start_web_application.ps1
Lance backend et frontend

.EXAMPLE
.\start_web_application.ps1 -BackendOnly
Lance uniquement le backend

.NOTES
Auteur: Équipe Argumentation Analysis
Version: 1.0
Date: 2025-06-06
#>

param(
    [switch]$BackendOnly,
    [switch]$FrontendOnly,
    [switch]$Help
)

if ($Help) {
    Get-Help $MyInvocation.MyCommand.Path -Full
    exit 0
}

# Configuration UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "🚀 Lancement de l'Application Web d'Analyse Argumentative" -ForegroundColor Green
Write-Host "=" * 60

# Chargement de l'environnement
Write-Host "📋 Chargement de l'environnement..." -ForegroundColor Blue
& .\scripts\env\activate_project_env.ps1

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Erreur lors du chargement de l'environnement" -ForegroundColor Red
    exit 1
}

# Fonction pour lancer le backend
function Start-Backend {
    Write-Host "🔧 Démarrage du serveur backend Flask..." -ForegroundColor Blue
    
    # Vérifier que le backend existe
    if (-not (Test-Path "argumentation_analysis/services/web_api/app.py")) {
        Write-Host "❌ Fichier backend non trouvé: argumentation_analysis/services/web_api/app.py" -ForegroundColor Red
        return $false
    }
    
    # Lancer le backend en arrière-plan
    $backendJob = Start-Job -ScriptBlock {
        param($projectPath)
        Set-Location $projectPath
        & .\scripts\env\activate_project_env.ps1 -CommandToRun "python -m argumentation_analysis.services.web_api.app"
    } -ArgumentList (Get-Location).Path -Name "Backend"
    
    Write-Host "📡 Backend Flask démarré (Job ID: $($backendJob.Id))" -ForegroundColor Green
    Write-Host "🌐 URL Backend: http://localhost:5003" -ForegroundColor Cyan
    
    return $backendJob
}

# Fonction pour lancer le frontend
function Start-Frontend {
    Write-Host "⚛️ Démarrage de l'interface React..." -ForegroundColor Blue
    
    # Vérifier que le frontend existe
    $frontendPath = "services/web_api/interface-web-argumentative"
    if (-not (Test-Path "$frontendPath/package.json")) {
        Write-Host "❌ Interface frontend non trouvée: $frontendPath" -ForegroundColor Red
        return $false
    }
    
    # Installer les dépendances si nécessaire
    Push-Location $frontendPath
    if (-not (Test-Path "node_modules")) {
        Write-Host "📦 Installation des dépendances npm..." -ForegroundColor Yellow
        npm install
        if ($LASTEXITCODE -ne 0) {
            Write-Host "❌ Erreur lors de l'installation npm" -ForegroundColor Red
            Pop-Location
            return $false
        }
    }
    
    # Lancer le frontend en arrière-plan
    $frontendJob = Start-Job -ScriptBlock {
        param($frontendPath)
        Set-Location $frontendPath
        npm start
    } -ArgumentList (Resolve-Path $frontendPath).Path -Name "Frontend"
    
    Pop-Location
    
    Write-Host "📱 Interface React démarrée (Job ID: $($frontendJob.Id))" -ForegroundColor Green
    Write-Host "🌐 URL Frontend: http://localhost:3000" -ForegroundColor Cyan
    
    return $frontendJob
}

# Fonction pour attendre que les serveurs soient prêts
function Wait-ForServers {
    param($CheckBackend = $true, $CheckFrontend = $true)
    
    Write-Host "⏳ Attente du démarrage des serveurs..." -ForegroundColor Yellow
    
    $maxAttempts = 30
    $sleepInterval = 2
    
    for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
        $backendReady = if ($CheckBackend) { 
            (Test-NetConnection -ComputerName localhost -Port 5003 -WarningAction SilentlyContinue).TcpTestSucceeded 
        } else { $true }
        
        $frontendReady = if ($CheckFrontend) { 
            (Test-NetConnection -ComputerName localhost -Port 3000 -WarningAction SilentlyContinue).TcpTestSucceeded 
        } else { $true }
        
        if ($backendReady -and $frontendReady) {
            Write-Host "✅ Tous les serveurs sont opérationnels!" -ForegroundColor Green
            return $true
        }
        
        $status = "Tentative $attempt/$maxAttempts"
        if ($CheckBackend) { $status += " | Backend: $(if($backendReady){'✅'}else{'⏳'})" }
        if ($CheckFrontend) { $status += " | Frontend: $(if($frontendReady){'✅'}else{'⏳'})" }
        Write-Host $status -ForegroundColor Yellow
        
        Start-Sleep -Seconds $sleepInterval
    }
    
    Write-Host "⚠️ Timeout: Les serveurs ne sont pas tous prêts" -ForegroundColor Red
    return $false
}

# Lancement conditionnel
$jobs = @()

if ($BackendOnly) {
    $backendJob = Start-Backend
    if ($backendJob) {
        $jobs += $backendJob
        Wait-ForServers -CheckBackend $true -CheckFrontend $false
    }
} elseif ($FrontendOnly) {
    $frontendJob = Start-Frontend
    if ($frontendJob) {
        $jobs += $frontendJob
        Wait-ForServers -CheckBackend $false -CheckFrontend $true
    }
} else {
    # Lancer backend et frontend
    $backendJob = Start-Backend
    if ($backendJob) { $jobs += $backendJob }
    
    Start-Sleep -Seconds 3  # Laisser le temps au backend de démarrer
    
    $frontendJob = Start-Frontend
    if ($frontendJob) { $jobs += $frontendJob }
    
    if ($jobs.Count -gt 0) {
        Wait-ForServers -CheckBackend $true -CheckFrontend $true
    }
}

if ($jobs.Count -eq 0) {
    Write-Host "❌ Aucun service n'a pu être démarré" -ForegroundColor Red
    exit 1
}

# Affichage des informations finales
Write-Host ""
Write-Host "🎉 Application Web lancée avec succès!" -ForegroundColor Green
Write-Host "=" * 60
Write-Host "📊 Services actifs:" -ForegroundColor Blue

foreach ($job in $jobs) {
    $status = if ($job.State -eq "Running") { "🟢 Actif" } else { "🔴 Arrêté" }
    Write-Host "  • $($job.Name): $status" -ForegroundColor White
}

if (-not $BackendOnly) {
    Write-Host ""
    Write-Host "🌐 Accès à l'interface:" -ForegroundColor Blue
    Write-Host "  Frontend: http://localhost:3000" -ForegroundColor Cyan
}

if (-not $FrontendOnly) {
    Write-Host "  Backend API: http://localhost:5003" -ForegroundColor Cyan
    Write-Host "  Documentation API: http://localhost:5003/api/health" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "🧪 Tests fonctionnels:" -ForegroundColor Blue
Write-Host "  Pour lancer les tests Playwright: .\scripts\run_all_and_test.ps1" -ForegroundColor Yellow

Write-Host ""
Write-Host "⏹️ Pour arrêter les services:" -ForegroundColor Red
Write-Host "  Appuyez sur Ctrl+C ou fermez cette fenêtre" -ForegroundColor Red

# Attendre que l'utilisateur arrête
try {
    Write-Host ""
    Write-Host "Appuyez sur Ctrl+C pour arrêter les services..." -ForegroundColor Yellow
    while ($true) {
        Start-Sleep -Seconds 5
        
        # Vérifier l'état des jobs
        $runningJobs = $jobs | Where-Object { $_.State -eq "Running" }
        if ($runningJobs.Count -eq 0) {
            Write-Host "⚠️ Tous les services se sont arrêtés" -ForegroundColor Yellow
            break
        }
    }
} finally {
    Write-Host ""
    Write-Host "🛑 Arrêt des services..." -ForegroundColor Yellow
    
    foreach ($job in $jobs) {
        if ($job.State -eq "Running") {
            Stop-Job $job -Force
            Write-Host "  ✅ $($job.Name) arrêté" -ForegroundColor Green
        }
        Remove-Job $job -Force
    }
    
    Write-Host "👋 Application fermée. Merci d'avoir utilisé notre outil!" -ForegroundColor Green
}