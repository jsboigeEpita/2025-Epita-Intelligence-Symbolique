# Script PowerShell pour installer automatiquement Visual Studio Build Tools 2022
# avec les composants nécessaires pour compiler les extensions Python

# Fonction pour afficher les messages de log avec timestamp
function Log-Message {
    param (
        [Parameter(Mandatory=$true)]
        [string]$Level,
        
        [Parameter(Mandatory=$true)]
        [string]$Message
    )
    
    $timestamp = Get-Date -Format "HH:mm:ss"
    Write-Host "$timestamp [$Level] $Message"
}

# Fonction pour vérifier si l'utilisateur a des droits d'administrateur
function Test-Admin {
    $currentUser = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $currentUser.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Fonction pour vérifier si Visual Studio Build Tools est déjà installé
function Check-BuildTools {
    $vsWhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
    
    if (-not (Test-Path -Path $vsWhere)) {
        return $false
    }
    
    $buildTools = & $vsWhere -products Microsoft.VisualStudio.Product.BuildTools -requires Microsoft.VisualCpp.Tools.Host.x86 -latest -property installationPath
    
    if (-not $buildTools) {
        return $false
    }
    
    return $true
}

# Point d'entrée principal du script
Log-Message -Level "INFO" -Message "Vérification des prérequis pour l'installation de Visual Studio Build Tools 2022..."

# Vérifier les droits d'administrateur
if (-not (Test-Admin)) {
    Log-Message -Level "ERROR" -Message "Ce script doit être exécuté avec des droits d'administrateur."
    Log-Message -Level "ERROR" -Message "Veuillez redémarrer PowerShell en tant qu'administrateur et réexécuter ce script."
    exit 1
}

# Vérifier si Visual Studio Build Tools est déjà installé
if (Check-BuildTools) {
    Log-Message -Level "INFO" -Message "Visual Studio Build Tools avec les outils C++ est déjà installé."
    Log-Message -Level "INFO" -Message "Aucune installation supplémentaire n'est nécessaire."
    exit 0
}

# Créer un répertoire temporaire pour le téléchargement
$tempDir = [System.IO.Path]::GetTempPath() + [System.Guid]::NewGuid().ToString()
New-Item -Path $tempDir -ItemType Directory -Force | Out-Null

try {
    # URL de téléchargement de Visual Studio Build Tools 2022
    $buildToolsUrl = "https://aka.ms/vs/17/release/vs_BuildTools.exe"
    $buildToolsInstaller = Join-Path -Path $tempDir -ChildPath "vs_BuildTools.exe"
    
    # Télécharger l'installateur
    Log-Message -Level "INFO" -Message "Téléchargement de Visual Studio Build Tools 2022..."
    $webClient = New-Object System.Net.WebClient
    $webClient.DownloadFile($buildToolsUrl, $buildToolsInstaller)
    
    # Vérifier que le téléchargement a réussi
    if (-not (Test-Path -Path $buildToolsInstaller)) {
        Log-Message -Level "ERROR" -Message "Échec du téléchargement de Visual Studio Build Tools 2022."
        exit 1
    }
    
    Log-Message -Level "INFO" -Message "Téléchargement terminé. Lancement de l'installation..."
    
    # Installer Visual Studio Build Tools avec les composants nécessaires
    # --add : Composants à installer
    # --quiet : Installation silencieuse
    # --norestart : Ne pas redémarrer après l'installation
    # --wait : Attendre la fin de l'installation
    $installArgs = @(
        "--add", "Microsoft.VisualStudio.Workload.VCTools",
        "--add", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
        "--add", "Microsoft.VisualStudio.Component.Windows10SDK.19041",
        "--add", "Microsoft.VisualStudio.Component.VC.CMake.Project",
        "--quiet", "--norestart", "--wait"
    )
    
    Log-Message -Level "INFO" -Message "Installation de Visual Studio Build Tools 2022 avec les composants nécessaires..."
    Log-Message -Level "INFO" -Message "Cette opération peut prendre plusieurs minutes. Veuillez patienter..."
    
    # Lancer l'installation
    $process = Start-Process -FilePath $buildToolsInstaller -ArgumentList $installArgs -PassThru -Wait
    
    # Vérifier le code de sortie
    if ($process.ExitCode -eq 0 -or $process.ExitCode -eq 3010) {
        Log-Message -Level "INFO" -Message "Installation de Visual Studio Build Tools 2022 terminée avec succès."
        
        if ($process.ExitCode -eq 3010) {
            Log-Message -Level "WARNING" -Message "Un redémarrage est nécessaire pour finaliser l'installation."
            Log-Message -Level "WARNING" -Message "Veuillez redémarrer votre ordinateur avant d'utiliser les outils de compilation."
        }
        
        # Vérifier que l'installation a réussi
        if (Check-BuildTools) {
            Log-Message -Level "INFO" -Message "Visual Studio Build Tools avec les outils C++ est maintenant correctement installé."
            Log-Message -Level "INFO" -Message "Vous pouvez maintenant exécuter le script fix_all_dependencies.ps1 pour installer les dépendances Python."
        } else {
            Log-Message -Level "WARNING" -Message "L'installation semble avoir réussi, mais Visual Studio Build Tools n'a pas été détecté."
            Log-Message -Level "WARNING" -Message "Veuillez redémarrer votre ordinateur et réexécuter ce script si nécessaire."
        }
        
        exit 0
    } else {
        Log-Message -Level "ERROR" -Message "Échec de l'installation de Visual Studio Build Tools 2022 (code de sortie: $($process.ExitCode))."
        Log-Message -Level "ERROR" -Message "Veuillez consulter les journaux d'installation pour plus de détails."
        exit 1
    }
} finally {
    # Nettoyer le répertoire temporaire
    if (Test-Path -Path $tempDir) {
        Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}