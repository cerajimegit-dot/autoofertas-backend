"""Modelo de movimientos de caja.

Reemplaza el archivo Excel "FLUJO DE CAJA ..." con un registro estructurado.
La mayoría de los movimientos se crean automáticamente cuando se cierra una
venta o se cobra una cuota; los gastos / compras al exterior / transporte
se cargan manualmente desde la UI.

Decisión de diseño: `amount` siempre positivo + `direction` (in/out). Eso
hace los `Sum` por dirección directos en SQL y evita confusión con signos.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class CashMovement(models.Model):
    KIND_CHOICES = (
        ('cobro_cuota',     _('Cobro de cuota')),
        ('venta_contado',   _('Venta contado')),
        ('seña_credito',    _('Seña de crédito')),
        ('pago_a_cuenta',   _('Pago a cuenta')),
        ('gasto_playa',     _('Gasto playa')),
        ('alquiler',        _('Alquiler')),
        ('sueldo',          _('Sueldo')),
        ('comision',        _('Comisión / honorario')),
        ('compra_exterior', _('Compra al exterior')),
        ('transporte',      _('Transporte / despacho')),
        ('impuesto',        _('Impuesto')),
        ('ajuste',          _('Ajuste de caja')),
        ('otro',            _('Otro')),
    )

    DIRECTION_CHOICES = (
        ('in',  _('Ingreso')),
        ('out', _('Egreso')),
    )

    CURRENCY_CHOICES = (
        ('PYG', 'PYG'),
        ('USD', 'USD'),
    )

    enterprise = models.ForeignKey(
        'core.Enterprise',
        on_delete=models.CASCADE,
        related_name='cash_movements',
        verbose_name=_('Empresa'),
    )
    branch = models.ForeignKey(
        'core.Branch',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='cash_movements',
        verbose_name=_('Sucursal'),
    )

    date = models.DateField(verbose_name=_('Fecha'))
    kind = models.CharField(
        max_length=20, choices=KIND_CHOICES,
        verbose_name=_('Tipo'),
    )
    direction = models.CharField(
        max_length=3, choices=DIRECTION_CHOICES,
        verbose_name=_('Dirección'),
    )
    description = models.TextField(verbose_name=_('Operación'))

    # Monto SIEMPRE positivo. El signo lo da `direction`.
    amount = models.DecimalField(
        max_digits=14, decimal_places=2,
        verbose_name=_('Monto'),
    )
    currency = models.CharField(
        max_length=3, choices=CURRENCY_CHOICES, default='PYG',
        verbose_name=_('Moneda'),
    )
    # Si currency=USD, guardamos también el monto en USD original y el TC
    # aplicado para auditar contra el Excel.
    amount_usd = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        verbose_name=_('Monto en USD'),
    )
    exchange_rate = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name=_('Tipo de cambio'),
    )

    # Trazabilidad
    provider = models.CharField(
        max_length=100, blank=True,
        verbose_name=_('Proveedor'),
        help_text=_('Ej: AUTOWINI, DADANI, LAYSOLA — para compras al exterior'),
    )
    sale = models.ForeignKey(
        'core.Sale', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='cash_movements',
        verbose_name=_('Venta'),
    )
    quota = models.ForeignKey(
        'core.Quotum', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='cash_movements',
        verbose_name=_('Cuota'),
    )

    # ¿Quién y cómo lo creó?
    created_by = models.ForeignKey(
        'core.CustomUser', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='cash_movements_created',
        verbose_name=_('Creado por'),
    )
    is_auto = models.BooleanField(
        default=False,
        verbose_name=_('Generado automáticamente'),
        help_text=_('True cuando proviene de una venta o cobro de cuota; '
                    'False cuando lo creó un usuario manualmente.'),
    )

    notes = models.TextField(blank=True, verbose_name=_('Notas'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Movimiento de caja')
        verbose_name_plural = _('Movimientos de caja')
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['enterprise', 'date']),
            models.Index(fields=['enterprise', 'branch', 'date']),
            models.Index(fields=['kind']),
            models.Index(fields=['direction']),
            models.Index(fields=['sale']),
            models.Index(fields=['quota']),
        ]

    def __str__(self):
        signo = '+' if self.direction == 'in' else '-'
        return f'{self.date} {signo}{self.amount} {self.kind}'

    @property
    def signed_amount(self):
        """Devuelve el monto con signo (positivo si ingreso, negativo si egreso)."""
        return self.amount if self.direction == 'in' else -self.amount
