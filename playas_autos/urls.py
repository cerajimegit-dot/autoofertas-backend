"""
URL Configuration for playas_autos project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # UI Routes
    path('', include('ui.urls')),
    
    # API Routes
    path('api/', include('core.urls')),

    # API Docs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# SaaS — sólo si está activado en settings. Mantiene AUTO OFERTAS
# limpio cuando SAAS_ENABLED=False (default).
if getattr(settings, 'SAAS_ENABLED', False):
    urlpatterns += [
        path('api/saas/', include('saas.urls')),
    ]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
