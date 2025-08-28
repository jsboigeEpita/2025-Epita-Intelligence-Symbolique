# L'activation de l'environnement est gérée par chaque commande `conda run`.
# La ligne d'activation globale a été supprimée car elle provoquait des erreurs de paramètres.

# Nettoyage agressif des caches
# Le nettoyage des caches a été supprimé car il est trop lent et peu fiable.

# Forcer la réinstallation du paquet en mode editable
Write-Host "Réinstallation du paquet en mode editable..."
conda run -n projet-is --no-capture-output --live-stream pip install -e .

# --- Build du Frontend ---
Write-Host "Vérification et build du frontend React..."
$frontendDir = "services/web_api/interface-web-argumentative"

if (Test-Path $frontendDir) {
    Push-Location $frontendDir
    
    Write-Host "  -> Installation des dépendances npm..."
    npm install
    
    Write-Host "  -> Lancement du build npm..."
    npm run build
    
    Pop-Location
    Write-Host "✅ Frontend build terminé."
} else {
    Write-Warning "Le répertoire du frontend '$frontendDir' n'a pas été trouvé. Le backend pourrait ne pas fonctionner correctement."
}
# --- Fin Build du Frontend ---

# Lancer l'orchestrateur unifié en arrière-plan
Write-Host "Démarrage de l'orchestrateur unifié en arrière-plan..."
# Définir le répertoire racine du projet de manière robuste
$ProjectRoot = Get-Location
Write-Host "Le répertoire racine du projet est: $ProjectRoot"

Start-Job -ScriptBlock {
    # On s'assure que le job s'exécute dans le même répertoire que le script principal
    Set-Location $using:ProjectRoot
    
    # Exécute l'orchestrateur qui gère le backend et le frontend
    conda run -n projet-is --no-capture-output --live-stream python -m argumentation_analysis.webapp.orchestrator --start --frontend --visible --log-level INFO
} -Name "Orchestrator" -ArgumentList @($ProjectRoot)

# Attente et récupération de l'URL du frontend depuis la sortie du job
$max_wait_seconds = 120 # Temps total d'attente
$check_interval_seconds = 2
$frontend_url = $null

Write-Host "Attente de l'URL du frontend depuis l'orchestrateur (max $max_wait_seconds secondes)..."

$timer = [System.Diagnostics.Stopwatch]::StartNew()
while ($timer.Elapsed.TotalSeconds -lt $max_wait_seconds) {
    $job_output = Receive-Job -Name Orchestrator -Keep
    if ($job_output) {
        foreach ($line in $job_output) {
            if ($line -match "FRONTEND_URL_READY=(.+)") {
                $frontend_url = $matches[1].Trim()
                Write-Host "✅ URL du frontend détectée: $frontend_url"
                break
            }
        }
    }
    if ($frontend_url) { break }
    Start-Sleep -Seconds $check_interval_seconds
}
$timer.Stop()

if (-not $frontend_url) {
    Write-Error "L'orchestrateur n'a pas communiqué l'URL du frontend dans le temps imparti."
    Write-Host "Affichage des derniers logs du job Orchestrator :"
    Receive-Job -Name Orchestrator
    Get-Job | Stop-Job
    Get-Job | Remove-Job
    exit 1
}

Write-Host "✅ L'orchestrateur est prêt. L'URL du frontend est $frontend_url"

# Définir la variable d'environnement pour les sous-processus
$env:FRONTEND_URL = $frontend_url

# Lancer les tests fonctionnels en passant l'URL
Write-Host "Lancement de tous les tests fonctionnels..."
# Exécute tous les tests dans le répertoire `tests/functional`, en passant l-URL au fixture pytest
conda run -n projet-is --no-capture-output --live-stream pytest tests/functional/ --frontend-url="$env:FRONTEND_URL"

# Nettoyage du job
Write-Host "Arrêt de l'orchestrateur..."
Get-Job -Name Orchestrator | Stop-Job
Get-Job -Name Orchestrator | Remove-Job