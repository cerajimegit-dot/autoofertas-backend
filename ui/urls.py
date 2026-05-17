from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

app_name = 'ui'

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', LogoutView.as_view(next_page='ui:login'), name='logout'),
    
    path('dashboard/', views.dashboard, name='dashboard'),
    path('vehicles/', views.vehicles, name='vehicles'),
    path('sales/', views.sales, name='sales'),
    path('sales/<int:sale_id>/', views.sale_detail, name='sale_detail'),
    path('sales/<int:sale_id>/assign-customer/', views.sale_assign_customer, name='sale_assign_customer'),
    path('sales/<int:sale_id>/delete/', views.sale_delete, name='sale_delete'),
    path('quotas/', views.quotas, name='quotas'),
    path('customers/', views.customers, name='customers'),
    
    # CRM Module
    path('crm/customers/', views.customer_list_crm, name='customer_list_crm'),
    path('crm/customer/<int:customer_id>/', views.customer_crm, name='customer_crm'),
    path('crm/customer/<int:customer_id>/edit/', views.customer_edit, name='customer_edit'),
    path('crm/sale-register/', views.sale_register, name='sale_register'),
    path('crm/quota/<int:quotum_id>/pay/', views.quota_payment, name='quota_payment'),
    path('crm/customer/<int:customer_id>/payments/', views.payment_history, name='payment_history'),
    path('crm/quota-generator/', views.quota_generator, name='quota_generator'),
    
    # Admin: Permisos
    path('admin/permissions/', views.user_permissions_list, name='user_permissions_list'),
    path('admin/permissions/<int:user_id>/', views.user_permissions_edit, name='user_permissions_edit'),
    
    # API endpoints
    path('api/dashboard-stats/', views.api_dashboard_stats, name='api_dashboard_stats'),
    path('api/quotum/<int:quotum_id>/pay/', views.api_mark_quotum_paid, name='api_mark_quotum_paid'),
]
