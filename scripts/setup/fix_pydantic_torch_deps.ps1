# Script PowerShell pour résoudre les problèmes avec pydantic_core et torch
# Ce script installe les versions précompilées de ces bibliothèques pour éviter les problèmes de compilation

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
        [switch]$ForceReinstall,
        
        [Parameter(Mandatory=$false)]
        [switch]$OnlyBinary
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
        
        if ($OnlyBinary) {
            $cmd += " --only-binary=:all:"
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

# Fonction pour résoudre les problèmes avec pydantic_core
function Fix-PydanticCore {
    # Désinstaller pydantic et pydantic_core s'ils sont déjà installés
    Log-Message -Level "INFO" -Message "Désinstallation de pydantic et pydantic_core..."
    python -m pip uninstall -y pydantic pydantic_core | Out-Null
    
    # Installer les dépendances de pydantic_core
    Log-Message -Level "INFO" -Message "Installation des dépendances de pydantic_core..."
    Install-Package -Package "setuptools" -Upgrade | Out-Null
    Install-Package -Package "wheel" -Upgrade | Out-Null
    
    # Installer pydantic_core avec --no-binary pour forcer la compilation
    Log-Message -Level "INFO" -Message "Installation de pydantic_core..."
    $success = Install-Package -Package "pydantic_core" -Version "2.10.1" -ForceReinstall
    
    # Si l'installation a échoué, essayer avec une version précompilée
    if (-not $success) {
        Log-Message -Level "WARNING" -Message "L'installation de pydantic_core a échoué. Tentative avec une version précompilée..."
        $success = Install-Package -Package "pydantic_core" -Version "2.10.1" -ForceReinstall -OnlyBinary
    }
    
    # Installer pydantic
    if ($success) {
        Log-Message -Level "INFO" -Message "Installation de pydantic..."
        $success = Install-Package -Package "pydantic" -Version "2.4.2" -ForceReinstall
    }
    
    return $success
}

# Fonction pour résoudre les problèmes avec torch
function Fix-Torch {
    # Désinstaller torch s'il est déjà installé
    Log-Message -Level "INFO" -Message "Désinstallation de torch..."
    python -m pip uninstall -y torch | Out-Null
    
    # Installer torch à partir d'une version précompilée
    Log-Message -Level "INFO" -Message "Installation de torch à partir d'une version précompilée..."
    $success = Install-Package -Package "torch" -Version "2.0.1" -ForceReinstall -OnlyBinary
    
    return $success
}

# Point d'entrée principal du script
Log-Message -Level "INFO" -Message "Résolution des problèmes avec pydantic_core et torch..."

# Mettre à jour pip
Log-Message -Level "INFO" -Message "Mise à jour de pip..."
python -m pip install --upgrade pip | Out-Null

# Résoudre les problèmes avec pydantic_core
Log-Message -Level "INFO" -Message "Résolution des problèmes avec pydantic_core..."
$pydanticSuccess = Fix-PydanticCore
if (-not $pydanticSuccess) {
    Log-Message -Level "ERROR" -Message "Échec de la résolution des problèmes avec pydantic_core."
}

# Résoudre les problèmes avec torch
Log-Message -Level "INFO" -Message "Résolution des problèmes avec torch..."
$torchSuccess = Fix-Torch
if (-not $torchSuccess) {
    Log-Message -Level "ERROR" -Message "Échec de la résolution des problèmes avec torch."
}

# Tester l'importation de pydantic_core et torch
if ($pydanticSuccess) {
    Test-Import -Module "pydantic_core"
}

if ($torchSuccess) {
    Test-Import -Module "torch"
}

if ($pydanticSuccess -and $torchSuccess) {
    Log-Message -Level "INFO" -Message "Tous les problèmes ont été résolus avec succès."
    exit 0
} else {
    Log-Message -Level "ERROR" -Message "Certains problèmes n'ont pas pu être résolus."
    exit 1
}