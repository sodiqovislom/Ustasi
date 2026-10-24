from rest_framework import generics, views, status, permissions
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import Category, Master, Service, Rating, Favorite, PortfolioWork
from .serializers import (
    CategorySerializer, MasterListSerializer, MasterDetailSerializer,
    RatingSerializer, RatingCreateSerializer, MasterProfileUpdateSerializer,
    PortfolioWorkSerializer
)
from .filters import MasterFilter


class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.filter(is_active=True).order_by('order', 'name')
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None


class MasterListView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = MasterListSerializer
    filterset_class = MasterFilter

    def get_queryset(self):
        qs = Master.objects.filter(status='active').select_related('user', 'category').prefetch_related('services')
        ordering = self.request.query_params.get('ordering', '-average_rating')
        if ordering in ['-average_rating', 'price', '-price', '-experience', '-created_at']:
            qs = qs.order_by(ordering)
        return qs


class MasterDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = MasterDetailSerializer
    queryset = Master.objects.select_related('user', 'category').prefetch_related('services', 'ratings__user')


class MasterRateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        master = get_object_or_404(Master, pk=pk)
        serializer = RatingCreateSerializer(
            data=request.data,
            context={'request': request, 'master': master}
        )
        serializer.is_valid(raise_exception=True)
        rating = serializer.save()
        master.refresh_from_db()
        return Response({
            'message': "Bahoyingiz qabul qilindi. Rahmat!",
            'rating': RatingSerializer(rating, context={'request': request}).data,
            'average_rating': master.average_rating,
            'ratings_count': master.ratings_count
        }, status=status.HTTP_201_CREATED)


