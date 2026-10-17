"""Forfaits : chaque avantage promis sur la carte est réellement appliqué (contrôle du 16 oct. 2026)."""
import io
from datetime import time, timedelta
from decimal import Decimal

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from b2b.models import B2BStoreSubscription, B2BSubscriptionPlan
from core.scheduled import expire_subscriptions
from notifications.models import Notification
from orders.models import Order, OrderItem
from orders.stock import reserve_stock
from payments.models import PaymentIntent, StoreSubscription, SubscriptionPlan
from payments.utils import carried_days
from payments.views import _activate_subscription_from_intent
from products.models import Product, ProductCategory
from stores.models import Store, StoreCategory
from users.models import User

CSV_HEADER = 'Nom;Prix;Stock;Poids (kg);Longueur (m);Catégorie;Prix avant promo\n'


def csv_file(body, name='produits.csv'):
    return SimpleUploadedFile(name, ('﻿' + CSV_HEADER + body).encode('utf-8'), content_type='text/csv')


class Base(TestCase):
    def setUp(self):
        cache.clear()
        self.free = SubscriptionPlan.objects.get(plan_type='free')
        self.pro = SubscriptionPlan.objects.get(plan_type='pro')
        self.manager = User.objects.create_user(phone='+24107610101', password='Mapeto88x', user_type='store_manager')
        self.category = StoreCategory.objects.create(name='Mode test outils')
        self.store = Store.objects.create(
            is_verified=True, name='Boutique outils', category=self.category, manager=self.manager,
            phone='+24107610110', address='Libreville', zone='Centre', commission_rate=Decimal('5'),
            opening_time=time(0, 0), closing_time=time(23, 59))
        self.shoes = ProductCategory.objects.create(name='Chaussures', store_category=self.category)
        self.api = APIClient()
        self.api.force_authenticate(self.manager)

    def subscribe(self, plan=None, days_left=20, fee=None):
        plan = plan or self.pro
        return StoreSubscription.objects.create(
            store=self.store, plan=plan, plan_name=plan.name, monthly_fee=fee if fee is not None else plan.price,
            status='active', end_date=timezone.now().date() + timedelta(days=days_left))

    def pay(self, plan):
        intent = PaymentIntent.objects.create(user=self.manager, amount=int(plan.price), currency='XAF',
                                              provider='singpay', metadata={
                                                  'purpose': 'store_subscription', 'plan_id': plan.id,
                                                  'store_id': self.store.id, 'subscription_kind': 'b2c'})
        return _activate_subscription_from_intent(intent)


class RenouvellementTests(Base):
    def test_carried_days(self):
        self.assertEqual(carried_days(10, 10000, 10000, True), 10)
        self.assertEqual(carried_days(10, 10000, 50000, False), 2)
        self.assertEqual(carried_days(10, 50000, 10000, False), 50)
        self.assertEqual(carried_days(0, 10000, 10000, True), 0)
        self.assertEqual(carried_days(10, 0, 10000, False), 0)

    def test_paying_early_keeps_the_remaining_days(self):
        old = self.subscribe(days_left=10)
        new = self.pay(self.pro)
        today = timezone.now().date()
        self.assertEqual(new.end_date, today + timedelta(days=30 + 10))
        old.refresh_from_db()
        self.assertEqual(old.status, 'expired')
        self.store.refresh_from_db()
        self.assertEqual(self.store.subscription_plan, 'pro')

    def test_first_payment_gives_a_normal_month(self):
        new = self.pay(self.pro)
        self.assertEqual(new.end_date, timezone.now().date() + timedelta(days=30))

    def test_wholesaler_renewal_keeps_the_remaining_days(self):
        self.store.set_market_mode('b2b')
        self.store.save()
        b2b_pro = B2BSubscriptionPlan.objects.get(plan_type='pro')
        B2BStoreSubscription.objects.create(store=self.store, plan=b2b_pro, plan_name=b2b_pro.name,
                                            monthly_fee=b2b_pro.price, status='active',
                                            end_date=timezone.now().date() + timedelta(days=7))
        intent = PaymentIntent.objects.create(user=self.manager, amount=int(b2b_pro.price), currency='XAF',
                                              provider='singpay', metadata={
                                                  'purpose': 'store_subscription', 'plan_id': b2b_pro.id,
                                                  'store_id': self.store.id, 'subscription_kind': 'b2b'})
        sub = _activate_subscription_from_intent(intent)
        self.assertEqual(sub.end_date, timezone.now().date() + timedelta(days=37))


