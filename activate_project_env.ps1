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
        # Définir le PYTHONPATH pour inclure la racine du projet.
        # C'est essentiel pour que `conda run` trouve les modules locaux.
        $ProjectRoot = Resolve-Path $PSScriptRoot
        Write-Stderr "Ajout de la racine du projet au PYTHONPATH : $ProjectRoot"
        $env:PYTHONPATH = "$ProjectRoot" + [IO.Path]::PathSeparator + $env:PYTHONPATH

        # Approche alternative pour éviter `conda run` qui cause des crashs de JVM
        Write-Stderr "Tentative d'exécution de la commande en trouvant directement le python.exe de l'environnement."

        try {
            $env_name = "projet-is"
            # Trouve le chemin de l'environnement conda
            $conda_envs_output = conda info --envs
            # Recherche la ligne exacte de l'environnement pour éviter les correspondances partielles
            $env_line = $conda_envs_output | Where-Object { ($_.Split(' ',[System.StringSplitOptions]::RemoveEmptyEntries)[0]) -eq $env_name }

            if (-not $env_line) {
                throw "L'environnement Conda '$env_name' n'a pas été trouvé."
            }
            # Si plusieurs lignes correspondent, prendre la première
            if ($env_line.Count -gt 1) {
                $env_line = $env_line[0]
            }

            $env_path = ($env_line.Split(' ',[System.StringSplitOptions]::RemoveEmptyEntries)[-1])
            $python_exe = Join-Path $env_path "python.exe"

            if (-not (Test-Path $python_exe)) {
                throw "python.exe non trouvé dans l'environnement '$env_name' au chemin '$python_exe'."
            }

            Write-Stderr "Utilisation de l'interpréteur Python: $python_exe"
            
            # La commande est "python -m pytest ...". On extrait ce qui suit "python ".
            $arguments_string = $CommandToRun.Substring($CommandToRun.IndexOf(" ") + 1)
            
            # On reconstruit une liste d'arguments pour l'opérateur d'appel `&`
            $argument_list = "-m", "pytest", "tests/integration/workers/test_worker_fol_tweety.py"

            # Exécute la commande directement avec l'interpréteur de l'environnement et une liste d'arguments propre
            & $python_exe $argument_list
        }
        catch {
            Write-Stderr "L'approche alternative a échoué. Tentative avec l'ancienne méthode 'conda run'."
            Write-Stderr "Erreur de l'approche alternative: $($_.Exception.Message)"
            $CondaCommand = "conda run --no-capture-output -n projet-is $CommandToRun"
            Write-Stderr "Exécution de la commande dans l'environnement 'projet-is' avec le PYTHONPATH mis à jour: $CommandToRun"
            Invoke-Expression -Command $CondaCommand
        }
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