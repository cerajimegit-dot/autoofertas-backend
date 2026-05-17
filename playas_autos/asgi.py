"""
ASGI config for playas_autos project.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'playas_autos.settings')

application = get_asgi_application()
