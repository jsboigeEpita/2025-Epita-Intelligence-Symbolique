param(
    [Parameter(Mandatory=$true)]
    [string]$CommandToRun
)

try {
    Write-Host "🚀 [INFO] Activation de l'environnement Conda 'projet-is' pour la commande..." -ForegroundColor Cyan
    Write-Host " Cde: $CommandToRun" -ForegroundColor Gray
    
    # Décomposition de la commande pour l'exécuter de manière plus fiable avec conda run
    # Cela évite les problèmes de "PowerShell-inception" et d'échappement de caractères.
    $command_parts = $CommandToRun.Split(' ')
    $executable = $command_parts[0]
    $arguments = $command_parts[1..($command_parts.Length - 1)]

    Write-Host "  -> Exécutable : $executable" -ForegroundColor Gray
    Write-Host "  -> Arguments  : $($arguments -join ' ')" -ForegroundColor Gray

    # Exécution directe de la commande via conda run
    conda run -n projet-is --no-capture-output --verbose -- $executable $arguments
    
    $exitCode = $LASTEXITCODE
    
    if ($exitCode -eq 0) {
        Write-Host "✅ [SUCCESS] Commande terminée avec succès." -ForegroundColor Green
    } else {
        Write-Host "❌ [FAILURE] La commande s'est terminée avec le code d'erreur: $exitCode" -ForegroundColor Red
    }
    
    exit $exitCode
}
catch {
    Write-Host "🔥 [CRITICAL] Une erreur inattendue est survenue dans le script d'activation." -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}