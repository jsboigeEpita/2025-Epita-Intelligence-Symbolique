Write-Host "--- Debug Info Start ---"
Write-Host "CONDA_DEFAULT_ENV: $env:CONDA_DEFAULT_ENV"
Write-Host "CONDA_PREFIX: $env:CONDA_PREFIX"
Write-Host "PYTHONPATH: $env:PYTHONPATH"
conda env list
Write-Host "--- Debug Info End ---"
pytest