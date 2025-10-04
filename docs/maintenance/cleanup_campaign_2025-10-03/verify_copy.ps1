# Script de vérification de la copie de documentation
Write-Host "=== Vérification Copie Documentation ===" -ForegroundColor Cyan

$sourcePath = ".temp/cleanup_campaign_2025-10-03"
$destPath = "docs/maintenance/cleanup_campaign_2025-10-03"

$sourceFiles = Get-ChildItem -Path $sourcePath -Recurse -File
$destFiles = Get-ChildItem -Path $destPath -Recurse -File | Where-Object { $_.Name -ne "verify_copy.ps1" }

Write-Host "`nSource: $($sourceFiles.Count) fichiers"
Write-Host "Destination: $($destFiles.Count) fichiers"

if ($sourceFiles.Count -eq $destFiles.Count) {
    Write-Host "`n✅ Tous les fichiers copiés correctement" -ForegroundColor Green
} else {
    Write-Host "`n⚠️ Fichiers manquants: $($sourceFiles.Count - $destFiles.Count)" -ForegroundColor Yellow
}

Write-Host "`nFichiers dans docs/maintenance/cleanup_campaign_2025-10-03/:"
$destFiles | ForEach-Object {
    $relativePath = $_.FullName.Replace("$PWD\docs\maintenance\cleanup_campaign_2025-10-03\", "")
    Write-Host "  - $relativePath" -ForegroundColor Gray
}