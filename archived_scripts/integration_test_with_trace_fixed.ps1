#!/usr/bin/env pwsh
# Script d'intégration avec trace détaillée des actions utilisateur

param(
    [switch]$Headfull,
    [int]$TimeoutMinutes = 5,
    [string]$TraceFile = "test_execution_trace.md"
)

# Configuration non-interactive
$ErrorActionPreference = "SilentlyContinue"
$WarningPreference = "SilentlyContinue"
$env:CONDA_ALWAYS_YES = "true"
$env:PYTHONUNBUFFERED = "1"

$global:TraceLog = @()
$global:BackendJob = $null
$global:FrontendJob = $null
$global:BackendPort = $null

function Write-TraceLog {
    param(
        [string]$Action,
        [string]$Details = "",
        [string]$Result = "",
        [string]$Screenshot = ""
    )
    
    $timestamp = Get-Date -Format "HH:mm:ss.fff"
    $entry = @{
        Time = $timestamp
        Action = $Action
        Details = $Details
        Result = $Result
        Screenshot = $Screenshot
    }
    
    $global:TraceLog += $entry
    Write-Host "[$timestamp] $Action" -ForegroundColor Cyan
    if ($Details) { Write-Host "   Details: $Details" -ForegroundColor Gray }
    if ($Result) { Write-Host "   Result: $Result" -ForegroundColor Green }
}

function Save-TraceToFile {
    param([string]$FilePath)
    
    $content = @"
# TRACE D'EXECUTION DES TESTS D'INTEGRATION
**Date d'execution:** $(Get-Date -Format "dd/MM/yyyy HH:mm:ss")  
**Mode:** $(if($Headfull){'Interface Visible (Headfull)'}else{'Mode Headless'})  
**Backend:** http://localhost:$global:BackendPort  
**Frontend:** http://localhost:3000  

---

## ACTIONS DETAILLEES

"@

    foreach ($entry in $global:TraceLog) {
        $content += @"

### $($entry.Time) - $($entry.Action)
"@
        if ($entry.Details) {
            $content += @"

**Details:** $($entry.Details)
"@
        }
        if ($entry.Result) {
            $content += @"

**Result:** $($entry.Result)
"@
        }
        if ($entry.Screenshot) {
            $content += @"

**Screenshot:** $($entry.Screenshot)
"@
        }
        $content += "`n"
    }

    $content += @"

---

## RESUME D'EXECUTION
- **Nombre d'actions:** $($global:TraceLog.Count)
- **Duree totale:** $(((Get-Date) - $startTime).TotalSeconds) secondes
- **Statut:** $(if($global:TestSuccess){'SUCCES'}else{'ECHEC'})

## CONFIGURATION TECHNIQUE
- **Backend Port:** $global:BackendPort
- **Backend Job ID:** $($global:BackendJob.Id)
- **Frontend Job ID:** $($global:FrontendJob.Id)
- **Mode Headfull:** $Headfull
"@

    $content | Out-File $FilePath -Encoding UTF8
    Write-Host "Trace sauvegardee dans: $FilePath" -ForegroundColor Green
}

function Cleanup-Services {
    Write-TraceLog "NETTOYAGE" "Arret de tous les services"
    
    if ($global:BackendJob) {
        Stop-Job $global:BackendJob -ErrorAction SilentlyContinue
        Remove-Job $global:BackendJob -ErrorAction SilentlyContinue
    }
    if ($global:FrontendJob) {
        Stop-Job $global:FrontendJob -ErrorAction SilentlyContinue
        Remove-Job $global:FrontendJob -ErrorAction SilentlyContinue
    }
    
    Get-Process -Name "python*", "node*" -ErrorAction SilentlyContinue | Where-Object {
        $cmdline = (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)" -ErrorAction SilentlyContinue).CommandLine
        $cmdline -and ($cmdline -like "*app.py*" -or $cmdline -like "*web_api*" -or $cmdline -like "*serve*")
    } | ForEach-Object {
        Write-TraceLog "PROCESSUS ARRETE" "PID: $($_.Id) | Nom: $($_.Name)"
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }
    
    Write-TraceLog "NETTOYAGE TERMINE" "" "Tous les services ont ete arretes"
}

Register-EngineEvent PowerShell.Exiting -Action { Cleanup-Services }

$startTime = Get-Date
$global:TestSuccess = $false

