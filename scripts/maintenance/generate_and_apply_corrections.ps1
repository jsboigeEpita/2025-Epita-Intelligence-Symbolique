$projectRoot = "d:/2025-Epita-Intelligence-Symbolique-4"
$obsoleteRefsRaw = powershell -c "& '$projectRoot/scripts/find_obsolete_test_references.ps1'"

$lines = $obsoleteRefsRaw -split [System.Environment]::NewLine
$i = 0
$correctionsCount = 0
$notFound = @()
$multipleFound = @()

while ($i -lt $lines.Length) {
    if ($lines[$i] -match "Référence obsolète trouvée :") {
        $fileLine = $lines[$i+1]
        $refLine = $lines[$i+2]
        
        if ($fileLine -match "Dans le fichier : (.*)" -and $refLine -match "Référence       : (.*)") {
            $markdownFileRaw = $matches[1].Trim()
            $obsoleteRef = $matches[1].Trim()
            
            $markdownFile = [System.IO.Path]::GetFullPath([System.IO.Path]::Combine($projectRoot, $markdownFileRaw.TrimStart('\/')))
            
            if (-not (Test-Path $markdownFile)) {
                Write-Warning "Fichier Markdown introuvable: $markdownFile"
                $i += 4
                continue
            }

            $obsoleteFileName = [System.IO.Path]::GetFileName($obsoleteRef)
            $newTestFiles = Get-ChildItem -Path "$projectRoot/tests" -Recurse -Name -Filter $obsoleteFileName
            
            if ($newTestFiles.Count -eq 1) {
                $newTestPath = Join-Path -Path "$projectRoot/tests" -ChildPath $newTestFiles[0]
                $markdownDir = [System.IO.Path]::GetDirectoryName($markdownFile)
                
                $newRelativePath = (Resolve-Path -Path $newTestPath -Relative -To $markdownDir).Replace('.\', '')

                $content = Get-Content $markdownFile -Raw
                $newContent = $content.Replace($obsoleteRef, $newRelativePath.Replace('\', '/'))
                if ($content -ne $newContent) {
                    Set-Content -Path $markdownFile -Value $newContent
                    Write-Host "Remplacement effectué dans '$markdownFile': '$obsoleteRef' -> '$newRelativePath'"
                    $correctionsCount++
                }
            } elseif ($newTestFiles.Count -gt 1) {
                $multipleFound += @{ File = $markdownFile; Obsolete = $obsoleteRef }
            } else {
                $notFound += @{ File = $markdownFile; Obsolete = $obsoleteRef }
            }
        }
        $i += 4
    } else {
        $i++
    }
}

Write-Host "`n--- Rapport final ---"
Write-Host "Corrections appliquées : $correctionsCount"
if ($notFound.Count -gt 0) {
    Write-Host "`nRéférences non trouvées :"
    $notFound | Format-Table
}
if ($multipleFound.Count -gt 0) {
    Write-Host "`nRéférences avec correspondances multiples :"
    $multipleFound | Format-Table
}