#!/usr/bin/env pwsh
# Script d'intégration complet avec failover backend

param(
    [switch]$Headfull,
    [string]$TestFilter = "",
    [int]$TimeoutMinutes = 10,
    [int]$BackendStartPort = 5003,
    [int]$BackendMaxAttempts = 5,
    [switch]$GenerateDetailedTrace
)

# Désactiver interactivité
$ErrorActionPreference = "SilentlyContinue"
$WarningPreference = "SilentlyContinue"
$env:CONDA_ALWAYS_YES = "true"
$env:PYTHONUNBUFFERED = "1"

Write-Host "=== INTEGRATION TESTS AVEC FAILOVER ===" -ForegroundColor Cyan
Write-Host "Headfull: $Headfull | Filter: '$TestFilter' | Timeout: $TimeoutMinutes min | Trace: $GenerateDetailedTrace" -ForegroundColor Yellow

$global:BackendJob = $null
$global:FrontendJob = $null
$global:BackendPort = $null

# Variables pour la trace détaillée
$script:TraceActions = @()
$script:StartTime = Get-Date

function Add-TraceAction {
    param($Action, $Details, $Result = "")
    if ($GenerateDetailedTrace) {
        $timestamp = Get-Date -Format "HH:mm:ss.fff"
        $entry = [PSCustomObject]@{
            Timestamp = $timestamp
            Action = $Action
            Details = $Details
            Result = $Result
        }
        $script:TraceActions += $entry
        Write-Host "[$timestamp] $Action" -ForegroundColor Cyan
        if ($Details) { Write-Host "   Details: $Details" -ForegroundColor Gray }
        if ($Result) { Write-Host "   Result: $Result" -ForegroundColor Green }
    }
}

# Fonction de nettoyage
function Cleanup-Services {
    Write-Host "`n[NETTOYAGE] Arrêt des services..." -ForegroundColor Yellow
    
    # Arrêt jobs PowerShell
    if ($global:BackendJob) {
        Stop-Job $global:BackendJob -ErrorAction SilentlyContinue
        Remove-Job $global:BackendJob -ErrorAction SilentlyContinue
    }
    if ($global:FrontendJob) {
        Stop-Job $global:FrontendJob -ErrorAction SilentlyContinue
        Remove-Job $global:FrontendJob -ErrorAction SilentlyContinue
    }
    
    # Arrêt processus Python
    Get-Process -Name "python*" -ErrorAction SilentlyContinue | Where-Object {
        $cmdline = (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)" -ErrorAction SilentlyContinue).CommandLine
        $cmdline -and ($cmdline -like "*app.py*" -or $cmdline -like "*web_api*")
    } | ForEach-Object {
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }
    
    # Arrêt serveurs Node.js (frontend)
    Get-Process -Name "node*" -ErrorAction SilentlyContinue | Where-Object {
        $cmdline = (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)" -ErrorAction SilentlyContinue).CommandLine
        $cmdline -and ($cmdline -like "*serve*" -or $cmdline -like "*dev*")
    } | ForEach-Object {
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }
    
    Start-Sleep -Seconds 2
}

# Gestionnaire d'interruption
Register-EngineEvent PowerShell.Exiting -Action { Cleanup-Services }

