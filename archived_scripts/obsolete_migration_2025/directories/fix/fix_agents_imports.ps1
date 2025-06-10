# Script pour corriger les imports semantic_kernel.agents
$ErrorActionPreference = "Continue"

Write-Host "Début de la correction des imports semantic_kernel.agents..."

# Patterns à corriger
$patterns = @(
    @{
        Search = "from semantic_kernel.agents import Agent, AgentGroupChat"
        Replace = "from semantic_kernel_compatibility import Agent, AgentGroupChat"
    },
    @{
        Search = "from semantic_kernel.agents import Agent, AgentGroupChat, ChatCompletionAgent"
        Replace = "from semantic_kernel_compatibility import Agent, AgentGroupChat, ChatCompletionAgent"
    },
    @{
        Search = "from semantic_kernel.agents import ChatCompletionAgent, Agent, AgentGroupChat"
        Replace = "from semantic_kernel_compatibility import ChatCompletionAgent, Agent, AgentGroupChat"
    },
    @{
        Search = "from semantic_kernel.agents import"
        Replace = "from semantic_kernel_compatibility import"
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

# Vérification rapide des imports restants
Write-Host "`nVérification des imports semantic_kernel.agents restants..."
$remainingIssues = Select-String -Path "*.py" -Pattern "from semantic_kernel\.agents" -Recurse 2>$null | Select-Object -First 5
if ($remainingIssues) {
    Write-Host "Problèmes restants détectés:"
    $remainingIssues | ForEach-Object { Write-Host "  $($_.Filename):$($_.LineNumber) - $($_.Line.Trim())" }
} else {
    Write-Host "Aucun problème d'import semantic_kernel.agents détecté."
}