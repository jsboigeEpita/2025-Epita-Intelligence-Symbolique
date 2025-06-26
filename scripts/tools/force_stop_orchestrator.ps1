# Script pour arrêter forcément l'orchestrateur et résoudre les conflits JVM JPype
# Cause: "Native Library already loaded in another classloader"

Write-Host "[FORCE STOP] Arrêt forcé de l'orchestrateur pour résoudre les conflits JVM JPype..." -ForegroundColor Yellow

# 1. Arrêt spécifique du processus unified_web_orchestrator
Write-Host "[STEP 1] Recherche et arrêt du processus unified_web_orchestrator..." -ForegroundColor Cyan
$orchestratorProcs = Get-WmiObject Win32_Process | Where-Object { 
    $_.CommandLine -like "*unified_web_orchestrator*" -or 
    $_.CommandLine -like "*conda run*projet-is*" 
}

foreach($proc in $orchestratorProcs) {
    Write-Host "[KILL] Arrêt forcé PID $($proc.ProcessId) - $($proc.CommandLine)" -ForegroundColor Red
    Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
}

# 2. Arrêt des processus Python liés au projet
Write-Host "[STEP 2] Nettoyage des processus Python liés..." -ForegroundColor Cyan
$pythonProcs = Get-WmiObject Win32_Process | Where-Object { 
    $_.CommandLine -like "*python*" -and (
        $_.CommandLine -like "*argumentation_analysis*" -or
        $_.CommandLine -like "*uvicorn*" -or
        $_.CommandLine -like "*8000*" -or
        $_.CommandLine -like "*8001*" -or
        $_.CommandLine -like "*8002*" -or
        $_.CommandLine -like "*8003*"
    )
}

foreach($proc in $pythonProcs) {
    Write-Host "[KILL] Arrêt Python PID $($proc.ProcessId)" -ForegroundColor Red
    Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
}

# 3. Libération des ports critiques
Write-Host "[STEP 3] Libération des ports webapp..." -ForegroundColor Cyan
$ports = @(8000,8001,8002,8003,5003,5004,5005,5006,3000)
foreach($port in $ports) {
    try {
        $conn = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
        if($conn) {
            $pid = $conn.OwningProcess
            Write-Host "[PORT] Libération port $port (PID: $pid)" -ForegroundColor Yellow
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        }
    } catch { }
}

# 4. Attente de stabilisation
Write-Host "[WAIT] Attente de stabilisation (3s)..." -ForegroundColor Green
Start-Sleep -Seconds 3

# 5. Vérification
Write-Host "[VERIFY] Vérification des processus restants..." -ForegroundColor Cyan
$remaining = Get-WmiObject Win32_Process | Where-Object { 
    $_.CommandLine -like "*unified_web_orchestrator*" -or
    ($_.CommandLine -like "*python*" -and $_.CommandLine -like "*argumentation_analysis*")
}

if($remaining) {
    Write-Host "[WARNING] Processus restants détectés:" -ForegroundColor Yellow
    foreach($proc in $remaining) {
        Write-Host "  PID $($proc.ProcessId): $($proc.CommandLine)" -ForegroundColor Yellow
    }
} else {
    Write-Host "[SUCCESS] Tous les processus conflictuels arrêtés avec succès!" -ForegroundColor Green
}

Write-Host "[READY] Environnement nettoyé - prêt pour les tests Playwright" -ForegroundColor Green