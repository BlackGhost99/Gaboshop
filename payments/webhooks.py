import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.db import transaction
from django.utils import timezone
from .models import Payment
from notifications.service import NotificationService

logger = logging.getLogger(__name__)

@csrf_exempt
@require_POST
def airtel_money_webhook(request):
    """
    Webhook pour les notifications de paiement Airtel Money
    """
    try:
        # 1. Vérification de la signature (Sécurité)
        # Airtel envoie souvent une signature HMAC dans les headers
        payload = request.body
        
        # TODO: Configurer la clé secrète dans settings.py
        # secret = settings.AIRTEL_MONEY_SECRET
        # expected_signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        # if signature != expected_signature:
        #     return HttpResponseForbidden("Invalid signature")

        data = json.loads(payload)
        logger.info(f"📩 Webhook Airtel reçu: {data}")

        # 2. Extraction des données
        transaction_id = data.get('transaction_id')
        status = data.get('status_code')  # Ex: 'TS' (Transaction Success)
        
        # 3. Traitement
        with transaction.atomic():
            try:
                payment = Payment.objects.get(transaction_id=transaction_id)
            except Payment.DoesNotExist:
                logger.error(f"❌ Paiement non trouvé pour transaction {transaction_id}")
                return JsonResponse({'status': 'error', 'message': 'Payment not found'}, status=404)

            # Mise à jour du paiement
            payment.webhook_data = data
            
            if status == 'TS':  # Transaction Success
                if payment.status != 'success':
                    payment.status = 'success'
                    payment.operator_reference = data.get('airtel_money_id')
                    payment.completed_at = timezone.now()
                    payment.save(update_fields=['status', 'operator_reference', 'completed_at', 'webhook_data', 'updated_at'])

                    # Marquer la commande comme payée
                    payment.order.status = 'paid'
                    payment.order.save(update_fields=['status', 'updated_at'])
                    
                    # Notifier le succès (déclenche aussi les signals Order)
                    NotificationService.notify_payment_success(payment.order, payment)
                    
            elif status == 'TF':  # Transaction Failed
                payment.status = 'failed'
                payment.save(update_fields=['status', 'webhook_data', 'updated_at'])
                NotificationService.notify_payment_failed(payment.order)
                
            else:
                logger.warning(f"⚠️ Statut Airtel inconnu: {status}")

        return JsonResponse({'status': 'received'})

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"❌ Erreur Webhook Airtel: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
@require_POST
def moov_money_webhook(request):
    """
    Webhook pour les notifications de paiement Moov Money (Flooz)
    """
    try:
        payload = request.body
        data = json.loads(payload)
        logger.info(f"📩 Webhook Moov reçu: {data}")

        # Structure typique Moov (à adapter selon la doc officielle Gabon)
        ref_commande = data.get('reference')
        statut = data.get('status')  # 0 = Succès, autre = Erreur
        ref_operateur = data.get('payid')

        with transaction.atomic():
            try:
                # On cherche par ID de transaction interne
                payment = Payment.objects.get(transaction_id=ref_commande)
            except Payment.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Payment not found'}, status=404)

            payment.webhook_data = data

            if str(statut) == '0':  # Succès chez Moov
                if payment.status != 'success':
                    payment.status = 'success'
                    payment.operator_reference = ref_operateur
                    payment.completed_at = timezone.now()
                    payment.save(update_fields=['status', 'operator_reference', 'completed_at', 'webhook_data', 'updated_at'])

                    payment.order.status = 'paid'
                    payment.order.save(update_fields=['status', 'updated_at'])
                    NotificationService.notify_payment_success(payment.order, payment)
            else:
                payment.status = 'failed'
                payment.save(update_fields=['status', 'webhook_data', 'updated_at'])
                NotificationService.notify_payment_failed(payment.order)

        return JsonResponse({'status': 'received'})

    except Exception as e:
        logger.error(f"❌ Erreur Webhook Moov: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
