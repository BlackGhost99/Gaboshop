"""Alertes sur téléphone et ordinateur (Web Push).

Toute notification enregistrée pour une personne part aussi, en quelques secondes, sur les appareils où elle a
accepté les alertes, même quand le site est fermé. L'envoi se fait en arrière-plan : une demande d'un client ne
attend jamais un service d'alertes lent.
"""
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, time, timedelta, timezone as dt_timezone

from django.conf import settings
from django.db import close_old_connections, transaction
from django.utils import timezone

from . import vapid

logger = logging.getLogger(__name__)

TTL_SECONDS = 24 * 3600          # une alerte non remise dans la journée n'a plus d'intérêt
MAX_FAILURES = 5                 # un appareil qui échoue 5 fois de suite est mis de côté
QUIET_START, QUIET_END = time(21, 0), time(7, 0)   # heure de Libreville : pas d'annonce commerciale la nuit
LIBREVILLE = dt_timezone(timedelta(hours=1))
_pool = None


def enabled():
    return bool(getattr(settings, 'PUSH_ENABLED', True))


def _executor():
    global _pool
    if _pool is None:
        _pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix='push')
    return _pool


def _run(func, *args):
    """En arrière-plan, sauf pour les tests (PUSH_SYNC) qui veulent le résultat tout de suite."""
    if getattr(settings, 'PUSH_SYNC', False):
        return func(*args)

    def runner():
        try:
            func(*args)
        except Exception:
            logger.exception('Envoi des alertes en échec')
        finally:
            close_old_connections()

    _executor().submit(runner)
    return None


# --- Contenu -----------------------------------------------------------------------------

def _short(text, limit):
    text = ' '.join((text or '').split())
    return text if len(text) <= limit else text[:limit - 1].rstrip() + '…'


def payload_for(notification):
    return {
        'title': _short(notification.title, 90),
        'body': _short(notification.body, 160),
        'url': notification.link or '/notifications',
        'tag': f'n-{notification.id}',
        'id': notification.id,
        'type': notification.notif_type,
        'level': (notification.metadata or {}).get('level', 'info'),
        'icon': '/icon-192.png',
        'badge': '/icon-192.png',
    }


def payload_for_announcement(announcement):
    return {
        'title': _short(announcement.title, 90),
        'body': _short(announcement.body, 160),
        'url': announcement.link or '/notifications',
        'tag': f'a-{announcement.id}',
        'type': 'announcement',
        'level': 'info',
        'icon': '/icon-192.png',
        'badge': '/icon-192.png',
    }


# --- Envoi à un appareil -----------------------------------------------------------------

def _post(subscription, payload):
    """Envoi réseau seul, sans toucher à la base (peut tourner en parallèle). Renvoie 'ok', 'gone' ou 'failed'."""
    from pywebpush import WebPushException, webpush

    _public, private = vapid.get_keys()
    if not private:
        return 'failed'
    try:
        webpush(
            subscription_info={'endpoint': subscription.endpoint,
                               'keys': {'p256dh': subscription.p256dh, 'auth': subscription.auth}},
            data=json.dumps(payload, ensure_ascii=False),
            vapid_private_key=private,
            vapid_claims={'sub': vapid.subject()},
            ttl=TTL_SECONDS,
            timeout=10,
        )
    except WebPushException as exc:
        status = getattr(getattr(exc, 'response', None), 'status_code', None)
        logger.info('Alerte refusée (%s) pour l\'appareil %s', status, subscription.pk)
        return 'gone' if status in (404, 410) else 'failed'
    except Exception as exc:
        logger.warning('Alerte non envoyée à l\'appareil %s : %s', subscription.pk, exc)
        return 'failed'
    return 'ok'


def _record(subscription, outcome):
    """Note le résultat : un appareil disparu (404/410) est désactivé, un appareil qui échoue 5 fois aussi."""
    from .models import PushSubscription

    if outcome == 'ok':
        PushSubscription.objects.filter(pk=subscription.pk).update(failure_count=0, last_success_at=timezone.now())
    elif outcome == 'gone':
        PushSubscription.objects.filter(pk=subscription.pk).update(is_active=False)
    else:
        count = subscription.failure_count + 1
        PushSubscription.objects.filter(pk=subscription.pk).update(
            failure_count=count, is_active=count < MAX_FAILURES)


