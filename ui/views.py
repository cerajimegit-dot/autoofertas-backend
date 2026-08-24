from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login as auth_login
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from core.models import Enterprise, Vehicle, Sale, Quotum, Customer, Branch, PaymentForm, ViewPermission, CustomUser, Supplier
from core.models.inventory import VehicleCost
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.contrib import messages
from decimal import Decimal
from functools import wraps
import json


def view_permission_required(view_name):
    """Decorador que verifica si el usuario tiene permiso para acceder a una vista.
    Admin siempre tiene acceso. Sin registro = permitido por defecto."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not ViewPermission.user_has_permission(request.user, view_name):
                messages.error(request, 'No tenés permiso para acceder a esta sección. Contactá al administrador.')
                return redirect('ui:dashboard')
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


@require_http_methods(["GET", "POST"])
def login_view(request):
    """Custom login view"""
    if request.user.is_authenticated:
        return redirect('ui:dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        
        # Authenticate user
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Login successful
            auth_login(request, user)
            return redirect('ui:dashboard')
        else:
            # Login failed - show error
            return render(request, 'ui/login.html', {
                'error': 'Usuario o contraseña inválidos',
                'username': username
            })
    
    return render(request, 'ui/login.html')


def index(request):
    """Home page"""
    if request.user.is_authenticated:
        return redirect('ui:dashboard')
    return redirect('ui:login')


@login_required
@view_permission_required('dashboard')
def dashboard(request):
    """Dashboard page with KPIs"""
    
    # Get user's enterprise
    enterprise = request.user.enterprise
    
    if not enterprise:
        # If user has no direct enterprise, get first enterprise
        enterprise = Enterprise.objects.first()
    
    context = {
        'enterprise': enterprise,
    }
    
    return render(request, 'ui/dashboard.html', context)


@login_required
@view_permission_required('vehicles')
def vehicles(request):
    """Vehicles inventory page"""
    
    enterprise = request.user.enterprise or Enterprise.objects.first()
    
    vehicles_list = Vehicle.objects.filter(enterprise=enterprise).select_related(
        'brand', 'model', 'branch'
    ).order_by('-created_at')
    
    context = {
        'vehicles': vehicles_list,
        'enterprise': enterprise,
    }
    
    return render(request, 'ui/vehicles.html', context)


@login_required
@view_permission_required('vehicles')
def vehicle_detail(request, vehicle_id):
    """Detalle de vehículo con gastos adicionales y balance."""
    enterprise = request.user.enterprise or Enterprise.objects.first()

    try:
        vehicle = Vehicle.objects.select_related(
            'brand', 'model', 'branch', 'exchange_rate'
        ).get(id=vehicle_id, enterprise=enterprise)
    except Vehicle.DoesNotExist:
        messages.error(request, 'Vehículo no encontrado.')
        return redirect('ui:vehicles')

    extra_costs = list(
        VehicleCost.objects.filter(vehicle=vehicle)
        .select_related('supplier')
        .order_by('-date', '-id')
    )

    # Balance: sumar todo en PYG
    D = Decimal
    fob = vehicle.fob or D(0)
    container = vehicle.container or D(0)
    dispatch = vehicle.dispatch or D(0)
    cam_vol = vehicle.cam_vol or D(0)
    # Si el vehículo está en USD, convertir el costo base con su exchange_rate
    if vehicle.currency == 'USD' and vehicle.exchange_rate:
        tc = vehicle.exchange_rate.rate or D(0)
        costo_base_pyg = (fob + container + dispatch + cam_vol) * tc
        precio_venta_pyg = (vehicle.price or D(0)) * tc
    else:
        costo_base_pyg = fob + container + dispatch + cam_vol
        precio_venta_pyg = vehicle.price or D(0)

    # Extras en PYG
    costo_extras_pyg = D(0)
    for c in extra_costs:
        amt = c.amount or D(0)
        if c.currency == 'USD':
            tc = c.exchange_rate or D(0)
            costo_extras_pyg += amt * tc
        else:
            costo_extras_pyg += amt

    costo_total_pyg = costo_base_pyg + costo_extras_pyg
    ganancia_pyg = precio_venta_pyg - costo_total_pyg

    # Proveedores activos (para el autocomplete inicial + fallback si JS falla)
    suppliers = Supplier.objects.filter(
        enterprise=enterprise, is_active=True
    ).order_by('name')

    context = {
        'vehicle': vehicle,
        'extra_costs': extra_costs,
        'costo_base_pyg': costo_base_pyg,
        'costo_extras_pyg': costo_extras_pyg,
        'costo_total_pyg': costo_total_pyg,
        'precio_venta_pyg': precio_venta_pyg,
        'ganancia_pyg': ganancia_pyg,
        'suppliers': suppliers,
        'enterprise': enterprise,
    }
    return render(request, 'ui/vehicle_detail.html', context)


@login_required
@view_permission_required('sales')
def sales(request):
    """Sales history page"""
    
    enterprise = request.user.enterprise or Enterprise.objects.first()
    
    sales_list = Sale.objects.filter(enterprise=enterprise).select_related(
        'vehicle', 'customer', 'payment_form', 'branch'
    ).order_by('-sale_date')
    
    context = {
        'sales': sales_list,
        'enterprise': enterprise,
    }
    
    return render(request, 'ui/sales.html', context)


@login_required
@view_permission_required('quotas')
def quotas(request):
    """Quotas to collect page"""
    
    enterprise = request.user.enterprise or Enterprise.objects.first()
    
    quotas_list = Quotum.objects.filter(
        enterprise=enterprise
    ).select_related('sale', 'customer').order_by('due_date', 'sale__sale_number', 'quota_number')
    
    context = {
        'quotas': quotas_list,
        'enterprise': enterprise,
    }
    
    return render(request, 'ui/quotas.html', context)


@login_required
@view_permission_required('customers')
def customers(request):
    """Customers page"""
    
    enterprise = request.user.enterprise or Enterprise.objects.first()
    
    customers_list = Customer.objects.filter(
        enterprise=enterprise
    ).order_by('-created_at')
    
    context = {
        'customers': customers_list,
        'enterprise': enterprise,
    }
    
    return render(request, 'ui/customers.html', context)


@login_required
def api_dashboard_stats(request):
    """API endpoint for dashboard statistics"""
    
    try:
        enterprise = request.user.enterprise or Enterprise.objects.first()
        
        # Get stats
        total_vehicles = Vehicle.objects.filter(enterprise=enterprise).count()
        total_sales = Sale.objects.filter(enterprise=enterprise).count()
        pending_quotas = Quotum.objects.filter(
            enterprise=enterprise,
            status='pending'
        ).count()
        total_customers = Customer.objects.filter(enterprise=enterprise).count()
        
        # Sales by month - using Python due to SQLite date handling
        sales_data = []
        for item in Sale.objects.filter(
            enterprise=enterprise
        ).values('sale_date').annotate(count=Count('id'), total=Sum('total_price')).order_by('sale_date'):
            sales_data.append({
                'month': item['sale_date'].strftime('%m'),
                'count': item['count'],
                'total': float(item['total'] or 0)
            })
        
        # Quotas status
        quotas_status = []
        for item in Quotum.objects.filter(
            enterprise=enterprise
        ).values('status').annotate(count=Count('id'), total=Sum('amount')):
            quotas_status.append({
                'status': item['status'],
                'count': item['count'],
                'total': float(item['total'] or 0)
            })
        
        return JsonResponse({
            'total_vehicles': total_vehicles,
            'total_sales': total_sales,
            'pending_quotas': pending_quotas,
            'total_customers': total_customers,
            'sales_data': sales_data,
            'quotas_status': quotas_status,
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def sale_detail(request, sale_id):
    """Vista de detalle de venta con cuotas relacionadas"""

    enterprise = request.user.enterprise or Enterprise.objects.first()

    try:
        sale = Sale.objects.select_related(
            'customer', 'vehicle', 'vehicle__brand', 'vehicle__model',
            'payment_form', 'branch'
        ).get(id=sale_id, enterprise=enterprise)
    except Sale.DoesNotExist:
        messages.error(request, 'Venta no encontrada.')
        return redirect('ui:sales')

    quotas = sale.quotas.all().order_by('quota_number')
    paid_count = quotas.filter(status='paid').count()
    pending_count = quotas.filter(status__in=['pending', 'overdue']).count()
    quota_total = quotas.aggregate(total=Sum('amount'))['total'] or 0

    # All customers for the assign-customer modal
    all_customers = Customer.objects.filter(
        enterprise=enterprise, is_generic=False
    ).order_by('last_name', 'first_name')

    # Detect if this sale was imported from ODS (CM prefix)
    is_ods_import = sale.sale_number.startswith('CM')

    # For ODS imports, provide prev/next navigation for easy review
    prev_ods = None
    next_ods = None
    if is_ods_import:
        ods_sales = list(Sale.objects.filter(
            enterprise=enterprise, sale_number__startswith='CM'
        ).order_by('sale_number').values_list('id', 'sale_number'))
        current_idx = next((i for i, s in enumerate(ods_sales) if s[0] == sale.id), None)
        if current_idx is not None:
            if current_idx > 0:
                prev_ods = ods_sales[current_idx - 1]
            if current_idx < len(ods_sales) - 1:
                next_ods = ods_sales[current_idx + 1]

    context = {
        'sale': sale,
        'quotas': quotas,
        'paid_count': paid_count,
        'pending_count': pending_count,
        'quota_total': quota_total,
        'all_customers': all_customers,
        'enterprise': enterprise,
        'is_ods_import': is_ods_import,
        'prev_ods': prev_ods,
        'next_ods': next_ods,
        'ods_count': len(ods_sales) if is_ods_import else 0,
        'ods_position': (current_idx + 1) if is_ods_import and current_idx is not None else 0,
    }

    return render(request, 'ui/sale_detail.html', context)


@login_required
@require_http_methods(["POST"])
def sale_assign_customer(request, sale_id):
    """Asignar un cliente real a una venta"""

    enterprise = request.user.enterprise or Enterprise.objects.first()

    try:
        sale = Sale.objects.get(id=sale_id, enterprise=enterprise)
        new_customer_id = request.POST.get('new_customer_id')
        customer = Customer.objects.get(id=new_customer_id, enterprise=enterprise)

        old_customer_name = sale.customer.full_name if sale.customer else 'Sin cliente'
        sale.customer = customer
        sale.save()

        # Also update customer on related quotas
        sale.quotas.update(customer=customer)

        messages.success(
            request,
            f'Cliente actualizado: {old_customer_name} -> {customer.full_name}'
        )
    except Sale.DoesNotExist:
        messages.error(request, 'Venta no encontrada.')
        return redirect('ui:sales')
    except Customer.DoesNotExist:
        messages.error(request, 'Cliente no encontrado.')
    except Exception as e:
        messages.error(request, f'Error al asignar cliente: {str(e)}')

    return redirect('ui:sale_detail', sale_id=sale_id)


@login_required
@require_http_methods(["POST"])
def sale_delete(request, sale_id):
    """Eliminar una venta y sus cuotas asociadas"""

    enterprise = request.user.enterprise or Enterprise.objects.first()

    try:
        sale = Sale.objects.get(id=sale_id, enterprise=enterprise)
        sale_number = sale.sale_number
        quota_count = sale.quotas.count()

        # Delete quotas first, then sale
        sale.quotas.all().delete()
        sale.delete()

        messages.success(
            request,
            f'Venta {sale_number} eliminada junto con {quota_count} cuotas.'
        )
    except Sale.DoesNotExist:
        messages.error(request, 'Venta no encontrada.')
    except Exception as e:
        messages.error(request, f'Error al eliminar: {str(e)}')

    return redirect('ui:sales')


@login_required
@require_http_methods(["POST"])
def api_mark_quotum_paid(request, quotum_id):
    """API endpoint para marcar una cuota como pagada"""
    
    try:
        quotum = Quotum.objects.get(id=quotum_id)
        
        # Verificar que el usuario tiene acceso a esta cuota
        if quotum.enterprise != (request.user.enterprise or Enterprise.objects.first()):
            return JsonResponse({'error': 'No autorizado'}, status=403)
        
        # Marcar como pagada
        quotum.status = 'paid'
        quotum.payment_date = timezone.now().date()
        quotum.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Cuota #{quotum.quota_number} marcada como pagada',
            'quotum': {
                'id': quotum.id,
                'status': quotum.status,
                'payment_date': quotum.payment_date.isoformat() if quotum.payment_date else None,
            }
        })
    
    except Quotum.DoesNotExist:
        return JsonResponse({'error': 'Cuota no encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ===== CRM MODULE =====

@login_required
@view_permission_required('customer_list_crm')
def customer_list_crm(request):
    """CRM: List customers with search, filter, and quick actions"""
    
    enterprise = request.user.enterprise or Enterprise.objects.first()
    
    # Get all customers for the enterprise
    customers_list = Customer.objects.filter(
        enterprise=enterprise
    ).order_by('-created_at')
    
    # Search filter
    search_query = request.GET.get('q', '')
    if search_query:
        customers_list = customers_list.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone__icontains=search_query)
        )
    
    # Enrich customers with sale count and pending quotas
    customers_data = []
    for customer in customers_list:
        sale_count = Sale.objects.filter(customer=customer).count()
        pending_quotas = Quotum.objects.filter(
            customer=customer,
            status='pending'
        ).aggregate(total=Sum('amount'))
        
        customers_data.append({
            'customer': customer,
            'sale_count': sale_count,
            'pending_amount': float(pending_quotas['total'] or 0),
        })
    
    context = {
        'customers_data': customers_data,
        'search_query': search_query,
        'enterprise': enterprise,
        'total_customers': len(customers_data),
    }
    
    return render(request, 'ui/customer_list_crm.html', context)


@login_required
@view_permission_required('customer_list_crm')
def customer_crm(request, customer_id):
    """CRM: Detailed customer view with sales history and quota status"""
    
    enterprise = request.user.enterprise or Enterprise.objects.first()
    
    try:
        customer = Customer.objects.get(id=customer_id, enterprise=enterprise)
    except Customer.DoesNotExist:
        return render(request, '404.html', status=404)
    
    # Get customer's sales
    sales_list = Sale.objects.filter(
        customer=customer
    ).select_related('vehicle', 'payment_form', 'branch').order_by('-sale_date')
    
    # Get customer's quotas
    quotas_list = Quotum.objects.filter(
        customer=customer
    ).order_by('quota_number')
    
    # Calculate totals
    total_sales = sales_list.aggregate(total=Sum('total_price'))['total'] or 0
    pending_amount = quotas_list.filter(status='pending').aggregate(
        total=Sum('amount')
    )['total'] or 0
    paid_amount = quotas_list.filter(status='paid').aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    context = {
        'customer': customer,
        'sales_list': sales_list,
        'quotas_list': quotas_list,
        'total_sales': float(total_sales),
        'pending_amount': float(pending_amount),
        'paid_amount': float(paid_amount),
        'enterprise': enterprise,
    }
    
    return render(request, 'ui/customer_crm.html', context)


@login_required
@view_permission_required('customer_edit')
@require_http_methods(["GET", "POST"])
def customer_edit(request, customer_id):
    """CRM: Edit customer information"""
    
    enterprise = request.user.enterprise or Enterprise.objects.first()
    
    try:
        customer = Customer.objects.get(id=customer_id, enterprise=enterprise)
    except Customer.DoesNotExist:
        return render(request, '404.html', status=404)
    
    if request.method == 'POST':
        # Update customer data
        customer.first_name = request.POST.get('first_name', customer.first_name)
        customer.last_name = request.POST.get('last_name', customer.last_name)
        customer.email = request.POST.get('email', customer.email)
        customer.phone = request.POST.get('phone', customer.phone)
        customer.address = request.POST.get('address', customer.address)
        customer.city = request.POST.get('city', customer.city)
        customer.estado = request.POST.get('estado', customer.estado)
        
        try:
            customer.save()
            return redirect('ui:customer_crm', customer_id=customer.id)
        except Exception as e:
            context = {
                'customer': customer,
                'error': f'Error al guardar: {str(e)}',
                'enterprise': enterprise,
            }
            return render(request, 'ui/customer_edit.html', context)
    
    context = {
        'customer': customer,
        'enterprise': enterprise,
    }
    
    return render(request, 'ui/customer_edit.html', context)


@login_required
@view_permission_required('sale_register')
@require_http_methods(["GET", "POST"])
def sale_register(request):
    """CRM: Register a new sale"""
    
    enterprise = request.user.enterprise or Enterprise.objects.first()
    
    if request.method == 'POST':
        try:
            # Get form data
            vehicle_id = request.POST.get('vehicle_id')
            customer_id = request.POST.get('customer_id')
            payment_form_id = request.POST.get('payment_form_id')
            total_price = request.POST.get('total_price')
            sale_date_str = request.POST.get('sale_date')
            branch_id = request.POST.get('branch_id')
            notes = request.POST.get('notes', '')
            
            # Get objects
            vehicle = Vehicle.objects.get(id=vehicle_id, enterprise=enterprise)
            customer = Customer.objects.get(id=customer_id, enterprise=enterprise)
            payment_form = PaymentForm.objects.get(id=payment_form_id, enterprise=enterprise)
            branch = Branch.objects.get(id=branch_id, enterprise=enterprise) if branch_id else None
            
            # Create sale
            sale = Sale.objects.create(
                enterprise=enterprise,
                vehicle=vehicle,
                customer=customer,
                payment_form=payment_form,
                total_price=total_price,
                sale_date=sale_date_str,
                branch=branch,
                notes=notes,
            )
            
            # Get payment form details
            num_quotas = int(payment_form.months_to_pay) if payment_form.months_to_pay else 1
            quota_amount = Decimal(total_price) / Decimal(num_quotas)
            
            # Create quotas
            for i in range(1, num_quotas + 1):
                Quotum.objects.create(
                    enterprise=enterprise,
                    sale=sale,
                    customer=customer,
                    quota_number=i,
                    amount=quota_amount,
                    due_date=sale.sale_date,
                    status='pending',
                )
            
            return redirect('ui:sale_detail', sale_id=sale.id)
        
        except Exception as e:
            context = {
                'vehicles': Vehicle.objects.filter(enterprise=enterprise),
                'customers': Customer.objects.filter(enterprise=enterprise),
                'payment_forms': PaymentForm.objects.filter(enterprise=enterprise),
                'branches': Branch.objects.filter(enterprise=enterprise),
                'error': f'Error al registrar venta: {str(e)}',
                'enterprise': enterprise,
            }
            return render(request, 'ui/sale_register.html', context)
    
    # GET request - show form
    vehicles = Vehicle.objects.filter(enterprise=enterprise)
    customers = Customer.objects.filter(enterprise=enterprise)
    payment_forms = PaymentForm.objects.filter(enterprise=enterprise)
    branches = Branch.objects.filter(enterprise=enterprise)
    
    context = {
        'vehicles': vehicles,
        'customers': customers,
        'payment_forms': payment_forms,
        'branches': branches,
        'enterprise': enterprise,
    }
    
    return render(request, 'ui/sale_register.html', context)


@login_required
@view_permission_required('quota_payment')
@require_http_methods(["GET", "POST"])
def quota_payment(request, quotum_id):
    """CRM: Process quota payment"""
    
    enterprise = request.user.enterprise or Enterprise.objects.first()
    
    try:
        quotum = Quotum.objects.get(id=quotum_id, enterprise=enterprise)
    except Quotum.DoesNotExist:
        return render(request, '404.html', status=404)
    
    if request.method == 'POST':
        try:
            # Mark as paid
            quotum.status = 'paid'
            quotum.payment_date = request.POST.get('payment_date', timezone.now().date())
            quotum.notes = request.POST.get('notes', '')
            quotum.save()
            
            # Redirect to customer detail
            return redirect('ui:customer_crm', customer_id=quotum.customer.id)
        
        except Exception as e:
            context = {
                'quotum': quotum,
                'error': f'Error al registrar pago: {str(e)}',
                'enterprise': enterprise,
            }
            return render(request, 'ui/quota_payment.html', context)
    
    # GET request - show payment form
    context = {
        'quotum': quotum,
        'enterprise': enterprise,
    }
    
    return render(request, 'ui/quota_payment.html', context)


@login_required
@view_permission_required('payment_history')
def payment_history(request, customer_id):
    """CRM: Show customer payment history"""
    
    enterprise = request.user.enterprise or Enterprise.objects.first()
    
    try:
        customer = Customer.objects.get(id=customer_id, enterprise=enterprise)
    except Customer.DoesNotExist:
        return render(request, '404.html', status=404)
    
    # Get all quotas (paid and pending)
    quotas_list = Quotum.objects.filter(
        customer=customer
    ).select_related('sale').order_by('-created_at')
    
    # Separate by status
    paid_quotas = quotas_list.filter(status='paid')
    pending_quotas = quotas_list.filter(status='pending')
    
    # Calculate totals
    total_paid = paid_quotas.aggregate(total=Sum('amount'))['total'] or 0
    total_pending = pending_quotas.aggregate(total=Sum('amount'))['total'] or 0
    
    context = {
        'customer': customer,
        'paid_quotas': paid_quotas,
        'pending_quotas': pending_quotas,
        'total_paid': float(total_paid),
        'total_pending': float(total_pending),
        'all_quotas': quotas_list,
        'enterprise': enterprise,
    }
    
    return render(request, 'ui/payment_history.html', context)


@login_required
@view_permission_required('quotas')
@require_http_methods(["GET", "POST"])
def quota_generator(request):
    """CRM: Generate quotas for a sale that has no quotas yet"""

    enterprise = request.user.enterprise or Enterprise.objects.first()

    if request.method == 'POST':
        try:
            sale_id = request.POST.get('sale_id')
            plan_name_val = request.POST.get('plan_name', '')
            quota_data_json = request.POST.get('quota_data', '[]')

            sale = Sale.objects.get(id=sale_id, enterprise=enterprise)

            # Safety check: sale must not already have quotas
            if sale.quotas.exists():
                raise ValueError(f'La venta {sale.sale_number} ya tiene cuotas cargadas.')

            quota_list = json.loads(quota_data_json)
            if not quota_list:
                raise ValueError('No se recibieron datos de cuotas.')

            total_plan = len(quota_list)

            created = 0
            for q in quota_list:
                Quotum.objects.create(
                    enterprise=enterprise,
                    sale=sale,
                    customer=sale.customer,
                    quota_number=q['quota_number'],
                    total_plan=total_plan,
                    plan_name=plan_name_val,
                    amount=Decimal(str(q['amount'])),
                    interest=Decimal('0'),
                    due_date=q['due_date'],
                    status='pending',
                )
                created += 1

            messages.success(
                request,
                f'{created} cuotas creadas para la venta {sale.sale_number}.'
            )
            return redirect('ui:sale_detail', sale_id=sale.id)

        except Sale.DoesNotExist:
            error = 'Venta no encontrada.'
        except ValueError as e:
            error = str(e)
        except Exception as e:
            error = f'Error al guardar cuotas: {str(e)}'

        # On error, re-render with error message
        sales_without_quotas = Sale.objects.filter(
            enterprise=enterprise
        ).exclude(
            id__in=Quotum.objects.filter(enterprise=enterprise).values_list('sale_id', flat=True).distinct()
        ).select_related('customer', 'vehicle', 'vehicle__brand', 'vehicle__model').order_by('sale_number')

        return render(request, 'ui/quota_generator.html', {
            'sales_without_quotas': sales_without_quotas,
            'enterprise': enterprise,
            'error': error,
        })

    # GET request
    sales_without_quotas = Sale.objects.filter(
        enterprise=enterprise
    ).exclude(
        id__in=Quotum.objects.filter(enterprise=enterprise).values_list('sale_id', flat=True).distinct()
    ).select_related('customer', 'vehicle', 'vehicle__brand', 'vehicle__model').order_by('sale_number')

    # Optional preselection via query parameter
    preselect_sale_id = request.GET.get('sale_id')
    if preselect_sale_id:
        try:
            preselect_sale_id = int(preselect_sale_id)
        except (ValueError, TypeError):
            preselect_sale_id = None

    context = {
        'sales_without_quotas': sales_without_quotas,
        'enterprise': enterprise,
        'preselect_sale_id': preselect_sale_id,
    }

    return render(request, 'ui/quota_generator.html', context)


# ===== ADMIN: PERMISOS DE USUARIO =====

@login_required
def user_permissions_list(request):
    """Lista de usuarios de la empresa para configurar permisos (solo admin)"""
    if request.user.role != 'admin':
        messages.error(request, 'Solo los administradores pueden configurar permisos.')
        return redirect('ui:dashboard')

    enterprise = request.user.enterprise or Enterprise.objects.first()
    users = CustomUser.objects.filter(
        enterprise=enterprise, is_active=True
    ).exclude(role='admin').order_by('first_name', 'last_name')

    users_with_perms = []
    for u in users:
        perms = ViewPermission.get_user_permissions(u)
        denied_count = sum(1 for v in perms.values() if not v)
        users_with_perms.append({
            'user': u,
            'permissions': perms,
            'denied_count': denied_count,
        })

    context = {
        'users_with_perms': users_with_perms,
        'enterprise': enterprise,
    }
    return render(request, 'ui/user_permissions_list.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def user_permissions_edit(request, user_id):
    """Editar permisos de un usuario específico (solo admin)"""
    if request.user.role != 'admin':
        messages.error(request, 'Solo los administradores pueden configurar permisos.')
        return redirect('ui:dashboard')

    enterprise = request.user.enterprise or Enterprise.objects.first()
    target_user = CustomUser.objects.filter(
        id=user_id, enterprise=enterprise, is_active=True
    ).exclude(role='admin').first()

    if not target_user:
        messages.error(request, 'Usuario no encontrado.')
        return redirect('ui:user_permissions_list')

    if request.method == 'POST':
        permissions_dict = {}
        for view_name, _ in ViewPermission.VIEW_CHOICES:
            permissions_dict[view_name] = request.POST.get(f'perm_{view_name}') == 'on'
        ViewPermission.set_user_permissions(target_user, permissions_dict, request.user)
        messages.success(request, f'Permisos actualizados para {target_user.get_full_name() or target_user.username}.')
        return redirect('ui:user_permissions_list')

    # GET: mostrar formulario
    current_perms = ViewPermission.get_user_permissions(target_user)
    view_choices = ViewPermission.VIEW_CHOICES

    context = {
        'target_user': target_user,
        'current_perms': current_perms,
        'view_choices': view_choices,
        'enterprise': enterprise,
    }
    return render(request, 'ui/user_permissions_edit.html', context)
