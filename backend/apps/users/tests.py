from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()


class UserAuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('auth-register')
        self.login_url = reverse('auth-login')
        self.me_url = reverse('auth-me')

    def test_register_with_phone_success(self):
        data = {
            'first_name': 'Ali',
            'last_name': 'Valiyev',
            'phone': '+998901234567',
            'password': 'password123',
            'role': 'client'
        }
        res = self.client.post(self.register_url, data)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['user']['first_name'], 'Ali')
        self.assertIn('tokens', res.data)
        self.assertTrue(User.objects.filter(phone='+998901234567').exists())

    def test_register_with_email_success(self):
        data = {
            'first_name': 'Sardor',
            'last_name': 'Azimov',
            'email': 'sardor@example.com',
            'password': 'password123',
            'role': 'master'
        }
        res = self.client.post(self.register_url, data)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['user']['role'], 'master')
        self.assertTrue(User.objects.filter(email='sardor@example.com').exists())

    def test_prevent_duplicate_phone_registration(self):
        User.objects.create_user(
            first_name='Ali', phone='+998901234567', password='password123'
        )
        data = {
            'first_name': 'Boshqa',
            'phone': '+998 90 123-45-67',  # Formatted differently, should be normalized and caught
            'password': 'password123'
        }
        res = self.client.post(self.register_url, data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('phone', res.data)
        self.assertEqual(res.data['phone'][0], "Bu telefon raqami allaqachon ro‘yxatdan o‘tgan.")

    def test_prevent_duplicate_email_registration_case_insensitive(self):
        User.objects.create_user(
            first_name='Zafar', email='zafar@test.uz', password='password123'
        )
        data = {
            'first_name': 'Zafar 2',
            'email': 'ZAFAR@TEST.UZ',  # Uppercase
            'password': 'password123'
        }
        res = self.client.post(self.register_url, data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', res.data)
        self.assertEqual(res.data['email'][0], "Bu elektron pochta allaqachon ro‘yxatdan o‘tgan.")

    def test_login_with_phone(self):
        user = User.objects.create_user(
            first_name='Bobur', phone='+998912345678', password='secretpassword'
        )
        data = {
            'login': '+998 91 234 56 78',
            'password': 'secretpassword'
        }
        res = self.client.post(self.login_url, data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('tokens', res.data)
        self.assertEqual(res.data['user']['id'], user.id)

    def test_login_with_email(self):
        user = User.objects.create_user(
            first_name='Nodir', email='nodir@test.uz', password='secretpassword'
        )
        data = {
            'login': 'NODIR@TEST.UZ',
            'password': 'secretpassword'
        }
        res = self.client.post(self.login_url, data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('tokens', res.data)
        self.assertEqual(res.data['user']['id'], user.id)

    def test_me_endpoint_requires_auth(self):
        res = self.client.get(self.me_url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
