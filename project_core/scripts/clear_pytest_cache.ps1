if (Test-Path -Path .\.pytest_cache -PathType Container) {
    Remove-Item -Recurse -Force .\.pytest_cache
    Write-Host "Le cache de pytest a été supprimé."
} else {
    Write-Host "Le cache de pytest n'existait pas."
}