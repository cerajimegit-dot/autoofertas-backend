from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

class CustomUser(AbstractUser):
    """Usuario personalizado con roles específicos del sistema"""
    
    ROLE_CHOICES = (
        ('admin', _('Administrador')),
        ('manager', _('Encargado de Sucursal')),
        ('vendor', _('Vendedor')),
    )
    
    enterprise = models.ForeignKey(
        'Enterprise',
        on_delete=models.CASCADE,
        related_name='users',
        null=True,
        blank=True,
        verbose_name=_('Empresa')
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='vendor',
        verbose_name=_('Rol')
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_('Teléfono')
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Activo')
    )
    # Sucursales que el usuario puede ver. Si está vacío significa "todas".
    branches_visible = models.ManyToManyField(
        'Branch',
        blank=True,
        related_name='visible_to_users',
        verbose_name=_('Sucursales visibles'),
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
        verbose_name = _('Usuario')
        verbose_name_plural = _('Usuarios')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"
    
    def get_role_display_spanish(self):
        roles = {
            'admin': 'Administrador',
            'manager': 'Encargado de Sucursal',
            'vendor': 'Vendedor',
        }
        return roles.get(self.role, self.role)


class Enterprise(models.Model):
    """Empresa cliente que adquiere el software (Multiempresa)"""
    
    name = models.CharField(
        max_length=255,
        unique=True,
        verbose_name=_('Nombre de Empresa')
    )
    ruc = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_('RUC')
    )
    email = models.EmailField(
        verbose_name=_('Email')
    )
    phone = models.CharField(
        max_length=20,
        verbose_name=_('Teléfono')
    )
    address = models.TextField(
        verbose_name=_('Dirección')
    )
    city = models.CharField(
        max_length=100,
        verbose_name=_('Ciudad')
    )
    country = models.CharField(
        max_length=100,
        default='Paraguay',
        verbose_name=_('País')
    )
    logo = models.ImageField(
        upload_to='logos/',
        null=True,
        blank=True,
        verbose_name=_('Logo')
    )
    subscription_status = models.CharField(
        max_length=20,
        choices=(
            ('active', _('Activo')),
            ('inactive', _('Inactivo')),
            ('suspended', _('Suspendido')),
        ),
        default='active',
        verbose_name=_('Estado de Suscripción')
    )
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='enterprises_created',
        verbose_name=_('Creado por')
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
        verbose_name = _('Empresa')
        verbose_name_plural = _('Empresas')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['ruc']),
            models.Index(fields=['subscription_status']),
        ]
    
    def __str__(self):
        return self.name


class Branch(models.Model):
    """Sucursal de una empresa"""
    
    enterprise = models.ForeignKey(
        Enterprise,
        on_delete=models.CASCADE,
        related_name='branches',
        verbose_name=_('Empresa')
    )
    name = models.CharField(
        max_length=255,
        verbose_name=_('Nombre de Sucursal')
    )
    code = models.CharField(
        max_length=50,
        verbose_name=_('Código de Sucursal')
    )
    address = models.TextField(
        verbose_name=_('Dirección')
    )
    city = models.CharField(
        max_length=100,
        verbose_name=_('Ciudad')
    )
    phone = models.CharField(
        max_length=20,
        verbose_name=_('Teléfono')
    )
    manager = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='branches_managed',
        limit_choices_to={'role': 'manager'},
        verbose_name=_('Encargado')
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
        verbose_name = _('Sucursal')
        verbose_name_plural = _('Sucursales')
        unique_together = ('enterprise', 'code')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['enterprise', 'code']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.enterprise.name})"


