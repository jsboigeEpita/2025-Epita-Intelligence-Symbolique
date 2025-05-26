# Script PowerShell pour installer JPype1 avec les variables d'environnement de Visual Studio

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
    $vsWhere = "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
    
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

# Fonction pour tester l'importation d'un module
function Test-Import {
    param (
        [Parameter(Mandatory=$true)]
        [string]$Module
    )
    
    try {
        $cmd = "python -c `"import $Module; print('$Module importé avec succès.')`"";
        $output = Invoke-Expression $cmd 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Log-Message -Level "INFO" -Message "$output"
            return $true
        } else {
            Log-Message -Level "ERROR" -Message "Erreur lors de l'importation de $Module : $output"
            return $false
        }
    } catch {
        Log-Message -Level "ERROR" -Message "Exception lors du test d'importation de $Module : $_"
        return $false
    }
}

# Point d'entrée principal du script
Log-Message -Level "INFO" -Message "Installation de JPype1 avec les variables d'environnement de Visual Studio..."

# Trouver le chemin vers vcvarsall.bat
$vcvarsall = Find-VCVarsAll

# Vérifier que vcvarsall.bat a été trouvé
if (-not $vcvarsall) {
    Log-Message -Level "ERROR" -Message "Le fichier vcvarsall.bat n'a pas été trouvé. Veuillez installer Visual Studio avec les outils de développement C++."
    exit 1
}

Log-Message -Level "INFO" -Message "Configuration de l'environnement avec les outils de compilation Visual Studio..."

# Créer un script batch temporaire qui appelle vcvarsall.bat puis installe JPype1
$tempBatchFile = [System.IO.Path]::GetTempFileName() + ".bat"

$batchContent = @"
@echo off
call "$vcvarsall" x64
echo Configuration de l'environnement terminée, installation de JPype1...
set DISTUTILS_USE_SDK=1
pip install --no-cache-dir JPype1==1.4.1 --use-pep517
exit %ERRORLEVEL%
"@

Set-Content -Path $tempBatchFile -Value $batchContent

try {
    Log-Message -Level "INFO" -Message "Exécution de l'installation de JPype1 avec les variables d'environnement de Visual Studio..."
    
    # Exécuter le script batch temporaire
    $process = Start-Process -FilePath $tempBatchFile -NoNewWindow -PassThru -Wait
    
    if ($process.ExitCode -eq 0) {
        Log-Message -Level "INFO" -Message "JPype1 a été installé avec succès."
        
#        # Tester l'importation de jpype
#        if (-not (Test-Import -Module "jpype")) {
#            Log-Message -Level "ERROR" -Message "Échec du test d'importation de jpype."
#            exit 1
#        }
        
        exit 0
    } else {
        Log-Message -Level "ERROR" -Message "L'installation de JPype1 s'est terminée avec le code d'erreur: $($process.ExitCode)"
        # Tenter de donner plus d'informations sur l'erreur si possible
        # $errorOutput = Get-Content -Path $process.StandardErrorPath -ErrorAction SilentlyContinue
        # if ($errorOutput) {
        #    Log-Message -Level "ERROR" -Message "Détails de l'erreur: $errorOutput"
        # }
        exit $process.ExitCode
    }
} finally {
    # Supprimer le fichier batch temporaire
    if (Test-Path -Path $tempBatchFile) {
        Remove-Item -Path $tempBatchFile -Force
    }
}