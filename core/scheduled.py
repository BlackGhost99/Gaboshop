"""Tâches automatiques de Gaboshop, sans worker Celery.

Render gratuit n'a pas de worker : un minuteur (GitHub Actions) appelle POST /api/v1/internal/tick/
toutes les quelques minutes, et chaque passage lance les tâches dont l'heure est venue.
Chaque tâche est « réservée » en base avant de tourner : deux appels simultanés ne la lancent pas deux fois.
"""
import logging
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

logger = logging.getLogger(__name__)

# Paiements en ligne : on interroge SingPay après 2 min, et plus du tout au-delà de 24 h.
PAYMENT_CHECK_AFTER = timedelta(minutes=2)
PAYMENT_CHECK_UNTIL = timedelta(hours=24)
PAYMENT_CHECKS_PER_TICK = 20


def _claim(name, every):
	"""Réserve la tâche si son dernier passage date d'au moins `every`. Renvoie True si on doit la lancer."""
	from core.models import ScheduledTaskRun
	now = timezone.now()
	ScheduledTaskRun.objects.get_or_create(name=name)
	return bool(
		ScheduledTaskRun.objects.filter(name=name)
		.filter(Q(last_run_at__isnull=True) | Q(last_run_at__lte=now - every))
		.update(last_run_at=now)
	)


def _record(name, ok, message):
	from core.models import ScheduledTaskRun
	ScheduledTaskRun.objects.filter(name=name).update(last_ok=ok, last_message=str(message)[:2000])


def advance_deliveries():
	"""Relance l'attribution des livreurs : commandes prêtes sans livreur, délais de réponse dépassés, diffusion à tous."""
	from delivery.assignment_flow import (
		ACCEPTED_STATUSES, _should_broadcast, assignment_timeout_minutes, broadcast_if_unaccepted,
		handle_assignment_timeout, start_delivery_assignment,
	)
	from delivery.models import Delivery
	from orders.models import Order

	now = timezone.now()
	started = timed_out = broadcast = 0
	waiting = Order.objects.filter(status='ready').filter(
		Q(delivery__isnull=True) | Q(delivery__delivery_agent__isnull=True, delivery__is_open_to_all=False)
	).select_related('store')
	for order in waiting:
		try:
			if start_delivery_assignment(order) is not None:
				started += 1
		except Exception:
			logger.exception('Attribution impossible pour la commande %s', order.order_number)

	pending = Delivery.objects.filter(
		auto_assignment_enabled=True, accepted_at__isnull=True, is_open_to_all=False,
	).exclude(status__in=ACCEPTED_STATUSES)
	timeout = timedelta(minutes=assignment_timeout_minutes())
	for delivery in pending.filter(status='assigned', assigned_at__lte=now - timeout):
		try:
			handle_assignment_timeout(delivery.id, delivery.assignment_round)
			timed_out += 1
		except Exception:
			logger.exception('Délai de réponse du livreur non traité (livraison %s)', delivery.id)
	for delivery in pending.filter(assignment_started_at__isnull=False):
		if _should_broadcast(delivery.assignment_started_at, now):
			try:
				broadcast_if_unaccepted(delivery.id)
				broadcast += 1
			except Exception:
				logger.exception('Diffusion de la course impossible (livraison %s)', delivery.id)
	return f'{started} attribution(s) relancée(s), {timed_out} délai(s) dépassé(s), {broadcast} course(s) ouvertes à tous'


def check_online_payments():
	"""Demande à SingPay le résultat des paiements en ligne restés en attente (le client a pu valider sans retour)."""
	from payments.models import Payment
	from payments.online_verification import verify_order_payment

	now = timezone.now()
	payments = Payment.objects.filter(
		status__in=('pending', 'processing'), payment_method__in=('airtel_money', 'moov_money'),
		created_at__lte=now - PAYMENT_CHECK_AFTER, created_at__gte=now - PAYMENT_CHECK_UNTIL,
	).select_related('order').order_by('updated_at')[:PAYMENT_CHECKS_PER_TICK]
	results = {}
	for payment in payments:
		try:
			outcome = verify_order_payment(payment, 'vérification automatique')
		except Exception:
			logger.exception('Vérification SingPay impossible pour le paiement %s', payment.pk)
			outcome = 'erreur'
		results[outcome] = results.get(outcome, 0) + 1
	return ', '.join(f'{n} {k}' for k, n in results.items()) or 'aucun paiement en attente'


def cancel_abandoned_orders():
	"""Annule les commandes jamais payées ni prises en charge après le délai réglé dans l'admin, et remet le stock."""
	from api.models import SystemSettings
	from notifications.service import NotificationService
	from orders.models import Order
	from orders.services import OrderService
	from payments.online_verification import verify_order_payment

	hours = int(SystemSettings.current('cart_validity_hours', 24) or 24)
	limit = timezone.now() - timedelta(hours=hours)
	orders = Order.objects.filter(status__in=('created', 'pending_payment'), created_at__lt=limit).exclude(
		# Un paiement Mobile Money déclaré au commerce attend sa vérification : on ne touche à rien.
		payment_arrangement__obligations__receipts__status__in=('pending', 'confirmed'),
	).distinct()
	cancelled = 0
	for order in orders:
		payment = getattr(order, 'payment', None)
		try:
			if payment is not None and payment.status != 'success' and payment.payment_method in ('airtel_money', 'moov_money'):
				verify_order_payment(payment, 'avant annulation automatique')
				payment.refresh_from_db()
			if payment is not None and payment.status == 'success':
				continue
			order.refresh_from_db()
			if order.status not in ('created', 'pending_payment'):
				continue
			old_status = order.status
			OrderService.cancel_order(order, reason=f'non payée ni prise en charge après {hours} h')
			cancelled += 1
			try:
				NotificationService.notify_order_status_update(order, old_status, 'cancelled')
			except Exception:
				logger.exception('Notification d’annulation impossible (%s)', order.order_number)
		except Exception:
			logger.exception('Annulation automatique impossible pour la commande %s', order.order_number)
	return f'{cancelled} commande(s) abandonnée(s) annulée(s), stock remis en vente'


def expire_subscriptions():
	"""Passe en « expiré » les abonnements de commerce dont la date de fin est passée."""
	from payments.models import StoreSubscription
	today = timezone.now().date()
	expired = StoreSubscription.objects.filter(status='active', end_date__lt=today)
	count = 0
	for subscription in expired:
		subscription.status = 'expired'
		subscription.save()
		count += 1
	return f'{count} abonnement(s) expiré(s)'


JOBS = (
	('livraisons', timedelta(minutes=2), advance_deliveries),
	('paiements_en_ligne', timedelta(minutes=2), check_online_payments),
	('commandes_abandonnees', timedelta(hours=1), cancel_abandoned_orders),
	('abonnements_expires', timedelta(hours=12), expire_subscriptions),
)


def run_due_jobs():
	"""Lance chaque tâche dont l'heure est venue. Renvoie {nom: résultat} pour les tâches lancées."""
	done = {}
	for name, every, job in JOBS:
		if not _claim(name, every):
			continue
		try:
			message, ok = job(), True
		except Exception as exc:
			logger.exception('Tâche automatique %s en échec', name)
			message, ok = f'Échec : {exc}', False
		_record(name, ok, message)
		done[name] = message
	return done
