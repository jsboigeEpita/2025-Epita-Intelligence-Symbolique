# =============================================================================
# Script de Nettoyage Agressif des Processus Node.js
# =============================================================================
#
# Auteur: Roo, Software Engineer
# Date: 27/06/2025
#
# Problème:
# Des processus 'node.exe' fantômes persistent et bloquent les ports
# nécessaires au démarrage du frontend, même après de multiples tentatives
# de nettoyage programmatique.
#
# Solution:
# Ce script identifie et arrête de force TOUS les processus 'node.exe'
# en cours d'exécution sur le système. Il fournit également des informations
# de diagnostic détaillées pour aider à identifier la source de ces processus.
#
# USAGE:
# 1. Ouvrir un terminal PowerShell en tant qu'administrateur.
# 2. Naviguer jusqu'au répertoire racine du projet.
# 3. Exécuter la commande: .\scripts\utils\cleanup_node.ps1
#
# =============================================================================

Write-Host "--- Début du nettoyage agressif des processus Node.js ---" -ForegroundColor Yellow

# Obtenir tous les processus 'node'
$nodeProcesses = Get-Process -Name "node" -ErrorAction SilentlyContinue

if ($null -eq $nodeProcesses) {
    Write-Host "Aucun processus 'node.exe' trouvé. Le système semble propre." -ForegroundColor Green
    Write-Host "--------------------------------------------------------"
    exit 0
}

Write-Host "Processus 'node.exe' trouvés. Tentative d'arrêt forcé..." -ForegroundColor Cyan

foreach ($proc in $nodeProcesses) {
    try {
        $processId = $proc.Id
        $processPath = $proc.Path
        $commandLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $processId").CommandLine

        Write-Host "--------------------------------------------------------"
        Write-Host "  - Arrêt du processus:"
        Write-Host "    - PID          : $processId"
        Write-Host "    - Exécutable   : $processPath"
        Write-Host "    - Ligne de Cmd : $commandLine"

        Stop-Process -Id $processId -Force -ErrorAction Stop
        
        Write-Host "    - STATUT       : Arrêté avec succès." -ForegroundColor Green
    }
    catch {
        Write-Host "    - ERREUR       : Impossible d'arrêter le processus PID $processId." -ForegroundColor Red
        Write-Host "      Raison: $_" -ForegroundColor Red
    }
}

Write-Host "--------------------------------------------------------"
Write-Host "--- Nettoyage terminé. ---" -ForegroundColor Yellow
Write-Host "Veuillez maintenant relancer le script d'orchestration."