import math
from django.db.models import Q
import django_filters
from .models import Master


class MasterFilter(django_filters.FilterSet):
    category = django_filters.CharFilter(method='filter_category')
    region = django_filters.CharFilter(lookup_expr='icontains')
    district = django_filters.CharFilter(lookup_expr='icontains')
    min_price = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='price', lookup_expr='lte')
    min_rating = django_filters.NumberFilter(field_name='average_rating', lookup_expr='gte')
    search = django_filters.CharFilter(method='filter_search')
    distance = django_filters.NumberFilter(method='filter_distance')

    class Meta:
        model = Master
        fields = ['category', 'region', 'district', 'min_price', 'max_price', 'min_rating', 'search']

    def filter_category(self, queryset, name, value):
        if not value:
            return queryset
        if value.isdigit():
            return queryset.filter(category_id=int(value))
        return queryset.filter(Q(category__slug__iexact=value) | Q(category__name__iexact=value))

    def filter_search(self, queryset, name, value):
        if not value or len(value.strip()) == 0:
            return queryset
        val = value.strip()
        return queryset.filter(
            Q(user__first_name__icontains=val) |
            Q(user__last_name__icontains=val) |
            Q(category__name__icontains=val) |
            Q(description__icontains=val) |
            Q(region__icontains=val) |
            Q(district__icontains=val) |
            Q(services__name__icontains=val)
        ).distinct()

    def filter_distance(self, queryset, name, value):
        """Filter by geographical radius (in km) if user coordinates (lat, lng) are provided."""
        request = self.request
        if not request or not value:
            return queryset
        user_lat = request.query_params.get('lat')
        user_lng = request.query_params.get('lng')
        if not user_lat or not user_lng:
            return queryset

        try:
            u_lat = float(user_lat)
            u_lng = float(user_lng)
            max_km = float(value)
        except (ValueError, TypeError):
            return queryset

        # Calculate bounding box first for DB optimization
        # 1 deg lat ~= 111 km
        lat_delta = max_km / 111.0
        lng_delta = max_km / (111.0 * max(0.1, math.cos(math.radians(u_lat))))

        candidates = queryset.filter(
            latitude__isnull=False,
            longitude__isnull=False,
            latitude__gte=u_lat - lat_delta,
            latitude__lte=u_lat + lat_delta,
            longitude__gte=u_lng - lng_delta,
            longitude__lte=u_lng + lng_delta
        )

        # Precise haversine filter
        matched_ids = []
        r = 6371.0
        for master in candidates:
            d_lat = math.radians(master.latitude - u_lat)
            d_lon = math.radians(master.longitude - u_lng)
            a = math.sin(d_lat / 2) ** 2 + math.cos(math.radians(u_lat)) * math.cos(math.radians(master.latitude)) * math.sin(d_lon / 2) ** 2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            dist = r * c
            if dist <= max_km:
                matched_ids.append(master.id)

        return queryset.filter(id__in=matched_ids)
