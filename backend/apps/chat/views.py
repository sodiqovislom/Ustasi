from rest_framework import views, status, permissions
from rest_framework.response import Response
from django.db.models import Q, Max
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from .models import Message
from .serializers import MessageSerializer, MessageCreateSerializer
from apps.users.serializers import UserSerializer

User = get_user_model()


class MessageListCreateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        partner_id = request.query_params.get('user_id')
        if not partner_id:
            return Response(
                {"detail": "user_id parametri ko‘rsatilishi shart."},
                status=status.HTTP_400_BAD_REQUEST
            )
        partner = get_object_or_404(User, id=partner_id)

        # Mark unread messages sent to current user by partner as read
        Message.objects.filter(
            sender=partner,
            receiver=request.user,
            is_read=False
        ).update(is_read=True)

        messages = Message.objects.filter(
            (Q(sender=request.user) & Q(receiver=partner)) |
            (Q(sender=partner) & Q(receiver=request.user))
        ).select_related('sender', 'receiver').order_by('created_at')

        serializer = MessageSerializer(messages, many=True, context={'request': request})
        return Response({
            'partner': {
                'id': partner.id,
                'full_name': partner.full_name,
                'avatar_url': request.build_absolute_uri(partner.avatar.url) if partner.avatar else None,
                'role': partner.role,
                'phone': partner.phone,
                'master_id': partner.master_profile.id if hasattr(partner, 'master_profile') else None,
                'master_category': partner.master_profile.category.name if hasattr(partner, 'master_profile') else None,
            },
            'messages': serializer.data
        })

    def post(self, request):
        serializer = MessageCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        message = serializer.save()
        return Response(
            MessageSerializer(message, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )


class ConversationListView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        # Get all distinct partners
        sent_to = Message.objects.filter(sender=user).values_list('receiver_id', flat=True)
        received_from = Message.objects.filter(receiver=user).values_list('sender_id', flat=True)
        partner_ids = set(sent_to) | set(received_from)

        conversations = []
        for pid in partner_ids:
            partner = User.objects.filter(id=pid).first()
            if not partner:
                continue

            last_msg = Message.objects.filter(
                (Q(sender=user) & Q(receiver_id=pid)) |
                (Q(sender_id=pid) & Q(receiver=user))
            ).order_by('-created_at').first()

            unread_cnt = Message.objects.filter(
                sender_id=pid,
                receiver=user,
                is_read=False
            ).count()

            conversations.append({
                'partner': {
                    'id': partner.id,
                    'full_name': partner.full_name,
                    'avatar_url': request.build_absolute_uri(partner.avatar.url) if partner.avatar else None,
                    'role': partner.role,
                    'master_id': partner.master_profile.id if hasattr(partner, 'master_profile') else None,
                    'master_category': partner.master_profile.category.name if hasattr(partner, 'master_profile') else None,
                },
                'last_message': {
                    'text': last_msg.text if last_msg else '',
                    'created_at': last_msg.created_at if last_msg else None,
                    'is_me': (last_msg.sender_id == user.id) if last_msg else False,
                } if last_msg else None,
                'unread_count': unread_cnt
            })

        # Sort conversations by last message time
        conversations.sort(
            key=lambda c: c['last_message']['created_at'] if c['last_message'] and c['last_message']['created_at'] else '',
            reverse=True
        )

        return Response(conversations)
