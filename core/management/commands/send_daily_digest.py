"""Comando: envía un digest diario al admin con métricas clave.

USO:
    python manage.py send_daily_digest                # imprime y envía a DAILY_DIGEST_RECIPIENTS
    python manage.py send_daily_digest --dry-run      # sólo imprime
    python manage.py send_daily_digest --to a@b.com   # destinatario explícito
    python manage.py send_daily_digest --enterprise 3 # sólo esa empresa

POR EMPRESA, calcula:
  - Cuotas que vencen HOY.
  - Cuotas vencidas (atrasadas, no pagadas).
  - Ventas del día.
  - Tasa de morosidad acumulada.
  - Vehículos estancados > 90d.
  - Saldo de caja del día (ingresos - egresos del cash flow).

EJECUCIÓN PROGRAMADA: agendar con cron (Render Cron Jobs, Linux cron,
GitHub Actions schedule). Sugerido: diario 08:00 hora Asunción.

   crontab equivalente:
   0 11 * * * /path/to/python manage.py send_daily_digest

Render Cron Job:
   command: python manage.py send_daily_digest
   schedule: 0 11 * * *   (UTC; 08:00 hora Asunción)
"""

from datetime import date, timedelta
from io import StringIO

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.db.models import Sum, Count, Q

from core.models import Enterprise, Sale, Quotum, Vehicle, CashMovement


