# Script PowerShell pour installer JPype1 pour Python 3.12
# Ce script essaie plusieurs méthodes pour installer JPype1 avec Python 3.12

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

# Fonction pour installer JPype1 avec pip
function Install-JPypeWithPip {
    param (
        [Parameter(Mandatory=$false)]
        [string]$Version = "1.4.1",
        
        [Parameter(Mandatory=$false)]
        [switch]$ForceReinstall,
        
        [Parameter(Mandatory=$false)]
        [switch]$NoBinary,
        
        [Parameter(Mandatory=$false)]
        [switch]$Verbose
    )
    
    try {
        $packageSpec = "JPype1==$Version"
        
        $cmd = "python -m pip install"
        
        if ($ForceReinstall) {
            $cmd += " --force-reinstall"
        }
        
        if ($NoBinary) {
            $cmd += " --no-binary=JPype1"
        }
        
        if ($Verbose) {
            $cmd += " -v"
        }
        
        $cmd += " $packageSpec"
        
        Log-Message -Level "INFO" -Message "Installation de $packageSpec avec pip..."
        Log-Message -Level "INFO" -Message "Commande: $cmd"
        
        $output = Invoke-Expression $cmd 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Log-Message -Level "INFO" -Message "$packageSpec installé avec succès."
            return $true
        } else {
            Log-Message -Level "ERROR" -Message "Erreur lors de l'installation de $packageSpec : $LASTEXITCODE"
            $output | ForEach-Object { Log-Message -Level "DEBUG" -Message $_ }
            return $false
        }
    } catch {
        Log-Message -Level "ERROR" -Message "Exception lors de l'installation de JPype1 : $_"
        return $false
    }
}

# Fonction pour installer JPype1 avec vcvarsall.bat
function Install-JPypeWithVCVars {
    param (
        [Parameter(Mandatory=$true)]
        [string]$VCVarsPath,
        
        [Parameter(Mandatory=$false)]
        [string]$Version = "1.4.1",
        
        [Parameter(Mandatory=$false)]
        [switch]$ForceReinstall,
        
        [Parameter(Mandatory=$false)]
        [switch]$NoBinary,
        
        [Parameter(Mandatory=$false)]
        [switch]$Verbose
    )
    
    try {
        $packageSpec = "JPype1==$Version"
        
        # Créer un script batch temporaire
        $tempBatchFile = [System.IO.Path]::GetTempFileName() + ".bat"
        
        $pipCmd = "pip install"
        
        if ($ForceReinstall) {
            $pipCmd += " --force-reinstall"
        }
        
        if ($NoBinary) {
            $pipCmd += " --no-binary=JPype1"
        }
        
        if ($Verbose) {
            $pipCmd += " -v"
        }
        
        $pipCmd += " $packageSpec"
        
        $batchContent = @"
@echo off
call "$VCVarsPath" x64
echo Configuration de l'environnement terminée, installation de JPype1...
set DISTUTILS_USE_SDK=1
set MSSdk=1
$pipCmd
exit %ERRORLEVEL%
"@
        
        Set-Content -Path $tempBatchFile -Value $batchContent
        
        Log-Message -Level "INFO" -Message "Installation de $packageSpec avec vcvarsall.bat..."
        
        # Exécuter le script batch temporaire
        $process = Start-Process -FilePath $tempBatchFile -NoNewWindow -PassThru -Wait
        
        if ($process.ExitCode -eq 0) {
            Log-Message -Level "INFO" -Message "$packageSpec installé avec succès."
            return $true
        } else {
            Log-Message -Level "ERROR" -Message "Erreur lors de l'installation de $packageSpec : $($process.ExitCode)"
            return $false
        }
    } catch {
        Log-Message -Level "ERROR" -Message "Exception lors de l'installation de JPype1 : $_"
        return $false
    } finally {
        # Supprimer le fichier batch temporaire
        if (Test-Path -Path $tempBatchFile) {
            Remove-Item -Path $tempBatchFile -Force
        }
    }
}

