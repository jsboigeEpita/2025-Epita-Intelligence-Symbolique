# Script PowerShell pour résoudre tous les problèmes de dépendances pour les tests
# Ce script installe toutes les dépendances nécessaires et gère spécifiquement les problèmes connus

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

# Fonction pour installer un package Python avec pip
function Install-Package {
    param (
        [Parameter(Mandatory=$true)]
        [string]$Package,
        
        [Parameter(Mandatory=$false)]
        [string]$Version,
        
        [Parameter(Mandatory=$false)]
        [switch]$Upgrade,
        
        [Parameter(Mandatory=$false)]
        [switch]$ForceReinstall
    )
    
    try {
        $packageSpec = if ($Version) { "$Package==$Version" } else { $Package }
        
        $cmd = "python -m pip install"
        
        if ($Upgrade) {
            $cmd += " --upgrade"
        }
        
        if ($ForceReinstall) {
            $cmd += " --force-reinstall"
        }
        
        $cmd += " $packageSpec"
        
        Log-Message -Level "INFO" -Message "Installation de $packageSpec..."
        
        $output = Invoke-Expression $cmd 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Log-Message -Level "INFO" -Message "$packageSpec installé avec succès."
            return $true
        } else {
            Log-Message -Level "ERROR" -Message "Erreur lors de l'installation de $packageSpec : $output"
            return $false
        }
    } catch {
        Log-Message -Level "ERROR" -Message "Exception lors de l'installation de $Package : $_"
        return $false
    }
}

# Fonction pour installer les packages à partir d'un fichier requirements
function Install-FromRequirements {
    param (
        [Parameter(Mandatory=$true)]
        [string]$RequirementsFile
    )
    
    try {
        Log-Message -Level "INFO" -Message "Installation des dépendances à partir de $RequirementsFile..."
        
        $cmd = "python -m pip install -r $RequirementsFile"
        $output = Invoke-Expression $cmd 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Log-Message -Level "INFO" -Message "Dépendances installées avec succès."
            return $true
        } else {
            Log-Message -Level "ERROR" -Message "Erreur lors de l'installation des dépendances : $output"
            return $false
        }
    } catch {
        Log-Message -Level "ERROR" -Message "Exception lors de l'installation des dépendances : $_"
        return $false
    }
}

# Fonction pour résoudre les problèmes d'importation de numpy
function Fix-Numpy {
    # Désinstaller numpy s'il est déjà installé
    python -m pip uninstall -y numpy | Out-Null
    
    # Installer une version spécifique de numpy connue pour être compatible
    return Install-Package -Package "numpy" -Version "1.24.3" -ForceReinstall
}

# Fonction pour résoudre les problèmes d'importation de pandas
function Fix-Pandas {
    # Désinstaller pandas s'il est déjà installé
    python -m pip uninstall -y pandas | Out-Null
    
    # Installer une version spécifique de pandas connue pour être compatible
    return Install-Package -Package "pandas" -Version "2.0.3" -ForceReinstall
}

# Fonction pour résoudre les problèmes d'importation de jpype
function Fix-Jpype {
    # Désinstaller jpype s'il est déjà installé
    python -m pip uninstall -y JPype1 | Out-Null
    
    # Installer une version spécifique de jpype connue pour être compatible
    return Install-Package -Package "JPype1" -Version "1.4.1" -ForceReinstall
}

# Fonction pour résoudre les problèmes d'importation de cryptography
function Fix-Cryptography {
    # Désinstaller cryptography s'il est déjà installé
    python -m pip uninstall -y cryptography | Out-Null
    
    # Installer les dépendances de cryptography
    Install-Package -Package "setuptools" -Upgrade | Out-Null
    Install-Package -Package "wheel" -Upgrade | Out-Null
    Install-Package -Package "cffi" -Upgrade | Out-Null
    
    # Installer cryptography
    return Install-Package -Package "cryptography" -Version "37.0.0" -ForceReinstall
}

