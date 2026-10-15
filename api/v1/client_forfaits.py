"""API des forfaits clients : catalogue, forfait en cours, souscription par Airtel Money / Moov Money."""
from datetime import timedelta

from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from payments.client_forfaits import activate_forfait, active_forfait, catalog, forfait_payload
from payments.models import Forfait, PaymentIntent, PaymentTransaction
from payments.utils import call_airtel_money_init, call_moov_money_init, payment_request_minutes


def _error(message, code=400, next_step=None):
    error = {'code': code, 'message': message}
    if next_step:
        error['next_step'] = next_step
    return Response({'success': False, 'error': error}, status=code)


class ForfaitCatalogView(APIView):
    """GET /api/v1/forfaits/ : forfaits proposés aux clients."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({'success': True, 'data': catalog()})


class MyForfaitView(APIView):
    """GET /api/v1/my-forfait/ : forfait en cours du client et dernier paiement en attente."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        current = active_forfait(request.user)
        pending = PaymentIntent.objects.filter(
            user=request.user, status='PENDING', metadata__purpose='client_forfait',
            created_at__gte=timezone.now() - timedelta(hours=1),
        ).order_by('-created_at').first()
        return Response({'success': True, 'data': {
            'forfait': forfait_payload(current.forfait) if current else None,
            'expires_at': current.expiration_date if current else None,
            'pending_payment': {'reference': pending.reference, 'amount': pending.amount} if pending else None,
        }})


class ForfaitSubscribeView(APIView):
    """POST /api/v1/my-forfait/subscribe/ {forfait_id, operator: airtel|moov, phone_number}

    Envoie la demande de paiement sur le téléphone du client. Le forfait s'active quand SingPay confirme le paiement.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if not request.user.is_client():
            return _error('Les forfaits sont réservés aux comptes clients.', 403)
        forfait = Forfait.objects.filter(id=request.data.get('forfait_id'), is_active=True).first()
        if forfait is None:
            return _error('Forfait introuvable.', 404)
        amount = int(forfait.monthly_price or 0)
        if amount <= 0:
            current = activate_forfait(request.user, forfait)
            return Response({'success': True, 'message': f'Forfait « {forfait.name} » activé.',
                             'data': {'expires_at': current.expiration_date}})

        operator = str(request.data.get('operator') or '').lower()
        phone = str(request.data.get('phone_number') or request.user.phone or '').strip().replace(' ', '')
        if operator not in ('airtel', 'moov'):
            return _error('Choisissez Airtel Money ou Moov Money.')
        if not phone:
            return _error('Indiquez le numéro Mobile Money qui va payer.')
        if phone.startswith('0'):
            phone = '+241' + phone[1:]

        intent = PaymentIntent.objects.create(
            user=request.user, amount=amount, currency='XAF', provider='singpay',
            expires_at=timezone.now() + timedelta(minutes=payment_request_minutes()),
            metadata={'purpose': 'client_forfait', 'forfait_id': forfait.id, 'operator': operator},
        )
        init = call_airtel_money_init if operator == 'airtel' else call_moov_money_init
        response = init(phone=phone, amount=intent.amount, reference=intent.reference, metadata=intent.metadata)
        intent.raw_response = response
        intent.status = 'PENDING' if isinstance(response, dict) and not response.get('error') else 'FAILED'
        intent.save()
        PaymentTransaction.objects.create(intent=intent, status=intent.status, raw_response=response)
        if intent.status == 'FAILED':
            return _error('La demande de paiement n’a pas pu être envoyée.', 502,
                          'Vérifiez le numéro et le solde, puis réessayez dans quelques minutes.')
        return Response({'success': True,
                         'message': f'Validez le paiement de {amount} FCFA sur votre téléphone avec votre code secret.',
                         'data': {'reference': intent.reference, 'amount': amount}}, status=status.HTTP_201_CREATED)
