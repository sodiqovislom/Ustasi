from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from apps.chat.models import Message

User = get_user_model()


class ChatSystemTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(
            first_name="Aziz", phone="+998901110001", password="password123", role="client"
        )
        self.user2 = User.objects.create_user(
            first_name="Sanjar", phone="+998901110002", password="password123", role="master"
        )

    def test_send_message_and_list_thread(self):
        self.client.force_authenticate(user=self.user1)
        url = reverse('message-list-create')

        # Send message
        res = self.client.post(url, {
            'receiver_id': self.user2.id,
            'text': "Assalomu alaykum, ertaga kela olasizmi?"
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Message.objects.count(), 1)

        # Get conversation thread with user2
        res_thread = self.client.get(f"{url}?user_id={self.user2.id}")
        self.assertEqual(res_thread.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_thread.data['messages']), 1)
        self.assertEqual(res_thread.data['messages'][0]['text'], "Assalomu alaykum, ertaga kela olasizmi?")

    def test_cannot_message_self(self):
        self.client.force_authenticate(user=self.user1)
        url = reverse('message-list-create')
        res = self.client.post(url, {
            'receiver_id': self.user1.id,
            'text': "O'zimga xabar"
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
