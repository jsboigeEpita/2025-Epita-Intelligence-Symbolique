[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string[]]$Commits,

    [Parameter(Mandatory=$true)]
    [string]$OutputFile,

    [Parameter(Mandatory=$true)]
    [string]$WorkingDirectory
)

# Définition des patterns et mots-clés à rechercher
$keywordsInCommitMessage = @("fix", "bug", "revert", "hotfix", "crash", "error", "instability", "regression")
$keywordsInDiff = @("KMP_DUPLICATE_LIB_OK=TRUE", "agent", "orchestrator", "uvicorn", "ASGI", "JVM", "semantic-kernel")
$sensitiveFiles = @("environment.yml", "package.json", "package-lock.json", "activate_project_env.ps1", "logs/frontend_url.txt", "playwright.config.js", "run_functional_tests.ps1")

# Définit le répertoire de travail pour les commandes git
Set-Location -Path $WorkingDirectory

# Initialise ou vide le fichier de sortie
New-Item -Path $OutputFile -ItemType File -Force | Out-Null

# Boucle sur chaque hash de commit fourni
foreach ($hash in $Commits) {
    Write-Host "Analyse du commit : $hash"
    
    $commitMessage = git show -s --format=%B $hash
    $commitDiff = git show $hash
    $gitOutput = git show --pretty="" --name-only $hash
    $changedFiles = if ($gitOutput) {
        $gitOutput.Split("`n") | Where-Object { $_ }
    } else {
        @()
    }


    $findings = @()

    # 1. Analyse du message de commit
    foreach ($keyword in $keywordsInCommitMessage) {
        if ($commitMessage -match $keyword) {
            $findings += "Mot-clé suspect '$keyword' trouvé dans le message de commit."
        }
    }

    # 2. Analyse du diff
    foreach ($keyword in $keywordsInDiff) {
        if ($commitDiff -match $keyword) {
            $findings += "Mot-clé suspect '$keyword' trouvé dans le diff."
        }
    }

    # 3. Analyse des fichiers modifiés
    foreach ($file in $changedFiles) {
        foreach ($sensitiveFile in $sensitiveFiles) {
            if ($file.Trim() -match $sensitiveFile) {
                $findings += "Modification du fichier sensible '$($file.Trim())'."
            }
        }
    }

    # Si des éléments ont été trouvés, les ajouter au rapport
    if ($findings.Count -gt 0) {
        $header = "==================== COMMIT: $hash ===================="
        Add-Content -Path $OutputFile -Value $header
        Add-Content -Path $OutputFile -Value "Message:"
        Add-Content -Path $OutputFile -Value $commitMessage
        Add-Content -Path $OutputFile -Value ""
        Add-Content -Path $OutputFile -Value "--- Détections ---"
        $findings | ForEach-Object { Add-Content -Path $OutputFile -Value "- $_" }
        Add-Content -Path $OutputFile -Value ""
        Add-Content -Path $OutputFile -Value "--- Diff Complet ---"
        $commitDiff | Out-File -FilePath $OutputFile -Append -Encoding utf8
        Add-Content -Path $OutputFile -Value ""
    }
}

Write-Host "L'analyse ciblée des commits est terminée. Les résultats sont dans le fichier : $OutputFile"