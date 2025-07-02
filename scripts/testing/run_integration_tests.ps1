# Point d'entrée pour l'exécution des tests d'intégration complets.
# Ce script utilise l'environnement d'activation du projet pour garantir que
# toutes les dépendances et variables d'environnement sont correctement configurées.

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
$OrchestratorArgs = "--integration --frontend" # --visible peut être ajouté manuellement pour le débogage

# Commande complète à passer au script d'activation
$CommandToExecute = "python $WebAppOrchestratorScript $OrchestratorArgs"

Write-Host "Activation de l'environnement et exécution du test d'intégration..."
Write-Host "Commande: $CommandToExecute"

# Le script d'activation ne va pas exécuter la commande directement,
# mais plutôt générer la commande complète avec l'environnement activé.
Write-Host "Génération de la commande finale via le script d'activation..."
# Créer un fichier temporaire unique pour la commande
$TempOutputFile = [System.IO.Path]::GetTempFileName()

try {
    # Exécuter l'activation et récupérer la commande via le fichier temporaire
    $ActivationOutput = & $ActivationScript -CommandToRun $CommandToExecute -EnableVerboseLogging -CommandOutputFile $TempOutputFile | Out-String
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERREUR: Le script d'activation a échoué. Sortie: $ActivationOutput"
        exit 1
    }

    $FinalCommand = Get-Content $TempOutputFile
} finally {
    # S'assurer que le fichier temporaire est supprimé
    if (Test-Path $TempOutputFile) {
        Remove-Item $TempOutputFile -Force
    }
}


if (-not $FinalCommand) {
    Write-Host "ERREUR: La génération de la commande via le script d'activation a échoué."
    exit 1
}

Write-Host "Commande finale à exécuter: $FinalCommand"
Write-Host "---------------------------------------------------------"

# Exécution de la commande finale générée
Invoke-Expression $FinalCommand

if ($LASTEXITCODE -ne 0) {
    Write-Host "---------------------------------------------------------"
    Write-Host "ERREUR: Le test d'intégration a échoué."
    exit 1
} else {
    Write-Host "---------------------------------------------------------"
    Write-Host "SUCCES: Le test d'intégration s'est terminé avec succès."
    exit 0
}