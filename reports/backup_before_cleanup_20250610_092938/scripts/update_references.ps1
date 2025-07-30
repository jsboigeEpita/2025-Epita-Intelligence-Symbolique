param(
    [Parameter(Mandatory=$true)]
    [string]$JsonPath
)

$replacements = Get-Content -Path $JsonPath | ConvertFrom-Json

foreach ($item in $replacements) {
    $markdownFile = $item.MarkdownFile
    $obsoleteRef = $item.ObsoleteRef
    $newRef = $item.NewRef

    if (Test-Path $markdownFile) {
        $content = Get-Content $markdownFile -Raw
        $newContent = $content.Replace($obsoleteRef, $newRef)
        if ($content -ne $newContent) {
            Set-Content -Path $markdownFile -Value $newContent
            Write-Host "Remplacement effectué dans '$markdownFile': '$obsoleteRef' -> '$newRef'"
        }
    } else {
        Write-Warning "Le fichier '$markdownFile' n'a pas été trouvé."
    }
}