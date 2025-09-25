# Ce script exécute le test d'intégration de l'API Dung instrumenté.
# Il est conçu pour être lancé depuis la racine du projet.

Write-Host "Lancement du test d'intégration instrumenté..."

# Activer l'environnement conda
Write-Host "Activation de l'environnement conda 'projet-is'..."
conda activate projet-is

# Lancer le test avec logs détaillés
Write-Host "Lancement du test pytest avec instrumentation..."
pytest tests/e2e/python/test_api_dung_integration.py -v --capture=no

if ($LASTEXITCODE -eq 0) {
    Write-Host "Le test s'est terminé."
} else {
    Write-Host "Le test a échoué avec le code de sortie: $LASTEXITCODE"
}