# Script PowerShell pour installer des wheels précompilés pour numpy et jpype
# Ce script évite les problèmes de compilation en utilisant des packages binaires précompilés

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

# Fonction pour obtenir les informations sur la version de Python
function Get-PythonInfo {
    try {
        $pythonVersion = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
        $pythonArch = python -c "import platform; print(platform.architecture()[0])"
        $pythonImpl = python -c "import platform; print(platform.python_implementation())"
        
        return @{
            Version = $pythonVersion.Trim()
            Architecture = $pythonArch.Trim()
            Implementation = $pythonImpl.Trim()
        }
    } catch {
        Log-Message -Level "ERROR" -Message "Erreur lors de la récupération des informations Python : $_"
        return $null
    }
}

# Fonction pour installer un package Python avec pip à partir d'un wheel précompilé
function Install-Wheel {
    param (
        [Parameter(Mandatory=$true)]
        [string]$Package,
        
        [Parameter(Mandatory=$false)]
        [string]$Version,
        
        [Parameter(Mandatory=$false)]
        [switch]$ForceReinstall,
        
        [Parameter(Mandatory=$false)]
        [switch]$TrySource
    )
    
    try {
        $packageSpec = if ($Version) { "$Package==$Version" } else { $Package }
        
        # Obtenir les informations Python
        $pythonInfo = Get-PythonInfo
        if (-not $pythonInfo) {
            return $false
        }
        
        Log-Message -Level "INFO" -Message "Python $($pythonInfo.Version) ($($pythonInfo.Architecture)) détecté"
        
        # Essayer d'abord avec --only-binary
        $cmd = "python -m pip install --only-binary=:all: --no-cache-dir"
        
        if ($ForceReinstall) {
            $cmd += " --force-reinstall"
        }
        
        $cmd += " $packageSpec"
        
        Log-Message -Level "INFO" -Message "Installation de $packageSpec à partir d'un wheel précompilé..."
        Log-Message -Level "INFO" -Message "Exécution de la commande: $cmd"
        
        $output = Invoke-Expression $cmd 2>&1
        
        # Afficher la sortie complète pour le débogage
        $output | ForEach-Object { Log-Message -Level "DEBUG" -Message $_ }
        
        if ($LASTEXITCODE -eq 0) {
            Log-Message -Level "INFO" -Message "$packageSpec installé avec succès à partir d'un wheel précompilé."
            return $true
        } else {
            Log-Message -Level "WARNING" -Message "Échec de l'installation de $packageSpec à partir d'un wheel précompilé."
            
            # Si TrySource est spécifié et que l'installation à partir d'un wheel a échoué, essayer à partir des sources
            if ($TrySource) {
                Log-Message -Level "INFO" -Message "Tentative d'installation de $packageSpec à partir des sources..."
                
                $cmd = "python -m pip install --no-cache-dir"
                
                if ($ForceReinstall) {
                    $cmd += " --force-reinstall"
                }
                
                $cmd += " $packageSpec"
                
                Log-Message -Level "INFO" -Message "Exécution de la commande: $cmd"
                $output = Invoke-Expression $cmd 2>&1
                
                # Afficher la sortie complète pour le débogage
                $output | ForEach-Object { Log-Message -Level "DEBUG" -Message $_ }
                
                if ($LASTEXITCODE -eq 0) {
                    Log-Message -Level "INFO" -Message "$packageSpec installé avec succès à partir des sources."
                    return $true
                } else {
                    Log-Message -Level "ERROR" -Message "Échec de l'installation de $packageSpec à partir des sources (code: $LASTEXITCODE)"
                    return $false
                }
            } else {
                return $false
            }
        }
    } catch {
        Log-Message -Level "ERROR" -Message "Exception lors de l'installation de $Package : $_"
        return $false
    }
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

# Fonction pour installer un wheel directement à partir d'une URL
function Install-WheelFromUrl {
    param (
        [Parameter(Mandatory=$true)]
        [string]$Url,
        
        [Parameter(Mandatory=$true)]
        [string]$PackageName
    )
    
    try {
        # Créer un répertoire temporaire pour télécharger le wheel
        $tempDir = [System.IO.Path]::GetTempPath() + [System.Guid]::NewGuid().ToString()
        New-Item -ItemType Directory -Path $tempDir | Out-Null
        
        # Nom du fichier wheel
        $wheelFile = Join-Path -Path $tempDir -ChildPath "$PackageName.whl"
        
        # Télécharger le wheel
        Log-Message -Level "INFO" -Message "Téléchargement du wheel précompilé pour $PackageName depuis $Url..."
        Invoke-WebRequest -Uri $Url -OutFile $wheelFile
        
        # Installer le wheel
        Log-Message -Level "INFO" -Message "Installation du wheel précompilé pour $PackageName..."
        $cmd = "python -m pip install --force-reinstall $wheelFile"
        $output = Invoke-Expression $cmd 2>&1
        
        # Afficher la sortie complète pour le débogage
        $output | ForEach-Object { Log-Message -Level "DEBUG" -Message $_ }
        
        if ($LASTEXITCODE -eq 0) {
            Log-Message -Level "INFO" -Message "$PackageName installé avec succès à partir du wheel précompilé."
            return $true
        } else {
            Log-Message -Level "ERROR" -Message "Erreur lors de l'installation de $PackageName à partir du wheel précompilé (code: $LASTEXITCODE)"
            return $false
        }
    } catch {
        Log-Message -Level "ERROR" -Message "Exception lors de l'installation de $PackageName : $_"
        return $false
    } finally {
        # Nettoyer le répertoire temporaire
        if (Test-Path -Path $tempDir) {
            Remove-Item -Path $tempDir -Recurse -Force
        }
    }
}

# Fonction pour déterminer l'URL du wheel numpy approprié pour la version de Python
function Get-NumpyWheelUrl {
    $pythonInfo = Get-PythonInfo
    if (-not $pythonInfo) {
        return $null
    }
    
    $pythonVersion = $pythonInfo.Version
    $pythonArch = $pythonInfo.Architecture
    
    # Déterminer la version de numpy compatible avec Python 3.12
    if ($pythonVersion.StartsWith("3.12")) {
        # Pour Python 3.12, utiliser numpy 2.0.0 ou plus récent
        return "https://files.pythonhosted.org/packages/a4/9b/027bec53c585cd739d8475bcf2437ba0384c1c07c39a6438fc4d0c9e314a/numpy-2.0.0-cp312-cp312-win_amd64.whl"
    } elseif ($pythonVersion.StartsWith("3.11")) {
        # Pour Python 3.11
        return "https://files.pythonhosted.org/packages/3d/17/2cc40e1ed5e4a31437a33a8ca8ea8538db4c0117b7eaf9cb2bb8cc065250/numpy-1.24.3-cp311-cp311-win_amd64.whl"
    } elseif ($pythonVersion.StartsWith("3.10")) {
        # Pour Python 3.10
        return "https://files.pythonhosted.org/packages/0b/d1/4c3399df56e1c9f8b86241f8d0f2fdc7e9c9982a9dff1c3a1a695c9c5b4d/numpy-1.24.3-cp310-cp310-win_amd64.whl"
    } elseif ($pythonVersion.StartsWith("3.9")) {
        # Pour Python 3.9
        return "https://files.pythonhosted.org/packages/a1/5a/9a2b7c0b3d8ac5c59f3e8f3a4a8c5c1c5b1c8f0f9a5b7f0b0a3a7925a5f/numpy-1.24.3-cp39-cp39-win_amd64.whl"
    } elseif ($pythonVersion.StartsWith("3.8")) {
        # Pour Python 3.8
        return "https://files.pythonhosted.org/packages/a8/84/fc03a43f5f989b922be3fcb3b7d5d609c1d0bdfc6a6bc9cdac76f99c00a9/numpy-1.24.3-cp38-cp38-win_amd64.whl"
    } else {
        Log-Message -Level "WARNING" -Message "Version de Python non supportée pour numpy précompilé: $pythonVersion"
        return $null
    }
}

# Fonction pour déterminer l'URL du wheel JPype1 approprié pour la version de Python
function Get-JpypeWheelUrl {
    $pythonInfo = Get-PythonInfo
    if (-not $pythonInfo) {
        return $null
    }
    
    $pythonVersion = $pythonInfo.Version
    $pythonArch = $pythonInfo.Architecture
    
    # Déterminer la version de JPype1 compatible avec Python 3.12
    if ($pythonVersion.StartsWith("3.12")) {
        # Pour Python 3.12, utiliser JPype1 1.4.1 ou plus récent
        return "https://files.pythonhosted.org/packages/a8/5d/6c8a3c3c0a3b4f4d0e4e2e3a5a1c9d9c88a527a7d3e09b2e7bd6f901c0d0/JPype1-1.4.1-cp312-cp312-win_amd64.whl"
    } elseif ($pythonVersion.StartsWith("3.11")) {
        # Pour Python 3.11
        return "https://files.pythonhosted.org/packages/9e/d8/c7c7a6b8b5b679f9d4a7d2d3b2e91e0c7bc6dc3e8d2cdb3a6d8f2c3a2e3/JPype1-1.4.1-cp311-cp311-win_amd64.whl"
    } elseif ($pythonVersion.StartsWith("3.10")) {
        # Pour Python 3.10
        return "https://files.pythonhosted.org/packages/9e/d8/c7c7a6b8b5b679f9d4a7d2d3b2e91e0c7bc6dc3e8d2cdb3a6d8f2c3a2e3/JPype1-1.4.1-cp310-cp310-win_amd64.whl"
    } elseif ($pythonVersion.StartsWith("3.9")) {
        # Pour Python 3.9
        return "https://files.pythonhosted.org/packages/9e/d8/c7c7a6b8b5b679f9d4a7d2d3b2e91e0c7bc6dc3e8d2cdb3a6d8f2c3a2e3/JPype1-1.4.1-cp39-cp39-win_amd64.whl"
    } elseif ($pythonVersion.StartsWith("3.8")) {
        # Pour Python 3.8
        return "https://files.pythonhosted.org/packages/9e/d8/c7c7a6b8b5b679f9d4a7d2d3b2e91e0c7bc6dc3e8d2cdb3a6d8f2c3a2e3/JPype1-1.4.1-cp38-cp38-win_amd64.whl"
    } else {
        Log-Message -Level "WARNING" -Message "Version de Python non supportée pour JPype1 précompilé: $pythonVersion"
        return $null
    }
}

# Point d'entrée principal du script
Log-Message -Level "INFO" -Message "Installation des wheels précompilés pour numpy et jpype..."

# Mettre à jour pip, setuptools et wheel
Log-Message -Level "INFO" -Message "Mise à jour de pip, setuptools et wheel..."
python -m pip install --upgrade pip setuptools wheel | Out-Null

# Vérifier si les outils de compilation C++ sont disponibles
function Check-BuildTools {
    $vsWhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
    
    if (-not (Test-Path -Path $vsWhere)) {
        Log-Message -Level "WARNING" -Message "Visual Studio ne semble pas être installé (vswhere.exe non trouvé)."
        return $false
    }
    
    # Rechercher d'abord Visual Studio Community/Professional/Enterprise avec les outils C++
    $vsInstallPath = & $vsWhere -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -latest -property installationPath
    
    if ($vsInstallPath) {
        Log-Message -Level "INFO" -Message "Visual Studio avec outils C++ trouvé à: $vsInstallPath"
        return $true
    }
    
    # Si Visual Studio n'est pas trouvé, rechercher les Build Tools autonomes
    $buildTools = & $vsWhere -products Microsoft.VisualStudio.Product.BuildTools -requires Microsoft.VisualCpp.Tools.Host.x86 -latest -property installationPath
    
    if (-not $buildTools) {
        Log-Message -Level "WARNING" -Message "Ni Visual Studio ni Visual Studio Build Tools avec les outils C++ ne semblent être installés."
        return $false
    }
    
    Log-Message -Level "INFO" -Message "Visual Studio Build Tools trouvé à: $buildTools"
    return $true
}

# Vérifier si les outils de compilation sont disponibles
$buildToolsAvailable = Check-BuildTools
if ($buildToolsAvailable) {
    Log-Message -Level "INFO" -Message "Outils de compilation C++ détectés, l'installation à partir des sources est possible si nécessaire."
} else {
    Log-Message -Level "WARNING" -Message "Outils de compilation C++ non détectés, seuls les wheels précompilés seront utilisés."
}

# Installer numpy à partir d'un wheel précompilé spécifique à la version de Python
$numpyWheelUrl = Get-NumpyWheelUrl
if ($numpyWheelUrl) {
    $numpySuccess = Install-WheelFromUrl -Url $numpyWheelUrl -PackageName "numpy"
    if (-not $numpySuccess) {
        # Si l'installation à partir de l'URL échoue, essayer avec pip
        Log-Message -Level "WARNING" -Message "L'installation de numpy à partir du wheel précompilé a échoué, tentative avec pip..."
        $numpySuccess = Install-Wheel -Package "numpy" -Version "2.0.0" -ForceReinstall -TrySource:$buildToolsAvailable
    }
} else {
    # Si aucune URL n'est disponible, essayer avec pip
    Log-Message -Level "WARNING" -Message "Aucun wheel précompilé spécifique trouvé pour numpy, tentative avec pip..."
    $numpySuccess = Install-Wheel -Package "numpy" -Version "2.0.0" -ForceReinstall -TrySource:$buildToolsAvailable
}

if (-not $numpySuccess) {
    Log-Message -Level "ERROR" -Message "Échec de l'installation de numpy."
    exit 1
}

# Tester l'importation de numpy
if (-not (Test-Import -Module "numpy")) {
    Log-Message -Level "ERROR" -Message "Échec du test d'importation de numpy."
    exit 1
}

# Installer jpype à partir d'un wheel précompilé spécifique à la version de Python
$jpypeWheelUrl = Get-JpypeWheelUrl
if ($jpypeWheelUrl) {
    $jpypeSuccess = Install-WheelFromUrl -Url $jpypeWheelUrl -PackageName "JPype1"
    if (-not $jpypeSuccess) {
        # Si l'installation à partir de l'URL échoue, essayer avec pip
        Log-Message -Level "WARNING" -Message "L'installation de JPype1 à partir du wheel précompilé a échoué, tentative avec pip..."
        $jpypeSuccess = Install-Wheel -Package "JPype1" -Version "1.4.1" -ForceReinstall -TrySource:$buildToolsAvailable
    }
} else {
    # Si aucune URL n'est disponible, essayer avec pip
    Log-Message -Level "WARNING" -Message "Aucun wheel précompilé spécifique trouvé pour JPype1, tentative avec pip..."
    $jpypeSuccess = Install-Wheel -Package "JPype1" -Version "1.4.1" -ForceReinstall -TrySource:$buildToolsAvailable
}

if (-not $jpypeSuccess) {
    Log-Message -Level "ERROR" -Message "Échec de l'installation de JPype1."
    exit 1
}

# Tester l'importation de jpype
if (-not (Test-Import -Module "jpype")) {
    Log-Message -Level "ERROR" -Message "Échec du test d'importation de jpype."
    exit 1
}

Log-Message -Level "INFO" -Message "Installation des wheels précompilés terminée avec succès."
exit 0