# Fichier : setup_test_env.ps1
# Auteur : Roo
# Date : 29/06/2025
#
# Description :
# Ce script prépare l'environnement pour l'exécution des tests d'intégration
# qui dépendent de Java (JPype et TweetyProject).
#
# Actions :
# 1. Tente de localiser un JDK sur le système.
# 2. Configure la variable d'environnement JAVA_HOME.
# 3. Construit et exporte le CLASSPATH pour les dépendances de Tweety.
# 4. Affiche des messages d'erreur clairs si une étape échoue.

$ErrorActionPreference = "Stop"

# --- CONFIGURATION ---
# Chemin vers le répertoire 'libs' de Tweety (à adapter si nécessaire)
$tweetyLibsDir = "$PSScriptRoot/tweety/libs"

# --- 1. LOCALISATION DU JDK ---
Write-Host "1. Recherche d'un JDK compatible..."

# Stratégie 1: Vérifier si un JDK portable existe dans le projet
$portableJdkPath = "$PSScriptRoot/portable_jdk"
if (Test-Path -Path $portableJdkPath -PathType Container) {
    $env:JAVA_HOME = $portableJdkPath
    Write-Host "   -> JDK portable trouvé : $env:JAVA_HOME"
}

# Stratégie 2: Vérifier si JAVA_HOME est déjà défini
if (-not $env:JAVA_HOME) {
    Write-Host "   -> La variable d'environnement JAVA_HOME n'est pas définie. Tentative de détection auto..."
    
    # Stratégie 3: Détection automatique (Windows)
    $jdkPaths = @(
        "C:\Program Files\Java\jdk*",
        "C:\Program Files\AdoptOpenJDK\jdk*",
        (Get-Command java -ErrorAction SilentlyContinue).Source | Split-Path | Split-Path
    )

    $installedJdk = $jdkPaths | ForEach-Object { Get-ChildItem -Path $_ -Directory -ErrorAction SilentlyContinue } | Sort-Object FullName -Descending | Select-Object -First 1

    if ($installedJdk) {
        $env:JAVA_HOME = $installedJdk.FullName
        Write-Host "   -> JDK détecté : $($env:JAVA_HOME)"
    } else {
        Write-Error "ÉCHEC : Impossible de trouver un JDK. Veuillez installer un JDK (version 11 ou supérieure) et/ou définir la variable d'environnement JAVA_HOME."
        exit 1
    }
}

# Vérifier que le chemin JAVA_HOME est valide
if (-not (Test-Path -Path $env:JAVA_HOME -PathType Container)) {
    Write-Error "ÉCHEC : Le chemin défini dans JAVA_HOME n'est pas valide : $($env:JAVA_HOME)"
    exit 1
}

Write-Host "`n   JAVA_HOME configuré : $($env:JAVA_HOME)"

# --- 2. CONSTRUCTION DU CLASSPATH ---
Write-Host "`n2. Construction du CLASSPATH pour TweetyProject..."

if (-not (Test-Path -Path $tweetyLibsDir -PathType Container)) {
    Write-Error "ÉCHEC : Le répertoire des bibliothèques Tweety est introuvable à l'emplacement : $tweetyLibsDir"
    exit 1
}

# Lister tous les fichiers .jar dans le répertoire libs
$jarFiles = Get-ChildItem -Path $tweetyLibsDir -Filter *.jar -Recurse | ForEach-Object { $_.FullName }

if ($jarFiles.Count -eq 0) {
    Write-Error "ÉCHEC : Aucun fichier .jar trouvé dans $tweetyLibsDir. Les bibliothèques de Tweety sont manquantes."
    exit 1
}

# Construire la chaîne CLASSPATH
$separator = if ($isWindows) {";"} else {":"}
$classpath = $jarFiles -join $separator

# Exporter le CLASSPATH pour la session courante
$env:CLASSPATH = $classpath

Write-Host "   -> CLASSPATH construit avec $($jarFiles.Count) librairies."
# Décommenter pour voir le détail du CLASSPATH
# Write-Host "   CLASSPATH: $classpath"


# --- 3. VÉRIFICATION FINALE ---
Write-Host "`n3. Environnement de test prêt."
Write-Host "   -> Prêt à lancer pytest."