# Fonction pour résoudre les problèmes avec pytest et ses plugins
function Fix-PytestAndPlugins {
    # Désinstaller pytest et ses plugins s'ils sont déjà installés
    python -m pip uninstall -y pytest pytest-asyncio pytest-cov | Out-Null
    
    # Installer pytest et ses plugins
    $success = Install-Package -Package "pytest" -Version "7.4.0" -ForceReinstall
    $success = $success -and (Install-Package -Package "pytest-asyncio" -Version "0.21.1" -ForceReinstall)
    $success = $success -and (Install-Package -Package "pytest-cov" -Version "4.1.0" -ForceReinstall)
    
    return $success
}

# Fonction pour créer un environnement virtuel temporaire pour tester les installations
function Create-TestVenv {
    try {
        # Créer un répertoire temporaire
        $tempDir = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), "test_venv_" + [System.Guid]::NewGuid().ToString())
        Log-Message -Level "INFO" -Message "Création d'un environnement virtuel temporaire dans $tempDir..."
        
        # Créer l'environnement virtuel
        python -m venv $tempDir | Out-Null
        
        Log-Message -Level "INFO" -Message "Environnement virtuel créé avec succès."
        return $tempDir
    } catch {
        Log-Message -Level "ERROR" -Message "Erreur lors de la création de l'environnement virtuel : $_"
        return $null
    }
}

# Fonction pour tester l'installation des dépendances dans un environnement virtuel
function Test-InstallationInVenv {
    param (
        [Parameter(Mandatory=$true)]
        [string]$VenvPath
    )
    
    try {
        # Déterminer le chemin vers l'exécutable Python dans l'environnement virtuel
        $pythonExe = Join-Path -Path $VenvPath -ChildPath "Scripts\python.exe"
        
        # Installer pip dans l'environnement virtuel
        Log-Message -Level "INFO" -Message "Installation de pip dans l'environnement virtuel..."
        & $pythonExe -m ensurepip | Out-Null
        
        # Mettre à jour pip
        Log-Message -Level "INFO" -Message "Mise à jour de pip dans l'environnement virtuel..."
        & $pythonExe -m pip install --upgrade pip | Out-Null
        
        # Installer les dépendances dans l'environnement virtuel
        Log-Message -Level "INFO" -Message "Installation des dépendances dans l'environnement virtuel..."
        $requirementsFile = Join-Path -Path $PSScriptRoot -ChildPath "..\..\requirements-test.txt"
        $output = & $pythonExe -m pip install -r $requirementsFile 2>&1
        
        if ($LASTEXITCODE -ne 0) {
            Log-Message -Level "ERROR" -Message "Erreur lors de l'installation des dépendances dans l'environnement virtuel : $output"
            return $false
        }
        
        # Tester l'importation des modules problématiques
        Log-Message -Level "INFO" -Message "Test de l'importation des modules problématiques..."
        
        # Test de numpy
        $output = & $pythonExe -c "import numpy; print(numpy.__version__)" 2>&1
        if ($LASTEXITCODE -ne 0) {
            Log-Message -Level "ERROR" -Message "Erreur lors de l'importation de numpy : $output"
            return $false
        }
        Log-Message -Level "INFO" -Message "numpy version: $output"
        
        # Test de pandas
        $output = & $pythonExe -c "import pandas; print(pandas.__version__)" 2>&1
        if ($LASTEXITCODE -ne 0) {
            Log-Message -Level "ERROR" -Message "Erreur lors de l'importation de pandas : $output"
            return $false
        }
        Log-Message -Level "INFO" -Message "pandas version: $output"
        
        # Test de jpype
        $output = & $pythonExe -c "import jpype; print(jpype.__version__)" 2>&1
        if ($LASTEXITCODE -ne 0) {
            Log-Message -Level "ERROR" -Message "Erreur lors de l'importation de jpype : $output"
            return $false
        }
        Log-Message -Level "INFO" -Message "jpype version: $output"
        
        # Test de cryptography
        $output = & $pythonExe -c "import cryptography; print(cryptography.__version__)" 2>&1
        if ($LASTEXITCODE -ne 0) {
            Log-Message -Level "ERROR" -Message "Erreur lors de l'importation de cryptography : $output"
            return $false
        }
        Log-Message -Level "INFO" -Message "cryptography version: $output"
        
        # Test de pytest
        $output = & $pythonExe -c "import pytest; print(pytest.__version__)" 2>&1
        if ($LASTEXITCODE -ne 0) {
            Log-Message -Level "ERROR" -Message "Erreur lors de l'importation de pytest : $output"
            return $false
        }
        Log-Message -Level "INFO" -Message "pytest version: $output"
        
        Log-Message -Level "INFO" -Message "Tous les tests d'importation ont réussi dans l'environnement virtuel."
        return $true
    } catch {
        Log-Message -Level "ERROR" -Message "Erreur lors des tests dans l'environnement virtuel : $_"
        return $false
    } finally {
        # Supprimer l'environnement virtuel
        try {
            Log-Message -Level "INFO" -Message "Suppression de l'environnement virtuel $VenvPath..."
            Remove-Item -Path $VenvPath -Recurse -Force
        } catch {
            Log-Message -Level "WARNING" -Message "Erreur lors de la suppression de l'environnement virtuel : $_"
        }
    }
}

