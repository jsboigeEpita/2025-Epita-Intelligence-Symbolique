# Script pour corriger les imports AgentChatException
$ErrorActionPreference = "Continue"

Write-Host "Correction des imports AgentChatException..."

# Patterns à corriger
$patterns = @(
    @{
        Search = "from semantic_kernel.exceptions import AgentChatException"
        Replace = "from semantic_kernel_compatibility import AgentChatException"
    }
)

# Trouver tous les fichiers Python
$pythonFiles = Get-ChildItem -Path . -Recurse -Filter "*.py" | Where-Object { 
    $_.FullName -notlike "*\.git*" -and $_.FullName -notlike "*__pycache__*" 
}

$modifiedFiles = 0

foreach ($file in $pythonFiles) {
    $content = Get-Content $file.FullName -Raw -Encoding UTF8
    $fileModified = $false
    
    foreach ($pattern in $patterns) {
        if ($content -match [regex]::Escape($pattern.Search)) {
            $content = $content -replace [regex]::Escape($pattern.Search), $pattern.Replace
            $fileModified = $true
            Write-Host "  Modifié: $($file.FullName)"
        }
    }
    
    if ($fileModified) {
        Set-Content -Path $file.FullName -Value $content -Encoding UTF8
        $modifiedFiles++
    }
}

Write-Host "Correction terminée. Fichiers modifiés: $modifiedFiles"