# Définition des chemins et du nom de la classe à rechercher
$jarPath = "libs/org.tweetyproject.tweety-full-1.28-with-dependencies.jar"
$outputFilePath = "_temp/found_class_path.txt"
# $classNameSubstringToFind = "PropositionalSignature.class" # Plus utilisé directement ici
$packagePrefix = "org/tweetyproject/logics/ml/syntax/" # Nom modifié pour clarté et usage

$originalPath = $env:Path
# $env:Path = $JdkBinPath + ';' + $env:Path # JdkBinPath n'est plus utilisé directement

try {
    # Activer l'environnement du projet pour définir JAVA_HOME
    . $PSScriptRoot/../activate_project_env.ps1
    Write-Host "JAVA_HOME après activation: $env:JAVA_HOME"

    if (-not $env:JAVA_HOME) {
        Write-Error "JAVA_HOME n'est pas défini après l'exécution de activate_project_env.ps1. Vérifiez le script d'activation."
        exit 1
    }
    $ResolvedJdkBinPath = Join-Path $env:JAVA_HOME "bin"

    # Assurer que le répertoire de sortie existe
    $OutputDirectory = Split-Path -Path $outputFilePath -Parent
    if (-not (Test-Path $OutputDirectory)) {
        New-Item -ItemType Directory -Path $OutputDirectory -Force -ErrorAction SilentlyContinue | Out-Null
    }

    # Exécuter jar tf et capturer la sortie brute
    $rawOutput = & (Join-Path $ResolvedJdkBinPath 'jar.exe') tf $jarPath

    # La sortie brute de 'jar tf' est dans $rawOutput (un tableau de lignes)
    # Aucune logique de nettoyage n'est appliquée ici.

    # Rechercher les classes directement dans le package spécifié
    # a. Définir le chemin du package à rechercher (déjà fait avec $packagePrefix)
    # b. Rechercher toutes les lignes qui :
    #    * Commencent par $packagePrefix (sensible à la casse : -cstartsWith).
    #    * ET se terminent par .class (sensible à la casse : -cendsWith).
    #    * ET ne contiennent pas d'autre / après le $packagePrefix initial.
    $foundClasses = $rawOutput | Where-Object {
        $_.StartsWith($packagePrefix, [System.StringComparison]::Ordinal) -and `
        $_.EndsWith(".class", [System.StringComparison]::Ordinal) -and `
        ($_.Substring($packagePrefix.Length) -notmatch "/")
    } | ForEach-Object { $_ } # Assure que $foundClasses est un tableau même avec un seul résultat ou aucun

    # c. Si des lignes correspondantes sont trouvées, écrire toutes ces lignes.
    # d. Si aucune ligne correspondante n'est trouvée, écrire la chaîne spécifiée.
    if ($foundClasses -and $foundClasses.Count -gt 0) {
        Set-Content -Path $outputFilePath -Value ($foundClasses -join "`n") -Encoding UTF8
        Write-Host "Classe(s) trouvée(s) directement dans le package '$packagePrefix' (sortie brute) et sauvegardée(s) dans $outputFilePath :"
        $foundClasses | ForEach-Object { Write-Host "- $_" }
    } else {
        Write-Host "Aucune classe trouvée directement dans le package '$packagePrefix' (sortie brute)."
        Set-Content -Path $outputFilePath -Value "AUCUNE_CLASSE_TROUVEE_DANS_PACKAGE_BRUT" -Encoding UTF8
        Write-Host "'AUCUNE_CLASSE_TROUVEE_DANS_PACKAGE_BRUT' sauvegardé dans $outputFilePath."
    }
}
catch {
    Write-Error "Erreur lors de l'exécution de jar tf ou du traitement de la sortie : $_"
    # Écrire la sortie brute en cas d'erreur de nettoyage pour diagnostic
    if ($rawOutput) {
        $rawOutputFilePath = $outputFilePath -replace '\.txt$', '_raw_error.txt' # Utiliser la variable définie localement
        Set-Content -Path $rawOutputFilePath -Value $rawOutput -Encoding UTF8
        Write-Warning "La sortie brute a été sauvegardée dans $rawOutputFilePath"
    }
    exit 1
}
finally {
    $env:Path = $originalPath
}