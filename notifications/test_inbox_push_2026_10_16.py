"""Boîte de notifications, alertes téléphone et PC (Web Push) et annonces de l'administration."""
from datetime import datetime, timedelta, timezone as dt_timezone
from decimal import Decimal
from unittest import mock

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from pywebpush import WebPushException
from rest_framework.test import APIClient

from notifications import push, vapid
from notifications.announcements import audience_counts
from notifications.links import default_action
from notifications.models import (
    Announcement, Notification, NotificationPreference, PushKeyPair, PushSubscription,
)
from notifications.service import NotificationService
from orders.models import Order
from stores.models import Store, StoreCategory
from users.models import User

WEBPUSH = 'pywebpush.webpush'


def subscribe(user, n=1, **kw):
    return PushSubscription.objects.create(
        user=user, endpoint=f'https://push.example.test/{user.pk}/{n}', p256dh='key', auth='auth', **kw)


class Base(TestCase):
    def setUp(self):
        cache.clear()
        vapid.clear_cache()
        self.client_user = User.objects.create_user(phone='+24108100001', password='x', user_type='client')
        self.client_two = User.objects.create_user(phone='+24108100002', password='x', user_type='client')
        self.manager = User.objects.create_user(phone='+24108100003', password='x', user_type='store_manager')
        self.driver = User.objects.create_user(phone='+24108100004', password='x', user_type='delivery_agent')
        self.admin = User.objects.create_user(phone='+24108100005', password='x', user_type='admin', is_staff=True)
        self.api = APIClient()


class InboxApiTests(Base):
    def make(self, n, **kw):
        return [Notification.objects.create(user=self.client_user, title=f'Titre {i}', body='Détail', **kw)
                for i in range(n)]

    def test_list_is_paged_newest_first_with_unread_count(self):
        self.make(35)
        self.api.force_authenticate(self.client_user)
        first = self.api.get('/api/v1/notifications/?limit=30').json()
        self.assertEqual(len(first['data']), 30)
        self.assertTrue(first['has_more'])
        self.assertEqual(first['unread_count'], 35)
        self.assertEqual(first['data'][0]['title'], 'Titre 34')
        last_id = first['data'][-1]['id']
        second = self.api.get(f'/api/v1/notifications/?limit=30&before={last_id}').json()
        self.assertEqual(len(second['data']), 5)
        self.assertFalse(second['has_more'])

    def test_filters_by_type_and_unread_and_never_shows_other_peoples(self):
        self.make(2, notif_type='order')
        self.make(1, notif_type='payment')
        Notification.objects.create(user=self.client_two, title='Autre', body='x')
        Notification.objects.filter(user=self.client_user, notif_type='order').update(is_read=True)
        self.api.force_authenticate(self.client_user)
        orders = self.api.get('/api/v1/notifications/?type=order').json()
        self.assertEqual(len(orders['data']), 2)
        unread = self.api.get('/api/v1/notifications/?unread=1').json()
        self.assertEqual([n['notif_type'] for n in unread['data']], ['payment'])
        everything = self.api.get('/api/v1/notifications/').json()['data']
        self.assertNotIn('Autre', [n['title'] for n in everything])

    def test_old_clients_without_params_still_get_a_list(self):
        self.make(3)
        self.api.force_authenticate(self.client_user)
        body = self.api.get('/api/v1/notifications/').json()
        self.assertTrue(body['success'])
        self.assertEqual(len(body['data']), 3)

    def test_mark_read_records_when_and_unread_counter_follows(self):
        notes = self.make(3)
        self.api.force_authenticate(self.client_user)
        count = self.api.get('/api/v1/notifications/unread-count/').json()['data']
        self.assertEqual(count, {'unread_count': 3, 'latest_id': notes[-1].pk})
        self.assertEqual(self.api.post(f'/api/v1/notifications/{notes[0].pk}/read/').status_code, 200)
        notes[0].refresh_from_db()
        self.assertTrue(notes[0].is_read)
        self.assertIsNotNone(notes[0].read_at)
        self.api.post('/api/v1/notifications/mark-all-read/')
        self.assertEqual(self.api.get('/api/v1/notifications/unread-count/').json()['data']['unread_count'], 0)

    def test_someone_else_cannot_read_or_delete_my_notification(self):
        note = self.make(1)[0]
        self.api.force_authenticate(self.client_two)
        self.assertEqual(self.api.post(f'/api/v1/notifications/{note.pk}/read/').status_code, 404)
        self.assertEqual(self.api.delete(f'/api/v1/notifications/{note.pk}/').status_code, 404)

    def test_anonymous_is_refused(self):
        self.assertIn(self.api.get('/api/v1/notifications/').status_code, (401, 403))
        self.assertIn(self.api.get('/api/v1/notifications/unread-count/').status_code, (401, 403))


