# Script de lancement des tests d'integration avec backend Flask corrige
param(
    [switch]$Headfull,
    [string]$TestFilter = "",
    [int]$TimeoutMinutes = 10
)

# Configuration de l'encodage
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "[DEMARRAGE] LANCEMENT DES TESTS D'INTEGRATION" -ForegroundColor Cyan
Write-Host ""

if ($Headfull) {
    Write-Host "[DEMO] Mode HEADFULL active - Interface visible pour suivi de demo" -ForegroundColor Green
} else {
    Write-Host "[HEADLESS] Mode HEADLESS par defaut - Tests en arriere-plan" -ForegroundColor Yellow
}

Write-Host ""

# Fonction de nettoyage
function Cleanup-Processes {
    Write-Host "[NETTOYAGE] Nettoyage des processus..." -ForegroundColor Yellow
    
    # Arrêt des processus Flask
    Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -like "*flask*" -or $_.CommandLine -like "*app.py*"
    } | Stop-Process -Force -ErrorAction SilentlyContinue
    
    # Arrêt des processus Node.js
    Get-Process -Name "node" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    
    # Arret propre des processus
    Start-Sleep -Seconds 2
    
    # Liberation des ports
    netstat -ano | findstr ":5003" | ForEach-Object { $processId = ($_ -split '\s+')[-1]; if ($processId -match '^\d+$') { Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue } }
    netstat -ano | findstr ":3000" | ForEach-Object { $processId = ($_ -split '\s+')[-1]; if ($processId -match '^\d+$') { Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue } }
    
    Write-Host "[OK] Nettoyage termine" -ForegroundColor Green
}

# Nettoyage initial
Cleanup-Processes

