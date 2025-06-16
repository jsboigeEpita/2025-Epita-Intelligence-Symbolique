# Activer l'environnement
. .\scripts\env\activate_project_env.ps1

# Nettoyage agressif des caches
Write-Host "Nettoyage des caches Python..."
Get-ChildItem -Path . -Include __pycache__ -Recurse -Force | Remove-Item -Recurse -Force
Remove-Item -Path .\.pytest_cache -Recurse -Force -ErrorAction SilentlyContinue

# Forcer la réinstallation du paquet en mode editable
Write-Host "Réinstallation du paquet en mode editable..."
conda run -n projet-is --no-capture-output --live-stream pip install -e .

# Lancer le backend en arrière-plan
Write-Host "Démarrage du serveur backend en arrière-plan..."
Start-Job -ScriptBlock {
    cd $PWD
    conda run -n projet-is --no-capture-output --live-stream python argumentation_analysis/services/web_api/start_api.py --port 5003
} -Name "Backend"

# Lancer le frontend en arrière-plan
Write-Host "Démarrage du serveur frontend en arrière-plan..."
Start-Job -ScriptBlock {
    cd $PWD
    conda run -n projet-is --no-capture-output --live-stream npm start --prefix services/web_api/interface-web-argumentative
} -Name "Frontend"

# Boucle de vérification pour les serveurs
$max_attempts = 30
$sleep_interval = 2 # secondes

$backend_ok = $false
$frontend_ok = $false

Write-Host "Attente du démarrage des serveurs (max $(($max_attempts * $sleep_interval)) secondes)..."

foreach ($attempt in 1..$max_attempts) {
    Write-Host "Tentative $attempt sur $max_attempts..."
    
    # Tester les ports
    if (-not $backend_ok) {
        $backend_ok = (Test-NetConnection -ComputerName localhost -Port 5003 -WarningAction SilentlyContinue).TcpTestSucceeded
        if ($backend_ok) { Write-Host "  -> Backend sur le port 5003 est prêt." }
    }
    if (-not $frontend_ok) {
        $frontend_ok = (Test-NetConnection -ComputerName localhost -Port 3000 -WarningAction SilentlyContinue).TcpTestSucceeded
        if ($frontend_ok) { Write-Host "  -> Frontend sur le port 3000 est prêt." }
    }

    if ($backend_ok -and $frontend_ok) {
        break
    }
    
    Start-Sleep -Seconds $sleep_interval
}


if (-not $backend_ok) {
    Write-Error "Le serveur backend n'a pas démarré sur le port 5003."
    Write-Host "Affichage des logs du job Backend :"
    Receive-Job -Name Backend
    Get-Job | Stop-Job
    Get-Job | Remove-Job
    exit 1
}

if (-not $frontend_ok) {
    Write-Error "Le serveur frontend n'a pas démarré sur le port 3000."
    Write-Host "Affichage des logs du job Frontend :"
    Receive-Job -Name Frontend
    Get-Job | Stop-Job
    Get-Job | Remove-Job
    exit 1
}

Write-Host "✅ Les deux serveurs semblent être en cours d'exécution."

# Lancer les tests
Write-Host "Lancement des tests fonctionnels..."
pytest tests/functional/test_logic_graph.py --headed

# Nettoyage des jobs
Write-Host "Arrêt des serveurs..."
Get-Job | Stop-Job
Get-Job | Remove-Job