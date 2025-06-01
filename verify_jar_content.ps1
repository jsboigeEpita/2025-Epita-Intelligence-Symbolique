param(
    [Parameter(Mandatory=$true)]
    [string]$TargetJarName,

    [Parameter(Mandatory=$true)]
    [string]$PackagePathToList # Doit se terminer par un slash, ex: "org/tweetyproject/lp/asp/syntax/"
)

$JarDir = "C:\dev\2025-Epita-Intelligence-Symbolique\libs" # Codé en dur pour cette version
$FullJarPath = Join-Path -Path $JarDir -ChildPath $TargetJarName

Write-Host "=================================================="
Write-Host "Script de listage du contenu d'un package dans un JAR."
Write-Host "=================================================="
Write-Host "JAR Cible         : '$FullJarPath'"
Write-Host "Package à lister  : '$PackagePathToList'"
Write-Host "--------------------------------------------------"

if (-not (Test-Path $FullJarPath -PathType Leaf)) {
    Write-Error "ERREUR CRITIQUE: Le fichier JAR '$FullJarPath' n'existe pas ou n'est pas accessible."
    exit 1
}

$packageContents = @()
$script:GlobalErrors = $false

Write-Host "Lecture du contenu de '$TargetJarName' pour le package '$PackagePathToList'..."

$processInfo = New-Object System.Diagnostics.ProcessStartInfo
$processInfo.FileName = "jar.exe"
$processInfo.Arguments = "tf ""$($FullJarPath)"""
$processInfo.RedirectStandardOutput = $true
$processInfo.RedirectStandardError = $true
$processInfo.UseShellExecute = $false
$processInfo.CreateNoWindow = $true

$process = New-Object System.Diagnostics.Process
$process.StartInfo = $processInfo

try {
    $process.Start() | Out-Null
    $stdoutTask = $process.StandardOutput.ReadToEndAsync()
    $stderrTask = $process.StandardError.ReadToEndAsync()
    
    # Attendre que les tâches de lecture asynchrone et le processus se terminent
    $process.WaitForExit(30000) # Timeout de 30 secondes

    if (-not $process.HasExited) {
        Write-Warning "  TIMEOUT: Le traitement de '$TargetJarName' a dépassé 30 secondes. Tentative de le tuer."
        try { $process.Kill() } catch { Write-Warning "  Impossible de tuer le processus : $($_.Exception.Message)"}
        $script:GlobalErrors = $true
        exit 1
    }
    
    # S'assurer que les lectures de flux sont terminées
    [System.Threading.Tasks.Task]::WaitAll($stdoutTask, $stderrTask)

    $exitCode = $process.ExitCode
    $outputLines = ($stdoutTask.Result).Split([System.Environment]::NewLine)
    $errorOutput = $stderrTask.Result

    Write-Host "  Code de sortie de 'jar.exe': $exitCode"

    if ($errorOutput -and $errorOutput.Trim().Length -gt 0) {
        Write-Warning "  Sortie d'erreur (stderr) de 'jar.exe' pour '$TargetJarName':"
        $errorOutput.Split([System.Environment]::NewLine) | ForEach-Object { Write-Warning "    $_" }
        if ($exitCode -eq 0) { $script:GlobalErrors = $true; } 
    }
    
    if ($exitCode -eq 0) {
        foreach ($line in $outputLines) {
            if ($line.StartsWith($PackagePathToList)) {
                $packageContents += $line
            }
        }
        if ($packageContents.Count -gt 0) {
            Write-Host ""
            Write-Host "Contenu trouvé dans le package '$PackagePathToList':" -ForegroundColor Green
            $packageContents | Sort-Object | ForEach-Object { Write-Host "  $_" }
        } else {
            Write-Host "Aucun contenu trouvé commençant par '$PackagePathToList' dans le JAR." -ForegroundColor Yellow
        }
    } else {
        Write-Error "  ERREUR: 'jar.exe' a retourné le code $exitCode pour '$TargetJarName'."
        $script:GlobalErrors = $true
    }
} catch {
    Write-Error "  EXCEPTION PowerShell lors du traitement de '$TargetJarName': $($_.Exception.Message)"
    $script:GlobalErrors = $true
} finally {
    if ($process -ne $null) {
        $process.Dispose()
    }
}

Write-Host "=================================================="
if ($script:GlobalErrors) {
    Write-Warning "Des erreurs se sont produites."
    exit 1
} else {
    Write-Host "Script terminé."
    exit 0
}