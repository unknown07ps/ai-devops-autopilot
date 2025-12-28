@echo on
echo =====================================
echo   AI DevOps Autopilot - Git Push (DEBUG)
echo =====================================

echo Current directory before cd:
cd

echo.
echo Switching to script directory...
cd /d "%~dp0"

echo.
echo Current directory after cd:
cd

echo.
echo Checking if this is a git repo...
git rev-parse --is-inside-work-tree
IF %ERRORLEVEL% NEQ 0 (
    echo  ERROR: This is NOT a git repository.
    pause
    exit /b
)

echo.
echo Git status:
git status

echo.
set /p COMMIT_MSG="Enter commit message: "

echo.
echo Adding files...
git add .

echo.
echo Committing...
git commit -m "%COMMIT_MSG%"

echo.
echo Pushing to origin main...
git push origin main

echo.
echo  Script finished.
pause
