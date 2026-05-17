from django import template
from core.models import ViewPermission

register = template.Library()


@register.filter
def has_view_perm(user, view_name):
    """Template filter: {{ user|has_view_perm:"dashboard" }}"""
    if not user or not user.is_authenticated:
        return False
    return ViewPermission.user_has_permission(user, view_name)
