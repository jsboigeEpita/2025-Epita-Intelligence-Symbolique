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
        # La commande est construite pour que le module Python fasse deux choses:
        # 1. --setup-vars: Charger les variables d'environnement.
        # 2. --run-command: Exécuter la commande passée par PowerShell.
        # `$CommandToRun` doit être la fin de la ligne de commande car `nargs=REMAINDER`
        # dans le script Python consomme tout ce qui suit.
        $PythonCommand = "python -m $PythonModule --setup-vars --run-command `"$CommandToRun`""
        
        # Commande finale à exécuter dans l'environnement conda.
        $CondaCommand = "conda run --no-capture-output -n projet-is $PythonCommand"

        if ($CommandOutputFile) {
            Write-Stderr "Génération de la commande pour le fichier de sortie : $CommandOutputFile"
            Set-Content -Path $CommandOutputFile -Value $CondaCommand
            Write-Stderr "Commande générée avec succès."
        } else {
            Write-Stderr "Exécution de la commande via le wrapper Python : $PythonCommand"
            Invoke-Expression -Command $CondaCommand
            $exitCode = $LASTEXITCODE
            if ($exitCode -ne 0) {
                Write-Stderr "ERREUR: La commande a échoué avec le code de sortie: $exitCode"
            }
            exit $exitCode
        }
    } else {
        # Si aucune commande n'est fournie, on exécute seulement le setup des variables.
        $PythonCommand = "python -m $PythonModule --setup-vars"
        $CondaCommand = "conda run --no-capture-output -n projet-is $PythonCommand"
        
        Write-Stderr "Activation de l'environnement (setup des variables via Python)..."
        Invoke-Expression -Command $CondaCommand
        $exitCode = $LASTEXITCODE
        if ($exitCode -ne 0) {
            Write-Stderr "ERREUR: Le setup de l'environnement a échoué avec le code de sortie: $exitCode"
        }
        exit $exitCode
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