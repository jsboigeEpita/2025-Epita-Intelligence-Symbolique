#!/usr/bin/env pwsh
# Script de diagnostic pour identifier les conflits de démarrage backend

param(
    [int]$MaxAttempts = 3,
    [int]$PortStart = 5003,
    [int]$TimeoutSeconds = 30
)

Write-Host "=== DIAGNOSTIC DEMARRAGE BACKEND ===" -ForegroundColor Cyan

# 1. Vérifier les processus Python existants
Write-Host "`n[1] Processus Python actifs:" -ForegroundColor Yellow
Get-Process -Name "python*" -ErrorAction SilentlyContinue | ForEach-Object {
    $processInfo = Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)" -ErrorAction SilentlyContinue
    if ($processInfo) {
        Write-Host "  PID: $($_.Id) | Commande: $($processInfo.CommandLine)" -ForegroundColor White
    }
}

# 2. Vérifier les ports occupés dans la plage 5000-5010
Write-Host "`n[2] Ports occupes (5000-5010):" -ForegroundColor Yellow
for ($port = 5000; $port -le 5010; $port++) {
    $connection = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($connection) {
        Write-Host "  Port $port : OCCUPE (PID: $($connection.OwningProcess))" -ForegroundColor Red
    } else {
        Write-Host "  Port $port : LIBRE" -ForegroundColor Green
    }
}

# 3. Vérifier l'environnement Java/JPype
Write-Host "`n[3] Configuration Java/JPype:" -ForegroundColor Yellow
Write-Host "  JAVA_HOME: $env:JAVA_HOME"
if ($env:JAVA_HOME -and (Test-Path "$env:JAVA_HOME\bin\java.exe")) {
    $javaVersion = & "$env:JAVA_HOME\bin\java.exe" -version 2>&1 | Select-Object -First 1
    Write-Host "  Version Java: $javaVersion" -ForegroundColor Green
} else {
    Write-Host "  ERREUR: Java non trouve ou JAVA_HOME invalide!" -ForegroundColor Red
}

# 4. Test simple d'import JPype
Write-Host "`n[4] Test import JPype:" -ForegroundColor Yellow
& .\scripts\env\activate_project_env.ps1 -CommandToRun "python -c `"
try:
    import jpype
    print('  JPype import: OK')
    print(f'  JPype version: {jpype.__version__}')
    if jpype.isJVMStarted():
        print('  JVM deja demarree: OUI - PROBLEME!')
    else:
        print('  JVM deja demarree: NON - OK')
except Exception as e:
    print(f'  ERREUR JPype: {e}')
`""

# 5. Test de démarrage backend avec ports progressifs
Write-Host "`n[5] Test demarrage backend avec failover ports:" -ForegroundColor Yellow

$successPort = $null
for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
    $testPort = $PortStart + $attempt - 1
    Write-Host "  Tentative $attempt : Port $testPort" -ForegroundColor Cyan
    
    # Tuer tous les processus Python backend existants
    Get-Process -Name "python*" -ErrorAction SilentlyContinue | ForEach-Object {
        $processInfo = Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)" -ErrorAction SilentlyContinue
        if ($processInfo -and $processInfo.CommandLine -like "*app.py*") {
            Write-Host "    Arret processus backend existant (PID: $($_.Id))" -ForegroundColor Orange
            Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
        }
    }
    
    Start-Sleep -Seconds 2
    
    # Tenter démarrage sur le port testé
    $env:PORT = $testPort
    $backendJob = Start-Job -ScriptBlock {
        Set-Location $using:PWD
        & .\scripts\env\activate_project_env.ps1 -CommandToRun "python argumentation_analysis/services/web_api/app.py"
    }
    
    # Attendre et tester la connectivité
    $connected = $false
    for ($wait = 1; $wait -le $TimeoutSeconds; $wait++) {
        Start-Sleep -Seconds 1
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:$testPort/api/health" -TimeoutSec 2 -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Write-Host "    SUCCES: Backend accessible sur port $testPort" -ForegroundColor Green
                $successPort = $testPort
                $connected = $true
                break
            }
        }
        catch {
            # Continuer à attendre
        }
        
        # Vérifier si le job a échoué
        if ($backendJob.State -eq "Failed" -or $backendJob.State -eq "Completed") {
            Write-Host "    ECHEC: Processus backend termine prematurement" -ForegroundColor Red
            break
        }
    }
    
    if (-not $connected) {
        Write-Host "    ECHEC: Timeout ou erreur sur port $testPort" -ForegroundColor Red
        Stop-Job $backendJob -ErrorAction SilentlyContinue
        Remove-Job $backendJob -ErrorAction SilentlyContinue
    } else {
        # Arrêter le backend test
        Stop-Job $backendJob -ErrorAction SilentlyContinue
        Remove-Job $backendJob -ErrorAction SilentlyContinue
        break
    }
}

# 6. Résumé et recommandations
Write-Host "`n=== RESUME DIAGNOSTIC ===" -ForegroundColor Cyan
if ($successPort) {
    Write-Host "PORT FONCTIONNEL TROUVE: $successPort" -ForegroundColor Green
    Write-Host "RECOMMANDATION: Utiliser le port $successPort pour les tests" -ForegroundColor Yellow
} else {
    Write-Host "AUCUN PORT FONCTIONNEL TROUVE" -ForegroundColor Red
    Write-Host "PROBLEMES DETECTES:" -ForegroundColor Yellow
    Write-Host "  - Conflit JPype/JVM probable" -ForegroundColor Red
    Write-Host "  - Verifier configuration Java" -ForegroundColor Red
    Write-Host "  - Nettoyer processus en conflit" -ForegroundColor Red
}

Write-Host "`nDiagnostic termine." -ForegroundColor Cyan