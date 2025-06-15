# L'activation de l'environnement est gérée par chaque commande `conda run`.
# La ligne d'activation globale a été supprimée car elle provoquait des erreurs de paramètres.

# Nettoyage agressif des caches
Write-Host "Nettoyage des caches Python..."
Get-ChildItem -Path . -Include __pycache__ -Recurse -Force | Remove-Item -Recurse -Force
Remove-Item -Path .\.pytest_cache -Recurse -Force -ErrorAction SilentlyContinue

# Forcer la réinstallation du paquet en mode editable
Write-Host "Réinstallation du paquet en mode editable..."
conda run -n projet-is --no-capture-output --live-stream pip install -e .

# Lancer l'orchestrateur unifié en arrière-plan
Write-Host "Démarrage de l'orchestrateur unifié en arrière-plan..."
Start-Job -ScriptBlock {
    cd $PWD
    # Exécute l'orchestrateur qui gère le backend et le frontend
    conda run -n projet-is --no-capture-output --live-stream python -m project_core.webapp_from_scripts.unified_web_orchestrator --start --frontend --visible --log-level INFO
} -Name "Orchestrator"

# Boucle de vérification pour le fichier URL du frontend
$max_attempts = 45 # Augmenté pour laisser le temps à l'orchestrateur de démarrer
$sleep_interval = 2 # secondes
$url_file_path = "logs/frontend_url.txt"
$orchestrator_ready = $false

# Nettoyer l'ancien fichier s'il existe
if (Test-Path $url_file_path) {
    Write-Host "Suppression de l'ancien fichier URL: $url_file_path"
    Remove-Item $url_file_path
}

Write-Host "Attente du démarrage de l'orchestrateur (max $(($max_attempts * $sleep_interval)) secondes)..."

foreach ($attempt in 1..$max_attempts) {
    Write-Host "Tentative $attempt sur $max_attempts..."
    
    if (Test-Path $url_file_path) {
        $content = Get-Content $url_file_path
        if ($content -and $content.Trim() -ne "") {
            Write-Host "  -> Fichier URL trouvé et non vide. L'orchestrateur est prêt."
            $orchestrator_ready = $true
            break
        }
    }
    
    Start-Sleep -Seconds $sleep_interval
}

if (-not $orchestrator_ready) {
    Write-Error "L'orchestrateur n'a pas créé le fichier de statut dans le temps imparti."
    Write-Host "Affichage des logs du job Orchestrator :"
    Receive-Job -Name Orchestrator
    Get-Job | Stop-Job
    Get-Job | Remove-Job
    exit 1
}

Write-Host "✅ L'orchestrateur semble être en cours d'exécution."

# Lancer les tests fonctionnels
Write-Host "Lancement de tous les tests fonctionnels..."
# Exécute tous les tests dans le répertoire `tests/functional`
conda run -n projet-is --no-capture-output --live-stream pytest tests/functional/

# Nettoyage du job
Write-Host "Arrêt de l'orchestrateur..."
Get-Job -Name Orchestrator | Stop-Job
Get-Job -Name Orchestrator | Remove-Job