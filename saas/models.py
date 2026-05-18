"""Modelos del SaaS — Plan y Subscription.

Plan: catálogo de niveles (free/starter/pro/enterprise) con sus límites
y precios. Hardcoded en código (no editable desde admin) — la lógica
de billing real vendrá después con Stripe/MercadoPago.

Subscription: estado de cada Enterprise. Una empresa nueva arranca con
plan='trial' por 14 días; después debe upgradear a un plan pago o se
suspende.

Notas de diseño:
- No reemplaza al modelo Enterprise existente. Sólo se LIGA a él vía FK.
- Suspender = `status='suspended'`. El frontend (o un middleware
  específico) puede decidir bloquear endpoints cuando esto pasa.
- Cancelación: `status='cancelled'` deja a la empresa en read-only
  hasta que reactive.
"""

from datetime import timedelta

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


# Catálogo de planes. Modificable en código; cuando agreguemos Stripe,
# cada plan llevará también un price_id de Stripe.
PLAN_CHOICES = (
    ('trial',      _('Trial 14 días')),
    ('starter',    _('Starter')),
    ('pro',        _('Profesional')),
    ('enterprise', _('Enterprise')),
)

# Límites por plan (vehículos, sucursales, usuarios, cuotas/mes).
# El middleware/permissions puede chequear esto para evitar abuso de
# planes free.
PLAN_LIMITS = {
    'trial':      {'vehicles': 50,  'branches': 2, 'users': 3,  'monthly_quotas': 200},
    'starter':    {'vehicles': 100, 'branches': 2, 'users': 5,  'monthly_quotas': 500},
    'pro':        {'vehicles': 500, 'branches': 5, 'users': 20, 'monthly_quotas': 5000},
    'enterprise': {'vehicles': None,'branches': None, 'users': None, 'monthly_quotas': None},
}

# Precios en USD por mes. Trial es gratis.
PLAN_PRICES_USD = {
    'trial':      0,
    'starter':    29,
    'pro':        79,
    'enterprise': 199,
}


class Subscription(models.Model):
    STATUS_CHOICES = (
        ('active',    _('Activa')),
        ('suspended', _('Suspendida (impago)')),
        ('cancelled', _('Cancelada')),
        ('expired',   _('Expirada')),
    )

    enterprise = models.OneToOneField(
        'core.Enterprise',
        on_delete=models.CASCADE,
        related_name='subscription',
        verbose_name=_('Empresa'),
    )
    plan = models.CharField(
        max_length=20,
        choices=PLAN_CHOICES,
        default='trial',
        verbose_name=_('Plan'),
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name=_('Estado'),
    )
    started_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Inicio'),
    )
    trial_ends_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name=_('Fin del trial'),
    )
    current_period_ends_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name=_('Fin del período actual'),
        help_text=_('Mensual o anual según el plan. Si pasa esta fecha sin '
                    'renovación, la suscripción se considera expirada.'),
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)

    # Integración con proveedor de billing (Stripe/MercadoPago) — placeholder.
    external_customer_id = models.CharField(max_length=100, blank=True)
    external_subscription_id = models.CharField(max_length=100, blank=True)

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Suscripción')
        verbose_name_plural = _('Suscripciones')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.enterprise.name} — {self.plan} ({self.status})'

    @property
    def is_trial(self):
        return self.plan == 'trial'

    @property
    def is_trial_expired(self):
        return self.is_trial and self.trial_ends_at and timezone.now() > self.trial_ends_at

    @property
    def is_active(self):
        """¿La suscripción está vigente para usar el sistema?"""
        if self.status != 'active':
            return False
        if self.is_trial:
            return not self.is_trial_expired
        if self.current_period_ends_at:
            return timezone.now() <= self.current_period_ends_at
        return True   # plan pago sin fecha = activo permanente (raro pero OK)

    @property
    def limits(self):
        return PLAN_LIMITS.get(self.plan, PLAN_LIMITS['trial'])

    def start_trial(self, days=14):
        """Helper para arrancar el trial al crearse la suscripción."""
        self.plan = 'trial'
        self.status = 'active'
        self.trial_ends_at = timezone.now() + timedelta(days=days)
        self.save()


class SignupRequest(models.Model):
    """Solicitud de signup pendiente de confirmación por email.

    El flujo es: el usuario completa el form de signup → creamos un
    SignupRequest con un token único → mandamos email con link →
    cuando hace clic, materializamos Enterprise + User + Subscription.

    Por ahora (MVP) el endpoint público crea directamente sin
    confirmación de email — este modelo queda como placeholder para
    cuando agreguemos verificación.
    """
    email = models.EmailField()
    enterprise_name = models.CharField(max_length=200)
    full_name = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=50, blank=True)

    token = models.CharField(max_length=64, unique=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()

    enterprise = models.ForeignKey(
        'core.Enterprise',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        help_text='Una vez confirmado, apunta a la enterprise creada.',
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Solicitud de signup')
        verbose_name_plural = _('Solicitudes de signup')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['email']),
        ]

    def __str__(self):
        return f'{self.email} → {self.enterprise_name}'
