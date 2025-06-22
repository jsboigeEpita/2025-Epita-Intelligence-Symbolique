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
    [string]$PythonScriptPath = $null,
    [switch]$Verbose = $false
)

# Fonction de logging simple
function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )
    # On écrit tout sur le flux d'erreur (stderr) pour ne pas polluer le stdout
    # qui est utilisé pour récupérer le résultat JSON des scripts Python.
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logLine = "[$timestamp] [$Level] $Message"
    $Host.UI.WriteErrorLine($logLine)
}

# Fonction pour trouver un exécutable Python robuste
function Get-PythonExecutable {
    # Windows: py.exe est le plus fiable
    if ($IsWindows) {
        $pythonExec = Get-Command "py.exe" -ErrorAction SilentlyContinue
        if ($pythonExec) {
            Write-Log "Lanceur Python 'py.exe' trouvé. Utilisation recommandée."
            return $pythonExec.Source
        }
    }
    # Ordre de préférence: python3, python
    $candidates = @("python3", "python")
    foreach ($candidate in $candidates) {
        $pythonExec = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($pythonExec) {
            Write-Log "Exécutable Python trouvé: $($pythonExec.Source)"
            return $pythonExec.Source
        }
    }
    Write-Log "Aucun exécutable Python (py.exe, python3, python) n'a été trouvé dans le PATH." "ERROR"
    return $null
}


# --- Début du Script ---

try {
    # === 1. Configuration et Validation des chemins ===
    Write-Log "Initialisation du script d'environnement."

    $ProjectRoot = $PSScriptRoot
    $PythonManagerModule = "project_core/core_from_scripts/environment_manager.py"
    $PythonManagerScriptPath = Join-Path $ProjectRoot $PythonManagerModule

    if (-not (Test-Path $PythonManagerScriptPath)) {
        throw "Le script de gestion d'environnement Python est introuvable: $PythonManagerScriptPath"
    }

    # === 2. Détection de l'interpréteur Python ===
    $PythonExecutable = Get-PythonExecutable
    if (-not $PythonExecutable) {
        throw "Python n'est pas installé ou non accessible. Veuillez l'installer et l'ajouter à votre PATH."
    }
    Write-Log "Utilisation de l'interpréteur: $PythonExecutable"

    # === 3. Construction de la commande à exécuter ===
    $FinalCommandToRun = $CommandToRun
    
    # Raccourci pour exécuter un script python directement
    if ($PythonScriptPath) {
        $FullScriptPath = Join-Path $ProjectRoot $PythonScriptPath
        if (-not (Test-Path $FullScriptPath)) {
            throw "Le fichier Python spécifié via -PythonScriptPath est introuvable: $FullScriptPath"
        }
        # On met la commande entre guillemets pour gérer les espaces dans les chemins
        $FinalCommandToRun = "$PythonExecutable `"$FullScriptPath`""
        Write-Log "Commande à exécuter définie via -PythonScriptPath: $FinalCommandToRun"
    }
    
    # === 4. Préparation des arguments pour le script Python manager ===
    $ManagerArgs = @($PythonManagerScriptPath)
    if ($FinalCommandToRun) {
        # On décompose les commandes si nécessaire (support du ';')
         $commands = $FinalCommandToRun.Split(';') | ForEach-Object {$_.Trim()}
         foreach ($cmd in $commands) {
            if (-not [string]::IsNullOrWhiteSpace($cmd)) {
                $ManagerArgs += "--command", $cmd
            }
         }
    }
    if ($Verbose) {
        $ManagerArgs += "--verbose"
    }
    
    Write-Log "Arguments passés au manager Python: $ManagerArgs" "DEBUG"

    # === 5. Exécution ===
    Write-Log "Lancement du gestionnaire d'environnement Python pour activation et exécution..."
    & $PythonExecutable $ManagerArgs
    $exitCode = $LASTEXITCODE

    if ($exitCode -ne 0) {
        Write-Log "Le script gestionnaire Python a terminé avec un code d'erreur: $exitCode" "ERROR"
    } else {
        Write-Log "Le script gestionnaire Python a terminé avec succès." "SUCCESS"
    }
    
    exit $exitCode

} catch {
    # Capture toutes les erreurs (PowerShell ou `throw`)
    Write-Log "Erreur critique dans le script $($MyInvocation.MyCommand.Name):" "ERROR"
    Write-Log "Message: $($_.Exception.Message)" "ERROR"
    # Endroit où l'erreur a eu lieu
    $errorRecord = $_
    $line = $errorRecord.InvocationInfo.ScriptLineNumber
    $pos = $errorRecord.InvocationInfo.OffsetInLine
    $scriptName = $errorRecord.InvocationInfo.ScriptName
    Write-Log "Erreur à: $scriptName (Ligne: $line, Colonne: $pos)" "ERROR"
    exit 1
}

Write-Log "Fin du script d'environnement." "DEBUG"