#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Crée ou recrée complètement l'environnement Conda du projet.
.DESCRIPTION
    Ce script assure une installation propre de l'environnement 'projet-is-v2'
    en utilisant le fichier 'environment.yml' comme seule source de vérité.
    Il supprime d'abord tout environnement existant du même nom pour éviter
    les conflits.
.NOTES
    Auteur: Roo
    Date: 25/06/2025
    Raison: Stratégie de dépendances unifiée pour garantir la stabilité.
#>

# --- Configuration ---
$EnvName = "projet-is-v2"
$EnvironmentFile = "environment.yml"

# --- Bannière ---
Write-Host "--- Configuration de l'environnement Conda '$EnvName' ---" -ForegroundColor Green

# 1. Tenter de supprimer l'environnement s'il existe pour garantir une installation propre.
Write-Host "[INFO] Vérification et suppression de l'ancien environnement '$EnvName' si présent..." -ForegroundColor Yellow
try {
    # Obtenir la liste des environnements et vérifier si le nôtre existe
    $envList = conda env list | Out-String
    if ($envList -match "\s$EnvName\s") {
        Write-Host "Environnement '$EnvName' trouvé. Tentative de suppression..."
        conda env remove -n $EnvName --yes
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[AVERTISSEMENT] La suppression de l'environnement a échoué. Il est possible qu'un processus l'utilise encore." -ForegroundColor Red
        } else {
            Write-Host "[INFO] Ancien environnement '$EnvName' supprimé." -ForegroundColor Green
        }
    } else {
        Write-Host "[INFO] Pas d'environnement existant '$EnvName' trouvé." -ForegroundColor Gray
    }
}
catch {
    Write-Host "[AVERTISSEMENT] Une erreur est survenue lors de la tentative de suppression de l'environnement. Le script va continuer." -ForegroundColor Yellow
}

# 2. Création de l'environnement à partir du fichier YAML
Write-Host "[INFO] Création du nouvel environnement '$EnvName' à partir de '$EnvironmentFile'." -ForegroundColor Green
try {
    # Utiliser mamba si disponible, sinon conda
    $PackageManager = if (Get-Command mamba -ErrorAction SilentlyContinue) { "mamba" } else { "conda" }
    Write-Host "[INFO] Utilisation de '$PackageManager' pour la création de l'environnement."
    
    & $PackageManager env create --file $EnvironmentFile --name $EnvName
    
    if ($LASTEXITCODE -ne 0) {
        throw "La création de l'environnement avec $PackageManager a échoué."
    }
    Write-Host "[SUCCÈS] L'environnement Conda '$EnvName' a été créé." -ForegroundColor Green
}
catch {
    Write-Host "[ERREUR] Une erreur critique est survenue lors de la création de l'environnement." -ForegroundColor Red
    Write-Host "Message: $($_.Exception.Message)"
    exit 1
}

# 3. Instructions finales
Write-Host -f Green "--- Installation terminée ---"
Write-Host "Pour activer l'environnement, utilisez la commande suivante dans votre terminal:"
Write-Host -f Cyan "conda activate $EnvName"