class BadgeTests(Base):
    def test_badge_disappears_when_the_plan_ends(self):
        sub = self.subscribe(days_left=5)
        self.store.subscription_plan = 'pro'
        self.store.save()
        StoreSubscription.objects.filter(pk=sub.pk).update(end_date=timezone.now().date() - timedelta(days=1))
        expire_subscriptions()
        self.store.refresh_from_db()
        self.assertEqual(self.store.subscription_plan, 'starter')

    def test_badge_follows_an_admin_given_plan(self):
        self.subscribe(days_left=5)
        expire_subscriptions()
        self.store.refresh_from_db()
        self.assertEqual(self.store.subscription_plan, 'pro')


    def test_pro_given_again_after_expiry_beats_the_automatic_free_row(self):
        sub = self.subscribe(days_left=5)
        StoreSubscription.objects.filter(pk=sub.pk).update(end_date=timezone.now().date() - timedelta(days=1))
        expire_subscriptions()
        self.assertTrue(StoreSubscription.objects.filter(store=self.store, status='active',
                                                         plan__plan_type='free').exists())
        self.subscribe(days_left=30)  # l'admin redonne Pro
        self.assertEqual(self.store.get_current_plan(), self.pro)
        self.assertEqual(self.store.refresh_plan_badge(), 'pro')
        tools = self.api.get('/api/v1/dashboard/store/').json()['data']['subscription']
        self.assertEqual(tools['plan_type'], 'pro')
        self.assertTrue(tools['tools']['promotions'])


class CarteTests(Base):
    def test_pro_card_lists_only_real_tools(self):
        self.pro.features_json = ['Sponsoring', 'Livraison express disponible', 'Import Excel/CSV', 'Accès API',
                                  'Support standard']
        self.pro.has_custom_page = True
        self.pro.has_priority_support = True
        self.pro.can_sponsor_products = True
        self.pro.save()
        text = ' | '.join(self.pro.get_features_list()).lower()
        for real in ('statistiques avancées', 'import de produits', 'alertes de stock', 'promotions', 'export excel'):
            self.assertIn(real, text)
        for fake in ('sponsor', 'express', 'api', 'page personnalisée', 'support prioritaire'):
            self.assertNotIn(fake, text)
        self.assertIn('support standard', text)

    def test_free_card_keeps_basic_stats(self):
        text = ' | '.join(self.free.get_features_list()).lower()
        self.assertIn('statistiques de base', text)
        self.assertNotIn('import', text)

    def test_closed_business_card_promises_nothing_unbuilt(self):
        business = SubscriptionPlan.objects.get(plan_type='business')
        self.assertFalse(business.is_available)
        text = ' | '.join(business.get_features_list()).lower()
        for fake in ('multi-boutiques', 'api', 'synchronisation', 'support prioritaire', 'tarifs négociés'):
            self.assertNotIn(fake, text)

    def test_pro_card_mentions_the_badge_and_the_pdf_export(self):
        text = ' | '.join(self.pro.get_features_list()).lower()
        self.assertIn('badge « pro »', text)
        self.assertIn('export pdf', text)
        self.assertNotIn('badge', ' | '.join(self.free.get_features_list()).lower())

    def test_wholesaler_history_line_only_when_longer_than_free(self):
        free = B2BSubscriptionPlan.objects.get(plan_type='free')
        pro = B2BSubscriptionPlan.objects.get(plan_type='pro')
        free.finance_history_limit_days = None
        free.save()
        self.assertNotIn('historique', ' | '.join(f['title'] for f in pro.get_all_features()).lower())
        free.finance_history_limit_days = 30
        free.save()
        self.assertIn('historique financier illimité',
                      ' | '.join(f['title'] for f in pro.get_all_features()).lower())

    def test_wholesalers_get_stats_and_exports_but_not_promotions(self):
        from payments.plan_features import has, required_message
        pro = B2BSubscriptionPlan.objects.get(plan_type='pro')
        pro.can_create_promotions = True
        pro.save()
        for tool in ('advanced_stats', 'exports', 'product_import', 'stock_alerts'):
            self.assertTrue(has(pro, tool), tool)
        self.assertFalse(has(pro, 'promotions'))
        self.assertIn('grossistes', required_message('promotions', pro))

    def test_wholesaler_card_drops_lines_without_code(self):
        plan = B2BSubscriptionPlan.objects.get(plan_type='pro')
        plan.can_offer_bulk_discounts = True
        plan.has_api_access = True
        plan.can_create_promotions = True
        plan.has_priority_support = True
        plan.custom_features = [{'title': 'Account Manager dédié'}, {'title': 'Livraison le samedi'}]
        plan.save()
        titles = ' | '.join(f['title'] for f in plan.get_all_features()).lower()
        # Un grossiste ne peut pas commander chez un autre grossiste : aucune carte ne promet l'approvisionnement.
        for fake in ('remises', 'api', 'approvisionnement', 'promotions', 'support prioritaire', 'account manager'):
            self.assertNotIn(fake, titles)
        self.assertIn('livraison le samedi', titles)
        self.assertIn('import de produits', titles)


