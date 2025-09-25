# Ce script lance les tests E2E avec une supervision pour éviter les blocages infinis.
# Il exécute les tests en tâche de fond, surveille leur durée d'exécution,
# et met fin au processus si un timeout est dépassé, tout en capturant les logs.

param(
    [int]$TimeoutSeconds = 1800  # Timeout de 30 minutes par défaut
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = $PSScriptRoot
$LogDir = Join-Path $ProjectRoot "_e2e_logs"
$LogFile = Join-Path $LogDir "e2e_run.log"
$TestScript = Join-Path $ProjectRoot "run_tests.ps1"

# S'assurer que le répertoire de logs existe
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

# Vider le fichier de log précédent s'il existe
if (Test-Path $LogFile) {
    Clear-Content $LogFile
}

Write-Host "[SUPERVISEUR] Lancement des tests E2E via '$TestScript' avec un timeout de $TimeoutSeconds secondes." -ForegroundColor Yellow
Write-Host "[SUPERVISEUR] Les logs seront capturés dans '$LogFile'." -ForegroundColor Yellow

# Définition de la commande à exécuter en tâche de fond.
# La redirection de tous les flux de sortie ('*>&1') est cruciale pour tout capturer.
$ScriptBlock = {
    param($Path)
    & $Path -Type "e2e" *>&1
}

# Lancement de la tâche de fond
$Job = Start-Job -ScriptBlock $ScriptBlock -ArgumentList $TestScript

Write-Host "[SUPERVISEUR] Tâche de test démarrée avec l'ID $($Job.Id)." -ForegroundColor Cyan

# Attente de la fin de la tâche ou du timeout
$Timer = [System.Diagnostics.Stopwatch]::StartNew()
$JobFinished = $false
while ($Timer.Elapsed.TotalSeconds -lt $TimeoutSeconds -and !$JobFinished) {
    if ($Job.State -in @('Completed', 'Failed', 'Stopped')) {
        $JobFinished = $true
    }
    Start-Sleep -Seconds 5
}
$Timer.Stop()

# Traitement du résultat
if ($JobFinished) {
    Write-Host "[SUPERVISEUR] La tâche de test s'est terminée normalement en $($Timer.Elapsed.TotalSeconds) secondes." -ForegroundColor Green
} else {
    Write-Host "[SUPERVISEUR] Timeout atteint ! La tâche de test a dépassé les $TimeoutSeconds secondes." -ForegroundColor Red
    Write-Host "[SUPERVISEUR] Arrêt forcé de la tâche et de ses processus enfants..." -ForegroundColor Red
    
    # Arrêter le job
    Stop-Job -Job $Job -PassThru
    
    # Tenter de trouver et de tuer les processus enfants (Python, Node, etc.)
    # Ceci est une mesure de sécurité supplémentaire
    try {
        $ChildProcesses = Get-CimInstance Win32_Process | Where-Object { $_.ParentProcessId -eq $Job.ChildJobs[0].ProcessId }
        if ($ChildProcesses) {
            $ChildProcesses | ForEach-Object {
                Write-Host "[SUPERVISEUR]  - Tentative d'arrêt du processus enfant : $($_.ProcessName) (PID: $($_.ProcessId))" -ForegroundColor Magenta
                Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
            }
        }
    } catch {
        Write-Host "[SUPERVISEUR] Avertissement : Impossible de lister ou d'arrêter les processus enfants. Cela peut arriver si le job principal s'est déjà arrêté." -ForegroundColor Yellow
    }
}

# Récupération et sauvegarde des logs
Write-Host "[SUPERVISEUR] Récupération des logs de la tâche..." -ForegroundColor Cyan
$Output = Receive-Job -Job $Job -Keep

if ($Output) {
    # Convertit la sortie en un tableau de chaînes et l'enregistre
    $Output | ForEach-Object { $_.ToString() } | Out-File -FilePath $LogFile -Encoding utf8 -Append
    Write-Host "[SUPERVISEUR] Logs enregistrés avec succès dans '$LogFile'." -ForegroundColor Green
} else {
    $errorMessage = "[SUPERVISEUR] Aucune sortie n'a été capturée depuis la tâche de test."
    Write-Host $errorMessage -ForegroundColor Yellow
    Add-Content -Path $LogFile -Value $errorMessage
}

# Nettoyage du job
Remove-Job -Job $Job

Write-Host "[SUPERVISEUR] Opération terminée." -ForegroundColor Yellow