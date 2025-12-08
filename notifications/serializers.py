from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'body', 'notif_type', 'is_read', 'created_at',
            'order', 'delivery', 'metadata', 'user', 'user_name'
        ]
        read_only_fields = ['id', 'created_at', 'user', 'user_name']

    def get_user_name(self, obj):
        """Obtenir le nom complet de l'utilisateur de manière sécurisée"""
        if not obj.user:
            return "Système"
        try:
            if hasattr(obj.user, 'get_full_name'):
                full_name = obj.user.get_full_name()
                return full_name if full_name else obj.user.email
            return obj.user.email
        except Exception:
            return "Utilisateur"

