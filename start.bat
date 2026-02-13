@echo off
title Assessment Ops Mini Platform
color 0A

echo.
echo  ============================================
echo   Assessment Ops Mini Platform - Quick Start
echo  ============================================
echo.

:: Check if PostgreSQL is available
where psql >nul 2>&1
if %errorlevel% neq 0 (
    set "PGBIN=C:\Program Files\PostgreSQL\16\bin"
    if exist "!PGBIN!\psql.exe" (
        set "PATH=!PGBIN!;%PATH%"
    ) else (
        echo [!] PostgreSQL not found in PATH.
        echo     Please install PostgreSQL 16 or add it to PATH.
        pause
        exit /b 1
    )
)

:: Enable delayed expansion for variables inside blocks
setlocal enabledelayedexpansion

set "PGBIN=C:\Program Files\PostgreSQL\16\bin"
if exist "%PGBIN%\psql.exe" (
    set "PATH=%PGBIN%;%PATH%"
)

set "DB_USER=assessment"
set "DB_PASS=assessment123"
set "DB_NAME=assessment_db"
set "DB_HOST=localhost"
set "DB_PORT=5432"
set "DATABASE_URL=postgresql://%DB_USER%:%DB_PASS%@%DB_HOST%:%DB_PORT%/%DB_NAME%"
set "BACKEND_PORT=8000"

echo [1/6] Checking PostgreSQL service...
sc query postgresql-x64-16 | findstr "RUNNING" >nul 2>&1
if %errorlevel% neq 0 (
    echo       Starting PostgreSQL service...
    net start postgresql-x64-16 >nul 2>&1
    timeout /t 3 >nul
)
echo       PostgreSQL is running.
echo.

echo [2/6] Setting up database...
set "PGPASSWORD=postgres"
psql -U postgres -tc "SELECT 1 FROM pg_roles WHERE rolname='%DB_USER%'" | findstr "1" >nul 2>&1
if %errorlevel% neq 0 (
    echo       Creating user '%DB_USER%'...
    psql -U postgres -c "CREATE USER %DB_USER% WITH PASSWORD '%DB_PASS%';" >nul 2>&1
)
psql -U postgres -tc "SELECT 1 FROM pg_database WHERE datname='%DB_NAME%'" | findstr "1" >nul 2>&1
if %errorlevel% neq 0 (
    echo       Creating database '%DB_NAME%'...
    psql -U postgres -c "CREATE DATABASE %DB_NAME% OWNER %DB_USER%;" >nul 2>&1
    psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE %DB_NAME% TO %DB_USER%;" >nul 2>&1
)
echo       Database ready.
echo.

echo [3/6] Installing backend dependencies...
cd backend
if not exist "venv" (
    python -m venv venv >nul 2>&1
)
call venv\Scripts\activate.bat >nul 2>&1
pip install -r requirements.txt -q >nul 2>&1
echo       Backend dependencies installed.
echo.

echo [4/6] Running database migrations...
set "DATABASE_URL=%DATABASE_URL%"
alembic upgrade head >nul 2>&1
echo       Migrations complete.
echo.

cd ..

echo [5/6] Installing frontend dependencies...
cd frontend
if not exist "node_modules" (
    call npm install --silent >nul 2>&1
)
echo       Frontend dependencies installed.
echo.
cd ..

echo [6/6] Starting services...
echo.
echo  ============================================
echo   Starting Backend  : http://localhost:%BACKEND_PORT%
echo   Starting Frontend : http://localhost:5173
echo   API Docs          : http://localhost:%BACKEND_PORT%/docs
echo  ============================================
echo.
echo   Press Ctrl+C in each window to stop.
echo.

:: Start backend in a new terminal
start "Assessment Ops - Backend" cmd /k "cd backend && call venv\Scripts\activate.bat && set DATABASE_URL=%DATABASE_URL% && uvicorn app.main:app --reload --host 127.0.0.1 --port %BACKEND_PORT%"

:: Wait for backend to start
echo  Waiting for backend to start...
timeout /t 4 >nul

:: Start frontend in a new terminal
start "Assessment Ops - Frontend" cmd /k "cd frontend && npm run dev"

:: Wait for frontend to start
timeout /t 3 >nul

echo.
echo  ============================================
echo   All services started!
echo  ============================================
echo.
echo   Frontend : http://localhost:5173
echo   Backend  : http://localhost:%BACKEND_PORT%
echo   API Docs : http://localhost:%BACKEND_PORT%/docs
echo.

:: Open browser
start http://localhost:5173

echo   Press any key to stop all services...
pause >nul

:: Kill the spawned processes
taskkill /FI "WINDOWTITLE eq Assessment Ops - Backend*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Assessment Ops - Frontend*" /F >nul 2>&1

echo.
echo   Services stopped. Goodbye!
endlocal
