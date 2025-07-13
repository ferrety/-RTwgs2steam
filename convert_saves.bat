@echo off
echo Xbox Game Pass to Steam Save Converter
echo For Warhammer 40000 Rogue Trader
echo.
echo Starting conversion...
echo.

REM Check if uv is installed
where uv >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo uv is required but not installed.
    set /p INSTALL_UV="Do you want to install uv now? (Y/N): "
    if /i "%INSTALL_UV%" NEQ "Y" (
        echo Installation cancelled. Exiting...
        pause
        exit /b 1
    )
    echo Installing uv...
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

    if %ERRORLEVEL% NEQ 0 (
        echo Failed to install uv. Please install it manually.
        echo Visit https://docs.astral.sh/uv/getting-started/installation/ for instractions
        exit /b 1
    )

    echo uv has been installed successfully.
) 
echo.

uv run .\RTwgs2steam.py -i

echo.
echo Conversion completed. Check the output above for any errors.
pause