class StatistiquesTests(Base):
    def order(self, client, total, product, qty=1, days_ago=0, status='delivered', confirmed=True):
        order = Order.objects.create(client=client, store=self.store, status=status, items_total=Decimal(total),
                                     total_amount=Decimal(total), delivery_address='Centre', delivery_phone='+24107000000',
                                     delivery_zone='Centre')
        OrderItem.objects.create(order=order, product=product, quantity=qty, unit_price=Decimal(total) / qty)
        moment = timezone.now() - timedelta(days=days_ago)
        Order.objects.filter(pk=order.pk).update(created_at=moment, confirmed_at=moment if confirmed else None)
        return order

    def test_free_plan_sees_the_summary_and_the_way_to_unlock(self):
        data = self.api.get('/api/v1/store/stats/').json()['data']
        self.assertTrue(data['locked'])
        self.assertIn('forfait Pro', data['message'])
        self.assertIn('summary', data)
        self.assertNotIn('top_products', data)

    def test_pro_plan_gets_the_full_statistics(self):
        self.subscribe()
        product = Product.objects.create(store=self.store, name='Baskets', price=10000, stock=10, category=self.shoes)
        idle = Product.objects.create(store=self.store, name='Sandales', price=5000, stock=8)
        client = User.objects.create_user(phone='+24107610199', password='Mapeto88x', user_type='client')
        self.order(client, 20000, product, qty=2, days_ago=1)
        self.order(client, 10000, product, days_ago=3)
        self.order(client, 9000, product, days_ago=40)  # période précédente
        self.order(client, 7000, product, days_ago=2, status='cancelled')
        self.order(client, 5000, product, days_ago=2, status='cancelled', confirmed=False)  # panier jamais payé
        data = self.api.get('/api/v1/store/stats/?days=30').json()['data']
        self.assertFalse(data['locked'])
        self.assertEqual(data['summary']['revenue'], 30000)
        self.assertEqual(data['summary']['orders'], 2)
        self.assertEqual(data['summary']['average_basket'], 15000)
        self.assertEqual(data['summary']['previous_revenue'], 9000)
        self.assertEqual(len(data['daily']), 30)
        self.assertEqual(sum(day['revenue'] for day in data['daily']), data['summary']['revenue'])
        self.assertEqual(data['top_products'][0]['name'], 'Baskets')
        self.assertEqual(data['top_products'][0]['quantity'], 3)
        self.assertEqual(data['categories'][0]['name'], 'Chaussures')
        self.assertEqual(data['customers'], {'unique': 1, 'returning': 1, 'new': 0})
        self.assertEqual([p['product_id'] for p in data['slow_products']], [idle.id])
        self.assertEqual(data['cancellation_rate'], 33)


