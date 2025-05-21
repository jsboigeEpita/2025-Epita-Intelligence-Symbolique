# Script PowerShell pour vérifier que toutes les dépendances sont correctement installées et fonctionnelles
# Ce script teste toutes les dépendances nécessaires pour le projet

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

# Fonction pour tester une dépendance Python
function Test-Dependency {
    param (
        [Parameter(Mandatory=$true)]
        [string]$Name,
        
        [Parameter(Mandatory=$false)]
        [string]$ImportName,
        
        [Parameter(Mandatory=$false)]
        [string]$MinVersion
    )
    
    if (-not $ImportName) {
        $ImportName = $Name
    }
    
    try {
        Log-Message -Level "INFO" -Message "Vérification de $Name..."
        
        # Créer un script Python temporaire pour tester l'importation
        $tempScript = [System.IO.Path]::GetTempFileName() + ".py"
        
        $scriptContent = @"
try:
    import $ImportName
    print(f"Version: {getattr($ImportName, '__version__', 'unknown')}")
    print("OK")
except ImportError as e:
    print(f"ImportError: {e}")
    print("FAIL")
except Exception as e:
    print(f"Error: {e}")
    print("FAIL")
"@
        
        Set-Content -Path $tempScript -Value $scriptContent
        
        # Exécuter le script Python
        $output = python $tempScript 2>&1
        $lastLine = ($output | Select-Object -Last 1).Trim()
        
        # Supprimer le script temporaire
        Remove-Item -Path $tempScript -Force
        
        if ($lastLine -eq "OK") {
            # Extraire la version
            $versionLine = ($output | Select-Object -First 1).Trim()
            $version = $versionLine -replace "Version: ", ""
            
            Log-Message -Level "INFO" -Message "$Name version: $version"
            
            # Vérifier la version minimale si spécifiée
            if ($MinVersion -and $version -ne "unknown") {
                if ((Compare-Version -Version1 $version -Version2 $MinVersion) -lt 0) {
                    Log-Message -Level "WARNING" -Message "La version de $Name ($version) est inférieure à la version minimale requise ($MinVersion)."
                    return $false
                }
            }
            
            Log-Message -Level "INFO" -Message "$Name est correctement installé et fonctionnel."
            return $true
        } else {
            $errorMessage = ($output | Select-Object -SkipLast 1) -join "`n"
            Log-Message -Level "ERROR" -Message "Erreur lors du test de $Name: $errorMessage"
            return $false
        }
    } catch {
        Log-Message -Level "ERROR" -Message "Exception lors du test de $Name: $_"
        return $false
    }
}

# Fonction pour comparer deux versions
function Compare-Version {
    param (
        [Parameter(Mandatory=$true)]
        [string]$Version1,
        
        [Parameter(Mandatory=$true)]
        [string]$Version2
    )
    
    $v1Parts = $Version1.Split('.') | ForEach-Object { [int]$_ }
    $v2Parts = $Version2.Split('.') | ForEach-Object { [int]$_ }
    
    $minLength = [Math]::Min($v1Parts.Length, $v2Parts.Length)
    
    for ($i = 0; $i -lt $minLength; $i++) {
        if ($v1Parts[$i] -lt $v2Parts[$i]) {
            return -1
        } elseif ($v1Parts[$i] -gt $v2Parts[$i]) {
            return 1
        }
    }
    
    if ($v1Parts.Length -lt $v2Parts.Length) {
        return -1
    } elseif ($v1Parts.Length -gt $v2Parts.Length) {
        return 1
    } else {
        return 0
    }
}

# Fonction pour tester numpy
function Test-Numpy {
    $script = @"
try:
    import numpy as np
    print(f"Version: {np.__version__}")
    
    # Tester quelques fonctionnalités de base
    arr = np.array([1, 2, 3, 4, 5])
    mean = np.mean(arr)
    sum_val = np.sum(arr)
    
    print(f"numpy array: {arr}")
    print(f"numpy mean: {mean}")
    print(f"numpy sum: {sum_val}")
    print("OK")
except ImportError as e:
    print(f"ImportError: {e}")
    print("FAIL")
except Exception as e:
    print(f"Error: {e}")
    print("FAIL")
"@
    
    $tempScript = [System.IO.Path]::GetTempFileName() + ".py"
    Set-Content -Path $tempScript -Value $script
    
    $output = python $tempScript 2>&1
    $lastLine = ($output | Select-Object -Last 1).Trim()
    
    Remove-Item -Path $tempScript -Force
    
    if ($lastLine -eq "OK") {
        $output | ForEach-Object {
            if ($_ -match "^numpy") {
                Log-Message -Level "INFO" -Message $_
            }
        }
        return $true
    } else {
        $errorMessage = ($output | Select-Object -SkipLast 1) -join "`n"
        Log-Message -Level "ERROR" -Message "Erreur lors du test de numpy: $errorMessage"
        return $false
    }
}

