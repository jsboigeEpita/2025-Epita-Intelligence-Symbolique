# Script pour corriger les imports AuthorRole vers ChatRole
$ErrorActionPreference = "Continue"

Write-Host "Début de la correction des imports AuthorRole..."

# Patterns à corriger
$patterns = @(
    @{
        Search = "from semantic_kernel.contents import ChatMessageContent, AuthorRole"
        Replace = "from semantic_kernel.contents import ChatMessageContent, ChatRole as AuthorRole"
    },
    @{
        Search = "from semantic_kernel.contents.utils.author_role import AuthorRole"
        Replace = "from semantic_kernel.contents import ChatRole as AuthorRole"
    }
)

# Trouver tous les fichiers Python
$pythonFiles = Get-ChildItem -Path . -Recurse -Filter "*.py" | Where-Object { 
    $_.FullName -notlike "*\.git*" -and $_.FullName -notlike "*__pycache__*" 
}

$totalFiles = $pythonFiles.Count
$modifiedFiles = 0

Write-Host "Fichiers Python trouvés: $totalFiles"

foreach ($file in $pythonFiles) {
    $content = Get-Content $file.FullName -Raw -Encoding UTF8
    $originalContent = $content
    $fileModified = $false
    
    foreach ($pattern in $patterns) {
        if ($content -match [regex]::Escape($pattern.Search)) {
            $content = $content -replace [regex]::Escape($pattern.Search), $pattern.Replace
            $fileModified = $true
            Write-Host "  Modifié: $($file.FullName) - Pattern: $($pattern.Search)"
        }
    }
    
    if ($fileModified) {
        Set-Content -Path $file.FullName -Value $content -Encoding UTF8
        $modifiedFiles++
    }
}

Write-Host "Correction terminée. Fichiers modifiés: $modifiedFiles sur $totalFiles"

# Vérification rapide
Write-Host "`nVérification des imports restants..."
$remainingIssues = Select-String -Path "*.py" -Pattern "from semantic_kernel.contents import.*AuthorRole" -Recurse | Select-Object -First 5
if ($remainingIssues) {
    Write-Host "Problèmes restants détectés:"
    $remainingIssues | ForEach-Object { Write-Host "  $($_.Filename):$($_.LineNumber) - $($_.Line.Trim())" }
} else {
    Write-Host "Aucun problème d'import AuthorRole détecté."
}