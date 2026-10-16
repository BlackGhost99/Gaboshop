"""Carte de livraison en direct.

GET  /orders/<id>/tracking/ : commerce, point d'arrivée, livreur (client de la commande, commerce, livreur, admin).
POST /dashboard/delivery/<id>/position/ : le livreur de la course envoie sa position {latitude, longitude}.
"""
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from delivery.models import Delivery
from delivery.tracking import can_read, record_courier_position, tracking_payload
from orders.models import Order


def _error(message, next_step='', code=status.HTTP_400_BAD_REQUEST):
    return Response({'success': False, 'error': {'message': message, 'reason': '', 'next_step': next_step}}, status=code)


class OrderTrackingView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, order_id):
        order = (Order.objects.select_related('store', 'landmark', 'neighborhood', 'delivery__delivery_agent')
                 .filter(pk=order_id).first())
        if order is None or not can_read(request.user, order):
            return _error('Commande introuvable.', code=status.HTTP_404_NOT_FOUND)
        return Response({'success': True, 'data': tracking_payload(order, request.user)})


class CourierPositionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, delivery_id):
        delivery = Delivery.objects.filter(pk=delivery_id, delivery_agent=request.user).first()
        if delivery is None:
            return _error('Livraison introuvable.', code=status.HTTP_404_NOT_FOUND)
        try:
            record_courier_position(delivery, request.data.get('latitude'), request.data.get('longitude'))
        except ValueError as exc:
            return _error(str(exc), 'Activez la localisation du téléphone pour être suivi par le client.')
        return Response({'success': True})
