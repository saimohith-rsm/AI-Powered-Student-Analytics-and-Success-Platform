from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'department_name', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('Smart Campus Roles & Info', {'fields': ('role', 'phone_number', 'department_name')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Smart Campus Roles & Info', {'fields': ('role', 'phone_number', 'department_name')}),
    )
    search_fields = ('username', 'email', 'first_name', 'last_name', 'department_name')
