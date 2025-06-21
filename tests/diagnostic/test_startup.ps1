#!/usr/bin/env pwsh
# Test de démarrage de l'orchestrateur unifié avec nouvelle logique de validation

Write-Host "🚀 TEST DE DEMARRAGE - ORCHESTRATEUR UNIFIE" -ForegroundColor Cyan
Write-Host 'Objectif: Vérifier que le frontend démarre même avec des endpoints backend défaillants' -ForegroundColor Yellow

try {
    # Activation de l'environnement
    Write-Host "`n📦 Activation de l'environnement Python..." -ForegroundColor Blue
    & "scripts/env/activate_project_env.ps1"
    if ($LASTEXITCODE -ne 0) {
        throw "Échec de l'activation de l'environnement Python."
    }
    Write-Host "✅ Environnement activé." -ForegroundColor Green

    # Démarrage de l'orchestrateur en mode --start (avec frontend)
    Write-Host "`n🌐 Démarrage de l'application web complète..." -ForegroundColor Blue
    $scriptPath = "project_core/webapp_from_scripts/unified_web_orchestrator.py"
    $arguments = @("--start", "--frontend", "--visible", "--log-level", "DEBUG")
    Write-Host "Commande: python $scriptPath $($arguments -join ' ')" -ForegroundColor Gray
    
    # Exécution directe et plus sûre de la commande
    & python $scriptPath $arguments

    if ($LASTEXITCODE -ne 0) {
        throw "Le script de l'orchestrateur s'est terminé avec le code d'erreur: $LASTEXITCODE"
    }

    Write-Host "✅ Orchestrateur démarré (ou en cours)." -ForegroundColor Green

} catch {
    Write-Host "❌ Erreur critique lors de l'exécution du test: $_" -ForegroundColor Red
    exit 1
}

Write-Host "`n🎉 Script de test terminé." -ForegroundColor Cyan