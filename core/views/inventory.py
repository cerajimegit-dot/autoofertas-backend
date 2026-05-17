from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers

from core.models import Brand, VehicleModel, ExchangeRate, Vehicle
from core.models.inventory import VehicleCost
from core.serializers import (
    BrandSerializer, VehicleModelSerializer, ExchangeRateSerializer,
    VehicleListSerializer, VehicleDetailSerializer, VehicleCostSerializer
)
from core.permissions import IsAuthenticated, IsEnterpriseOwnerOrAdmin


def catalog_cache(seconds=300):
    """Cache para listings que cambian muy poco (catalogos)."""
    def deco(view_func):
        view_func = vary_on_headers('Authorization')(view_func)
        view_func = cache_page(seconds)(view_func)
        return view_func
    return deco


@method_decorator(catalog_cache(300), name='list')
class BrandViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de marcas de vehículos"""
    serializer_class = BrandSerializer
    permission_classes = [IsAuthenticated, IsEnterpriseOwnerOrAdmin]

    # Marcas-basura de la migración (importer las creaba como fallback). Las
    # excluimos del listado para que nadie las elija al cargar un vehículo
    # nuevo, pero no las borramos por si algún vehículo viejo todavía las
    # referencia.
    PLACEHOLDER_BRAND_NAMES = ('MARCA', 'DUMMY')

    def get_queryset(self):
        if self.request.user and self.request.user.enterprise:
            qs = Brand.objects.filter(
                enterprise=self.request.user.enterprise,
                is_active=True,
            )
            # Sólo escondemos en list/retrieve. El admin de Django sigue viéndolas.
            if self.action in ('list', 'retrieve'):
                qs = qs.exclude(name__in=self.PLACEHOLDER_BRAND_NAMES)
            return qs
        return Brand.objects.none()
    
    def perform_create(self, serializer):
        serializer.save(enterprise=self.request.user.enterprise)


@method_decorator(catalog_cache(300), name='list')
class VehicleModelViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de modelos de vehículos"""
    serializer_class = VehicleModelSerializer
    permission_classes = [IsAuthenticated, IsEnterpriseOwnerOrAdmin]
    
    def get_queryset(self):
        if self.request.user and self.request.user.enterprise:
            queryset = VehicleModel.objects.filter(
                enterprise=self.request.user.enterprise,
                is_active=True
            )
            
            # Filtrar por marca si se especifica
            brand_id = self.request.query_params.get('brand')
            if brand_id:
                queryset = queryset.filter(brand_id=brand_id)
            
            return queryset
        return VehicleModel.objects.none()
    
    def perform_create(self, serializer):
        serializer.save(enterprise=self.request.user.enterprise)
    
    @action(detail=False, methods=['get'])
    def by_brand(self, request):
        """Obtener modelos de una marca específica"""
        brand_id = request.query_params.get('brand_id')
        if not brand_id:
            return Response(
                {'error': 'brand_id es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        models = self.get_queryset().filter(brand_id=brand_id)
        serializer = self.get_serializer(models, many=True)
        return Response(serializer.data)


class ExchangeRateViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de cotizaciones USD/PYG"""
    serializer_class = ExchangeRateSerializer
    permission_classes = [IsAuthenticated, IsEnterpriseOwnerOrAdmin]
    
    def get_queryset(self):
        if self.request.user and self.request.user.enterprise:
            return ExchangeRate.objects.filter(
                enterprise=self.request.user.enterprise
            ).order_by('-date')
        return ExchangeRate.objects.none()
    
    def perform_create(self, serializer):
        serializer.save(enterprise=self.request.user.enterprise)
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """Obtener la cotización actual (más reciente)"""
        exchange_rate = self.get_queryset().filter(is_active=True).first()
        if exchange_rate:
            serializer = self.get_serializer(exchange_rate)
            return Response(serializer.data)
        return Response(
            {'error': 'No hay cotización activa'},
            status=status.HTTP_404_NOT_FOUND
        )


class VehicleViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de vehículos (inventario)"""
    permission_classes = [IsAuthenticated, IsEnterpriseOwnerOrAdmin]

    def get_queryset(self):
        from django.db.models import Case, When, IntegerField

        queryset = Vehicle.objects.select_related(
            'brand', 'model', 'branch'
        ).all()

        if self.request.user and self.request.user.enterprise:
            queryset = queryset.filter(enterprise=self.request.user.enterprise)

        # Filtros adicionales
        branch_id = self.request.query_params.get('branch')
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)

        state = self.request.query_params.get('state')
        if state:
            queryset = queryset.filter(state=state)

        brand_id = self.request.query_params.get('brand')
        if brand_id:
            queryset = queryset.filter(brand_id=brand_id)

        year = self.request.query_params.get('year')
        if year:
            queryset = queryset.filter(year=year)

        # Orden por defecto:
        #   1) disponibles primero, después reservados, mantenimiento y al final vendidos
        #   2) dentro de cada estado, más recientes primero
        # Esto coincide con el flujo del vendedor: "qué tengo para ofrecer hoy".
        state_order = Case(
            When(state='available',   then=0),
            When(state='reserved',    then=1),
            When(state='maintenance', then=2),
            When(state='sold',        then=3),
            default=9,
            output_field=IntegerField(),
        )
        return queryset.annotate(_state_order=state_order).order_by(
            '_state_order', '-created_at'
        )
    
    def get_serializer_class(self):
        if self.action in ['list']:
            return VehicleListSerializer
        return VehicleDetailSerializer
    
    def perform_create(self, serializer):
        from core.models import Branch
        user = self.request.user
        # branches_managed.first() devuelve None si el usuario no gerencia sucursales
        # (p.ej. el admin). Caemos entonces a la primera sucursal de la empresa.
        branch = user.branches_managed.first() or Branch.objects.filter(
            enterprise=user.enterprise
        ).first()
        serializer.save(enterprise=user.enterprise, branch=branch)
    
    @action(detail=False, methods=['get'])
    def by_state(self, request):
        """Obtener vehículos por estado"""
        state = request.query_params.get('state')
        if not state:
            return Response(
                {'error': 'state es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        vehicles = self.get_queryset().filter(state=state)
        serializer = VehicleListSerializer(vehicles, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def available(self, request):
        """Obtener solo vehículos disponibles"""
        vehicles = (
            self.get_queryset()
            .filter(state='available')
            .select_related('brand', 'model', 'branch')
        )
        serializer = VehicleListSerializer(vehicles, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stock_summary(self, request):
        """Obtener resumen de stock por rama y estado"""
        queryset = self.get_queryset()
        
        summary = queryset.values('branch__name', 'state').annotate(
            count=Count('id')
        ).order_by('branch__name', 'state')
        
        return Response(summary)
    
    @action(detail=False, methods=['get'])
    def valorized_stock(self, request):
        """Obtener stock valorizado por sucursal"""
        from django.db.models import F, Sum, DecimalField, ExpressionWrapper
        
        queryset = self.get_queryset().filter(state='available')
        
        valorized = queryset.values('branch__name').annotate(
            total_vehicles=Count('id'),
            total_value=Sum(
                ExpressionWrapper(F('price'), output_field=DecimalField())
            ),
            average_price=Sum(F('price')) / Count('id')
        ).order_by('branch__name')

        return Response(valorized)


class VehicleCostViewSet(viewsets.ModelViewSet):
    """ViewSet para costos extras de vehículos (conceptos flexibles)."""
    serializer_class = VehicleCostSerializer
    permission_classes = [IsAuthenticated, IsEnterpriseOwnerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if not (user and user.enterprise):
            return VehicleCost.objects.none()
        qs = VehicleCost.objects.filter(enterprise=user.enterprise)
        # Filtrar por vehículo si se pide ?vehicle=ID
        vehicle_id = self.request.query_params.get('vehicle')
        if vehicle_id:
            qs = qs.filter(vehicle_id=vehicle_id)
        return qs.order_by('vehicle_id', 'order', 'id')

    def perform_create(self, serializer):
        serializer.save(enterprise=self.request.user.enterprise)
