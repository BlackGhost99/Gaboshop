from rest_framework import serializers
from .models import Announcement, Notification
from .announcements import AUDIENCE_LABELS


class NotificationSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    order_number = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'body', 'notif_type', 'is_read', 'created_at', 'read_at',
            'order', 'order_number', 'delivery', 'metadata', 'user', 'user_name', 'link', 'action_label', 'announcement',
        ]
        read_only_fields = ['id', 'created_at', 'user', 'user_name']

    def get_order_number(self, obj):
        """Le numéro que le client connaît (CMD…), pas l'identifiant interne."""
        order = getattr(obj, 'order', None)
        return getattr(order, 'order_number', None)

    def get_user_name(self, obj):
        """Obtenir le nom complet de l'utilisateur de manière sécurisée"""
        user = getattr(obj, "user", None)
        if not user:
            return "Systeme"
        try:
            if hasattr(user, 'get_full_name'):
                full_name = user.get_full_name()
                return full_name if full_name else (getattr(user, "email", "") or "Utilisateur")
            return getattr(user, "email", "") or "Utilisateur"
        except Exception:
            return "Utilisateur"


class AnnouncementSerializer(serializers.ModelSerializer):
    """Une annonce vue par l'administration : qui l'a reçue, qui l'a lue, combien d'appareils alertés."""
    audience_label = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    read_count = serializers.SerializerMethodField()
    push_state = serializers.SerializerMethodField()

    class Meta:
        model = Announcement
        fields = [
            'id', 'title', 'body', 'audience', 'audience_label', 'link', 'action_label', 'send_push', 'urgent',
            'created_at', 'sent_at', 'created_by_name', 'recipients_count', 'read_count',
            'push_state', 'push_after', 'push_attempted', 'push_delivered',
        ]

    def get_audience_label(self, obj):
        return AUDIENCE_LABELS.get(obj.audience, obj.audience)

    def get_created_by_name(self, obj):
        user = obj.created_by
        if not user:
            return ''
        return (user.get_full_name() or '').strip() or user.phone

    def get_read_count(self, obj):
        return obj.notifications.filter(is_read=True).count()

    def get_push_state(self, obj):
        if not obj.send_push:
            return 'off'
        if obj.push_done:
            return 'sent'
        return 'deferred' if obj.push_after else 'pending'
