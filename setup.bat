@echo off
REM Script de inicialización rápida para Windows

echo ===== Configuración del proyecto =====
echo.

REM Crear entorno virtual si no existe
if not exist "venv" (
    echo Creando entorno virtual...
    python -m venv venv
    echo.
)

REM Activar entorno
echo Activando entorno virtual...
call venv\Scripts\activate.bat
echo.

REM Instalar dependencias
echo Instalando dependencias...
pip install -r requirements.txt
echo.

REM Crear archivo .env si no existe
if not exist ".env" (
    echo Creando archivo .env...
    copy .env.example .env
    echo.
)

REM Hacer migraciones
echo Ejecutando migraciones...
python manage.py makemigrations
python manage.py migrate
echo.

REM Crear datos de prueba
echo Creando datos de prueba...
python scripts\create_test_data.py
echo.

REM Generar archivos de ejemplo
echo Generando archivos de ejemplo...
cd scripts
python generate_sample_excel.py
cd ..
echo.

echo ===== ¡Configuración completada! =====
echo.
echo Para ejecutar el servidor:
echo   python manage.py runserver
echo.
echo Accede a:
echo   - Admin: http://localhost:8000/admin/
echo   - API: http://localhost:8000/api/
echo.
echo Credenciales de prueba:
echo   - Usuario: admin
echo   - Contraseña: admin123456
echo.
pause
