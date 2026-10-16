import logging
from urllib.parse import urlparse

from django.db.utils import OperationalError
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from notifications import announcements as announcement_service
from notifications import push, vapid
from notifications.models import Announcement, Notification, NotificationPreference, PushSubscription
from notifications.serializers import AnnouncementSerializer, NotificationSerializer

logger = logging.getLogger(__name__)

TYPES = {'info', 'order', 'delivery', 'payment', 'warning', 'announcement'}
MAX_DEVICES = 10
# Services d'alertes des navigateurs (Chrome/Edge/Opera/Samsung via Google, Firefox, Safari, Edge Windows).
# Le serveur envoie vers l'adresse enregistrée : une adresse quelconque servirait à lui faire contacter n'importe quel site.
PUSH_HOST_SUFFIXES = ('.googleapis.com', '.push.services.mozilla.com', '.push.apple.com', '.notify.windows.com')


def _is_push_service(endpoint):
    parsed = urlparse(endpoint)
    host = (parsed.hostname or '').lower()
    if parsed.scheme != 'https' or parsed.username or parsed.password or parsed.port not in (None, 443):
        return False
    return any(host.endswith(suffix) for suffix in PUSH_HOST_SUFFIXES)


def _error(code, message, next_step='', http=status.HTTP_400_BAD_REQUEST, reason=''):
    error = {'code': code, 'message': message}
    if reason:
        error['reason'] = reason
    if next_step:
        error['next_step'] = next_step
    return Response({'success': False, 'error': error}, status=http)


class NotificationListView(APIView):
    """GET /notifications/?limit=30&before=<id>&unread=1&type=order : les plus récentes d'abord, par pages."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            try:
                limit = max(1, min(int(request.query_params.get('limit') or 30), 100))
                before = int(request.query_params.get('before') or 0)
            except (TypeError, ValueError):
                limit, before = 30, 0
            qs = Notification.objects.filter(user=request.user)
            if request.query_params.get('unread') in ('1', 'true'):
                qs = qs.filter(is_read=False)
            kind = request.query_params.get('type')
            if kind in TYPES:
                qs = qs.filter(notif_type=kind)
            if before:
                qs = qs.filter(pk__lt=before)
            rows = list(qs.select_related('user', 'order').order_by('-id')[:limit + 1])
            has_more = len(rows) > limit
            return Response({
                'success': True,
                'data': NotificationSerializer(rows[:limit], many=True).data,
                'has_more': has_more,
                'unread_count': Notification.objects.filter(user=request.user, is_read=False).count(),
            })
        except OperationalError as e:
            logger.warning("Notification query temporarily unavailable for user %s: %s", request.user.id, str(e))
            return Response({
                'success': True, 'data': [], 'has_more': False, 'unread_count': 0,
                'message': 'Notifications temporairement indisponibles, reessayez.',
            })
        except Exception as e:
            logger.error(f"Error fetching notifications for user {request.user.id}: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': {
                    'code': status.HTTP_500_INTERNAL_SERVER_ERROR,
                    'message': 'Erreur lors de la récupération des notifications',
                    'details': str(e) if request.user.is_staff else None,
                },
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class NotificationUnreadCountView(APIView):
    """GET /notifications/unread-count/ : appel léger pour le badge ; latest_id change quand une nouvelle arrive."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            mine = Notification.objects.filter(user=request.user)
            latest = mine.order_by('-id').values_list('id', flat=True).first() or 0
            return Response({'success': True, 'data': {
                'unread_count': mine.filter(is_read=False).count(), 'latest_id': latest,
            }})
        except OperationalError:
            return Response({'success': True, 'data': {'unread_count': 0, 'latest_id': 0}})


class NotificationMarkAllReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True, read_at=timezone.now())
        return Response({'success': True, 'message': 'Notifications marquées lues'})


class NotificationMarkReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            notif = Notification.objects.get(id=pk, user=request.user)
            if not notif.is_read:
                notif.is_read = True
                notif.read_at = timezone.now()
                notif.save(update_fields=['is_read', 'read_at'])
            return Response({'success': True})
        except Notification.DoesNotExist:
            return Response({
                'success': False,
                'error': {
                    'code': status.HTTP_404_NOT_FOUND,
                    'message': 'Notification introuvable'
                }
            }, status=status.HTTP_404_NOT_FOUND)


class NotificationDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        try:
            notif = Notification.objects.get(id=pk, user=request.user)
            notif.delete()
            return Response({'success': True, 'message': 'Notification supprimée'})
        except Notification.DoesNotExist:
            return Response({
                'success': False,
                'error': {
                    'code': status.HTTP_404_NOT_FOUND,
                    'message': 'Notification introuvable'
                }
            }, status=status.HTTP_404_NOT_FOUND)


# --- Alertes sur l'appareil ------------------------------------------------------------------

class PushConfigView(APIView):
    """GET /notifications/push/config/ : clé publique pour s'abonner, et nombre d'appareils déjà enregistrés."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        public_key, _private = vapid.get_keys()
        devices = PushSubscription.objects.filter(user=request.user, is_active=True, kind='web').count()
        return Response({'success': True, 'data': {
            'enabled': bool(public_key), 'public_key': public_key, 'devices': devices,
        }})


class PushSubscribeView(APIView):
    """POST /notifications/push/subscribe/ {endpoint, keys: {p256dh, auth}} : enregistre cet appareil."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        data = request.data if isinstance(request.data, dict) else {}
        endpoint = str(data.get('endpoint') or '').strip()
        keys = data.get('keys') if isinstance(data.get('keys'), dict) else {}
        p256dh, auth = str(keys.get('p256dh') or '').strip(), str(keys.get('auth') or '').strip()
        if not _is_push_service(endpoint) or len(endpoint) > 2000 or not p256dh or not auth:
            return _error(
                'invalid_subscription', "Cet appareil n'a pas pu être enregistré pour les alertes.",
                next_step="Réessayez en cliquant sur « Activer les alertes ». Si cela recommence, utilisez Chrome ou Safari à jour.",
                reason="Le navigateur a envoyé une inscription incomplète.")
        if not vapid.get_keys()[0]:
            return _error('push_disabled', "Les alertes sont désactivées sur ce site pour le moment.",
                          http=status.HTTP_503_SERVICE_UNAVAILABLE)
        sub, _created = PushSubscription.objects.update_or_create(
            endpoint_hash=PushSubscription.hash_endpoint(endpoint),
            defaults={
                'user': request.user, 'kind': 'web', 'endpoint': endpoint, 'p256dh': p256dh, 'auth': auth,
                'user_agent': str(data.get('user_agent') or request.META.get('HTTP_USER_AGENT', ''))[:300],
                'is_active': True, 'failure_count': 0,
            },
        )
        # Au plus MAX_DEVICES appareils actifs par personne : les plus anciens sont mis de côté.
        extra = PushSubscription.objects.filter(user=request.user, is_active=True).order_by('-id').values_list('id', flat=True)[MAX_DEVICES:]
        PushSubscription.objects.filter(id__in=list(extra)).update(is_active=False)
        return Response({'success': True, 'data': {'id': sub.pk}}, status=status.HTTP_201_CREATED)


class PushUnsubscribeView(APIView):
    """POST /notifications/push/unsubscribe/ {endpoint} : cet appareil n'est plus alerté."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        endpoint = str((request.data or {}).get('endpoint') or '').strip()
        if endpoint:
            PushSubscription.objects.filter(
                user=request.user, endpoint_hash=PushSubscription.hash_endpoint(endpoint)).delete()
        return Response({'success': True})


class PushTestView(APIView):
    """POST /notifications/push/test/ : envoie une alerte d'essai à tous les appareils de la personne."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        devices = PushSubscription.objects.filter(user=request.user, is_active=True, kind='web').count()
        if not devices:
            return _error(
                'no_device', "Aucun appareil n'est enregistré pour les alertes.",
                next_step="Cliquez d'abord sur « Activer les alertes » sur l'appareil à tester.",
                reason="Ce compte n'a pas encore autorisé les alertes sur un téléphone ou un ordinateur.")
        note = Notification(
            user=request.user, title='Les alertes fonctionnent', notif_type='info',
            body="Vous recevrez ici les nouvelles de vos commandes, paiements et livraisons, même quand Gaboshop est fermé.",
            link='/notifications', action_label='Voir mes notifications', metadata={'level': 'success'},
        )
        note._skip_push = True  # l'envoi ci-dessous se fait tout de suite, pour compter les appareils joints
        note.save()
        delivered = push.deliver_notification(note.pk) if push.enabled() else 0
        return Response({'success': True, 'data': {'devices': devices, 'delivered': delivered}})