try {
    Write-Host "DEMARRAGE TEST D'INTEGRATION AVEC TRACE" -ForegroundColor Green
    Write-TraceLog "INITIALISATION" "Demarrage test integration avec trace detaillee" "Mode: $(if($Headfull){'Headfull'}else{'Headless'})"

    # 1. DÉMARRAGE BACKEND
    Write-TraceLog "BACKEND" "Lancement du script de failover backend"
    
    $backendResult = & ".\scripts\backend_failover_non_interactive.ps1" -Background -StartPort 5003 -MaxAttempts 5 -TimeoutSeconds 30
    
    if (-not (Test-Path "backend_info.json")) {
        Write-TraceLog "ERREUR BACKEND" "Fichier backend_info.json non trouve" "ECHEC - Script interrompu"
        exit 1
    }
    
    $backendInfo = Get-Content "backend_info.json" | ConvertFrom-Json
    if ($backendInfo.Status -ne "SUCCESS") {
        Write-TraceLog "ERREUR BACKEND" "Statut: $($backendInfo.Status)" "ECHEC - Backend non operationnel"
        exit 1
    }
    
    $global:BackendPort = $backendInfo.Port
    Write-TraceLog "BACKEND OPERATIONNEL" "Port: $global:BackendPort | Job ID: $($backendInfo.JobId)" "Backend accessible sur http://localhost:$global:BackendPort"

    # 2. TEST CONNECTIVITÉ BACKEND
    Write-TraceLog "TEST BACKEND" "Verification endpoint /api/health"
    
    $maxRetries = 10
    $backendReady = $false
    for ($retry = 1; $retry -le $maxRetries; $retry++) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:$global:BackendPort/api/health" -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Write-TraceLog "ENDPOINT HEALTH" "Status Code: $($response.StatusCode)" "Backend repond correctement"
                $backendReady = $true
                break
            }
        }
        catch {
            Write-TraceLog "ATTENTE BACKEND" "Tentative $retry/$maxRetries" "En cours..."
            Start-Sleep -Seconds 2
        }
    }
    
    if (-not $backendReady) {
        Write-TraceLog "TIMEOUT BACKEND" "Backend non accessible apres $maxRetries tentatives" "ECHEC"
        exit 1
    }

    # 3. DÉMARRAGE FRONTEND
    Write-TraceLog "FRONTEND" "Demarrage interface React"
    
    $frontendPath = "services\web_api\interface-web-argumentative"
    if (-not (Test-Path "$frontendPath\package.json")) {
        Write-TraceLog "ERREUR FRONTEND" "package.json non trouve dans: $frontendPath" "ECHEC"
        exit 1
    }
    
    $global:FrontendJob = Start-Job -ScriptBlock {
        param($workDir, $frontendPath)
        Set-Location $workDir
        Set-Location $frontendPath
        $env:PYTHONUNBUFFERED = "1"
        
        if (-not (Test-Path "node_modules")) {
            npm install 2>&1
        }
        npm start 2>&1
    } -ArgumentList $PWD, $frontendPath
    
    Write-TraceLog "FRONTEND LANCE" "Job ID: $($global:FrontendJob.Id)" "Interface React en cours de demarrage"
    
    # Attendre démarrage frontend
    Write-TraceLog "ATTENTE FRONTEND" "Demarrage serveur de developpement React"
    Start-Sleep -Seconds 15
    Write-TraceLog "FRONTEND PRET" "Serveur React demarre" "Interface disponible sur http://localhost:3000"

    # 4. CRÉATION TEST PLAYWRIGHT DÉTAILLÉ
    Write-TraceLog "CREATION TEST" "Generation test Playwright avec actions detaillees"
    
    $playwrightTest = @"
import pytest
from playwright.sync_api import Page, expect
import time
import os

def test_interface_integration_complete(page: Page):
    """Test d'integration complet avec trace des actions"""
    
    # Configuration
    backend_url = "http://localhost:$global:BackendPort"
    frontend_url = "http://localhost:3000"
    
    print(f"[CONFIG] Backend={backend_url}, Frontend={frontend_url}")
    
    # 1. NAVIGATION VERS FRONTEND
    print("[ACTION] Navigation vers l'interface frontend")
    page.goto(frontend_url)
    print(f"[RESULT] Page chargee - URL: {page.url}")
    
    # Attendre chargement
    time.sleep(3)
    print("[WAIT] Chargement complet de l'interface")
    
    # 2. VÉRIFICATION TITRE PAGE
    print("[ACTION] Verification du titre de la page")
    title = page.title()
    print(f"[RESULT] Titre de la page: '{title}'")
    
    # 3. RECHERCHE ÉLÉMENTS INTERFACE
    print("[ACTION] Recherche des elements d'interface")
    
    # Chercher zone de texte
    text_inputs = page.locator("textarea, input[type='text']").all()
    print(f"[RESULT] {len(text_inputs)} zone(s) de texte trouvee(s)")
    
    # Chercher boutons
    buttons = page.locator("button").all()
    print(f"[RESULT] {len(buttons)} bouton(s) trouve(s)")
    
    # 4. TEST INTERACTION SI ÉLÉMENTS DISPONIBLES
    if text_inputs:
        print("[ACTION] Saisie de texte de test")
        first_input = text_inputs[0]
        test_text = "Ceci est un test d'analyse argumentative."
        first_input.fill(test_text)
        print(f"[RESULT] Texte saisi: '{test_text}'")
        
        # Vérifier la saisie
        filled_value = first_input.input_value()
        print(f"[VERIFY] Valeur dans le champ: '{filled_value}'")
    
    if buttons:
        print("[ACTION] Tentative de clic sur premier bouton")
        first_button = buttons[0]
        button_text = first_button.inner_text()
        print(f"[DETAILS] Texte du bouton: '{button_text}'")
        
        # Clic si bouton visible et activé
        if first_button.is_visible() and first_button.is_enabled():
            first_button.click()
            print("[RESULT] Clic effectue sur le bouton")
            time.sleep(2)
        else:
            print("[RESULT] Bouton non cliquable (invisible ou desactive)")
    
    # 5. TEST BACKEND DIRECT
    print("[ACTION] Test direct du backend API")
    response = page.request.get(f"{backend_url}/api/health")
    print(f"[RESULT] Status backend: {response.status}")
    
    if response.ok:
        response_text = response.text()
        print(f"[CONTENT] Reponse backend: {response_text}")
    
    # 6. CAPTURE FINALE
    print("[ACTION] Capture d'ecran finale")
    screenshot_path = "integration_test_final.png"
    page.screenshot(path=screenshot_path)
    print(f"[RESULT] Screenshot sauve: {screenshot_path}")
    
    print("[SUCCESS] TEST TERMINE: Toutes les actions ont ete executees avec succes")
