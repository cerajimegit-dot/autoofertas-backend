from rest_framework import serializers
from core.models import Customer, PaymentForm, Sale, Quotum
from datetime import datetime, timedelta


class CustomerSerializer(serializers.ModelSerializer):
    """Serializador para Customer.

    `sales_count` se lee de una anotación que pone el ViewSet
    (`get_queryset` agrega `Count('sales')`). Antes era un
    SerializerMethodField que disparaba un COUNT por cada cliente —
    ~300 queries para abrir la página de Ventas. Con la anotación es
    1 query global.
    """
    enterprise_name = serializers.CharField(source='enterprise.name', read_only=True)
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    sales_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Customer
        fields = (
            'id', 'enterprise', 'enterprise_name', 'is_generic',
            'first_name', 'last_name', 'document_type', 'document_type_display',
            'document_number', 'email', 'phone', 'address', 'city',
            'notes', 'sales_count', 'created_at', 'updated_at'
        )
        # `enterprise` se asigna en perform_create del ViewSet a partir del
        # usuario autenticado — no debe pedirse al frontend.
        read_only_fields = ('id', 'enterprise', 'created_at', 'updated_at')
        unique_together = ('enterprise', 'document_number')


class PaymentFormSerializer(serializers.ModelSerializer):
    """Serializador para PaymentForm"""
    enterprise_name = serializers.CharField(source='enterprise.name', read_only=True)

    class Meta:
        model = PaymentForm
        fields = (
            'id', 'enterprise', 'enterprise_name', 'name', 'description',
            'is_active', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'enterprise', 'created_at', 'updated_at')


class SaleListSerializer(serializers.ModelSerializer):
    """Serializador de lista para Sale.

    `status` es el estado del CONTRATO (Reserva/Cerrada/Cancelada).
    `collection_status` es el estado de COBRANZA calculado en línea
    desde las cuotas + payment_form. Una venta puede estar Cerrada
    pero `collection_status='overdue'` si tiene cuotas vencidas.
    """
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    customer_name = serializers.SerializerMethodField()
    vehicle_info = serializers.SerializerMethodField()
    vehicle_vin = serializers.CharField(source='vehicle.vin', read_only=True)
    payment_form_name = serializers.CharField(source='payment_form.name', read_only=True)
    seller_name = serializers.CharField(source='seller.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    # Estado de cobranza
    collection_status = serializers.CharField(read_only=True)
    collection_status_display = serializers.CharField(read_only=True)
    collection_summary = serializers.JSONField(read_only=True)

    class Meta:
        model = Sale
        fields = (
            'id', 'sale_number', 'sale_date', 'branch', 'branch_name',
            'customer', 'customer_name', 'vehicle', 'vehicle_info', 'vehicle_vin',
            'total_price', 'down_payment', 'payment_form_name', 'seller_name',
            'status', 'status_display',
            'collection_status', 'collection_status_display', 'collection_summary',
        )
        read_only_fields = fields
    
    def get_customer_name(self, obj):
        if obj.customer:
            return obj.customer.full_name
        return 'N/A'
    
    def get_vehicle_info(self, obj):
        if obj.vehicle:
            brand = obj.vehicle.brand.name if obj.vehicle.brand else ''
            model = obj.vehicle.model.name if obj.vehicle.model else ''
            return f"{brand} {model} ({obj.vehicle.year})".strip()
        return 'N/A'


class SaleDetailSerializer(serializers.ModelSerializer):
    """Serializador detallado para Sale"""
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    customer_detail = CustomerSerializer(source='customer', read_only=True)
    vehicle_detail = serializers.SerializerMethodField()
    payment_form_detail = PaymentFormSerializer(source='payment_form', read_only=True)
    seller_name = serializers.CharField(source='seller.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    quotas_detail = serializers.SerializerMethodField()
    
    class Meta:
        model = Sale
        fields = (
            'id', 'sale_number', 'sale_date', 'branch', 'branch_name',
            'customer', 'customer_detail', 'vehicle', 'vehicle_detail',
            'unit_price', 'discount', 'total_price', 'down_payment',
            'payment_form', 'payment_form_detail', 'seller', 'seller_name',
            'status', 'status_display', 'notes', 'quotas_detail',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_vehicle_detail(self, obj):
        if obj.vehicle:
            return {
                'id': obj.vehicle.id,
                'vin': obj.vehicle.vin,
                'brand': obj.vehicle.brand.name,
                'model': obj.vehicle.model.name,
                'year': obj.vehicle.year,
                'price': str(obj.vehicle.price)
            }
        return None
    
    def get_quotas_detail(self, obj):
        from .sales import QuotumSerializer
        quotas = obj.quotas.all()
        return QuotumSerializer(quotas, many=True).data


class QuotumListSerializer(serializers.ModelSerializer):
    """Serializador de lista para Quotum.

    `is_overdue` y `effective_status` se leen de propiedades del modelo
    que se calculan en línea. Antes había una versión local del cálculo
    que sólo consideraba `status='pending'` y dejaba afuera las 62 cuotas
    legacy con `status='overdue'` literal. Ahora todo pasa por
    `Quotum.is_overdue`.
    """
    sale_number = serializers.CharField(source='sale.sale_number', read_only=True)
    customer_id = serializers.IntegerField(source='customer.id', read_only=True, allow_null=True)
    customer_name = serializers.CharField(source='customer.full_name', read_only=True, allow_null=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    days_until_due = serializers.SerializerMethodField()
    is_overdue = serializers.BooleanField(read_only=True)
    effective_status = serializers.CharField(read_only=True)

    class Meta:
        model = Quotum
        fields = (
            'id', 'sale', 'sale_number', 'customer_id', 'customer_name',
            'quota_number', 'plan_name', 'total_plan',
            'amount', 'interest', 'due_date', 'payment_date', 'cancelled_date',
            'status', 'status_display', 'effective_status',
            'payment_method', 'payment_method_display',
            'days_until_due', 'is_overdue',
        )
        read_only_fields = fields

    def get_days_until_due(self, obj):
        from datetime import date
        if not obj.due_date:
            return 0
        days = (obj.due_date - date.today()).days
        return days  # negativo si está vencida — útil para mostrar "-12 días"


class QuotumDetailSerializer(serializers.ModelSerializer):
    """Serializador detallado para Quotum."""
    sale_number = serializers.CharField(source='sale.sale_number', read_only=True)
    customer_detail = CustomerSerializer(source='customer', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    days_until_due = serializers.SerializerMethodField()
    is_overdue = serializers.BooleanField(read_only=True)
    effective_status = serializers.CharField(read_only=True)

    class Meta:
        model = Quotum
        fields = (
            'id', 'sale', 'sale_number', 'customer', 'customer_detail',
            'quota_number', 'plan_name', 'total_plan', 'amount', 'interest',
            'due_date', 'payment_date', 'cancelled_date',
            'status', 'status_display', 'effective_status',
            'payment_method', 'payment_method_display',
            'notes', 'days_until_due', 'is_overdue',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_days_until_due(self, obj):
        from datetime import date
        if not obj.due_date:
            return 0
        return (obj.due_date - date.today()).days

    def update(self, instance, validated_data):
        # Si el estado es 'paid', registrar la fecha de pago
        if validated_data.get('status') == 'paid' and instance.status != 'paid':
            from datetime import date
            instance.payment_date = date.today()

        return super().update(instance, validated_data)


QuotumSerializer = QuotumDetailSerializer
