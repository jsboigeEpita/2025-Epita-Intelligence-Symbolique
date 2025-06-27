@echo off
setlocal

set "CONDA_ENV_NAME_TO_ACTIVATE=projet-is"
if defined CONDA_ENV_NAME (
    set "CONDA_ENV_NAME_TO_ACTIVATE=%CONDA_ENV_NAME%"
)

set "CONDA_PATH=C:\Tools\miniconda3"

call "%CONDA_PATH%\Scripts\activate.bat" "%CONDA_ENV_NAME_TO_ACTIVATE%"
if errorlevel 1 (
    echo [RUN_E2E_TESTS.BAT] ERROR: Failed to activate Conda environment '%CONDA_ENV_NAME_TO_ACTIVATE%'.
    exit /b 1
)

echo [RUN_E2E_TESTS.BAT] Conda environment '%CONDA_ENV_NAME_TO_ACTIVATE%' activated.
echo [RUN_E2E_TESTS.BAT] Executing: python %*

python %*

endlocal