class ImportTests(Base):
    def post(self, body, confirm=False, name='produits.csv'):
        return self.api.post('/api/v1/store/products/import/',
                             {'file': csv_file(body, name), 'confirm': '1' if confirm else '0'}, format='multipart')

    def test_free_plan_is_told_how_to_unlock(self):
        res = self.post('Sac;5000;3;1;0,3;;\n')
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.json()['error']['code'], 'plan_required')
        self.assertEqual(Product.objects.count(), 0)

    def test_preview_then_create(self):
        self.subscribe()
        Product.objects.create(store=self.store, name='Sac en cuir', price=9000, stock=1)
        body = ('Baskets;12 000;5;0,8;0,35;chaussures;15000\n'
                'Sac en cuir;9000;1;1;0,4;;\n'
                'Sans prix;;2;1;0,3;;\n'
                'Chapeau;3000;2;0,2;0,3;Inconnue;\n')
        preview = self.post(body).json()['data']
        self.assertEqual(preview['counts'], {'ok': 2, 'created': 0, 'skipped': 1, 'error': 1})
        self.assertEqual(Product.objects.count(), 1)
        done = self.post(body, confirm=True).json()['data']
        self.assertEqual(done['counts']['created'], 2)
        shoes = Product.objects.get(name='Baskets')
        self.assertEqual(shoes.price, Decimal('12000'))
        self.assertEqual(shoes.compare_price, Decimal('15000'))
        self.assertEqual(shoes.category, self.shoes)
        hat = Product.objects.get(name='Chapeau')
        self.assertIsNone(hat.category)
        self.assertIn('inconnue', ' '.join(done['rows'][3]['notes']))

    def test_product_limit_is_respected(self):
        self.pro.max_products = 1
        self.pro.save()
        self.subscribe()
        res = self.post('A;1000;1;1;0,3;;\nB;1000;1;1;0,3;;\n', confirm=True).json()['data']
        self.assertEqual(res['counts']['created'], 1)
        self.assertIn('limite', res['rows'][1]['message'])

    def test_missing_required_column(self):
        self.subscribe()
        upload = SimpleUploadedFile('p.csv', b'Nom;Prix\nSac;5000\n', content_type='text/csv')
        res = self.api.post('/api/v1/store/products/import/', {'file': upload}, format='multipart')
        self.assertEqual(res.status_code, 400)
        self.assertIn('Poids', res.json()['error']['message'])

    def test_excel_file(self):
        from openpyxl import Workbook
        self.subscribe()
        book = Workbook()
        sheet = book.active
        sheet.append(['Nom', 'Prix', 'Stock', 'Poids (kg)', 'Longueur (m)'])
        sheet.append(['Montre', 25000, 3, 0.2, 0.1])
        buffer = io.BytesIO()
        book.save(buffer)
        upload = SimpleUploadedFile('p.xlsx', buffer.getvalue())
        res = self.api.post('/api/v1/store/products/import/', {'file': upload, 'confirm': '1'}, format='multipart')
        self.assertEqual(res.json()['data']['counts']['created'], 1, res.content)
        self.assertEqual(Product.objects.get(name='Montre').stock, 3)

    def test_prices_are_read_as_fcfa_and_zero_is_refused(self):
        self.subscribe()
        res = self.post('Riz;4.500;3;5;0,4;;\nErreur;0;1;1;0,3;;\nPromo;5000;1;1;0,3;;4000\n').json()['data']
        self.assertEqual(res['rows'][0]['status'], 'ok')
        self.assertEqual(res['rows'][0]['price'], 4500)
        self.assertEqual(res['rows'][1]['status'], 'error')
        self.assertIn('plus grand que 0', res['rows'][1]['message'])
        self.assertEqual(res['rows'][2]['status'], 'error')
        self.assertIn('prix avant promo', res['rows'][2]['message'].lower())

    def test_unreadable_accents_are_explained_not_a_crash(self):
        self.subscribe()
        body = (CSV_HEADER + 'Crème de karité;3000;2;0,2;0,1;;\n').encode('mac_roman')
        upload = SimpleUploadedFile('mac.csv', body, content_type='text/csv')
        res = self.api.post('/api/v1/store/products/import/', {'file': upload}, format='multipart')
        self.assertEqual(res.status_code, 400)
        self.assertIn('CSV UTF-8', res.json()['error']['message'])

    def test_template_download(self):
        res = self.api.get('/api/v1/store/products/import/template/')
        self.assertEqual(res.status_code, 200)
        self.assertIn('Poids (kg)', res.content.decode('utf-8'))


