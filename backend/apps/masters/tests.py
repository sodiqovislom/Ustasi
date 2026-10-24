from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from apps.masters.models import Category, Master, Service, Rating

User = get_user_model()


class MasterSystemTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Categories
        self.cat_phone = Category.objects.create(
            name="Telefon ustasi", slug="phone-repair", icon="Smartphone", order=1
        )
        self.cat_electric = Category.objects.create(
            name="Elektrik", slug="electrician", icon="Zap", order=2
        )
        self.cat_builder = Category.objects.create(
            name="Quruvchi", slug="builder", icon="Hammer", order=3
        )

        # Users
        self.client_user = User.objects.create_user(
            first_name="Temur", phone="+998901112233", password="password123", role="client"
        )
        self.client_user_2 = User.objects.create_user(
            first_name="Anvar", phone="+998902223344", password="password123", role="client"
        )
        self.master_user = User.objects.create_user(
            first_name="Rustam", last_name="Umarov", phone="+998903334455",
            password="password123", role="master"
        )

        # Master profile
        self.master = Master.objects.create(
            user=self.master_user,
            category=self.cat_phone,
            description="Har qanday telefonlarni tez va sifatli tuzataman",
            experience=5,
            price=60000,
            region="Toshkent shahri",
            district="Yunusobod tumani",
            latitude=41.3500,
            longitude=69.2800,
            working_hours="09:00 - 20:00",
            status="active"
        )

        Service.objects.create(master=self.master, name="Ekran almashtirish", price=120000)
        Service.objects.create(master=self.master, name="Batareya almashtirish", price=70000)

    def test_list_masters(self):
        url = reverse('master-list')
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['count'], 1)
        self.assertEqual(res.data['results'][0]['full_name'], 'Rustam Umarov')
        self.assertEqual(len(res.data['results'][0]['services']), 2)

    def test_filter_by_category(self):
        url = reverse('master-list') + '?category=phone-repair'
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['count'], 1)

        url_empty = reverse('master-list') + '?category=electrician'
        res_empty = self.client.get(url_empty)
        self.assertEqual(res_empty.status_code, status.HTTP_200_OK)
        self.assertEqual(res_empty.data['count'], 0)

    def test_rate_master_success_and_stats_recalculation(self):
        self.client.force_authenticate(user=self.client_user)
        url = reverse('master-rate', kwargs={'pk': self.master.id})
        res = self.client.post(url, {'score': 5, 'comment': 'Ajoyib usta, tez bitirdi!'})
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        self.master.refresh_from_db()
        self.assertEqual(float(self.master.average_rating), 5.0)
        self.assertEqual(self.master.ratings_count, 1)

        # Second client rates 4
        self.client.force_authenticate(user=self.client_user_2)
        res2 = self.client.post(url, {'score': 4, 'comment': 'Yaxshi usta'})
        self.assertEqual(res2.status_code, status.HTTP_201_CREATED)

        self.master.refresh_from_db()
        self.assertEqual(float(self.master.average_rating), 4.5)
        self.assertEqual(self.master.ratings_count, 2)

    def test_prevent_duplicate_rating(self):
        self.client.force_authenticate(user=self.client_user)
        url = reverse('master-rate', kwargs={'pk': self.master.id})
        # First rating
        res = self.client.post(url, {'score': 5})
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        # Duplicate rating attempt
        res_duplicate = self.client.post(url, {'score': 4})
        self.assertEqual(res_duplicate.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("allaqachon", str(res_duplicate.data).lower())

    def test_prevent_master_self_rating(self):
        # Master cannot rate themselves
        self.client.force_authenticate(user=self.master_user)
        url = reverse('master-rate', kwargs={'pk': self.master.id})
        res = self.client.post(url, {'score': 5})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("o‘ziga o‘zi", str(res.data).lower())

    def test_guest_cannot_rate(self):
        url = reverse('master-rate', kwargs={'pk': self.master.id})
        res = self.client.post(url, {'score': 5})
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_search_suggestions_min_chars(self):
        url = reverse('search-suggestions') + '?q=e'
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['suggestions']), 0)  # less than 2 chars

        url_valid = reverse('search-suggestions') + '?q=el'
        res_valid = self.client.get(url_valid)
        self.assertEqual(res_valid.status_code, status.HTTP_200_OK)
        self.assertTrue(len(res_valid.data['suggestions']) > 0)
        # Should include Elektrik category or Ekran almashtirish service
        labels = [s['label'] for s in res_valid.data['suggestions']]
        self.assertTrue(any('Elektrik' in l or 'Ekran' in l for l in labels))

    def test_filter_by_min_rating(self):
        # Give 5 star rating
        Rating.objects.create(user=self.client_user, master=self.master, score=5)
        self.master.refresh_from_db()

        url_match = reverse('master-list') + '?min_rating=4.5'
        res_match = self.client.get(url_match)
        self.assertEqual(res_match.data['count'], 1)

        url_no_match = reverse('master-list') + '?min_rating=5.1'
        res_no_match = self.client.get(url_no_match)
        self.assertEqual(res_no_match.data['count'], 0)

    def test_invalid_score_range(self):
        self.client.force_authenticate(user=self.client_user)
        url = reverse('master-rate', kwargs={'pk': self.master.id})
        # Score 6 (out of range)
        res_high = self.client.post(url, {'score': 6})
        self.assertEqual(res_high.status_code, status.HTTP_400_BAD_REQUEST)

        # Score 0 (out of range)
        res_low = self.client.post(url, {'score': 0})
        self.assertEqual(res_low.status_code, status.HTTP_400_BAD_REQUEST)

    def test_db_unique_constraint_rating_integrity_error(self):
        from django.db import IntegrityError
        Rating.objects.create(user=self.client_user, master=self.master, score=5)
        with self.assertRaises(IntegrityError):
            Rating.objects.create(user=self.client_user, master=self.master, score=4)

    def test_master_address_and_portfolio_workflow(self):
        self.client.force_authenticate(user=self.master_user)

        # 1. Update address
        update_url = reverse('master-my-profile')
        res_update = self.client.patch(update_url, {'address': 'Yunusobod 4-mavze, 12-uy'}, format='json')
        self.assertEqual(res_update.status_code, status.HTTP_200_OK)
        self.assertEqual(res_update.data['address'], 'Yunusobod 4-mavze, 12-uy')

        # 2. Add portfolio work
        portfolio_url = reverse('master-portfolio-list-create')
        res_add = self.client.post(portfolio_url, {
            'title': 'iPhone 13 Pro ekran almashtirildi',
            'description': 'Original ekran qo‘yildi, 6 oy kafolat berildi'
        }, format='json')
        self.assertEqual(res_add.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res_add.data['title'], 'iPhone 13 Pro ekran almashtirildi')
        work_id = res_add.data['id']

        # 3. Master detail should now contain the portfolio work and address
        detail_url = reverse('master-detail', kwargs={'pk': self.master.id})
        res_detail = self.client.get(detail_url)
        self.assertEqual(res_detail.status_code, status.HTTP_200_OK)
        self.assertEqual(res_detail.data['address'], 'Yunusobod 4-mavze, 12-uy')
        self.assertEqual(len(res_detail.data['portfolio']), 1)
        self.assertEqual(res_detail.data['portfolio'][0]['title'], 'iPhone 13 Pro ekran almashtirildi')

        # 4. Delete portfolio work
        delete_url = reverse('master-portfolio-delete', kwargs={'pk': work_id})
        res_del = self.client.delete(delete_url)
        self.assertEqual(res_del.status_code, status.HTTP_204_NO_CONTENT)

        # Confirm deleted
        res_detail_after = self.client.get(detail_url)
        self.assertEqual(len(res_detail_after.data['portfolio']), 0)

    def test_user_avatar_base64_upload(self):
        self.client.force_authenticate(user=self.client_user)
        me_url = reverse('auth-me')
        # 1x1 transparent PNG as base64
        tiny_png = (
            "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        )
        res = self.client.patch(me_url, {'avatar': tiny_png}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(bool(res.data.get('avatar_url')))

