from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Message

User = get_user_model()


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.full_name', read_only=True)
    sender_avatar = serializers.SerializerMethodField()
    receiver_name = serializers.CharField(source='receiver.full_name', read_only=True)
    receiver_avatar = serializers.SerializerMethodField()
    is_me = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            'id', 'sender', 'sender_name', 'sender_avatar',
            'receiver', 'receiver_name', 'receiver_avatar',
            'text', 'is_read', 'created_at', 'is_me'
        ]
        read_only_fields = ['id', 'sender', 'created_at']

    def get_sender_avatar(self, obj):
        if obj.sender.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.sender.avatar.url)
            return obj.sender.avatar.url
        return None

    def get_receiver_avatar(self, obj):
        if obj.receiver.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.receiver.avatar.url)
            return obj.receiver.avatar.url
        return None

    def get_is_me(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.sender_id == request.user.id
        return False


class MessageCreateSerializer(serializers.ModelSerializer):
    receiver_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='receiver', write_only=True
    )

    class Meta:
        model = Message
        fields = ['receiver_id', 'text']

    def validate_text(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Xabar bo‘sh bo‘lishi mumkin emas.")
        return value.strip()

    def validate(self, attrs):
        request = self.context['request']
        if attrs['receiver'] == request.user:
            raise serializers.ValidationError("O‘zingizga xabar yubora olmaysiz.")
        return attrs

    def create(self, validated_data):
        request = self.context['request']
        return Message.objects.create(
            sender=request.user,
            receiver=validated_data['receiver'],
            text=validated_data['text']
        )
