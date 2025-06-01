# Script d'activation de l'environnement du projet

# --- Configuration ---
$venvName = "venv_py310"
$envFile = ".env"

# --- Activation de l'Environnement Virtuel Python ---
$activateScriptPath = Join-Path -Path (Join-Path -Path $PSScriptRoot -ChildPath $venvName) -ChildPath "Scripts\Activate.ps1"

if (Test-Path $activateScriptPath) {
    Write-Host "Activation de l'environnement virtuel Python '$venvName'..."
    . $activateScriptPath
} else {
    Write-Error "Script d'activation '$activateScriptPath' introuvable."
    Write-Error "Veuillez exécuter le script setup_project_env.ps1 pour configurer l'environnement."
    exit 1
}

# --- Configuration des Variables d'Environnement ---
$envFilePath = Join-Path $PSScriptRoot $envFile

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
                
                # Remplacer les slashes par des backslashes pour les chemins Windows si nécessaire,
                # mais JAVA_HOME est souvent mieux avec des slashes pour la compatibilité inter-outils.
                # Pour le PATH, les backslashes sont standards sous Windows.
                if ($key -eq "JAVA_HOME") {
                    # Convertir en chemin absolu basé sur la racine du script
                    if ($value.StartsWith("./") -or $value.StartsWith(".\\")) {
                        $value = (Resolve-Path (Join-Path -Path $PSScriptRoot -ChildPath $value.Substring(2))).Path
                    } elseif ($value.StartsWith("/") -or $value.StartsWith("\")) {
                         # Si c'est un chemin relatif à la racine du lecteur, cela pourrait être problématique.
                         # Pour ce projet, nous attendons ./portable_jdk/...
                         Write-Warning "Le chemin JAVA_HOME commence par un slash, ce qui pourrait ne pas être interprété comme relatif au projet: $value"
                    }
                    # Assurer que les backslashes sont utilisés si c'est un chemin Windows, bien que les slashes fonctionnent souvent.
                    # $value = $value.Replace('/', '\')
                }

                Write-Host "Définition de `$env:$key = '$value'"
                Set-Content "env:$key" -Value $value
            }
        }
    }

    # Configuration spécifique pour JAVA_HOME et PATH si JAVA_HOME est défini
    if ($env:JAVA_HOME) {
        $javaHomeAbs = $env:JAVA_HOME
        # Assurer que JAVA_HOME est un chemin absolu
        if (-not (Test-Path $javaHomeAbs -PathType Container)) {
             # Tenter de résoudre si c'est un chemin relatif qui n'a pas été correctement converti
            $potentialAbsPath = (Resolve-Path (Join-Path -Path $PSScriptRoot -ChildPath $javaHomeAbs) -ErrorAction SilentlyContinue).Path
            if ($potentialAbsPath -and (Test-Path $potentialAbsPath -PathType Container)) {
                $javaHomeAbs = $potentialAbsPath
                $env:JAVA_HOME = $javaHomeAbs # Mettre à jour la variable d'environnement
                Write-Host "JAVA_HOME résolu en chemin absolu: $javaHomeAbs"
            } else {
                Write-Warning "JAVA_HOME ('$($env:JAVA_HOME)') n'est pas un répertoire valide ou n'a pas pu être résolu en chemin absolu."
            }
        }


        $jdkBinPath = Join-Path -Path $javaHomeAbs -ChildPath "bin"
        if (Test-Path $jdkBinPath -PathType Container) {
            Write-Host "Ajout de '$jdkBinPath' au PATH."
            $env:PATH = "$jdkBinPath;$($env:PATH)"
        } else {
            Write-Warning "Le répertoire bin du JDK ('$jdkBinPath') est introuvable. JAVA_HOME pourrait être incorrect."
        }
    } else {
        Write-Warning "JAVA_HOME n'est pas défini dans le fichier .env ou n'a pas pu être chargé."
    }
} else {
    Write-Warning "Fichier '$envFile' introuvable. Certaines variables d'environnement (comme JAVA_HOME) pourraient ne pas être configurées."
    Write-Warning "Veuillez exécuter le script setup_project_env.ps1."
}

# Configuration de PYTHONPATH (optionnel, si nécessaire)
# $env:PYTHONPATH = "$($PSScriptRoot);$($env:PYTHONPATH)"
# Write-Host "PYTHONPATH configuré pour inclure la racine du projet."

# --- Message de Confirmation ---
Write-Host ""
Write-Host "---------------------------------------------------------------------"
Write-Host "Environnement du projet activé!"
Write-Host "Python actif :"
python --version # Ou py --version si python n'est pas directement dans le PATH du venv activé
Write-Host "JAVA_HOME :"
if ($env:JAVA_HOME) {
    Write-Host "  $($env:JAVA_HOME)"
} else {
    Write-Host "  Non défini"
}
Write-Host "Pour vérifier la configuration Java, essayez : java -version"
Write-Host "---------------------------------------------------------------------"