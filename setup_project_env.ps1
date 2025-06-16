param (
    [string]$CommandToRun = "", # Commande à exécuter après activation
    [switch]$Help,              # Afficher l'aide
    [switch]$Status,            # Vérifier le statut environnement
    [switch]$Setup              # Configuration initiale
)

# Bannière d'information
Write-Host "=================================================================" -ForegroundColor Green
Write-Host "ORACLE ENHANCED v2.1.0 - Environnement Dédié" -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Green

# Gestion des paramètres spéciaux
if ($Help) {
    Write-Host @"
UTILISATION DU SCRIPT PRINCIPAL:

VERIFICATIONS:
   .\setup_project_env.ps1 -Status
   .\setup_project_env.ps1 -CommandToRun 'python scripts/env/check_environment.py'

EXECUTION DE COMMANDES:
   .\setup_project_env.ps1 -CommandToRun 'python demos/webapp/run_webapp.py'
   .\setup_project_env.ps1 -CommandToRun 'python -m pytest tests/unit/ -v'
   .\setup_project_env.ps1 -CommandToRun 'python scripts/sherlock_watson/run_sherlock_watson_moriarty_robust.py'

CONFIGURATION:
   .\setup_project_env.ps1 -Setup
   .\setup_project_env.ps1 -CommandToRun 'python scripts/env/manage_environment.py setup'

DOCUMENTATION:
   Voir: ENVIRONMENT_SETUP.md
   Voir: CORRECTED_RECOMMENDATIONS.md

IMPORTANT: Ce script active automatiquement l'environnement dédié 'projet-is'
"@ -ForegroundColor Cyan
    exit 0
}

if ($Status) {
    Write-Host "[INFO] Vérification rapide du statut environnement..." -ForegroundColor Cyan
    $CommandToRun = "python scripts/env/check_environment.py"
}

if ($Setup) {
    Write-Host "[INFO] Configuration initiale de l'environnement..." -ForegroundColor Cyan
    $CommandToRun = "python scripts/env/manage_environment.py setup"
}

# Vérifications préliminaires
if ([string]::IsNullOrEmpty($CommandToRun)) {
    Write-Host "[ERREUR] Aucune commande spécifiée!" -ForegroundColor Red
    Write-Host "[INFO] Utilisez: .\setup_project_env.ps1 -Help pour voir les options" -ForegroundColor Yellow
    Write-Host "[INFO] Exemple: .\setup_project_env.ps1 -CommandToRun 'python --version'" -ForegroundColor Yellow
    Write-Host "[INFO] Status: .\setup_project_env.ps1 -Status" -ForegroundColor Yellow
    exit 1
}

# Information sur l'environnement requis
Write-Host "[INFO] Environnement cible: conda 'projet-is'" -ForegroundColor Cyan
Write-Host "[INFO] [COMMANDE] $CommandToRun" -ForegroundColor Cyan

# Raccourci vers le script de setup principal
# $realScriptPath = Join-Path $PSScriptRoot "activate_project_env.ps1"
#
# if (!(Test-Path $realScriptPath)) {
#     Write-Host "[ERREUR] Script d'activation non trouvé: $realScriptPath" -ForegroundColor Red
#     Write-Host "[INFO] Vérifiez l'intégrité du projet" -ForegroundColor Yellow
#     exit 1
# }
#
# & $realScriptPath -CommandToRun $CommandToRun
# $exitCode = $LASTEXITCODE
# --- VALIDATION D'ENVIRONNEMENT DÉLÉGUÉE À PYTHON ---
# Le mécanisme 'project_core/core_from_scripts/auto_env.py' gère la validation, l'activation
# et le coupe-circuit de manière robuste. Ce script PowerShell se contente de l'invoquer.

Write-Host "[INFO] Délégation de la validation de l'environnement à 'project_core.core_from_scripts.auto_env.py'" -ForegroundColor Cyan

# Échapper les guillemets simples et doubles dans la commande pour l'injection dans la chaîne Python.
# PowerShell utilise ` comme caractère d'échappement pour les guillemets doubles.
$EscapedCommand = $CommandToRun.Replace("'", "\'").replace('"', '\"')

# Construction de la commande Python
# 1. Importe auto_env (active et valide l'environnement, lève une exception si échec)
# 2. Importe les modules 'os' et 'sys'
# 3. Exécute la commande passée au script et propage le code de sortie
$PythonCommand = "python -c `"import sys; import os; import project_core.core_from_scripts.auto_env; exit_code = os.system('$EscapedCommand'); sys.exit(exit_code)`""

Write-Host "[DEBUG] Commande Python complète à exécuter: $PythonCommand" -ForegroundColor Magenta

# Exécution de la commande
Invoke-Expression $PythonCommand
$exitCode = $LASTEXITCODE


# Message final informatif
Write-Host ""
Write-Host "=================================================================" -ForegroundColor Green
Write-Host "EXECUTION TERMINEE - Code de sortie: $exitCode" -ForegroundColor Green
if ($exitCode -eq 0) {
    Write-Host "[SUCCES] Environnement dédié opérationnel" -ForegroundColor Green
} else {
    Write-Host "[ECHEC] Vérifiez l'environnement avec: .\setup_project_env.ps1 -Status" -ForegroundColor Red
}

exit $exitCode