class AuditLog(models.Model):
    """Registro de auditoría de todas las acciones del sistema"""
    
    ACTION_CHOICES = (
        ('create', _('Crear')),
        ('update', _('Actualizar')),
        ('delete', _('Eliminar')),
        ('view', _('Ver')),
        ('login', _('Iniciar Sesión')),
        ('logout', _('Cerrar Sesión')),
        ('export', _('Exportar')),
        ('import', _('Importar')),
    )
    
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs',
        verbose_name=_('Usuario')
    )
    enterprise = models.ForeignKey(
        Enterprise,
        on_delete=models.CASCADE,
        related_name='audit_logs',
        verbose_name=_('Empresa')
    )
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        verbose_name=_('Acción')
    )
    model_name = models.CharField(
        max_length=100,
        verbose_name=_('Modelo')
    )
    object_id = models.IntegerField(
        verbose_name=_('ID del Objeto')
    )
    object_str = models.CharField(
        max_length=255,
        verbose_name=_('Objeto')
    )
    old_values = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Valores Anteriores')
    )
    new_values = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Valores Nuevos')
    )
    ip_address = models.GenericIPAddressField(
        verbose_name=_('Dirección IP')
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Marca de Tiempo')
    )
    
    class Meta:
        verbose_name = _('Registro de Auditoría')
        verbose_name_plural = _('Registros de Auditoría')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['enterprise', 'timestamp']),
            models.Index(fields=['model_name', 'object_id']),
        ]
    
    def __str__(self):
        return f"{self.user} - {self.action} - {self.model_name}({self.object_id})"


class ViewPermission(models.Model):
    """Permisos configurables por usuario para acceder a vistas específicas"""

    VIEW_CHOICES = (
        ('dashboard', _('Dashboard')),
        ('vehicles', _('Vehículos')),
        ('sales', _('Ventas')),
        ('quotas', _('Cuotas')),
        ('customers', _('Clientes')),
        ('customer_list_crm', _('CRM - Gestión de Clientes')),
        ('customer_edit', _('CRM - Editar Cliente')),
        ('sale_register', _('CRM - Registrar Venta')),
        ('quota_payment', _('CRM - Cobrar Cuota')),
        ('payment_history', _('CRM - Historial de Pagos')),
    )

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='view_permissions',
        verbose_name=_('Usuario')
    )
    view_name = models.CharField(
        max_length=50,
        choices=VIEW_CHOICES,
        verbose_name=_('Vista')
    )
    is_allowed = models.BooleanField(
        default=True,
        verbose_name=_('Permitido')
    )
    granted_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='permissions_granted',
        verbose_name=_('Otorgado por')
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
        verbose_name = _('Permiso de Vista')
        verbose_name_plural = _('Permisos de Vista')
        unique_together = ('user', 'view_name')
        ordering = ['user', 'view_name']

    def __str__(self):
        status = '✅' if self.is_allowed else '❌'
        return f"{self.user.username} - {self.get_view_name_display()} {status}"

    @classmethod
    def user_has_permission(cls, user, view_name):
        """Verifica si un usuario tiene permiso para acceder a una vista.
        Admin siempre tiene acceso. Si no hay registro, se permite por defecto."""
        if user.role == 'admin':
            return True
        perm = cls.objects.filter(user=user, view_name=view_name).first()
        if perm is None:
            return True  # Sin restricción explícita = permitido
        return perm.is_allowed

    @classmethod
    def get_user_permissions(cls, user):
        """Retorna dict {view_name: is_allowed} para un usuario"""
        perms = {}
        for view_name, _ in cls.VIEW_CHOICES:
            if user.role == 'admin':
                perms[view_name] = True
            else:
                perm = cls.objects.filter(user=user, view_name=view_name).first()
                perms[view_name] = perm.is_allowed if perm else True
        return perms

    @classmethod
    def set_user_permissions(cls, user, permissions_dict, granted_by):
        """Establece permisos masivamente. permissions_dict = {view_name: bool}"""
        for view_name, is_allowed in permissions_dict.items():
            cls.objects.update_or_create(
                user=user,
                view_name=view_name,
                defaults={
                    'is_allowed': is_allowed,
                    'granted_by': granted_by,
                }
            )
