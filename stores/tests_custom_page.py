"""Page de boutique personnalisée : réservée aux forfaits qui l'incluent, éteinte publiquement à l'expiration."""
from datetime import time, timedelta
from decimal import Decimal

from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from b2b.models import B2BStoreSubscription, B2BSubscriptionPlan
from payments.models import StoreSubscription, SubscriptionPlan
from payments.subscription_check import SubscriptionChecker
from stores.models import Store, StoreCategory
from users.models import User

CUSTOM = {
    'accent_color': '#1e40af',
    'tagline': 'Le bon goût, livré chez vous',
    'about': 'Épicerie familiale installée à Libreville depuis 2010.',
    'facebook_url': 'https://www.facebook.com/monepicerie',
    'instagram_url': 'instagram.com/monepicerie',
    'tiktok_url': 'https://www.tiktok.com/@monepicerie',
    'website_url': 'https://monepicerie.ga',
}


class CustomPageTests(TestCase):
    def setUp(self):
        cache.clear()
        self.free = SubscriptionPlan.objects.get(plan_type='free')
        self.pro = SubscriptionPlan.objects.get(plan_type='pro')
        self.manager = User.objects.create_user(phone='+24107620101', password='Mapeto88x', user_type='store_manager')
        self.category = StoreCategory.objects.create(name='Épicerie page perso')
        self.store = Store.objects.create(
            is_verified=True, name='Épicerie perso', category=self.category, manager=self.manager,
            phone='+24107620110', address='Libreville', zone='Centre', commission_rate=Decimal('5'),
            opening_time=time(0, 0), closing_time=time(23, 59))
        self.api = APIClient()
        self.api.force_authenticate(self.manager)
        self.public = APIClient()
        self.url = f'/api/v1/stores/{self.store.id}/'
        self.update_url = f'/api/v1/stores/{self.store.id}/update/'

    def subscribe(self, plan, days_left=20):
        return StoreSubscription.objects.create(
            store=self.store, plan=plan, plan_name=plan.name, monthly_fee=plan.price,
            status='active', end_date=timezone.now().date() + timedelta(days=days_left))

    def patch(self, data):
        return self.api.patch(self.update_url, data, format='multipart')

    def test_free_plan_cannot_write_and_gets_a_clear_message(self):
        res = self.patch({'accent_color': '#112233', 'about': 'Bienvenue'})
        self.assertEqual(res.status_code, 400)
        details = res.json()['error']['details']
        self.assertIn('accent_color', details)
        self.assertIn('Page de boutique personnalisée', details['accent_color'][0])
        self.assertIn('Pro', details['accent_color'][0])
        self.store.refresh_from_db()
        self.assertEqual(self.store.accent_color, '')
        self.assertEqual(self.store.about, '')

    def test_free_plan_can_still_save_other_fields_and_resend_empty_values(self):
        res = self.patch({'name': 'Épicerie renommée', 'accent_color': '', 'about': ''})
        self.assertEqual(res.status_code, 200, res.content)
        self.store.refresh_from_db()
        self.assertEqual(self.store.name, 'Épicerie renommée')

    def test_pro_plan_saves_and_normalizes_everything(self):
        self.subscribe(self.pro)
        res = self.patch(CUSTOM)
        self.assertEqual(res.status_code, 200, res.content)
        self.store.refresh_from_db()
        self.assertEqual(self.store.accent_color, '#1E40AF')
        self.assertEqual(self.store.instagram_url, 'https://instagram.com/monepicerie')
        self.assertEqual(self.store.tagline, CUSTOM['tagline'])
        data = res.json()['data']
        self.assertEqual(data['facebook_url'], CUSTOM['facebook_url'])
        self.assertTrue(data['custom_page']['enabled'])

    def test_validation(self):
        self.subscribe(self.pro)
        for field, bad in [
            ('accent_color', 'rouge'), ('accent_color', '#12345'), ('accent_color', 'url(javascript:1)'),
            ('facebook_url', 'https://autre-site.com/page'), ('instagram_url', 'javascript:alert(1)'),
            ('tiktok_url', 'https://facebook.com/x'), ('website_url', 'ftp://monepicerie.ga'),
            ('website_url', 'pas un lien'), ('tagline', 'x' * 121), ('about', 'x' * 2001),
        ]:
            res = self.patch({field: bad})
            self.assertEqual(res.status_code, 400, (field, bad, res.content))
            self.assertIn(field, res.json()['error']['details'])
        self.store.refresh_from_db()
        self.assertEqual(self.store.accent_color, '')

    def test_public_sees_customization_while_plan_is_active_and_not_after_expiry(self):
        sub = self.subscribe(self.pro)
        self.assertEqual(self.patch(CUSTOM).status_code, 200)
        public = self.public.get(self.url).json()['data']
        self.assertEqual(public['accent_color'], '#1E40AF')
        self.assertEqual(public['about'], CUSTOM['about'])
        self.assertEqual(public['tiktok_url'], CUSTOM['tiktok_url'])
        self.assertNotIn('custom_page', public)

        StoreSubscription.objects.filter(pk=sub.pk).update(end_date=timezone.now().date() - timedelta(days=1))
        public = self.public.get(self.url).json()['data']
        for field in CUSTOM:
            self.assertEqual(public[field], '', field)
        # Les valeurs restent en base et le commerçant les revoit, verrouillées.
        self.store.refresh_from_db()
        self.assertEqual(self.store.accent_color, '#1E40AF')
        owner = self.api.get(self.url).json()['data']
        self.assertEqual(owner['accent_color'], '#1E40AF')
        self.assertFalse(owner['custom_page']['enabled'])
        # Le commerçant ne peut plus les modifier.
        self.assertEqual(self.patch({'accent_color': '#000000'}).status_code, 400)

    def test_owner_sees_upgrade_hint_on_free_plan(self):
        info = self.api.get(self.url).json()['data']['custom_page']
        self.assertFalse(info['enabled'])
        self.assertEqual(info['plan_name'], 'Pro')
        self.assertIn('Pro', info['upgrade_hint'])
        self.assertIn('Page de boutique personnalisée', info['upgrade_hint'])

    def test_other_manager_cannot_write(self):
        self.subscribe(self.pro)
        other = User.objects.create_user(phone='+24107620102', password='Mapeto88x', user_type='store_manager')
        client = APIClient()
        client.force_authenticate(other)
        res = client.patch(self.update_url, {'accent_color': '#112233'}, format='multipart')
        self.assertEqual(res.status_code, 403)

    def test_can_customize_store_and_checker_follow_the_plan(self):
        self.assertFalse(self.store.can_customize_store())
        with self.assertRaises(PermissionDenied) as ctx:
            SubscriptionChecker.check_can_customize_store(self.store)
        self.assertIn('fait partie du forfait Pro', str(ctx.exception))
        self.assertNotIn('pas encore proposée', str(ctx.exception))
        self.subscribe(self.pro)
        self.assertTrue(self.store.can_customize_store())
        SubscriptionChecker.check_can_customize_store(self.store)

    def test_b2b_wholesaler_does_not_get_the_tool(self):
        self.store.is_b2b, self.store.is_b2c, self.store.store_type = True, False, 'wholesaler'
        self.store.save()
        plan = B2BSubscriptionPlan.objects.get(plan_type='pro')
        B2BStoreSubscription.objects.create(
            store=self.store, plan=plan, plan_name=plan.name, monthly_fee=plan.price, status='active',
            end_date=timezone.now().date() + timedelta(days=20))
        self.assertFalse(self.store.can_customize_store())
        self.assertEqual(self.patch({'tagline': 'Gros'}).status_code, 400)
