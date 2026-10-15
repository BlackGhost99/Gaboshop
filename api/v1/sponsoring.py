"""API de la mise en avant payante côté commerce : offre, mes mises en avant, achat par Mobile Money."""
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from payments.online_verification import refresh_pending_intents
from payments.sponsoring import SponsoringError, mine, offer, request_purchase
from stores.models import Store


def _error(message, code=400, next_step=None):
    error = {'code': code, 'message': message}
    if next_step:
        error['next_step'] = next_step
    return Response({'success': False, 'error': error}, status=code)


class StoreSponsoringView(APIView):
    """GET /api/v1/store/sponsoring/ : offre (ouverte ou bientôt disponible), prix, mes mises en avant.
    POST {target: product|store, product_id?, weeks, operator: airtel|moov, phone_number}."""
    permission_classes = [permissions.IsAuthenticated]

    def _store(self, request):
        return Store.objects.filter(manager=request.user).first()

    def get(self, request):
        store = self._store(request)
        if store is None:
            return _error('Réservé aux commerces.', 403)
        refresh_pending_intents(request.user)
        products = list(store.products.filter(is_available=True, market_type__in=['b2c', 'both'])
                        .order_by('name').values('id', 'name')[:200])
        return Response({'success': True, 'data': {**offer(), 'mine': mine(store), 'products': products}})

    def post(self, request):
        store = self._store(request)
        if store is None:
            return _error('Réservé aux commerces.', 403)
        try:
            sponsorship, intent = request_purchase(store, request.user, request.data)
        except SponsoringError as exc:
            return _error(exc.message, exc.code, exc.next_step)
        if intent is None:
            return Response({'success': True, 'message': 'Mise en avant activée.',
                             'data': {'id': sponsorship.id, 'end_date': sponsorship.end_date}},
                            status=status.HTTP_201_CREATED)
        return Response({'success': True,
                         'message': f'Validez le paiement de {intent.amount} FCFA sur votre téléphone avec votre code secret. '
                                    'La mise en avant démarre dès que le paiement est confirmé.',
                         'data': {'id': sponsorship.id, 'reference': intent.reference, 'amount': intent.amount}},
                        status=status.HTTP_201_CREATED)