class PromotionTests(Base):
    payload = {'name': 'Robe', 'price': '8000', 'compare_price': '10000', 'stock': 2, 'weight_kg': '0.5',
               'length_m': '0.6'}

    def create(self):
        return self.api.post(f'/api/v1/stores/{self.store.id}/products/create/', self.payload, format='json')

    def test_free_plan_cannot_add_a_promotion(self):
        res = self.create()
        self.assertEqual(res.status_code, 400, res.content)
        self.assertIn('forfait Pro', str(res.json()))

    def test_pro_plan_can(self):
        self.subscribe()
        self.assertEqual(self.create().status_code, 201)

    def test_existing_promotion_is_kept_on_free(self):
        product = Product.objects.create(store=self.store, name='Robe', price=8000, compare_price=10000, stock=1)
        res = self.api.patch(f'/api/v1/products/{product.id}/update/', {'stock': 4, 'compare_price': '10000'},
                             format='json')
        self.assertEqual(res.status_code, 200, res.content)
        product.refresh_from_db()
        self.assertEqual(product.stock, 4)
        self.assertEqual(product.compare_price, Decimal('10000'))
        res = self.api.patch(f'/api/v1/products/{product.id}/update/', {'compare_price': '12000'}, format='json')
        self.assertEqual(res.status_code, 400, res.content)


class StockAlertTests(Base):
    def sell(self, product, qty):
        with self.captureOnCommitCallbacks(execute=True):
            with transaction.atomic():
                reserve_stock([(product, qty)])

    def alerts(self):
        return list(Notification.objects.filter(user=self.manager, metadata__kind='stock_alert')
                    .values_list('title', flat=True))

    def test_pro_store_is_warned_once_then_at_the_last_unit(self):
        self.subscribe()
        product = Product.objects.create(store=self.store, name='Baskets', price=10000, stock=5)
        self.sell(product, 1)   # 4 : au-dessus du seuil (3)
        self.assertEqual(self.alerts(), [])
        self.sell(product, 2)   # 2 : passage sous le seuil
        self.sell(product, 1)   # 1 : déjà prévenu
        self.assertEqual(self.alerts(), ['Stock faible : Baskets'])
        self.sell(product, 1)   # 0 : rupture
        self.assertEqual(sorted(self.alerts()), ['Rupture de stock : Baskets', 'Stock faible : Baskets'])

    def test_free_store_gets_no_alert(self):
        product = Product.objects.create(store=self.store, name='Baskets', price=10000, stock=2)
        self.sell(product, 2)
        self.assertEqual(self.alerts(), [])


class GrossisteVisibiliteTests(TestCase):
    def test_expired_wholesaler_loses_its_priority(self):
        from b2b.models import B2BProfile
        from b2b.services.supply import get_available_wholesalers
        plan = B2BSubscriptionPlan.objects.get(plan_type='pro')
        plan.catalog_priority = 9
        plan.save()
        category = StoreCategory.objects.create(name='Gros test')
        stores = []
        for i, end in enumerate((-2, 10)):
            manager = User.objects.create_user(phone=f'+2410762010{i}', password='Mapeto88x', user_type='store_manager')
            store = Store.objects.create(is_verified=True, name=f'Grossiste {i}', category=category, manager=manager,
                                         phone=f'+2410762011{i}', address='Libreville', zone='Centre')
            store.set_market_mode('b2b')
            store.save()
            B2BProfile.objects.update_or_create(store=store, defaults={'is_active': True})
            B2BStoreSubscription.objects.create(store=store, plan=plan, plan_name=plan.name, monthly_fee=plan.price,
                                                status='active', end_date=timezone.now().date() + timedelta(days=end))
            stores.append(store)
        result = {s.id: s.catalog_priority_value for s in get_available_wholesalers()}
        self.assertEqual(result[stores[0].id], 0)
        self.assertEqual(result[stores[1].id], 9)


