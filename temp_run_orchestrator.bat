@echo off
echo Activation de l'environnement Conda projet-is...
call C:\Users\MYIA\miniconda3\condabin\conda.bat activate projet-is
if %errorlevel% neq 0 (
    echo ERREUR: L'activation de Conda a echoue.
    exit /b %errorlevel%
)
echo Lancement de l'orchestrateur Python...
C:\Users\MYIA\miniconda3\envs\projet-is\python.exe -m project_core.webapp_from_scripts.unified_web_orchestrator --integration --config config/webapp_config.yml
if %errorlevel% neq 0 (
    echo ERREUR: L'execution du script Python a echoue.
    exit /b %errorlevel%
)
echo Script termine.