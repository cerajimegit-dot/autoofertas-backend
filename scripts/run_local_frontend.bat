@echo off
REM ============================================================
REM Levanta el frontend apuntando al backend LOCAL (no Render).
REM
REM Uso:
REM   1) En otra terminal: scripts\run_local.bat   (backend en :8001)
REM   2) Aquí:             scripts\run_local_frontend.bat
REM
REM Abre Python http.server en el puerto 8000 sirviendo la carpeta
REM playa-frontend\. La app detecta window.API_BASE_URL en config.js;
REM config.local.js (generado abajo) lo sobreescribe a localhost.
REM ============================================================

cd /d %~dp0..\..\playa-frontend

REM Generamos config.js apuntando a backend local. Se sobreescribe
REM cada vez para que no haya drift entre el .gitignore'd y el remoto.
echo // GENERADO POR run_local_frontend.bat - apunta al backend local. > config.js
echo window.API_BASE_URL = 'http://localhost:8001/api'; >> config.js

echo === Frontend AUTO OFERTAS local ===
echo URL:     http://localhost:8000/
echo Backend: http://localhost:8001/api/
echo.
echo NOTA: cuando termines de testear y quieras volver a prod, restaurá
echo       config.js con: window.API_BASE_URL = 'https://playa-backend.onrender.com/api';
echo.

python -m http.server 8000
