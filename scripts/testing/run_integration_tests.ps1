# Point d'entrée pour l'exécution des tests d'intégration complets.
# Ce script utilise l'environnement d'activation du projet pour garantir que
# toutes les dépendances et variables d'environnement sont correctement configurées.

param(
    [string]$Tests = "tests/e2e/python"
)

$ErrorActionPreference = 'Stop'

# Chemin vers le script d'activation de l'environnement
$ActivationScript = Join-Path $PSScriptRoot "..\..\activate_project_env.ps1"

# Chemin vers le script d'orchestration web unifié
# Le script se trouve dans scripts/ donc on remonte d'un niveau puis on descend dans apps/webapp
$WebAppOrchestratorScript = "scripts/apps/webapp/unified_web_orchestrator.py"

# Arguments à passer à l'orchestrateur.
# --integration est la valeur par défaut mais on l'explicite pour la clarté.
# --frontend est requis pour les tests e2e
# --visible peut être utile pour le débogage. Retirer pour exécution en headless.
$OrchestratorArgs = "--integration --frontend --tests $Tests" # --visible peut être ajouté manuellement pour le débogage

# Commande complète à passer au script d'activation
$CommandToExecute = "python $WebAppOrchestratorScript $OrchestratorArgs"

Write-Host "Activation de l'environnement et exécution du test d'intégration..."
Write-Host "Commande: $CommandToExecute"
Write-Host "---------------------------------------------------------"

# Le script 'activate_project_env.ps1' exécute directement la commande.
# Il n'est pas nécessaire de capturer une commande finale ou d'utiliser des fichiers temporaires.
& $ActivationScript -CommandToRun $CommandToExecute

if ($LASTEXITCODE -ne 0) {
    Write-Host "---------------------------------------------------------"
    Write-Host "ERREUR: Le test d'intégration a échoué."
    exit 1
} else {
    Write-Host "---------------------------------------------------------"
    Write-Host "SUCCES: Le test d'intégration s'est terminé avec succès."
    exit 0
}