@echo off
title F76 Price Guide - Build
echo ============================================
echo  F76 Price Guide - Full Build
echo ============================================
echo.

:: ── Config ───────────────────────────────────────────────────────────────────
set PYTHON=C:\Python314\python.exe
set PYINSTALLER=C:\Python314\Scripts\pyinstaller.exe
set INNO="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
set SPEC=F76PriceGuide.spec
set ISS=Pack.iss

:: ── Sanity checks ─────────────────────────────────────────────────────────────
if not exist "%PYTHON%" (
    echo [ERROR] Python not found at %PYTHON%
    echo         Edit PYTHON= at the top of this bat to match your install.
    pause & exit /b 1
)
if not exist "%SPEC%" (
    echo [ERROR] %SPEC% not found. Run this bat from the TRADES folder.
    pause & exit /b 1
)
if not exist "app.ico" (
    echo [ERROR] app.ico not found. Must be in the same folder.
    pause & exit /b 1
)

:: ── Step 1: Clean old build artifacts ────────────────────────────────────────
echo [1/4] Cleaning old build...
if exist build   rmdir /s /q build
if exist dist    rmdir /s /q dist
if exist Output  rmdir /s /q Output
echo       Done.
echo.

:: ── Step 2: Install / update dependencies ────────────────────────────────────
echo [2/4] Updating dependencies...
"%PYTHON%" -m pip install --quiet --upgrade pyinstaller customtkinter pillow rapidfuzz py7zr requests
echo       Done.
echo.

:: ── Step 3: PyInstaller ───────────────────────────────────────────────────────
echo [3/4] Building exe with PyInstaller...
"%PYINSTALLER%" %SPEC%
if errorlevel 1 (
    echo.
    echo [ERROR] PyInstaller failed. See output above.
    pause & exit /b 1
)
if not exist "dist\F76PriceGuide.exe" (
    echo [ERROR] dist\F76PriceGuide.exe not found after build.
    pause & exit /b 1
)
echo       dist\F76PriceGuide.exe created OK.
echo.

:: ── Step 4: Inno Setup installer ─────────────────────────────────────────────
echo [4/4] Building installer with Inno Setup...
if not exist %INNO% (
    echo [SKIP] Inno Setup not found at %INNO%
    echo        Install Inno Setup 6 or update the INNO= path to build the installer.
    echo        The exe is ready at: dist\F76PriceGuide.exe
    goto :done
)
%INNO% %ISS%
if errorlevel 1 (
    echo.
    echo [ERROR] Inno Setup failed. See output above.
    pause & exit /b 1
)
echo       Output\F76TradeGuide_Installer.exe created OK.

:done
echo.
echo ============================================
echo  Build complete!
echo  EXE:       dist\F76PriceGuide.exe
echo  Installer: Output\F76TradeGuide_Installer.exe
echo ============================================
echo.
pause
