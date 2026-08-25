from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

# Unregister standard UserAdmin to replace it with a Group-free UserAdmin
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    """
    Custom UserAdmin that removes all references to auth_group/groups,
    matching the project's migration (0001_drop_auth_group_tables)
    where auth_group tables were dropped.
    """
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    filter_horizontal = ('user_permissions',)

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        (
            'Permissions',
            {
                'fields': (
                    'is_active',
                    'is_staff',
                    'is_superuser',
                    'user_permissions',
                ),
            },
        ),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
