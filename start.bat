@echo off
setlocal enabledelayedexpansion
title Assessment Ops Mini Platform
color 0A

echo.
echo  ============================================
echo   Assessment Ops Mini Platform - Quick Start
echo  ============================================
echo.

:: ---- PostgreSQL PATH detection ----
where psql >nul 2>&1
if !errorlevel! neq 0 (
    for %%V in (16 17 18 15 14) do (
        if exist "C:\Program Files\PostgreSQL\%%V\bin\psql.exe" (
            set "PATH=C:\Program Files\PostgreSQL\%%V\bin;!PATH!"
            echo   [OK] Added PostgreSQL %%V to PATH.
            goto :pg_found
        )
    )
    echo   [X] PostgreSQL not found. Install it or add its bin folder to PATH.
    pause
    exit /b 1
)
:pg_found

:: ---- Config ----
set "DB_USER=assessment"
set "DB_PASS=assessment123"
set "DB_NAME=assessment_db"
set "DB_HOST=localhost"
set "DB_PORT=5432"
set "DB_URL=postgresql://assessment:assessment123@localhost:5432/assessment_db"
set "BACKEND_PORT=8000"

:: ---- 1. PostgreSQL service ----
echo   [1/6] Checking PostgreSQL...
sc query postgresql-x64-16 | findstr "RUNNING" >nul 2>&1
if !errorlevel! neq 0 (
    net start postgresql-x64-16 >nul 2>&1
    timeout /t 3 >nul
)
echo         PostgreSQL is running.

:: ---- 2. Database setup ----
echo   [2/6] Setting up database...
set "PGPASSWORD=postgres"
psql -U postgres -tc "SELECT 1 FROM pg_roles WHERE rolname='%DB_USER%'" | findstr "1" >nul 2>&1
if !errorlevel! neq 0 (
    psql -U postgres -c "CREATE USER %DB_USER% WITH PASSWORD '%DB_PASS%';" >nul 2>&1
)
psql -U postgres -tc "SELECT 1 FROM pg_database WHERE datname='%DB_NAME%'" | findstr "1" >nul 2>&1
if !errorlevel! neq 0 (
    psql -U postgres -c "CREATE DATABASE %DB_NAME% OWNER %DB_USER%;" >nul 2>&1
    psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE %DB_NAME% TO %DB_USER%;" >nul 2>&1
)
echo         Database ready.

:: ---- 3. Backend dependencies ----
echo   [3/6] Installing backend dependencies...
pushd backend
if not exist "venv" (
    python -m venv venv >nul 2>&1
)
call venv\Scripts\activate.bat >nul 2>&1
pip install -r requirements.txt -q >nul 2>&1
echo         Done.

:: ---- 4. Migrations ----
echo   [4/6] Running migrations...
set "DATABASE_URL=%DB_URL%"
alembic upgrade head >nul 2>&1
echo         Done.
popd

:: ---- 5. Frontend dependencies ----
echo   [5/6] Installing frontend dependencies...
pushd frontend
if not exist "node_modules" (
    call npm install --silent >nul 2>&1
)
echo         Done.
popd

:: ---- 6. Launch services ----
echo   [6/6] Starting services...
echo.
echo  ============================================
echo   Backend  : http://localhost:%BACKEND_PORT%
echo   Frontend : http://localhost:5173
echo   API Docs : http://localhost:%BACKEND_PORT%/docs
echo  ============================================
echo.

:: Start backend (quoted set to avoid trailing spaces)
start "Assessment Ops - Backend" cmd /k "cd /d "%~dp0backend" && call venv\Scripts\activate.bat && set "DATABASE_URL=postgresql://assessment:assessment123@localhost:5432/assessment_db" && uvicorn app.main:app --reload --host 127.0.0.1 --port %BACKEND_PORT%"

echo   Waiting for backend...
timeout /t 5 >nul

:: Start frontend
start "Assessment Ops - Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

timeout /t 4 >nul

echo.
echo  ============================================
echo   All services started!
echo  ============================================
echo.
echo   Frontend : http://localhost:5173
echo   Backend  : http://localhost:%BACKEND_PORT%
echo   API Docs : http://localhost:%BACKEND_PORT%/docs
echo.

start http://localhost:5173

echo   Press any key to stop all services...
pause >nul

taskkill /FI "WINDOWTITLE eq Assessment Ops - Backend*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Assessment Ops - Frontend*" /F >nul 2>&1

echo.
echo   Services stopped. Goodbye!
endlocal
