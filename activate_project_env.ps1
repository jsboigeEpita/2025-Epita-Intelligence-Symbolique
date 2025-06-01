# Script simplifié pour l'activation de l'environnement Conda du projet

$condaEnvName = "projet-is"

Write-Host ""
Write-Host "---------------------------------------------------------------------"
Write-Host "Activation de l'environnement Conda '$condaEnvName'"
Write-Host ""
Write-Host "Pour activer l'environnement '$condaEnvName', veuillez exécuter la commande suivante"
Write-Host "dans votre terminal PowerShell :"
Write-Host ""
Write-Host "    conda activate $condaEnvName"
Write-Host ""
Write-Host "Si Conda n'est pas initialisé pour PowerShell, vous pourriez avoir besoin"
Write-Host "d'exécuter 'conda init powershell' une fois (et redémarrer votre terminal),"
Write-Host "ou d'utiliser l'invite de commandes Anaconda."
Write-Host ""
Write-Host "Après activation, votre prompt devrait inclure '($condaEnvName)'."
Write-Host "---------------------------------------------------------------------"
Write-Host ""

# Note: La gestion des variables d'environnement comme JAVA_HOME et l'ajout au PATH
# sont maintenant gérés par le script setup_project_env.ps1 (pour .env)
# et potentiellement par des scripts activate.d/deactivate.d de Conda si nécessaire.
# Ce script ne tente plus d'activer programmatiquement l'environnement
# car la méthode Conda standard est plus robuste et recommandée.