class Command(BaseCommand):
    help = 'Envía digest diario por empresa con métricas clave.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Sólo imprime, no envía email.')
        parser.add_argument('--to', type=str, default=None,
                            help='Email destinatario explícito (override de settings).')
        parser.add_argument('--enterprise', type=int, default=None,
                            help='ID de empresa específica. Por default itera todas.')

    def handle(self, *args, **opts):
        today = date.today()
        enterprises = Enterprise.objects.all()
        if opts['enterprise']:
            enterprises = enterprises.filter(id=opts['enterprise'])

        any_sent = False
        for e in enterprises:
            digest = self._build_digest(e, today)
            txt = self._format_text(e, today, digest)
            self.stdout.write(txt)

            if opts['dry_run']:
                continue

            recipients = (
                [opts['to']] if opts['to']
                else (settings.DAILY_DIGEST_RECIPIENTS or [])
            )
            recipients = [r for r in recipients if r]
            if not recipients:
                self.stdout.write(self.style.WARNING(
                    f'[{e.name}] No hay destinatarios configurados '
                    '(DAILY_DIGEST_RECIPIENTS en .env). Saltando email.'))
                continue

            try:
                send_mail(
                    subject=f'[{e.name}] Digest diario — {today.isoformat()}',
                    message=txt,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=recipients,
                    fail_silently=False,
                )
                any_sent = True
                self.stdout.write(self.style.SUCCESS(
                    f'  → enviado a {", ".join(recipients)}'))
            except Exception as err:
                self.stdout.write(self.style.ERROR(
                    f'  → ERROR enviando email: {err}'))

        if opts['dry_run']:
            self.stdout.write(self.style.NOTICE('(--dry-run: no se envió ningún email)'))
        elif not any_sent:
            self.stdout.write(self.style.WARNING(
                'Ningún digest se envió. Verificá DAILY_DIGEST_RECIPIENTS y EMAIL_HOST.'))

    def _build_digest(self, enterprise, today):
        """Calcula las métricas del día para una empresa."""
        # Cuotas que vencen hoy (pending, no pagadas).
        quotas_hoy = Quotum.objects.filter(
            enterprise=enterprise, due_date=today,
        ).exclude(status__in=['paid', 'cancelled'])

        # Cuotas vencidas (due_date < hoy y no pagadas/canceladas).
        quotas_vencidas = Quotum.objects.filter(
            enterprise=enterprise, due_date__lt=today,
        ).exclude(status__in=['paid', 'cancelled'])

        # Ventas del día (sale_date=hoy, status completed).
        ventas_hoy = Sale.objects.filter(
            enterprise=enterprise,
            sale_date__date=today,
            status='completed',
        )

        # Cuotas cobradas hoy
        cobradas_hoy = Quotum.objects.filter(
            enterprise=enterprise,
            payment_date=today,
            status='paid',
        )

        # Morosidad acumulada: activas vs vencidas.
        cuotas_activas = Quotum.objects.filter(
            enterprise=enterprise,
        ).exclude(status='cancelled')
        n_activas = cuotas_activas.count()
        n_mora = cuotas_activas.filter(
            due_date__lt=today,
        ).exclude(status='paid').count()
        mora_pct = (n_mora / n_activas * 100) if n_activas else 0

        # Vehículos estancados.
        cutoff = today - timedelta(days=90)
        estancados = Vehicle.objects.filter(
            enterprise=enterprise, state='available',
            created_at__date__lt=cutoff,
        ).count()

        # Flujo de caja del día.
        cash_hoy = CashMovement.objects.filter(
            enterprise=enterprise, date=today,
        )
        cash_in = cash_hoy.filter(direction='in').aggregate(s=Sum('amount'))['s'] or 0
        cash_out = cash_hoy.filter(direction='out').aggregate(s=Sum('amount'))['s'] or 0

        return {
            'quotas_hoy': list(quotas_hoy.select_related('customer', 'sale')),
            'quotas_vencidas_count': quotas_vencidas.count(),
            'quotas_vencidas_amount': quotas_vencidas.aggregate(s=Sum('amount'))['s'] or 0,
            'ventas_hoy_count': ventas_hoy.count(),
            'ventas_hoy_amount': ventas_hoy.aggregate(s=Sum('total_price'))['s'] or 0,
            'cobradas_hoy_count': cobradas_hoy.count(),
            'cobradas_hoy_amount': cobradas_hoy.aggregate(s=Sum('amount'))['s'] or 0,
            'mora_pct': round(mora_pct, 1),
            'mora_n': n_mora,
            'mora_total': n_activas,
            'estancados': estancados,
            'cash_in': cash_in,
            'cash_out': cash_out,
            'cash_neto': cash_in - cash_out,
        }

    def _format_text(self, enterprise, today, d):
        """Texto plano del digest. Renderizable como cuerpo de email."""
        out = StringIO()
        w = lambda s='': out.write(s + '\n')
        nf = lambda n: f'Gs. {int(n):,}'.replace(',', '.')

        w(f'═══════════════════════════════════════════════════════')
        w(f' DIGEST DIARIO — {enterprise.name}')
        w(f' Fecha: {today.strftime("%A %d/%m/%Y")}')
        w(f'═══════════════════════════════════════════════════════')
        w()

        # Ventas del día
        w('▌ VENTAS DEL DÍA')
        if d['ventas_hoy_count'] > 0:
            w(f'  · {d["ventas_hoy_count"]} venta(s) · {nf(d["ventas_hoy_amount"])}')
        else:
            w('  · Sin ventas hoy.')
        w()

        # Cobranzas
        w('▌ COBRANZAS')
        if d['cobradas_hoy_count'] > 0:
            w(f'  · Hoy se cobraron {d["cobradas_hoy_count"]} cuota(s) · {nf(d["cobradas_hoy_amount"])}')
        else:
            w('  · Sin cuotas cobradas hoy.')
        w()

        # Vencen hoy
        w('▌ VENCEN HOY')
        if d['quotas_hoy']:
            for q in d['quotas_hoy']:
                cust = q.customer.full_name if q.customer_id else '(sin cliente)'
                sale_num = q.sale.sale_number if q.sale_id else ''
                w(f'  · {sale_num} cuota {q.quota_number} — {cust} — {nf(q.amount)}')
        else:
            w('  · Nada vence hoy. ✓')
        w()

        # Vencidas
        w('▌ CARTERA VENCIDA (ACUMULADA)')
        if d['quotas_vencidas_count'] > 0:
            w(f'  ⚠ {d["quotas_vencidas_count"]} cuota(s) vencidas sin cobrar — {nf(d["quotas_vencidas_amount"])}')
        else:
            w('  · Sin vencidas. ✓')
        w()

        # KPIs
        w('▌ INDICADORES')
        w(f'  · Morosidad acumulada: {d["mora_pct"]}% ({d["mora_n"]}/{d["mora_total"]} cuotas)')
        w(f'  · Vehículos estancados >90d: {d["estancados"]}')
        w()

        # Caja
        w('▌ FLUJO DE CAJA DEL DÍA')
        w(f'  · Ingresos: {nf(d["cash_in"])}')
        w(f'  · Egresos:  {nf(d["cash_out"])}')
        neto = d['cash_neto']
        signo = '+' if neto >= 0 else ''
        w(f'  · NETO:     {signo}{nf(neto)}')
        w()

        # Alertas críticas (umbrales hardcoded por ahora)
        alertas = []
        if d['mora_pct'] >= 25:
            alertas.append(f'⚠ Morosidad {d["mora_pct"]}% — crítica.')
        if d['estancados'] >= 15:
            alertas.append(f'⚠ {d["estancados"]} vehículos estancados — revisar precios.')
        if d['quotas_vencidas_count'] >= 20:
            alertas.append(f'⚠ {d["quotas_vencidas_count"]} cuotas vencidas acumuladas.')
        if alertas:
            w('▌ ALERTAS')
            for a in alertas:
                w(f'  {a}')
            w()

        w('───────────────────────────────────────────────────────')
        return out.getvalue()
