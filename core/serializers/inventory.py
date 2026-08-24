from rest_framework import serializers
from core.models import Brand, Supplier, VehicleModel, ExchangeRate, Vehicle
from core.models.inventory import VehicleCost


class SupplierSerializer(serializers.ModelSerializer):
    """Serializador para Supplier (proveedor de servicios)."""

    costs_count = serializers.SerializerMethodField()

    class Meta:
        model = Supplier
        fields = (
            'id', 'name', 'phone', 'notes', 'is_active',
            'costs_count', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'costs_count', 'created_at', 'updated_at')

    def get_costs_count(self, obj):
        return obj.costs.count()


class BrandSerializer(serializers.ModelSerializer):
    """Serializador para Brand"""
    enterprise_name = serializers.CharField(source='enterprise.name', read_only=True)
    models_count = serializers.SerializerMethodField()

    class Meta:
        model = Brand
        fields = (
            'id', 'enterprise', 'enterprise_name', 'name', 'description',
            'image', 'is_active', 'models_count', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'enterprise', 'created_at', 'updated_at')
    
    def get_models_count(self, obj):
        return obj.models.count()


class VehicleModelSerializer(serializers.ModelSerializer):
    """Serializador para VehicleModel"""
    enterprise_name = serializers.CharField(source='enterprise.name', read_only=True)
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    vehicles_count = serializers.SerializerMethodField()

    class Meta:
        model = VehicleModel
        fields = (
            'id', 'enterprise', 'enterprise_name', 'brand', 'brand_name',
            'name', 'description', 'image', 'is_active', 'vehicles_count',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'enterprise', 'created_at', 'updated_at')
    
    def get_vehicles_count(self, obj):
        return obj.vehicle_set.count()


class ExchangeRateSerializer(serializers.ModelSerializer):
    """Serializador para ExchangeRate"""
    enterprise_name = serializers.CharField(source='enterprise.name', read_only=True)
    
    class Meta:
        model = ExchangeRate
        fields = (
            'id', 'enterprise', 'enterprise_name', 'rate', 'source',
            'date', 'is_active', 'created_at'
        )
        read_only_fields = ('id', 'date', 'created_at')


class VehicleCostSerializer(serializers.ModelSerializer):
    """Serializador para costos extras de vehículos"""

    supplier_name = serializers.CharField(source='supplier.name', read_only=True, default=None)

    class Meta:
        model = VehicleCost
        fields = (
            'id', 'enterprise', 'vehicle', 'concept', 'amount', 'currency',
            'exchange_rate',
            'date', 'supplier', 'supplier_name',
            'notes', 'order', 'created_at', 'updated_at',
        )
        # enterprise lo asigna el ViewSet
        read_only_fields = ('id', 'enterprise', 'supplier_name', 'created_at', 'updated_at')

    def validate(self, attrs):
        """USD exige exchange_rate. Replicamos la validación del modelo
        a nivel serializer para que DRF devuelva 400 con field errors
        en lugar de un 500 de ValidationError sin atajar.
        """
        currency = attrs.get('currency', getattr(self.instance, 'currency', 'PYG'))
        exchange_rate = attrs.get('exchange_rate',
                                  getattr(self.instance, 'exchange_rate', None))
        if currency == 'USD' and not exchange_rate:
            raise serializers.ValidationError({
                'exchange_rate': 'Es obligatorio cargar el tipo de cambio cuando '
                                 'la moneda es USD.'
            })
        return attrs


class VehicleListSerializer(serializers.ModelSerializer):
    """Serializador de lista para Vehicle (sin detalles de costos)"""
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    model_name = serializers.CharField(source='model.name', read_only=True)
    state_display = serializers.CharField(source='get_state_display', read_only=True)
    
    class Meta:
        model = Vehicle
        fields = (
            'id', 'branch', 'branch_name', 'brand', 'brand_name',
            'model', 'model_name', 'year', 'vin', 'license_plate',
            'color', 'price', 'currency', 'state', 'state_display', 'created_at'
        )
        read_only_fields = ('id', 'created_at')


class VehicleDetailSerializer(serializers.ModelSerializer):
    """Serializador detallado para Vehicle"""
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    model_name = serializers.CharField(source='model.name', read_only=True)
    enterprise_name = serializers.CharField(source='enterprise.name', read_only=True)
    exchange_rate_value = serializers.DecimalField(
        source='exchange_rate.rate',
        read_only=True,
        decimal_places=2,
        max_digits=10
    )
    total_cost = serializers.SerializerMethodField()
    state_display = serializers.CharField(source='get_state_display', read_only=True)
    currency_display = serializers.CharField(source='get_currency_display', read_only=True)
    extra_costs = VehicleCostSerializer(many=True, read_only=True)

    class Meta:
        model = Vehicle
        fields = (
            'id', 'enterprise', 'enterprise_name', 'branch', 'branch_name',
            'brand', 'brand_name', 'model', 'model_name', 'year', 'vin',
            'license_plate', 'color', 'mileage', 'fob', 'container',
            'dispatch', 'cam_vol', 'total_cost', 'price', 'currency',
            'currency_display', 'exchange_rate', 'exchange_rate_value',
            'state', 'state_display', 'description', 'image',
            'extra_costs',
            'created_at', 'updated_at'
        )
        # enterprise y branch los asigna perform_create a partir del usuario
        read_only_fields = ('id', 'enterprise', 'branch', 'created_at', 'updated_at', 'total_cost')
    
    def get_total_cost(self, obj):
        return obj.total_cost
    
    def validate(self, data):
        # Validar que si es USD, tiene cotización
        currency = data.get('currency', self.instance.currency if self.instance else None)
        exchange_rate = data.get('exchange_rate', self.instance.exchange_rate if self.instance else None)
        
        if currency == 'USD' and not exchange_rate:
            raise serializers.ValidationError({
                'exchange_rate': 'Debe proporcionar una cotización para precios en USD'
            })
        
        return data
