from django.contrib import admin
from django.utils.html import format_html
from core.models import (
    CustomUser, Enterprise, Branch, AuditLog,
    Brand, VehicleModel, ExchangeRate, Vehicle,
    Customer, PaymentForm, Sale, Quotum
)


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'get_full_name', 'enterprise', 'role', 'is_active', 'created_at')
    list_filter = ('role', 'is_active', 'created_at', 'enterprise')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    fieldsets = (
        ('Información de Usuario', {
            'fields': ('username', 'email', 'first_name', 'last_name', 'password')
        }),
        ('Información de Empresa', {
            'fields': ('enterprise', 'role', 'phone')
        }),
        ('Permisos', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Fechas', {
            'fields': ('last_login', 'created_at', 'updated_at')
        }),
    )
    readonly_fields = ('created_at', 'updated_at', 'last_login')
    ordering = ['-created_at']


@admin.register(Enterprise)
class EnterpriseAdmin(admin.ModelAdmin):
    list_display = ('name', 'ruc', 'city', 'subscription_status', 'created_at')
    list_filter = ('subscription_status', 'country', 'created_at')
    search_fields = ('name', 'ruc', 'email')
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'ruc', 'logo')
        }),
        ('Contacto', {
            'fields': ('email', 'phone', 'address', 'city', 'country')
        }),
        ('Suscripción', {
            'fields': ('subscription_status', 'created_by')
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    readonly_fields = ('created_at', 'updated_at')
    ordering = ['-created_at']


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'enterprise', 'city', 'manager', 'is_active', 'created_at')
    list_filter = ('enterprise', 'is_active', 'city', 'created_at')
    search_fields = ('name', 'code', 'city')
    fieldsets = (
        ('Información Básica', {
            'fields': ('enterprise', 'name', 'code')
        }),
        ('Ubicación', {
            'fields': ('address', 'city', 'phone')
        }),
        ('Administración', {
            'fields': ('manager', 'is_active')
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    readonly_fields = ('created_at', 'updated_at')
    ordering = ['-created_at']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'model_name', 'timestamp', 'ip_address')
    list_filter = ('action', 'model_name', 'timestamp')
    search_fields = ('user__username', 'model_name', 'ip_address')
    readonly_fields = ('user', 'action', 'model_name', 'object_id', 'timestamp', 'old_values', 'new_values')
    fieldsets = (
        ('Usuario', {
            'fields': ('user', 'enterprise', 'ip_address')
        }),
        ('Acción', {
            'fields': ('action', 'model_name', 'object_id', 'object_str')
        }),
        ('Valores', {
            'fields': ('old_values', 'new_values')
        }),
        ('Timestamp', {
            'fields': ('timestamp',)
        }),
    )
    ordering = ['-timestamp']

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'enterprise', 'is_active', 'created_at')
    list_filter = ('enterprise', 'is_active', 'created_at')
    search_fields = ('name', 'description')
    fieldsets = (
        ('Información', {
            'fields': ('enterprise', 'name', 'description', 'image')
        }),
        ('Estado', {
            'fields': ('is_active',)
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    readonly_fields = ('created_at', 'updated_at')
    ordering = ['name']


@admin.register(VehicleModel)
class VehicleModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand', 'enterprise', 'is_active', 'created_at')
    list_filter = ('enterprise', 'brand', 'is_active', 'created_at')
    search_fields = ('name', 'description')
    fieldsets = (
        ('Información', {
            'fields': ('enterprise', 'brand', 'name', 'description', 'image')
        }),
        ('Estado', {
            'fields': ('is_active',)
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    readonly_fields = ('created_at', 'updated_at')
    ordering = ['brand__name', 'name']


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ('rate', 'enterprise', 'date', 'source', 'is_active')
    list_filter = ('enterprise', 'is_active', 'date')
    search_fields = ('source',)
    fieldsets = (
        ('Cotización', {
            'fields': ('enterprise', 'rate', 'source', 'date')
        }),
        ('Estado', {
            'fields': ('is_active',)
        }),
    )
    readonly_fields = ('created_at', 'date')
    ordering = ['-date']


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('vin', 'brand', 'model', 'year', 'state', 'price', 'currency', 'branch')
    list_filter = ('branch', 'brand', 'state', 'currency', 'year', 'created_at')
    search_fields = ('vin', 'license_plate')
    fieldsets = (
        ('Información Básica', {
            'fields': ('enterprise', 'branch', 'brand', 'model', 'year', 'vin', 'license_plate', 'color')
        }),
        ('Costos', {
            'fields': ('fob', 'container', 'dispatch', 'cam_vol')
        }),
        ('Precio', {
            'fields': ('price', 'currency', 'exchange_rate')
        }),
        ('Detalles', {
            'fields': ('mileage', 'description', 'image')
        }),
        ('Estado', {
            'fields': ('state',)
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    readonly_fields = ('created_at', 'updated_at')
    ordering = ['-created_at']


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'document_number', 'email', 'phone', 'enterprise')
    list_filter = ('enterprise', 'document_type', 'is_generic', 'created_at')
    search_fields = ('first_name', 'last_name', 'document_number', 'email')
    fieldsets = (
        ('Información Personal', {
            'fields': ('enterprise', 'first_name', 'last_name', 'is_generic')
        }),
        ('Documento', {
            'fields': ('document_type', 'document_number')
        }),
        ('Contacto', {
            'fields': ('email', 'phone', 'address', 'city')
        }),
        ('Información Adicional', {
            'fields': ('notes',)
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    readonly_fields = ('created_at', 'updated_at')
    ordering = ['-created_at']


@admin.register(PaymentForm)
class PaymentFormAdmin(admin.ModelAdmin):
    list_display = ('name', 'enterprise', 'is_active')
    list_filter = ('enterprise', 'is_active')
    search_fields = ('name', 'description')
    fieldsets = (
        ('Información', {
            'fields': ('enterprise', 'name', 'description')
        }),
        ('Estado', {
            'fields': ('is_active',)
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('sale_number', 'customer', 'branch', 'total_price', 'status', 'sale_date')
    list_filter = ('branch', 'status', 'payment_form', 'sale_date')
    search_fields = ('sale_number', 'customer__first_name', 'customer__last_name')
    fieldsets = (
        ('Información de Venta', {
            'fields': ('sale_number', 'sale_date', 'enterprise', 'branch')
        }),
        ('Cliente', {
            'fields': ('customer',)
        }),
        ('Vehículo', {
            'fields': ('vehicle',)
        }),
        ('Precios', {
            'fields': ('unit_price', 'discount', 'total_price')
        }),
        ('Otros', {
            'fields': ('payment_form', 'seller', 'status', 'notes')
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    readonly_fields = ('created_at', 'updated_at', 'sale_date', 'sale_number')
    ordering = ['-sale_date']


@admin.register(Quotum)
class QuotumAdmin(admin.ModelAdmin):
    list_display = ('quota_number', 'sale', 'customer', 'amount', 'status', 'due_date')
    list_filter = ('status', 'due_date', 'created_at', 'enterprise')
    search_fields = ('sale__sale_number', 'customer__first_name', 'customer__last_name')
    fieldsets = (
        ('Información', {
            'fields': ('enterprise', 'sale', 'customer')
        }),
        ('Cuota', {
            'fields': ('quota_number', 'plan_name', 'total_plan')
        }),
        ('Montos', {
            'fields': ('amount', 'interest')
        }),
        ('Fechas', {
            'fields': ('due_date', 'payment_date')
        }),
        ('Estado', {
            'fields': ('status', 'notes')
        }),
        ('Fechas de Sistema', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    readonly_fields = ('created_at', 'updated_at')
    ordering = ['-due_date']
