param (
    [string]$CommandToRun = "" # Commande à exécuter après activation
)

$condaEnvName = "projet-is"
$envFile = ".env"
# Assurer que PSScriptRoot est défini, même si le script est appelé d'une manière où $PSScriptRoot n'est pas automatiquement peuplé.
if ($PSScriptRoot) {
    $scriptRoot = $PSScriptRoot
} else {
    $scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
}
$projectRoot = Split-Path -Parent (Split-Path -Parent $scriptRoot) # Racine du projet (parent du parent de scripts/env)

# --- Gestion de JAVA_HOME et Chargement des Variables d'Environnement ---
$envJavaHomeProcessed = $false # Pour s'assurer que la logique de PATH pour JAVA_HOME n'est exécutée qu'une fois
# $foundValidSystemJavaHome n'est plus utilisé car .env est la source principale gérée par le setup Python.

# Charger les variables depuis .env. JAVA_HOME du .env sera la source principale.
$envFilePath = Join-Path $projectRoot $envFile # Chercher .env à la racine du projet
if (Test-Path $envFilePath) {
    Write-Host "Chargement des variables d'environnement depuis '$envFile' (chemin du .env: $envFilePath)..."
    Get-Content $envFilePath | ForEach-Object {
        $line = $_.Trim()
        if ($line -and $line -notmatch "^\s*#") { # Ignorer les commentaires et les lignes vides
            $parts = $line.Split("=", 2)
            if ($parts.Length -eq 2) {
                $key = $parts[0].Trim()
                $value = $parts[1].Trim()

                if ($key -eq "JAVA_HOME") {
                    # JAVA_HOME du .env est maintenant la source principale, gérée par le setup Python.
                    # La logique de $foundValidSystemJavaHome a été supprimée.
                    if ($value.StartsWith("./") -or $value.StartsWith(".\\")) {
                        $resolvedValue = (Resolve-Path (Join-Path -Path $projectRoot -ChildPath $value.Substring(2)) -ErrorAction SilentlyContinue).Path
                        if ($resolvedValue) {
                            $value = $resolvedValue
                        } else {
                            Write-Warning "Impossible de résoudre le chemin relatif pour JAVA_HOME depuis .env: $($parts[1].Trim()) depuis $projectRoot. Utilisation de la valeur brute."
                        }
                    }
                    Write-Host "Définition de `$env:JAVA_HOME = '$value' (depuis .env)"
                    Set-Content "env:JAVA_HOME" -Value $value
                    # La logique de validation et d'ajout au PATH pour JAVA_HOME du .env sera faite après la boucle
                } elseif ($key -eq "CONDA_ENV_NAME") {
                    $condaEnvName = $value # Mettre à jour $condaEnvName directement
                    Write-Host "[INFO] Utilisation de CONDA_ENV_NAME depuis .env: '$condaEnvName'"
                    Set-Content "env:$key" -Value $value # Aussi la définir comme variable d'env pour la session
                } else {
                    # Pour les autres variables (USE_REAL_JPYPE, etc.)
                    Write-Host "Définition de `$env:$key = '$value' (depuis .env)"
                    Set-Content "env:$key" -Value $value
                }
            }
        }
    }

    # 3. Configuration spécifique pour JAVA_HOME et PATH si elle vient du .env et n'a pas été traitée via système
    if ($env:JAVA_HOME -and -not $envJavaHomeProcessed) { # $env:JAVA_HOME ici serait celle du .env
        $javaHomeFromEnvFile = $env:JAVA_HOME
        if (-not (Test-Path $javaHomeFromEnvFile -PathType Container)) {
             Write-Warning "JAVA_HOME ('$javaHomeFromEnvFile' depuis .env) n'est pas un répertoire valide."
        } else {
            $jdkBinPathFromEnvFile = Join-Path -Path $javaHomeFromEnvFile -ChildPath "bin"
            if (Test-Path $jdkBinPathFromEnvFile -PathType Container) {
                if ($env:PATH -notlike "*$jdkBinPathFromEnvFile*") {
                    Write-Host "Ajout de '$jdkBinPathFromEnvFile' (depuis .env) au début du PATH."
                    $env:PATH = "$jdkBinPathFromEnvFile;$($env:PATH)"
                } else {
                    Write-Host "'$jdkBinPathFromEnvFile' (depuis .env) semble déjà être dans le PATH."
                }
                $envJavaHomeProcessed = $true # Marquer comme traité
            } else {
                Write-Warning "Le répertoire bin du JDK ('$jdkBinPathFromEnvFile' depuis .env) est introuvable. JAVA_HOME ('$javaHomeFromEnvFile') pourrait être incorrect."
            }
        }
    }
    
    # Vérification finale pour CONDA_ENV_NAME si elle n'a pas été mise par le .env
    if ($env:CONDA_ENV_NAME) {
        # $condaEnvName est déjà mis à jour si la variable était dans .env
    } else {
         Write-Warning "[WARN] CONDA_ENV_NAME n'est pas défini dans .env. Utilisation de la valeur par défaut '$condaEnvName'."
    }

} else { # Si .env n'est pas trouvé
    Write-Warning "Fichier '$envFile' ('$envFilePath') introuvable."
    if (-not $foundValidSystemJavaHome) {
        Write-Warning "JAVA_HOME n'est pas configuré (ni par système, ni par .env)."
    }
    Write-Warning "[WARN] Fichier .env non trouvé. Utilisation de la valeur par défaut pour condaEnvName: '$condaEnvName'."
}

