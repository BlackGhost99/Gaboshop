"""API du support : ouvrir une demande, suivre le fil de réponses, contact direct selon le forfait."""
from django.db.models import Count
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import SystemSettings
from payments.plan_features import has, required_message

from . import notify
from .models import SupportReply, SupportTicket
from .priority import plan_priority, support_context
from .serializers import SupportReplySerializer, SupportTicketDetailSerializer, SupportTicketSerializer

STATUSES = {code for code, _ in SupportTicket.STATUSES}
MAX_LIST = 200


def _error(code, message, http=status.HTTP_400_BAD_REQUEST, next_step=''):
    error = {'code': code, 'message': message}
    if next_step:
        error['next_step'] = next_step
    return Response({'success': False, 'error': error}, status=http)


def _is_admin(user):
    return bool(user.is_staff or user.is_superuser or getattr(user, 'user_type', '') == 'admin')


def _visible(user):
    qs = SupportTicket.objects.select_related('author', 'store')
    return qs if _is_admin(user) else qs.filter(author=user)


def _get_ticket(request, ticket_id):
    return _visible(request.user).filter(pk=ticket_id).first()


class TicketListCreateView(APIView):
    """GET /support/tickets/ : mes demandes (l'admin voit toutes les demandes, priorité d'abord, puis les plus anciennes).
    POST : ouvrir une demande {subject, message, category}."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        admin_view = _is_admin(request.user) and request.query_params.get('mine') not in ('1', 'true')
        qs = _visible(request.user) if admin_view else SupportTicket.objects.select_related('author', 'store').filter(
            author=request.user)
        state = request.query_params.get('status')
        if state in STATUSES:
            qs = qs.filter(status=state)
        elif state == 'active':
            qs = qs.exclude(status='resolved')
        level = request.query_params.get('priority')
        if level in dict(SupportTicket.PRIORITIES):
            qs = qs.filter(priority=level)
        qs = qs.annotate(replies_total=Count('replies'))
        if admin_view:
            # Les demandes résolues passent après celles qui attendent une réponse.
            qs = sorted(qs[:MAX_LIST * 5], key=lambda t: (t.status == 'resolved', t.priority_rank, t.created_at))[:MAX_LIST]
        else:
            qs = qs.order_by('-updated_at')[:MAX_LIST]
        return Response({'success': True, 'data': SupportTicketSerializer(qs, many=True).data})

    def post(self, request):
        serializer = SupportTicketSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'error': {
                'code': 'invalid_ticket', 'message': 'Votre demande est incomplète.', 'details': serializer.errors,
                'next_step': 'Corrigez les champs indiqués, puis envoyez à nouveau.',
            }}, status=status.HTTP_400_BAD_REQUEST)
        user = request.user
        store, plan, priority = support_context(user)
        ticket = serializer.save(
            author=user, author_role=getattr(user, 'user_type', '') or '', store=store,
            plan_name=getattr(plan, 'name', '') or '', priority=priority,
        )
        notify.ticket_opened(ticket)
        message = ("Votre demande est enregistrée. Elle sera traitée en priorité." if ticket.is_priority
                   else "Votre demande est enregistrée. Nous vous répondons dans l'ordre d'arrivée.")
        return Response({'success': True, 'message': message, 'data': SupportTicketDetailSerializer(ticket).data},
                        status=status.HTTP_201_CREATED)


class TicketDetailView(APIView):
    """GET /support/tickets/<id>/ : la demande et son fil. PATCH {status} : l'admin change le statut."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, ticket_id):
        ticket = _get_ticket(request, ticket_id)
        if ticket is None:
            return _error('ticket_not_found', 'Demande introuvable.', status.HTTP_404_NOT_FOUND)
        return Response({'success': True, 'data': SupportTicketDetailSerializer(ticket).data})

    def patch(self, request, ticket_id):
        if not _is_admin(request.user):
            return _error('forbidden', "Seule l'équipe Gaboshop peut changer le statut d'une demande.",
                          status.HTTP_403_FORBIDDEN)
        ticket = _get_ticket(request, ticket_id)
        if ticket is None:
            return _error('ticket_not_found', 'Demande introuvable.', status.HTTP_404_NOT_FOUND)
        new_status = request.data.get('status')
        if new_status not in STATUSES:
            return _error('invalid_status', 'Statut inconnu.', next_step='Choisissez Ouvert, En cours ou Résolu.')
        changed = new_status != ticket.status
        ticket.status = new_status
        ticket.resolved_at = timezone.now() if new_status == 'resolved' else None
        ticket.save()
        if changed and new_status == 'resolved':
            notify.resolved(ticket)
        return Response({'success': True, 'message': 'Statut mis à jour.',
                         'data': SupportTicketDetailSerializer(ticket).data})


