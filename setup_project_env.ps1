#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Wrapper pour l'activation et la gestion de l'environnement projet.
.DESCRIPTION
    Ce script délègue toutes les opérations au script d'activation principal 'activate_project_env.ps1',
    en traduisant les anciens paramètres (-Setup, -Status) en commandes modernes.
.PARAMETER CommandToRun
    Commande à exécuter après activation (passée à activate_project_env.ps1).
.PARAMETER Setup
    Raccourci pour configurer l'environnement. Équivaut à -CommandToRun 'python project_core/core_from_scripts/environment_manager.py setup'
.PARAMETER Status
    Raccourci pour vérifier le statut de l'environnement. Équivaut à -CommandToRun 'python project_core/core_from_scripts/environment_manager.py --check-only'
.EXAMPLE
    .\setup_project_env.ps1 -Setup
    .\setup_project_env.ps1 -Status
    .\setup_project_env.ps1 -CommandToRun "pytest ./tests"
#>

param (
    [string]$CommandToRun,
    [switch]$Setup,
    [switch]$Status,
    [switch]$Help # Gardé pour la compatibilité
)

# --- Bannière ---
Write-Host "=================================================================" -ForegroundColor Green
Write-Host "ORACLE ENHANCED v2.1.0 - Wrapper d'Environnement" -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Green

if ($Help) {
    Get-Help $MyInvocation.MyCommand.Path -Full
    exit 0
}

# --- Conversion des anciens paramètres en CommandToRun ---
$FinalCommand = $CommandToRun

if ($Setup) {
    Write-Host "[INFO] Mode SETUP activé." -ForegroundColor Cyan
    $FinalCommand = "python project_core/core_from_scripts/environment_manager.py --reinstall all"
}

if ($Status) {
    Write-Host "[INFO] Mode STATUS activé." -ForegroundColor Cyan
    $FinalCommand = "python project_core/core_from_scripts/environment_manager.py --check-only"
}

# --- Validation ---
if (-not $FinalCommand) {
    Write-Host "[ERREUR] Aucune action spécifiée. Utilisez -Setup, -Status, -CommandToRun ou -Help." -ForegroundColor Red
    exit 1
}

# --- Exécution ---
# Si le mode -Setup est activé, on exécute directement le script Python
# car l'environnement n'existe peut-être pas encore, et l'activation échouerait.
if ($Setup) {
    Write-Host "[INFO] Exécution directe de la commande de réinstallation..." -ForegroundColor Cyan
    # Exécuter python directement
    python project_core/core_from_scripts/environment_manager.py --reinstall all
    $exitCode = $LASTEXITCODE
} else {
    # Pour toutes les autres commandes, on utilise le script d'activation
    $ActivationScript = Join-Path $PSScriptRoot "activate_project_env.ps1"
    if (-not (Test-Path $ActivationScript)) {
        Write-Host "[ERREUR] Script d'activation principal introuvable: $ActivationScript" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "[INFO] Délégation au script: $ActivationScript" -ForegroundColor Cyan
    Write-Host "[INFO] Commande à exécuter: $FinalCommand" -ForegroundColor Cyan
    
    # Exécution du script d'activation avec la commande finale
    & $ActivationScript -CommandToRun $FinalCommand
    $exitCode = $LASTEXITCODE
}

# --- Résultat ---
Write-Host "=================================================================" -ForegroundColor Green
if ($exitCode -eq 0) {
    Write-Host "Opération terminée avec SUCCES (Code: $exitCode)" -ForegroundColor Green
} else {
    Write-Host "Opération terminée en ECHEC (Code: $exitCode)" -ForegroundColor Red
}
Write-Host "=================================================================" -ForegroundColor Green

exit $exitCode