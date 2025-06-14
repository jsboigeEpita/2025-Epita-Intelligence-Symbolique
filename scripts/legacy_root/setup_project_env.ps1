param(
    [Parameter(Mandatory=$true)]
    [string]$CommandToRun
)

try {
    Write-Host "🚀 [INFO] Activation de l'environnement Conda 'projet-is' pour la commande..." -ForegroundColor Cyan
    Write-Host " Cde: $CommandToRun" -ForegroundColor Gray
    
    # Utilisation de l'opérateur d'appel (&) pour exécuter la commande
    # Ceci est plus sûr car la chaîne est traitée comme une seule commande avec des arguments.
    conda run -n projet-is --no-capture-output --verbose powershell -Command "& { $CommandToRun }"
    
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