@echo off
echo ========================================================
echo   P25 Traffic Orchestration Network - Git Setup & Push
echo   Target Repo: https://github.com/swathi098-lgtm/multi-agent-traffic-orchestration.git
echo ========================================================
echo.

:: Check for git executable in PATH or Program Files
set "GIT_CMD=git"
if exist "C:\Program Files\Git\cmd\git.exe" set "GIT_CMD=C:\Program Files\Git\cmd\git.exe"
if exist "%LOCALAPPDATA%\Programs\Git\cmd\git.exe" set "GIT_CMD=%LOCALAPPDATA%\Programs\Git\cmd\git.exe"

"%GIT_CMD%" --version >nul 2>nul
if %errorlevel% neq 0 (
    echo [!] Git is not installed yet on your system.
    echo [!] Downloading Git installer setup page...
    start https://git-scm.com/download/win
    echo.
    echo Please install Git from the opened webpage, then run this batch file again!
    pause
    exit /b
)

echo [+] Configuring Git user identity as Swathi...
"%GIT_CMD%" config --global user.name "swathi098-lgtm"

echo [+] Initializing Git Repository...
"%GIT_CMD%" init
"%GIT_CMD%" branch -M main
"%GIT_CMD%" add .
"%GIT_CMD%" commit -m "Initial Commit: P25 Dynamic Multi-Modal Traffic Orchestration Network"

set REPO_URL=https://github.com/swathi098-lgtm/multi-agent-traffic-orchestration.git

"%GIT_CMD%" remote remove origin 2>nul
"%GIT_CMD%" remote add origin %REPO_URL%

echo.
echo [+] Pushing code to %REPO_URL%...
"%GIT_CMD%" push -u origin main

echo.
echo ========================================================
echo [+] Successfully pushed to GitHub!
echo ========================================================
pause
