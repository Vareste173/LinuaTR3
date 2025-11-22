@echo off
echo [INFO] BAĞIMLILIKLER KONTROL EDİLİYOR...
WHERE cl >nul 2>&1 || ECHO [ERROR] Visual Studio Build Tools bulunamadı! Lütfen Visual Studio 2022 Build Tools'u yükleyin.
chcp 65001 >nul
echo [BUILD] FourYourLanguage C++ Overlay Building...
echo.

cd /d "%~dp0"

:: Check Visual Studio 2022
if exist "C:\Program Files\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" (
    call "C:\Program Files\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
) else if exist "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" (
    call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
) else (
    echo [ERROR] Visual Studio Build Tools not found!
    echo [INFO] Please install Visual Studio 2022 Build Tools
    pause
    exit /b 1
)

echo [INFO] Compiler check...
cl >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Visual Studio compiler not found!
    pause
    exit /b 1
)

echo [INFO] Compiler found! Building C++ code...

:: Build command
cl /std:c++17 /O2 /EHsc /I "." overlay.cpp ^
/link ws2_32.lib d2d1.lib dwrite.lib user32.lib gdi32.lib ^
/OUT:"overlay_app.exe" /MACHINE:X64

if %errorlevel% equ 0 (
    echo.
    echo [SUCCESS] Build completed! overlay_app.exe created.
    echo [INFO] You can now run: python main.py
) else (
    echo.
    echo [ERROR] Build failed!
    echo [DEBUG] Check overlay.cpp file and dependencies
)

pause