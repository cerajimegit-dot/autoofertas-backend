"""Endpoints de movimientos de caja (CashMovement)."""

from datetime import datetime, date
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
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
