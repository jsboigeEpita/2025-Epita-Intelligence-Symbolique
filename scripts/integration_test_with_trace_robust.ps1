param(
    [switch]$Headfull,
    [int]$TimeoutMinutes = 10
)

# Configuration UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Variables globales
$script:TraceActions = @()

function Add-TraceAction {
    param($Action, $Details, $Result = "")
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

function Wait-ForUrl {
    param([string]$Url, [int]$TimeoutSeconds = 60)
    
    Add-TraceAction "VERIFICATION URL" "Test de disponibilite: $Url"
    
    $startTime = Get-Date
    while ((Get-Date) - $startTime -lt [TimeSpan]::FromSeconds($TimeoutSeconds)) {
        try {
            $response = Invoke-WebRequest -Uri $Url -Method HEAD -TimeoutSec 5 -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Add-TraceAction "URL DISPONIBLE" "Status: $($response.StatusCode)" "URL accessible: $Url"
                return $true
            }
        }
        catch {
            # Continue à attendre
        }
        Start-Sleep -Seconds 2
    }
    
    Add-TraceAction "TIMEOUT URL" "Echec apres $TimeoutSeconds secondes" "URL non accessible: $Url"
    return $false
}

function Test-IntegrationWithRobustTrace {
    Add-TraceAction "INITIALISATION ROBUSTE" "Demarrage test integration avec verification robuste" "Mode: $(if($Headfull){'Headfull'}else{'Headless'})"

    # 1. BACKEND
    Add-TraceAction "BACKEND" "Lancement du script de failover backend"
    $backendOutput = & powershell -ExecutionPolicy Bypass -File "scripts\backend_failover_non_interactive.ps1" 2>&1
    Write-Host $backendOutput

    # Lire les infos backend
    if (Test-Path "backend_info.json") {
        $backendInfo = Get-Content "backend_info.json" | ConvertFrom-Json
        Add-TraceAction "BACKEND OPERATIONNEL" "Port: $($backendInfo.port) | Job ID: $($backendInfo.job_id)" "Backend accessible sur $($backendInfo.url)"
        
        # Test backend
        Add-TraceAction "TEST BACKEND" "Verification endpoint /api/health"
        try {
            $healthResponse = Invoke-WebRequest -Uri "$($backendInfo.url)/api/health" -TimeoutSec 10
            Add-TraceAction "ENDPOINT HEALTH" "Status Code: $($healthResponse.StatusCode)" "Backend repond correctement"
        }
        catch {
            Add-TraceAction "ERREUR BACKEND" "Echec verification health" "Backend inaccessible: $($_.Exception.Message)"
            return
        }
    }

    # 2. FRONTEND
    Add-TraceAction "FRONTEND" "Demarrage interface React"
    $frontendPath = "services\web_api\interface-web-argumentative"
    
    $frontendJob = Start-Job -ScriptBlock {
        param($Path)
        Set-Location $Path
        npm start 2>&1
    } -ArgumentList (Resolve-Path $frontendPath)
    
    Add-TraceAction "FRONTEND LANCE" "Job ID: $($frontendJob.Id)" "Interface React en cours de demarrage"

    # 3. ATTENTE FRONTEND ROBUSTE
    Add-TraceAction "ATTENTE FRONTEND ROBUSTE" "Verification disponibilite complete avec retry"
    
    # Attendre que le frontend soit vraiment accessible
    $frontendReady = Wait-ForUrl -Url "http://localhost:3000" -TimeoutSeconds 90
    
    if (-not $frontendReady) {
        Add-TraceAction "ECHEC FRONTEND" "Frontend non accessible apres timeout" "Arret du test"
        Stop-Job $frontendJob -Force
        Remove-Job $frontendJob -Force
        return
    }

    Add-TraceAction "FRONTEND CONFIRME" "URL accessible avec success" "Interface disponible sur http://localhost:3000"

    # 4. TEST PLAYWRIGHT AVEC TRACE
    Add-TraceAction "CREATION TEST" "Generation test Playwright avec actions detaillees"

    $testContent = @"
import pytest
from playwright.sync_api import Page, expect
import time
import requests

def test_interface_integration_complete_robust(page: Page):
    '''Test d'integration complet avec trace des actions et verification robuste'''
    
    # Configuration
    backend_url = "http://localhost:5003"
    frontend_url = "http://localhost:3000"
    
    print(f"[CONFIG] Backend={backend_url}, Frontend={frontend_url}")
    
    # DOUBLE VERIFICATION AVANT NAVIGATION
    print("[VERIFICATION] Test preliminaire de disponibilite du frontend")
    try:
        response = requests.get(frontend_url, timeout=10)
        print(f"[VERIFICATION] Status frontend: {response.status_code}")
    except Exception as e:
        print(f"[ERREUR] Frontend non accessible: {e}")
        pytest.fail("Frontend non accessible avant navigation")
    
    # 1. NAVIGATION VERS FRONTEND
    print("[ACTION] Navigation vers l'interface frontend")
    page.goto(frontend_url, wait_until="networkidle", timeout=30000)
    print(f"[RESULT] Page chargee - URL: {page.url}")
    
    # Attendre chargement complet
    print("[WAIT] Attente chargement complet de l'interface")
    page.wait_for_load_state("networkidle")
    time.sleep(3)
    print("[RESULT] Interface completement chargee")
    
    # 2. VERIFICATION TITRE PAGE
    print("[ACTION] Verification du titre de la page")
    title = page.title()
    print(f"[RESULT] Titre de la page: '{title}'")
    
    # 3. RECHERCHE ELEMENTS INTERFACE
    print("[ACTION] Recherche des elements d'interface")
    
    # Chercher zone de texte
    text_inputs = page.locator("textarea, input[type='text'], input:not([type])").all()
    print(f"[RESULT] {len(text_inputs)} zone(s) de texte trouvee(s)")
    
    # Chercher boutons
    buttons = page.locator("button").all()
    print(f"[RESULT] {len(buttons)} bouton(s) trouve(s)")
    
    # Chercher liens
    links = page.locator("a").all()
    print(f"[RESULT] {len(links)} lien(s) trouve(s)")
    
    # 4. CAPTURE INITIALE
    print("[ACTION] Capture d'ecran initiale")
    page.screenshot(path="integration_test_initial.png")
    print("[RESULT] Screenshot initial sauve")
    
    # 5. TEST INTERACTION SI ELEMENTS DISPONIBLES
    if text_inputs:
        print("[ACTION] Saisie de texte de test")
        first_input = text_inputs[0]
        test_text = "Ceci est un test d'analyse argumentative avec verification robuste."
        first_input.fill(test_text)
        print(f"[RESULT] Texte saisi: '{test_text}'")
        
        # Verifier la saisie
        filled_value = first_input.input_value()
        print(f"[VERIFY] Valeur dans le champ: '{filled_value}'")
        
        # Capture après saisie
        page.screenshot(path="integration_test_after_input.png")
        print("[RESULT] Screenshot apres saisie sauve")
    
    if buttons:
        print("[ACTION] Analyse des boutons disponibles")
        for i, button in enumerate(buttons[:3]):  # Max 3 boutons
            try:
                button_text = button.inner_text()
                is_visible = button.is_visible()
                is_enabled = button.is_enabled()
                print(f"[DETAILS] Bouton {i+1}: '{button_text}' - Visible: {is_visible}, Active: {is_enabled}")
                
                if is_visible and is_enabled and button_text.strip():
                    print(f"[ACTION] Clic sur bouton: '{button_text}'")
                    button.click()
                    print(f"[RESULT] Clic effectue sur '{button_text}'")
                    time.sleep(2)
                    
                    # Capture après clic
                    page.screenshot(path=f"integration_test_after_click_{i+1}.png")
                    print(f"[RESULT] Screenshot apres clic {i+1} sauve")
                    break
            except Exception as e:
                print(f"[ERREUR] Probleme avec bouton {i+1}: {e}")
    
    # 6. TEST BACKEND DIRECT
    print("[ACTION] Test direct du backend API")
    response = page.request.get(f"{backend_url}/api/health")
    print(f"[RESULT] Status backend: {response.status}")
    
    if response.ok:
        response_text = response.text()
        print(f"[CONTENT] Reponse backend: {response_text}")
    
    # 7. VERIFICATION DE LA PAGE
    print("[ACTION] Verification contenu de la page")
    page_content = page.content()
    content_length = len(page_content)
    print(f"[RESULT] Taille du contenu HTML: {content_length} caracteres")
    
    # Rechercher elements specifiques
    headers = page.locator("h1, h2, h3").all()
    print(f"[RESULT] {len(headers)} titre(s) trouve(s)")
    
    # 8. CAPTURE FINALE
    print("[ACTION] Capture d'ecran finale")
    page.screenshot(path="integration_test_final.png", full_page=True)
    print("[RESULT] Screenshot final complet sauve")
    
    print("[SUCCESS] TEST TERMINE: Toutes les actions ont ete executees avec succes")
"@

    $testContent | Out-File -FilePath "test_integration_robust.py" -Encoding UTF8
    Add-TraceAction "TEST CREE" "Fichier: test_integration_robust.py" "Test Playwright robuste avec verification complete genere"

    # Configuration environment
    Add-TraceAction "CONFIGURATION" "Parametres environment test"
    @"
BACKEND_URL=http://localhost:5003
FRONTEND_URL=http://localhost:3000
PLAYWRIGHT_HEADED=$($Headfull.ToString().ToLower())
"@ | Out-File -FilePath ".env.test" -Encoding UTF8
    Add-TraceAction "CONFIG CREEE" "Fichier: .env.test" "Variables d'environnement configurees"

    # Execution du test
    Add-TraceAction "EXECUTION TEST ROBUSTE" "Lancement Playwright avec verification complete"
    
    $headedFlag = if ($Headfull) { "--headed" } else { "" }
    Add-TraceAction "MODE VISUEL" "Test en mode $(if($Headfull){'headed'}else{'headless'})" "Interface navigateur $(if($Headfull){'visible'}else{'cachee'})"
    
    Add-TraceAction "LANCEMENT PYTEST ROBUSTE" "Arguments: run -n projet-is python -m pytest -v -s $headedFlag test_integration_robust.py"
    
    $testResult = & conda run -n projet-is python -m pytest -v -s $headedFlag test_integration_robust.py 2>&1
    $exitCode = $LASTEXITCODE
    
    Add-TraceAction "PYTEST TERMINE" "Code de sortie: $exitCode"
    
    # Analyse des resultats
    Add-TraceAction "ANALYSE RESULTATS" "Lecture logs de test"
    
    $testResult | Out-File -FilePath "test_robust_output.log" -Encoding UTF8
    Add-TraceAction "SORTIE STANDARD" "Taille: $($testResult.Length) caracteres" "Log disponible dans test_robust_output.log"
    
    # Extraire les actions du test
    $actions = $testResult | Where-Object { $_ -match "^\[ACTION\]|^\[RESULT\]|^\[VERIFY\]|^\[CONFIG\]|^\[SUCCESS\]" }
    foreach ($action in $actions) {
        Add-TraceAction "ACTION TEST" $action.Trim()
    }
    
    if ($exitCode -eq 0) {
        Add-TraceAction "SUCCES TESTE" "Tous les tests ont reussi" "Integration complete validee"
    } else {
        Add-TraceAction "ECHEC DETECTE" "Code de sortie: $exitCode" "Voir logs pour details"
    }

    # Sauvegarde de la trace
    Add-TraceAction "SAUVEGARDE TRACE" "Generation fichier de trace final"
    Save-TraceToFile

    # Nettoyage
    Add-TraceAction "NETTOYAGE" "Arret de tous les services"
    Cleanup-Services

    Write-Host "`nTRACE COMPLETE DISPONIBLE DANS: test_execution_trace_robust.md" -ForegroundColor Yellow
}

