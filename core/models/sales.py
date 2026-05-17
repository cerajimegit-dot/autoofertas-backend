from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Customer(models.Model):
    """Cliente de la empresa"""
    
    DOCUMENT_TYPE_CHOICES = (
        ('ci', _('Cédula de Identidad')),
        ('ruc', _('RUC')),
        ('passport', _('Pasaporte')),
    )
    
    enterprise = models.ForeignKey(
        'core.Enterprise',
        on_delete=models.CASCADE,
        related_name='customers',
        verbose_name=_('Empresa')
    )
    
    # Cliente genérico para ventas sin cliente definido
    is_generic = models.BooleanField(
        default=False,
        verbose_name=_('Es Cliente Genérico')
    )
    
    # Datos personales
    first_name = models.CharField(
        max_length=100,
        verbose_name=_('Nombre')
    )
    last_name = models.CharField(
        max_length=100,
        verbose_name=_('Apellido')
    )
    
    document_type = models.CharField(
        max_length=20,
        choices=DOCUMENT_TYPE_CHOICES,
        default='ci',
        verbose_name=_('Tipo de Documento')
    )
    document_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_('Número de Documento')
    )
    
    email = models.EmailField(
        blank=True,
        verbose_name=_('Email')
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_('Teléfono')
    )
    address = models.TextField(
        blank=True,
        verbose_name=_('Dirección')
    )
    city = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Ciudad')
    )
    
    # Información adicional
    notes = models.TextField(
        blank=True,
        verbose_name=_('Notas')
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Fecha de Creación')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Fecha de Actualización')
    )
    
    class Meta:
        verbose_name = _('Cliente')
        verbose_name_plural = _('Clientes')
        unique_together = ('enterprise', 'document_number')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['enterprise', 'document_number']),
            models.Index(fields=['enterprise', 'is_generic']),
        ]
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.document_number})"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class PaymentForm(models.Model):
    """Forma de pago (Efectivo, Tarjeta, Cheque, etc.)"""
    
    enterprise = models.ForeignKey(
        'core.Enterprise',
        on_delete=models.CASCADE,
        related_name='payment_forms',
        verbose_name=_('Empresa')
    )
    
    name = models.CharField(
        max_length=100,
        verbose_name=_('Nombre de Forma de Pago')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Descripción')
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Activo')
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Fecha de Creación')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Fecha de Actualización')
    )
    
    class Meta:
        verbose_name = _('Forma de Pago')
        verbose_name_plural = _('Formas de Pago')
        unique_together = ('enterprise', 'name')
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Sale(models.Model):
    """Registro de venta"""
    
    STATUS_CHOICES = (
        ('pending', _('Pendiente')),
        ('completed', _('Completada')),
        ('cancelled', _('Cancelada')),
    )
    
    enterprise = models.ForeignKey(
        'core.Enterprise',
        on_delete=models.CASCADE,
        related_name='sales',
        verbose_name=_('Empresa')
    )
    branch = models.ForeignKey(
        'core.Branch',
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_('Sucursal')
    )
    
    # Referencia
    sale_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_('Número de Venta')
    )
    sale_date = models.DateTimeField(
        default=timezone.now,
        verbose_name=_('Fecha de Venta')
    )
    
    # Cliente
    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sales',
        verbose_name=_('Cliente')
    )
    
    # Vehículo
    vehicle = models.ForeignKey(
        'core.Vehicle',
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_('Vehículo')
    )
    
    # Detalles de precio
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_('Precio Unitario')
    )
    discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name=_('Descuento')
    )
    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_('Precio Total')
    )
    down_payment = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name=_('Entrega Inicial')
    )

    # Forma de pago
    payment_form = models.ForeignKey(
        PaymentForm,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_('Forma de Pago')
    )
    
    # Empleado que realizó la venta
    seller = models.ForeignKey(
        'core.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        related_name='sales',
        verbose_name=_('Vendedor')
    )
    
    # Estado
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name=_('Estado')
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name=_('Notas')
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Fecha de Creación')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Fecha de Actualización')
    )
    
    class Meta:
        verbose_name = _('Venta')
        verbose_name_plural = _('Ventas')
        ordering = ['-sale_date']
        indexes = [
            models.Index(fields=['enterprise', 'branch', 'sale_date']),
            models.Index(fields=['sale_number']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Venta #{self.sale_number} - {self.customer.full_name if self.customer else 'N/A'}"

    # Mapeo de status de la venta → estado deseado del vehículo asociado.
    # `completed` deja el auto vendido, `pending` lo reserva, `cancelled` lo
    # libera (siempre que no haya OTRA venta activa apuntando al mismo).
    _SALE_TO_VEHICLE_STATE = {
        'completed': 'sold',
        'pending':   'reserved',
        'cancelled': 'available',
    }

    def save(self, *args, **kwargs):
        """Persiste la venta y sincroniza el estado del vehículo.

        Casos cubiertos:
          - Crear venta con vehículo → el vehículo pasa a sold/reserved
            según el status de la venta.
          - Cambiar el vehículo de una venta existente → el viejo se libera
            (si no hay otra venta activa apuntándolo) y el nuevo se marca.
          - Cambiar el status (pending→completed, completed→cancelled, etc.) →
            el vehículo se ajusta. Cancelar libera el vehículo.

        Si la sincronización del vehículo falla por cualquier motivo
        (ej. el vehículo fue borrado), NO bloqueamos el save de la venta:
        loguemos y seguimos.
        """
        # Capturar valores anteriores antes del super().save()
        old_vehicle_id = None
        old_status = None
        if self.pk is not None:
            old = type(self).objects.filter(pk=self.pk).only(
                'vehicle_id', 'status'
            ).first()
            if old:
                old_vehicle_id = old.vehicle_id
                old_status = old.status

        super().save(*args, **kwargs)

        try:
            self._sync_vehicle_state(old_vehicle_id, old_status)
        except Exception as e:
            # No queremos que un fallo en la sincronización rompa la venta.
            import logging
            logging.getLogger(__name__).warning(
                'Sale.save: fallo sincronizando vehicle.state para sale_id=%s: %s',
                self.pk, e,
            )

        try:
            self._sync_cash_movements()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                'Sale.save: fallo creando cash movements para sale_id=%s: %s',
                self.pk, e,
            )

    def _sync_vehicle_state(self, old_vehicle_id, old_status):
        """Aplica las transiciones de estado al vehículo viejo y al nuevo."""
        from core.models import Vehicle

        new_vehicle_id = self.vehicle_id
        target_state = self._SALE_TO_VEHICLE_STATE.get(self.status)

        # Si cambió el vehículo de la venta, liberar al viejo si corresponde.
        if old_vehicle_id and old_vehicle_id != new_vehicle_id:
            self._maybe_release_vehicle(old_vehicle_id)

        # Si la venta tiene un vehículo asignado, actualizar su estado.
        if new_vehicle_id and target_state:
            if target_state == 'available':
                # El status pasó a cancelled — sólo liberamos si NO existe otra
                # venta activa apuntando a este vehículo.
                self._maybe_release_vehicle(new_vehicle_id)
            else:
                Vehicle.objects.filter(pk=new_vehicle_id).update(state=target_state)

    @classmethod
    def _maybe_release_vehicle(cls, vehicle_id):
        """Libera el vehículo (pone state='available') sólo si no hay otra
        venta activa (status pending/completed) que lo siga referenciando.
        """
        from core.models import Vehicle

        other_active = cls.objects.filter(
            vehicle_id=vehicle_id,
            status__in=('pending', 'completed'),
        ).exists()
        if not other_active:
            Vehicle.objects.filter(pk=vehicle_id).update(state='available')

    def delete(self, *args, **kwargs):
        """Al borrar una venta, liberar el vehículo si era el último que lo
        referenciaba como activo.
        """
        vehicle_id = self.vehicle_id
        result = super().delete(*args, **kwargs)
        if vehicle_id:
            try:
                self._maybe_release_vehicle(vehicle_id)
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(
                    'Sale.delete: fallo liberando vehicle_id=%s: %s', vehicle_id, e,
                )
        return result

    def _sync_cash_movements(self):
        """Crea o actualiza los movimientos de caja automáticos para esta venta:
          - venta_contado: si la venta es CONTADO y status='completed'.
          - seña_credito:  si down_payment > 0 (cualquier forma de pago).
        Si la venta se cancela, los movimientos automáticos se borran (las
        ventas canceladas no generaron ingreso real).
        """
        from core.models.cash import CashMovement

        # Si la venta no está completada (pending, cancelled), removemos los
        # movimientos automáticos generados por ella.
        if self.status != 'completed':
            CashMovement.objects.filter(
                sale=self, is_auto=True,
                kind__in=('venta_contado', 'seña_credito'),
            ).delete()
            return

        pf_name = (self.payment_form.name.upper() if self.payment_form else '')
        sale_date = self.sale_date.date() if hasattr(self.sale_date, 'date') else self.sale_date

        # Venta contado: el monto total ingresa el día de la venta.
        if 'CONTADO' in pf_name:
            CashMovement.objects.update_or_create(
                sale=self, kind='venta_contado',
                defaults={
                    'enterprise': self.enterprise,
                    'branch': self.branch,
                    'date': sale_date,
                    'direction': 'in',
                    'amount': self.total_price,
                    'description': f'Venta contado {self.sale_number}',
                    'is_auto': True,
                    'created_by': self.seller,
                },
            )
        else:
            # Si la venta cambió de CONTADO a CREDITO/MIXTO, limpiar.
            CashMovement.objects.filter(
                sale=self, kind='venta_contado', is_auto=True,
            ).delete()

        # Seña de crédito: ingresa el día de la venta si down_payment > 0.
        if self.down_payment and float(self.down_payment) > 0:
            CashMovement.objects.update_or_create(
                sale=self, kind='seña_credito',
                defaults={
                    'enterprise': self.enterprise,
                    'branch': self.branch,
                    'date': sale_date,
                    'direction': 'in',
                    'amount': self.down_payment,
                    'description': f'Seña venta {self.sale_number}',
                    'is_auto': True,
                    'created_by': self.seller,
                },
            )
        else:
            CashMovement.objects.filter(
                sale=self, kind='seña_credito', is_auto=True,
            ).delete()


class Quotum(models.Model):
    """Cuota de pago de una venta a crédito"""

    PAYMENT_STATUS_CHOICES = (
        ('pending', _('Pendiente')),
        ('paid', _('Cobrada')),
        ('overdue', _('Vencida')),
        ('cancelled', _('Cancelada')),
    )

    # Formas de cobro de cuotas usadas por AUTO OFERTAS. Distintas de
    # Sale.payment_form (que es el tipo de venta: contado/crédito/mixto).
    PAYMENT_METHOD_CHOICES = (
        ('EF', _('Efectivo')),
        ('TB', _('Transferencia bancaria')),
        ('CJ', _('Caja')),
        ('AC', _('Acuerdo')),
    )
    
    enterprise = models.ForeignKey(
        'core.Enterprise',
        on_delete=models.CASCADE,
        related_name='quotas',
        verbose_name=_('Empresa')
    )
    
    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name='quotas',
        verbose_name=_('Venta')
    )
    
    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        related_name='quotas',
        verbose_name=_('Cliente')
    )
    
    # Número de cuota
    quota_number = models.IntegerField(
        verbose_name=_('Número de Cuota')
    )
    
    # Plan de financiación
    plan_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Plan de Financiación')
    )
    total_plan = models.IntegerField(
        verbose_name=_('Total de Cuotas del Plan')
    )
    
    # Montos
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_('Monto de Cuota')
    )
    interest = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name=_('Interés')
    )
    
    # Fechas
    due_date = models.DateField(
        verbose_name=_('Fecha de Vencimiento')
    )
    payment_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Fecha de Pago')
    )
    cancelled_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Fecha de Cancelación')
    )

    # Estado
    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending',
        verbose_name=_('Estado')
    )

    # Forma de cobro — sólo aplica para cuotas pagadas. Antes se prefijaba
    # como `[EF]/[TB]/...` en `notes` (workaround del quick-win); ahora vive
    # como campo propio.
    payment_method = models.CharField(
        max_length=2,
        choices=PAYMENT_METHOD_CHOICES,
        blank=True,
        null=True,
        verbose_name=_('Forma de cobro')
    )

    notes = models.TextField(
        blank=True,
        verbose_name=_('Notas')
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Fecha de Creación')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Fecha de Actualización')
    )
    
    class Meta:
        verbose_name = _('Cuota')
        verbose_name_plural = _('Cuotas')
        unique_together = ('sale', 'quota_number')
        ordering = ['sale', 'quota_number']
        indexes = [
            models.Index(fields=['enterprise', 'customer', 'due_date']),
            models.Index(fields=['status', 'due_date']),
        ]

    def __str__(self):
        return f"Cuota #{self.quota_number} - Venta #{self.sale.sale_number}"

    @property
    def is_overdue(self):
        """Una cuota está vencida si:
          - su status es 'overdue' (legacy — se mantienen las 62 filas
            actuales para no perder información de migración), O
          - su status es 'pending' y la fecha de vencimiento ya pasó.

        Calcular esto en línea evita el problema de mantener un campo
        derivado: hay 970 cuotas pending con due_date < hoy que la lógica
        antigua marcaba como "pending" en el listado y "vencidas" en el
        dashboard. Con esta property la respuesta es una sola.
        """
        if self.status == 'paid' or self.status == 'cancelled':
            return False
        if self.status == 'overdue':
            return True
        from datetime import date
        return bool(self.due_date and self.due_date < date.today())

    def save(self, *args, **kwargs):
        """Persiste la cuota y sincroniza el movimiento de caja asociado.

        Cuando una cuota pasa a `paid` se crea un `CashMovement(kind='cobro_cuota')`
        con la fecha del cobro real (`payment_date`). Si vuelve a `pending` o
        `cancelled`, el movimiento se elimina (no fue un cobro real).
        """
        super().save(*args, **kwargs)
        try:
            self._sync_cash_movement()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                'Quotum.save: fallo creando cash movement para quota_id=%s: %s',
                self.pk, e,
            )

    def _sync_cash_movement(self):
        """Auto-crea / actualiza / borra el movimiento de caja de esta cuota."""
        from core.models.cash import CashMovement

        if self.status == 'paid' and self.payment_date:
            customer_name = self.customer.full_name if self.customer else 'sin cliente'
            sale_number = self.sale.sale_number if self.sale else ''
            CashMovement.objects.update_or_create(
                quota=self, kind='cobro_cuota',
                defaults={
                    'enterprise': self.enterprise,
                    'branch': self.sale.branch if self.sale else None,
                    'date': self.payment_date,
                    'direction': 'in',
                    'amount': self.amount,
                    'description': (
                        f'Cuota {self.quota_number}'
                        f'{("/" + str(self.total_plan)) if self.total_plan else ""} '
                        f'venta {sale_number} — {customer_name}'
                    ),
                    'is_auto': True,
                },
            )
        else:
            # Si la cuota vuelve a pending/cancelled/overdue, el movimiento
            # auto se borra: no hubo cobro real.
            CashMovement.objects.filter(
                quota=self, is_auto=True, kind='cobro_cuota',
            ).delete()

    @property
    def effective_status(self):
        """Status efectivo para mostrar al usuario, calculado en línea.

        - 'paid'      → 'paid'
        - 'cancelled' → 'cancelled'
        - pending con due_date pasado → 'overdue'
        - cualquier otro pending → 'pending'
        - 'overdue' (legacy) → 'overdue'
        """
        if self.status in ('paid', 'cancelled'):
            return self.status
        return 'overdue' if self.is_overdue else 'pending'
