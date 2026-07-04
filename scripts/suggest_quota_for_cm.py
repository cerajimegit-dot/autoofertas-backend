"""Para un CashMovement dado, sugiere candidatos de Quotum a linkear.

Estrategias de busqueda:
  1. Si CM tiene sale_id -> buscar Quotum de esa venta con amount cercano
     y status compatible.
  2. Si no, buscar Quotum con amount exacto y due_date o payment_date
     cercano a CM.date (+/- 30 dias).
  3. Mostrar score por candidato:
     +50 si sale_id coincide
     +30 si amount es exacto (+/- 100)
     +20 si payment_date == CM.date
     +10 si due_date dentro de +/- 30 dias de CM.date
     +5  si status == paid

USO:
    DB_ENGINE=sqlite python scripts/suggest_quota_for_cm.py CM_ID
    DB_ENGINE=sqlite python scripts/suggest_quota_for_cm.py 42
"""

import argparse
import os
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'playas_autos.settings')
django.setup()

from core.models import CashMovement, Quotum


def fmt(n):
    return f'Gs.{int(n or 0):,}'.replace(',', '.')


def score_quota(q, cm):
    """Calcula score de cuanto matchea esta Quotum con el CashMovement."""
    score = 0
    reasons = []

    if cm.sale_id and q.sale_id == cm.sale_id:
        score += 50
        reasons.append('sale_id coincide')

    amount_diff = abs(int(q.amount or 0) - int(cm.amount or 0))
    if amount_diff <= 100:
        score += 30
        reasons.append('amount exacto')
    elif amount_diff <= int(cm.amount or 1) * 0.05:
        score += 15
        reasons.append('amount cercano (+/- 5%)')

    if q.payment_date == cm.date:
        score += 20
        reasons.append('payment_date == CM.date')

    if q.due_date and cm.date:
        diff = abs((q.due_date - cm.date).days)
        if diff <= 7:
            score += 15
            reasons.append(f'due_date a {diff}d de CM.date')
        elif diff <= 30:
            score += 10
            reasons.append(f'due_date a {diff}d de CM.date')

    if q.status == 'paid':
        score += 5
        reasons.append('quota paid')

    return score, reasons


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('cm_id', type=int, help='ID del CashMovement a investigar')
    p.add_argument('--top', type=int, default=10,
                    help='Cuantos candidatos mostrar (default 10)')
    args = p.parse_args()

    cm = CashMovement.objects.filter(id=args.cm_id).select_related('sale').first()
    if not cm:
        print(f'  No existe CashMovement id={args.cm_id}')
        return

    print(f'\n  CashMovement #{cm.id}')
    print(f'    fecha:       {cm.date}')
    print(f'    monto:       {fmt(cm.amount)}')
    print(f'    kind:        {cm.kind}')
    print(f'    direction:   {cm.direction}')
    print(f'    sale_id:     {cm.sale_id or "(ninguno)"}')
    print(f'    sale_number: {cm.sale.sale_number if cm.sale else "—"}')
    print(f'    description: {cm.description or ""}')
    print(f'    quota_id actual: {cm.quota_id or "(NULL — esto es lo que vamos a setear)"}')

    # Buscar candidatos
    candidates_qs = Quotum.objects.all()
    if cm.sale_id:
        # Caso (1): tenemos sale, restringir a sus cuotas
        candidates_qs = candidates_qs.filter(sale_id=cm.sale_id)
        print(f'\n  Buscando dentro de la venta {cm.sale.sale_number} ({candidates_qs.count()} cuotas)...')
    else:
        # Caso (2): sin sale — buscar por monto y fecha cercana
        from datetime import timedelta
        date_low = cm.date - timedelta(days=60)
        date_high = cm.date + timedelta(days=60)
        candidates_qs = candidates_qs.filter(
            amount__gte=int(cm.amount or 0) * 0.95,
            amount__lte=int(cm.amount or 0) * 1.05,
        ).filter(
            due_date__gte=date_low,
            due_date__lte=date_high,
        )
        print(f'\n  Sin sale_id — busqueda por amount +/- 5% y fecha +/- 60d ({candidates_qs.count()} candidatos)...')

    # Score cada uno
    candidates_qs = candidates_qs.select_related('sale')
    scored = []
    for q in candidates_qs:
        s, reasons = score_quota(q, cm)
        if s > 0:
            scored.append((s, q, reasons))
    scored.sort(key=lambda x: -x[0])

    print(f'\n  === Top {min(args.top, len(scored))} candidatos ===')
    if not scored:
        print('  Ningun candidato con score > 0. Escalar al senior.')
        return

    print(f'  {"score":>5}  {"q_id":>5}  {"sale_num":15}  {"#/total":>10}  {"amount":>14}  {"due":12}  {"pay":12}  {"status":10}  reasons')
    for s, q, reasons in scored[:args.top]:
        sn = q.sale.sale_number if q.sale else ''
        print(f'  {s:>5}  {q.id:>5}  {sn:15}  {q.quota_number}/{q.total_plan:<8}  '
              f'{fmt(q.amount):>14}  {str(q.due_date):12}  {str(q.payment_date) or "—":12}  '
              f'{q.status:10}  {", ".join(reasons)}')

    if len(scored) >= 1 and scored[0][0] >= 70:
        print(f'\n  💡 Top candidato tiene score {scored[0][0]} — alta confianza.')
        print(f'     Para linkear:  python scripts/link_cm_to_quota.py {cm.id} {scored[0][1].id}')
    elif len(scored) >= 1:
        print(f'\n  Top candidato tiene score {scored[0][0]} — revisar a mano antes de linkear.')


if __name__ == '__main__':
    main()