class LinkTests(Base):
    def setUp(self):
        super().setUp()
        store = Store.objects.create(
            name='Boutique', category=StoreCategory.objects.create(name='Cat'), manager=self.manager,
            phone='+24108100010', address='Libreville', zone='Centre')
        self.order = Order.objects.create(
            client=self.client_user, store=store, order_number='CMD-LINK', total_amount=Decimal('1000'),
            items_total=Decimal('1000'), delivery_address='x', delivery_phone='+24108100001', delivery_zone='Centre')

    def test_list_gives_the_order_number_the_client_knows(self):
        Notification.objects.create(user=self.client_user, title='t', body='b', order=self.order)
        self.api.force_authenticate(self.client_user)
        row = self.api.get('/api/v1/notifications/').json()['data'][0]
        self.assertEqual(row['order_number'], 'CMD-LINK')

    def test_each_role_lands_on_its_own_screen(self):
        note = Notification.objects.create(user=self.client_user, title='t', body='b', order=self.order)
        self.assertEqual((note.link, note.action_label), (f'/client/orders?order={self.order.pk}', 'Voir ma commande'))
        note = Notification.objects.create(user=self.manager, title='t', body='b', order=self.order)
        self.assertEqual(note.link, f'/store/orders?order={self.order.pk}')
        note = Notification.objects.create(user=self.driver, title='t', body='b', order=self.order)
        self.assertEqual(note.link, '/delivery/dashboard')

    def test_failed_payment_leads_to_the_payment_screen(self):
        note = Notification.objects.create(user=self.client_user, title='Paiement échoué', body='b', order=self.order,
                                           notif_type='payment', metadata={'level': 'error'})
        self.assertEqual((note.link, note.action_label), (f'/client/orders?pay={self.order.pk}', 'Payer ma commande'))

    def test_notification_without_target_has_no_button(self):
        note = Notification.objects.create(user=self.client_user, title='Bienvenue', body='b')
        self.assertEqual((note.link, note.action_label), ('', ''))
        self.assertEqual(default_action(note), ('', ''))

    def test_service_notifications_get_their_link_too(self):
        NotificationService.notify_user(
            self.client_user, {'title': 'Commande payée', 'body': 'ok', 'level': 'success'}, notif_type='order',
            order=self.order)
        self.assertEqual(Notification.objects.get(user=self.client_user).link, f'/client/orders?order={self.order.pk}')


