"""Exposition en lecture seule des droits équipe du gérant B2C."""
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from payments.staff_entitlements import get_b2c_staff_policy
from stores.models import Store


class StoreTeamPolicyView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        if not user.is_store_manager():
            return Response({'success': False, 'detail': 'Réservé au gérant.'}, status=status.HTTP_403_FORBIDDEN)
        store = Store.objects.filter(manager=user, is_active=True).first()
        if not store:
            return Response({'success': False, 'detail': 'Aucune boutique active.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({
            'success': True, 'data': get_b2c_staff_policy(store),
        })
