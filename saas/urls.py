"""URLs del SaaS — montadas en /api/saas/."""

from django.urls import path
from . import views


urlpatterns = [
    path('plans/',           views.list_plans,       name='saas-plans'),
    path('signup/',          views.public_signup,    name='saas-signup'),
    path('me/subscription/', views.my_subscription,  name='saas-my-subscription'),
    path('upgrade/',         views.request_upgrade,  name='saas-upgrade'),
]
