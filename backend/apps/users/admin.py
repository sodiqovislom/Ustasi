from django.contrib import admin
from .models import User


admin.site.site_header = "Ustasi Boshqaruv Paneli"
admin.site.site_title = "Ustasi Admin"
admin.site.index_title = "Platformani boshqarish"


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'phone', 'email', 'role', 'is_active', 'created_at')
    list_filter = ('role', 'is_active', 'created_at')
    search_fields = ('first_name', 'last_name', 'phone', 'email')
    ordering = ('-created_at',)
