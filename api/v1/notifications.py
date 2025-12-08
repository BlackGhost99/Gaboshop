from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
import logging

from notifications.models import Notification
from notifications.serializers import NotificationSerializer

logger = logging.getLogger(__name__)


class NotificationListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            qs = Notification.objects.filter(user=request.user).order_by('-created_at')
            serializer = NotificationSerializer(qs, many=True)
            return Response({
                'success': True,
                'data': serializer.data
            })
        except Exception as e:
            logger.error(f"Error fetching notifications for user {request.user.id}: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': {
                    'code': status.HTTP_500_INTERNAL_SERVER_ERROR,
                    'message': 'Erreur lors de la récupération des notifications',
                    'details': str(e) if request.user.is_staff else None
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class NotificationMarkAllReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'success': True, 'message': 'Notifications marquées lues'})


class NotificationMarkReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            notif = Notification.objects.get(id=pk, user=request.user)
            notif.is_read = True
            notif.save(update_fields=['is_read'])
            return Response({'success': True})
        except Notification.DoesNotExist:
            return Response({
                'success': False,
                'error': {
                    'code': status.HTTP_404_NOT_FOUND,
                    'message': 'Notification introuvable'
                }
            }, status=status.HTTP_404_NOT_FOUND)


class NotificationDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        try:
            notif = Notification.objects.get(id=pk, user=request.user)
            notif.delete()
            return Response({'success': True, 'message': 'Notification supprimée'})
        except Notification.DoesNotExist:
            return Response({
                'success': False,
                'error': {
                    'code': status.HTTP_404_NOT_FOUND,
                    'message': 'Notification introuvable'
                }
            }, status=status.HTTP_404_NOT_FOUND)
