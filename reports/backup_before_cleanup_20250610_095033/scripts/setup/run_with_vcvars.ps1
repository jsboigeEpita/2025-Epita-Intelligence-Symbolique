# Script PowerShell pour exécuter fix_all_dependencies.ps1 avec les variables d'environnement de Visual Studio

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

# Fonction pour trouver le chemin vers vcvarsall.bat
function Find-VCVarsAll {
    # Utiliser vswhere pour trouver l'installation de Visual Studio
    $vsWhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
    
    if (-not (Test-Path -Path $vsWhere)) {
        Log-Message -Level "ERROR" -Message "Visual Studio ne semble pas être installé (vswhere.exe non trouvé)."
        return $null
    }
    
    # Rechercher d'abord Visual Studio Community/Professional/Enterprise
    $vsInstallPath = & $vsWhere -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -latest -property installationPath
    
    if ($vsInstallPath) {
        $vcvarsall = Join-Path -Path $vsInstallPath -ChildPath "VC\Auxiliary\Build\vcvarsall.bat"
        if (Test-Path -Path $vcvarsall) {
            Log-Message -Level "INFO" -Message "vcvarsall.bat trouvé dans Visual Studio à: $vcvarsall"
            return $vcvarsall
        }
    }
    
    # Si Visual Studio n'est pas trouvé, rechercher les Build Tools autonomes
    $buildToolsPath = & $vsWhere -products Microsoft.VisualStudio.Product.BuildTools -requires Microsoft.VisualCpp.Tools.Host.x86 -latest -property installationPath
    
    if ($buildToolsPath) {
        $vcvarsall = Join-Path -Path $buildToolsPath -ChildPath "VC\Auxiliary\Build\vcvarsall.bat"
        if (Test-Path -Path $vcvarsall) {
            Log-Message -Level "INFO" -Message "vcvarsall.bat trouvé dans Build Tools à: $vcvarsall"
            return $vcvarsall
        }
    }
    
    Log-Message -Level "ERROR" -Message "Impossible de trouver vcvarsall.bat dans les installations de Visual Studio."
    return $null
}

# Trouver le chemin vers vcvarsall.bat
$vcvarsall = Find-VCVarsAll

# Vérifier que vcvarsall.bat a été trouvé
if (-not $vcvarsall) {
    Log-Message -Level "ERROR" -Message "Le fichier vcvarsall.bat n'a pas été trouvé. Veuillez installer Visual Studio avec les outils de développement C++."
    exit 1
}

Log-Message -Level "INFO" -Message "Configuration de l'environnement avec les outils de compilation Visual Studio..."

# Créer un script batch temporaire qui appelle vcvarsall.bat puis exécute notre script PowerShell
$tempBatchFile = [System.IO.Path]::GetTempFileName() + ".bat"
$scriptPath = Join-Path -Path $PSScriptRoot -ChildPath "fix_all_dependencies.ps1"
$scriptPath = Resolve-Path -Path $scriptPath

$batchContent = @"
@echo off
call "$vcvarsall" x64
powershell -ExecutionPolicy Bypass -File "$scriptPath"
exit %ERRORLEVEL%
"@

Set-Content -Path $tempBatchFile -Value $batchContent

try {
    Log-Message -Level "INFO" -Message "Exécution du script fix_all_dependencies.ps1 avec les variables d'environnement de Visual Studio..."
    
    # Exécuter le script batch temporaire
    $process = Start-Process -FilePath $tempBatchFile -NoNewWindow -PassThru -Wait
    
    if ($process.ExitCode -eq 0) {
        Log-Message -Level "INFO" -Message "Le script fix_all_dependencies.ps1 s'est exécuté avec succès."
        exit 0
    } else {
        Log-Message -Level "ERROR" -Message "Le script fix_all_dependencies.ps1 s'est terminé avec le code d'erreur: $($process.ExitCode)"
        exit $process.ExitCode
    }
} finally {
    # Supprimer le fichier batch temporaire
    if (Test-Path -Path $tempBatchFile) {
        Remove-Item -Path $tempBatchFile -Force
    }
}