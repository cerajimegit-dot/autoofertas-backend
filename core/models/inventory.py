from django.db import models
from django.utils.translation import gettext_lazy as _


class Brand(models.Model):
    """Marca de vehículos (ej. Toyota, Honda, Ford, etc.)"""
    
    enterprise = models.ForeignKey(
        'core.Enterprise',
        on_delete=models.CASCADE,
        related_name='brands',
        verbose_name=_('Empresa')
    )
    name = models.CharField(
        max_length=100,
        verbose_name=_('Nombre de Marca')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Descripción')
    )
    image = models.ImageField(
        upload_to='brands/',
        null=True,
        blank=True,
        verbose_name=_('Imagen')
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
        verbose_name = _('Marca')
        verbose_name_plural = _('Marcas')
        unique_together = ('enterprise', 'name')
        ordering = ['name']
        indexes = [
            models.Index(fields=['enterprise', 'is_active']),
        ]
    
    def __str__(self):
        return self.name


class VehicleModel(models.Model):
    """Modelo de vehículo (ej. Corolla, Civic, F-150)"""
    
    enterprise = models.ForeignKey(
        'core.Enterprise',
        on_delete=models.CASCADE,
        related_name='vehicle_models',
        verbose_name=_('Empresa')
    )
    brand = models.ForeignKey(
        Brand,
        on_delete=models.CASCADE,
        related_name='models',
        verbose_name=_('Marca')
    )
    name = models.CharField(
        max_length=100,
        verbose_name=_('Nombre del Modelo')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Descripción')
    )
    image = models.ImageField(
        upload_to='models/',
        null=True,
        blank=True,
        verbose_name=_('Imagen')
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
        verbose_name = _('Modelo de Vehículo')
        verbose_name_plural = _('Modelos de Vehículos')
        unique_together = ('enterprise', 'brand', 'name')
        ordering = ['brand__name', 'name']
        indexes = [
            models.Index(fields=['enterprise', 'brand']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.brand.name} {self.name}"


class ExchangeRate(models.Model):
    """Cotización USD/PYG para conversión de precios"""
    
    enterprise = models.ForeignKey(
        'core.Enterprise',
        on_delete=models.CASCADE,
        related_name='exchange_rates',
        verbose_name=_('Empresa')
    )
    rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_('Cotización (USD/PYG)')
    )
    source = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Fuente')
    )
    date = models.DateField(
        auto_now_add=True,
        verbose_name=_('Fecha')
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Activo')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Fecha de Creación')
    )
    
    class Meta:
        verbose_name = _('Cotización')
        verbose_name_plural = _('Cotizaciones')
        ordering = ['-date']
        indexes = [
            models.Index(fields=['enterprise', 'is_active', 'date']),
        ]
    
    def __str__(self):
        return f"USD/PYG: {self.rate} - {self.date}"


