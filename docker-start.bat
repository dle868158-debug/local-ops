@echo off
REM Quick start script for local-console Docker

echo.
echo ============================================
echo   Local Console - Docker Quick Start
echo ============================================
echo.

REM Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo Error: Docker is not installed or not in PATH
    echo Please install Docker Desktop from https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

echo [1/3] Building Docker image...
docker build -t local-console:latest . >nul 2>&1
if errorlevel 1 (
    echo Build failed!
    docker build -t local-console:latest .
    pause
    exit /b 1
)
echo [OK] Image built successfully

echo.
echo [2/3] Starting container...
docker-compose down >nul 2>&1
docker-compose up -d
if errorlevel 1 (
    echo Failed to start container
    docker-compose up
    pause
    exit /b 1
)
echo [OK] Container started

echo.
echo [3/3] Waiting for service to be ready...
timeout /t 3 /nobreak >nul

echo.
echo ============================================
echo   Console is ready!
echo ============================================
echo.
echo Access the console at: http://localhost:9600
echo.
echo Useful commands:
echo   - View logs:     docker-compose logs -f
echo   - Stop service:  docker-compose down
echo   - Restart:       docker-compose restart
echo.
pause
