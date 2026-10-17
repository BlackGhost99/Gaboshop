"""Notifications du support : chaque envoi porte un lien vers la demande, et ne fait jamais échouer la requête."""
import logging

from django.db.models import Q

from notifications.models import Notification
from users.models import User

from . import messages

logger = logging.getLogger(__name__)


def _send(user, message, link, label, ticket):
    Notification.objects.create(
        user=user, title=message['title'][:200], body=message['body'], notif_type='info', link=link,
        action_label=label,
        metadata={
            'level': message.get('level', 'info'), 'reason': message.get('reason', ''),
            'next_step': message.get('next_step', ''), 'ticket_id': ticket.pk, 'priority': ticket.priority,
        },
    )


def admins():
    return User.objects.filter(is_active=True).filter(Q(user_type='admin') | Q(is_staff=True) | Q(is_superuser=True))


def _to_admins(ticket, message, exclude=None):
    for admin in admins().exclude(pk=exclude.pk if exclude else None):
        _send(admin, message, f'/admin/support?ticket={ticket.pk}', 'Ouvrir la demande', ticket)


def ticket_opened(ticket):
    """Une demande prioritaire prévient les admins avec « Priorité » ; une demande standard attend dans la liste."""
    if not ticket.is_priority:
        return
    try:
        _to_admins(ticket, messages.new_priority_for_admin(ticket), exclude=ticket.author)
    except Exception:
        logger.exception('Notification admin du ticket %s non envoyée', ticket.pk)


def staff_replied(ticket):
    try:
        _send(ticket.author, messages.reply_for_author(ticket), f'/support?ticket={ticket.pk}',
              'Voir ma demande', ticket)
    except Exception:
        logger.exception('Notification de réponse du ticket %s non envoyée', ticket.pk)


def customer_replied(ticket):
    try:
        _to_admins(ticket, messages.customer_reply_for_admin(ticket), exclude=ticket.author)
    except Exception:
        logger.exception('Notification admin de la réponse du ticket %s non envoyée', ticket.pk)


def resolved(ticket):
    message = messages.status_for_author(ticket)
    if message is None:
        return
    try:
        _send(ticket.author, message, f'/support?ticket={ticket.pk}', 'Voir ma demande', ticket)
    except Exception:
        logger.exception('Notification de résolution du ticket %s non envoyée', ticket.pk)