class Vehicle(models.Model):
    """Stock de vehículos en sucursal"""
    
    STATE_CHOICES = (
        ('available', _('Disponible')),
        ('reserved', _('Reservado')),
        ('sold', _('Vendido')),
        ('maintenance', _('Mantenimiento')),
    )
    
    CURRENCY_CHOICES = (
        ('PYG', _('Guaraní')),
        ('USD', _('Dólar')),
    )
    
    enterprise = models.ForeignKey(
        'core.Enterprise',
        on_delete=models.CASCADE,
        related_name='vehicles',
        verbose_name=_('Empresa')
    )
    branch = models.ForeignKey(
        'core.Branch',
        on_delete=models.CASCADE,
        related_name='vehicles',
        verbose_name=_('Sucursal')
    )
    brand = models.ForeignKey(
        Brand,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_('Marca')
    )
    model = models.ForeignKey(
        VehicleModel,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_('Modelo')
    )
    year = models.IntegerField(
        verbose_name=_('Año')
    )
    vin = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_('VIN')
    )
    license_plate = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('Placa de Patente')
    )
    color = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('Color')
    )
    mileage = models.IntegerField(
        default=0,
        verbose_name=_('Kilometraje')
    )
    
    # Costos detallados
    fob = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_('FOB (Costo Base)')
    )
    container = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name=_('CONTEN (Costo Contenedor)')
    )
    dispatch = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name=_('DESPACHO')
    )
    cam_vol = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name=_('CAM/VOL (Carga/Volumen)')
    )
    
    @property
    def total_cost(self):
        """Calcular costo total"""
        return self.fob + self.container + self.dispatch + self.cam_vol
    
    # Precios
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_('Precio de Venta')
    )
    currency = models.CharField(
        max_length=10,
        choices=CURRENCY_CHOICES,
        default='PYG',
        verbose_name=_('Moneda')
    )
    
    # Cotización (obligatoria si es USD)
    exchange_rate = models.ForeignKey(
        ExchangeRate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Cotización')
    )
    
    state = models.CharField(
        max_length=20,
        choices=STATE_CHOICES,
        default='available',
        verbose_name=_('Estado')
    )
    
    description = models.TextField(
        blank=True,
        verbose_name=_('Descripción')
    )
    image = models.ImageField(
        upload_to='vehicles/',
        null=True,
        blank=True,
        verbose_name=_('Imagen')
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
        verbose_name = _('Vehículo')
        verbose_name_plural = _('Vehículos')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['enterprise', 'branch', 'state']),
            models.Index(fields=['vin']),
            models.Index(fields=['state']),
        ]
    
    def __str__(self):
        return f"{self.brand} {self.model} {self.year} - VIN: {self.vin}"
    
    def clean(self):
        """Validación a nivel de modelo. La sube DRF como 400 en la API.

        ValueError (lo que había antes) escapa como 500 con stacktrace
        feo. ValidationError es lo que Django/DRF esperan.
        """
        from django.core.exceptions import ValidationError
        if self.currency == 'USD' and not self.exchange_rate:
            raise ValidationError({
                'exchange_rate': 'Es obligatorio cargar el tipo de cambio cuando '
                                 'el precio está en USD.'
            })

    def save(self, *args, **kwargs):
        # Mantengo la validación en save por compat (admin, scripts) — pero
        # también vía clean() para que DRF la atrape antes.
        self.clean()
        super().save(*args, **kwargs)


class VehicleCost(models.Model):
    """Conceptos de costo adicionales por vehículo.

    Permite agregar cualquier concepto (Flete, Seguro, Honorarios, Impuestos...)
    con su monto y moneda, más allá de los 4 estándar del vehículo
    (FOB, CONTEN, DESPACHO, CAM/VOL).
    """

    CURRENCY_CHOICES = (
        ('PYG', _('Guaraní')),
        ('USD', _('Dólar')),
    )

    enterprise = models.ForeignKey(
        'core.Enterprise',
        on_delete=models.CASCADE,
        related_name='vehicle_costs',
    )
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='extra_costs',
        verbose_name=_('Vehículo'),
    )
    concept = models.CharField(
        max_length=100,
        verbose_name=_('Concepto'),
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name=_('Monto'),
    )
    currency = models.CharField(
        max_length=10,
        choices=CURRENCY_CHOICES,
        default='PYG',
        verbose_name=_('Moneda'),
    )
    # Tipo de cambio aplicado cuando el monto está en USD. Lo guardamos
    # como DecimalField (no FK a ExchangeRate) para que el costo quede
    # congelado al TC del momento — si después cambia la cotización
    # vigente, el costo histórico no se mueve.
    exchange_rate = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        verbose_name=_('Tipo de cambio'),
        help_text=_('Obligatorio si moneda=USD. Se usa para calcular el '
                    'equivalente en PYG en el análisis de margen.'),
    )
    notes = models.TextField(blank=True, verbose_name=_('Notas'))
    order = models.IntegerField(default=0, verbose_name=_('Orden'))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Costo extra de vehículo')
        verbose_name_plural = _('Costos extras de vehículos')
        ordering = ['vehicle_id', 'order', 'id']
        indexes = [
            models.Index(fields=['vehicle']),
        ]

    def __str__(self):
        return f"{self.vehicle_id} - {self.concept}: {self.amount} {self.currency}"

    @property
    def amount_pyg(self):
        """Monto en guaraníes. Si currency=USD usa el TC guardado;
        si currency=PYG devuelve amount tal cual. Si USD sin TC, devuelve
        None (el llamador debe interpretar como "incomputable")."""
        if self.currency == 'PYG':
            return self.amount or 0
        if self.currency == 'USD' and self.exchange_rate:
            return (self.amount or 0) * self.exchange_rate
        return None

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.currency == 'USD' and not self.exchange_rate:
            raise ValidationError({
                'exchange_rate': 'Es obligatorio cargar el tipo de cambio cuando '
                                 'el monto está en USD.'
            })
