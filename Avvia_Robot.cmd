@echo off
cd /d "%~dp0"
if exist "LaboratorioRobot.exe" (
    start "" "LaboratorioRobot.exe"
    exit /b
)
python main.py
if errorlevel 1 (
    echo.
    echo Per il sorgente servono Python 3.10 o successivo e Pygame.
    echo Installa Pygame con: python -m pip install -r requirements.txt
    echo Oppure estrai lo ZIP Windows e avvia LaboratorioRobot.exe.
    pause
)
