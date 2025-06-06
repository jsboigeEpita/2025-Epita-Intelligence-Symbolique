@echo off
echo "Starting backend server..."

set "PYTHON_SCRIPT_PATH=%~dp0..\argumentation_analysis\services\web_api\start_api.py"
set "ARGS="

if not [%1]==[] (
  echo "Attempting to start backend on port %1"
  set "ARGS=--port %1"
) else (
  echo "No port specified, using default (usually 5000 as set in start_api.py)."
)

python "%PYTHON_SCRIPT_PATH%" %ARGS%