class MasterMyProfileView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        if not hasattr(user, 'master_profile'):
            return Response(
                {"detail": "Sizda hali usta profili mavjud emas."},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = MasterDetailSerializer(user.master_profile, context={'request': request})
        return Response(serializer.data)

    def post(self, request):
        user = request.user
        if hasattr(user, 'master_profile'):
            return Response(
                {"detail": "Sizda allaqachon usta profili mavjud. Profilni tahrirlash uchun PATCH metodidan foydalaning."},
                status=status.HTTP_400_BAD_REQUEST
            )
        # Convert user to master role if not already
        if user.role != 'master':
            user.role = 'master'
            user.save(update_fields=['role'])

        category_id = request.data.get('category_id')
        category = get_object_or_404(Category, id=category_id)

        master = Master.objects.create(
            user=user,
            category=category,
            description=request.data.get('description', ''),
            experience=int(request.data.get('experience', 1)),
            price=int(request.data.get('price', 50000)),
            region=request.data.get('region', 'Toshkent shahri'),
            district=request.data.get('district', 'Yunusobod tumani'),
            address=request.data.get('address', ''),
            latitude=request.data.get('latitude'),
            longitude=request.data.get('longitude'),
            working_hours=request.data.get('working_hours', '09:00 - 18:00'),
            status='active'
        )

        # Create services if provided
        services_data = request.data.get('services', [])
        for s in services_data:
            name = s.get('name', '').strip()
            price = s.get('price', 0)
            if name:
                Service.objects.create(master=master, name=name, price=int(price))

        serializer = MasterDetailSerializer(master, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def patch(self, request):
        user = request.user
        if not hasattr(user, 'master_profile'):
            return Response(
                {"detail": "Usta profili topilmadi."},
                status=status.HTTP_404_NOT_FOUND
            )
        master = user.master_profile
        serializer = MasterProfileUpdateSerializer(master, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(MasterDetailSerializer(master, context={'request': request}).data)


class SearchSuggestionsView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        query = request.query_params.get('q', '').strip()
        if len(query) < 2:
            return Response({'query': query, 'suggestions': []})

        suggestions = []

        # 1. Matched Categories
        categories = Category.objects.filter(
            Q(name__icontains=query) | Q(slug__icontains=query)
        )[:3]
        for cat in categories:
            suggestions.append({
                'type': 'category',
                'label': cat.name,
                'subtext': 'Kategoriya',
                'category_id': cat.id,
                'slug': cat.slug
            })

        # 2. Matched Masters
        masters = Master.objects.filter(
            status='active'
        ).filter(
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(description__icontains=query)
        ).select_related('user', 'category')[:4]

        for m in masters:
            suggestions.append({
                'type': 'master',
                'label': m.user.full_name,
                'subtext': f"{m.category.name} • {m.region}",
                'master_id': m.id
            })

        # 3. Matched Services
        services = Service.objects.filter(
            name__icontains=query
        ).select_related('master__user')[:3]

        for s in services:
            suggestions.append({
                'type': 'service',
                'label': s.name,
                'subtext': f"{s.master.user.full_name} ({s.price:,} so'm)",
                'master_id': s.master_id
            })

        # 4. Matched Regions/Districts from existing masters
        regions = Master.objects.filter(
            Q(region__icontains=query) | Q(district__icontains=query)
        ).values_list('district', 'region').distinct()[:3]

        for district, region in regions:
            suggestions.append({
                'type': 'location',
                'label': f"{district}, {region}",
                'subtext': 'Hudud',
                'district': district,
                'region': region
            })

        return Response({
            'query': query,
            'suggestions': suggestions[:8]
        })


class LocationsListView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        locations = [
            {
                "region": "Toshkent shahri",
                "lat": 41.2995,
                "lng": 69.2401,
                "districts": [
                    "Yunusobod tumani", "Mirzo Ulug'bek tumani", "Chilonzor tumani",
                    "Shayxontohur tumani", "Yakkasaroy tumani", "Mirobod tumani",
                    "Sergeli tumani", "Olmazor tumani", "Uchtepa tumani",
                    "Yashnobod tumani", "Bektemir tumani", "Yangihayot tumani"
                ]
            },
            {
                "region": "Toshkent viloyati",
                "lat": 41.2500,
                "lng": 69.3500,
                "districts": [
                    "Chirchiq shahri", "Olmaliq shahri", "Angren shahri",
                    "Qibray tumani", "Zangiota tumani", "Bo'stonliq tumani",
                    "Yangiyo'l tumani", "Bekobod tumani"
                ]
            },
            {
                "region": "Samarqand viloyati",
                "lat": 39.6270,
                "lng": 66.9750,
                "districts": [
                    "Samarqand shahri", "Urgut tumani", "Pastdarg'om tumani",
                    "Bulung'ur tumani", "Kattaqo'rg'on shahri"
                ]
            },
            {
                "region": "Farg'ona viloyati",
                "lat": 40.3842,
                "lng": 71.7843,
                "districts": [
                    "Farg'ona shahri", "Marg'ilon shahri", "Qo'qon shahri",
                    "Quva tumani", "Oltiariq tumani"
                ]
            },
            {
                "region": "Andijon viloyati",
                "lat": 40.7821,
                "lng": 72.3442,
                "districts": [
                    "Andijon shahri", "Asaka tumani", "Shahrixon tumani", "Xo'jaobod tumani"
                ]
            },
            {
                "region": "Namangan viloyati",
                "lat": 40.9983,
                "lng": 71.6726,
                "districts": [
                    "Namangan shahri", "Chust tumani", "Kosonsoy tumani", "To'raqo'rg'on tumani"
                ]
            },
            {
                "region": "Buxoro viloyati",
                "lat": 39.7747,
                "lng": 64.4286,
                "districts": [
                    "Buxoro shahri", "G'ijduvon tumani", "Kogon shahri"
                ]
            },
            {
                "region": "Qashqadaryo viloyati",
                "lat": 38.8606,
                "lng": 65.7891,
                "districts": [
                    "Qarshi shahri", "Shahrisabz shahri", "Kitob tumani", "Koson tumani"
                ]
            },
            {
                "region": "Surxondaryo viloyati",
                "lat": 37.2242,
                "lng": 67.2783,
                "districts": [
                    "Termiz shahri", "Denov tumani", "Sherobod tumani"
                ]
            },
            {
                "region": "Xorazm viloyati",
                "lat": 41.5504,
                "lng": 60.6314,
                "districts": [
                    "Urganch shahri", "Xiva shahri", "Xonqa tumani"
                ]
            },
            {
                "region": "Navoiy viloyati",
                "lat": 40.0844,
                "lng": 65.3792,
                "districts": [
                    "Navoiy shahri", "Zarafshon shahri", "Karmana tumani"
                ]
            },
            {
                "region": "Jizzax viloyati",
                "lat": 40.1158,
                "lng": 67.8422,
                "districts": [
                    "Jizzax shahri", "Zomin tumani", "G'allaorol tumani"
                ]
            },
            {
                "region": "Sirdaryo viloyati",
                "lat": 40.5000,
                "lng": 68.6667,
                "districts": [
                    "Guliston shahri", "Yangiyer shahri", "Boyovut tumani"
                ]
            },
            {
                "region": "Qoraqalpog'iston Respublikasi",
                "lat": 42.4619,
                "lng": 59.6166,
                "districts": [
                    "Nukus shahri", "Xo'jayli tumani", "Beruniy tumani", "To'rtko'l tumani"
                ]
            }
        ]
        return Response(locations)


class FavoriteToggleView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, master_id):
        master = get_object_or_404(Master, id=master_id)
        fav = Favorite.objects.filter(user=request.user, master=master).first()
        if fav:
            fav.delete()
            return Response({"is_favorite": False, "message": "Usta saqlanganlardan o'chirildi."})
        else:
            Favorite.objects.create(user=request.user, master=master)
            return Response({"is_favorite": True, "message": "Usta saqlanganlarga qo'shildi."})


class FavoriteListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MasterListSerializer

    def get_queryset(self):
        fav_master_ids = Favorite.objects.filter(user=self.request.user).values_list('master_id', flat=True)
        return Master.objects.filter(id__in=fav_master_ids).select_related('user', 'category').prefetch_related('services')


class MyRatingsListView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        ratings = Rating.objects.filter(user=request.user).select_related('master__user', 'master__category')
        data = []
        for r in ratings:
            data.append({
                'id': r.id,
                'score': r.score,
                'comment': r.comment,
                'created_at': r.created_at,
                'master': {
                    'id': r.master.id,
                    'full_name': r.master.user.full_name,
                    'category': r.master.category.name,
                    'region': r.master.region,
                    'district': r.master.district,
                    'avatar_url': r.master.avatar_url,
                }
            })
        return Response(data)


class PortfolioListCreateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not hasattr(request.user, 'master_profile'):
            return Response({"detail": "Usta profili topilmadi."}, status=status.HTTP_404_NOT_FOUND)
        works = request.user.master_profile.portfolio.all()
        serializer = PortfolioWorkSerializer(works, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request):
        if not hasattr(request.user, 'master_profile'):
            return Response({"detail": "Usta profili topilmadi."}, status=status.HTTP_404_NOT_FOUND)
        serializer = PortfolioWorkSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        work = serializer.save(master=request.user.master_profile)
        return Response(PortfolioWorkSerializer(work, context={'request': request}).data, status=status.HTTP_201_CREATED)


class PortfolioDeleteView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        if not hasattr(request.user, 'master_profile'):
            return Response({"detail": "Usta profili topilmadi."}, status=status.HTTP_404_NOT_FOUND)
        work = get_object_or_404(PortfolioWork, id=pk, master=request.user.master_profile)
        work.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
