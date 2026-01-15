from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Role


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Registers the custom User model with the Django admin."""
    pass


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """Admin configuration for the Role model."""
    list_display = ('name', 'display_name', 'is_active')
    search_fields = ('name', 'display_name')
    filter_horizontal = ('permissions',)
