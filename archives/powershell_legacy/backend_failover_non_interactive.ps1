#!/usr/bin/env pwsh
# Script de démarrage backend avec failover ports - VERSION NON-INTERACTIVE

param(
    [int]$StartPort = 5003,
    [int]$MaxAttempts = 5,
    [int]$TimeoutSeconds = 30,
    [switch]$Background
)

# Désactiver toute interactivité
$ErrorActionPreference = "SilentlyContinue"
$WarningPreference = "SilentlyContinue"
$InformationPreference = "SilentlyContinue"
$env:CONDA_ALWAYS_YES = "true"
$env:PYTHONUNBUFFERED = "1"

Write-Host "=== BACKEND FAILOVER NON-INTERACTIF ===" -ForegroundColor Cyan

# Fonctions utilitaires
function Stop-BackendProcesses {
    Get-Process -Name "python*" -ErrorAction SilentlyContinue | Where-Object {
        $cmdline = (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)" -ErrorAction SilentlyContinue).CommandLine
        $cmdline -and ($cmdline -like "*app.py*" -or $cmdline -like "*web_api*")
    } | ForEach-Object {
        Write-Host "Arrêt processus backend PID: $($_.Id)" -ForegroundColor Orange
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
}

function Test-PortFree($port) {
    $null -eq (Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue)
}

function Test-BackendResponse($port) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$port/api/health" -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop
        return $response.StatusCode -eq 200
    }
    catch {
        return $false
    }
}

function Free-Port($port) {
    $connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    foreach ($conn in $connections) {
        $process = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
        if ($process) {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        }
    }
    Start-Sleep -Seconds 1
}

# Nettoyage initial
Write-Host "Nettoyage processus existants..." -ForegroundColor Yellow
Stop-BackendProcesses

# Tentatives de démarrage avec failover
$successPort = $null
for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
    $testPort = $StartPort + $attempt - 1
    Write-Host "Tentative $attempt/$MaxAttempts - Port $testPort" -ForegroundColor Cyan
    
    # Libérer le port si nécessaire
    if (-not (Test-PortFree $testPort)) {
        Write-Host "  Libération port $testPort..." -ForegroundColor Yellow
        Free-Port $testPort
    }
    
    # Configuration environnement
    $env:PORT = $testPort
    
    # Démarrage backend
    if ($Background) {
        $job = Start-Job -ScriptBlock {
            param($workDir, $port)
            Set-Location $workDir
            $env:PORT = $port
            $env:PYTHONUNBUFFERED = "1"
            $env:CONDA_ALWAYS_YES = "true"
            
            # Utilisation directe conda run sans capture interactive
            & conda run -n projet-is python argumentation_analysis/services/web_api/app.py 2>&1
        } -ArgumentList $PWD, $testPort
        
        Write-Host "  Backend Job ID: $($job.Id)" -ForegroundColor Green
        
        # Test de connectivité
        $connected = $false
        for ($wait = 1; $wait -le $TimeoutSeconds; $wait++) {
            Start-Sleep -Seconds 1
            
            if ($job.State -eq "Failed" -or $job.State -eq "Completed") {
                Write-Host "  Job terminé prématurément" -ForegroundColor Red
                break
            }
            
            if (Test-BackendResponse $testPort) {
                Write-Host "  SUCCES: Backend accessible sur port $testPort" -ForegroundColor Green
                $successPort = $testPort
                $connected = $true
                
                # Sauvegarder les informations
                @{
                    Port = $testPort
                    JobId = $job.Id
                    Status = "SUCCESS"
                    URL = "http://localhost:$testPort"
                } | ConvertTo-Json | Out-File "backend_info.json" -Encoding UTF8
                
                break
            }
            
            if ($wait % 10 -eq 0) {
                Write-Host "  Attente... $wait/$TimeoutSeconds sec" -ForegroundColor Gray
            }
        }
        
        if (-not $connected) {
            Write-Host "  ECHEC: Timeout sur port $testPort" -ForegroundColor Red
            Stop-Job $job -ErrorAction SilentlyContinue
            Remove-Job $job -ErrorAction SilentlyContinue
        } else {
            break
        }
    } else {
        # Mode synchrone - juste démarrer
        Write-Host "  Démarrage synchrone sur port $testPort..." -ForegroundColor Green
        & conda run -n projet-is python argumentation_analysis/services/web_api/app.py
        return
    }
}

# Résultat final
if ($successPort) {
    Write-Host "`nSUCCES: Backend opérationnel sur port $successPort" -ForegroundColor Green
    Write-Host "URL: http://localhost:$successPort" -ForegroundColor Green
    exit 0
} else {
    Write-Host "`nECHEC: Impossible de démarrer le backend" -ForegroundColor Red
    @{
        Status = "FAILED"
        TestedPorts = @($StartPort..($StartPort + $MaxAttempts - 1))
    } | ConvertTo-Json | Out-File "backend_info.json" -Encoding UTF8
    exit 1
}