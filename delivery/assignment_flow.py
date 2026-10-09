import logging
from datetime import timedelta
from decimal import Decimal

from celery import current_app
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from delivery.models import Delivery
from delivery.utils import haversine_distance
from notifications.service import NotificationService
from users.models import LivreurProfile
from api.models import SystemSettings

logger = logging.getLogger(__name__)

# Valeurs par défaut ; les vraies valeurs se règlent dans l'espace admin (Réglages > Livraison).
ASSIGNMENT_TIMEOUT_MINUTES = 10
BROADCAST_AFTER_MINUTES = 40
RETRY_DELAY_MINUTES = 5


def _setting(name, default):
    from api.models import SystemSettings
    try:
        return int(SystemSettings.current(name, default) or default)
    except (TypeError, ValueError):
        return default


def assignment_timeout_minutes():
    return _setting('assignment_timeout_minutes', ASSIGNMENT_TIMEOUT_MINUTES)

# Livraisons en cours (comptées pour la limite par livreur réglée dans l'admin)
BUSY_STATUSES = ('assigned', 'accepted_by_driver', 'accepted', 'picked_up', 'in_delivery', 'in_transit')

ACCEPTED_STATUSES = {
    'accepted',
    'accepted_by_driver',
    'picked_up',
    'in_transit',
    'delivered',
}


def start_delivery_assignment(order):
    """Start or resume the auto-assignment flow for an order."""
    if not order or order.status not in ['ready', 'assigned']:
        return None
    from payments.direct_service import can_dispatch, store_delivers
    if store_delivers(order) and getattr(order, 'payment_arrangement', None) is not None \
            and order.payment_arrangement.delivery_method == 'store':
        # Option « tout au commerce » : le commerce livre lui-même, aucun livreur Gaboshop n'est appelé.
        return None
    if not can_dispatch(order):
        logger.warning('Assignment blocked: required payment is not confirmed for order %s', order.pk)
        return None

    auto_assignment_enabled = _default_auto_assignment_enabled()
    delivery, _ = Delivery.objects.get_or_create(
        order=order,
        defaults={
            'pickup_address': order.store.address,
            'pickup_lat': order.store.latitude,
            'pickup_lng': order.store.longitude,
            'delivery_address': order.delivery_address,
            'delivery_fee': order.delivery_fee,
            'city': order.city,
            'status': 'waiting',
            'auto_assignment_enabled': auto_assignment_enabled,
        },
    )

    if not delivery.auto_assignment_enabled:
        return delivery

    # If already accepted or completed, do not reassign.
    if delivery.status in ACCEPTED_STATUSES or delivery.accepted_at:
        return delivery

    now = timezone.now()
    if delivery.delivery_agent_id and delivery.status == 'assigned':
        with transaction.atomic():
            locked = Delivery.objects.select_for_update().get(id=delivery.id)
            if not locked.assignment_started_at:
                locked.assignment_started_at = now
            if not locked.assigned_at:
                locked.assigned_at = now
            timeout_minutes = _effective_timeout_minutes(locked)
            if locked.assignment_round == 0:
                locked.assignment_round = 1
            locked.save(update_fields=['assignment_started_at', 'assigned_at', 'assignment_round', 'assignment_timeout_minutes'])

            assignment_round = locked.assignment_round
            delivery_id = locked.id

            transaction.on_commit(
                lambda: _enqueue_timeout_task(
                    delivery_id, assignment_round, timeout_minutes
                )
            )
            if assignment_round == 1:
                delay_seconds = _broadcast_delay_seconds(locked.assignment_started_at, now)
                transaction.on_commit(
                    lambda: _enqueue_broadcast_task(delivery_id, delay_seconds)
                )
        return delivery

    return assign_next_driver(delivery.id, reason='start')


