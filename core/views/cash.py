"""Endpoints de movimientos de caja (CashMovement)."""

import csv
import io
from calendar import monthrange
from datetime import datetime, date
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import HttpResponse
from django.db.models import Sum, Count, Q

from core.models import CashMovement
from core.serializers import CashMovementSerializer
from core.permissions import IsAuthenticated, IsEnterpriseOwnerOrAdmin


class CashMovementViewSet(viewsets.ModelViewSet):
    """CRUD de movimientos de caja, con filtros por fecha, sucursal, tipo y dirección.

    Acepta:
      - `date_from` / `date_to` (YYYY-MM-DD)
      - `branch` (id)
      - `kind` (uno de los choices)
      - `direction` (in | out)
      - `is_auto` (true | false) — para distinguir auto-generados de manuales
    """
    serializer_class = CashMovementSerializer
    permission_classes = [IsAuthenticated, IsEnterpriseOwnerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if not (user and user.enterprise):
            return CashMovement.objects.none()
        qs = CashMovement.objects.select_related(
            'branch', 'sale', 'quota', 'created_by',
        ).filter(enterprise=user.enterprise)

        params = self.request.query_params
        date_from = params.get('date_from')
        date_to = params.get('date_to')
        # Shortcut: ?period=YYYY-MM equivale a el mes completo. Útil para
        # el contador, que cierra caja mes por mes ("flujo de mayo 2026").
        # Si vienen date_from/date_to explícitos, esos ganan.
        period = params.get('period')
        if period and not (date_from or date_to):
            try:
                yyyy, mm = period.split('-')
                y, m = int(yyyy), int(mm)
                last_day = monthrange(y, m)[1]
                date_from = f'{y:04d}-{m:02d}-01'
                date_to = f'{y:04d}-{m:02d}-{last_day:02d}'
            except (ValueError, IndexError):
                pass  # ignoramos period malformado en silencio
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        branch_id = params.get('branch')
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        kind = params.get('kind')
        if kind:
            qs = qs.filter(kind=kind)
        direction = params.get('direction')
        if direction in ('in', 'out'):
            qs = qs.filter(direction=direction)
        is_auto = params.get('is_auto')
        if is_auto in ('true', 'false'):
            qs = qs.filter(is_auto=(is_auto == 'true'))

        return qs.order_by('-date', '-created_at')

    def perform_create(self, serializer):
        # Sólo los movimientos manuales pasan por acá; auto-generados se
        # crean en Sale.save() / Quotum.save(). Forzamos is_auto=False.
        serializer.save(
            enterprise=self.request.user.enterprise,
            is_auto=False,
            created_by=self.request.user,
        )

    def perform_update(self, serializer):
        # No permitimos cambiar `is_auto` ni desbloquear los auto-generados
        # vía PATCH del usuario — eso se maneja desde Sale/Quotum.
        validated = serializer.validated_data
        validated.pop('is_auto', None)
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.is_auto:
            return Response(
                {'detail': 'No se puede borrar un movimiento generado automáticamente. '
                           'Cambiá el estado de la venta o cuota de origen.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Totales por tipo y dirección en el período pedido."""
        qs = self.get_queryset()

        in_total = qs.filter(direction='in').aggregate(
            total=Sum('amount'), n=Count('id'),
        )
        out_total = qs.filter(direction='out').aggregate(
            total=Sum('amount'), n=Count('id'),
        )

        by_kind = (
            qs.values('kind', 'direction')
              .annotate(total=Sum('amount'), n=Count('id'))
              .order_by('direction', '-total')
        )

        # Choices de tipos para que la UI sepa qué etiquetas mostrar.
        kind_labels = dict(CashMovement.KIND_CHOICES)
        by_kind_data = [
            {
                'kind': r['kind'],
                'kind_display': str(kind_labels.get(r['kind'], r['kind'])),
                'direction': r['direction'],
                'n': r['n'],
                'total': float(r['total'] or 0),
            }
            for r in by_kind
        ]

        return Response({
            'ingresos': {
                'total': float(in_total['total'] or 0),
                'n': in_total['n'] or 0,
            },
            'egresos': {
                'total': float(out_total['total'] or 0),
                'n': out_total['n'] or 0,
            },
            'neto': float((in_total['total'] or 0) - (out_total['total'] or 0)),
            'by_kind': by_kind_data,
        })

    @action(detail=False, methods=['get'], url_path='export')
    def export_csv(self, request):
        """Exporta los movimientos filtrados como CSV.

        Acepta los mismos query params que el listado (date_from, date_to,
        branch, kind, direction, is_auto) y además:
          - `period=YYYY-MM` (shortcut para el mes completo)
          - `delimiter=comma|semicolon` (por default semicolon — Excel ES
            usa `,` como separador decimal, así que `;` evita conflictos
            cuando un monto se rompe en dos columnas).

        El archivo arranca con BOM UTF-8 (﻿) para que Excel español
        muestre los acentos sin pedir importación manual.

        Al final agrega tres filas con totales (Ingresos, Egresos, Neto)
        para que no haya que sumar a mano.
        """
        qs = self.get_queryset()
        # Iteramos en orden cronológico ascendente para el CSV (más natural
        # para revisar un mes que el orden por defecto -date).
        rows = list(qs.order_by('date', 'created_at'))

        delimiter_param = request.query_params.get('delimiter', 'semicolon')
        delim = ',' if delimiter_param == 'comma' else ';'

        # Buffer en memoria. Para los volúmenes esperados (cientos/miles
        # de filas por mes, máximo) no necesitamos StreamingHttpResponse.
        buf = io.StringIO()
        buf.write('﻿')  # BOM UTF-8 para Excel
        writer = csv.writer(buf, delimiter=delim, lineterminator='\r\n')

        writer.writerow([
            'Fecha', 'Sucursal', 'Tipo', 'Dirección', 'Operación',
            'Monto', 'Moneda', 'Monto USD', 'TC',
            'Proveedor', 'Venta', 'Cuota', 'Notas',
            'Creado por', 'Auto',
        ])

        kind_labels = dict(CashMovement.KIND_CHOICES)
        dir_labels = dict(CashMovement.DIRECTION_CHOICES)
        total_in = 0
        total_out = 0
        for m in rows:
            writer.writerow([
                m.date.isoformat() if m.date else '',
                m.branch.name if m.branch_id else '',
                str(kind_labels.get(m.kind, m.kind)),
                str(dir_labels.get(m.direction, m.direction)),
                m.description or '',
                f'{m.amount:.2f}' if m.amount is not None else '',
                m.currency or '',
                f'{m.amount_usd:.2f}' if m.amount_usd is not None else '',
                f'{m.exchange_rate:.2f}' if m.exchange_rate is not None else '',
                m.provider or '',
                getattr(m.sale, 'sale_number', '') if m.sale_id else '',
                m.quota_id or '',
                (m.notes or '').replace('\n', ' / ').replace('\r', ' '),
                m.created_by.get_full_name() if m.created_by_id else '',
                'Sí' if m.is_auto else 'No',
            ])
            if m.direction == 'in':
                total_in += float(m.amount or 0)
            else:
                total_out += float(m.amount or 0)

        # Línea en blanco + totales (15 columnas para alinear con la cabecera).
        writer.writerow([])
        writer.writerow(['', '', '', '', 'TOTAL INGRESOS', f'{total_in:.2f}',
                         '', '', '', '', '', '', '', '', ''])
        writer.writerow(['', '', '', '', 'TOTAL EGRESOS', f'{total_out:.2f}',
                         '', '', '', '', '', '', '', '', ''])
        writer.writerow(['', '', '', '', 'NETO', f'{(total_in - total_out):.2f}',
                         '', '', '', '', '', '', '', '', ''])

        # Nombre de archivo que tenga sentido al guardarse.
        params = request.query_params
        period = params.get('period')
        date_from = params.get('date_from')
        date_to = params.get('date_to')
        if period:
            tag = period
        elif date_from and date_to:
            tag = f'{date_from}_a_{date_to}'
        elif date_from:
            tag = f'desde_{date_from}'
        elif date_to:
            tag = f'hasta_{date_to}'
        else:
            tag = datetime.now().strftime('%Y-%m-%d')
        filename = f'flujo_caja_{tag}.csv'

        response = HttpResponse(
            buf.getvalue().encode('utf-8'),
            content_type='text/csv; charset=utf-8',
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @action(detail=False, methods=['get'])
    def kinds(self, request):
        """Devuelve la lista de tipos disponibles para los selectores de la UI."""
        return Response({
            'kinds': [
                {'value': k, 'label': str(v)}
                for k, v in CashMovement.KIND_CHOICES
            ],
            'directions': [
                {'value': k, 'label': str(v)}
                for k, v in CashMovement.DIRECTION_CHOICES
            ],
        })

    @action(detail=False, methods=['post'], parser_classes=None)
    def import_ods(self, request):
        """Importa un archivo ODS de flujo de caja. Sólo admin.

        El archivo se envía como multipart `file=`. Acepta también
        `branch=<id>` opcional y `dry_run=true`.
        """
        if request.user.role != 'admin' and not request.user.is_superuser:
            return Response({'detail': 'Sólo administradores'},
                            status=status.HTTP_403_FORBIDDEN)

        upload = request.FILES.get('file')
        if not upload:
            return Response({'detail': 'Falta el archivo (campo "file" multipart)'},
                            status=status.HTTP_400_BAD_REQUEST)

        # Guardar a un tmp para que odfpy pueda leerlo por path.
        import os, tempfile
        from core.services.cash_import import import_ods_to_cash_movements
        from core.models import Branch as _Branch

        with tempfile.NamedTemporaryFile(suffix='.ods', delete=False) as f:
            for chunk in upload.chunks():
                f.write(chunk)
            tmp_path = f.name

        try:
            branch = None
            branch_id = request.data.get('branch')
            if branch_id:
                branch = _Branch.objects.filter(
                    id=branch_id, enterprise=request.user.enterprise,
                ).first()
            dry = str(request.data.get('dry_run', '')).lower() in ('true', '1', 'yes')

            result = import_ods_to_cash_movements(
                tmp_path,
                enterprise=request.user.enterprise,
                branch=branch,
                created_by=request.user,
                dry_run=dry,
            )
            return Response(result)
        finally:
            try: os.unlink(tmp_path)
            except OSError: pass
