@echo off
REM ============================================================
REM Levanta el backend en modo "testing local con SQLite".
REM
REM Uso:
REM   scripts\run_local.bat
REM
REM Esto:
REM   - Fuerza DB_ENGINE=sqlite (ignora el DATABASE_URL de Supabase
REM     del .env). Asegura que NUNCA tocás producción al probar local.
REM   - Pone DEBUG=True para ver trazas detalladas.
REM   - Setea PYTHONUTF8=1 / PYTHONIOENCODING=utf-8 para evitar el
REM     bug de cp1252 en Windows con caracteres como '→' o '✓'.
REM   - Levanta runserver en el puerto 8001.
REM
REM El frontend se levanta aparte (ver scripts\run_local_frontend.bat).
REM ============================================================

set DB_ENGINE=sqlite
set DEBUG=True
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

cd /d %~dp0..
echo === Backend AUTO OFERTAS local ===
echo DB:      SQLite (db.sqlite3)
echo Modo:    DEBUG=True
echo URL:     http://localhost:8001/api/
echo Frontend a apuntar: window.API_BASE_URL = 'http://localhost:8001/api'
echo.

venv\Scripts\python.exe manage.py runserver 8001
