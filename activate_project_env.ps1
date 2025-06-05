param (
    [string]$CommandToRun = "" # Commande à exécuter après activation
)

# Assurer que PSScriptRoot est défini, même si le script est appelé d'une manière où $PSScriptRoot n'est pas automatiquement peuplé.
if ($PSScriptRoot) {
    $scriptRoot = $PSScriptRoot
} else {
    $scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
}

$envFile = ".env"

# --- Chargement des Variables d'Environnement ---
$envFilePath = Join-Path $scriptRoot $envFile
if (Test-Path $envFilePath) {
    Write-Host "Chargement des variables d'environnement depuis '$envFile'..."
    Get-Content $envFilePath | ForEach-Object {
        $line = $_.Trim()
        # Ignorer les commentaires et les lignes vides
        if ($line -and $line -notmatch "^\s*#") {
            $parts = $line.Split("=", 2)
            if ($parts.Length -eq 2) {
                $key = $parts[0].Trim()
                $value = $parts[1].Trim()

                # Retirer les guillemets englobants s'ils existent (simples ou doubles)
                if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
                    if ($value.Length -ge 2) { # S'assurer qu'il y a au moins deux caractères (les guillemets)
                        $value = $value.Substring(1, $value.Length - 2)
                    } else {
                        # Cas étrange : une chaîne comme "'" ou """", laisser vide ou tel quel ? Pour l'instant, on la vide.
                        $value = ""
                    }
                }
                
                # Résolution spécifique pour JAVA_HOME si c'est un chemin relatif
                if ($key -eq "JAVA_HOME") {
                    if ($value.StartsWith("./") -or $value.StartsWith(".\\")) {
                        $resolvedValue = (Resolve-Path (Join-Path -Path $scriptRoot -ChildPath $value.Substring(2)) -ErrorAction SilentlyContinue).Path
                        if ($resolvedValue) {
                            $value = $resolvedValue
                        } else {
                            Write-Warning "Impossible de résoudre le chemin relatif pour JAVA_HOME: $($parts[1].Trim()) depuis $scriptRoot. Utilisation de la valeur brute."
                        }
                    }
                }
                # Pour USE_REAL_JPYPE et autres, on prend la valeur telle quelle.
                Write-Host "Définition de `$env:$key = '$value'"
                Set-Content "env:$key" -Value $value # Définit la variable pour la session PowerShell actuelle
            }
        }
    }

    # Configuration spécifique pour JAVA_HOME et PATH si JAVA_HOME est défini
    if ($env:JAVA_HOME) {
        $javaHomeAbs = $env:JAVA_HOME
        if (-not (Test-Path $javaHomeAbs -PathType Container)) {
             Write-Warning "JAVA_HOME ('$($env:JAVA_HOME)') n'est pas un répertoire valide ou n'a pas pu être résolu en chemin absolu."
        } else {
            $jdkBinPath = Join-Path -Path $javaHomeAbs -ChildPath "bin"
            if (Test-Path $jdkBinPath -PathType Container) {
                if ($env:PATH -notlike "*$jdkBinPath*") { # Vérifie si le chemin n'est pas déjà présent pour éviter les duplications
                    Write-Host "Ajout de '$jdkBinPath' au début du PATH."
                    $env:PATH = "$jdkBinPath;$($env:PATH)"
                } else {
                    Write-Host "'$jdkBinPath' semble déjà être dans le PATH."
                }
            } else {
                Write-Warning "Le répertoire bin du JDK ('$jdkBinPath') est introuvable. JAVA_HOME ('$javaHomeAbs') pourrait être incorrect."
            }
        }
    } else {
        Write-Warning "JAVA_HOME n'est pas défini dans le fichier .env ou n'a pas pu être chargé."
    }
} else {
    Write-Warning "Fichier '$envFile' ('$envFilePath') introuvable. Certaines variables d'environnement (comme JAVA_HOME) pourraient ne pas être configurées."
}

# --- Récupération du nom de l'environnement Conda ---
$envNameScriptPath = Join-Path $scriptRoot "scripts/get_env_name.py"
$condaEnvName = "" # Initialisation
$fallbackCondaEnvName = "projet-is" # Nom de secours final

