"""Endpoints SaaS: signup público + planes + estado de suscripción.

Todo está en /api/saas/. Algunos son públicos (signup, planes); otros
requieren JWT (mi suscripción, checkout).
"""

import secrets
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action, permission_classes, api_view, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from core.models import Enterprise, Branch
from core.throttling import RegisterRateThrottle
from .models import (
    Subscription, SignupRequest, PLAN_CHOICES, PLAN_LIMITS, PLAN_PRICES_USD,
)


User = get_user_model()


@api_view(['GET'])
@permission_classes([AllowAny])
def list_plans(request):
    """Catálogo de planes disponibles. Público — para la landing."""
    plans = [
        {
            'id': key,
            'name': label,
            'price_usd': PLAN_PRICES_USD.get(key, 0),
            'limits': PLAN_LIMITS.get(key, {}),
            'features': _plan_features(key),
        }
        for key, label in PLAN_CHOICES
    ]
    return Response({'plans': plans})


def _plan_features(plan_id):
    """Lista textual de "qué incluye" cada plan, para el pricing page."""
    base = [
        'Multi-sucursal',
        'Gestión de clientes y ventas',
        'Cuotas y cobranzas',
        'Flujo de caja',
        'Dashboard con KPIs',
        'Búsqueda fuzzy de clientes',
        'PDF de cronograma y dossier',
        'Audit log',
    ]
    if plan_id == 'trial':
        return base + ['14 días sin cargo', 'Sin tarjeta de crédito']
    if plan_id == 'starter':
        return base + ['Soporte por email', 'Backups semanales']
    if plan_id == 'pro':
        return base + ['Soporte prioritario', 'Backups diarios',
                       'Recordatorios automáticos por email',
                       'Reporte de comisiones por vendedor']
    if plan_id == 'enterprise':
        return base + ['Sin límites', 'SLA 99.9%', 'White-label',
                       'API access', 'Onboarding dedicado']
    return base


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([RegisterRateThrottle])
def public_signup(request):
    """Signup público — crea Enterprise + User admin + Subscription trial.

    Diseño MVP: confirmación de email pospuesta (se crea directamente).
    Cuando agreguemos email transactional, este endpoint crea un
    SignupRequest pendiente y el endpoint /saas/confirm/<token>/
    materializa los registros.

    Body (todos requeridos salvo phone):
      - email
      - password (mínimo 8 chars)
      - enterprise_name
      - full_name
      - phone (opcional)

    Devuelve 201 con { user_id, enterprise_id, subscription, access, refresh }.
    """
    data = request.data
    required = ['email', 'password', 'enterprise_name', 'full_name']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return Response({'detail': f'Faltan campos: {", ".join(missing)}'},
                        status=status.HTTP_400_BAD_REQUEST)

    email = data['email'].lower().strip()
    if User.objects.filter(email__iexact=email).exists():
        return Response({'detail': 'Ya existe una cuenta con ese email.'},
                        status=status.HTTP_409_CONFLICT)

    password = data['password']
    if len(password) < 8:
        return Response({'password': 'La contraseña debe tener al menos 8 caracteres.'},
                        status=status.HTTP_400_BAD_REQUEST)

    enterprise_name = data['enterprise_name'].strip()
    if not enterprise_name:
        return Response({'enterprise_name': 'Requerido.'},
                        status=status.HTTP_400_BAD_REQUEST)

    full_name = data['full_name'].strip()
    first_name, _, last_name = full_name.partition(' ')

    # Username derivado del email (parte antes del @, + suffix si colisiona).
    base_username = email.split('@')[0][:30]
    username = base_username
    suffix = 1
    while User.objects.filter(username=username).exists():
        username = f'{base_username}{suffix}'
        suffix += 1

    # Creamos todo dentro de transaction para que si algo falla quede
    # consistente — Enterprise sin usuarios es basura.
    with transaction.atomic():
        # 1. Enterprise. El RUC queda pendiente — el operador lo
        #    completa después desde el admin. Usamos un placeholder
        #    único para no romper unique constraint.
        ruc_placeholder = f'PEND-{secrets.token_hex(4).upper()}'
        enterprise = Enterprise.objects.create(
            name=enterprise_name,
            ruc=ruc_placeholder,
            email=email,
            phone=data.get('phone', '') or '',
            address='',
            city='',
        )

        # 2. Branch inicial — "Casa Central".
        Branch.objects.create(
            enterprise=enterprise,
            name='Casa Central',
            code='CC',
        )

        # 3. Usuario admin.
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            enterprise=enterprise,
            role='admin',
            first_name=first_name or full_name[:30],
            last_name=last_name[:30],
        )

        # 4. Subscription en trial.
        sub = Subscription.objects.create(enterprise=enterprise)
        sub.start_trial(days=14)

    # JWT para que el cliente quede logueado inmediatamente.
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(user)

    return Response({
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
        },
        'enterprise': {
            'id': enterprise.id,
            'name': enterprise.name,
        },
        'subscription': {
            'plan': sub.plan,
            'status': sub.status,
            'trial_ends_at': sub.trial_ends_at.isoformat() if sub.trial_ends_at else None,
        },
        'access':  str(refresh.access_token),
        'refresh': str(refresh),
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_subscription(request):
    """Estado de la suscripción del usuario actual."""
    user = request.user
    if not user.enterprise:
        return Response({'detail': 'Usuario sin empresa.'}, status=400)
    try:
        sub = user.enterprise.subscription
    except Subscription.DoesNotExist:
        return Response({'detail': 'Empresa sin suscripción (legacy AUTO OFERTAS).'},
                        status=404)
    return Response({
        'plan': sub.plan,
        'plan_display': sub.get_plan_display(),
        'status': sub.status,
        'is_active': sub.is_active,
        'is_trial': sub.is_trial,
        'is_trial_expired': sub.is_trial_expired,
        'trial_ends_at': sub.trial_ends_at.isoformat() if sub.trial_ends_at else None,
        'current_period_ends_at': sub.current_period_ends_at.isoformat() if sub.current_period_ends_at else None,
        'limits': sub.limits,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def request_upgrade(request):
    """Solicita upgrade a un plan pago. Placeholder — sin Stripe real.

    Por ahora sólo guarda la intención del usuario en notes y devuelve
    un mensaje de "te contactaremos". Cuando integremos billing real,
    este endpoint redirige a Stripe Checkout.
    """
    target_plan = (request.data.get('plan') or '').lower()
    if target_plan not in dict(PLAN_CHOICES) or target_plan == 'trial':
        return Response({'detail': 'Plan inválido.'}, status=400)

    user = request.user
    sub = user.enterprise.subscription
    sub.notes = (sub.notes or '') + (
        f'\n[{timezone.now().isoformat()}] {user.email} solicita upgrade a {target_plan}'
    )
    sub.save()
    return Response({
        'detail': (
            f'Solicitud de upgrade a {target_plan} registrada. '
            f'Te contactaremos a {user.email} en las próximas 24h con el link de pago.'
        )
    })
