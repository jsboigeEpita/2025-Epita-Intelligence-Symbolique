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

# --- Exécution de la commande dans l'environnement Conda ---
if (-not [string]::IsNullOrEmpty($CommandToRun)) {
    Write-Host ""
    Write-Host "Tentative d'exécution de la commande '$CommandToRun' dans l'environnement Conda '$condaEnvName'..."
    Write-Host "Variables d'environnement actuelles (extrait):"
    Write-Host "  JAVA_HOME=$($env:JAVA_HOME)"
    Write-Host "  USE_REAL_JPYPE=$($env:USE_REAL_JPYPE)"
    Write-Host "  PATH (début)= $($env:PATH.Substring(0, [System.Math]::Min($env:PATH.Length, 200)))..."
    Write-Host "---------------------------------------------------------------------"
    
    # Utilisation de 'conda run' pour exécuter la commande dans l'environnement spécifié.
    # Les variables d'environnement définies ci-dessus dans la session PowerShell actuelle
    # devraient être héritées par le processus lancé par 'conda run'.
    $condaRunCommand = "conda run -n $condaEnvName --no-capture-output --live-stream -- $CommandToRun"
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
    exit $exitCode # Quitte le script avec le code de sortie de la commande exécutée
} else {
    # Si aucune commande n'est fournie, ce script est probablement sourcé ou appelé pour charger l'environnement
    # dans un contexte où l'utilisateur exécutera des commandes ensuite.
    # L'activation réelle de Conda pour la session appelante via `conda activate` directement dans le script
    # ne fonctionne de manière fiable que si le script est "sourcé" (ex: . .\activate_project_env.ps1).
    # Si appelé normalement (.\activate_project_env.ps1), l'activation est locale au script.
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