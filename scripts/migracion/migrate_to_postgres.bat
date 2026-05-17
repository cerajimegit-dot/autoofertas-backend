@echo off
REM Migracion SQLite -> Postgres (Supabase)
REM Se ejecuta desde la raiz del proyecto playa/

cd /d %~dp0..\..
echo Working dir: %CD%

REM Activar venv si existe
if exist venv\Scripts\activate.bat (
    echo Activando venv...
    call venv\Scripts\activate.bat
)

REM Instalar dependencias nuevas
echo.
echo Instalando psycopg2-binary y dj-database-url...
pip install psycopg2-binary==2.9.10 dj-database-url==2.3.0

REM Ejecutar migracion
python scripts\migracion\migrate_to_postgres.py
if errorlevel 1 (
    echo.
    echo === ERROR EN MIGRACION ===
    pause
    exit /b 1
)

echo.
echo === MIGRACION OK ===
echo Para usar Postgres edita .env y pone:
echo   DB_ENGINE=postgres
echo.
pause