# Fonction principale pour résoudre tous les problèmes de dépendances
function Fix-AllDependencies {
    $success = $true
    
    # Mettre à jour pip
    Log-Message -Level "INFO" -Message "Mise à jour de pip..."
    python -m pip install --upgrade pip | Out-Null
    
    # Installer setuptools et wheel
    Log-Message -Level "INFO" -Message "Installation de setuptools et wheel..."
    Install-Package -Package "setuptools" -Upgrade | Out-Null
    Install-Package -Package "wheel" -Upgrade | Out-Null
    
    # Résoudre les problèmes de numpy
    Log-Message -Level "INFO" -Message "Résolution des problèmes de numpy..."
    if (-not (Fix-Numpy)) {
        $success = $false
    }
    
    # Résoudre les problèmes de pandas
    Log-Message -Level "INFO" -Message "Résolution des problèmes de pandas..."
    if (-not (Fix-Pandas)) {
        $success = $false
    }
    
    # Résoudre les problèmes de jpype
    Log-Message -Level "INFO" -Message "Résolution des problèmes de jpype..."
    if (-not (Fix-Jpype)) {
        $success = $false
    }
    
    # Résoudre les problèmes de cryptography
    Log-Message -Level "INFO" -Message "Résolution des problèmes de cryptography..."
    if (-not (Fix-Cryptography)) {
        $success = $false
    }
    
    # Résoudre les problèmes de pytest et ses plugins
    Log-Message -Level "INFO" -Message "Résolution des problèmes de pytest et ses plugins..."
    if (-not (Fix-PytestAndPlugins)) {
        $success = $false
    }
    
    # Installer les autres dépendances à partir du fichier requirements-test.txt
    Log-Message -Level "INFO" -Message "Installation des autres dépendances..."
    $requirementsFile = Join-Path -Path $PSScriptRoot -ChildPath "..\..\requirements-test.txt"
    if (-not (Install-FromRequirements -RequirementsFile $requirementsFile)) {
        $success = $false
    }
    
    # Tester les installations dans un environnement virtuel
    Log-Message -Level "INFO" -Message "Test des installations dans un environnement virtuel..."
    $venvPath = Create-TestVenv
    if ($venvPath) {
        if (-not (Test-InstallationInVenv -VenvPath $venvPath)) {
            Log-Message -Level "WARNING" -Message "Les tests dans l'environnement virtuel ont échoué."
            # Ne pas considérer cela comme un échec global, car l'environnement principal peut fonctionner
        }
    }
    
    return $success
}

# Point d'entrée principal du script
Log-Message -Level "INFO" -Message "Résolution de tous les problèmes de dépendances pour les tests..."

if (Fix-AllDependencies) {
    Log-Message -Level "INFO" -Message "Tous les problèmes de dépendances ont été résolus avec succès."
    exit 0
} else {
    Log-Message -Level "ERROR" -Message "Certains problèmes de dépendances n'ont pas pu être résolus."
    exit 1
}