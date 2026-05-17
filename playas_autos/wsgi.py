"""
WSGI config for playas_autos project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'playas_autos.settings')

application = get_wsgi_application()
