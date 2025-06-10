# Script PowerShell Non-Bloquant - Investigation Playwright Textes Variés
# Orchestration automatisée des tests avec différents textes

param(
    [string]$Mode = "complet",
    [switch]$NoWait,
    [switch]$ShowReport
)

$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"

Write-Host "🚀 INVESTIGATION PLAYWRIGHT - TEXTES VARIÉS" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

# Configuration
$PROJECT_ROOT = "c:\dev\2025-Epita-Intelligence-Symbolique"
$PLAYWRIGHT_DIR = "$PROJECT_ROOT\tests_playwright"
$TEMP_DIR = "$PROJECT_ROOT\_temp\investigation_playwright"

# Créer répertoire temporaire
if (-not (Test-Path $TEMP_DIR)) {
    New-Item -ItemType Directory -Path $TEMP_DIR -Force | Out-Null
}

# Timestamp pour les rapports
$TIMESTAMP = Get-Date -Format "yyyyMMdd_HHmmss"
$REPORT_FILE = "$TEMP_DIR\investigation_report_$TIMESTAMP.json"

Write-Host "📁 Répertoire: $PLAYWRIGHT_DIR" -ForegroundColor Green
Write-Host "📊 Rapport: $REPORT_FILE" -ForegroundColor Green

# Fonction pour vérifier les services
function Test-Services {
    Write-Host "`n🔍 VÉRIFICATION DES SERVICES" -ForegroundColor Yellow
    
    $services = @(
        @{ Name = "API Backend"; Url = "http://localhost:5003/api/health"; Port = 5003 },
        @{ Name = "Interface Web"; Url = "http://localhost:3000/status"; Port = 3000 }
    )
    
    $serviceStatus = @{}
    
    foreach ($service in $services) {
        try {
            $response = Invoke-WebRequest -Uri $service.Url -TimeoutSec 3 -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Write-Host "✅ $($service.Name) - Opérationnel" -ForegroundColor Green
                $serviceStatus[$service.Name] = "OK"
            } else {
                Write-Host "⚠️ $($service.Name) - Status $($response.StatusCode)" -ForegroundColor Yellow
                $serviceStatus[$service.Name] = "WARNING"
            }
        } catch {
            Write-Host "❌ $($service.Name) - Non accessible" -ForegroundColor Red
            $serviceStatus[$service.Name] = "ERROR"
        }
    }
    
    return $serviceStatus
}

# Fonction pour démarrer un service si nécessaire
function Start-ServiceIfNeeded {
    param([string]$ServiceName, [int]$Port, [string]$Command)
    
    $process = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    if (-not $process) {
        Write-Host "🚀 Démarrage $ServiceName sur port $Port..." -ForegroundColor Yellow
        
        # Démarrer en arrière-plan
        $job = Start-Job -ScriptBlock {
            param($cmd, $dir)
            Set-Location $dir
            Invoke-Expression $cmd
        } -ArgumentList $Command, $PROJECT_ROOT
        
        Write-Host "⏳ Service $ServiceName démarré (Job $($job.Id))" -ForegroundColor Green
        Start-Sleep 3
        return $job
    } else {
        Write-Host "✅ $ServiceName déjà actif sur port $Port" -ForegroundColor Green
        return $null
    }
}

# Vérifier et démarrer les services
Write-Host "`n🏗️ GESTION DES SERVICES" -ForegroundColor Yellow

$serviceJobs = @()

# Vérifier si API est active, sinon la démarrer
$apiJob = Start-ServiceIfNeeded -ServiceName "API Backend" -Port 5003 -Command "python -m uvicorn api.main_simple:app --host 0.0.0.0 --port 5003"
if ($apiJob) { $serviceJobs += $apiJob }

# Vérifier si Interface est active, sinon la démarrer  
$webJob = Start-ServiceIfNeeded -ServiceName "Interface Web" -Port 3000 -Command "python interface_web/app.py"
if ($webJob) { $serviceJobs += $webJob }

# Attendre que les services soient prêts
if ($serviceJobs.Count -gt 0) {
    Write-Host "⏳ Attente de la préparation des services..." -ForegroundColor Yellow
    Start-Sleep 5
}

