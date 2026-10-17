from rest_framework import serializers

from .models import SupportReply, SupportTicket


def _name(user):
    if user is None:
        return 'Gaboshop'
    return (user.get_full_name() or '').strip() or user.phone


class SupportReplySerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = SupportReply
        fields = ['id', 'message', 'is_staff_reply', 'author_name', 'created_at']
        read_only_fields = fields

    def get_author_name(self, obj):
        # Pour la personne qui écrit, le personnel s'appelle « Gaboshop » : on ne montre pas le nom de l'agent.
        return 'Équipe Gaboshop' if obj.is_staff_reply else _name(obj.author)


class SupportTicketSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    author_phone = serializers.SerializerMethodField()
    store_name = serializers.SerializerMethodField()
    category_label = serializers.CharField(source='get_category_display', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    priority_label = serializers.CharField(source='get_priority_display', read_only=True)
    replies_count = serializers.SerializerMethodField()

    class Meta:
        model = SupportTicket
        fields = [
            'id', 'subject', 'message', 'category', 'category_label', 'status', 'status_label',
            'priority', 'priority_label', 'plan_name', 'store', 'store_name', 'author_name', 'author_phone',
            'author_role', 'replies_count', 'created_at', 'updated_at', 'resolved_at',
        ]
        read_only_fields = [
            'id', 'status', 'priority', 'plan_name', 'store', 'author_role', 'created_at', 'updated_at', 'resolved_at',
        ]

    def get_author_name(self, obj):
        return _name(obj.author)

    def get_author_phone(self, obj):
        return obj.author.phone

    def get_store_name(self, obj):
        return obj.store.name if obj.store_id else ''

    def get_replies_count(self, obj):
        annotated = getattr(obj, 'replies_total', None)
        return annotated if annotated is not None else obj.replies.count()

    def validate_subject(self, value):
        value = (value or '').strip()
        if len(value) < 3:
            raise serializers.ValidationError('Donnez un sujet clair (3 caractères au moins).')
        return value

    def validate_message(self, value):
        value = (value or '').strip()
        if len(value) < 10:
            raise serializers.ValidationError('Décrivez votre problème en quelques mots (10 caractères au moins).')
        return value


class SupportTicketDetailSerializer(SupportTicketSerializer):
    replies = SupportReplySerializer(many=True, read_only=True)

    class Meta(SupportTicketSerializer.Meta):
        fields = SupportTicketSerializer.Meta.fields + ['replies']
