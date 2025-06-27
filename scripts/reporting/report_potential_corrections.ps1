$projectRoot = "d:/2025-Epita-Intelligence-Symbolique-4"
$obsoleteRefsRaw = powershell -c "& '$projectRoot/scripts/find_obsolete_test_references.ps1'"

$lines = $obsoleteRefsRaw -split [System.Environment]::NewLine
$i = 0
$potentialCorrections = @()

while ($i -lt $lines.Length) {
    if ($lines[$i] -match "Référence obsolète trouvée :") {
        $fileLine = $lines[$i+1]
        $refLine = $lines[$i+2]
        
        if ($fileLine -match "Dans le fichier : (.*)" -and $refLine -match "Référence       : (.*)") {
            $markdownFileRaw = $matches[1].Trim()
            $obsoleteRef = $matches[1].Trim()
            
            $markdownFile = [System.IO.Path]::GetFullPath([System.IO.Path]::Combine($projectRoot, $markdownFileRaw.TrimStart('\/')))
            
            if (-not (Test-Path $markdownFile)) {
                $potentialCorrections += [pscustomobject]@{
                    MarkdownFile = $markdownFileRaw
                    ObsoleteRef = $obsoleteRef
                    NewRef = "Fichier Markdown introuvable"
                    Status = "Erreur"
                }
                $i += 4
                continue
            }

            $obsoleteFileName = [System.IO.Path]::GetFileName($obsoleteRef)
            $newTestFiles = Get-ChildItem -Path "$projectRoot/tests" -Recurse -Name -Filter $obsoleteFileName
            
            if ($newTestFiles.Count -eq 1) {
                $newTestPath = Join-Path -Path "$projectRoot/tests" -ChildPath $newTestFiles[0]
                $markdownDir = [System.IO.Path]::GetDirectoryName($markdownFile)
                
                $newRelativePath = (Resolve-Path -Path $newTestPath -Relative -To $markdownDir).Replace('.\', '')

                $potentialCorrections += [pscustomobject]@{
                    MarkdownFile = $markdownFileRaw
                    ObsoleteRef = $obsoleteRef
                    NewRef = $newRelativePath.Replace('\', '/')
                    Status = "Prêt"
                }
            } elseif ($newTestFiles.Count -gt 1) {
                $potentialCorrections += [pscustomobject]@{
                    MarkdownFile = $markdownFileRaw
                    ObsoleteRef = $obsoleteRef
                    NewRef = "Correspondances multiples"
                    Status = "Ignoré"
                }
            } else {
                $potentialCorrections += [pscustomobject]@{
                    MarkdownFile = $markdownFileRaw
                    ObsoleteRef = $obsoleteRef
                    NewRef = "Aucune correspondance"
                    Status = "Ignoré"
                }
            }
        }
        $i += 4
    } else {
        $i++
    }
}

$potentialCorrections | Export-Csv -Path "$projectRoot/scripts/corrections_report.csv" -NoTypeInformation -Encoding UTF8
Write-Host "Rapport de corrections potentielles généré dans scripts/corrections_report.csv"