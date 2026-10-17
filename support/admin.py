from django.contrib import admin
from django.db.models import Count

from . import notify
from .models import SupportReply, SupportTicket


class SupportReplyInline(admin.TabularInline):
    model = SupportReply
    extra = 0
    readonly_fields = ('author', 'is_staff_reply', 'created_at')


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'subject', 'priority', 'status', 'author', 'store', 'plan_name', 'category', 'created_at', 'replies_total')
    list_filter = ('priority', 'status', 'category', 'author_role')
    search_fields = ('subject', 'message', 'author__phone', 'author__email', 'store__name')
    readonly_fields = ('author', 'author_role', 'store', 'plan_name', 'priority_rank', 'created_at', 'updated_at')
    inlines = [SupportReplyInline]
    # Priorité d'abord (ligne dédiée, prioritaire, standard), puis la demande la plus ancienne.
    ordering = ('priority_rank', 'created_at')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('author', 'store').annotate(replies_total=Count('replies'))

    @admin.display(description='Réponses', ordering='replies_total')
    def replies_total(self, obj):
        return obj.replies_total

    def save_formset(self, request, form, formset, change):
        # Une réponse saisie dans l'admin Django vient du personnel.
        new_staff_reply = None
        for obj in formset.save(commit=False):
            if isinstance(obj, SupportReply) and obj.pk is None:
                obj.author = obj.author or request.user
                obj.is_staff_reply = True
                if obj.ticket.status == 'open':
                    obj.ticket.status = 'in_progress'
                    obj.ticket.save()
                new_staff_reply = obj.ticket
            obj.save()
            if new_staff_reply is not None:
                notify.staff_replied(new_staff_reply)
                new_staff_reply = None
        formset.save_m2m()
        for obj in formset.deleted_objects:
            obj.delete()


@admin.register(SupportReply)
class SupportReplyAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket', 'author', 'is_staff_reply', 'created_at')
    list_filter = ('is_staff_reply',)