class NotificationPreferencesView(APIView):
    """GET/PATCH /notifications/preferences/ : couper les annonces (jamais les alertes de commande)."""
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def _payload(user):
        pref = NotificationPreference.objects.filter(user=user).first()
        return {'announcements': True if pref is None else pref.announcements}

    def get(self, request):
        return Response({'success': True, 'data': self._payload(request.user)})

    def patch(self, request):
        value = (request.data or {}).get('announcements')
        if not isinstance(value, bool):
            return _error('invalid_preference', "Réglage non reconnu.",
                          next_step="Choisissez « Recevoir les annonces » ou « Ne plus recevoir les annonces ».")
        NotificationPreference.objects.update_or_create(user=request.user, defaults={'announcements': value})
        return Response({'success': True, 'data': self._payload(request.user)})


# --- Annonces de l'administration ------------------------------------------------------------

class IsPlatformAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_staff or user.user_type == 'admin'))


class AdminAnnouncementsView(APIView):
    """GET : historique et nombre de destinataires par groupe ; POST : envoyer une annonce."""
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        rows = Announcement.objects.select_related('created_by')[:50]
        return Response({'success': True, 'data': {
            'announcements': AnnouncementSerializer(rows, many=True).data,
            'audiences': announcement_service.audience_counts(),
            'push_enabled': bool(vapid.get_keys()[0]),
        }})

    def post(self, request):
        data = request.data if isinstance(request.data, dict) else {}
        title = ' '.join(str(data.get('title') or '').split())
        body = str(data.get('body') or '').strip()
        audience = str(data.get('audience') or '')
        link = str(data.get('link') or '').strip()
        action_label = ' '.join(str(data.get('action_label') or '').split())

        if not 3 <= len(title) <= 120:
            return _error('invalid_title', 'Le titre doit faire entre 3 et 120 caractères.',
                          next_step="Écrivez une phrase courte qui dit l'essentiel, par exemple « 10 % sur les boissons ce week-end ».")
        if not 5 <= len(body) <= 600:
            return _error('invalid_body', 'Le message doit faire entre 5 et 600 caractères.',
                          next_step="Dites en deux ou trois phrases simples ce que la personne doit savoir ou faire.")
        if audience not in announcement_service.AUDIENCE_LABELS:
            return _error('invalid_audience', "Choisissez à qui envoyer l'annonce.",
                          next_step="Clients, commerces, livreurs, tout le monde, ou « Moi seul » pour essayer.")
        if link and (not link.startswith('/') or link.startswith('//') or len(link) > 200):
            return _error('invalid_link', "Le lien doit mener à une page de Gaboshop.",
                          next_step="Choisissez une destination dans la liste, ou laissez vide.")
        if link and not action_label:
            action_label = 'Voir'
        if not link:
            action_label = ''

        if audience != 'me' and announcement_service.find_duplicate(title, body, audience):
            return _error(
                'duplicate_announcement', 'Cette annonce vient déjà d\'être envoyée.',
                reason="Le même message est parti au même groupe il y a moins de 2 minutes (double clic probable).",
                next_step="Vérifiez l'historique ci-dessous. Pour renvoyer, modifiez le message ou attendez 2 minutes.",
                http=status.HTTP_409_CONFLICT)

        announcement = Announcement.objects.create(
            title=title, body=body, audience=audience, link=link, action_label=action_label[:40],
            send_push=bool(data.get('send_push', True)), urgent=bool(data.get('urgent', False)),
            created_by=request.user,
        )
        announcement_service.send_announcement(announcement, sender=request.user)
        announcement.refresh_from_db()
        payload = AnnouncementSerializer(announcement).data
        payload['push_mode'] = getattr(announcement, 'push_mode', 'none')
        return Response({'success': True, 'data': payload}, status=status.HTTP_201_CREATED)
