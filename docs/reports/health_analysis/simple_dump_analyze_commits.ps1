[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string[]]$Commits,

    [Parameter(Mandatory=$true)]
    [string]$OutputFile,

    [Parameter(Mandatory=$true)]
    [string]$WorkingDirectory
)

# Définit le répertoire de travail pour les commandes git
Set-Location -Path $WorkingDirectory

# Initialise ou vide le fichier de sortie
Clear-Content -Path $OutputFile -ErrorAction SilentlyContinue

# Boucle sur chaque hash de commit fourni
foreach ($hash in $Commits) {
    Write-Host "Début de l'analyse du commit : $hash"
    # Ajoute un séparateur et le hash du commit dans le fichier de sortie
    Add-Content -Path $OutputFile -Value "==================== COMMIT: $hash ===================="
    
    # Exécute git show pour obtenir les détails du commit et les ajoute au fichier
    git show $hash | Out-File -FilePath $OutputFile -Append -Encoding utf8
    
    # Ajoute une ligne vide pour la lisibilité
    Add-Content -Path $OutputFile -Value ""
    Write-Host "Fin de l'analyse du commit : $hash"
}

Write-Host "L'analyse des commits est terminée. Les résultats sont dans le fichier : $OutputFile"