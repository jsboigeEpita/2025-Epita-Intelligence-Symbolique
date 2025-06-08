param (
    [string]$CommandToRun = "", # Commande à exécuter après activation
    [switch]$Help,              # Afficher l'aide
    [switch]$Status,            # Vérifier le statut environnement
    [switch]$Setup              # Configuration initiale
)

# Bannière d'information
Write-Host "🚀 =================================================================" -ForegroundColor Green
Write-Host "🚀 ORACLE ENHANCED v2.1.0 - Environnement Dédié" -ForegroundColor Green
Write-Host "🚀 =================================================================" -ForegroundColor Green

# Gestion des paramètres spéciaux
if ($Help) {
    Write-Host "
💡 UTILISATION DU SCRIPT PRINCIPAL:

🔍 VÉRIFICATIONS:
   .\setup_project_env.ps1 -Status
   .\setup_project_env.ps1 -CommandToRun 'python scripts/env/check_environment.py'

🚀 EXÉCUTION DE COMMANDES:
   .\setup_project_env.ps1 -CommandToRun 'python demos/webapp/run_webapp.py'
   .\setup_project_env.ps1 -CommandToRun 'python -m pytest tests/unit/ -v'
   .\setup_project_env.ps1 -CommandToRun 'python scripts/sherlock_watson/run_sherlock_watson_moriarty_robust.py'

🔧 CONFIGURATION:
   .\setup_project_env.ps1 -Setup
   .\setup_project_env.ps1 -CommandToRun 'python scripts/env/manage_environment.py setup'

📚 DOCUMENTATION:
   Voir: ENVIRONMENT_SETUP.md
   Voir: CORRECTED_RECOMMENDATIONS.md

⚠️  IMPORTANT: Ce script active automatiquement l'environnement dédié 'projet-is'
" -ForegroundColor Cyan
    exit 0
}

if ($Status) {
    Write-Host "🔍 Vérification rapide du statut environnement..." -ForegroundColor Cyan
    $CommandToRun = "python scripts/env/check_environment.py"
}

if ($Setup) {
    Write-Host "🔧 Configuration initiale de l'environnement..." -ForegroundColor Cyan
    $CommandToRun = "python scripts/env/manage_environment.py setup"
}

# Vérifications préliminaires
if ([string]::IsNullOrEmpty($CommandToRun)) {
    Write-Host "❌ Aucune commande spécifiée!" -ForegroundColor Red
    Write-Host "💡 Utilisez: .\setup_project_env.ps1 -Help pour voir les options" -ForegroundColor Yellow
    Write-Host "💡 Exemple: .\setup_project_env.ps1 -CommandToRun 'python --version'" -ForegroundColor Yellow
    Write-Host "💡 Status: .\setup_project_env.ps1 -Status" -ForegroundColor Yellow
    exit 1
}

# Information sur l'environnement requis
Write-Host "🎯 [INFO] Environnement cible: conda 'projet-is'" -ForegroundColor Cyan
Write-Host "📋 [COMMANDE] $CommandToRun" -ForegroundColor Cyan

# Raccourci vers le script de setup principal
$realScriptPath = Join-Path $PSScriptRoot "scripts\env\activate_project_env.ps1"

if (!(Test-Path $realScriptPath)) {
    Write-Host "❌ [ERREUR] Script d'activation non trouvé: $realScriptPath" -ForegroundColor Red
    Write-Host "💡 Vérifiez l'intégrité du projet" -ForegroundColor Yellow
    exit 1
}

& $realScriptPath -CommandToRun $CommandToRun
$exitCode = $LASTEXITCODE

# Message final informatif
Write-Host ""
Write-Host "🏁 =================================================================" -ForegroundColor Green
Write-Host "🏁 EXÉCUTION TERMINÉE - Code de sortie: $exitCode" -ForegroundColor Green
if ($exitCode -eq 0) {
    Write-Host "🏁 ✅ SUCCÈS - Environnement dédié opérationnel" -ForegroundColor Green
} else {
    Write-Host "🏁 ❌ ÉCHEC - Vérifiez l'environnement avec: .\setup_project_env.ps1 -Status" -ForegroundColor Red
}
Write-Host "🏁 =================================================================" -ForegroundColor Green

exit $exitCode