param (
    [string]$JdkBinPath,
    [string]$TweetyJarPath,
    [string]$OutputFilePath
)

$originalPath = $env:Path
$env:Path = $JdkBinPath + ';' + $env:Path

try {
    New-Item -ItemType Directory -Path (Split-Path -Path $OutputFilePath -Parent) -Force -ErrorAction SilentlyContinue | Out-Null
    & (Join-Path $JdkBinPath 'jar.exe') tf $TweetyJarPath > $OutputFilePath
    Write-Host "Contenu du JAR listé dans $OutputFilePath"
}
catch {
    Write-Error "Erreur lors de l'exécution de jar tf : $_"
    exit 1
}
finally {
    $env:Path = $originalPath
}