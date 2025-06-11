# Script pour démarrer l'application web complète (Backend Flask + Frontend React)
# avec configuration de JAVA_HOME et activation de l'environnement.

$ErrorActionPreference = "Stop"
Clear-Host

# --- Configuration ---
$ProjectRoot = $PSScriptRoot | Split-Path | Split-Path # Remonte de deux niveaux si le script est dans scripts/
if (-not ($ProjectRoot -match "2025-Epita-Intelligence-Symbolique$")) {
    # Si le script est exécuté depuis un autre endroit, ajuster ou définir manuellement
    $ProjectRoot = "c:/dev/2025-Epita-Intelligence-Symbolique"
    Write-Warning "Chemin du projet déduit. Assurez-vous que '$ProjectRoot' est correct."
}

$JavaHomePath = Join-Path $ProjectRoot "libs\portable_jdk\jdk-17.0.11+9"
$CondaEnvName = "projet-is"
$StartWebappScript = Join-Path $ProjectRoot "start_webapp.py"
$AutoEnvScriptForImport = Join-Path $ProjectRoot "scripts\core\auto_env.py" # Juste pour s'assurer qu'il est là

Write-Host "=====================================================================" -ForegroundColor Green
Write-Host "🚀 DÉMARRAGE APPLICATION WEB COMPLÈTE" -ForegroundColor Green
Write-Host "====================================================================="
Write-Host "[INFO] Racine du projet: $ProjectRoot"
Write-Host "[INFO] Environnement Conda cible: $CondaEnvName"

# --- 1. Vérification et Configuration de JAVA_HOME (Désactivé)---
# La configuration de l'environnement, y compris JAVA_HOME, est maintenant
# entièrement gérée par le one-liner ci-dessous, via auto_env.py.
# if (Test-Path $JavaHomePath) {
#     Write-Host "[JAVA] Configuration de JAVA_HOME sur: $JavaHomePath" -ForegroundColor Cyan
#     $env:JAVA_HOME = $JavaHomePath
# } else {
#     Write-Warning "[JAVA] JDK portable non trouvé à $JavaHomePath. Assurez-vous que JAVA_HOME est correctement configuré."
# }

# --- 2. Activation de l'environnement Conda et chargement .env (via start_webapp.py qui devrait le faire) ---
# start_webapp.py gère l'activation de Conda.
# Pour s'assurer que la logique de auto_env.py (chargement de .env) est potentiellement active
# si start_webapp.py ou ses dépendances l'importent, nous n'avons rien à faire ici directement
# car start_webapp.py est le point d'entrée.
# Si start_webapp.py N'importe PAS auto_env.py, et qu'un .env est nécessaire,
# il faudrait modifier start_webapp.py pour ajouter "import scripts.core.auto_env" au début.
# Pour l'instant, on se fie à la structure existante.

Write-Host "[CONDA] Tentative de démarrage via start_webapp.py (qui devrait activer Conda: $CondaEnvName)" -ForegroundColor Cyan

# --- 3. Lancement de l'application web (Backend + Frontend) ---
Write-Host "[WEBAPP] Lancement de l'application (Flask Backend + React Frontend)..." -ForegroundColor Cyan
# Write-Host "[COMMAND] conda run -n $CondaEnvName python $StartWebappScript --frontend --visible" # Ancienne méthode

try {
    # Naviguer à la racine du projet pour que les chemins relatifs fonctionnent
    Push-Location $ProjectRoot
    
    # --- MÉTHODE D'ACTIVATION VIA SCRIPT WRAPPER (la plus fiable) ---
    # On appelle un script Python dédié qui se charge d'exécuter l'activation.
    # Cela évite tous les problèmes de parsing de chaîne entre PowerShell et Python.
    $ActivationWrapper = Join-Path $ProjectRoot "scripts\core\activate_env_wrapper.py"
    
    Write-Host "[INFO] Exécution du wrapper d'activation: python $ActivationWrapper" -ForegroundColor Cyan
    python $ActivationWrapper
    
    # Lancement de l'application principale
    Write-Host "[INFO] Lancement du script principal: python $StartWebappScript" -ForegroundColor Cyan
    python $StartWebappScript --frontend --visible
    
    $ExitCode = $LASTEXITCODE
    if ($ExitCode -eq 0) {
        Write-Host "[SUCCESS] start_webapp.py semble s'être lancé correctement." -ForegroundColor Green
        Write-Host "[INFO] Vérifiez les logs de start_webapp.py pour le statut du backend et du frontend."
        Write-Host "[INFO] API attendue sur http://localhost:5003 (ou fallback)"
        Write-Host "[INFO] UI attendue sur http://localhost:3000"
    } else {
        Write-Error "[FAILURE] start_webapp.py a terminé avec le code d'erreur: $ExitCode"
    }
} catch {
    Write-Error "[FATAL] Erreur lors de l'exécution de python $StartWebappScript : $($_.Exception.Message)"
} finally {
    Pop-Location
}

Write-Host "====================================================================="
Write-Host "SCRIPT DE DÉMARRAGE TERMINÉ"
Write-Host "====================================================================="