@override_settings(PUSH_SYNC=True)
class PushDeviceApiTests(Base):
    def sub_body(self, endpoint='https://fcm.googleapis.com/fcm/send/dev-1'):
        return {'endpoint': endpoint, 'keys': {'p256dh': 'BKey', 'auth': 'authkey'}}

    def test_config_gives_a_public_key_and_creates_it_once(self):
        self.api.force_authenticate(self.client_user)
        first = self.api.get('/api/v1/notifications/push/config/').json()['data']
        self.assertTrue(first['enabled'])
        self.assertGreater(len(first['public_key']), 80)
        vapid.clear_cache()
        second = self.api.get('/api/v1/notifications/push/config/').json()['data']
        self.assertEqual(first['public_key'], second['public_key'])
        self.assertEqual(PushKeyPair.objects.count(), 1)

    def test_environment_keys_win_over_the_database(self):
        with override_settings(VAPID_PUBLIC_KEY='PUB', VAPID_PRIVATE_KEY='PRIV'):
            self.assertEqual(vapid.get_keys(), ('PUB', 'PRIV'))
        self.assertEqual(PushKeyPair.objects.count(), 0)

    def test_push_can_be_cut_off_entirely(self):
        self.api.force_authenticate(self.client_user)
        with override_settings(PUSH_ENABLED=False):
            config = self.api.get('/api/v1/notifications/push/config/').json()['data']
            self.assertFalse(config['enabled'])
            res = self.api.post('/api/v1/notifications/push/subscribe/', self.sub_body(), format='json')
            self.assertEqual(res.status_code, 503)

    def test_subscribe_registers_the_device_and_a_second_call_does_not_duplicate(self):
        self.api.force_authenticate(self.client_user)
        for _ in range(2):
            res = self.api.post('/api/v1/notifications/push/subscribe/', self.sub_body(), format='json')
            self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(PushSubscription.objects.filter(user=self.client_user).count(), 1)

    def test_incomplete_or_insecure_subscription_is_explained(self):
        self.api.force_authenticate(self.client_user)
        for body in ({'endpoint': 'http://insecure/x', 'keys': {'p256dh': 'a', 'auth': 'b'}},
                     {'endpoint': 'https://fcm.googleapis.com/x', 'keys': {}}, {}):
            res = self.api.post('/api/v1/notifications/push/subscribe/', body, format='json')
            self.assertEqual(res.status_code, 400)
            error = res.json()['error']
            self.assertTrue(error['reason'] and error['next_step'])
        self.assertFalse(PushSubscription.objects.exists())

    def test_only_real_push_services_are_accepted(self):
        """Le serveur envoie vers l'adresse enregistrée : une adresse interne ou inconnue est refusée."""
        self.api.force_authenticate(self.client_user)
        keys = {'p256dh': 'BKey', 'auth': 'authkey'}
        for endpoint in ('https://169.254.169.254/latest/meta-data', 'https://localhost/x', 'https://evil.example/x',
                         'https://fcm.googleapis.com.evil.example/x', 'https://user:pw@fcm.googleapis.com/x',
                         'https://fcm.googleapis.com:8443/x', 'https://notgoogleapis.com/x'):
            res = self.api.post('/api/v1/notifications/push/subscribe/', {'endpoint': endpoint, 'keys': keys}, format='json')
            self.assertEqual(res.status_code, 400, endpoint)
        for endpoint in ('https://fcm.googleapis.com/fcm/send/abc', 'https://updates.push.services.mozilla.com/wpush/v2/abc',
                         'https://web.push.apple.com/abc', 'https://wns2-par02p.notify.windows.com/w/?token=abc'):
            res = self.api.post('/api/v1/notifications/push/subscribe/', {'endpoint': endpoint, 'keys': keys}, format='json')
            self.assertEqual(res.status_code, 201, endpoint)

    def test_device_moves_to_the_account_that_logs_in_on_it(self):
        self.api.force_authenticate(self.client_user)
        self.api.post('/api/v1/notifications/push/subscribe/', self.sub_body(), format='json')
        self.api.force_authenticate(self.client_two)
        self.api.post('/api/v1/notifications/push/subscribe/', self.sub_body(), format='json')
        self.assertEqual(PushSubscription.objects.get().user, self.client_two)

    def test_at_most_ten_devices_stay_active(self):
        self.api.force_authenticate(self.client_user)
        for i in range(12):
            self.api.post('/api/v1/notifications/push/subscribe/', self.sub_body(f'https://fcm.googleapis.com/fcm/send/d{i}'),
                          format='json')
        self.assertEqual(PushSubscription.objects.filter(user=self.client_user, is_active=True).count(), 10)

    def test_unsubscribe_forgets_only_my_device(self):
        self.api.force_authenticate(self.client_user)
        self.api.post('/api/v1/notifications/push/subscribe/', self.sub_body(), format='json')
        self.api.force_authenticate(self.client_two)
        self.api.post('/api/v1/notifications/push/unsubscribe/', {'endpoint': self.sub_body()['endpoint']}, format='json')
        self.assertEqual(PushSubscription.objects.count(), 1)  # pas le sien : rien n'est supprimé
        self.api.force_authenticate(self.client_user)
        self.api.post('/api/v1/notifications/push/unsubscribe/', {'endpoint': self.sub_body()['endpoint']}, format='json')
        self.assertEqual(PushSubscription.objects.count(), 0)

    def test_test_alert_needs_a_device_then_reports_how_many_got_it(self):
        self.api.force_authenticate(self.client_user)
        refused = self.api.post('/api/v1/notifications/push/test/')
        self.assertEqual(refused.status_code, 400)
        self.assertEqual(refused.json()['error']['code'], 'no_device')
        subscribe(self.client_user)
        with mock.patch(WEBPUSH) as sent:
            res = self.api.post('/api/v1/notifications/push/test/')
        self.assertEqual(res.json()['data'], {'devices': 1, 'delivered': 1})
        self.assertEqual(sent.call_count, 1)  # un seul envoi : pas de doublon avec l'envoi automatique
        self.assertTrue(Notification.objects.filter(user=self.client_user, title='Les alertes fonctionnent').exists())

    def test_preferences_only_cut_announcements(self):
        self.api.force_authenticate(self.client_user)
        self.assertTrue(self.api.get('/api/v1/notifications/preferences/').json()['data']['announcements'])
        res = self.api.patch('/api/v1/notifications/preferences/', {'announcements': False}, format='json')
        self.assertFalse(res.json()['data']['announcements'])
        self.assertEqual(self.api.patch('/api/v1/notifications/preferences/', {'announcements': 'oui'},
                                        format='json').status_code, 400)