try {
    # 1. DEMARRAGE BACKEND AVEC FAILOVER
    Write-Host "`n[1] Démarrage backend avec failover..." -ForegroundColor Cyan
    Add-TraceAction "DEMARRAGE BACKEND" "Lancement backend avec failover sur port $BackendStartPort"
    
    $backendResult = & ".\scripts\backend_failover_non_interactive.ps1" -Background -StartPort $BackendStartPort -MaxAttempts $BackendMaxAttempts -TimeoutSeconds 30
    
    if (-not (Test-Path "backend_info.json")) {
        Write-Host "ERREUR: Échec démarrage backend" -ForegroundColor Red
        exit 1
    }
    
    $backendInfo = Get-Content "backend_info.json" | ConvertFrom-Json
    if ($backendInfo.Status -ne "SUCCESS") {
        Write-Host "ERREUR: Backend non opérationnel" -ForegroundColor Red
        exit 1
    }
    
    $global:BackendPort = $backendInfo.Port
    Write-Host "Backend opérationnel sur port: $global:BackendPort" -ForegroundColor Green
    Add-TraceAction "BACKEND OPERATIONNEL" "Port: $global:BackendPort | Job ID: $($backendInfo.JobId)" "Backend accessible sur http://localhost:$global:BackendPort"
    
    # 2. VERIFICATION BACKEND
    Write-Host "`n[2] Vérification accessibilité backend..." -ForegroundColor Cyan
    Add-TraceAction "VERIFICATION BACKEND" "Test endpoint /api/health"
    
    $maxRetries = 10
    $backendReady = $false
    for ($retry = 1; $retry -le $maxRetries; $retry++) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:$global:BackendPort/api/health" -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Write-Host "Backend accessible: OK" -ForegroundColor Green
                Add-TraceAction "BACKEND ACCESSIBLE" "Status Code: $($response.StatusCode)" "Endpoint /api/health répond correctement"
                $backendReady = $true
                break
            }
        }
        catch {
            Start-Sleep -Seconds 2
        }
    }
    
    if (-not $backendReady) {
        Write-Host "ERREUR: Backend non accessible" -ForegroundColor Red
        exit 1
    }
    
    # 3. DEMARRAGE FRONTEND
    Write-Host "`n[3] Démarrage frontend..." -ForegroundColor Cyan
    Add-TraceAction "DEMARRAGE FRONTEND" "Lancement interface React depuis $frontendPath"
    
    $frontendPath = "services\web_api\interface-web-argumentative"
    if (-not (Test-Path $frontendPath)) {
        Write-Host "ERREUR: Répertoire frontend non trouvé: $frontendPath" -ForegroundColor Red
        exit 1
    }
    
    $global:FrontendJob = Start-Job -ScriptBlock {
        param($workDir, $frontendPath)
        Set-Location $workDir
        Set-Location $frontendPath
        $env:PYTHONUNBUFFERED = "1"
        
        # Installer dépendances si nécessaire
        if (-not (Test-Path "node_modules")) {
            npm install 2>&1
        }
        
        # Démarrer serveur dev
        npm run dev 2>&1
    } -ArgumentList $PWD, $frontendPath
    
    Write-Host "Frontend Job ID: $($global:FrontendJob.Id)" -ForegroundColor Green
    Add-TraceAction "FRONTEND LANCE" "Job ID: $($global:FrontendJob.Id)" "Interface React en cours de démarrage"
    
    # Attendre démarrage frontend
    Write-Host "Attente démarrage frontend..." -ForegroundColor Yellow
    Add-TraceAction "ATTENTE FRONTEND" "Délai de démarrage: 10 secondes"
    Start-Sleep -Seconds 10
    Add-TraceAction "FRONTEND PRET" "Délai d'attente écoulé" "Interface présumée disponible sur http://localhost:3000"
    
    # 4. CONFIGURATION TESTS PLAYWRIGHT
    Write-Host "`n[4] Configuration tests Playwright..." -ForegroundColor Cyan
    Add-TraceAction "CONFIGURATION TESTS" "Paramétrage environnement Playwright"
    
    # Mise à jour URL backend dans configuration test
    $testConfig = @"
BACKEND_URL=http://localhost:$global:BackendPort
FRONTEND_URL=http://localhost:3000
HEADLESS=$(-not $Headfull)
"@
    $testConfig | Out-File ".env.test" -Encoding UTF8
    Add-TraceAction "CONFIG CREEE" "Fichier: .env.test" "Variables d'environnement configurées"
    
    # 5. EXECUTION TESTS INTEGRATION
    Write-Host "`n[5] Exécution tests d'intégration..." -ForegroundColor Cyan
    Add-TraceAction "EXECUTION TESTS" "Lancement tests d'intégration Playwright"
    
    $testArgs = @()
    if ($TestFilter) {
        $testArgs += "-k", $TestFilter
    }
    if ($Headfull) {
        $testArgs += "--headed"
    }
    $testArgs += "tests/functional/test_integration_workflows.py"
    
    Write-Host "Arguments pytest: $($testArgs -join ' ')" -ForegroundColor Gray
    Add-TraceAction "PARAMETRES PYTEST" "Arguments: $($testArgs -join ' ')" "Mode: $(if($Headfull){'Interface visible'}else{'Interface cachée'})"
    
    # Exécution avec timeout
    $testProcess = Start-Process -FilePath "conda" -ArgumentList @("run", "-n", "projet-is", "python", "-m", "pytest") + $testArgs -PassThru -NoNewWindow -RedirectStandardOutput "test_output.log" -RedirectStandardError "test_error.log"
    
    $timeoutMs = $TimeoutMinutes * 60 * 1000
    if (-not $testProcess.WaitForExit($timeoutMs)) {
        Write-Host "TIMEOUT: Tests interrompus après $TimeoutMinutes minutes" -ForegroundColor Red
        $testProcess.Kill()
        exit 1
    }
    
    Add-TraceAction "TESTS TERMINES" "Code de sortie: $($testProcess.ExitCode)" "Durée d'exécution: $([math]::Round((New-TimeSpan -Start $script:StartTime).TotalSeconds, 2)) secondes"
    
    # 6. RESULTATS
    Write-Host "`n[6] Résultats des tests..." -ForegroundColor Cyan
    
    if (Test-Path "test_output.log") {
        Write-Host "=== SORTIE TESTS ===" -ForegroundColor Yellow
        Get-Content "test_output.log" | ForEach-Object { Write-Host $_ }
    }
    
    if (Test-Path "test_error.log") {
        $errorContent = Get-Content "test_error.log"
        if ($errorContent) {
            Write-Host "=== ERREURS TESTS ===" -ForegroundColor Red
            $errorContent | ForEach-Object { Write-Host $_ -ForegroundColor Red }
        }
    }
    
    $exitCode = $testProcess.ExitCode
    if ($exitCode -eq 0) {
        Write-Host "`nSUCCES: Tests d'intégration réussis" -ForegroundColor Green
        Add-TraceAction "TESTS REUSSIS" "Tous les tests d'intégration ont passé" "Code de sortie: 0"
    } else {
        Write-Host "`nECHEC: Tests d'intégration échoués (code: $exitCode)" -ForegroundColor Red
        Add-TraceAction "TESTS ECHECS" "Certains tests ont échoué" "Code de sortie: $exitCode"
    }
    
    # Génération du rapport détaillé si demandé
    if ($GenerateDetailedTrace) {
        Write-Host "`n[7] Génération rapport détaillé..." -ForegroundColor Cyan
        Generate-DetailedTrace -ExitCode $exitCode
    }
    
    exit $exitCode
    
} finally {
    Cleanup-Services
}