# Fonction pour tester pandas
function Test-Pandas {
    $script = @"
try:
    import pandas as pd
    print(f"Version: {pd.__version__}")
    
    # Tester quelques fonctionnalités de base
    df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
    mean = df.mean()
    sum_val = df.sum()
    
    print(f"pandas DataFrame:\\n{df}")
    print(f"pandas mean:\\n{mean}")
    print(f"pandas sum:\\n{sum_val}")
    print("OK")
except ImportError as e:
    print(f"ImportError: {e}")
    print("FAIL")
except Exception as e:
    print(f"Error: {e}")
    print("FAIL")
"@
    
    $tempScript = [System.IO.Path]::GetTempFileName() + ".py"
    Set-Content -Path $tempScript -Value $script
    
    $output = python $tempScript 2>&1
    $lastLine = ($output | Select-Object -Last 1).Trim()
    
    Remove-Item -Path $tempScript -Force
    
    if ($lastLine -eq "OK") {
        $output | ForEach-Object {
            if ($_ -match "^pandas") {
                Log-Message -Level "INFO" -Message $_
            }
        }
        return $true
    } else {
        $errorMessage = ($output | Select-Object -SkipLast 1) -join "`n"
        Log-Message -Level "ERROR" -Message "Erreur lors du test de pandas: $errorMessage"
        return $false
    }
}

# Fonction pour tester jpype
function Test-Jpype {
    $script = @"
try:
    import jpype
    print(f"Version: {jpype.__version__}")
    
    # Tester quelques fonctionnalités de base (sans initialiser la JVM)
    print(f"jpype.isJVMStarted(): {jpype.isJVMStarted()}")
    print(f"jpype.getDefaultJVMPath(): {jpype.getDefaultJVMPath()}")
    print("OK")
except ImportError as e:
    print(f"ImportError: {e}")
    print("FAIL")
except Exception as e:
    print(f"Error: {e}")
    print("FAIL")
"@
    
    $tempScript = [System.IO.Path]::GetTempFileName() + ".py"
    Set-Content -Path $tempScript -Value $script
    
    $output = python $tempScript 2>&1
    $lastLine = ($output | Select-Object -Last 1).Trim()
    
    Remove-Item -Path $tempScript -Force
    
    if ($lastLine -eq "OK") {
        $output | ForEach-Object {
            if ($_ -match "^jpype") {
                Log-Message -Level "INFO" -Message $_
            }
        }
        return $true
    } else {
        $errorMessage = ($output | Select-Object -SkipLast 1) -join "`n"
        Log-Message -Level "ERROR" -Message "Erreur lors du test de jpype: $errorMessage"
        return $false
    }
}

# Fonction pour tester cryptography
function Test-Cryptography {
    $script = @"
try:
    import cryptography
    from cryptography.fernet import Fernet
    print(f"Version: {cryptography.__version__}")
    
    # Tester quelques fonctionnalités de base
    key = Fernet.generate_key()
    f = Fernet(key)
    token = f.encrypt(b"test message")
    decrypted = f.decrypt(token)
    
    print(f"cryptography key: {key}")
    print(f"cryptography token: {token}")
    print(f"cryptography decrypted: {decrypted}")
    print("OK")
except ImportError as e:
    print(f"ImportError: {e}")
    print("FAIL")
except Exception as e:
    print(f"Error: {e}")
    print("FAIL")
"@
    
    $tempScript = [System.IO.Path]::GetTempFileName() + ".py"
    Set-Content -Path $tempScript -Value $script
    
    $output = python $tempScript 2>&1
    $lastLine = ($output | Select-Object -Last 1).Trim()
    
    Remove-Item -Path $tempScript -Force
    
    if ($lastLine -eq "OK") {
        $output | ForEach-Object {
            if ($_ -match "^cryptography") {
                Log-Message -Level "INFO" -Message $_
            }
        }
        return $true
    } else {
        $errorMessage = ($output | Select-Object -SkipLast 1) -join "`n"
        Log-Message -Level "ERROR" -Message "Erreur lors du test de cryptography: $errorMessage"
        return $false
    }
}

