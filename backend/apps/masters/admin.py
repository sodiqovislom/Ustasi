from django.contrib import admin
from .models import Category, Master, Service, Rating, Favorite


class ServiceInline(admin.TabularInline):
    model = Service
    extra = 1


class RatingInline(admin.TabularInline):
    model = Rating
    extra = 0
    readonly_fields = ('user', 'score', 'comment', 'created_at')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'icon', 'order', 'is_active')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('order', 'is_active')


@admin.register(Master)
class MasterAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'category', 'region', 'district', 'price', 'average_rating', 'ratings_count', 'status')
    list_filter = ('category', 'status', 'region')
    search_fields = ('user__first_name', 'user__last_name', 'user__phone', 'region', 'district')
    inlines = [ServiceInline, RatingInline]


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('user', 'master', 'score', 'created_at')
    list_filter = ('score', 'created_at')
    search_fields = ('user__first_name', 'user__last_name', 'master__user__first_name')


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'master', 'created_at')