# Si après tout ça, JAVA_HOME n'est toujours pas défini ou valide
if (-not $envJavaHomeProcessed) {
    Write-Warning "AVERTISSEMENT FINAL: JAVA_HOME n'est pas configuré correctement ou le répertoire bin est introuvable."
}


# --- Exécution de la commande dans l'environnement Conda ---
if (-not [string]::IsNullOrWhiteSpace($CommandToRun)) {
    Write-Host ""
    Write-Host "Tentative d'exécution de la commande '$CommandToRun' dans l'environnement Conda '$condaEnvName'..."
    Write-Host "Variables d'environnement actuelles (extrait):"
    Write-Host "  JAVA_HOME=$($env:JAVA_HOME)"
    Write-Host "  USE_REAL_JPYPE=$($env:USE_REAL_JPYPE)"
    Write-Host "  PATH (début)= $($env:PATH.Substring(0, [System.Math]::Min($env:PATH.Length, 200)))..."
    Write-Host "---------------------------------------------------------------------"
    
    $condaRunCommand = "conda run -n $condaEnvName --no-capture-output --live-stream $CommandToRun"
    Write-Host "Exécution via: $condaRunCommand"
    
    try {
        Invoke-Expression $condaRunCommand
        $exitCode = $LASTEXITCODE
    }
    catch {
        Write-Error "Une erreur s'est produite lors de l'exécution de la commande via conda run : $($_.Exception.Message)"
        $exitCode = 1 
    }

    Write-Host "---------------------------------------------------------------------"
    Write-Host "Commande '$CommandToRun' terminée avec le code de sortie: $exitCode"
    exit $exitCode 
} else {
    Write-Host ""
    Write-Host "---------------------------------------------------------------------"
    Write-Host "Variables d'environnement du projet chargées."
    Write-Host "JAVA_HOME configuré à: $($env:JAVA_HOME)"
    Write-Host "Aucune commande spécifiée à exécuter via -CommandToRun."
    Write-Host ""
    Write-Host "Pour activer manuellement l'environnement Conda '$condaEnvName' dans votre session PowerShell actuelle :"
    Write-Host "    conda activate $condaEnvName"
    Write-Host ""
    Write-Host "Ou pour exécuter une commande spécifique dans l'environnement :"
    Write-Host "    powershell -File .\scripts\env\activate_project_env.ps1 -CommandToRun \"votre_commande --arg1\""
    Write-Host "    (Assurez-vous que Conda est initialisé pour PowerShell: conda init powershell)"
    Write-Host "---------------------------------------------------------------------"
}