# Fonction pour tester les importations des modules du projet
function Test-ProjectImports {
    $script = @"
try:
    # Liste des modules du projet à tester
    project_modules = [
        "argumentation_analysis",
        "argumentation_analysis.core",
        "argumentation_analysis.agents",
        "argumentation_analysis.services",
        "argumentation_analysis.ui",
        "argumentation_analysis.utils",
        "argumentation_analysis.orchestration"
    ]
    
    all_ok = True
    results = {}
    
    for module_name in project_modules:
        try:
            print(f"Importation de {module_name}...")
            __import__(module_name)
            print(f"Importation de {module_name} réussie.")
            results[module_name] = True
        except ImportError as e:
            print(f"Erreur d'importation de {module_name}: {e}")
            results[module_name] = False
            all_ok = False
        except Exception as e:
            print(f"Erreur lors de l'importation de {module_name}: {e}")
            results[module_name] = False
            all_ok = False
    
    # Afficher un résumé
    print("\\nRésumé des importations des modules du projet:")
    print("-" * 40)
    
    for name, ok in results.items():
        status = "OK" if ok else "ÉCHEC"
        print(f"{name}: {status}")
    
    print("-" * 40)
    
    if all_ok:
        print("OK")
    else:
        print("FAIL")
except Exception as e:
    print(f"Error: {e}")
    print("FAIL")
"@
    
    $tempScript = [System.IO.Path]::GetTempFileName() + ".py"
    Set-Content -Path $tempScript -Value $script
    
    $output = python $tempScript 2>&1
    $lastLine = ($output | Select-Object -Last 1).Trim()
    
    Remove-Item -Path $tempScript -Force
    
    # Afficher tous les messages
    $output | ForEach-Object {
        if ($_ -ne "OK" -and $_ -ne "FAIL") {
            Log-Message -Level "INFO" -Message $_
        }
    }
    
    if ($lastLine -eq "OK") {
        Log-Message -Level "INFO" -Message "Toutes les importations des modules du projet ont réussi."
        return $true
    } else {
        Log-Message -Level "ERROR" -Message "Certaines importations des modules du projet ont échoué."
        return $false
    }
}

# Fonction principale pour tester toutes les dépendances
function Test-AllDependencies {
    $dependencies = @(
        @{Name="numpy"; MinVersion="1.24.0"; Test=$true},
        @{Name="pandas"; MinVersion="2.0.0"; Test=$true},
        @{Name="matplotlib"; MinVersion="3.5.0"},
        @{Name="jpype1"; ImportName="jpype"; MinVersion="1.4.0"; Test=$true},
        @{Name="cryptography"; MinVersion="37.0.0"; Test=$true},
        @{Name="cffi"; MinVersion="1.15.0"},
        @{Name="psutil"; MinVersion="5.9.0"},
        @{Name="tika"; MinVersion="1.24.0"},
        @{Name="jina"; MinVersion="3.0.0"},
        @{Name="pytest"; MinVersion="7.0.0"},
        @{Name="pytest-asyncio"; ImportName="pytest_asyncio"; MinVersion="0.18.0"},
        @{Name="pytest-cov"; ImportName="pytest_cov"; MinVersion="3.0.0"},
        @{Name="scikit-learn"; ImportName="sklearn"; MinVersion="1.0.0"},
        @{Name="networkx"; MinVersion="2.6.0"},
        @{Name="torch"; MinVersion="2.0.0"},
        @{Name="transformers"; MinVersion="4.20.0"},
        @{Name="jupyter"; MinVersion="1.0.0"},
        @{Name="notebook"; MinVersion="6.4.0"},
        @{Name="jupyter_ui_poll"; MinVersion="0.2.0"},
        @{Name="ipywidgets"; MinVersion="7.7.0"}
    )
    
    $allOk = $true
    $results = @{}
    
    foreach ($dependency in $dependencies) {
        $name = $dependency.Name
        $importName = $dependency.ImportName
        $minVersion = $dependency.MinVersion
        $test = $dependency.Test
        
        if (-not $importName) {
            $importName = $name
        }
        
        if ($test) {
            # Utiliser la fonction de test spécifique
            switch ($name) {
                "numpy" { $results[$name] = Test-Numpy }
                "pandas" { $results[$name] = Test-Pandas }
                "jpype1" { $results[$name] = Test-Jpype }
                "cryptography" { $results[$name] = Test-Cryptography }
                default { $results[$name] = Test-Dependency -Name $name -ImportName $importName -MinVersion $minVersion }
            }
        } else {
            # Utiliser la fonction de test générique
            $results[$name] = Test-Dependency -Name $name -ImportName $importName -MinVersion $minVersion
        }
        
        $allOk = $allOk -and $results[$name]
    }
    
    # Afficher un résumé
    Log-Message -Level "INFO" -Message "`nRésumé des tests de dépendances:"
    Log-Message -Level "INFO" -Message ("-" * 40)
    
    foreach ($name in $results.Keys) {
        $status = if ($results[$name]) { "OK" } else { "ÉCHEC" }
        Log-Message -Level "INFO" -Message "$name : $status"
    }
    
    Log-Message -Level "INFO" -Message ("-" * 40)
    
    return $allOk
}

# Point d'entrée principal du script
Log-Message -Level "INFO" -Message "Vérification des dépendances..."

$dependenciesOk = Test-AllDependencies
$projectImportsOk = Test-ProjectImports

if ($dependenciesOk -and $projectImportsOk) {
    Log-Message -Level "INFO" -Message "Toutes les dépendances sont correctement installées et fonctionnelles."
    Log-Message -Level "INFO" -Message "Vous pouvez exécuter les tests avec la commande: pytest"
    exit 0
} else {
    Log-Message -Level "ERROR" -Message "Certaines dépendances ne sont pas correctement installées ou fonctionnelles."
    Log-Message -Level "ERROR" -Message "Exécutez le script fix_all_dependencies.ps1 pour résoudre les problèmes."
    exit 1
}