# Fonction pour installer JPype1 avec setuptools
function Install-JPypeWithSetuptools {
    param (
        [Parameter(Mandatory=$false)]
        [string]$Version = "1.4.1",
        
        [Parameter(Mandatory=$false)]
        [switch]$Verbose
    )
    
    try {
        # Créer un répertoire temporaire
        $tempDir = [System.IO.Path]::GetTempPath() + [System.Guid]::NewGuid().ToString()
        New-Item -ItemType Directory -Path $tempDir | Out-Null
        
        # Télécharger JPype1
        $url = "https://github.com/jpype-project/jpype/archive/refs/tags/v$Version.zip"
        $zipFile = Join-Path -Path $tempDir -ChildPath "jpype.zip"
        
        Log-Message -Level "INFO" -Message "Téléchargement de JPype1 depuis $url..."
        Invoke-WebRequest -Uri $url -OutFile $zipFile
        
        # Extraire l'archive
        Log-Message -Level "INFO" -Message "Extraction de l'archive..."
        Expand-Archive -Path $zipFile -DestinationPath $tempDir
        
        # Trouver le répertoire extrait
        $extractDir = Get-ChildItem -Path $tempDir -Directory | Where-Object { $_.Name -like "jpype*" } | Select-Object -First 1
        
        if (-not $extractDir) {
            Log-Message -Level "ERROR" -Message "Impossible de trouver le répertoire extrait."
            return $false
        }
        
        # Installer JPype1
        Log-Message -Level "INFO" -Message "Installation de JPype1 avec setuptools..."
        
        $cmd = "python setup.py install"
        
        if ($Verbose) {
            $cmd += " -v"
        }
        
        $output = Invoke-Expression "cd $($extractDir.FullName) && $cmd" 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Log-Message -Level "INFO" -Message "JPype1 installé avec succès."
            return $true
        } else {
            Log-Message -Level "ERROR" -Message "Erreur lors de l'installation de JPype1 : $LASTEXITCODE"
            $output | ForEach-Object { Log-Message -Level "DEBUG" -Message $_ }
            return $false
        }
    } catch {
        Log-Message -Level "ERROR" -Message "Exception lors de l'installation de JPype1 : $_"
        return $false
    } finally {
        # Supprimer le répertoire temporaire
        if (Test-Path -Path $tempDir) {
            Remove-Item -Path $tempDir -Recurse -Force
        }
    }
}

# Fonction pour installer JPype1 avec une version de développement
function Install-JPypeFromGit {
    param (
        [Parameter(Mandatory=$false)]
        [string]$Branch = "master",
        
        [Parameter(Mandatory=$false)]
        [switch]$Verbose
    )
    
    try {
        $cmd = "python -m pip install git+https://github.com/jpype-project/jpype.git@$Branch"
        
        if ($Verbose) {
            $cmd += " -v"
        }
        
        Log-Message -Level "INFO" -Message "Installation de JPype1 depuis GitHub (branche $Branch)..."
        
        $output = Invoke-Expression $cmd 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Log-Message -Level "INFO" -Message "JPype1 installé avec succès depuis GitHub."
            return $true
        } else {
            Log-Message -Level "ERROR" -Message "Erreur lors de l'installation de JPype1 depuis GitHub : $LASTEXITCODE"
            $output | ForEach-Object { Log-Message -Level "DEBUG" -Message $_ }
            return $false
        }
    } catch {
        Log-Message -Level "ERROR" -Message "Exception lors de l'installation de JPype1 depuis GitHub : $_"
        return $false
    }
}

# Fonction pour installer JPype1 avec une version précompilée
function Install-JPypeFromWheel {
    param (
        [Parameter(Mandatory=$false)]
        [string]$Version = "1.4.1",
        
        [Parameter(Mandatory=$false)]
        [switch]$ForceReinstall
    )
    
    try {
        # Obtenir la version de Python
        $pythonVersion = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
        
        # Construire l'URL du wheel
        $wheelUrl = "https://files.pythonhosted.org/packages/a8/5d/6c8a3c3c0a3b4f4d0e4e2e3a5a1c9d9c88a527a7d3e09b2e7bd6f901c0d0/JPype1-$Version-cp$($pythonVersion.Replace('.', ''))-cp$($pythonVersion.Replace('.', ''))-win_amd64.whl"
        
        # Créer un répertoire temporaire
        $tempDir = [System.IO.Path]::GetTempPath() + [System.Guid]::NewGuid().ToString()
        New-Item -ItemType Directory -Path $tempDir | Out-Null
        
        # Télécharger le wheel
        $wheelFile = Join-Path -Path $tempDir -ChildPath "JPype1.whl"
        
        Log-Message -Level "INFO" -Message "Téléchargement du wheel JPype1 depuis $wheelUrl..."
        
        try {
            Invoke-WebRequest -Uri $wheelUrl -OutFile $wheelFile
        } catch {
            Log-Message -Level "ERROR" -Message "Erreur lors du téléchargement du wheel : $_"
            return $false
        }
        
        # Installer le wheel
        $cmd = "python -m pip install"
        
        if ($ForceReinstall) {
            $cmd += " --force-reinstall"
        }
        
        $cmd += " $wheelFile"
        
        Log-Message -Level "INFO" -Message "Installation du wheel JPype1..."
        
        $output = Invoke-Expression $cmd 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Log-Message -Level "INFO" -Message "JPype1 installé avec succès à partir du wheel."
            return $true
        } else {
            Log-Message -Level "ERROR" -Message "Erreur lors de l'installation de JPype1 à partir du wheel : $LASTEXITCODE"
            $output | ForEach-Object { Log-Message -Level "DEBUG" -Message $_ }
            return $false
        }
    } catch {
        Log-Message -Level "ERROR" -Message "Exception lors de l'installation de JPype1 à partir du wheel : $_"
        return $false
    } finally {
        # Supprimer le répertoire temporaire
        if (Test-Path -Path $tempDir) {
            Remove-Item -Path $tempDir -Recurse -Force
        }
    }
}

