from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from core.views import (
    CustomUserViewSet, EnterpriseViewSet, BranchViewSet, AuditLogViewSet,
    BrandViewSet, VehicleModelViewSet, ExchangeRateViewSet, VehicleViewSet,
    VehicleCostViewSet,
    CustomerViewSet, PaymentFormViewSet, SaleViewSet, QuotumViewSet,
    DashboardViewSet, CashMovementViewSet,
)

router = DefaultRouter()

# Autenticación
router.register(r'users', CustomUserViewSet, basename='user')

# Empresa
router.register(r'enterprises', EnterpriseViewSet, basename='enterprise')
router.register(r'branches', BranchViewSet, basename='branch')

# Auditoría
router.register(r'audit-logs', AuditLogViewSet, basename='auditlog')

# Inventario
router.register(r'brands', BrandViewSet, basename='brand')
router.register(r'vehicle-models', VehicleModelViewSet, basename='vehiclemodel')
router.register(r'exchange-rates', ExchangeRateViewSet, basename='exchangerate')
router.register(r'vehicles', VehicleViewSet, basename='vehicle')
router.register(r'vehicle-costs', VehicleCostViewSet, basename='vehiclecost')

# Ventas
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'payment-forms', PaymentFormViewSet, basename='paymentform')
router.register(r'sales', SaleViewSet, basename='sale')
router.register(r'quotas', QuotumViewSet, basename='quotum')

# Dashboard
router.register(r'dashboard', DashboardViewSet, basename='dashboard')

# Flujo de caja
router.register(r'cash-movements', CashMovementViewSet, basename='cashmovement')

urlpatterns = [
    path('', include(router.urls)),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
