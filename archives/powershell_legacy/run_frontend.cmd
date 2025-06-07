@echo off
echo "Changing directory to frontend and starting npm..."
cd "%~dp0..\services\web_api\interface-web-argumentative"
if not [%1]==[] (
  echo "Attempting to start frontend on port %1"
  set PORT=%1
) else (
  echo "No port specified, using default (usually 3000 or as set in .env for React)."
)
npm start