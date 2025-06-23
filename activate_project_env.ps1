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
    [switch]$EnableVerboseLogging = $false,
    [switch]$ForceReinstall = $false,
    [int]$CondaVerboseLevel = 0,
    [switch]$LaunchWebApp = $false,
    [switch]$DebugMode = $false,
    [string]$CommandOutputFile = $null
)

#--------------------------------------------------------------------------------
# Fonctions de base et utilitaires
#--------------------------------------------------------------------------------

# Fonction de logging simple
function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO",
        [System.Exception]$Exception = $null
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logLine = "[$timestamp] [$Level] $Message"
    if ($Exception) {
        $logLine += " | Exception: $($Exception.Message)"
    }
    # Écrire sur le flux d'erreur pour ne pas interférer avec la sortie de commande
    $Host.UI.WriteErrorLine($logLine)
}

# Fonction pour charger la configuration depuis le fichier .env
function Get-ProjectConfiguration {
    param([string]$EnvPath)
    $config = @{}
    if (-not (Test-Path $EnvPath)) {
        throw "Fichier de configuration .env introuvable à l'adresse '$EnvPath'."
    }
    Get-Content $EnvPath | ForEach-Object {
        if ($_ -match "^\s*#") { return } # Ignorer les commentaires
        if ($_ -match "^(.+?)=(.+)") {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim().Trim('"')
            $config[$key] = $value
        }
    }
    Write-Log "Configuration chargée depuis '$EnvPath'." "DEBUG"
    return $config
}

# Fonction pour trouver l'exécutable Python (simplifiée)
function Get-PythonExecutable {
    $executable = Get-Command -Name "python" -ErrorAction SilentlyContinue
    if ($executable) {
        $path = $executable.Source
        Write-Log "Exécutable Python trouvé: $path"
        return $path
    }
    throw "Aucun exécutable 'python' trouvé dans le PATH. Veuillez l'installer."
}

#--------------------------------------------------------------------------------
# Fonctions modulaires principales
#--------------------------------------------------------------------------------

# Valide les prérequis (Python, scripts essentiels)
function Test-Prerequisites {
    param(
        [hashtable]$Config,
        [string]$ProjectRoot
    )
    $Global:PythonExecutable = Get-PythonExecutable
    $Config.Keys | ForEach-Object {
        if ($_ -like "*_SCRIPT") {
            $scriptPath = Join-Path $ProjectRoot $Config[$_]
            if (-not (Test-Path $scriptPath)) {
                throw "Script prérequis introuvable: $scriptPath"
            }
        }
    }
    Write-Log "Prérequis validés." "SUCCESS"
}

# Initialise l'environnement (variables, etc.)
function Initialize-ProjectEnvironment {
    param(
        [string]$PythonExecutable,
        [string]$PortManagerScript,
        [string]$ProjectRoot
    )
    Write-Log "Injection des variables d'environnement des ports..."
    $portManagerFullPath = Join-Path $ProjectRoot $PortManagerScript
    try {
        $envVars = & $PythonExecutable $portManagerFullPath --export-env
        foreach ($line in $envVars) {
            if ($line -match "^(.+?)=(.+)$") {
                $key = $matches[1]
                $value = $matches[2]
                Set-Item -Path "env:$key" -Value $value
                Write-Log "Variable injectée: $key" "DEBUG"
            }
        }
        Write-Log "Variables d'environnement des ports injectées." "SUCCESS"
    }
    catch {
        throw "Échec de l'injection des variables d'environnement des ports."
    }
}

# Construit la commande à exécuter
function Build-Command {
    param(
        [string]$CommandToRun,
        [string]$PythonScriptPath,
        [string]$ProjectRoot
    )
    if ($PythonScriptPath) {
        $fullPath = Join-Path $ProjectRoot $PythonScriptPath
        if (-not (Test-Path $fullPath)) {
            throw "Le fichier Python spécifié via -PythonScriptPath est introuvable: $fullPath"
        }
        return "$($Global:PythonExecutable) `"$fullPath`""
    }
    return $CommandToRun
}

# Invoque le gestionnaire Python pour activer l'environnement et exécuter la commande
function Invoke-PythonManager {
    param(
        [hashtable]$Config,
        [string]$Command,
        [bool]$DebugMode,
        [string]$ProjectRoot
    )
    if (-not $Command) {
        Write-Log "Activation simple terminée. Aucune commande à exécuter." "SUCCESS"
        return
    }

    $managerModule = if ($DebugMode) { $Config["DEBUG_MANAGER_MODULE"] } else { $Config["MANAGER_MODULE"] }
    $managerPath = Join-Path $ProjectRoot $managerModule
    if (-not (Test-Path $managerPath)) {
        throw "Le script de gestion Python '$managerPath' est introuvable."
    }

    $managerArgs = @(
        "--command", $Command,
        "--env-name", $Config["CONDA_ENV_NAME"],
        "--verbose" # Simplifié pour toujours être verbeux
    )

    Write-Log "Invocation du gestionnaire Python: $managerPath"
    try {
        # Le script Python va maintenant gérer l'activation et l'exécution
        & $Global:PythonExecutable $managerPath $managerArgs
        if ($LASTEXITCODE -ne 0) {
            throw "Le gestionnaire Python a échoué. Voir les logs ci-dessus."
        }
        Write-Log "Le gestionnaire Python a terminé avec succès." "SUCCESS"
    }
    catch {
        throw "Erreur lors de l'invocation du gestionnaire Python."
    }
}

# Nettoie les ressources (ports, etc.)
function Clear-Resources {
    param(
        [string]$PortManagerScript,
        [string]$ProjectRoot
    )
    if (-not $Global:PythonExecutable) {
        Write-Log "Python non disponible, impossible de nettoyer les ressources." "WARNING"
        return
    }
    $portManagerFullPath = Join-Path $ProjectRoot $PortManagerScript
    if (Test-Path $portManagerFullPath) {
        Write-Log "Nettoyage du verrouillage de port..."
        & $Global:PythonExecutable $portManagerFullPath --unlock *>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Log "Verrouillage de port nettoyé." "SUCCESS"
        }
        else {
            Write-Log "Échec du nettoyage du verrouillage de port." "WARNING"
        }
    }
}

#--------------------------------------------------------------------------------
# Exécution principale
#--------------------------------------------------------------------------------

$ProjectRoot = $PSScriptRoot
$ErrorActionPreference = "Stop"

try {
    # Phase 1: Configuration
    $envFilePath = Join-Path $ProjectRoot ".env"
    $config = Get-ProjectConfiguration -EnvPath $envFilePath

    # Phase 2: Prérequis
    Test-Prerequisites -Config $config -ProjectRoot $ProjectRoot

    # Phase 3: Initialisation
    Initialize-ProjectEnvironment -PythonExecutable $Global:PythonExecutable -PortManagerScript $config["PORT_MANAGER_SCRIPT"] -ProjectRoot $ProjectRoot

    # Phase 4: Exécution
    $command = Build-Command -CommandToRun $CommandToRun -PythonScriptPath $PythonScriptPath -ProjectRoot $ProjectRoot
    Invoke-PythonManager -Config $config -Command $command -DebugMode $DebugMode -ProjectRoot $ProjectRoot

}
catch {
    Write-Log "Une erreur critique est survenue." -Level "ERROR" -Exception $_.Exception
    # Le bloc finally s'exécutera quand même
    exit 1
}
finally {
    # Phase 5: Nettoyage
    Clear-Resources -PortManagerScript $config["PORT_MANAGER_SCRIPT"] -ProjectRoot $ProjectRoot
    Write-Log "Fin du script d'environnement." "DEBUG"
}