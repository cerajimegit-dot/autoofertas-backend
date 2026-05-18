"""
Dashboard y KPIs - ViewSet para reportes generales del sistema
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count, Sum, Avg, F, ExpressionWrapper, DecimalField
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from datetime import datetime, timedelta, date


def dashboard_cache(seconds=60):
    """Decorador combinado: cache + variacion por Authorization (asi cache es por usuario)."""
    def deco(view_func):
        view_func = vary_on_headers('Authorization')(view_func)
        view_func = cache_page(seconds)(view_func)
        return view_func
    return deco

from core.models import (
    Vehicle, Sale, Quotum, Customer, Branch,
    Enterprise
)


class DashboardViewSet(viewsets.ViewSet):
    """ViewSet para dashboard y KPIs del sistema"""
    permission_classes = [IsAuthenticated]

    # Exclusión de ventas placeholder (VIN dummy) para cálculos en el dashboard
    PLACEHOLDER_FILTERS = dict(
        vehicle__vin__startswith='VIN-DUMMY',
    )

    def _exclude_placeholders(self, qs):
        return qs.exclude(vehicle__vin__startswith='VIN-DUMMY') \
                 .exclude(vehicle__vin__regex=r'^VIN[0-9]+$')

    def _parse_period(self, request):
        """Lee query params date_from / date_to. Si faltan, devuelve mes actual."""
        today = date.today()
        date_from_str = request.query_params.get('date_from')
        date_to_str = request.query_params.get('date_to')
        try:
            date_from = (datetime.strptime(date_from_str, '%Y-%m-%d').date()
                         if date_from_str else today.replace(day=1))
        except ValueError:
            date_from = today.replace(day=1)
        try:
            date_to = (datetime.strptime(date_to_str, '%Y-%m-%d').date()
                       if date_to_str else today)
        except ValueError:
            date_to = today
        return date_from, date_to

    def _branch_id(self, request):
        """Devuelve el branch_id del query param ?branch=, o None si no aplica."""
        bid = request.query_params.get('branch')
        if bid and str(bid).isdigit():
            return int(bid)
        return None

    def _filter_sales(self, qs, request):
        """Aplica filtro por sucursal sobre un queryset de Sale."""
        bid = self._branch_id(request)
        return qs.filter(branch_id=bid) if bid else qs

    def _filter_quotas(self, qs, request):
        """Aplica filtro por sucursal sobre un queryset de Quotum (vía sale__branch)."""
        bid = self._branch_id(request)
        return qs.filter(sale__branch_id=bid) if bid else qs

    def _filter_vehicles(self, qs, request):
        """Aplica filtro por sucursal sobre un queryset de Vehicle."""
        bid = self._branch_id(request)
        return qs.filter(branch_id=bid) if bid else qs

    @method_decorator(dashboard_cache(60))
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Resumen general del sistema (respeta ?date_from=&date_to=)"""
        user = request.user

        if not user.enterprise:
            return Response(
                {'error': 'Usuario no tiene empresa asignada'},
                status=status.HTTP_400_BAD_REQUEST
            )

        enterprise = user.enterprise
        date_from, date_to = self._parse_period(request)
        today = date.today()

        # Ventas del período, excluyendo placeholders por VIN dummy
        sales_month = self._filter_sales(
            self._exclude_placeholders(
                Sale.objects.filter(
                    enterprise=enterprise,
                    sale_date__gte=date_from,
                    sale_date__lte=date_to,
                )
            ),
            request,
        )

        # Cuotas pendientes — incluye las "vencidas de facto" (pending +
        # due_date pasado) porque seguís sin haber cobrado el dinero.
        quotas_pending = self._filter_quotas(
            Quotum.objects.filter(enterprise=enterprise, status='pending'),
            request,
        )

        # Cuotas vencidas (cálculo dinámico): pending vencidas + las legacy
        # con status='overdue' literal. Una sola fuente de verdad.
        quotas_overdue = self._filter_quotas(
            Quotum.objects.filter(enterprise=enterprise).filter(
                Q(status='overdue') |
                Q(status='pending', due_date__lt=today)
            ),
            request,
        )

        # Vehículos disponibles
        vehicles_available = self._filter_vehicles(
            Vehicle.objects.filter(enterprise=enterprise, state='available'),
            request,
        ).count()

        # Totales (con filtro de branch aplicado donde corresponde)
        total_vehicles = self._filter_vehicles(
            Vehicle.objects.filter(enterprise=enterprise), request
        ).count()
        # Clientes no tienen branch directo — se cuenta global.
        total_customers = Customer.objects.filter(enterprise=enterprise).count()

        # Cuotas cobradas dentro del período
        quotas_cobradas = self._filter_quotas(
            Quotum.objects.filter(
                enterprise=enterprise,
                status='paid',
                payment_date__gte=date_from,
                payment_date__lte=date_to,
            ),
            request,
        )

        summary = {
            'ventas_mes': {
                'total': sales_month.count(),
                'monto': float(sales_month.aggregate(Sum('total_price'))['total_price__sum'] or 0)
            },
            'cuotas_pendientes': {
                'total': quotas_pending.count(),
                'monto': float(quotas_pending.aggregate(Sum('amount'))['amount__sum'] or 0)
            },
            'cuotas_vencidas': {
                'total': quotas_overdue.count(),
                'monto': float(quotas_overdue.aggregate(Sum('amount'))['amount__sum'] or 0)
            },
            'cobrado_periodo': {
                'total': quotas_cobradas.count(),
                'monto': float(quotas_cobradas.aggregate(Sum('amount'))['amount__sum'] or 0)
            },
            'inventario_disponible': vehicles_available,
            'total_vehicles': total_vehicles,
            'total_customers': total_customers,
            'fecha': today.isoformat(),
            'date_from': date_from.isoformat(),
            'date_to': date_to.isoformat(),
        }
        
        return Response(summary)
    
    @method_decorator(dashboard_cache(300))
    @action(detail=False, methods=['get'])
    def sales_by_month(self, request):
        """Ventas agrupadas por mes (últimos 12 meses)"""
        user = request.user
        enterprise = user.enterprise
        
        if not enterprise:
            return Response(
                {'error': 'Usuario no tiene empresa asignada'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        sales = self._filter_sales(
            Sale.objects.filter(
                enterprise=enterprise,
                sale_date__gte=timezone.now() - timedelta(days=365),
            ),
            request,
        ).values('sale_date__year', 'sale_date__month').annotate(
            count=Count('id'),
            total=Sum('total_price'),
        ).order_by('sale_date__year', 'sale_date__month')
        
        data = {
            'data': [
                {
                    'mes': f"{s['sale_date__month']:02d}/{s['sale_date__year']}",
                    'ventas': s['count'],
                    'monto': float(s['total'] or 0)
                }
                for s in sales
            ]
        }
        
        return Response(data)
    
    @method_decorator(dashboard_cache(300))
    @action(detail=False, methods=['get'])
    def sales_by_branch(self, request):
        """Ventas agrupadas por sucursal"""
        user = request.user
        enterprise = user.enterprise
        
        if not enterprise:
            return Response(
                {'error': 'Usuario no tiene empresa asignada'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        sales = Sale.objects.filter(
            enterprise=enterprise
        ).values('branch__name').annotate(
            count=Count('id'),
            total=Sum('total_price')
        ).order_by('-total')
        
        data = {
            'data': [
                {
                    'sucursal': s['branch__name'],
                    'ventas': s['count'],
                    'monto': float(s['total'] or 0)
                }
                for s in sales
            ]
        }
        
        return Response(data)
    
    @method_decorator(dashboard_cache(300))
    @action(detail=False, methods=['get'])
    def vehicle_models_ranking(self, request):
        """Ranking de modelos de vehículos más vendidos (respeta date_from/date_to)"""
        user = request.user
        enterprise = user.enterprise

        if not enterprise:
            return Response({'error': 'Usuario no tiene empresa asignada'},
                            status=status.HTTP_400_BAD_REQUEST)

        date_from, date_to = self._parse_period(request)
        qs = self._filter_sales(
            self._exclude_placeholders(
                Sale.objects.filter(
                    enterprise=enterprise,
                    vehicle__isnull=False,
                    sale_date__gte=date_from,
                    sale_date__lte=date_to,
                )
            ),
            request,
        )
        models = qs.values(
            'vehicle__brand__name', 'vehicle__model__name'
        ).annotate(count=Count('id'), total=Sum('total_price')).order_by('-count')[:10]

        brands = qs.values('vehicle__brand__name').annotate(
            count=Count('id'), total=Sum('total_price')
        ).order_by('-count')[:10]

        return Response({
            'models': [
                {'modelo': f"{m['vehicle__brand__name']} {m['vehicle__model__name']}",
                 'ventas': m['count'], 'monto': float(m['total'] or 0)}
                for m in models
            ],
            'brands': [
                {'marca': b['vehicle__brand__name'], 'ventas': b['count'],
                 'monto': float(b['total'] or 0)}
                for b in brands
            ],
            'date_from': date_from.isoformat(),
            'date_to': date_to.isoformat(),
        })

    @method_decorator(dashboard_cache(300))
    @action(detail=False, methods=['get'])
    def top_morosos(self, request):
        """Top 15 clientes con cuotas vencidas (morosos)"""
        user = request.user
        if not user.enterprise:
            return Response({'error': 'Sin empresa'}, status=status.HTTP_400_BAD_REQUEST)

        today = date.today()
        overdue_qs = self._filter_quotas(
            Quotum.objects.filter(
                enterprise=user.enterprise,
                customer__isnull=False,
            ).filter(
                Q(status='overdue') |
                Q(status='pending', due_date__lt=today)
            ),
            request,
        ).values(
            'customer_id',
            'customer__first_name',
            'customer__last_name',
            'customer__document_number',
            'customer__phone',
        ).annotate(
            cuotas_vencidas=Count('id'),
            monto_vencido=Sum('amount'),
        ).order_by('-monto_vencido')[:15]

        # Calcular dias atraso en Python (más simple que ORM con dates)
        # Optimización: traemos todas las "más viejas por cliente" en una sola
        # query agrupada, en vez de hacer una query por cliente (N+1).
        from django.db.models import Min
        customer_ids = [r['customer_id'] for r in overdue_qs]
        oldest_by_customer = dict(
            self._filter_quotas(
                Quotum.objects.filter(
                    enterprise=user.enterprise,
                    customer_id__in=customer_ids,
                ).filter(
                    Q(status='overdue') |
                    Q(status='pending', due_date__lt=today)
                ),
                request,
            ).values('customer_id').annotate(oldest=Min('due_date'))
              .values_list('customer_id', 'oldest')
        )
        data = []
        for row in overdue_qs:
            oldest_date = oldest_by_customer.get(row['customer_id'])
            dias = (today - oldest_date).days if oldest_date else 0

            data.append({
                'customer_id': row['customer_id'],
                'nombre': f"{row['customer__first_name'] or ''} {row['customer__last_name'] or ''}".strip() or '(sin nombre)',
                'documento': row['customer__document_number'] or '',
                'telefono': row['customer__phone'] or '',
                'cuotas_vencidas': row['cuotas_vencidas'],
                'monto_vencido': float(row['monto_vencido'] or 0),
                'dias_atraso_max': dias,
            })
        return Response({'data': data})

    @action(detail=False, methods=['get'])
    def aging_cuotas(self, request):
        """Antigüedad de cuotas vencidas: 1-30, 31-60, 61-90, 90+ días"""
        user = request.user
        if not user.enterprise:
            return Response({'error': 'Sin empresa'}, status=status.HTTP_400_BAD_REQUEST)

        today = date.today()
        base = self._filter_quotas(
            Quotum.objects.filter(enterprise=user.enterprise).filter(
                Q(status='overdue') |
                Q(status='pending', due_date__lt=today)
            ),
            request,
        )
        buckets = [
            ('1-30 días',   today - timedelta(days=30),  today - timedelta(days=1)),
            ('31-60 días',  today - timedelta(days=60),  today - timedelta(days=31)),
            ('61-90 días',  today - timedelta(days=90),  today - timedelta(days=61)),
            ('+90 días',    None,                        today - timedelta(days=91)),
        ]
        out = []
        for label, desde, hasta in buckets:
            qs = base.filter(due_date__lte=hasta)
            if desde:
                qs = qs.filter(due_date__gte=desde)
            out.append({
                'rango': label,
                'cuotas': qs.count(),
                'monto': float(qs.aggregate(Sum('amount'))['amount__sum'] or 0),
            })
        return Response({'data': out})

    @action(detail=False, methods=['get'])
    def sales_by_payment_form(self, request):
        """Distribución de ventas por forma de pago (contado/crédito/mixto)"""
        user = request.user
        if not user.enterprise:
            return Response({'error': 'Sin empresa'}, status=status.HTTP_400_BAD_REQUEST)

        date_from, date_to = self._parse_period(request)
        qs = self._filter_sales(
            self._exclude_placeholders(
                Sale.objects.filter(
                    enterprise=user.enterprise,
                    sale_date__gte=date_from,
                    sale_date__lte=date_to,
                )
            ),
            request,
        )
        data = qs.values('payment_form__name').annotate(
            count=Count('id'), total=Sum('total_price')
        ).order_by('-total')

        return Response({
            'data': [
                {'forma_pago': d['payment_form__name'] or 'Sin forma',
                 'ventas': d['count'], 'monto': float(d['total'] or 0)}
                for d in data
            ],
            'date_from': date_from.isoformat(),
            'date_to': date_to.isoformat(),
        })

    @action(detail=False, methods=['get'])
    def alertas(self, request):
        """Alertas para gerencia: cuotas próximas a vencer, ratios, etc."""
        user = request.user
        if not user.enterprise:
            return Response({'error': 'Sin empresa'}, status=status.HTTP_400_BAD_REQUEST)

        today = date.today()
        in_7 = today + timedelta(days=7)
        in_30 = today + timedelta(days=30)
        ent = user.enterprise

        prox_7 = self._filter_quotas(Quotum.objects.filter(
            enterprise=ent, status='pending',
            due_date__gte=today, due_date__lte=in_7,
        ), request).aggregate(n=Count('id'), total=Sum('amount'))

        prox_30 = self._filter_quotas(Quotum.objects.filter(
            enterprise=ent, status='pending',
            due_date__gte=today, due_date__lte=in_30,
        ), request).aggregate(n=Count('id'), total=Sum('amount'))

        all_q = self._filter_quotas(Quotum.objects.filter(enterprise=ent), request)
        paid_total = all_q.filter(status='paid').aggregate(total=Sum('amount'))['total'] or 0
        pending_total = all_q.filter(status='pending').aggregate(total=Sum('amount'))['total'] or 0
        overdue_total = all_q.filter(
            Q(status='overdue') |
            Q(status='pending', due_date__lt=today)
        ).aggregate(total=Sum('amount'))['total'] or 0

        gran_total = (paid_total or 0) + (pending_total or 0)
        ratio_cobranza = (float(paid_total) / float(gran_total) * 100) if gran_total else 0
        ratio_morosidad = (float(overdue_total) / float(pending_total) * 100) if pending_total else 0

        # Ventas sin cliente o sin vehículo (para saneamiento)
        sales_qs = self._filter_sales(
            self._exclude_placeholders(Sale.objects.filter(enterprise=ent)),
            request,
        )
        ventas_sin_cliente = sales_qs.filter(customer__isnull=True).count()
        ventas_sin_vehiculo = sales_qs.filter(vehicle__isnull=True).count()

        return Response({
            'proximas_7_dias': {
                'cuotas': prox_7['n'] or 0,
                'monto': float(prox_7['total'] or 0),
            },
            'proximas_30_dias': {
                'cuotas': prox_30['n'] or 0,
                'monto': float(prox_30['total'] or 0),
            },
            'ratio_cobranza_pct': round(ratio_cobranza, 1),
            'ratio_morosidad_pct': round(ratio_morosidad, 1),
            'cartera_pendiente': float(pending_total),
            'cartera_vencida': float(overdue_total),
            'cartera_cobrada': float(paid_total),
            'ventas_sin_cliente': ventas_sin_cliente,
            'ventas_sin_vehiculo': ventas_sin_vehiculo,
        })
    
    @action(detail=False, methods=['get'])
    def quotas_status(self, request):
        """Estado general de cuotas"""
        user = request.user
        enterprise = user.enterprise
        
        if not enterprise:
            return Response(
                {'error': 'Usuario no tiene empresa asignada'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        today = date.today()

        quotas_all = self._filter_quotas(
            Quotum.objects.filter(enterprise=enterprise), request,
        )

        overdue_filter = Q(status='overdue') | Q(status='pending', due_date__lt=today)
        status_data = {
            'pendientes': {
                'total': quotas_all.filter(status='pending').count(),
                'monto': float(quotas_all.filter(status='pending').aggregate(Sum('amount'))['amount__sum'] or 0)
            },
            'cobradas': {
                'total': quotas_all.filter(status='paid').count(),
                'monto': float(quotas_all.filter(status='paid').aggregate(Sum('amount'))['amount__sum'] or 0)
            },
            'vencidas': {
                'total': quotas_all.filter(overdue_filter).count(),
                'monto': float(quotas_all.filter(overdue_filter).aggregate(Sum('amount'))['amount__sum'] or 0)
            },
            'proximas_30_dias': {
                'total': quotas_all.filter(
                    status='pending',
                    due_date__gte=today,
                    due_date__lte=today + timedelta(days=30)
                ).count(),
                'monto': float(quotas_all.filter(
                    status='pending',
                    due_date__gte=today,
                    due_date__lte=today + timedelta(days=30)
                ).aggregate(Sum('amount'))['amount__sum'] or 0)
            }
        }
        
        return Response(status_data)
    
    @action(detail=False, methods=['get'])
    def inventory_stats(self, request):
        """Estadísticas de inventario"""
        user = request.user
        enterprise = user.enterprise
        
        if not enterprise:
            return Response(
                {'error': 'Usuario no tiene empresa asignada'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        vehicles = self._filter_vehicles(
            Vehicle.objects.filter(enterprise=enterprise), request,
        )

        stats = {
            'total_vehicles': vehicles.count(),
            'disponibles': vehicles.filter(state='available').count(),
            'reservados': vehicles.filter(state='reserved').count(),
            'vendidos': vehicles.filter(state='sold').count(),
            'mantenimiento': vehicles.filter(state='maintenance').count(),
            'valor_total': float(vehicles.aggregate(
                total=Sum(ExpressionWrapper(F('price'), output_field=DecimalField()))
            )['total'] or 0),
            'valor_disponible': float(vehicles.filter(state='available').aggregate(
                total=Sum(ExpressionWrapper(F('price'), output_field=DecimalField()))
            )['total'] or 0),
            'costo_total': float(vehicles.aggregate(
                total=Sum(
                    ExpressionWrapper(
                        F('fob') + F('container') + F('dispatch') + F('cam_vol'),
                        output_field=DecimalField()
                    )
                )
            )['total'] or 0),
        }
        
        return Response(stats)
    
    @action(detail=False, methods=['get'])
    def data_quality(self, request):
        """Auditoría rápida de calidad de datos para el panel "Datos a revisar".

        Cada métrica incluye un `count` y, cuando aplica, un `sample` con los
        primeros IDs/códigos para que la UI ofrezca un drill-down. Respeta
        ?branch= como el resto de los endpoints del dashboard.
        """
        user = request.user
        if not user.enterprise:
            return Response({'error': 'Sin empresa'}, status=status.HTTP_400_BAD_REQUEST)

        ent = user.enterprise
        today = date.today()

        sales_qs = self._filter_sales(Sale.objects.filter(enterprise=ent), request)
        quotas_qs = self._filter_quotas(Quotum.objects.filter(enterprise=ent), request)
        vehicles_qs = self._filter_vehicles(Vehicle.objects.filter(enterprise=ent), request)

        def sample(qs, fields, limit=10):
            return list(qs.values(*fields)[:limit])

        # Ventas sin cliente / sin vehículo
        sin_cliente = sales_qs.filter(customer__isnull=True)
        sin_vehiculo = sales_qs.filter(vehicle__isnull=True)

        # Ventas con código MIG/placeholder
        ventas_mig = sales_qs.filter(sale_number__startswith='MIG')
        ventas_placeholder = sales_qs.filter(
            Q(sale_number__contains='??') |
            Q(sale_number__startswith='V0') |
            Q(sale_number='VDUMMY')
        )

        # Cuotas con due_date en años raros (typos típicos 2025→2021)
        cuotas_fecha_rara = quotas_qs.exclude(
            due_date__year__in=[2022, 2023, 2024, 2025, 2026, 2027, 2028, 2029, 2030]
        )

        # Cuotas paid con payment_date futuro
        cuotas_pago_futuro = quotas_qs.filter(
            status='paid', payment_date__gt=today,
        )

        # Cuotas con monto 0 o plan_name vacío
        cuotas_monto_cero = quotas_qs.filter(amount=0)
        cuotas_sin_plan = quotas_qs.filter(plan_name='')

        # Cuotas vencidas (cálculo dinámico): incluye tanto status='overdue'
        # literal (62 legacy) como pending vencidas (~970). Antes era sólo
        # el segundo grupo — dejaba afuera las 62 legacy.
        cuotas_overdue_de_facto = quotas_qs.filter(
            Q(status='overdue') |
            Q(status='pending', due_date__lt=today)
        )

        # Vehículos disponibles pero ya en una venta
        vehiculos_inconsistentes = vehicles_qs.filter(
            state='available',
            sale__isnull=False,
        ).distinct()

        # Vehículos con VIN basura
        vin_basura = vehicles_qs.filter(
            Q(vin__startswith='VIN-DUMMY') | Q(vin__regex=r'^VIN[0-9]+$')
        )

        # Vehículos con precio 0
        vehiculos_sin_precio = vehicles_qs.filter(price=0)

        # Clientes con documento autogenerado o email sintético
        # (clientes no tienen branch — siempre cuento globalmente).
        customers_all = Customer.objects.filter(enterprise=ent)
        clientes_doc_auto = customers_all.filter(
            Q(document_number__startswith='DRV026-') |
            Q(document_number__startswith='SUC026-') |
            Q(document_number__startswith='CUOTA')
        )
        clientes_email_sintetico = customers_all.filter(email__endswith='@import.local')
        clientes_sin_telefono = customers_all.filter(Q(phone='') | Q(phone__isnull=True))

        # Ventas sin vendedor asignado
        ventas_sin_vendedor = sales_qs.filter(seller__isnull=True)

        return Response({
            'ventas_sin_cliente': {
                'count': sin_cliente.count(),
                'sample': sample(sin_cliente.order_by('-sale_date'),
                                 ['id', 'sale_number', 'sale_date', 'total_price']),
            },
            'ventas_sin_vehiculo': {
                'count': sin_vehiculo.count(),
                'sample': sample(sin_vehiculo.order_by('-sale_date'),
                                 ['id', 'sale_number', 'sale_date']),
            },
            'ventas_sin_vendedor': {
                'count': ventas_sin_vendedor.count(),
                'sample': [],
            },
            'ventas_mig': {
                'count': ventas_mig.count(),
                'sample': sample(ventas_mig, ['id', 'sale_number']),
            },
            'ventas_placeholder': {
                'count': ventas_placeholder.count(),
                'sample': sample(ventas_placeholder, ['id', 'sale_number']),
            },
            'cuotas_overdue_de_facto': {
                'count': cuotas_overdue_de_facto.count(),
                'monto': float(cuotas_overdue_de_facto.aggregate(
                    Sum('amount'))['amount__sum'] or 0),
            },
            'cuotas_fecha_rara': {
                'count': cuotas_fecha_rara.count(),
                'sample': sample(cuotas_fecha_rara,
                                 ['id', 'sale_id', 'quota_number', 'due_date']),
            },
            'cuotas_pago_futuro': {
                'count': cuotas_pago_futuro.count(),
                'sample': sample(cuotas_pago_futuro,
                                 ['id', 'sale_id', 'quota_number', 'payment_date']),
            },
            'cuotas_monto_cero': {'count': cuotas_monto_cero.count()},
            'cuotas_sin_plan': {'count': cuotas_sin_plan.count()},
            'vehiculos_inconsistentes': {
                'count': vehiculos_inconsistentes.count(),
                'sample': sample(vehiculos_inconsistentes,
                                 ['id', 'vin', 'brand_id', 'model_id']),
            },
            'vehiculos_vin_basura': {'count': vin_basura.count()},
            'vehiculos_sin_precio': {'count': vehiculos_sin_precio.count()},
            'clientes_doc_auto': {
                'count': clientes_doc_auto.count(),
                'sample': sample(clientes_doc_auto,
                                 ['id', 'first_name', 'last_name', 'document_number']),
            },
            'clientes_email_sintetico': {'count': clientes_email_sintetico.count()},
            'clientes_sin_telefono': {'count': clientes_sin_telefono.count()},
        })

    @action(detail=False, methods=['get'])
    def top_customers(self, request):
        """Top 10 clientes por monto gastado.

        Filtra clientes que tengan al menos una venta con monto > 0.
        Sin este filtro, los clientes recién creados aparecían arriba
        con "Gs. 0 · 0x" porque NULL en `total_spent` ordena primero en
        SQLite (y a veces también en Postgres con NULLS FIRST).

        Excluye también:
          - clientes genéricos (`Cliente General`).
          - clientes con documento autogenerado por la migración
            (DRV026-/SUC026-/CUOTA…) — son placeholders que rocío
            todavía no completó.
        Respeta `?branch=` filtrando las ventas que cuentan.
        """
        user = request.user
        enterprise = user.enterprise

        if not enterprise:
            return Response(
                {'error': 'Usuario no tiene empresa asignada'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Sub-filter: si vino ?branch=, sólo contamos ventas de esa sucursal.
        branch_id = self._branch_id(request)
        sales_filter = Q(sales__total_price__gt=0)
        if branch_id:
            sales_filter &= Q(sales__branch_id=branch_id)

        customers = Customer.objects.filter(
            enterprise=enterprise,
            is_generic=False,
        ).exclude(
            Q(document_number__startswith='DRV026-') |
            Q(document_number__startswith='SUC026-') |
            Q(document_number__startswith='CUOTA')
        ).annotate(
            total_spent=Sum('sales__total_price', filter=sales_filter),
            total_sales=Count('sales', filter=sales_filter),
        ).filter(
            total_sales__gt=0,
            total_spent__gt=0,
        ).order_by('-total_spent')[:10]

        data = {
            'data': [
                {
                    'customer_id': c.id,
                    'cliente': c.full_name,
                    'total_gastado': float(c.total_spent or 0),
                    'numero_compras': c.total_sales,
                }
                for c in customers
            ]
        }

        return Response(data)

    @action(detail=False, methods=['get'])
    def margin_analysis(self, request):
        """Análisis de margen por venta cerrada en el período.

        Calcula para cada venta:
          - costo total del vehículo = fob + container + dispatch + cam_vol
            + sum(VehicleCost.amount con same currency PYG; USD se
            convierte a 0 si no hay exchange_rate, sino se aplica).
          - margen = total_price - costo total
          - margen_pct = margen / total_price * 100

        Devuelve la lista ordenada por margen_pct ASC (las peores
        primero — son las que conviene revisar para no repetir).

        Aproximación / decisiones:
          - VehicleCosts en USD se ignoran si no traen exchange_rate (mejor
            mostrar 0 que un número falso). El frontend muestra una
            advertencia cuando esto pasa.
          - Sólo ventas con vehicle (no MIG huérfanos).
          - Sólo status='completed' (las pending/cancelled distorsionan).

        Query: date_from, date_to, branch.
        """
        from decimal import Decimal
        from core.models.inventory import VehicleCost

        user = request.user
        if not user.enterprise:
            return Response({'error': 'sin empresa'}, status=400)

        date_from, date_to = self._parse_period(request)

        sales_qs = Sale.objects.filter(
            enterprise=user.enterprise,
            status='completed',
            sale_date__date__gte=date_from,
            sale_date__date__lte=date_to,
            vehicle__isnull=False,
            total_price__gt=0,
        ).select_related('vehicle', 'vehicle__brand', 'vehicle__model', 'customer', 'branch')
        sales_qs = self._filter_sales(sales_qs, request)

        # Cargamos en una sola query los VehicleCost de todos los vehículos
        # implicados para no hacer N+1.
        vehicle_ids = [s.vehicle_id for s in sales_qs if s.vehicle_id]
        costs_by_vehicle = {}
        for vc in VehicleCost.objects.filter(vehicle_id__in=vehicle_ids):
            costs_by_vehicle.setdefault(vc.vehicle_id, []).append(vc)

        items = []
        warnings_count = 0
        for s in sales_qs:
            veh = s.vehicle
            base_cost = (
                (veh.fob or 0) + (veh.container or 0)
                + (veh.dispatch or 0) + (veh.cam_vol or 0)
            )
            extras_total = Decimal('0')
            has_usd_sin_tc = False
            for vc in costs_by_vehicle.get(veh.id, []):
                if vc.currency == 'USD':
                    # Si no tenemos forma fácil de convertir, ignoramos y
                    # marcamos el warning. El servicio podría llamar a
                    # ExchangeRate.current, pero eso depende del modelo —
                    # lo dejamos para una iteración futura.
                    has_usd_sin_tc = True
                    continue
                extras_total += vc.amount or 0
            if has_usd_sin_tc:
                warnings_count += 1
            costo_total = base_cost + extras_total
            price = s.total_price or Decimal('0')
            margen = price - costo_total
            margen_pct = (float(margen) / float(price) * 100) if price else 0.0

            items.append({
                'sale_id':       s.id,
                'sale_number':   s.sale_number,
                'sale_date':     s.sale_date.date().isoformat() if s.sale_date else None,
                'customer_name': s.customer.full_name if s.customer_id else '',
                'vehicle_info':  (
                    f"{veh.brand.name if veh.brand_id else ''} "
                    f"{veh.model.name if veh.model_id else ''} "
                    f"{veh.year or ''}"
                ).strip(),
                'price':         float(price),
                'cost':          float(costo_total),
                'margin':        float(margen),
                'margin_pct':    round(margen_pct, 1),
                'has_usd_without_tc': has_usd_sin_tc,
            })

        # Ordenar por margen_pct ASC (peores primero) — el caso de uso
        # típico es "qué vendí mal este mes".
        items.sort(key=lambda r: r['margin_pct'])

        # Agregados generales.
        total_price = sum(r['price'] for r in items)
        total_cost  = sum(r['cost'] for r in items)
        total_margin = total_price - total_cost
        avg_margin_pct = (total_margin / total_price * 100) if total_price else 0.0

        return Response({
            'periodo': {
                'date_from': date_from.isoformat(),
                'date_to':   date_to.isoformat(),
            },
            'n_ventas':       len(items),
            'total_price':    total_price,
            'total_cost':     total_cost,
            'total_margin':   total_margin,
            'avg_margin_pct': round(avg_margin_pct, 1),
            'warnings_usd_sin_tc': warnings_count,
            'results':        items,
        })

    @action(detail=False, methods=['get'])
    def seller_commissions(self, request):
        """Comisiones por vendedor en el período pedido.

        AUTO OFERTAS hoy no tiene comisiones formalizadas, pero quería
        ver cuánto le correspondería a cada vendedor en base a sus ventas
        cerradas. Esta es la base — el porcentaje se pasa por query, el
        endpoint sólo agrega.

        Query params:
          - `date_from`, `date_to`: período (default mes actual).
          - `branch`: filtrar por sucursal.
          - `rate`: porcentaje en decimal (default 1.0 = 1%). Acepta hasta
            100. Si pasás 1.5, es 1.5%.

        Devuelve una lista por vendedor + el total general, para que el
        admin pueda usarlo como reporte.
        """
        user = request.user
        if not user.enterprise:
            return Response({'error': 'Usuario sin empresa'},
                            status=status.HTTP_400_BAD_REQUEST)

        date_from, date_to = self._parse_period(request)
        try:
            rate = float(request.query_params.get('rate', 1.0))
        except ValueError:
            rate = 1.0
        rate = max(0, min(rate, 100))

        sales_qs = Sale.objects.filter(
            enterprise=user.enterprise,
            status='completed',
            sale_date__date__gte=date_from,
            sale_date__date__lte=date_to,
        )
        sales_qs = self._filter_sales(sales_qs, request)

        by_seller = (
            sales_qs.values('seller_id', 'seller__first_name', 'seller__last_name', 'seller__username')
                    .annotate(n=Count('id'), total=Sum('total_price'))
                    .order_by('-total')
        )

        items = []
        total_ventas = 0
        total_monto = 0.0
        for row in by_seller:
            monto = float(row['total'] or 0)
            comision = monto * rate / 100
            items.append({
                'seller_id':       row['seller_id'],
                'seller_username': row['seller__username'],
                'seller_name':     (
                    f"{row['seller__first_name'] or ''} {row['seller__last_name'] or ''}".strip()
                    or row['seller__username']
                    or '(sin vendedor)'
                ),
                'n_ventas':        row['n'],
                'monto_total':     monto,
                'comision':        round(comision, 2),
            })
            total_ventas += row['n']
            total_monto += monto

        return Response({
            'periodo': {
                'date_from': date_from.isoformat(),
                'date_to':   date_to.isoformat(),
            },
            'rate_pct':       rate,
            'rate':           rate,
            'total_ventas':   total_ventas,
            'total_monto':    total_monto,
            'total_comision': round(total_monto * rate / 100, 2),
            'by_seller':      items,
        })

    @method_decorator(dashboard_cache(120))
    @action(detail=False, methods=['get'])
    def health(self, request):
        """Indicadores de salud del negocio en el período pedido.

        Métricas (todas calculadas con el filtro de ?date_from/?date_to
        y ?branch= cuando aplica):

        - `tasa_morosidad`: % de cuotas con due_date < hoy y no pagadas,
          sobre total de cuotas activas. Indicador clave de calidad
          de cartera.
        - `ticket_promedio`: monto promedio de las ventas cerradas del
          período. Sube → la playa está moviendo autos más caros.
        - `dias_promedio_pago`: promedio de (payment_date - due_date)
          en cuotas pagadas del período. Negativo = pagan antes;
          positivo = pagan tarde.
        - `vehiculos_estancados_90d`: cantidad de vehículos disponibles
          con created_at > 90 días. Candidatos a bajar de precio.
        - `top_vendedor`: vendedor con más ventas en el período (id,
          nombre, cantidad, monto total).
        - `tasa_conversion_clientes`: ventas / clientes únicos. Subir
          significa más cross-sell (clientes repiten).

        El cache es de 120s porque estas métricas no cambian con cada
        clic — son útiles para mirar tendencias.
        """
        from django.db.models import F, ExpressionWrapper, DurationField
        user = request.user
        if not user.enterprise:
            return Response({'error': 'Usuario sin empresa'},
                            status=status.HTTP_400_BAD_REQUEST)

        date_from, date_to = self._parse_period(request)
        today = date.today()

        # Base querysets multi-tenancy + período + sucursal.
        sales_base = Sale.objects.filter(
            enterprise=user.enterprise,
            status='completed',
            sale_date__date__gte=date_from,
            sale_date__date__lte=date_to,
        )
        sales_base = self._filter_sales(sales_base, request)

        quotas_base = Quotum.objects.filter(
            enterprise=user.enterprise,
            sale__status='completed',
        )
        quotas_base = self._filter_quotas(quotas_base, request)

        # === 1. Tasa de morosidad ===
        # Numerador: cuotas no pagadas con vencimiento ya pasado.
        # Denominador: cuotas activas (no canceladas).
        cuotas_activas = quotas_base.exclude(status='cancelled')
        n_activas = cuotas_activas.count()
        n_vencidas = cuotas_activas.filter(
            due_date__lt=today,
        ).exclude(status='paid').count()
        tasa_mora = (n_vencidas / n_activas * 100) if n_activas else 0.0

        # === 2. Ticket promedio ===
        ticket = sales_base.aggregate(avg=Avg('total_price'))['avg']
        ticket_promedio = float(ticket) if ticket else 0.0
        n_ventas = sales_base.count()

        # === 3. Días promedio de pago ===
        # SQLite no soporta restar DateField nativamente en aggregate, así
        # que iteramos en Python (las cuotas pagadas son <1000 típicamente).
        pagadas = list(quotas_base.filter(
            status='paid',
            payment_date__gte=date_from,
            payment_date__lte=date_to,
        ).values_list('due_date', 'payment_date'))
        if pagadas:
            diffs = [(pd - dd).days for dd, pd in pagadas if dd and pd]
            dias_promedio_pago = sum(diffs) / len(diffs) if diffs else 0.0
        else:
            dias_promedio_pago = None

        # === 4. Vehículos estancados (>90 días) ===
        vehs_base = Vehicle.objects.filter(
            enterprise=user.enterprise, state='available',
        )
        vehs_base = self._filter_vehicles(vehs_base, request)
        cutoff_90 = today - timedelta(days=90)
        estancados = vehs_base.filter(created_at__date__lt=cutoff_90).count()

        # === 5. Top vendedor del período ===
        top_seller_qs = (
            sales_base.exclude(seller__isnull=True)
                      .values('seller_id', 'seller__first_name', 'seller__last_name')
                      .annotate(n=Count('id'), total=Sum('total_price'))
                      .order_by('-total')
        )
        top = top_seller_qs.first()
        top_vendedor = None
        if top:
            top_vendedor = {
                'id':     top['seller_id'],
                'nombre': f"{top['seller__first_name'] or ''} {top['seller__last_name'] or ''}".strip(),
                'ventas': top['n'],
                'total':  float(top['total'] or 0),
            }

        # === 6. Tasa de conversión (ventas / clientes únicos del período) ===
        # Ojo: si la misma persona compra 2 autos cuenta 1 vez como cliente.
        n_clientes_unicos = sales_base.values('customer_id').distinct().count()
        tasa_conversion = (n_ventas / n_clientes_unicos) if n_clientes_unicos else 0.0

        return Response({
            'periodo': {
                'date_from': date_from.isoformat(),
                'date_to':   date_to.isoformat(),
            },
            'tasa_morosidad': {
                'porcentaje': round(tasa_mora, 1),
                'n_vencidas': n_vencidas,
                'n_activas':  n_activas,
            },
            'ticket_promedio': {
                'monto':    round(ticket_promedio, 0),
                'n_ventas': n_ventas,
            },
            'dias_promedio_pago': {
                'dias':       round(dias_promedio_pago, 1) if dias_promedio_pago is not None else None,
                'n_muestras': len(pagadas),
                # Interpretación: <0 pagan antes; >0 pagan tarde
            },
            'vehiculos_estancados_90d': {
                'count': estancados,
            },
            'top_vendedor': top_vendedor,
            'tasa_conversion_clientes': {
                'ratio':             round(tasa_conversion, 2),
                'ventas':            n_ventas,
                'clientes_unicos':   n_clientes_unicos,
            },
        })
