#!/usr/bin/env pwsh
<#
.SYNOPSIS
Script d'activation de l'environnement projet (refactorisé avec Python)

.DESCRIPTION
Active l'environnement conda du projet et exécute optionnellement une commande.
Utilise les modules Python mutualisés pour la gestion d'environnement.

.PARAMETER CommandToRun
Commande à exécuter après activation de l'environnement

.EXAMPLE
.\activate_project_env.ps1
.\activate_project_env.ps1 -CommandToRun "python --version"

.NOTES
Refactorisé - Utilise scripts/core/environment_manager.py
#>

param(
    [string]$CommandToRun = $null,
    [string]$CommandOutputFile = $null
)

# Ce script est maintenant un "wrapper mince". Toute la logique de configuration
# est déléguée au module Python pour garantir qu'elle soit indépendante de l'OS.

$ErrorActionPreference = "Stop"

# Nom du module Python qui sert de point d'entrée central
$PythonModule = "project_core.core_from_scripts.environment_manager"

# Fonction pour écrire les messages sur la sortie d'erreur, pour ne pas polluer stdout
function Write-Stderr {
    param([string]$Message)
    $Host.UI.WriteErrorLine($Message)
}

try {
    if ($CommandToRun) {
        # Exécution directe: On ne passe plus par le wrapper python.
        # conda run active l'environnement et exécute la commande.
        $CondaCommand = "conda run --no-capture-output -n projet-is $CommandToRun"

        Write-Stderr "Exécution directe de la commande dans l'environnement 'projet-is': $CommandToRun"
        Invoke-Expression -Command $CondaCommand
        $exitCode = $LASTEXITCODE
        if ($exitCode -ne 0) {
            Write-Stderr "ERREUR: La commande a échoué avec le code de sortie: $exitCode"
        }
        exit $exitCode
    } else {
        # Comportement par défaut: lancer un shell interactif
        Write-Stderr "Aucune commande spécifiée. Lancement d'un shell interactif dans 'projet-is'."
        conda activate projet-is
    }
}
catch {
    Write-Stderr "--- ERREUR CRITIQUE DANS activate_project_env.ps1 ---"
    $errorRecord = $_
    $line = $errorRecord.InvocationInfo.ScriptLineNumber
    $scriptName = $errorRecord.InvocationInfo.ScriptName
    Write-Stderr "Message: $($_.Exception.Message) à $scriptName (Ligne: $line)"
    exit 1
}