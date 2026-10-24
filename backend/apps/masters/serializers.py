import math
from rest_framework import serializers
from django.db import IntegrityError
from django.contrib.auth import get_user_model
from .models import Category, Master, Service, Rating, Favorite, PortfolioWork
from apps.users.serializers import UserSerializer

User = get_user_model()


class PortfolioWorkSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = PortfolioWork
        fields = ['id', 'title', 'description', 'image', 'image_url', 'created_at']
        read_only_fields = ['id', 'created_at']

    def to_internal_value(self, data):
        data = data.copy() if hasattr(data, 'copy') else dict(data)
        img_val = data.get('image')
        if isinstance(img_val, str) and img_val.startswith('data:image'):
            try:
                import base64
                import uuid
                from django.core.files.base import ContentFile
                header, imgstr = img_val.split(';base64,')
                ext = header.split('/')[-1].split(';')[0]
                if ext == 'jpeg':
                    ext = 'jpg'
                file_name = f"portfolio_{uuid.uuid4().hex[:8]}.{ext}"
                data['image'] = ContentFile(base64.b64decode(imgstr), name=file_name)
            except Exception:
                pass
        return super().to_internal_value(data)

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class CategorySerializer(serializers.ModelSerializer):
    masters_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'icon', 'description', 'order', 'masters_count']

    def get_masters_count(self, obj):
        return obj.masters.filter(status='active').count()


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ['id', 'name', 'price']


class RatingSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_avatar = serializers.SerializerMethodField()

    class Meta:
        model = Rating
        fields = ['id', 'user', 'user_name', 'user_avatar', 'master', 'score', 'comment', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']

    def get_user_avatar(self, obj):
        if obj.user.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.user.avatar.url)
            return obj.user.avatar.url
        return None


class RatingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rating
        fields = ['id', 'score', 'comment']
        extra_kwargs = {
            'score': {'min_value': 1, 'max_value': 5, 'required': True}
        }

    def validate_score(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Baho faqat 1 dan 5 gacha bo‘lishi mumkin.")
        return value

    def validate(self, attrs):
        user = self.context['request'].user
        master = self.context['master']

        if not user.is_authenticated:
            raise serializers.ValidationError("Baho berish uchun avval tizimga kiring.")

        if master.user_id == user.id:
            raise serializers.ValidationError("Usta o‘ziga o‘zi baho bera olmaydi.")

        if Rating.objects.filter(user=user, master=master).exists():
            raise serializers.ValidationError(
                "Siz ushbu ustaga allaqachon baho bergansiz. Har bir ustaga faqat bir marta baho berish mumkin."
            )

        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        master = self.context['master']
        try:
            rating = Rating.objects.create(
                user=user,
                master=master,
                score=validated_data['score'],
                comment=validated_data.get('comment', '')
            )
            return rating
        except IntegrityError:
            raise serializers.ValidationError(
                "Siz ushbu ustaga allaqachon baho bergansiz. Har bir ustaga faqat bir marta baho berish mumkin."
            )


class MasterListSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    full_name = serializers.CharField(read_only=True)
    phone = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    is_favorite = serializers.SerializerMethodField()
    distance_km = serializers.SerializerMethodField()
    services = ServiceSerializer(many=True, read_only=True)

    class Meta:
        model = Master
        fields = [
            'id', 'user_id', 'full_name', 'avatar_url', 'phone',
            'category', 'description', 'experience', 'price',
            'region', 'district', 'address', 'latitude', 'longitude',
            'working_hours', 'status', 'average_rating', 'ratings_count',
            'is_favorite', 'distance_km', 'services'
        ]

    def get_avatar_url(self, obj):
        if obj.user.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.user.avatar.url)
            return obj.user.avatar.url
        return None

    def get_phone(self, obj):
        # Guests can see that phone exists, but full phone action checks auth on frontend/backend
        return obj.user.phone

    def get_is_favorite(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.favorited_by.filter(user=request.user).exists()
        return False

    def get_distance_km(self, obj):
        request = self.context.get('request')
        if not request:
            return None
        user_lat = request.query_params.get('lat')
        user_lng = request.query_params.get('lng')
        if user_lat and user_lng and obj.latitude and obj.longitude:
            try:
                lat1, lon1 = float(user_lat), float(user_lng)
                lat2, lon2 = float(obj.latitude), float(obj.longitude)
                # Haversine formula
                r = 6371.0  # Earth's radius in km
                d_lat = math.radians(lat2 - lat1)
                d_lon = math.radians(lon2 - lon1)
                a = math.sin(d_lat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2
                c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
                return round(r * c, 1)
            except (ValueError, TypeError):
                return None
        return None


class MasterDetailSerializer(MasterListSerializer):
    ratings = RatingSerializer(many=True, read_only=True)
    portfolio = PortfolioWorkSerializer(many=True, read_only=True)
    user_rated = serializers.SerializerMethodField()
    user_rating = serializers.SerializerMethodField()

    class Meta(MasterListSerializer.Meta):
        fields = MasterListSerializer.Meta.fields + ['ratings', 'user_rated', 'user_rating', 'portfolio']

    def get_user_rated(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.ratings.filter(user=request.user).exists()
        return False

    def get_user_rating(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            r = obj.ratings.filter(user=request.user).first()
            if r:
                return {'id': r.id, 'score': r.score, 'comment': r.comment}
        return None


class MasterProfileUpdateSerializer(serializers.ModelSerializer):
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', write_only=True, required=False
    )
    first_name = serializers.CharField(source='user.first_name', required=False)
    last_name = serializers.CharField(source='user.last_name', required=False, allow_blank=True)
    phone = serializers.CharField(source='user.phone', required=False)
    services = ServiceSerializer(many=True, required=False)

    class Meta:
        model = Master
        fields = [
            'category_id', 'description', 'experience', 'price',
            'region', 'district', 'address', 'latitude', 'longitude',
            'working_hours', 'status', 'first_name', 'last_name',
            'phone', 'services'
        ]

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        services_data = validated_data.pop('services', None)

        # Update user fields
        user = instance.user
        for attr, value in user_data.items():
            setattr(user, attr, value)
        user.save()

        # Update master fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update services if passed
        if services_data is not None:
            instance.services.all().delete()
            for s_data in services_data:
                Service.objects.create(master=instance, **s_data)

        return instance