class ExportsTests(Base):
    def test_free_plan_gets_a_clear_refusal_not_a_crash(self):
        for kind in ('csv', 'pdf'):
            res = self.api.get(f'/api/v1/store/finance/sales/export/{kind}/')
            self.assertEqual(res.status_code, 403, kind)
            body = res.content.decode('utf-8')
            self.assertIn('forfait Pro', body)
            self.assertNotIn('Traceback', body)

    def test_pro_plan_exports_csv_and_pdf(self):
        self.subscribe()
        csv_res = self.api.get('/api/v1/store/finance/sales/export/csv/')
        self.assertEqual(csv_res.status_code, 200)
        pdf_res = self.api.get('/api/v1/store/finance/sales/export/pdf/')
        self.assertEqual(pdf_res.status_code, 200, pdf_res.content[:300])
        self.assertEqual(pdf_res['Content-Type'], 'application/pdf')

    def test_card_payment_is_refused_up_front(self):
        res = self.api.post('/api/v1/payments/subscriptions/intent/',
                            {'plan_id': self.pro.id, 'provider': 'cinetpay'}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('Airtel Money', res.json()['detail'])


class ConseilsHonnetesTests(Base):
    def test_pro_at_its_limit_is_not_sent_to_a_closed_plan(self):
        from payments.subscription_check import SubscriptionChecker
        text = SubscriptionChecker.product_limit_message(self.pro, 200)
        self.assertIn("Aucun forfait en vente ne permet encore d'ajouter davantage de produits", text)
        self.assertNotIn('Business', text)
        free_text = SubscriptionChecker.product_limit_message(self.free, 20)
        self.assertIn('Passez au forfait Pro', free_text)

    def test_wholesaler_assistant_promo_refusal_is_not_an_upsell(self):
        from payments.plan_features import required_message
        b2b_pro = B2BSubscriptionPlan.objects.get(plan_type='pro')
        self.assertNotIn('Passez', required_message('promotions', b2b_pro))

    def test_wholesaler_is_told_procurement_is_for_retailers_whatever_its_plan(self):
        self.store.set_market_mode('b2b')
        self.store.save()
        res = self.api.get('/api/v1/b2b/wholesalers/')
        self.assertEqual(res.status_code, 403)
        self.assertIn('réservé aux commerces de détail', res.json()['error']['message'])
        b2b_pro = B2BSubscriptionPlan.objects.get(plan_type='pro')
        B2BStoreSubscription.objects.create(store=self.store, plan=b2b_pro, plan_name=b2b_pro.name,
                                            monthly_fee=b2b_pro.price, status='active',
                                            end_date=timezone.now().date() + timedelta(days=10))
        res = self.api.get('/api/v1/b2b/wholesalers/')
        self.assertEqual(res.status_code, 403)
        self.assertIn('réservé aux commerces de détail', res.json()['error']['message'])

    def test_assistant_promo_refusal_uses_the_plan_rule(self):
        from api.v1.ai import assistant
        self.assertNotIn("les promotions font partie du forfait Pro.\"", open(assistant.__file__, encoding='utf-8').read())


class AttributionAdminTests(Base):
    def setUp(self):
        super().setUp()
        self.admin = User.objects.create_user(phone='+24107610199', password='Mapeto88x', user_type='admin', is_staff=True)
        self.admin_api = APIClient()
        self.admin_api.force_authenticate(self.admin)

    def test_admin_gives_free_to_a_pro_shop_and_it_takes_effect(self):
        self.subscribe(days_left=20)
        self.assertEqual(self.store.get_current_plan().plan_type, 'pro')
        res = self.admin_api.post('/api/v1/admin/store-subscriptions/create/',
                                  {'store_id': self.store.id, 'plan_id': self.free.id}, format='json')
        self.assertEqual(res.status_code, 201, res.content)
        self.store.refresh_from_db()
        self.assertEqual(self.store.get_current_plan().plan_type, 'free')
        self.assertEqual(StoreSubscription.objects.filter(store=self.store, status='active').count(), 1)

    def test_admin_gives_pro_again_and_it_takes_effect(self):
        self.subscribe(plan=self.free, days_left=36500)
        res = self.admin_api.post('/api/v1/admin/store-subscriptions/create/',
                                  {'store_id': self.store.id, 'plan_id': self.pro.id}, format='json')
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(self.store.get_current_plan().plan_type, 'pro')

    def test_row_without_plan_counts_as_free(self):
        self.subscribe(days_left=5)
        StoreSubscription.objects.create(store=self.store, plan=None, plan_name='Free', monthly_fee=0,
                                         status='active', end_date=timezone.now().date() + timedelta(days=36500))
        self.assertEqual(self.store.get_active_subscription().plan_id, self.pro.id)


class TroisiemeRelectureTests(Base):
    """Défauts trouvés à la troisième relecture (17 oct. 2026)."""

    def setUp(self):
        super().setUp()
        self.admin = User.objects.create_user(phone='+24107610198', password='Mapeto88x', user_type='admin', is_staff=True)
        self.admin_api = APIClient()
        self.admin_api.force_authenticate(self.admin)

    def dashboard_sub(self):
        return self.api.get('/api/v1/dashboard/store/').json()['data']['subscription']

    def test_admin_status_other_than_active_keeps_the_paid_plan(self):
        paid = self.subscribe(days_left=20)
        res = self.admin_api.post('/api/v1/admin/store-subscriptions/create/',
                                  {'store_id': self.store.id, 'plan_id': self.pro.id, 'status': 'pending_payment'},
                                  format='json')
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.json()['data']['status'], 'pending_payment')
        paid.refresh_from_db()
        self.assertEqual(paid.status, 'active')
        self.assertEqual(self.store.get_active_subscription().pk, paid.pk)

    def test_free_given_by_admin_never_says_it_expires(self):
        self.subscribe(days_left=20)
        res = self.admin_api.post('/api/v1/admin/store-subscriptions/create/',
                                  {'store_id': self.store.id, 'plan_id': self.free.id,
                                   'end_date': (timezone.now().date() + timedelta(days=3)).isoformat()}, format='json')
        self.assertEqual(res.status_code, 201, res.content)
        sub = self.dashboard_sub()
        self.assertEqual(sub['plan_type'], 'free')
        self.assertIsNone(sub['days_until_expiry'])
        self.assertIsNone(sub['end_date'])
        current = self.api.get('/api/v1/payments/subscription-plans/').json()['current_plan']
        self.assertEqual(current['plan_type'], 'free')
        self.assertIsNone(current['end_date'])

    def test_automatic_free_row_shows_no_end_date(self):
        StoreSubscription.objects.create(store=self.store, plan=self.free, plan_name=self.free.name, monthly_fee=0,
                                         status='active', end_date=timezone.now().date() + timedelta(days=36500))
        self.assertIsNone(self.api.get('/api/v1/payments/subscription-plans/').json()['current_plan']['end_date'])
        self.assertIsNone(self.dashboard_sub()['end_date'])

    def test_wholesaler_dashboard_shows_the_enforced_wholesale_plan(self):
        self.subscribe(days_left=20)  # reste d'un abonnement commerce
        self.store.set_market_mode('b2b')
        self.store.save()
        sub = self.dashboard_sub()
        self.assertEqual(sub['plan_type'], 'free')
        self.assertEqual(sub['plan_name'], self.store.get_current_plan().name)
        self.assertFalse(sub['tools']['exports'])

    def test_admin_gives_a_wholesaler_its_first_plan_without_error(self):
        self.store.set_market_mode('b2b')
        self.store.save()
        b2b_pro = B2BSubscriptionPlan.objects.get(plan_type='pro')
        res = self.admin_api.post('/api/v1/admin/b2b-store-subscriptions/create/',
                                  {'store_id': self.store.id, 'plan_id': b2b_pro.id}, format='json')
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(self.dashboard_sub()['plan_type'], 'pro')

    def test_no_message_sends_a_shop_to_a_plan_that_is_not_for_sale(self):
        from payments.plan_features import required_message
        b2b_free = B2BSubscriptionPlan.objects.get(plan_type='free')
        B2BSubscriptionPlan.objects.filter(plan_type='pro').update(is_available=False)
        text = required_message('exports', b2b_free)
        self.assertIn('aucun forfait en vente', text)
        self.assertNotIn('Passez', text)
        # Un Pro sans export : on ne lui dit pas de passer à Pro.
        SubscriptionPlan.objects.filter(pk=self.pro.pk).update(can_export_excel=False, can_export_pdf=False)
        self.subscribe()
        res = self.api.get('/api/v1/store/finance/sales/export/csv/')
        self.assertEqual(res.status_code, 403)
        self.assertIn('aucun forfait en vente', res.content.decode('utf-8'))

    def test_pro_at_its_limit_is_offered_business_once_it_opens_with_more_room(self):
        from payments.subscription_check import SubscriptionChecker
        SubscriptionPlan.objects.filter(plan_type='business').update(is_available=True, max_products=None)
        self.assertIn('Passez au forfait', SubscriptionChecker.product_limit_message(self.pro, self.pro.max_products))
        SubscriptionPlan.objects.filter(plan_type='business').update(max_products=self.pro.max_products)
        self.assertIn('Aucun forfait en vente',
                      SubscriptionChecker.product_limit_message(self.pro, self.pro.max_products))

    def test_order_limit_refusal_is_written_for_the_customer(self):
        from django.core.exceptions import PermissionDenied
        from payments.subscription_check import SubscriptionChecker
        SubscriptionPlan.objects.filter(pk=self.free.pk).update(max_orders_per_month=1)
        client = User.objects.create_user(phone='+24107610197', password='Mapeto88x', user_type='client')
        Order.objects.create(client=client, store=self.store, status='pending', items_total=Decimal('1000'),
                             total_amount=Decimal('1000'), delivery_address='Centre', delivery_phone='+24107000000',
                             delivery_zone='Centre')
        with self.assertRaises(PermissionDenied) as ctx:
            SubscriptionChecker.check_can_create_order(self.store)
        text = str(ctx.exception)
        self.assertIn(self.store.name, text)
        self.assertNotIn('Passez', text)
        self.assertNotIn('votre forfait', text)

    def test_pro_card_shows_a_longer_sales_history(self):
        SubscriptionPlan.objects.filter(pk=self.free.pk).update(history_limit_days=30)
        SubscriptionPlan.objects.filter(pk=self.pro.pk).update(history_limit_days=None)
        self.pro.refresh_from_db()
        self.assertIn('Historique des ventes illimité', self.pro.get_features_list())


