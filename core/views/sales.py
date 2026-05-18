import re
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Count, Sum, F, Value
from django.db.models.functions import Concat, Lower
from django.db import connection
from datetime import datetime, timedelta

from core.models import Customer, PaymentForm, Sale, Quotum
from core.throttling import WhatsAppRateThrottle
from core.serializers import (
    CustomerSerializer, PaymentFormSerializer,
    SaleListSerializer, SaleDetailSerializer,
    QuotumListSerializer, QuotumDetailSerializer
)
from core.permissions import IsAuthenticated, IsEnterpriseOwnerOrAdmin, CanDeleteSale


class CustomerViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de clientes"""
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated, IsEnterpriseOwnerOrAdmin]

    def get_queryset(self):
        if self.request.user and self.request.user.enterprise:
            # select_related('enterprise') evita un SELECT extra por cliente
            # al acceder a `enterprise.name` en el serializer (N+1 #2 — el
            # primero era `sales_count`).
            # Anotamos `sales_count` una sola vez en SQL. El serializer lo
            # lee de la anotación.
            return Customer.objects.select_related('enterprise').filter(
                enterprise=self.request.user.enterprise
            ).annotate(
                sales_count=Count('sales')
            ).order_by('-created_at')
        return Customer.objects.none()

    def perform_create(self, serializer):
        serializer.save(enterprise=self.request.user.enterprise)

    # Cache de feature-flag: ¿está disponible pg_trgm en la BD? Lo
    # determinamos una sola vez (al primer request) para no hacer un
    # SELECT extra en cada búsqueda. Es seguro cachear a nivel de clase
    # porque, durante la vida del proceso, la disponibilidad de la
    # extensión no va a cambiar.
    _pg_trgm_available = None

    @classmethod
    def _has_pg_trgm(cls):
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
        """Busca clientes por nombre, apellido, documento, email o teléfono.

        Usa `pg_trgm` cuando está disponible (Postgres con la extensión
        habilitada) — eso tolera typos: "Cristian" matchea "Kristian",
        "Garcia" matchea "García", etc. La similaridad se ordena de mayor
        a menor.

        Si la extensión no está (SQLite local, o Supabase sin habilitar
        la extensión todavía), cae a un fallback que parte la query en
        tokens y exige que CADA token aparezca en algún campo (ILIKE
        substring). Eso da matches razonables aunque no tolera typos.

        Acepta:
          - `q=...`: la cadena de búsqueda (requerido, ≥ 2 caracteres)
          - `limit=...`: máximo de resultados (default 10, máximo 50)
        """
        q = (request.query_params.get('q') or '').strip()
        if len(q) < 2:
            return Response({'results': [], 'used': 'none'})

        try:
            limit = min(int(request.query_params.get('limit', 10)), 50)
        except ValueError:
            limit = 10

        qs = self.get_queryset()

        if self._has_pg_trgm():
            results = self._search_pg_trgm(qs, q, limit)
            backend_used = 'pg_trgm'
        else:
            results = self._search_fallback(qs, q, limit)
            backend_used = 'ilike'

        return Response({
            'results': CustomerSerializer(results, many=True).data,
            'used': backend_used,
        })

    @staticmethod
    def _search_pg_trgm(qs, q, limit):
        """Búsqueda con scoring de similaridad. Sólo Postgres + pg_trgm."""
        # Concatenamos nombre completo lowercased — el índice GIN que
        # creamos en la migración 0010 está sobre la misma expresión, así
        # que esto debería usarlo (chequeable con EXPLAIN).
        # `extra` es la única forma cómoda de usar `similarity()` en Django
        # sin escribir una función personalizada — DRF ORM no la expone.
        q_lower = q.lower()
        return list(
            qs.extra(
                select={
                    'sim_name': (
                        "similarity("
                        "  LOWER(COALESCE(first_name, '') || ' ' || COALESCE(last_name, '')),"
                        "  %s"
                        ")"
                    ),
                    'sim_doc': "similarity(document_number, %s)",
                },
                select_params=[q_lower, q],
                where=[
                    # Umbral 0.2 = razonablemente permisivo. Subir si vienen
                    # demasiados falsos positivos en producción.
                    "(LOWER(COALESCE(first_name, '') || ' ' || COALESCE(last_name, '')) %% %s"
                    " OR document_number %% %s"
                    " OR LOWER(COALESCE(email, '')) LIKE %s"
                    " OR phone LIKE %s)"
                ],
                params=[q_lower, q, f'%{q_lower}%', f'%{q}%'],
                order_by=['-sim_name', '-sim_doc'],
            )[:limit]
        )

    @staticmethod
    def _search_fallback(qs, q, limit):
        """Fallback sin pg_trgm: partir en tokens y exigir match de TODOS.

        Funciona en SQLite (tests) y en Postgres sin la extensión.
        Cubre el caso típico: el usuario tipea "carlos perez 12345" y se
        espera matchear contra alguien que tenga "Carlos" Y "Pérez" Y
        "12345" en alguno de los campos.
        """
        tokens = [t for t in q.split() if t]
        if not tokens:
            return []
        for tok in tokens:
            qs = qs.filter(
                Q(first_name__icontains=tok)
                | Q(last_name__icontains=tok)
                | Q(document_number__icontains=tok)
                | Q(email__icontains=tok)
                | Q(phone__icontains=tok)
            )
        # Ordenamos por -id como proxy de "más recientes primero" — sin
        # similaridad, no hay un score razonable.
        return list(qs.order_by('-id')[:limit])

    @action(detail=True, methods=['get'])
    def full(self, request, pk=None):
        """Devuelve cliente + ventas + cuotas + resumen financiero en 1 sola
        respuesta. Reemplaza los 3 round-trips que hacía /customers/:id antes.

        Optimizaciones:
          - 2 queries SQL al backend (sales + quotas) en vez de 3 endpoints +
            4 aggregate adicionales. Cada query a Supabase São Paulo cuesta
            100-200 ms de RTT — minimizamos el número total.
          - El resumen financiero se calcula en Python desde los datos ya
            traídos (con N≤24 cuotas típicamente, sumar en Python es <1 ms).
          - Las cuotas se traen con `select_related('sale')` — sólo lo
            necesario para mostrar sale_number, no vehicle__brand__model
            que sobrecargaba la query.
        """
        from datetime import date

        customer = self.get_object()
        today = date.today()

        # === Ventas del cliente (1 query) ===
        # Incluimos 'customer' en select_related aunque ya sabemos que es
        # `customer` — el serializer `SaleListSerializer.get_customer_name`
        # accede a obj.customer.full_name, que sin select_related dispararía
        # 1 query SELECT extra por venta (N+1).
        sales_list = list(
            Sale.objects.select_related(
                'customer',
                'branch', 'vehicle', 'vehicle__brand', 'vehicle__model',
                'payment_form', 'seller',
            ).filter(customer=customer).order_by('-sale_date')
        )
        from core.serializers import SaleListSerializer
        sales_data = SaleListSerializer(sales_list, many=True).data

        # === Cuotas del cliente (1 query) ===
        # Idem: QuotumListSerializer lee customer.id y customer.full_name. Sin
        # select_related('customer') hace 1 query por cuota (N+1, hasta 50
        # queries para un cliente moroso con muchas cuotas).
        quotas_list = list(
            Quotum.objects.select_related('customer', 'sale').filter(
                customer=customer
            ).order_by('sale__sale_date', 'quota_number')
        )
        quotas_data = QuotumListSerializer(quotas_list, many=True).data

        # === Resumen financiero, calculado en Python ===
        # Con typically <30 cuotas y <5 ventas por cliente, recorrer en Python
        # es del orden de microsegundos. Antes hacíamos 4 aggregate extra a
        # Supabase (~800 ms total de RTT).
        tot_comprado = sum(float(s.total_price or 0) for s in sales_list)
        tot_cobrado = sum(float(q.amount or 0) for q in quotas_list if q.status == 'paid')
        n_pagadas   = sum(1 for q in quotas_list if q.status == 'paid')

        pending_quotas = [q for q in quotas_list if q.status not in ('paid', 'cancelled')]
        overdue_quotas = [q for q in pending_quotas
                          if q.status == 'overdue'
                          or (q.due_date and q.due_date < today)]
        tot_pendiente = sum(float(q.amount or 0) for q in pending_quotas)
        tot_vencido = sum(float(q.amount or 0) for q in overdue_quotas)

        summary = {
            'tot_comprado':  tot_comprado,
            'n_ventas':      len(sales_list),
            'tot_cobrado':   tot_cobrado,
            'n_pagadas':     n_pagadas,
            'tot_pendiente': tot_pendiente,
            'n_pendientes':  len(pending_quotas) - len(overdue_quotas),
            'tot_vencido':   tot_vencido,
            'n_vencidas':    len(overdue_quotas),
        }

        return Response({
            'customer': CustomerSerializer(customer).data,
            'sales':    sales_data,
            'quotas':   quotas_data,
            'summary':  summary,
        })


class PaymentFormViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de formas de pago"""
    serializer_class = PaymentFormSerializer
    permission_classes = [IsAuthenticated, IsEnterpriseOwnerOrAdmin]
    
    def get_queryset(self):
        if self.request.user and self.request.user.enterprise:
            return PaymentForm.objects.filter(
                enterprise=self.request.user.enterprise,
                is_active=True
            )
        return PaymentForm.objects.none()
    
    def perform_create(self, serializer):
        serializer.save(enterprise=self.request.user.enterprise)


class SaleViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de ventas"""
    permission_classes = [IsAuthenticated, IsEnterpriseOwnerOrAdmin, CanDeleteSale]
    
    def get_queryset(self):
        # prefetch_related('quotas') es clave para que `Sale.collection_status`
        # del serializer no dispare 3 queries por venta (N+1: con 400 ventas
        # serían 1200 queries extras a Supabase).
        queryset = Sale.objects.select_related(
            'customer', 'vehicle', 'vehicle__brand', 'vehicle__model',
            'branch', 'payment_form', 'seller',
        ).prefetch_related('quotas').all()

        if self.request.user and self.request.user.enterprise:
            queryset = queryset.filter(enterprise=self.request.user.enterprise)

        # Filtros adicionales
        branch_id = self.request.query_params.get('branch')
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)

        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filtro por cliente — usado por la vista /customers/:id.
        customer_id = self.request.query_params.get('customer')
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)

        date_from = self.request.query_params.get('date_from')
        if date_from:
            queryset = queryset.filter(sale_date__gte=date_from)

        date_to = self.request.query_params.get('date_to')
        if date_to:
            queryset = queryset.filter(sale_date__lte=date_to)

        return queryset.order_by('-sale_date')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return SaleListSerializer
        return SaleDetailSerializer
    
    def perform_create(self, serializer):
        from core.models import Branch
        user = self.request.user
        enterprise = user.enterprise

        # Permitir sale_number explícito desde el payload; si no, dejar un
        # placeholder visible (??/YY) en vez de "V20260512NNNNN" que no encaja
        # con el formato CM/MC esperado por el usuario.
        sale_number = serializer.validated_data.get('sale_number')
        if not sale_number:
            yy = datetime.now().strftime('%y')
            sale_number = f"??/{yy}"
            # Garantizar unicidad para no romper la creación: si ya existe,
            # incrementamos hasta encontrar uno libre.
            i = 1
            while Sale.objects.filter(sale_number=sale_number).exists():
                sale_number = f"??/{yy}-{i}"
                i += 1

        # Resolver sucursal en este orden:
        #  1. branch explícito en el payload (lo manda el frontend desde el selector).
        #  2. branch del query param ?branch= (por consistencia con get_queryset).
        #  3. branches_managed del usuario (manager/admin).
        #  4. primera sucursal de la empresa como fallback.
        payload_branch = serializer.validated_data.get('branch')
        query_branch_id = self.request.query_params.get('branch')
        if payload_branch:
            branch = payload_branch
        elif query_branch_id:
            branch = Branch.objects.filter(
                id=query_branch_id, enterprise=enterprise
            ).first() or Branch.objects.filter(enterprise=enterprise).first()
        else:
            branch = user.branches_managed.first() or Branch.objects.filter(
                enterprise=enterprise
            ).first()

        serializer.save(
            enterprise=enterprise,
            branch=branch,
            sale_number=sale_number,
            seller=user,
        )
    
    @action(detail=False, methods=['get'])
    def monthly_sales(self, request):
        """Obtener ventas del mes actual"""
        today = datetime.now().date()
        month_start = today.replace(day=1)
        
        sales = self.get_queryset().filter(
            sale_date__gte=month_start,
            sale_date__lte=today
        )
        
        serializer = SaleListSerializer(sales, many=True)
        return Response({
            'count': sales.count(),
            'total': sales.aggregate(Sum('total_price'))['total_price__sum'],
            'sales': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def sales_report(self, request):
        """Generar reporte de ventas por período"""
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        queryset = self.get_queryset()
        
        if date_from and date_to:
            queryset = queryset.filter(
                sale_date__gte=date_from,
                sale_date__lte=date_to
            )
        
        report = {
            'total_sales': queryset.count(),
            'total_amount': queryset.aggregate(Sum('total_price'))['total_price__sum'],
            'by_status': queryset.values('status').annotate(
                count=Count('id'),
                total=Sum('total_price')
            ),
            'by_branch': queryset.values('branch__name').annotate(
                count=Count('id'),
                total=Sum('total_price')
            ),
            'by_payment_form': queryset.values('payment_form__name').annotate(
                count=Count('id'),
                total=Sum('total_price')
            ),
        }
        
        return Response(report)


class QuotumViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de cuotas"""
    permission_classes = [IsAuthenticated, IsEnterpriseOwnerOrAdmin]
    
    def get_queryset(self):
        from datetime import date

        queryset = Quotum.objects.select_related(
            'customer', 'sale', 'sale__branch', 'sale__vehicle',
            'sale__vehicle__brand', 'sale__vehicle__model'
        ).all()

        if self.request.user and self.request.user.enterprise:
            queryset = queryset.filter(enterprise=self.request.user.enterprise)

        # Filtros adicionales
        customer_id = self.request.query_params.get('customer')
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)

        # Filtro por status. El status "overdue" se calcula en línea:
        #   - 'overdue'   → status legacy 'overdue' OR (status pending Y vencida)
        #   - 'pending'   → pending (incluye las que están "vencidas de facto"
        #                  — para listarlas separadas, usá ?status=overdue)
        # Para distinguir, agregamos un alias: ?status=pending_only filtra solo
        # las pending NO vencidas (las "al día").
        today = date.today()
        status_filter = self.request.query_params.get('status')
        if status_filter == 'overdue':
            queryset = queryset.filter(
                Q(status='overdue') |
                Q(status='pending', due_date__lt=today)
            )
        elif status_filter == 'pending_only':
            queryset = queryset.filter(status='pending', due_date__gte=today)
        elif status_filter:
            queryset = queryset.filter(status=status_filter)

        sale_id = self.request.query_params.get('sale')
        if sale_id:
            queryset = queryset.filter(sale_id=sale_id)

        branch_id = self.request.query_params.get('branch') or self.request.query_params.get('sale__branch')
        if branch_id:
            queryset = queryset.filter(sale__branch_id=branch_id)

        return queryset.order_by('due_date')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return QuotumListSerializer
        return QuotumDetailSerializer
    
    def perform_create(self, serializer):
        serializer.save(enterprise=self.request.user.enterprise)
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Obtener cuotas pendientes (acepta filtro ?branch=)"""
        queryset = self.get_queryset().filter(status='pending')
        serializer = QuotumListSerializer(queryset, many=True)
        # Devolvemos formato paginado-compatible para que el frontend
        # pueda hacer `r.data.results || r.data` indistintamente.
        return Response({'results': serializer.data, 'count': len(serializer.data)})
    
    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """Obtener cuotas vencidas (cálculo dinámico).

        Incluye:
          - cuotas con status='overdue' literal (62 cuotas legacy en BD), y
          - cuotas pending cuya fecha de vencimiento ya pasó (~970 hoy).

        Sin esta unión, el filtro "Vencidas" del frontend mostraba 62 cuando
        en realidad hay ~1000.
        """
        from datetime import date
        today = date.today()

        queryset = self.get_queryset().filter(
            Q(status='overdue') |
            Q(status='pending', due_date__lt=today)
        )
        # Devolvemos paginated-compatible para que el cliente use .results.
        serializer = QuotumListSerializer(queryset, many=True)
        return Response({'results': serializer.data, 'count': len(serializer.data)})
    
    @action(detail=False, methods=['get'])
    def next_30_days(self, request):
        """Obtener cuotas que vencen en los próximos 30 días"""
        from datetime import date
        today = date.today()
        in_30_days = today + timedelta(days=30)
        
        queryset = self.get_queryset().filter(
            status='pending',
            due_date__gte=today,
            due_date__lte=in_30_days
        )
        serializer = QuotumListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def quota_report(self, request):
        """Generar reporte de cuotas"""
        queryset = self.get_queryset()
        
        report = {
            'total_quotas': queryset.count(),
            'pending_amount': queryset.filter(
                status='pending'
            ).aggregate(Sum('amount'))['amount__sum'] or 0,
            'paid_amount': queryset.filter(
                status='paid'
            ).aggregate(Sum('amount'))['amount__sum'] or 0,
            'overdue_amount': queryset.filter(
                status='pending',
                due_date__lt=datetime.now().date()
            ).aggregate(Sum('amount'))['amount__sum'] or 0,
            'by_status': queryset.values('status').annotate(
                count=Count('id'),
                total=Sum('amount')
            ),
        }
        
        return Response(report)
    
    @action(detail=True, methods=['post'])
    def mark_as_paid(self, request, pk=None):
        """Marcar cuota como cobrada.

        Acepta opcionalmente:
          - payment_date (YYYY-MM-DD) — para registrar cobros recibidos en
            otra fecha (transferencia anterior, cheque, etc).
          - payment_method — uno de EF/TB/CJ/AC. Forma de cobro.
          - notes — texto libre que se concatena a las notas existentes.
        Si no se pasa payment_date, usa hoy.
        """
        quota = self.get_object()

        payment_date_str = request.data.get('payment_date')
        if payment_date_str:
            try:
                quota.payment_date = datetime.strptime(
                    payment_date_str, '%Y-%m-%d'
                ).date()
            except ValueError:
                return Response(
                    {'payment_date': 'Formato inválido, usar YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            quota.payment_date = datetime.now().date()

        payment_method = request.data.get('payment_method')
        if payment_method:
            valid = dict(Quotum.PAYMENT_METHOD_CHOICES).keys()
            if payment_method not in valid:
                return Response(
                    {'payment_method': f'Valor inválido. Debe ser uno de: {", ".join(valid)}'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            quota.payment_method = payment_method

        new_notes = request.data.get('notes')
        if new_notes:
            quota.notes = (quota.notes + '\n' if quota.notes else '') + new_notes

        quota.status = 'paid'
        quota.save()

        serializer = self.get_serializer(quota)
        return Response(serializer.data)

    @action(
        detail=True, methods=['get', 'post'],
        throttle_classes=[WhatsAppRateThrottle],
    )
    def contact_whatsapp(self, request, pk=None):
        """Genera un link de WhatsApp con mensaje pre-armado en español PY.

        El teléfono se normaliza:
          - se sacan espacios, guiones, paréntesis, signos.
          - si arranca con 0 (formato local PY) se reemplaza por 595.
          - si no arranca con 595 y tampoco tiene + se prefija 595.
        Para que `wa.me/...` funcione siempre.
        """
        quota = self.get_object()
        customer = quota.customer

        if not customer or not customer.phone:
            return Response(
                {'error': 'Cliente sin teléfono registrado'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        digits = re.sub(r'\D', '', customer.phone)
        if digits.startswith('0'):
            digits = '595' + digits[1:]
        elif not digits.startswith('595'):
            digits = '595' + digits

        nombre = (customer.first_name or '').split(' ')[0].title() or 'cliente'
        vto = quota.due_date.strftime('%d/%m/%Y') if quota.due_date else ''
        monto_int = int(quota.amount or 0)
        # Formato es-PY: separador de miles con punto, sin decimales.
        monto_str = f"{monto_int:,}".replace(',', '.')

        message = (
            f"Buen día {nombre}, le recordamos la cuota N°{quota.quota_number} "
            f"con vencimiento {vto} por Gs. {monto_str}. "
            f"Cualquier consulta estamos a las órdenes. AUTO OFERTAS."
        )

        from urllib.parse import quote_plus
        whatsapp_link = f"https://wa.me/{digits}?text={quote_plus(message)}"

        return Response({
            'whatsapp_link': whatsapp_link,
            'whatsapp_url': whatsapp_link,  # alias por compatibilidad con frontend viejo
            'phone_normalized': digits,
            'message': message,
        })
