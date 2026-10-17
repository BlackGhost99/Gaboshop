"""Support : une demande garde le niveau du forfait, le contact direct est réservé, l'admin répond et les gens sont prévenus."""
from datetime import time, timedelta
from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from api.models import SystemSettings
from notifications.models import Notification
from payments.models import StoreSubscription, SubscriptionPlan
from stores.models import Store, StoreCategory
from users.models import User

from .models import SupportReply, SupportTicket

TICKETS = '/api/v1/support/tickets/'
CONTACT = '/api/v1/support/contact/'
BODY = {'subject': 'Paiement non reçu', 'message': "Mon paiement Airtel est parti mais la commande n'a pas bougé.",
        'category': 'payment'}


class SupportTests(TestCase):
    def setUp(self):
        cache.clear()
        self.category = StoreCategory.objects.create(name='Support test')
        self.admin = User.objects.create_user(phone='+24107700001', password='Mapeto88x', user_type='admin', is_staff=True)
        self.client_user = User.objects.create_user(phone='+24107700002', password='Mapeto88x', user_type='client')
        self.manager = self.manager_with_store('+24107700010', '+24107700011')
        self.store = self.manager.managed_stores.get()
        SystemSettings.objects.update_or_create(pk=1, defaults={
            'support_email': 'aide@gaboshop.ga', 'support_phone': '+24101000000', 'support_whatsapp': '+24107000000'})
        self.free = SubscriptionPlan.objects.get(plan_type='free')
        self.pro = SubscriptionPlan.objects.get(plan_type='pro')
        self.business = SubscriptionPlan.objects.get(plan_type='business')
        SubscriptionPlan.objects.filter(pk=self.free.pk).update(has_priority_support=False, support_level='standard')
        SubscriptionPlan.objects.filter(pk=self.pro.pk).update(has_priority_support=True, support_level='prioritaire')
        SubscriptionPlan.objects.filter(pk=self.business.pk).update(has_priority_support=True, support_level='dedie')

    def manager_with_store(self, phone, store_phone):
        user = User.objects.create_user(phone=phone, password='Mapeto88x', user_type='store_manager')
        Store.objects.create(
            is_verified=True, name=f'Boutique {phone[-2:]}', category=self.category, manager=user, phone=store_phone,
            address='Libreville', zone='Centre', commission_rate=Decimal('5'),
            opening_time=time(0, 0), closing_time=time(23, 59))
        return user

    def subscribe(self, plan, store=None):
        StoreSubscription.objects.create(
            store=store or self.store, plan=plan, plan_name=plan.name, monthly_fee=plan.price, status='active',
            end_date=timezone.now().date() + timedelta(days=30))

    def api(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    def open_ticket(self, user, **extra):
        return self.api(user).post(TICKETS, {**BODY, **extra}, format='json')

    # --- création ---

    def test_client_opens_a_standard_ticket_and_sees_only_his_own(self):
        res = self.open_ticket(self.client_user)
        self.assertEqual(res.status_code, 201, res.content)
        data = res.json()['data']
        self.assertEqual((data['priority'], data['status'], data['author_role']), ('standard', 'open', 'client'))
        self.open_ticket(self.manager, subject='Autre sujet')
        mine = self.api(self.client_user).get(TICKETS).json()['data']
        self.assertEqual([t['subject'] for t in mine], ['Paiement non reçu'])
        other = self.api(self.manager).get(f"{TICKETS}{data['id']}/")
        self.assertEqual(other.status_code, 404)

    def test_anonymous_is_refused(self):
        self.assertIn(APIClient().post(TICKETS, BODY, format='json').status_code, (401, 403))
        self.assertIn(APIClient().get(CONTACT).status_code, (401, 403))
        self.assertEqual(SupportTicket.objects.count(), 0)

    def test_incomplete_ticket_explains_what_to_fix(self):
        res = self.open_ticket(self.client_user, subject='', message='court')
        self.assertEqual(res.status_code, 400)
        details = res.json()['error']['details']
        self.assertIn('subject', details)
        self.assertIn('message', details)
        self.assertEqual(SupportTicket.objects.count(), 0)

    def test_priority_follows_the_plan_of_the_store(self):
        # Gratuit (rien de souscrit) : standard
        self.assertEqual(self.open_ticket(self.manager).json()['data']['priority'], 'standard')
        self.subscribe(self.pro)
        ticket = self.open_ticket(self.manager).json()['data']
        self.assertEqual((ticket['priority'], ticket['plan_name'], ticket['store']), ('prioritaire', self.pro.name, self.store.id))
        StoreSubscription.objects.all().delete()
        self.subscribe(self.business)
        self.assertEqual(self.open_ticket(self.manager).json()['data']['priority'], 'dedie')

    def test_manager_with_several_stores_gets_the_best_level(self):
        second = Store.objects.create(
            is_verified=True, name='Deuxième', category=self.category, manager=self.manager, phone='+24107700012',
            address='Libreville', zone='Centre', commission_rate=Decimal('5'),
            opening_time=time(0, 0), closing_time=time(23, 59))
        self.subscribe(self.pro, store=second)
        ticket = self.open_ticket(self.manager).json()['data']
        self.assertEqual((ticket['priority'], ticket['store']), ('prioritaire', second.id))

    # --- contact direct ---

    def test_direct_contact_is_hidden_without_priority_support(self):
        data = self.api(self.manager).get(CONTACT).json()['data']
        self.assertFalse(data['direct'])
        self.assertEqual((data['phone'], data['whatsapp']), ('', ''))
        self.assertEqual(data['email'], 'aide@gaboshop.ga')
        self.assertIn('Support prioritaire', data['message'])
        self.assertIn(self.pro.name, data['message'])
        self.assertNotIn('+24107000000', str(data))

    def test_client_only_gets_the_standard_email(self):
        data = self.api(self.client_user).get(CONTACT).json()['data']
        self.assertFalse(data['direct'])
        self.assertEqual((data['phone'], data['whatsapp'], data['email']), ('', '', 'aide@gaboshop.ga'))

    def test_priority_plan_gets_direct_contact(self):
        self.subscribe(self.pro)
        data = self.api(self.manager).get(CONTACT).json()['data']
        self.assertTrue(data['direct'])
        self.assertFalse(data['dedicated'])
        self.assertEqual((data['phone'], data['whatsapp']), ('+24101000000', '+24107000000'))
        self.assertEqual(data['priority_label'], 'Support prioritaire')

    def test_dedicated_plan_is_marked_dedicated_line(self):
        self.subscribe(self.business)
        data = self.api(self.manager).get(CONTACT).json()['data']
        self.assertTrue(data['direct'])
        self.assertTrue(data['dedicated'])
        self.assertEqual(data['priority_label'], 'Ligne dédiée')

    def test_priority_plan_without_published_number_says_so(self):
        SystemSettings.objects.filter(pk=1).update(support_phone='', support_whatsapp='')
        self.subscribe(self.pro)
        data = self.api(self.manager).get(CONTACT).json()['data']
        self.assertTrue(data['direct'])
        self.assertIn("pas encore publié", data['message'])

    # --- admin, réponses, statut ---

    def test_admin_sees_everything_priority_first_then_oldest(self):
        standard_old = self.open_ticket(self.client_user, subject='Ancienne demande').json()['data']['id']
        standard_new = self.open_ticket(self.client_user, subject='Récente demande').json()['data']['id']
        self.subscribe(self.pro)
        prioritaire = self.open_ticket(self.manager, subject='Demande prioritaire').json()['data']['id']
        resolved = self.open_ticket(self.client_user, subject='Déjà réglée').json()['data']['id']
        SupportTicket.objects.filter(pk=resolved).update(status='resolved')
        ids = [t['id'] for t in self.api(self.admin).get(TICKETS).json()['data']]
        self.assertEqual(ids, [prioritaire, standard_old, standard_new, resolved])
        only = self.api(self.admin).get(TICKETS, {'priority': 'prioritaire'}).json()['data']
        self.assertEqual([t['id'] for t in only], [prioritaire])
        # La file Django suit le même ordre.
        self.assertEqual(list(SupportTicket.objects.exclude(pk=resolved).values_list('pk', flat=True)),
                         [prioritaire, standard_old, standard_new])

    def test_admin_reply_moves_to_in_progress_and_notifies_the_author(self):
        ticket_id = self.open_ticket(self.client_user).json()['data']['id']
        res = self.api(self.admin).post(f'{TICKETS}{ticket_id}/replies/', {'message': 'Nous vérifions votre paiement.'}, format='json')
        self.assertEqual(res.status_code, 201, res.content)
        reply = SupportReply.objects.get()
        self.assertTrue(reply.is_staff_reply)
        self.assertEqual(SupportTicket.objects.get().status, 'in_progress')
        note = Notification.objects.get(user=self.client_user)
        self.assertEqual((note.link, note.action_label), (f'/support?ticket={ticket_id}', 'Voir ma demande'))
        self.assertIn('Réponse', note.title)
        detail = self.api(self.client_user).get(f'{TICKETS}{ticket_id}/').json()['data']
        self.assertEqual(detail['replies'][0]['author_name'], 'Équipe Gaboshop')

    def test_customer_cannot_change_status_but_reply_reopens(self):
        ticket_id = self.open_ticket(self.client_user).json()['data']['id']
        api = self.api(self.client_user)
        self.assertEqual(api.patch(f'{TICKETS}{ticket_id}/', {'status': 'resolved'}, format='json').status_code, 403)
        res = self.api(self.admin).patch(f'{TICKETS}{ticket_id}/', {'status': 'resolved'}, format='json')
        self.assertEqual(res.status_code, 200, res.content)
        self.assertIsNotNone(SupportTicket.objects.get().resolved_at)
        self.assertTrue(Notification.objects.filter(user=self.client_user, title__contains='résolue').exists())
        api.post(f'{TICKETS}{ticket_id}/replies/', {'message': 'Le problème persiste encore.'}, format='json')
        ticket = SupportTicket.objects.get()
        self.assertEqual((ticket.status, ticket.resolved_at), ('open', None))
        self.assertFalse(SupportReply.objects.get().is_staff_reply)

    def test_someone_else_cannot_reply_to_a_ticket(self):
        ticket_id = self.open_ticket(self.client_user).json()['data']['id']
        res = self.api(self.manager).post(f'{TICKETS}{ticket_id}/replies/', {'message': 'Je me mêle de ça.'}, format='json')
        self.assertEqual(res.status_code, 404)
        self.assertEqual(SupportReply.objects.count(), 0)

    def test_invalid_status_is_refused(self):
        ticket_id = self.open_ticket(self.client_user).json()['data']['id']
        res = self.api(self.admin).patch(f'{TICKETS}{ticket_id}/', {'status': 'fermé'}, format='json')
        self.assertEqual(res.status_code, 400)

    # --- notifications aux admins ---

    def test_priority_ticket_notifies_admins_with_priorite(self):
        self.subscribe(self.pro)
        ticket_id = self.open_ticket(self.manager).json()['data']['id']
        note = Notification.objects.get(user=self.admin)
        self.assertIn('Priorité', note.title)
        self.assertEqual((note.link, note.metadata['ticket_id']), (f'/admin/support?ticket={ticket_id}', ticket_id))
        self.assertEqual(note.metadata['level'], 'warning')

    def test_standard_ticket_does_not_notify_admins(self):
        self.open_ticket(self.client_user)
        self.assertEqual(Notification.objects.filter(user=self.admin).count(), 0)

    def test_dedicated_ticket_notifies_admins_too(self):
        self.subscribe(self.business)
        self.open_ticket(self.manager)
        self.assertIn('Priorité', Notification.objects.get(user=self.admin).title)

    def test_customer_reply_on_priority_ticket_alerts_admins(self):
        self.subscribe(self.pro)
        ticket_id = self.open_ticket(self.manager).json()['data']['id']
        Notification.objects.all().delete()
        self.api(self.manager).post(f'{TICKETS}{ticket_id}/replies/', {'message': 'Une précision utile.'}, format='json')
        self.assertIn('Priorité', Notification.objects.get(user=self.admin).title)

    def test_django_admin_lists_priority_first_and_filters_by_priority(self):
        self.open_ticket(self.client_user, subject='Demande standard')
        self.subscribe(self.pro)
        self.open_ticket(self.manager, subject='Demande prioritaire')
        root = User.objects.create_superuser(phone='+24107700099', password='Mapeto88x')
        self.client.force_login(root)
        page = self.client.get('/admin/support/supportticket/')
        self.assertEqual(page.status_code, 200)
        subjects = [t.subject for t in page.context['cl'].result_list]
        self.assertEqual(subjects, ['Demande prioritaire', 'Demande standard'])
        filtered = self.client.get('/admin/support/supportticket/?priority__exact=standard')
        self.assertEqual([t.subject for t in filtered.context['cl'].result_list], ['Demande standard'])
