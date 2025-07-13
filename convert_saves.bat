@echo off
echo Xbox Game Pass to Steam Save Converter
echo For Warhammer 40000 Rogue Trader
echo.
echo Starting conversion...
echo.

where uv >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo uv is required but not installed.
    choice /C YN /M "Do you want to install uv now"
    if %ERRORLEVEL% NEQ 1 (
        echo Installation cancelled. Exiting...
        pause
        exit /b 1
    )
    
    echo For manual installation visit https://docs.astral.sh/uv/getting-started/installation/ for instructions
    echo Installing uv...
    
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    
    echo.
    echo =========================================================
    echo You must relaunch this script after uv is installed.
    echo =========================================================
    pause
    )

    echo uv has been installed successfully.
) 
echo.

uv run .\RTwgs2steam.py -i