@echo off
echo ========================================
echo KDTPS Error Manager - Build Script
echo ========================================
echo.

REM Check Python
python --version 2>nul
if errorlevel 1 (
    echo ERROR: Python not found!
    pause
    exit /b 1
)

REM Install PyInstaller if needed
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

echo.
echo Building executable...
echo.

REM Build with spec file
pyinstaller kdtps.spec --clean --noconfirm

if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo BUILD SUCCESSFUL!
echo ========================================
echo.
echo Output: dist\KDTPS_Error_Manager.exe
echo.

REM Copy additional files to dist
if not exist "dist\data" mkdir "dist\data"
copy "data\ai_settings.json" "dist\data\" >nul 2>&1

echo Ready to run!
pause
