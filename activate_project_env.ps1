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
    [switch]$Verbose = $false,
    [switch]$ForceReinstall = $false,
    [int]$CondaVerboseLevel = 0,
    [switch]$LaunchWebApp = $false,
    [switch]$DebugMode = $false
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
    $candidates = @("py", "python3", "python")
    $StoreAppPath = [System.IO.Path]::Combine($env:LOCALAPPDATA, "Microsoft", "WindowsApps")

    foreach ($candidate in $candidates) {
        $executables = Get-Command $candidate -All -ErrorAction SilentlyContinue
        if (-not $executables) {
            continue
        }

        # Itérer sur tous les exécutables trouvés pour ce candidat
        foreach ($exec in $executables) {
            try {
                $path = $exec.Source
                $resolvedPath = [System.IO.Path]::GetFullPath($path)
                
                # Vérifier si le chemin résolu n'est pas dans le dossier des applications du store
                if ($IsWindows -and $resolvedPath.StartsWith($StoreAppPath, [System.StringComparison]::OrdinalIgnoreCase)) {
                    Write-Log "Ignoré: Exécutable Python '$path' semble être un stub du Microsoft Store." "DEBUG"
                    continue
                }

                Write-Log "Exécutable Python valide trouvé: $path"
                return $path
            } catch {
                Write-Log "Erreur lors de la résolution du chemin pour '$($exec.Source)': $($_.Exception.Message)" "WARNING"
            }
        }
    }

    Write-Log "Aucun exécutable Python valide (non-stub) n'a été trouvé dans le PATH." "ERROR"
    return $null
}

# --- Début du Script ---
$portManagerScript = Join-Path $PSScriptRoot "project_core/config/port_manager.py"
$WebAppLauncherScript = Join-Path $PSScriptRoot "scripts/apps/webapp/launch_webapp_background.py"

try {
    # === 1. Configuration et Validation des chemins ===
    Write-Log "Initialisation du script d'environnement."

    $ProjectRoot = $PSScriptRoot
    
    # Sélection du script de gestion en fonction du mode de débogage
    if ($DebugMode) {
        Write-Log "Mode de débogage activé. Utilisation du gestionnaire d'environnement de débogage." "WARNING"
        $PythonManagerModule = "project_core/core_from_scripts/environment_manager.debug.py"
    } else {
        $PythonManagerModule = "project_core/core_from_scripts/environment_manager.py"
    }
    
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

    # === INJECTION DES VARIABLES D'ENV DES PORTS ===
    Write-Log "Injection des variables d'environnement des ports..." "INFO"
    if (-not (Test-Path $portManagerScript)) {
        Write-Log "Script port_manager.py introuvable à: $portManagerScript" "ERROR"
        exit 1
    }
    try {
        $envVars = & $PythonExecutable $portManagerScript --export-env
        foreach ($line in $envVars) {
            if ($line -match "^(.+?)=(.+)$") {
                $key = $matches[1]
                $value = $matches[2]
                Set-Item -Path "env:$key" -Value $value
                Write-Log "Variable d'environnement injectée: $key=$value" "DEBUG"
            }
        }
        Write-Log "Variables d'environnement des ports injectées avec succès." "SUCCESS"
    } catch {
        Write-Log "Échec de l'injection des variables d'environnement des ports : $($_.Exception.Message)" "ERROR"
        exit 1
    }

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
        # Le script Python gère maintenant la décomposition des commandes si nécessaire
        $ManagerArgs += "--command", $FinalCommandToRun
        # On ajoute le nouvel argument pour seulement construire la commande
        $ManagerArgs += "--get-command-only"
    } else {
         # Si pas de commande, on ne peut pas utiliser get-command-only.
         # Le script s'arrête après l'activation simple.
         Write-Log "Aucune commande à exécuter. Activation simple de l'environnement." "INFO"
    }

    if ($Verbose) {
        $ManagerArgs += "--verbose"
    }
    
    if ($ForceReinstall) {
        Write-Log "Option -ForceReinstall détectée. L'environnement Conda sera forcé à la réinstallation." "INFO"
        $ManagerArgs += "--reinstall", "conda"
    }

    if ($CondaVerboseLevel -gt 0) {
        Write-Log "Niveau de verbosité Conda: $CondaVerboseLevel" "INFO"
        $ManagerArgs += "--conda-verbose-level", $CondaVerboseLevel
    }
    
    Write-Log "Arguments passés au manager Python: $($ManagerArgs -join ' ')" "DEBUG"

   # === 5. Construction de la commande finale ===
   # Le script n'exécute plus rien, il génère la commande pour le script appelant.

   # Si pas de commande spécifiée, le travail est déjà fait (variables d'env injectées)
   if (-not $FinalCommandToRun) {
       Write-Log "Activation simple terminée. Aucune commande à générer." "SUCCESS"
       exit 0
   }
   
   Write-Log "Génération de la commande d'exécution finale via le manager Python..."

   # Appel du script Python, qui va maintenant écrire la commande finale sur stdout
   $FinalExecutableCommand = & $PythonExecutable $ManagerArgs
   $exitCode = $LASTEXITCODE

   if ($exitCode -ne 0) {
       # Si le script de génération de commande échoue, c'est une erreur critique.
       # Les logs d'erreur de Python devraient être sur stderr.
       throw "Le script de génération de commande a échoué avec le code: $exitCode."
   }

   if (-not $FinalExecutableCommand) {
       throw "Le script de génération n'a renvoyé aucune commande."
   }
   
   # Écrire la commande finale sur la sortie standard pour que le script appelant la récupère
   Write-Output $FinalExecutableCommand
   
   # Le script se termine ici. Le code de sortie de la commande sera géré par l'appelant.

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
finally {
    # Assurer le déverrouillage systématique du port
    Write-Log "Nettoyage du verrouillage de port (finally)..." "INFO"
    try {
        & $PythonExecutable $portManagerScript --unlock
        Write-Log "Verrouillage de port nettoyé." "SUCCESS"
    } catch {
        Write-Log "Avertissement: Échec du nettoyage du verrouillage de port. Un nettoyage manuel peut être requis." "WARNING"
    }

    # Et on s'assure que le serveur web est bien terminé
    if ($LaunchWebApp) {
        Write-Log "Arrêt du serveur web en arrière-plan (finally)..." "INFO"
        try {
            $killArgs = $ManagerArgs.Clone()
            $killArgs += "--command", "$PythonExecutable `"$WebAppLauncherScript`" kill"
            & $PythonExecutable $killArgs
            Write-Log "Commande d'arrêt du serveur envoyée." "SUCCESS"
        } catch {
            Write-Log "Avertissement: Échec de l'envoi de la commande d'arrêt du serveur." "WARNING"
        }
    }
}

Write-Log "Fin du script d'environnement." "DEBUG"