class ImportRelectureTests(Base):
    post = ImportTests.post

    def test_example_rows_and_deleted_products_and_food_limit(self):
        self.subscribe()
        Product.objects.create(store=self.store, name='Sandales', price=5000, stock=1, is_available=False)
        body = ('Exemple : Riz parfumé 5 kg;4500;20;5;0,4;;\n'
                'Sandales;6000;2;0,5;0,3;chaussures;\n')
        data = self.post(body).json()['data']
        by_name = {r['name']: r for r in data['rows']}
        self.assertEqual(by_name['Exemple : Riz parfumé 5 kg']['status'], 'skipped')
        self.assertEqual(by_name['Sandales']['status'], 'ok')

    def test_preview_counts_food_rows_against_the_food_limit(self):
        self.category.name = 'Alimentation test'
        self.category.save()
        SubscriptionPlan.objects.filter(pk=self.pro.pk).update(max_products_food=1)
        self.subscribe()
        body = ('Riz;4500;20;5;0,4;chaussures;\n'
                'Huile;2500;20;1;0,3;chaussures;\n')
        data = self.post(body).json()['data']
        self.assertEqual(data['counts']['ok'], 1)
        self.assertEqual(data['counts']['error'], 1)
        done = self.post(body, confirm=True).json()['data']
        self.assertEqual(done['counts']['created'], 1)