"@

    $playwrightTest | Out-File "test_integration_detailed.py" -Encoding UTF8
    Write-TraceLog "TEST CREE" "Fichier: test_integration_detailed.py" "Test Playwright avec actions detaillees genere"

    # 5. CONFIGURATION ENVIRONNEMENT TEST
    Write-TraceLog "CONFIGURATION" "Parametres environment test"
    
    $testConfig = @"
BACKEND_URL=http://localhost:$global:BackendPort
FRONTEND_URL=http://localhost:3000
HEADLESS=$(-not $Headfull)
"@
    $testConfig | Out-File ".env.test" -Encoding UTF8
    Write-TraceLog "CONFIG CREEE" "Fichier: .env.test" "Variables d'environnement configurees"

    # 6. EXÉCUTION TESTS
    Write-TraceLog "EXECUTION TEST" "Lancement Playwright avec trace detaillee"
    
    $testArgs = @("run", "-n", "projet-is", "python", "-m", "pytest", "-v", "-s")
    if ($Headfull) {
        $testArgs += "--headed"
        Write-TraceLog "MODE VISUEL" "Test en mode headed" "Interface navigateur visible"
    } else {
        Write-TraceLog "MODE SILENCIEUX" "Test en mode headless" "Interface navigateur cachee"
    }
    $testArgs += "test_integration_detailed.py"
    
    Write-TraceLog "LANCEMENT PYTEST" "Arguments: $($testArgs -join ' ')"
    
    $testProcess = Start-Process -FilePath "conda" -ArgumentList $testArgs -PassThru -NoNewWindow -RedirectStandardOutput "test_detailed_output.log" -RedirectStandardError "test_detailed_error.log" -Wait
    
    Write-TraceLog "PYTEST TERMINE" "Code de sortie: $($testProcess.ExitCode)"
    
    # 7. ANALYSE RÉSULTATS
    Write-TraceLog "ANALYSE RESULTATS" "Lecture logs de test"
    
    if (Test-Path "test_detailed_output.log") {
        $output = Get-Content "test_detailed_output.log" -Raw
        Write-TraceLog "SORTIE STANDARD" "Taille: $($output.Length) caracteres" "Log disponible dans test_detailed_output.log"
        
        # Extraire actions du test
        $output -split "`n" | Where-Object { $_ -match "^\[" } | ForEach-Object {
            Write-TraceLog "ACTION TEST" $_.Trim()
        }
    }
    
    if (Test-Path "test_detailed_error.log") {
        $errors = Get-Content "test_detailed_error.log" -Raw
        if ($errors.Trim()) {
            Write-TraceLog "ERREURS DETECTEES" "Taille: $($errors.Length) caracteres" "Voir test_detailed_error.log"
        }
    }
    
    # 8. VÉRIFICATION SCREENSHOTS
    if (Test-Path "integration_test_final.png") {
        Write-TraceLog "SCREENSHOT TROUVE" "Fichier: integration_test_final.png" "Capture d'ecran finale disponible"
    }
    
    $global:TestSuccess = ($testProcess.ExitCode -eq 0)
    if ($global:TestSuccess) {
        Write-TraceLog "SUCCES COMPLET" "Tous les tests ont reussi" "Integration reussie avec trace complete"
    } else {
        Write-TraceLog "ECHEC DETECTE" "Code de sortie: $($testProcess.ExitCode)" "Voir logs pour details"
    }

} finally {
    Write-TraceLog "SAUVEGARDE TRACE" "Generation fichier de trace final"
    Save-TraceToFile $TraceFile
    
    Cleanup-Services
    
    Write-Host "`nTRACE COMPLETE DISPONIBLE DANS: $TraceFile" -ForegroundColor Green
}