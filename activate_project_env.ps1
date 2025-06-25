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
Write-Host "DEBUG: CommandToRun = $CommandToRun"
    if ($CommandToRun) {
        # --- Logique de `main` ---
        # Définir le PYTHONPATH pour inclure la racine du projet.
        $ProjectRoot = Resolve-Path $PSScriptRoot
        Write-Stderr "Ajout de la racine du projet au PYTHONPATH : $ProjectRoot"
        $env:PYTHONPATH = "$ProjectRoot" + [IO.Path]::PathSeparator + $env:PYTHONPATH
        
        # Détermine le nom de l'environnement Conda dynamiquement
        $env_name = "projet-is" # Fallback par défaut
        $config_file = Join-Path $PSScriptRoot "argumentation_analysis" "config" "environment_config.py"
        if(Test-Path $config_file) {
            $config_content = Get-Content $config_file
            $env_name_line = $config_content | Select-String -Pattern 'CONDA_ENV_NAME\s*=\s*"([^"]+)"'
            if($env_name_line) {
                $env_name = $env_name_line.Matches[0].Groups[1].Value
            }
        }
        Write-Stderr "Recherche de l'environnement Conda: $env_name"

        # Trouve le chemin de l'environnement Conda de manière robuste
        $env_line = conda info --envs | findstr.exe /R /C:"^..*\b$env_name\b.*"
        
        if (-not $env_line) {
            throw "L'environnement Conda '$env_name' n'a pas été trouvé."
        }
        if ($env_line.Count -gt 1) {
            $env_line = $env_line[0] # Prend le premier si plusieurs lignes correspondent
        }

        $env_path = ($env_line.Split(' ',[System.StringSplitOptions]::RemoveEmptyEntries)[-1])
        $python_exe = Join-Path $env_path "python.exe"

        if (-not (Test-Path $python_exe)) {
            throw "python.exe non trouvé dans l'environnement '$env_name' au chemin '$python_exe'."
        }

        Write-Stderr "Utilisation de l'interpréteur Python: $python_exe"
        
        # Encapsule la commande pour une exécution robuste avec Invoke-Expression
        $command_to_execute = "$python_exe -m $CommandToRun"

        # Exécute la commande et gère la sortie
        Write-Stderr "Exécution: $command_to_execute"
        Invoke-Expression -Command $command_to_execute
        
        $exitCode = $LASTEXITCODE
        if ($exitCode -ne 0) {
            Write-Stderr "ERREUR: La commande a échoué avec le code de sortie: $exitCode"
        }
        exit $exitCode

    } else {
        # Comportement par défaut : Lancer un shell interactif dans l'environnement
        $env_name = "projet-is" # Assurez-vous que le nom de l'environnement est correct
        Write-Stderr "Aucune commande spécifiée. Lancement d'un shell interactif dans '$env_name'."
        conda activate $env_name
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