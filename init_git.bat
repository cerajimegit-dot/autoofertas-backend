@echo off
setlocal
cd /d "%~dp0"

echo.
echo ============================================
echo  Inicializando repositorio git Playas Autos
echo ============================================
echo.

REM Limpiar cualquier intento anterior fallido
if exist ".git" rmdir /s /q .git

REM Inicializar
git init -b main
if errorlevel 1 goto :nogit

REM Configuracion local del repo
git config user.email "leticia.jimenezdc@gmail.com"
git config user.name "Leticia"

echo.
echo Agregando archivos al primer commit...
git add .
git status --short
echo.

git commit -m "Initial commit - migraciones, sucursales y modulo admin"
if errorlevel 1 goto :nocommit

REM Crear branch develop
git branch develop

echo.
echo ============================================
echo  Repositorio inicializado correctamente
echo ============================================
echo.
echo Branches disponibles:
git branch
echo.
echo Comandos utiles:
echo   git status        Ver cambios pendientes
echo   git add .         Agregar todos los cambios
echo   git commit -m m   Confirmar cambios
echo   git log --oneline Ver historial
echo.
goto :end

:nogit
echo.
echo ERROR: git no esta instalado o no esta en el PATH.
echo Descargalo de https://git-scm.com/download/win
goto :end

:nocommit
echo.
echo ERROR al hacer el commit. Revisa el output arriba.
goto :end

:end
pause