def assign_next_driver(delivery_id, reason='timeout', force=False):
    """Assign the next available driver by distance, or queue retry/broadcast."""
    now = timezone.now()
    try:
        with transaction.atomic():
            delivery = (
                Delivery.objects.select_for_update()
                .select_related('order', 'order__store')
                .get(id=delivery_id)
            )

            if not force and (delivery.status in ACCEPTED_STATUSES or delivery.accepted_at):
                return delivery

            if delivery.is_open_to_all:
                return delivery

            if not delivery.order:
                return None
            if delivery.order.status not in ['ready', 'assigned']:
                if not force:
                    return None
                delivery.order.status = 'ready'
                delivery.order.save(update_fields=['status'])

            if not delivery.auto_assignment_enabled:
                _clear_assignment(delivery)
                return delivery

            if not delivery.assignment_started_at:
                delivery.assignment_started_at = now

            if _should_broadcast(delivery.assignment_started_at, now):
                return open_delivery_to_all(delivery, reason='timeout')

            attempts = _normalize_attempts(delivery)
            if delivery.delivery_agent_id:
                _append_attempt(attempts, delivery.delivery_agent_id)

            candidate, distance_km = _select_candidate(delivery.order, attempts)
            if not candidate:
                should_reset = _has_any_candidates(delivery.order)
                delivery.assignment_attempts = [] if should_reset else attempts
                _clear_assignment(delivery)
                if delivery.assignment_round == 0 and delivery.assignment_started_at:
                    broadcast_delay = _broadcast_delay_seconds(delivery.assignment_started_at, now)
                    transaction.on_commit(
                        lambda: _enqueue_broadcast_task(delivery.id, broadcast_delay)
                    )
                if delivery.assignment_started_at and not _should_broadcast(
                    delivery.assignment_started_at, now
                ):
                    transaction.on_commit(
                        lambda: _enqueue_retry_task(delivery.id)
                    )
                return None

            delivery.delivery_agent = candidate.user
            delivery.status = 'assigned'
            delivery.is_auto_assigned = True
            delivery.assigned_at = now
            delivery.accepted_at = None
            delivery.distance_to_store = distance_km
            delivery.is_open_to_all = False
            delivery.opened_at = None

            timeout_minutes = _effective_timeout_minutes(delivery)
            delivery.assignment_round = (delivery.assignment_round or 0) + 1
            _append_attempt(attempts, candidate.user_id)
            delivery.assignment_attempts = attempts

            if delivery.order and delivery.order.delivery_fee:
                from payments.direct_service import is_manual_order
                delivery.agent_commission = delivery.order.delivery_fee if is_manual_order(delivery.order) else SystemSettings.courier_share(delivery.order.delivery_fee)

            delivery.save()

            if delivery.order.status != 'assigned':
                delivery.order.status = 'assigned'
                delivery.order.save(update_fields=['status'])

            try:
                NotificationService.notify_delivery_assigned(delivery)
            except Exception:
                logger.exception('Failed to notify delivery agent')

            assignment_round = delivery.assignment_round
            delivery_id = delivery.id
            started_at = delivery.assignment_started_at

            transaction.on_commit(
                lambda: _enqueue_timeout_task(
                    delivery_id, assignment_round, timeout_minutes
                )
            )
            if assignment_round == 1 and started_at:
                broadcast_delay = _broadcast_delay_seconds(started_at, now)
                transaction.on_commit(
                    lambda: _enqueue_broadcast_task(delivery_id, broadcast_delay)
                )

            logger.info(
                "Assigned delivery %s to driver %s (reason=%s)",
                delivery.id,
                candidate.user_id,
                reason,
            )

            return delivery
    except Delivery.DoesNotExist:
        return None


def handle_assignment_timeout(delivery_id, assignment_round):
    """Handle assignment timeout and reassign when needed."""
    delivery = Delivery.objects.filter(id=delivery_id).first()
    if not delivery:
        return None

    if delivery.assignment_round != assignment_round:
        return None

    if delivery.status in ACCEPTED_STATUSES or delivery.accepted_at:
        return delivery

    if delivery.is_open_to_all:
        return delivery

    now = timezone.now()
    timeout_minutes = _effective_timeout_minutes(delivery)
    if delivery.assigned_at and delivery.assigned_at + timedelta(minutes=timeout_minutes) > now:
        return delivery

    return assign_next_driver(delivery_id, reason='timeout')


def broadcast_if_unaccepted(delivery_id):
    """Open a delivery to all drivers if still unaccepted after the window."""
    try:
        with transaction.atomic():
            delivery = (
                Delivery.objects.select_for_update()
                .select_related('order')
                .get(id=delivery_id)
            )

            if delivery.status in ACCEPTED_STATUSES or delivery.accepted_at:
                return delivery

            if delivery.is_open_to_all:
                return delivery

            now = timezone.now()
            if delivery.assignment_started_at and not _should_broadcast(
                delivery.assignment_started_at, now
            ):
                return delivery

            return open_delivery_to_all(delivery, reason='broadcast')
    except Delivery.DoesNotExist:
        return None


def open_delivery_to_all(delivery, reason='broadcast'):
    """Make delivery visible to all drivers for fast claim."""
    now = timezone.now()
    delivery.delivery_agent = None
    delivery.status = 'waiting'
    delivery.is_auto_assigned = False
    delivery.assigned_at = None
    delivery.accepted_at = None
    delivery.is_open_to_all = True
    delivery.opened_at = now
    delivery.save()

    if delivery.order and delivery.order.status != 'ready':
        delivery.order.status = 'ready'
        delivery.order.save(update_fields=['status'])

    logger.info("Delivery %s opened to all drivers (reason=%s)", delivery.id, reason)
    return delivery


