#!/bin/bash

# Script de inicialización rápida para desarrollo

echo "===== Configuración del proyecto ====="
echo ""

# Crear entorno virtual si no existe
if [ ! -d "venv" ]; then
    echo "Creando entorno virtual..."
    python -m venv venv
    echo ""
fi

# Activar entorno
echo "Activando entorno virtual..."
source venv/bin/activate  # En Windows: venv\Scripts\activate
echo ""

# Instalar dependencias
echo "Instalando dependencias..."
pip install -r requirements.txt
echo ""

# Crear archivo .env si no existe
if [ ! -f ".env" ]; then
    echo "Creando archivo .env..."
    cp .env.example .env
    echo ""
fi

# Hacer migraciones
echo "Ejecutando migraciones..."
python manage.py makemigrations
python manage.py migrate
echo ""

# Crear datos de prueba
echo "Creando datos de prueba..."
python scripts/create_test_data.py
echo ""

# Generar archivos de ejemplo
echo "Generando archivos de ejemplo..."
cd scripts
python generate_sample_excel.py
cd ..
echo ""

echo "===== ¡Configuración completada! ====="
echo ""
echo "Para ejecutar el servidor:"
echo "  python manage.py runserver"
echo ""
echo "Accede a:"
echo "  - Admin: http://localhost:8000/admin/"
echo "  - API: http://localhost:8000/api/"
echo ""
echo "Credenciales de prueba:"
echo "  - Usuario: admin"
echo "  - Contraseña: admin123456"
echo ""
