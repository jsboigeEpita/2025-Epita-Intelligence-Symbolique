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
    cd 'C:\dev\2025-Epita-Intelligence-Symbolique'
    conda run -n projet-is --no-capture-output --live-stream python argumentation_analysis/services/web_api/start_api.py --port 5003
} -Name "Backend"

# Lancer le frontend en arrière-plan
Write-Host "Démarrage du serveur frontend en arrière-plan..."
Start-Job -ScriptBlock {
    cd 'C:\dev\2025-Epita-Intelligence-Symbolique'
    conda run -n projet-is --no-capture-output --live-stream npm start --prefix services/web_api/interface-web-argumentative
} -Name "Frontend"

# Attendre que les serveurs démarrent
Write-Host "Attente de 30 secondes pour le démarrage des serveurs..."
Start-Sleep -Seconds 30

# Vérifier si les ports sont ouverts
$backend_ok = (Test-NetConnection -ComputerName localhost -Port 5003 -WarningAction SilentlyContinue).TcpTestSucceeded
$frontend_ok = (Test-NetConnection -ComputerName localhost -Port 3000 -WarningAction SilentlyContinue).TcpTestSucceeded

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