class TicketReplyView(APIView):
    """POST /support/tickets/<id>/replies/ {message} : l'auteur ou l'admin ajoute une réponse au fil."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, ticket_id):
        ticket = _get_ticket(request, ticket_id)
        if ticket is None:
            return _error('ticket_not_found', 'Demande introuvable.', status.HTTP_404_NOT_FOUND)
        text = str(request.data.get('message') or '').strip()
        if not text:
            return _error('empty_reply', 'Écrivez votre réponse avant de l’envoyer.')
        if len(text) > 4000:
            return _error('reply_too_long', 'Votre réponse est trop longue (4000 caractères au plus).')
        staff = _is_admin(request.user)
        reply = SupportReply.objects.create(ticket=ticket, author=request.user, message=text, is_staff_reply=staff)
        if staff:
            if ticket.status == 'open':
                ticket.status = 'in_progress'
            notify.staff_replied(ticket)
        elif ticket.status != 'open':
            # Le client reprend la parole : la demande revient dans la file des admins.
            ticket.status = 'open'
            ticket.resolved_at = None
        ticket.save()
        if not staff:
            notify.customer_replied(ticket)
        return Response({'success': True, 'message': 'Réponse envoyée.', 'data': {
            'reply': SupportReplySerializer(reply).data,
            'ticket': SupportTicketDetailSerializer(ticket).data,
        }}, status=status.HTTP_201_CREATED)


class ContactView(APIView):
    """GET /support/contact/ : le contact direct de Gaboshop n'est donné qu'aux forfaits « Support prioritaire »."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        config = SystemSettings.get_settings()
        email = config.support_email or ''
        store, plan, priority = support_context(request.user)
        data = {
            'direct': False, 'dedicated': False, 'email': email, 'phone': '', 'whatsapp': '',
            'plan_name': getattr(plan, 'name', '') or '', 'priority': priority, 'priority_label': '', 'message': '',
        }
        if store is not None and has(plan, 'priority_support'):
            data['direct'] = True
            data['dedicated'] = plan_priority(plan) == 'dedie'
            data['priority_label'] = 'Ligne dédiée' if data['dedicated'] else 'Support prioritaire'
            data['phone'] = config.support_phone or ''
            data['whatsapp'] = config.support_whatsapp or ''
            if data['phone'] or data['whatsapp']:
                data['message'] = (
                    'Votre forfait inclut la ligne dédiée Gaboshop (WhatsApp et téléphone).' if data['dedicated']
                    else 'Votre forfait inclut le contact direct de Gaboshop.'
                )
            else:
                data['message'] = ("Votre forfait inclut le contact direct, mais Gaboshop n'a pas encore publié "
                                   "de numéro. Ouvrez une demande : elle est traitée en priorité.")
        elif store is not None:
            data['message'] = (f"Le contact direct n'est pas inclus dans votre forfait. "
                               f"{required_message('priority_support', plan)} "
                               f"En attendant, écrivez à {email or 'Gaboshop'} ou ouvrez une demande ci-dessous.")
        else:
            data['message'] = (f"Écrivez-nous à {email} ou ouvrez une demande ci-dessous : "
                               "elle est traitée dans l'ordre d'arrivée.") if email else (
                "Ouvrez une demande ci-dessous : elle est traitée dans l'ordre d'arrivée.")
        return Response({'success': True, 'data': data})
