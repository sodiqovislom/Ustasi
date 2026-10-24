import re
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db.models import Q
from .models import normalize_phone_number

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'first_name', 'last_name', 'full_name',
            'phone', 'email', 'role', 'avatar', 'avatar_url',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def to_internal_value(self, data):
        data = data.copy() if hasattr(data, 'copy') else dict(data)
        avatar_val = data.get('avatar')
        if isinstance(avatar_val, str) and avatar_val.startswith('data:image'):
            try:
                import base64
                import uuid
                from django.core.files.base import ContentFile
                header, imgstr = avatar_val.split(';base64,')
                ext = header.split('/')[-1].split(';')[0]
                if ext == 'jpeg':
                    ext = 'jpg'
                file_name = f"avatar_{uuid.uuid4().hex[:8]}.{ext}"
                data['avatar'] = ContentFile(base64.b64decode(imgstr), name=file_name)
            except Exception:
                pass
        return super().to_internal_value(data)

    def get_avatar_url(self, obj):
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6, error_messages={
        'min_length': "Parol kamida 6 ta belgidan iborat bo‘lishi kerak."
    })
    password_confirm = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone', 'email',
            'password', 'password_confirm', 'role'
        ]
        extra_kwargs = {
            'first_name': {'required': True, 'allow_blank': False},
            'last_name': {'required': False, 'allow_blank': True},
            'role': {'required': False},
        }

    def validate_phone(self, value):
        if not value:
            return None
        normalized = normalize_phone_number(value)
        if len(re.sub(r'\D', '', normalized)) < 9:
            raise serializers.ValidationError("Telefon raqami noto‘g‘ri formatda kiritildi.")
        if User.objects.filter(phone=normalized).exists():
            raise serializers.ValidationError("Bu telefon raqami allaqachon ro‘yxatdan o‘tgan.")
        return normalized

    def validate_email(self, value):
        if not value:
            return None
        cleaned = value.strip().lower()
        if User.objects.filter(email__iexact=cleaned).exists():
            raise serializers.ValidationError("Bu elektron pochta allaqachon ro‘yxatdan o‘tgan.")
        return cleaned

    def validate(self, attrs):
        phone = attrs.get('phone')
        email = attrs.get('email')
        if not phone and not email:
            raise serializers.ValidationError({
                "non_field_errors": ["Ro‘yxatdan o‘tish uchun telefon raqami yoki elektron pochta kiritilishi shart."]
            })

        pwd = attrs.get('password')
        pwd_confirm = attrs.get('password_confirm')
        if pwd_confirm and pwd != pwd_confirm:
            raise serializers.ValidationError({
                "password_confirm": ["Kiritilgan parollar bir-biriga mos kelmadi."]
            })
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm', None)
        password = validated_data.pop('password')
        try:
            user = User.objects.create_user(password=password, **validated_data)
            return user
        except IntegrityError as e:
            err_str = str(e).lower()
            if 'phone' in err_str:
                raise serializers.ValidationError({"phone": "Bu telefon raqami allaqachon ro‘yxatdan o‘tgan."})
            elif 'email' in err_str:
                raise serializers.ValidationError({"email": "Bu elektron pochta allaqachon ro‘yxatdan o‘tgan."})
            raise serializers.ValidationError({"non_field_errors": ["Foydalanuvchi ma'lumotlarida xatolik yuz berdi."]})


class UserLoginSerializer(serializers.Serializer):
    login = serializers.CharField(required=True, error_messages={
        'required': "Telefon raqami yoki elektron pochtani kiriting."
    })
    password = serializers.CharField(write_only=True, required=True, error_messages={
        'required': "Parolni kiriting."
    })

    def validate(self, attrs):
        raw_login = attrs.get('login', '').strip()
        password = attrs.get('password', '')

        if not raw_login or not password:
            raise serializers.ValidationError("Login va parol to‘ldirilishi shart.")

        # Try to match via phone or email
        normalized_phone = normalize_phone_number(raw_login)
        user = User.objects.filter(
            Q(phone=normalized_phone) |
            Q(email__iexact=raw_login.lower()) |
            Q(phone=raw_login)
        ).first()

        if not user or not user.check_password(password):
            raise serializers.ValidationError("Telefon/email yoki parol noto‘g‘ri kiritildi.")

        if not user.is_active:
            raise serializers.ValidationError("Ushbu akkaunt faol emas.")

        refresh = RefreshToken.for_user(user)
        return {
            'user': user,
            'access': str(refresh.access_token),
            'refresh': str(refresh)
        }
