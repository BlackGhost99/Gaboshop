"""Services de simulation pour le développement et tests
"""
import logging
from django.utils import timezone
from payments.models import Payment

logger = logging.getLogger(__name__)

class MockPaymentService:
    """Service de simulation pour les paiements pendant le développement"""
    
    @staticmethod
    def simulate_successful_payment(order):
        """
        Simuler un paiement réussi (pour tests)
        """
        try:
            from payments.services import PaymentService
            
            # Créer un paiement simulé
            payment = Payment.objects.create(
                order=order,
                payment_method='mobile_money',
                amount=order.total_amount,
                status='completed',
                transaction_id=f"MOCK_SUCCESS_{order.id}_{int(timezone.now().timestamp())}",
                operator_reference="MOCK_REF_SUCCESS",
                completed_at=timezone.now()
            )
            
            # Confirmer le paiement
            PaymentService.confirm_payment(payment.transaction_id, 'SUCCESS')
            
            logger.info(f"🎯 Paiement simulé réussi pour #{order.order_number}")
            
            return payment
            
        except Exception as e:
            logger.error(f"❌ Erreur simulation paiement: {e}")
            raise
    
    @staticmethod
    def simulate_failed_payment(order):
        """
        Simuler un paiement échoué (pour tests)
        """
        try:
            payment = Payment.objects.create(
                order=order,
                payment_method='mobile_money',
                amount=order.total_amount,
                status='failed',
                transaction_id=f"MOCK_FAILED_{order.id}_{int(timezone.now().timestamp())}",
                operator_reference="MOCK_REF_FAILED"
            )
            
            logger.info(f"🎯 Paiement simulé échoué pour #{order.order_number}")
            
            return payment
            
        except Exception as e:
            logger.error(f"❌ Erreur simulation échec paiement: {e}")
            raise