# Vérifier l'état des services
$serviceStatus = Test-Services

# Préparer l'environnement Playwright
Write-Host "`n🎭 PRÉPARATION PLAYWRIGHT" -ForegroundColor Yellow

Set-Location $PLAYWRIGHT_DIR

# Vérifier que les dépendances sont installées
if (-not (Test-Path "node_modules")) {
    Write-Host "📦 Installation des dépendances npm..." -ForegroundColor Yellow
    npm install | Out-Null
}

# Configuration des tests selon le mode
$testCommands = @()

switch ($Mode) {
    "complet" {
        Write-Host "🎯 Mode COMPLET - Tous les tests" -ForegroundColor Cyan
        $testCommands += "npx playwright test investigation-textes-varies.spec.js --reporter=json"
        $testCommands += "npx playwright test api-backend.spec.js --reporter=json"
        $testCommands += "npx playwright test flask-interface.spec.js --reporter=json"
    }
    "investigation" {
        Write-Host "🔍 Mode INVESTIGATION - Tests variés uniquement" -ForegroundColor Cyan
        $testCommands += "npx playwright test investigation-textes-varies.spec.js --reporter=json"
    }
    "rapide" {
        Write-Host "⚡ Mode RAPIDE - Tests essentiels" -ForegroundColor Cyan
        $testCommands += "npx playwright test investigation-textes-varies.spec.js --grep='API - Test complet' --reporter=json"
    }
    default {
        Write-Host "❓ Mode inconnu, utilisation du mode investigation" -ForegroundColor Yellow
        $testCommands += "npx playwright test investigation-textes-varies.spec.js --reporter=json"
    }
}

# Exécution des tests
Write-Host "`n🧪 EXÉCUTION DES TESTS" -ForegroundColor Yellow

$testResults = @()
$testStartTime = Get-Date

foreach ($command in $testCommands) {
    Write-Host "`n▶️ Exécution: $command" -ForegroundColor Cyan
    
    $testStart = Get-Date
    
    try {
        if ($NoWait) {
            # Mode non-bloquant
            $testJob = Start-Job -ScriptBlock {
                param($cmd, $dir)
                Set-Location $dir
                $output = Invoke-Expression $cmd 2>&1
                return @{
                    Output = $output
                    ExitCode = $LASTEXITCODE
                    Command = $cmd
                }
            } -ArgumentList $command, $PLAYWRIGHT_DIR
            
            Write-Host "🚀 Test lancé en arrière-plan (Job $($testJob.Id))" -ForegroundColor Green
            $testResults += @{
                Command = $command
                Status = "RUNNING"
                JobId = $testJob.Id
                StartTime = $testStart
            }
        } else {
            # Mode synchrone avec timeout
            $process = Start-Process -FilePath "cmd" -ArgumentList "/c", $command -WorkingDirectory $PLAYWRIGHT_DIR -PassThru -WindowStyle Hidden
            
            if ($process.WaitForExit(30000)) {
                $exitCode = $process.ExitCode
                $status = if ($exitCode -eq 0) { "SUCCESS" } else { "FAILURE" }
                
                Write-Host "✅ Test terminé: $status (Code: $exitCode)" -ForegroundColor $(if ($exitCode -eq 0) { "Green" } else { "Red" })
            } else {
                $process.Kill()
                Write-Host "⏰ Test interrompu (timeout 30s)" -ForegroundColor Yellow
                $status = "TIMEOUT"
                $exitCode = -1
            }
            
            $testResults += @{
                Command = $command
                Status = $status
                ExitCode = $exitCode
                Duration = (Get-Date) - $testStart
                StartTime = $testStart
            }
        }
    } catch {
        Write-Host "❌ Erreur: $($_.Exception.Message)" -ForegroundColor Red
        $testResults += @{
            Command = $command
            Status = "ERROR"
            Error = $_.Exception.Message
            StartTime = $testStart
        }
    }
    
    # Pause entre les tests
    Start-Sleep 1
}