try {
    # Tenter d'exécuter avec 'python' qui devrait être dans le PATH
    $condaEnvNameFromScript = ("$(python $envNameScriptPath 2>&1)" | Out-String).Trim()
    
    if ($LASTEXITCODE -ne 0 -or $condaEnvNameFromScript -match "^ERROR_GETTING_ENV_NAME" -or $condaEnvNameFromScript -match "^CRITICAL_ERROR" -or [string]::IsNullOrWhiteSpace($condaEnvNameFromScript) -or $condaEnvNameFromScript -match "\s") {
        Write-Warning "Erreur ou nom invalide lors de la récupération du nom de l'environnement Conda depuis '$envNameScriptPath': '$condaEnvNameFromScript'"
        # Tentative de fallback sur $env:CONDA_ENV_NAME
        if (-not [string]::IsNullOrWhiteSpace($env:CONDA_ENV_NAME)) {
            $condaEnvName = $env:CONDA_ENV_NAME
            Write-Host "[INFO] Utilisation du nom de l'environnement Conda depuis la variable d'environnement `$env:CONDA_ENV_NAME: '$condaEnvName'"
        } else {
            Write-Warning "La variable d'environnement `$env:CONDA_ENV_NAME n'est pas définie ou est vide."
            Write-Warning "Utilisation du nom par défaut '$fallbackCondaEnvName'."
            $condaEnvName = $fallbackCondaEnvName
        }
    } else {
        $condaEnvName = $condaEnvNameFromScript
        Write-Host "[INFO] Nom de l'environnement Conda récupéré depuis le script: '$condaEnvName'"
    }
} catch {
    Write-Warning "Exception lors de l'exécution de '$envNameScriptPath': $($_.Exception.Message)"
    # Tentative de fallback sur $env:CONDA_ENV_NAME en cas d'exception
    if (-not [string]::IsNullOrWhiteSpace($env:CONDA_ENV_NAME)) {
        $condaEnvName = $env:CONDA_ENV_NAME
        Write-Host "[INFO] Utilisation du nom de l'environnement Conda depuis la variable d'environnement `$env:CONDA_ENV_NAME (suite à une exception): '$condaEnvName'"
    } else {
        Write-Warning "La variable d'environnement `$env:CONDA_ENV_NAME n'est pas définie ou est vide (suite à une exception)."
        Write-Warning "Utilisation du nom par défaut '$fallbackCondaEnvName'."
        $condaEnvName = $fallbackCondaEnvName
    }
}

Write-Host "[INFO] Nom de l'environnement Conda final à utiliser: $condaEnvName"

# --- Exécution de la commande dans l'environnement Conda ---
if (-not [string]::IsNullOrEmpty($CommandToRun)) {
    Write-Host ""
    Write-Host "Tentative d'exécution de la commande '$CommandToRun' dans l'environnement Conda '$condaEnvName'..."
    Write-Host "Variables d'environnement actuelles (extrait):"
    Write-Host "  JAVA_HOME=$($env:JAVA_HOME)"
    Write-Host "  USE_REAL_JPYPE=$($env:USE_REAL_JPYPE)"
    Write-Host "  PATH (début)= $($env:PATH.Substring(0, [System.Math]::Min($env:PATH.Length, 200)))..."
    Write-Host "---------------------------------------------------------------------"
    
    $FullCommandToExecute = $CommandToRun
    if ($args.Count -gt 0) {
        $EscapedArgs = $args | ForEach-Object {
            if ($_ -match "\s" -or $_ -match "'" -or $_ -match '"') {
                "'$($_ -replace "'", "''")'"
            } elseif ($_.StartsWith("-") -and $_.Contains("=")) {
                $parts = $_.Split("=", 2)
                "$($parts[0])=$($parts[1])"
            }
            else {
                $_
            }
        }
        $FullCommandToExecute = "$CommandToRun $($EscapedArgs -join ' ')"
    }

    $condaRunCommand = "conda run -n $condaEnvName --no-capture-output --live-stream $FullCommandToExecute"
    Write-Host "Exécution via: $condaRunCommand"
    
    try {
        Invoke-Expression $condaRunCommand
        $exitCode = $LASTEXITCODE
    }
    catch {
        Write-Error "Une erreur s'est produite lors de l'exécution de la commande via conda run : $($_.Exception.Message)"
        $exitCode = 1 # Code d'erreur générique en cas d'exception PowerShell
    }

    Write-Host "---------------------------------------------------------------------"
    Write-Host "Commande '$CommandToRun' terminée avec le code de sortie: $exitCode"
    exit $exitCode 
} else {
    Write-Host ""
    Write-Host "---------------------------------------------------------------------"
    Write-Host "Variables d'environnement du projet chargées (si .env trouvé)."
    Write-Host "Aucune commande spécifiée à exécuter via -CommandToRun."
    Write-Host ""
    Write-Host "Pour activer manuellement l'environnement Conda '$condaEnvName' dans votre session PowerShell actuelle :"
    Write-Host "    conda activate $condaEnvName"
    Write-Host ""
    Write-Host "Ou pour exécuter une commande spécifique dans l'environnement :"
    Write-Host "    powershell -File .\activate_project_env.ps1 -CommandToRun \"votre_commande --arg1\""
    Write-Host "    (Assurez-vous que Conda est initialisé pour PowerShell: conda init powershell)"
    Write-Host "---------------------------------------------------------------------"
}