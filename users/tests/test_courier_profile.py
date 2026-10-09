from django.test import TestCase
from rest_framework.test import APIClient

from users.models import LivreurProfile, User


class CourierProfileTests(TestCase):
    def test_courier_created_by_admin_can_open_dashboard(self):
        # Compte livreur créé sans passer par l'inscription (admin, console) : le profil existe quand même.
        courier = User.objects.create_user(phone='+24107500001', password='password', user_type='delivery_agent')
        self.assertTrue(LivreurProfile.objects.filter(user=courier).exists())

        api = APIClient()
        api.force_authenticate(courier)
        response = api.get('/api/v1/dashboard/delivery/')
        self.assertEqual(response.status_code, 200)

    def test_dashboard_recreates_a_missing_profile(self):
        courier = User.objects.create_user(phone='+24107500002', password='password', user_type='delivery_agent')
        LivreurProfile.objects.filter(user=courier).delete()
        api = APIClient()
        api.force_authenticate(courier)
        self.assertEqual(api.get('/api/v1/dashboard/delivery/').status_code, 200)

    def test_client_gets_no_courier_profile(self):
        client = User.objects.create_user(phone='+24107500003', password='password', user_type='client')
        self.assertFalse(LivreurProfile.objects.filter(user=client).exists())