# Attendre les jobs si mode non-bloquant
if ($NoWait -and (Get-Job -State Running | Where-Object { $_.Name -like "*test*" })) {
    Write-Host "`n⏳ Attente des tests en cours..." -ForegroundColor Yellow
    
    $timeout = 60 # 60 secondes max
    $elapsed = 0
    
    while ((Get-Job -State Running | Where-Object { $_.Name -like "*test*" }) -and $elapsed -lt $timeout) {
        Start-Sleep 2
        $elapsed += 2
        Write-Host "." -NoNewline -ForegroundColor Yellow
    }
    Write-Host ""
    
    # Récupérer les résultats des jobs
    foreach ($result in $testResults | Where-Object { $_.Status -eq "RUNNING" }) {
        $job = Get-Job -Id $result.JobId -ErrorAction SilentlyContinue
        if ($job) {
            if ($job.State -eq "Completed") {
                $jobResult = Receive-Job -Job $job
                $result.Status = if ($jobResult.ExitCode -eq 0) { "SUCCESS" } else { "FAILURE" }
                $result.ExitCode = $jobResult.ExitCode
                $result.Duration = (Get-Date) - $result.StartTime
            } else {
                $result.Status = "INCOMPLETE"
            }
            Remove-Job -Job $job -Force
        }
    }
}

# Génération du rapport
Write-Host "`n📊 GÉNÉRATION DU RAPPORT" -ForegroundColor Yellow

$totalDuration = (Get-Date) - $testStartTime
$successCount = ($testResults | Where-Object { $_.Status -eq "SUCCESS" }).Count
$totalTests = $testResults.Count

$report = @{
    Timestamp = $TIMESTAMP
    Mode = $Mode
    Duration = $totalDuration.TotalSeconds
    Services = $serviceStatus
    Tests = @{
        Total = $totalTests
        Success = $successCount
        SuccessRate = if ($totalTests -gt 0) { [math]::Round(($successCount / $totalTests) * 100, 2) } else { 0 }
        Results = $testResults
    }
    Environment = @{
        PlaywrightDir = $PLAYWRIGHT_DIR
        ProjectRoot = $PROJECT_ROOT
        PowerShellVersion = $PSVersionTable.PSVersion.ToString()
    }
}

# Sauvegarder le rapport JSON
$report | ConvertTo-Json -Depth 10 | Set-Content -Path $REPORT_FILE -Encoding UTF8

Write-Host "💾 Rapport sauvegardé: $REPORT_FILE" -ForegroundColor Green

# Affichage du résumé
Write-Host "`n📋 RÉSUMÉ FINAL" -ForegroundColor Cyan
Write-Host "===============" -ForegroundColor Cyan
Write-Host "🎯 Mode: $Mode" -ForegroundColor White
Write-Host "⏱️ Durée totale: $([math]::Round($totalDuration.TotalSeconds, 2))s" -ForegroundColor White
Write-Host "🧪 Tests: $successCount/$totalTests réussis ($($report.Tests.SuccessRate)%)" -ForegroundColor $(if ($report.Tests.SuccessRate -gt 80) { "Green" } else { "Yellow" })

foreach ($service in $serviceStatus.GetEnumerator()) {
    $color = switch ($service.Value) {
        "OK" { "Green" }
        "WARNING" { "Yellow" }
        default { "Red" }
    }
    Write-Host "🔧 $($service.Key): $($service.Value)" -ForegroundColor $color
}

# Ouvrir le rapport si demandé
if ($ShowReport) {
    if (Test-Path $REPORT_FILE) {
        Write-Host "`n📖 Ouverture du rapport..." -ForegroundColor Yellow
        Start-Process notepad $REPORT_FILE
    }
    
    # Ouvrir le rapport HTML Playwright s'il existe
    $htmlReport = "$PLAYWRIGHT_DIR\playwright-report\index.html"
    if (Test-Path $htmlReport) {
        Write-Host "🌐 Ouverture du rapport HTML Playwright..." -ForegroundColor Yellow
        Start-Process $htmlReport
    }
}

# Nettoyage des jobs restants
Get-Job | Remove-Job -Force -ErrorAction SilentlyContinue

Write-Host "`n🏁 Investigation terminée!" -ForegroundColor Green
Write-Host "📁 Résultats dans: $TEMP_DIR" -ForegroundColor Green

exit 0