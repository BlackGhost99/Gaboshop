"""Textes des notifications du support (même forme que notifications/messages.py)."""
from notifications.messages import _message


def reply_for_author(ticket):
    return _message(
        f"Réponse à votre demande « {ticket.subject[:80]} »",
        f"L'équipe Gaboshop a répondu à votre demande n° {ticket.pk}. Ouvrez-la pour lire la réponse.",
        level='info', next_step='Ouvrez la demande pour lire la réponse, et répondez si besoin.',
        sms=f"GABOSHOP - Réponse à votre demande n° {ticket.pk}.",
    )


def status_for_author(ticket):
    if ticket.status != 'resolved':
        return None
    return _message(
        f"Demande n° {ticket.pk} résolue",
        f"Votre demande « {ticket.subject[:80]} » est marquée comme résolue. Répondez-lui si le problème persiste.",
        level='success', next_step="Si le problème persiste, répondez dans la demande : elle sera rouverte.",
    )


def new_priority_for_admin(ticket):
    who = ticket.author.get_display_name()
    shop = f" ({ticket.store.name})" if ticket.store_id else ''
    label = 'ligne dédiée' if ticket.priority == 'dedie' else 'prioritaire'
    return _message(
        f"Priorité : nouvelle demande n° {ticket.pk}",
        f"{who}{shop} a ouvert une demande {label} : « {ticket.subject[:100]} ». "
        f"Forfait : {ticket.plan_name or 'non précisé'}.",
        level='warning', reason='Le forfait de ce commerce donne un traitement en priorité.',
        next_step='Traitez-la avant les demandes standard.',
    )


def customer_reply_for_admin(ticket):
    prefix = 'Priorité : ' if ticket.priority != 'standard' else ''
    return _message(
        f"{prefix}nouveau message sur la demande n° {ticket.pk}",
        f"{ticket.author.get_display_name()} a répondu à « {ticket.subject[:100]} ».",
        level='warning' if prefix else 'info', next_step='Ouvrez la demande pour répondre.',
    )