function Generate-DetailedTrace {
    param($ExitCode)
    
    $endTime = Get-Date
    $duration = ($endTime - $script:StartTime).TotalSeconds
    
    $traceContent = @"
# TRACE COMPLETE D'EXECUTION DES TESTS D'INTEGRATION
**Date d'execution:** $(Get-Date -Format "dd/MM/yyyy HH:mm:ss")
**Mode navigateur:** $(if($Headfull){'Interface Visible (Headfull)'}else{'Interface Cachee (Headless)'})
**Duree totale:** $duration secondes
**Statut:** $(if($ExitCode -eq 0){'SUCCES COMPLET'}else{'ECHEC PARTIEL'})
**Backend Port:** $global:BackendPort
**Frontend URL:** http://localhost:3000

---

## ACTIONS DETAILLEES

"@

    foreach ($action in $script:TraceActions) {
        $traceContent += @"
### $($action.Timestamp) - $($action.Action)
**Details:** $($action.Details)
$(if($action.Result){"**Result:** $($action.Result)"})

"@
    }

    $traceContent += @"
---

## RESUME D'EXECUTION

### 🔧 **Configuration Technique**
- **Backend démarré sur port:** $global:BackendPort
- **Frontend URL:** http://localhost:3000
- **Mode d'exécution:** $(if($Headfull){'Interface visible pour observation'}else{'Interface cachée pour performance'})
- **Filtre de test:** $(if($TestFilter){"'$TestFilter'"}else{"Aucun (tous les tests)"})
- **Timeout configuré:** $TimeoutMinutes minutes

### 📊 **Statistiques**
- **Nombre total d'actions:** $($script:TraceActions.Count)
- **Durée totale:** $duration secondes
- **Statut final:** $(if($ExitCode -eq 0){'✅ SUCCÈS'}else{'❌ ÉCHEC'})

### 📁 **Fichiers générés**
- **Logs de sortie:** test_output.log
- **Logs d'erreur:** test_error.log
- **Configuration test:** .env.test
- **Informations backend:** backend_info.json

### 🎯 **Tests exécutés**
- **Fichier de test:** tests/functional/test_integration_workflows.py
- **Arguments pytest:** $($testArgs -join ' ')
- **Code de sortie:** $ExitCode

---

*Cette trace documente l'exécution complète des tests d'intégration avec tous les services backend et frontend.*
"@

    $traceFileName = "integration_tests_detailed_trace_$(Get-Date -Format 'yyyy-MM-dd_HH-mm-ss').md"
    $traceContent | Out-File -FilePath $traceFileName -Encoding UTF8
    
    Write-Host "Trace détaillée générée: $traceFileName" -ForegroundColor Green
    Write-Host "Actions documentées: $($script:TraceActions.Count)" -ForegroundColor Gray
    Write-Host "Durée totale: $duration secondes" -ForegroundColor Gray
}