@override_settings(PUSH_SYNC=True)
class PushDeliveryTests(Base):
    def create_note(self, user=None, **kw):
        with self.captureOnCommitCallbacks(execute=True):
            return Notification.objects.create(user=user or self.client_user, title='Commande en route',
                                               body='Le livreur arrive avec votre commande.', **kw)

    def test_every_new_notification_alerts_the_persons_devices(self):
        subscribe(self.client_user)
        subscribe(self.client_user, n=2)
        with mock.patch(WEBPUSH) as sent:
            note = self.create_note(link='/client/orders?order=7', action_label='Voir')
        self.assertEqual(sent.call_count, 2)
        payload = __import__('json').loads(sent.call_args.kwargs['data'])
        self.assertEqual(payload['title'], 'Commande en route')
        self.assertEqual(payload['url'], '/client/orders?order=7')
        self.assertEqual(payload['tag'], f'n-{note.pk}')
        claims = sent.call_args.kwargs['vapid_claims']
        self.assertTrue(claims['sub'].startswith(('mailto:', 'https://')))

    def test_nobody_else_is_alerted_and_no_device_means_no_attempt(self):
        subscribe(self.client_user)
        with mock.patch(WEBPUSH) as sent:
            self.create_note(user=self.client_two)
        sent.assert_not_called()

    def test_service_notifications_alert_too(self):
        subscribe(self.client_user)
        with mock.patch(WEBPUSH) as sent, self.captureOnCommitCallbacks(execute=True):
            NotificationService.notify_user(self.client_user, {'title': 'Paiement reçu', 'body': 'Merci', 'level': 'success'},
                                            notif_type='payment')
        self.assertEqual(sent.call_count, 1)

    def test_a_long_message_is_shortened_for_the_lock_screen(self):
        subscribe(self.client_user)
        with mock.patch(WEBPUSH) as sent, self.captureOnCommitCallbacks(execute=True):
            Notification.objects.create(user=self.client_user, title='T' * 150, body='mot ' * 200)
        payload = __import__('json').loads(sent.call_args.kwargs['data'])
        self.assertLessEqual(len(payload['title']), 90)
        self.assertLessEqual(len(payload['body']), 160)

    def test_expired_device_is_set_aside_at_once(self):
        sub = subscribe(self.client_user)
        gone = WebPushException('Gone', response=mock.Mock(status_code=410))
        with mock.patch(WEBPUSH, side_effect=gone):
            self.create_note()
        sub.refresh_from_db()
        self.assertFalse(sub.is_active)

    def test_a_flaky_device_is_set_aside_after_five_failures(self):
        sub = subscribe(self.client_user)
        boom = WebPushException('Server error', response=mock.Mock(status_code=500))
        with mock.patch(WEBPUSH, side_effect=boom):
            for _ in range(4):
                self.create_note()
            sub.refresh_from_db()
            self.assertTrue(sub.is_active)
            self.assertEqual(sub.failure_count, 4)
            self.create_note()
        sub.refresh_from_db()
        self.assertFalse(sub.is_active)

    def test_success_resets_the_failure_counter(self):
        sub = subscribe(self.client_user)
        PushSubscription.objects.filter(pk=sub.pk).update(failure_count=3)
        with mock.patch(WEBPUSH):
            self.create_note()
        sub.refresh_from_db()
        self.assertEqual(sub.failure_count, 0)
        self.assertIsNotNone(sub.last_success_at)

    def test_a_network_error_never_breaks_the_order_flow(self):
        subscribe(self.client_user)
        with mock.patch(WEBPUSH, side_effect=ConnectionError('réseau coupé')):
            note = self.create_note()
        self.assertTrue(Notification.objects.filter(pk=note.pk).exists())

    @override_settings(PUSH_ENABLED=False)
    def test_nothing_is_sent_when_alerts_are_cut(self):
        subscribe(self.client_user)
        with mock.patch(WEBPUSH) as sent:
            self.create_note()
        sent.assert_not_called()