def send_one(subscription, payload):
    """True si le service d'alertes a accepté l'envoi."""
    outcome = _post(subscription, payload)
    _record(subscription, outcome)
    return outcome == 'ok'


# --- Notifications ordinaires ------------------------------------------------------------

def deliver_notification(notification_id):
    """Envoie une notification enregistrée à tous les appareils actifs de la personne."""
    from .models import Notification, PushSubscription

    note = Notification.objects.select_related('user').filter(pk=notification_id).first()
    if note is None or not enabled():
        return 0
    subscriptions = list(PushSubscription.objects.filter(user=note.user, is_active=True, kind='web'))
    if not subscriptions:
        return 0
    payload = payload_for(note)
    return sum(1 for sub in subscriptions if send_one(sub, payload))


def schedule_notification(notification):
    """Appelé quand une notification est enregistrée : l'envoi part une fois la base à jour."""
    if not enabled():
        return
    from .models import PushSubscription

    note_id, user_id = notification.pk, notification.user_id

    def after_commit():
        if PushSubscription.objects.filter(user_id=user_id, is_active=True, kind='web').exists():
            _run(deliver_notification, note_id)

    transaction.on_commit(after_commit)


# --- Annonces de l'administration --------------------------------------------------------

def in_quiet_hours(moment=None):
    local = (moment or timezone.now()).astimezone(LIBREVILLE).time()
    return local >= QUIET_START or local < QUIET_END


def next_morning(moment=None):
    """7 h à Libreville : l'heure où une annonce repoussée part."""
    local = (moment or timezone.now()).astimezone(LIBREVILLE)
    morning = datetime.combine(local.date(), QUIET_END, tzinfo=LIBREVILLE)
    if local.time() >= QUIET_END:
        morning += timedelta(days=1)
    return morning.astimezone(dt_timezone.utc)


def push_announcement(announcement_id):
    """Alerte les appareils des personnes qui ont reçu l'annonce. Renvoie (essayés, remis)."""
    from .models import Announcement, PushSubscription

    announcement = Announcement.objects.filter(pk=announcement_id).first()
    if announcement is None or announcement.push_done or not enabled():
        return 0, 0
    user_ids = announcement.notifications.values_list('user_id', flat=True)
    subscriptions = list(PushSubscription.objects.filter(user_id__in=list(user_ids), is_active=True, kind='web'))
    payload = payload_for_announcement(announcement)
    if subscriptions:
        vapid.get_keys()   # lues ici une fois (base), pas dans les envois parallèles
        # Le réseau part en parallèle ; la base n'est touchée que d'ici, un appareil après l'autre.
        with ThreadPoolExecutor(max_workers=8) as pool:
            outcomes = list(pool.map(lambda sub: _post(sub, payload), subscriptions))
        for sub, outcome in zip(subscriptions, outcomes):
            _record(sub, outcome)
        results = [outcome == 'ok' for outcome in outcomes]
    else:
        results = []
    Announcement.objects.filter(pk=announcement.pk).update(
        push_done=True, push_attempted=len(results), push_delivered=sum(results))
    return len(results), sum(results)


def schedule_announcement(announcement):
    """Envoie l'alerte tout de suite, ou la repousse à 7 h si c'est la nuit et que l'annonce n'est pas urgente."""
    from .models import Announcement

    if not announcement.send_push or not enabled():
        Announcement.objects.filter(pk=announcement.pk).update(push_done=True)
        return 'none'
    if in_quiet_hours() and not announcement.urgent:
        Announcement.objects.filter(pk=announcement.pk).update(push_after=next_morning())
        return 'deferred'
    announcement_id = announcement.pk
    transaction.on_commit(lambda: _run(push_announcement, announcement_id))
    return 'now'


def send_deferred_announcements():
    """Tâche automatique : envoie les alertes d'annonces repoussées dont l'heure est venue."""
    from .models import Announcement

    due = list(Announcement.objects.filter(push_done=False, push_after__isnull=False, push_after__lte=timezone.now()))
    sent = 0
    for announcement in due:
        _attempted, delivered = push_announcement(announcement.pk)
        sent += delivered
    return f'{len(due)} annonce(s) repoussée(s) envoyée(s), {sent} appareil(s) alerté(s)'
