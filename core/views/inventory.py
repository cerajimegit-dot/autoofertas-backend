from datetime import timedelta
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers

from core.models import Brand, VehicleModel, ExchangeRate, Vehicle
from core.models.inventory import VehicleCost, VehicleImage
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
    
    @action(detail=True, methods=['get', 'post'])
    def images(self, request, pk=None):
        """GET: lista fotos del vehiculo. POST: sube una nueva (multipart)."""
        vehicle = self.get_object()
        if request.method == 'POST':
            file = request.FILES.get('image')
            if not file:
                return Response({'error': 'Falta el campo image'}, status=400)
            order = int(request.data.get('order', 0))
            img = VehicleImage.objects.create(vehicle=vehicle, image=file, order=order)
            return Response({
                'id': img.id,
                'url': request.build_absolute_uri(img.image.url),
                'order': img.order,
            }, status=201)
        # GET
        imgs = VehicleImage.objects.filter(vehicle=vehicle).order_by('order', 'id')
        data = [{
            'id': i.id,
            'url': request.build_absolute_uri(i.image.url) if i.image else None,
            'order': i.order,
        } for i in imgs]
        return Response(data)

    @action(detail=True, methods=['delete'], url_path='images/(?P<img_id>[^/.]+)')
    def delete_image(self, request, pk=None, img_id=None):
        vehicle = self.get_object()
        img = VehicleImage.objects.filter(vehicle=vehicle, id=img_id).first()
        if not img:
            return Response({'error': 'Foto no encontrada'}, status=404)
        img.image.delete(save=False)
        img.delete()
        return Response(status=204)

    @action(detail=True, methods=['get'])
    def costs(self, request, pk=None):
        """Lista los gastos extra (VehicleCost) imputados a este vehiculo.

        Devuelve concept, amount, currency, exchange_rate. La UI usa esto en
        la ficha /vehicles/:id para el panel Balance de Unidad.
        """
        from core.models import VehicleCost
        vehicle = self.get_object()
        costs = VehicleCost.objects.filter(vehicle=vehicle).order_by('-id')
        data = [{
            'id': c.id,
            'concept': c.concept,
            'amount': str(c.amount),
            'currency': c.currency,
            'exchange_rate': str(c.exchange_rate) if c.exchange_rate else None,
        } for c in costs]
        return Response(data)

    @action(detail=False, methods=['get'])
    def stuck(self, request):
        """Lista vehículos available que llevan ≥ `days` días en stock.

        El backend deja `Vehicle.created_at` cuando entra el vehículo al
        sistema, y `Sale.save()` cambia automáticamente el state a
        'sold'. Por lo tanto, un vehículo `state='available'` con
        `created_at` viejo es uno que NO se vendió todavía.

        Query params:
          - `days`: umbral en días (default 90, mín 7, máx 720).
          - `branch`: filtra por sucursal.

        Devuelve hasta 200 vehículos (suficiente para revisión manual),
        ordenados por `created_at` ascendente (los más viejos primero).
        Cada item lleva un campo extra `days_in_stock` para que la UI
        no tenga que calcularlo.
        """
        from datetime import date
        try:
            days = int(request.query_params.get('days', 90))
        except ValueError:
            days = 90
        days = max(7, min(days, 720))

        today = date.today()
        cutoff = today - timedelta(days=days)

        qs = self.get_queryset().filter(
            state='available', created_at__date__lt=cutoff,
        )
        # `get_queryset` ya respeta `?branch=`, no repetimos.
        qs = qs.order_by('created_at')[:200]

        data = VehicleListSerializer(qs, many=True).data
        # Adjuntamos days_in_stock para que el frontend pinte bien.
        by_id = {v.id: v for v in qs}
        for item in data:
            v = by_id.get(item['id'])
            if v and v.created_at:
                item['days_in_stock'] = (today - v.created_at.date()).days
            else:
                item['days_in_stock'] = None
        return Response({
            'days_threshold': days,
            'count': len(data),
            'results': data,
        })

    @action(detail=False, methods=['get'])
    def price_suggestion(self, request):
        """Sugerencia de precio basada en ventas históricas.

        Acepta `brand`, `model`, `year`. Busca ventas cerradas (status =
        'completed') de vehículos con el mismo brand+model y devuelve
        min/max/mediana/promedio. Si no hay matches exactos del año,
        amplía progresivamente la ventana hasta ±2 años, luego "cualquier
        año del modelo".

        El frontend usa esto como hint, no como precio forzado — el
        usuario sigue tipeando el precio a mano si quiere.

        Devuelve `matches=0` cuando no hay ninguna venta histórica del
        modelo (caso de un modelo recién creado).
        """
        from core.models import Sale  # import local para evitar ciclo
        from statistics import median, mean

        brand_id = request.query_params.get('brand')
        model_id = request.query_params.get('model')
        try:
            year = int(request.query_params.get('year') or 0)
        except ValueError:
            year = 0

        if not (brand_id and model_id):
            return Response({'matches': 0, 'reason': 'missing_brand_or_model'})

        user = request.user
        if not (user and user.enterprise):
            return Response({'matches': 0})

        base = Sale.objects.filter(
            enterprise=user.enterprise,
            vehicle__brand_id=brand_id,
            vehicle__model_id=model_id,
            status='completed',
            total_price__gt=0,   # ignoramos ventas con precio 0 (basura de la migración)
        ).select_related('vehicle')

        def summarize(qs, scope):
            prices = [float(p) for p in qs.values_list('total_price', flat=True) if p]
            if not prices:
                return None
            recent = list(
                qs.order_by('-sale_date').values(
                    'sale_number', 'sale_date', 'total_price', 'vehicle__year',
                )[:3]
            )
            return {
                'matches': len(prices),
                'scope':   scope,
                'min':     min(prices),
                'max':     max(prices),
                'median':  median(prices),
                'mean':    mean(prices),
                'recent_examples': [
                    {
                        'sale_number': r['sale_number'],
                        'sale_date':   r['sale_date'].isoformat() if r['sale_date'] else None,
                        'total_price': float(r['total_price']),
                        'year':        r['vehicle__year'],
                    } for r in recent
                ],
            }

        # 1) Año exacto
        if year:
            result = summarize(base.filter(vehicle__year=year), 'exact_year')
            if result:
                return Response(result)
            # 2) Ventana ±2 años
            window = base.filter(vehicle__year__gte=year - 2,
                                  vehicle__year__lte=year + 2)
            result = summarize(window, 'year_window_2')
            if result:
                return Response(result)

        # 3) Cualquier año del modelo
        result = summarize(base, 'any_year')
        if result:
            return Response(result)

        return Response({'matches': 0, 'scope': 'none'})

    # Cache de feature-flag pg_trgm — sigue el mismo pattern que
    # CustomerViewSet._has_pg_trgm.
    _pg_trgm_available = None

    @classmethod
    def _has_pg_trgm(cls):
        from django.db import connection
        if cls._pg_trgm_available is None:
            if connection.vendor != 'postgresql':
                cls._pg_trgm_available = False
            else:
                try:
                    with connection.cursor() as c:
                        c.execute("SELECT similarity('a', 'a');")
                        c.fetchone()
                    cls._pg_trgm_available = True
                except Exception:
                    cls._pg_trgm_available = False
        return cls._pg_trgm_available

    @action(detail=False, methods=['get'])
    def search(self, request):
        """Busca vehículos para el palette global (Ctrl+K).

        Filtra por VIN (con tolerancia a typos vía pg_trgm cuando está),
        marca, modelo, año (exacto si q es numérico).

        Estrategia:
          - Si pg_trgm está disponible: aplicamos similarity() sobre vin
            como criterio adicional (UNION-like a las matches ILIKE),
            ordenado por mejor similaridad primero. Esto permite que
            "JTDDT123" matchee "JTDBT123" (typo de letra).
          - Fallback: ILIKE puro como antes.
        """
        from django.db.models import Q
        q = (request.query_params.get('q') or '').strip()
        if len(q) < 2:
            return Response({'results': []})
        try:
            limit = min(int(request.query_params.get('limit', 8)), 30)
        except ValueError:
            limit = 8

        qs = self.get_queryset()
        used = 'ilike'

        if self._has_pg_trgm() and len(q) >= 4:
            # pg_trgm sobre VIN: similarity > 0.3 (config razonable para
            # códigos alfanuméricos cortos). Combinamos OR con los otros
            # criterios para no perder matches por marca/modelo.
            qs = qs.extra(
                select={
                    'sim_vin': 'similarity(vin, %s)',
                },
                select_params=[q],
                where=[
                    "(vin %% %s "
                    " OR vin ILIKE %s"
                    " OR LOWER(COALESCE((SELECT name FROM core_brand WHERE id=core_vehicle.brand_id), '')) LIKE %s"
                    " OR LOWER(COALESCE((SELECT name FROM core_vehiclemodel WHERE id=core_vehicle.model_id), '')) LIKE %s)"
                ],
                params=[q, f'%{q}%', f'%{q.lower()}%', f'%{q.lower()}%'],
                order_by=['-sim_vin'],
            )[:limit]
            used = 'pg_trgm'
        else:
            cond = (
                Q(vin__icontains=q)
                | Q(brand__name__icontains=q)
                | Q(model__name__icontains=q)
            )
            if q.isdigit():
                cond |= Q(year=int(q))
            qs = qs.filter(cond)[:limit]

        data = [{
            'id': v.id,
            'vin': v.vin or '',
            'brand_name': v.brand.name if v.brand_id else '',
            'model_name': v.model.name if v.model_id else '',
            'year': v.year,
            'state': v.state,
            'state_display': v.get_state_display() if hasattr(v, 'get_state_display') else v.state,
        } for v in qs]
        return Response({'results': data, 'used': used})

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
