"""Views públicas — sin autenticación.

Contiene el endpoint del catálogo público autogenerado por enterprise:
    GET /public/catalogo/{slug}/

Devuelve lista de vehículos disponibles con datos limitados (sin fob,
sin gastos, sin ganancia — solo lo que sirve al comprador).
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from core.models import Enterprise, Vehicle
from core.models.inventory import VehicleImage


@api_view(['GET'])
@permission_classes([AllowAny])
def public_catalog(request, slug):
    """Catálogo público de una empresa por slug."""
    enterprise = get_object_or_404(Enterprise, slug=slug)
    vehicles = Vehicle.objects.filter(
        enterprise=enterprise, state='available',
    ).select_related('brand', 'model', 'branch').order_by('-created_at')

    data = []
    for v in vehicles:
        # Foto principal: primera de VehicleImage o Vehicle.image legacy
        images = VehicleImage.objects.filter(vehicle=v).order_by('order', 'id')
        main_image = None
        if images.exists():
            main_image = request.build_absolute_uri(images.first().image.url)
        elif v.image:
            main_image = request.build_absolute_uri(v.image.url)

        data.append({
            'id': v.id,
            'brand': v.brand.name if v.brand else '',
            'model': v.model.name if v.model else '',
            'year': v.year,
            'color': v.color or '',
            'mileage': v.mileage,
            'price': str(v.price) if v.price and float(v.price) > 0 else None,
            'currency': v.currency,
            'image_url': main_image,
            'branch': v.branch.name if v.branch else '',
        })

    return Response({
        'enterprise': {
            'name': enterprise.name,
            'phone': enterprise.phone,
            'email': enterprise.email,
            'city': enterprise.city,
        },
        'vehicles': data,
        'total': len(data),
    })
