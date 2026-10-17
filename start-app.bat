@echo off
setlocal
echo ====================================================
echo  OpenPhysicalAI Lab - Windows Launcher
echo ====================================================

call "%USERPROFILE%\miniconda3\Scripts\activate.bat" thermo_agent 2>nul
if errorlevel 1 (
    echo [INFO] Using detected Python / venv environment...
) else (
    echo [INFO] Activated conda environment: thermo_agent
)

echo [INFO] Starting Electron desktop app...
npm start