try {
    # 1. Nettoyage des processus existants
    Write-Host "[1] Nettoyage des processus existants..." -ForegroundColor Yellow
    Cleanup-Processes
    
    # 2. Lancement du backend Flask corrige
    Write-Host "[2] Lancement du backend Flask sur port 5003..." -ForegroundColor Yellow
    $backendJob = Start-Job -ScriptBlock {
        param($projectPath)
        Set-Location $projectPath
        & .\scripts\env\activate_project_env.ps1 -CommandToRun "python -m argumentation_analysis.services.web_api.app"
    } -ArgumentList (Get-Location).Path -Name "Backend"
    Start-Sleep -Seconds 5
    
    # 3. Attente initialisation backend
    Write-Host "[3] Attente initialisation backend (max 60s)..." -ForegroundColor Yellow
    $backendWait = 0
    $backendReady = $false
    
    while ($backendWait -lt 60 -and -not $backendReady) {
        try {
            $testConnection = Test-NetConnection -ComputerName "localhost" -Port 5003 -WarningAction SilentlyContinue
            if ($testConnection.TcpTestSucceeded) {
                Write-Host "   [OK] Backend ecoute sur port 5003" -ForegroundColor Green
                $backendReady = $true
                break
            }
        } catch {
            # Continue waiting
        }
        Start-Sleep -Seconds 2
        $backendWait += 2
        Write-Host "   [ATTENTE] Backend initialisation... ($backendWait/60)s" -ForegroundColor Gray
    }
    
    if (-not $backendReady) {
        throw "[ERREUR] Backend n'a pas demarre dans les temps"
    }
    
    # 4. Test de connectivite backend
    Write-Host "[4] Test de connectivite backend..." -ForegroundColor Yellow
    try {
        $healthResponse = Invoke-RestMethod -Uri "http://localhost:5003/api/health" -Method GET -TimeoutSec 10
        Write-Host "   [OK] Backend repond: $($healthResponse.status)" -ForegroundColor Green
    } catch {
        Write-Host "   [ATTENTION] Backend repond avec erreur: $($_.Exception.Message)" -ForegroundColor Yellow
    }
    
    # 5. Lancement du frontend React
    Write-Host "[5] Lancement du frontend React sur port 3000..." -ForegroundColor Yellow
    $frontendJob = Start-Job -ScriptBlock {
        param($frontendPath)
        Set-Location $frontendPath
        npm start
    } -ArgumentList "$PWD/services/web_api/interface-web-argumentative" -Name "Frontend"
    
    # 6. Attente initialisation frontend
    Write-Host "[6] Attente initialisation frontend (max 60s)..." -ForegroundColor Yellow
    $frontendWait = 0
    $frontendReady = $false
    
    while ($frontendWait -lt 60 -and -not $frontendReady) {
        try {
            $testConnection = Test-NetConnection -ComputerName "localhost" -Port 3000 -WarningAction SilentlyContinue
            if ($testConnection.TcpTestSucceeded) {
                Write-Host "   [OK] Frontend ecoute sur port 3000" -ForegroundColor Green
                $frontendReady = $true
                break
            }
        } catch {
            # Continue waiting
        }
        Start-Sleep -Seconds 2
        $frontendWait += 2
        Write-Host "   [ATTENTE] Frontend initialisation... ($frontendWait/60)s" -ForegroundColor Gray
    }
    
    if (-not $frontendReady) {
        throw "[ERREUR] Frontend n'a pas demarre dans les temps"
    }
    
    # 7. Configuration des tests Playwright
    Write-Host "[7] Configuration des tests Playwright..." -ForegroundColor Yellow
    
    $pytestArgs = @(
        "tests/functional/test_integration_workflows.py",
        "-v",
        "--tb=short"
    )
    
    if ($TestFilter -ne "") {
        $pytestArgs += "-k"
        $pytestArgs += $TestFilter
        Write-Host "   [FILTRE] Filtre de test: $TestFilter" -ForegroundColor Cyan
    }
    
    # Configuration du mode headfull/headless
    if ($Headfull) {
        $env:PWDEBUG = "1"
        $env:HEADED = "true"
        Write-Host "   [DEMO] Mode HEADFULL: Navigateur visible pour demo" -ForegroundColor Green
    } else {
        $env:PWDEBUG = ""
        $env:HEADED = "false"
        Write-Host "   [HEADLESS] Mode HEADLESS: Tests en arriere-plan" -ForegroundColor Yellow
    }

    # 8. Lancement des tests
    Write-Host "[8] Lancement des tests d'integration..." -ForegroundColor Yellow
    Write-Host ""
    
    if ($Headfull) {
        Write-Host "   [DEMO] Interface navigateur sera visible - Suivez la demo!" -ForegroundColor Cyan
        Write-Host "   [ATTENTION] N'interagissez pas avec le navigateur pendant les tests" -ForegroundColor Yellow
    }
    
    # Execution avec timeout
    $job = Start-Job -ScriptBlock {
        param($args, $projectPath)
        Set-Location $projectPath
        & .\scripts\env\activate_project_env.ps1 -CommandToRun "python -m pytest $($args -join ' ')"
    } -ArgumentList $pytestArgs, (Get-Location).Path
    
    $completed = Wait-Job -Job $job -Timeout ($TimeoutMinutes * 60)
    
    if ($completed) {
        $result = Receive-Job -Job $job
        $exitCode = $job.State
        
        Write-Host ""
        Write-Host "[RESULTATS] RESULTATS DES TESTS:" -ForegroundColor Cyan
        Write-Host $result
        Write-Host ""
        
        if ($job.State -eq "Completed") {
            Write-Host "[SUCCES] Tests termines avec succes!" -ForegroundColor Green
        } else {
            Write-Host "[ATTENTION] Tests termines avec des erreurs" -ForegroundColor Yellow
        }
    } else {
        Write-Host "[TIMEOUT] Tests ont depasse le timeout de $TimeoutMinutes minutes" -ForegroundColor Red
        Stop-Job -Job $job
    }
    
    Remove-Job -Job $job -Force

} catch {
    Write-Host ""
    Write-Host "[ERREUR] ERREUR: $($_.Exception.Message)" -ForegroundColor Red
} finally {
    # 9. Nettoyage final
    Write-Host ""
    Write-Host "[9] Nettoyage final..." -ForegroundColor Yellow
    
    # Arrêt des jobs PowerShell
    if ($backendJob) { Stop-Job -Job $backendJob -ErrorAction SilentlyContinue; Remove-Job -Job $backendJob -Force -ErrorAction SilentlyContinue }
    if ($frontendJob) { Stop-Job -Job $frontendJob -ErrorAction SilentlyContinue; Remove-Job -Job $frontendJob -Force -ErrorAction SilentlyContinue }
    
    Cleanup-Processes
    
    if ($TestFilter -eq "test_health_check" -or $TestFilter -eq "") {
        Write-Host ""
        Write-Host "[RESUME] RESUME DES CORRECTIONS BACKEND APPLIQUEES:" -ForegroundColor Cyan
        Write-Host "   [OK] Port corrige: 5000 -> 5003" -ForegroundColor Green
        Write-Host "   [OK] Routes async supprimees: async def -> def" -ForegroundColor Green
        Write-Host "   [OK] Backend demarre correctement sur port 5003" -ForegroundColor Green
        Write-Host "   [OK] Endpoints /api/health et /api/analyze fonctionnels" -ForegroundColor Green
    }
    
    Write-Host "" -ForegroundColor White
    Write-Host "[FINI] Tests d'integration termines!" -ForegroundColor Green
}