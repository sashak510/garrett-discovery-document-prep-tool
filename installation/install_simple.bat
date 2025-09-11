@echo off
echo =============================================
echo Garrett Discovery Document Prep Tool
echo Simple Installer - Python 3.13+ Required
echo =============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ ERROR: Python is not installed or not in PATH
    echo.
    echo Please install Python 3.13+ first:
    echo 1. Go to python.org
    echo 2. Download Python 3.13 or newer
    echo 3. During installation, CHECK "Add Python to PATH"
    echo 4. Run this installer again
    echo.
    pause
    exit /b 1
)

echo ✅ Python found! Starting installation...
echo.

REM Run the Python installation script
python install_demo.py

echo.
echo 🎉 Installation complete!
echo.
pause
