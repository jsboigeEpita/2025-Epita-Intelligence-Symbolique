@echo OFF
REM Script pour lancer les tests E2E Pytest dans un environnement Conda correctement activé.

REM Récupérer le nom de l'environnement depuis la variable d'environnement CONDA_ENV_NAME_TO_ACTIVATE
IF NOT DEFINED CONDA_ENV_NAME_TO_ACTIVATE (
    echo [RUN_E2E_TESTS.BAT] ERREUR: La variable d'environnement CONDA_ENV_NAME_TO_ACTIVATE n'est pas définie.
    EXIT /B 1
)
SET CONDA_ENV_NAME=%CONDA_ENV_NAME_TO_ACTIVATE%

REM Chemin vers l'installation de Conda - à ajuster si nécessaire
SET CONDA_PATH=C:\Users\MYIA\miniconda3

REM Activer l'environnement en utilisant le hook de Conda
CALL %CONDA_PATH%\Scripts\activate.bat %CONDA_ENV_NAME%

REM Afficher des informations de débogage pour vérifier l'environnement
echo [RUN_E2E_TESTS.BAT] Python executable:
where python
echo [RUN_E2E_TESTS.BAT] Conda environment: %CONDA_DEFAULT_ENV%

REM Exécuter la commande pytest passée en arguments.
REM Pas de SHIFT nécessaire, car le nom de l'env n'est plus dans les arguments.
echo [RUN_E2E_TESTS.BAT] Executing: python %*
python %*

REM Capturer le code de sortie de pytest
EXIT /B %ERRORLEVEL%