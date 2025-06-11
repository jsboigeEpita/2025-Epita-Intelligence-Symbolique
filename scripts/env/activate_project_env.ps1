<#
.SYNOPSIS
Script d'activation de l'environnement Oracle Enhanced v2.1.0

.DESCRIPTION
Active l'environnement Python du projet et execute une commande specifiee.
Gere automatiquement l'activation de conda/venv et la configuration des paths.

.PARAMETER CommandToRun
Commande a executer dans l'environnement active

.EXAMPLE
powershell -File .\scripts\env\activate_project_env.ps1 -CommandToRun "python -m scripts.maintenance.analyze_obsolete_documentation --full-analysis"
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$CommandToRun,

    [Parameter(Mandatory=$false)]
    [switch]$ForceReinstall
)

# Configuration
$ProjectRoot = (Get-Item -Path $PSScriptRoot).Parent.Parent.FullName
# Correction du chemin en utilisant la concaténation de chaînes, plus fiable sous PowerShell pour les chemins de fichiers
$EnvironmentManagerScript = Join-Path $ProjectRoot "scripts\core\environment_manager.py"
$PythonSystemExecutable = "python" # "python.exe" ou "python3" selon le PATH système

# Définir un drapeau pour que les scripts Python (y compris le manager) sachent qu'ils sont exécutés par ce script.
# Cela évite les boucles d'activation.
$env:IS_ACTIVATION_SCRIPT_RUNNING = "true"

Write-Host "🚀 =====================================================================" -ForegroundColor Green
Write-Host "🚀 DÉLÉGATION À ENVIRONMENT_MANAGER.PY - Oracle Enhanced v2.3.0" -ForegroundColor Green
Write-Host "🚀 =====================================================================" -ForegroundColor Green
Write-Host "[PROJET] Racine projet: $ProjectRoot" -ForegroundColor Cyan
Write-Host "[INFO] Script d'activation: $PSCommandPath" -ForegroundColor Gray
Write-Host "[MANAGER] Cible: $EnvironmentManagerScript" -ForegroundColor Cyan

# Changer vers la racine du projet est crucial pour que les chemins relatifs dans Python fonctionnent correctement
Push-Location $ProjectRoot

try {
    # La seule responsabilité de ce script est d'appeler le gestionnaire Python centralisé.
    # Il passe la commande à exécuter en argument.
    # Le gestionnaire Python s'occupe de TOUT : chargement .env, activation conda, PATH, JAVA_HOME, etc.
    
    Write-Host "[EXECUTION] Appel du manager Python pour activer l'environnement et lancer la commande..." -ForegroundColor White
    
    # Construction de la liste d'arguments pour l'opérateur d'appel '&'
    # C'est la manière la plus sûre de passer des arguments contenant des espaces ou des guillemets.
    $ArgumentList = @(
        "-u", # Exécuter sans buffer pour voir les logs en temps réel
        $EnvironmentManagerScript
    )

    if ($ForceReinstall.IsPresent) {
        $ArgumentList += "--force-reinstall"
    }

    if ($CommandToRun) {
        $ArgumentList += "--command"
        $ArgumentList += $CommandToRun
    }
    
    Write-Host "[CMD] & '$PythonSystemExecutable' $ArgumentList" -ForegroundColor Gray
    
    # Exécution du script Python.
    & $PythonSystemExecutable $ArgumentList
    
    # Récupérer le code de sortie du processus Python
    $ExitCode = $LASTEXITCODE
    
    Write-Host ("=" * 80) -ForegroundColor Gray
    
    if ($ExitCode -eq 0) {
        Write-Host "[SUCCES] Environment Manager a terminé avec succès (code: $ExitCode)" -ForegroundColor Green
    } else {
        Write-Host "[ECHEC] Environment Manager a terminé avec une erreur (code: $ExitCode)" -ForegroundColor Red
    }
    
    exit $ExitCode
    
} catch {
    Write-Host "[ERREUR FATALE] Échec de l'appel à environment_manager.py: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
    
} finally {
    # Retour au repertoire original
    Pop-Location
}