# Point d'entrée principal du script
Log-Message -Level "INFO" -Message "Installation de JPype1 pour Python 3.12..."

# Obtenir la version de Python
$pythonVersion = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
Log-Message -Level "INFO" -Message "Version de Python détectée : $pythonVersion"

# Vérifier si JPype1 est déjà installé
$jpypeInstalled = Test-Import -Module "jpype"
if ($jpypeInstalled) {
    Log-Message -Level "INFO" -Message "JPype1 est déjà installé et fonctionne correctement."
    exit 0
}

# Désinstaller JPype1 s'il est déjà installé mais ne fonctionne pas
Log-Message -Level "INFO" -Message "Désinstallation de JPype1 existant..."
python -m pip uninstall -y JPype1 | Out-Null

# Mettre à jour pip, setuptools et wheel
Log-Message -Level "INFO" -Message "Mise à jour de pip, setuptools et wheel..."
python -m pip install --upgrade pip setuptools wheel | Out-Null

# Trouver vcvarsall.bat
$vcvarsall = Find-VCVarsAll
$vcvarsAvailable = $null -ne $vcvarsall

# Méthode 1: Installer JPype1 avec pip standard
Log-Message -Level "INFO" -Message "Méthode 1: Installation de JPype1 avec pip standard..."
$success = Install-JPypeWithPip -ForceReinstall
if ($success -and (Test-Import -Module "jpype")) {
    Log-Message -Level "INFO" -Message "JPype1 installé avec succès avec pip standard."
    exit 0
}

# Méthode 2: Installer JPype1 avec pip et --no-binary
Log-Message -Level "INFO" -Message "Méthode 2: Installation de JPype1 avec pip et --no-binary..."
$success = Install-JPypeWithPip -ForceReinstall -NoBinary
if ($success -and (Test-Import -Module "jpype")) {
    Log-Message -Level "INFO" -Message "JPype1 installé avec succès avec pip et --no-binary."
    exit 0
}

# Méthode 3: Installer JPype1 avec vcvarsall.bat
if ($vcvarsAvailable) {
    Log-Message -Level "INFO" -Message "Méthode 3: Installation de JPype1 avec vcvarsall.bat..."
    $success = Install-JPypeWithVCVars -VCVarsPath $vcvarsall -ForceReinstall
    if ($success -and (Test-Import -Module "jpype")) {
        Log-Message -Level "INFO" -Message "JPype1 installé avec succès avec vcvarsall.bat."
        exit 0
    }
}

# Méthode 4: Installer JPype1 avec setuptools
Log-Message -Level "INFO" -Message "Méthode 4: Installation de JPype1 avec setuptools..."
$success = Install-JPypeWithSetuptools -Version "1.4.1"
if ($success -and (Test-Import -Module "jpype")) {
    Log-Message -Level "INFO" -Message "JPype1 installé avec succès avec setuptools."
    exit 0
}

# Méthode 5: Installer JPype1 depuis GitHub
Log-Message -Level "INFO" -Message "Méthode 5: Installation de JPype1 depuis GitHub..."
$success = Install-JPypeFromGit -Branch "master"
if ($success -and (Test-Import -Module "jpype")) {
    Log-Message -Level "INFO" -Message "JPype1 installé avec succès depuis GitHub."
    exit 0
}

# Méthode 6: Installer JPype1 depuis un wheel précompilé
Log-Message -Level "INFO" -Message "Méthode 6: Installation de JPype1 depuis un wheel précompilé..."
$success = Install-JPypeFromWheel -ForceReinstall
if ($success -and (Test-Import -Module "jpype")) {
    Log-Message -Level "INFO" -Message "JPype1 installé avec succès depuis un wheel précompilé."
    exit 0
}

# Si toutes les méthodes ont échoué
Log-Message -Level "ERROR" -Message "Toutes les méthodes d'installation de JPype1 ont échoué."
Log-Message -Level "INFO" -Message "Suggestions:"
Log-Message -Level "INFO" -Message "1. Essayez d'installer une version antérieure de Python (3.11 ou moins)."
Log-Message -Level "INFO" -Message "2. Vérifiez que Visual Studio avec les outils de développement C++ est correctement installé."
Log-Message -Level "INFO" -Message "3. Consultez la documentation de JPype1 pour plus d'informations: https://jpype.readthedocs.io/"

exit 1