@override_settings(PUSH_SYNC=True)
class AnnouncementTests(Base):
    URL = '/api/v1/admin/announcements/'

    def post(self, **kw):
        body = {'title': '10 % sur les boissons', 'body': 'Ce week-end, profitez de 10 % sur toutes les boissons.',
                'audience': 'clients', **kw}
        with self.captureOnCommitCallbacks(execute=True):
            return self.api.post(self.URL, body, format='json')

    def test_only_an_admin_can_send_or_read_announcements(self):
        for user in (self.client_user, self.manager, self.driver):
            self.api.force_authenticate(user)
            self.assertEqual(self.api.post(self.URL, {'title': 'abc', 'body': 'hello world', 'audience': 'clients'},
                                           format='json').status_code, 403)
            self.assertEqual(self.api.get(self.URL).status_code, 403)
        self.assertFalse(Announcement.objects.exists())

    def test_clients_receive_it_and_nobody_else(self):
        self.api.force_authenticate(self.admin)
        res = self.post()
        self.assertEqual(res.status_code, 201, res.content)
        data = res.json()['data']
        self.assertEqual(data['recipients_count'], 2)
        got = set(Notification.objects.filter(notif_type='announcement').values_list('user__phone', flat=True))
        self.assertEqual(got, {self.client_user.phone, self.client_two.phone})
        note = Notification.objects.get(user=self.client_user)
        self.assertEqual(note.title, '10 % sur les boissons')
        self.assertFalse(note.is_read)

    def test_each_audience_reaches_its_own_group(self):
        self.api.force_authenticate(self.admin)
        self.assertEqual(self.post(audience='stores').json()['data']['recipients_count'], 1)
        self.assertEqual(self.post(audience='drivers', title='Nouvelle règle livreurs').json()['data']['recipients_count'], 1)
        everyone = self.post(audience='everyone', title='Maintenance ce soir').json()['data']
        self.assertEqual(everyone['recipients_count'], 4)  # sans l'administrateur

    def test_inactive_accounts_and_people_who_cut_announcements_are_skipped(self):
        User.objects.filter(pk=self.client_two.pk).update(is_active=False)
        extra = User.objects.create_user(phone='+24108100006', password='x', user_type='client')
        NotificationPreference.objects.create(user=extra, announcements=False)
        self.api.force_authenticate(self.admin)
        self.assertEqual(self.post().json()['data']['recipients_count'], 1)
        self.assertFalse(Notification.objects.filter(user=extra).exists())

    def test_admin_can_try_it_on_their_own_phone_first(self):
        self.api.force_authenticate(self.admin)
        res = self.post(audience='me')
        self.assertEqual(res.json()['data']['recipients_count'], 1)
        self.assertEqual(list(Notification.objects.values_list('user', flat=True)), [self.admin.pk])

    def test_a_double_click_does_not_send_twice(self):
        self.api.force_authenticate(self.admin)
        self.assertEqual(self.post().status_code, 201)
        again = self.post()
        self.assertEqual(again.status_code, 409)
        self.assertEqual(again.json()['error']['code'], 'duplicate_announcement')
        self.assertEqual(Notification.objects.filter(notif_type='announcement').count(), 2)
        # Un message modifié, lui, part.
        self.assertEqual(self.post(body='Un autre message pour les clients.').status_code, 201)

    def test_bad_input_is_explained(self):
        self.api.force_authenticate(self.admin)
        for field, value, code in (('title', 'ab', 'invalid_title'), ('body', 'non', 'invalid_body'),
                                   ('audience', 'martiens', 'invalid_audience'),
                                   ('link', 'https://evil.example/x', 'invalid_link'), ('link', '//evil', 'invalid_link')):
            res = self.post(**{field: value})
            self.assertEqual(res.status_code, 400, (field, value))
            self.assertEqual(res.json()['error']['code'], code)
            self.assertTrue(res.json()['error']['next_step'])
        self.assertFalse(Announcement.objects.exists())

    def test_link_and_button_reach_the_notification(self):
        self.api.force_authenticate(self.admin)
        self.post(link='/boutiques', action_label='Voir les boutiques')
        note = Notification.objects.get(user=self.client_user)
        self.assertEqual((note.link, note.action_label), ('/boutiques', 'Voir les boutiques'))
        self.post(link='/boutiques', title='Autre annonce', action_label='')
        self.assertEqual(Notification.objects.filter(user=self.client_user).latest('id').action_label, 'Voir')

    def test_devices_of_recipients_are_alerted_during_the_day(self):
        subscribe(self.client_user)
        subscribe(self.manager)  # pas dans l'audience
        self.api.force_authenticate(self.admin)
        with mock.patch(WEBPUSH) as sent, mock.patch('notifications.push.in_quiet_hours', return_value=False), \
                self.captureOnCommitCallbacks(execute=True):
            data = self.post().json()['data']
        self.assertEqual(data['push_state'], 'pending')   # l'alerte part en arrière-plan
        self.assertEqual(sent.call_count, 1)
        shown = self.api.get(self.URL).json()['data']['announcements'][0]
        self.assertEqual((shown['push_attempted'], shown['push_delivered'], shown['push_state']), (1, 1, 'sent'))

    def test_at_night_the_alert_waits_for_morning_unless_urgent(self):
        subscribe(self.client_user)
        self.api.force_authenticate(self.admin)
        with mock.patch(WEBPUSH) as sent, mock.patch('notifications.push.in_quiet_hours', return_value=True):
            data = self.post().json()['data']
            self.assertEqual(sent.call_count, 0)
            self.assertEqual(data['push_state'], 'deferred')
            self.assertIsNotNone(data['push_after'])
            # In-app, le client la voit déjà.
            self.assertTrue(Notification.objects.filter(user=self.client_user, notif_type='announcement').exists())
            with self.captureOnCommitCallbacks(execute=True):
                urgent = self.post(title='Coupure de courant', urgent=True).json()['data']
        self.assertEqual(sent.call_count, 1)
        self.assertEqual(Announcement.objects.get(pk=urgent['id']).push_done, True)

    def test_deferred_alert_leaves_at_seven_through_the_scheduled_job(self):
        subscribe(self.client_user)
        self.api.force_authenticate(self.admin)
        with mock.patch(WEBPUSH) as sent, mock.patch('notifications.push.in_quiet_hours', return_value=True):
            announcement_id = self.post().json()['data']['id']
            self.assertEqual(push.send_deferred_announcements(), '0 annonce(s) repoussée(s) envoyée(s), 0 appareil(s) alerté(s)')
            Announcement.objects.filter(pk=announcement_id).update(push_after=timezone.now() - timedelta(minutes=1))
            message = push.send_deferred_announcements()
            self.assertIn('1 annonce(s)', message)
            self.assertEqual(sent.call_count, 1)
            push.send_deferred_announcements()  # une annonce n'est alertée qu'une fois
            self.assertEqual(sent.call_count, 1)

    def test_push_can_be_switched_off_per_announcement(self):
        subscribe(self.client_user)
        self.api.force_authenticate(self.admin)
        with mock.patch(WEBPUSH) as sent:
            data = self.post(send_push=False).json()['data']
        sent.assert_not_called()
        self.assertEqual(data['push_state'], 'off')

    def test_history_shows_reads_and_audience_sizes(self):
        subscribe(self.client_user)
        self.api.force_authenticate(self.admin)
        self.post()
        Notification.objects.filter(user=self.client_user, notif_type='announcement').update(is_read=True)
        data = self.api.get(self.URL).json()['data']
        self.assertEqual(data['announcements'][0]['read_count'], 1)
        self.assertEqual(data['announcements'][0]['recipients_count'], 2)
        self.assertEqual(data['audiences']['clients'], {'recipients': 2, 'with_alerts': 1})
        self.assertEqual(data['audiences']['everyone']['recipients'], 4)
        self.assertTrue(data['push_enabled'])

    def test_night_helpers_use_libreville_time(self):
        utc = dt_timezone.utc
        self.assertTrue(push.in_quiet_hours(datetime(2026, 10, 16, 20, 30, tzinfo=utc)))   # 21 h 30 à Libreville
        self.assertFalse(push.in_quiet_hours(datetime(2026, 10, 16, 12, 0, tzinfo=utc)))   # 13 h
        self.assertTrue(push.in_quiet_hours(datetime(2026, 10, 16, 5, 30, tzinfo=utc)))    # 6 h 30
        self.assertEqual(push.next_morning(datetime(2026, 10, 16, 21, 0, tzinfo=utc)),
                         datetime(2026, 10, 17, 6, 0, tzinfo=utc))   # 7 h le lendemain à Libreville
        self.assertEqual(push.next_morning(datetime(2026, 10, 16, 4, 0, tzinfo=utc)),
                         datetime(2026, 10, 16, 6, 0, tzinfo=utc))

    def test_audience_counts_helper(self):
        self.assertEqual(audience_counts()['stores']['recipients'], 1)


class HealthTests(Base):
    def test_health_tells_how_alerts_are_configured(self):
        data = self.api.get('/api/v1/health/').json()['data']
        self.assertEqual(data['push_mode'], 'database')
        with override_settings(VAPID_PUBLIC_KEY='a', VAPID_PRIVATE_KEY='b'):
            self.assertEqual(self.api.get('/api/v1/health/').json()['data']['push_mode'], 'env')
        with override_settings(PUSH_ENABLED=False):
            self.assertEqual(self.api.get('/api/v1/health/').json()['data']['push_mode'], 'off')
