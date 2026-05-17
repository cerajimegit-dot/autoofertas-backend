@echo off
REM Migracion DIRECTA SQLite -> Postgres (sin dumpdata)
REM Asume que `migrate` ya creo el schema en Postgres

cd /d %~dp0..\..

if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

REM Asegurar que el schema esta creado en Postgres
set DB_ENGINE=postgres
echo Asegurando schema en Postgres (migrate)...
python manage.py migrate --noinput
if errorlevel 1 (
    echo ERROR en migrate
    pause
    exit /b 1
)

REM Reset DB_ENGINE para no afectar la sesion del usuario
set DB_ENGINE=

echo.
echo Copiando datos...
python scripts\migracion\direct_copy_to_postgres.py
if errorlevel 1 (
    echo ERROR en copia
    pause
    exit /b 1
)

echo.
echo === COPIA OK ===
echo Para usar Postgres edita .env y pone:
echo   DB_ENGINE=postgres
pause