def _clear_assignment(delivery):
    delivery.delivery_agent = None
    delivery.status = 'waiting'
    delivery.is_auto_assigned = False
    delivery.assigned_at = None
    delivery.accepted_at = None
    delivery.save()

    if delivery.order and delivery.order.status != 'ready':
        delivery.order.status = 'ready'
        delivery.order.save(update_fields=['status'])


def _normalize_attempts(delivery):
    attempts = delivery.assignment_attempts
    if not isinstance(attempts, list):
        return []
    cleaned = []
    for item in attempts:
        try:
            cleaned.append(int(item))
        except (TypeError, ValueError):
            continue
    return cleaned


def _append_attempt(attempts, user_id):
    if user_id and user_id not in attempts:
        attempts.append(user_id)


def _effective_timeout_minutes(delivery):
    timeout = assignment_timeout_minutes()
    delivery.assignment_timeout_minutes = timeout
    return timeout


def _select_candidate(order, exclude_ids):
    ranked = _rank_candidates(order, exclude_ids, same_city_only=True)
    if not ranked:
        ranked = _rank_candidates(order, exclude_ids, same_city_only=False)
    if not ranked:
        return None, None
    from payments.direct_service import can_courier_accept_collection
    for profile, distance in ranked:
        if can_courier_accept_collection(profile.user, order):
            return profile, distance
    return None, None


def _rank_candidates(order, exclude_ids, same_city_only=True):
    qs = LivreurProfile.objects.filter(
        disponible=True,
        user__is_available=True,
        user__user_type='delivery_agent',
    ).select_related('user')

    if same_city_only and order.city:
        qs = qs.filter(user__city=order.city)

    if exclude_ids:
        qs = qs.exclude(user_id__in=exclude_ids)

    # Réglage admin : un livreur déjà chargé de N livraisons en cours n'en reçoit pas d'autre.
    from api.models import SystemSettings
    max_active = int(SystemSettings.current('max_orders_per_delivery', 3) or 3)
    busy = (
        Delivery.objects.filter(status__in=BUSY_STATUSES, delivery_agent__isnull=False)
        .values('delivery_agent').annotate(n=Count('id')).filter(n__gte=max_active)
        .values_list('delivery_agent', flat=True)
    )
    qs = qs.exclude(user_id__in=list(busy))

    qs = qs.order_by('-documents_verifies', 'last_position_update', 'id')
    profiles = list(qs)
    if not profiles:
        return []

    store_lat = order.store.latitude
    store_lng = order.store.longitude
    if not (store_lat and store_lng):
        return [(profile, None) for profile in profiles]

    with_distance = []
    without_distance = []
    for profile in profiles:
        distance = haversine_distance(
            store_lat, store_lng, profile.position_lat, profile.position_lng
        )
        if distance is None:
            without_distance.append((profile, None))
        else:
            with_distance.append((distance, profile))

    with_distance.sort(key=lambda x: x[0])
    ranked = [(profile, distance) for distance, profile in with_distance]
    ranked.extend(without_distance)
    return ranked


def _default_auto_assignment_enabled():
    try:
        from api.models import SystemSettings
        settings = SystemSettings.get_settings()
        return bool(settings.auto_assign_delivery)
    except Exception:
        return True


def _has_any_candidates(order):
    if _rank_candidates(order, [], same_city_only=True):
        return True
    if _rank_candidates(order, [], same_city_only=False):
        return True
    return False


def _should_broadcast(started_at, now):
    if not started_at:
        return False
    return now - started_at >= timedelta(minutes=_setting('broadcast_after_minutes', BROADCAST_AFTER_MINUTES))


def _broadcast_delay_seconds(started_at, now):
    delay = (started_at + timedelta(minutes=_setting('broadcast_after_minutes', BROADCAST_AFTER_MINUTES)) - now).total_seconds()
    return max(0, int(delay))


def _enqueue_timeout_task(delivery_id, assignment_round, timeout_minutes):
    current_app.send_task(
        'delivery.tasks.assignment_timeout_check',
        args=[delivery_id, assignment_round],
        countdown=int(timeout_minutes * 60),
    )


def _enqueue_broadcast_task(delivery_id, delay_seconds):
    current_app.send_task(
        'delivery.tasks.broadcast_delivery_if_unaccepted',
        args=[delivery_id],
        countdown=int(delay_seconds),
    )


def _enqueue_retry_task(delivery_id):
    current_app.send_task(
        'delivery.tasks.retry_delivery_assignment',
        args=[delivery_id],
        countdown=int(_setting('assignment_retry_minutes', RETRY_DELAY_MINUTES) * 60),
    )


def enqueue_assignment_tasks(delivery_id, assignment_round, timeout_minutes, started_at=None):
    _enqueue_timeout_task(delivery_id, assignment_round, timeout_minutes)
    if assignment_round == 1 and started_at:
        delay_seconds = _broadcast_delay_seconds(started_at, timezone.now())
        _enqueue_broadcast_task(delivery_id, delay_seconds)
