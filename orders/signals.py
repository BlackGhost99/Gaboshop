"""
Signals pour automatisation du workflow GABOSHOP
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from decimal import Decimal
from .models import Order
from payments.models import Payment, Commission
from delivery.models import Delivery
from notifications.service import NotificationService


@receiver(pre_save, sender=Order)
def track_order_status(sender, instance, **kwargs):
	"""
	Capture l'ancien statut avant sauvegarde pour détecter les changements
	"""
	if instance.pk:
		try:
			old_instance = Order.objects.get(pk=instance.pk)
			instance._old_status = old_instance.status
		except Order.DoesNotExist:
			pass


@receiver(post_save, sender=Order)
def handle_order_status_change(sender, instance, created, **kwargs):
	"""
	Gère les changements de statut de commande
	"""
	order = instance
	
	# 1. Notifications et Actions à la création
	if created:
		# Créer une livraison (en attente)
		Delivery.objects.get_or_create(
			order=order,
			defaults={
				'pickup_address': order.store.address,
				'pickup_lat': order.store.latitude,
				'pickup_lng': order.store.longitude,
				'delivery_address': order.delivery_address,
				'delivery_fee': order.delivery_fee,
				'agent_commission': Decimal(str(order.delivery_fee)) * Decimal('0.6'),  # 60% pour le livreur
				'status': 'waiting'
			}
		)
		# Notifier le magasin
		NotificationService.notify_new_order(order)
	
	# 2. Notifications sur changement de statut
	if hasattr(order, '_old_status') and order._old_status != order.status:
		# Notifier le client
		NotificationService.notify_order_status_update(order, order._old_status, order.status)
	
	# 3. Créer Commission quand commande est payée
	if order.status == 'paid' and not hasattr(order, 'commission'):
		Commission.objects.create(
			order=order,
			store=order.store,
			order_amount=order.items_total,
			commission_rate=order.commission_rate,
			commission_amount=order.commission_amount,
			delivery_fee_share=order.delivery_fee * Decimal('0.4'),  # 40% des frais de livraison pour GABOSHOP
		)
		print(f"✅ Commission créée pour commande {order.order_number}: {order.commission_amount} FCFA")
	
	# 4. Confirmer la commande après paiement
	if order.status == 'paid' and not order.confirmed_at:
		order.status = 'confirmed'
		order.confirmed_at = timezone.now()
		order.save(update_fields=['status', 'confirmed_at'])
		print(f"✅ Commande {order.order_number} confirmée")


@receiver(post_save, sender=Payment)
def handle_payment_success(sender, instance, created, **kwargs):
	"""
	Gère le succès d'un paiement
	"""
	payment = instance
	
	# Quand le paiement passe en SUCCESS
	if payment.status == 'success' and payment.order.status != 'paid':
		# 1. Marquer la date de complétion
		if not payment.completed_at:
			payment.completed_at = timezone.now()
			payment.save(update_fields=['completed_at'])
		
		# 2. Changer le statut de la commande
		order = payment.order
		order.status = 'paid'
		order.save(update_fields=['status'])
		
		print(f"✅ Paiement validé pour commande {order.order_number}")
		
		# 3. Déclencher l'assignation du livreur (via Celery task)
		# Import ici pour éviter circular import
		try:
			from delivery.tasks import assign_nearest_delivery_agent
			assign_nearest_delivery_agent.delay(order.id)
			print(f"🚀 Task d'assignation livreur lancée pour {order.order_number}")
		except ImportError:
			# Si Celery n'est pas encore configuré, on passe
			print(f"⚠️ Celery task non disponible pour {order.order_number}")
