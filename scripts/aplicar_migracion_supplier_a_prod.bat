@echo off
setlocal ENABLEDELAYEDEXPANSION
cd /d "%~dp0.."
set PY=venv\Scripts\python.exe
set DB_ENGINE=postgres
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

if not exist "%PY%" ( echo ERROR: Python venv no encontrado & exit /b 1 )

echo.
echo === MIGRACION 0016: Supplier + VehicleCost date/supplier ===
echo Aplica en PROD:
echo   - Nueva tabla core_supplier
echo   - Nueva columna core_vehiclecost.date (nullable)
echo   - Nueva columna core_vehiclecost.supplier_id (FK, nullable)
echo Datos existentes NO se tocan (todos los campos nuevos son nullable).
echo.
set /p OK="Tipea 'EMPEZAR' para arrancar: "
if /I NOT "%OK%"=="EMPEZAR" ( exit /b 0 )

if not exist backups ( mkdir backups )
for /f "delims=" %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set BKPTS=%%I
set BACKUP=backups\prod_pre_migracion_supplier_!BKPTS!.json
echo Backup: %BACKUP%
%PY% manage.py dumpdata --skip-checks core --exclude core.VehicleCost --exclude core.Supplier --indent=2 --natural-primary --natural-foreign > "%BACKUP%"
if errorlevel 1 ( echo Backup fallo & exit /b 1 )
pause

echo === MIGRATE ===
%PY% manage.py migrate --skip-checks
if errorlevel 1 ( echo Migrate fallo & exit /b 1 )

echo.
echo LISTO. Backup: %BACKUP%
echo Los cambios se propagan a Render al proximo deploy (main branch).
endlocal