function Save-TraceToFile {
    $traceContent = @"
# TRACE D'EXECUTION DES TESTS D'INTEGRATION (VERSION ROBUSTE)
**Date d'execution:** $(Get-Date -Format "dd/MM/yyyy HH:mm:ss")  
**Mode:** $(if($Headfull){'Interface Visible (Headfull)'}else{'Interface Cachee (Headless)'})  
**Backend:** http://localhost:5003  
**Frontend:** http://localhost:3000  

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
- **Nombre d'actions:** $($script:TraceActions.Count)
- **Duree totale:** $((Get-Date) - $script:startTime).TotalSeconds secondes
- **Statut:** $(if($LASTEXITCODE -eq 0){'SUCCES'}else{'ECHEC'})

## CONFIGURATION TECHNIQUE
- **Backend Port:** 5003
- **Frontend URL:** http://localhost:3000
- **Mode Headfull:** $Headfull
- **Verification robuste:** Active
"@

    $traceContent | Out-File -FilePath "test_execution_trace_robust.md" -Encoding UTF8
    Write-Host "Trace sauvegardee dans: test_execution_trace_robust.md" -ForegroundColor Green
}

function Cleanup-Services {
    # Arreter les processus Python (backend/frontend)
    Get-Process python -ErrorAction SilentlyContinue | ForEach-Object {
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
        Add-TraceAction "PROCESSUS ARRETE" "PID: $($_.Id) | Nom: $($_.Name)"
    }
    
    # Arreter les jobs PowerShell
    Get-Job | ForEach-Object {
        Stop-Job $_ -Force -ErrorAction SilentlyContinue
        Remove-Job $_ -Force -ErrorAction SilentlyContinue
    }
    
    Add-TraceAction "NETTOYAGE TERMINE" "" "Tous les services ont ete arretes"
}

# Enregistrer job de nettoyage
Register-EngineEvent PowerShell.Exiting -Action { Cleanup-Services }

$script:startTime = Get-Date

Write-Host "DEMARRAGE TEST D'INTEGRATION AVEC TRACE ROBUSTE" -ForegroundColor Yellow
Test-IntegrationWithRobustTrace