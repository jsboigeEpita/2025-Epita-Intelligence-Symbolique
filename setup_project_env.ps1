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
    [switch]$Clean,
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

if ($Clean) {
    Write-Host "[INFO] Mode CLEAN activé. Tentative de suppression de l'environnement 'projet-is'." -ForegroundColor Yellow
    conda env remove -n projet-is --yes
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[AVERTISSEMENT] La suppression de l'environnement a échoué. Il se peut qu'il n'ait pas existé, ou qu'un problème soit survenu. Le script va continuer." -ForegroundColor Yellow
    } else {
        Write-Host "[INFO] Environnement 'projet-is' supprimé avec succès." -ForegroundColor Green
    }
    # On force le mode Setup après un clean
    $Setup = $true
}

# --- Conversion des anciens paramètres en CommandToRun ---
$FinalCommand = $CommandToRun

if ($Setup) {
    Write-Host "[INFO] Mode SETUP activé. Forçage d'une réinstallation propre pour la stabilité." -ForegroundColor Cyan
    $Clean = $true # Forcer le nettoyage
}

if ($Clean) {
    Write-Host "[INFO] Mode CLEAN activé. Tentative de suppression de l'environnement 'projet-is'." -ForegroundColor Yellow
    # Arrêter les processus bloquants d'abord
    Get-Process | Where-Object { $_.ProcessName -like "*conda*" -or $_.ProcessName -like "*mamba*" } | Stop-Process -Force -ErrorAction SilentlyContinue
    conda env remove -n projet-is --yes
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[AVERTISSEMENT] La suppression de l'environnement a échoué. Il se peut qu'il n'ait pas existé, ou qu'un problème soit survenu. Le script va continuer." -ForegroundColor Yellow
    } else {
        Write-Host "[INFO] Environnement 'projet-is' supprimé avec succès." -ForegroundColor Green
    }
}

# --- Conversion des anciens paramètres en CommandToRun ---
$FinalCommand = $CommandToRun

if ($Setup) {
    # La seule stratégie fiable est de créer à partir de zéro
    $PackageManager = "conda"
    if (Get-Command mamba -ErrorAction SilentlyContinue) {
        $PackageManager = "mamba"
    }
    
    $SetupCommands = @(
        "$PackageManager env create --file environment.yml --yes -v",
        "$PackageManager install scipy=1.13.1 --force-reinstall --yes",
        "pip install -e .",
        "playwright install"
    )
    # On assigne une valeur factice pour passer la validation
    $FinalCommand = "setup"
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

# Information sur l'environnement requis
Write-Host "[INFO] Environnement cible: conda 'projet-is'" -ForegroundColor Cyan
Write-Host "[INFO] [COMMANDE] $CommandToRun" -ForegroundColor Cyan

# --- DÉLÉGATION AU SCRIPT D'ACTIVATION MODERNE ---
# Ce script est maintenant un simple alias pour activate_project_env.ps1
# qui contient la logique d'activation et d'exécution à jour.

Write-Host "[INFO] Délégation de l'exécution au script moderne 'activate_project_env.ps1'" -ForegroundColor Cyan

$ActivationScriptPath = Join-Path $PSScriptRoot "activate_project_env.ps1"

if (-not (Test-Path $ActivationScriptPath)) {
    Write-Host "[ERREUR] Le script d'activation principal 'activate_project_env.ps1' est introuvable." -ForegroundColor Red
    Write-Host "[INFO] Assurez-vous que le projet est complet." -ForegroundColor Yellow
    exit 1
}

# Construire les arguments pour le script d'activation
$ActivationArgs = @{
    CommandToRun = $FinalCommand
}

# Exécuter le script d'activation moderne en passant les arguments
if ($Setup) {
    # La première commande est create ou update, elle doit être exécutée directement
    $EnvManagementCommand = $SetupCommands[0]
    Write-Host "=================================================================" -ForegroundColor Green
    Write-Host "Exécution de la commande de gestion d'environnement: $EnvManagementCommand" -ForegroundColor Yellow
    Invoke-Expression -Command $EnvManagementCommand
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        Write-Host "La commande de gestion d'environnement a échoué avec le code $exitCode. Arrêt du setup." -ForegroundColor Red
        exit $exitCode
    }

    # Les commandes suivantes sont exécutées via le script d'activation
    for ($i = 1; $i -lt $SetupCommands.Length; $i++) {
        $cmd = $SetupCommands[$i]
        Write-Host "=================================================================" -ForegroundColor Green
        Write-Host "Exécution de la sous-commande SETUP: $cmd" -ForegroundColor Yellow
        $ActivationArgs = @{ CommandToRun = $cmd }
        & $ActivationScriptPath @ActivationArgs
        $exitCode = $LASTEXITCODE
        if ($exitCode -ne 0) {
            Write-Host "La sous-commande '$cmd' a échoué avec le code $exitCode. Arrêt du setup." -ForegroundColor Red
            exit $exitCode
        }
    }
} else {
    # Exécution normale pour les autres commandes
    & $ActivationScriptPath @ActivationArgs
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