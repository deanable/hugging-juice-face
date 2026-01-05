@echo off
setlocal

REM Check if PyInstaller is installed
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo PyInstaller not found. Installing...
    pip install pyinstaller
)

REM Clean previous builds
if exist "build" rd /s /q "build"
if exist "dist" rd /s /q "dist"

REM Build the application
echo Building 64-bit Windows Application...
pyinstaller --noconfirm --clean ^
    --name "AI_Image_Tagger" ^
    --windowed ^
    --onefile ^
    --icon "icon.ico" ^
    --add-data "config.py;." ^
    --add-data "logging_config.py;." ^
    --hidden-import "customtkinter" ^
    --hidden-import "PIL" ^
    --hidden-import "torch" ^
    --hidden-import "transformers" ^
    --collect-all "customtkinter" ^
    main.py

if %errorlevel% neq 0 (
    echo Build failed!
    exit /b %errorlevel%
)

echo Build complete! Executable is in the 'dist' folder.
pause
