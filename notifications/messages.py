"""Textes des notifications Gaboshop : ce qui s'est passé, pourquoi, et quoi faire.

Chaque message est un dictionnaire :
- ``title``  : une ligne qui dit l'essentiel ;
- ``body``   : le détail (montant, commerce, numéro, étapes suivantes) ;
- ``level``  : ``success``, ``error``, ``warning`` ou ``info`` ;
- ``reason`` : pour un échec, la cause en mots simples ;
- ``next_step`` : ce que la personne doit faire maintenant ;
- ``sms``    : version courte pour SMS.

``reason`` et ``next_step`` sont gardés dans les métadonnées de la notification : l'application
les affiche, et l'assistant IA s'en sert pour expliquer comment régler le problème.
"""
from decimal import Decimal, InvalidOperation

ORDER_STATUS_LABELS = {
    'created': 'enregistrée',
    'pending_payment': 'en attente de paiement',
    'paid': 'payée',
    'confirmed': 'confirmée',
    'preparing': 'en préparation',
    'ready': 'prête',
    'assigned': 'confiée à un livreur',
    'in_transit': 'en route',
    'delivered': 'livrée',
    'cancelled': 'annulée',
    'refunded': 'remboursée',
    'delayed': 'en retard',
}

OPERATOR_LABELS = {
    'airtel_money': 'Airtel Money', 'moov_money': 'Moov Money', 'mobile_money': 'Mobile Money', 'cash': 'espèces',
}


def money(value):
    try:
        amount = Decimal(str(value or 0)).quantize(Decimal('1'))
    except (InvalidOperation, TypeError, ValueError):
        return f'{value} F CFA'
    return f"{int(amount):,}".replace(',', ' ') + ' F CFA'


def status_label(code):
    return ORDER_STATUS_LABELS.get(code, str(code or ''))


def _store_name(order):
    store = getattr(order, 'store', None)
    return getattr(store, 'name', '') or 'le commerce'


def _message(title, body, level='info', reason='', next_step='', sms=''):
    return {
        'title': title, 'body': body, 'level': level, 'reason': reason, 'next_step': next_step,
        'sms': sms or f"GABOSHOP - {title}",
    }


def _items_summary(order):
    try:
        items = list(order.items.select_related('product')[:4])
    except Exception:
        return ''
    if not items:
        return ''
    parts = [f"{item.quantity} x {getattr(item.product, 'name', 'article')}" for item in items[:3]]
    if len(items) > 3:
        parts.append('…')
    return ', '.join(parts)


# --- Commandes : commerce ----------------------------------------------------------------

def new_order_for_store(order, store_closed=False):
    items = _items_summary(order)
    payment = getattr(getattr(order, 'payment_arrangement', None), 'method', '') or ''
    lines = [
        f"Commande #{order.order_number} de {money(order.total_amount)}"
        + (f" : {items}." if items else '.'),
        f"Livraison : {order.delivery_zone or order.delivery_address or 'adresse indiquée dans la commande'}.",
    ]
    if payment:
        lines.append(f"Paiement choisi : {OPERATOR_LABELS.get(payment, payment)}.")
    if store_closed:
        store = order.store
        lines.append(
            f"Votre commerce était fermé selon vos horaires ({store.opening_time:%H:%M} à {store.closing_time:%H:%M}), "
            "donc aucun SMS ne vous a été envoyé."
            if hasattr(store.opening_time, 'strftime') and hasattr(store.closing_time, 'strftime')
            else "Votre commerce était fermé selon vos horaires, donc aucun SMS ne vous a été envoyé."
        )
        return _message(
            f"Nouvelle commande #{order.order_number} reçue pendant la fermeture",
            ' '.join(lines),
            level='warning',
            reason='Commerce fermé selon ses horaires au moment de la commande.',
            next_step="Ouvrez « Mes commandes » pour la confirmer ou la refuser. Si vous êtes ouvert, corrigez vos "
                      "horaires dans « Profil du commerce » (même heure d'ouverture et de fermeture = ouvert 24 h/24).",
        )
    return _message(
        f"Nouvelle commande #{order.order_number} : {money(order.total_amount)}",
        ' '.join(lines),
        level='info',
        next_step="Ouvrez « Mes commandes », vérifiez le stock puis confirmez la commande pour que le client soit prévenu.",
        sms=f"GABOSHOP - Nouvelle commande #{order.order_number} : {money(order.total_amount)}. "
            f"Zone : {order.delivery_zone}. Confirmez-la dans l'application.",
    )


def order_update_for_store(order, new_status):
    """Changements que le commerce doit connaître sans les avoir faits lui-même."""
    if new_status == 'cancelled':
        return _message(
            f"Commande #{order.order_number} annulée",
            f"La commande #{order.order_number} de {money(order.total_amount)} a été annulée. "
            "Ne la préparez pas ; si elle est déjà prête, remettez les articles en stock.",
            level='warning',
            reason='Annulation par le client ou par Gaboshop.',
            next_step="Vérifiez votre stock dans « Mes produits ».",
        )
    if new_status == 'delivered':
        return _message(
            f"Commande #{order.order_number} livrée",
            f"Le client a reçu la commande #{order.order_number} ({money(order.total_amount)}). Vente terminée.",
            level='success',
        )
    return None


# --- Commandes : client ------------------------------------------------------------------

def order_update_for_client(order, old_status, new_status):
    store = _store_name(order)
    number, total = order.order_number, money(order.total_amount)
    delivery = getattr(order, 'delivery', None)
    agent = getattr(delivery, 'delivery_agent', None) if delivery is not None else None
    agent_text = ''
    if agent is not None:
        name = (agent.get_full_name() if hasattr(agent, 'get_full_name') else '') or 'Votre livreur'
        agent_text = f"{name} ({agent.phone})" if getattr(agent, 'phone', '') else name

    texts = {
        'pending_payment': (
            f"Commande #{number} : paiement attendu",
            f"Votre commande chez {store} ({total}) attend votre paiement.",
            'info', "Ouvrez la commande et validez la demande de paiement sur votre téléphone.",
        ),
        'paid': (
            f"Commande #{number} payée",
            f"Votre paiement de {total} pour la commande chez {store} est bien reçu.",
            'success', "Rien à faire : le commerce va la préparer.",
        ),
        'confirmed': (
            f"Commande #{number} confirmée",
            f"{store} a bien votre commande de {total}. Elle va être préparée.",
            'success', "Rien à faire pour l'instant : vous serez prévenu à chaque étape.",
        ),
        'preparing': (
            f"Commande #{number} en préparation",
            f"{store} prépare votre commande ({total}).",
            'info', "Rien à faire : vous serez prévenu dès qu'un livreur la prend.",
        ),
        'ready': (
            f"Commande #{number} prête",
            f"Votre commande chez {store} est prête. Gaboshop cherche un livreur.",
            'info', "Gardez votre téléphone allumé pour la livraison.",
        ),
        'assigned': (
            f"Livreur trouvé pour la commande #{number}",
            f"{agent_text or 'Un livreur'} va récupérer votre commande chez {store}.",
            'info', "Gardez votre téléphone allumé : le livreur peut vous appeler.",
        ),
        'in_transit': (
            f"Commande #{number} en route",
            f"{agent_text or 'Le livreur'} arrive avec votre commande ({total}).",
            'info', "Préparez votre code de livraison : donnez-le au livreur seulement quand vous avez vos articles.",
        ),
        'delivered': (
            f"Commande #{number} livrée",
            f"Votre commande chez {store} ({total}) est livrée. Merci pour votre achat !",
            'success', "Un souci avec un article ? Écrivez à l'assistant Gaboshop.",
        ),
        'cancelled': (
            f"Commande #{number} annulée",
            f"Votre commande chez {store} ({total}) a été annulée.",
            'warning', "Si vous aviez déjà payé en ligne, demandez le remboursement à l'assistant Gaboshop. "
                       "Sinon, vous pouvez repasser commande.",
        ),
        'refunded': (
            f"Commande #{number} remboursée",
            f"Le remboursement de {total} pour votre commande chez {store} est fait.",
            'success', "Vérifiez votre solde Mobile Money.",
        ),
        'delayed': (
            f"Commande #{number} en retard",
            f"Votre commande chez {store} prend plus de temps que prévu. "
            + (f"{agent_text} est en route." if agent_text else "Le livreur est en route."),
            'warning', "Vous pouvez appeler le livreur, ou demander de l'aide à l'assistant Gaboshop.",
        ),
    }
    title, body, level, next_step = texts.get(new_status, (
        f"Commande #{number} : {status_label(new_status)}",
        f"Votre commande chez {store} est maintenant {status_label(new_status)}.",
        'info', '',
    ))
    reason = 'Annulation de la commande.' if new_status == 'cancelled' else ''
    return _message(title, body, level=level, reason=reason, next_step=next_step,
                    sms=f"GABOSHOP - {title}. {next_step}".strip())


# --- Paiements en ligne ------------------------------------------------------------------

PAYMENT_FAILURES = {
    'password': (
        "Code secret Mobile Money incorrect.",
        "Relancez la demande depuis la commande et tapez votre code secret avec soin.",
    ),
    'balance': (
        "Solde Mobile Money insuffisant pour payer ce montant (frais de l'opérateur compris).",
        "Rechargez votre compte Mobile Money, puis relancez la demande depuis la commande.",
    ),
    'timeout': (
        "La demande de paiement n'a pas été validée à temps sur le téléphone : elle a expiré.",
        "Relancez la demande depuis la commande, puis validez-la tout de suite avec votre code secret.",
    ),
    'refused': (
        "Le paiement a été refusé ou annulé sur le téléphone.",
        "Si c'était une erreur, relancez la demande depuis la commande.",
    ),
    'number': (
        "Le numéro Mobile Money n'a pas été accepté par l'opérateur.",
        "Vérifiez le numéro (Airtel : 07…, Moov : 06…) et l'opérateur choisi, puis relancez.",
    ),
    'service': (
        "Le service de paiement n'a pas pu envoyer la demande (problème chez l'opérateur ou chez Gaboshop).",
        "Réessayez dans quelques minutes. Si ça recommence, demandez à l'assistant Gaboshop : il préviendra l'équipe.",
    ),
    'unknown': (
        "L'opérateur n'a pas confirmé le paiement.",
        "Relancez la demande depuis la commande. Si de l'argent a été retiré, ne repayez pas : demandez à l'assistant.",
    ),
}


def payment_failure_code(details):
    """Cause d'un échec SingPay à partir de sa réponse (dict) ou d'un message d'erreur."""
    if isinstance(details, dict):
        # Réponse SingPay : seuls le résultat et les messages comptent, pas les noms de champs.
        tx = details.get('transaction') if isinstance(details.get('transaction'), dict) else {}
        status = details.get('status') if isinstance(details.get('status'), dict) else {}
        details = ' '.join(str(v) for v in (
            tx.get('result'), tx.get('status'), status.get('message'), details.get('message'), details.get('error'),
        ) if v)
    text = str(details or '').lower()
    if 'password' in text or 'pin' in text or 'mot de passe' in text:
        return 'password'
    if 'balance' in text or 'solde' in text or 'insufficient' in text or 'insuffisant' in text:
        return 'balance'
    if 'timeout' in text or 'expire' in text or 'time out' in text:
        return 'timeout'
    if 'msisdn' in text or 'numéro' in text or 'numero' in text or 'phone' in text:
        return 'number'
    if 'cancel' in text or 'refus' in text or 'reject' in text or 'annul' in text:
        return 'refused'
    if any(word in text for word in ('config', 'http', 'wallet', 'connexion', 'connection', 'portefeuille')):
        return 'service'
    return 'unknown'


def payment_failed_for_client(order, payment, details=None):
    code = payment_failure_code(details)
    reason, next_step = PAYMENT_FAILURES[code]
    operator = OPERATOR_LABELS.get(getattr(payment, 'payment_method', ''), 'Mobile Money')
    phone = getattr(payment, 'client_phone', '') or ''
    body = (
        f"Le paiement {operator} de {money(payment.amount)} pour la commande #{order.order_number} "
        f"chez {_store_name(order)}{f' (numéro {phone})' if phone else ''} n'a pas abouti. "
        f"Cause : {reason} Aucun montant n'a été encaissé par Gaboshop pour cet essai."
    )
    return _message(
        f"Paiement non abouti : commande #{order.order_number}", body, level='error',
        reason=reason, next_step=next_step,
        sms=f"GABOSHOP - Paiement non abouti (commande #{order.order_number}). {reason} {next_step}",
    ) | {'failure_code': code}


def payment_success_for_client(order, payment):
    operator = OPERATOR_LABELS.get(getattr(payment, 'payment_method', ''), 'Mobile Money')
    phone = getattr(payment, 'client_phone', '') or ''
    return _message(
        f"Paiement reçu : commande #{order.order_number}",
        f"Votre paiement {operator} de {money(payment.amount)}{f' depuis le {phone}' if phone else ''} est confirmé. "
        f"{_store_name(order)} est prévenu et va préparer votre commande.",
        level='success',
        next_step="Rien à faire : vous serez prévenu à chaque étape de la livraison.",
        sms=f"GABOSHOP - Paiement de {money(payment.amount)} reçu pour la commande #{order.order_number}. Merci !",
    )


def payment_success_for_store(order, payment):
    items = _items_summary(order)
    return _message(
        f"Commande #{order.order_number} payée en ligne : {money(payment.amount)}",
        f"Le client a payé {money(payment.amount)} en ligne"
        + (f" pour : {items}." if items else '.')
        + " L'argent est encaissé par Gaboshop ; votre part vous est versée quand vous lancez la préparation.",
        level='success',
        next_step="Ouvrez « Mes commandes » et passez la commande « En préparation ».",
        sms=f"GABOSHOP - Commande #{order.order_number} payée ({money(payment.amount)}). Préparez-la.",
    )


# --- Versements au commerce --------------------------------------------------------------

def store_payout_message(payout):
    order = payout.order
    if payout.status == 'paid':
        return _message(
            f"Versement envoyé : {money(payout.amount)}",
            f"Votre part de la commande #{order.order_number} ({money(payout.amount)}) a été envoyée sur votre "
            f"compte Mobile Money (produits {money(payout.products_amount)}, commission Gaboshop "
            f"{money(payout.commission_amount)}"
            + (f", livraison {money(payout.delivery_amount)}" if payout.includes_delivery else '') + ").",
            level='success',
            next_step="Vérifiez le SMS de votre opérateur.",
        )
    note = (payout.note or '').strip()
    if payout.status == 'pending':
        if 'décaissement' in note.lower():
            next_step = ("Renseignez votre numéro Mobile Money dans « Profil du commerce » ; Gaboshop l'active "
                         "puis vous verse les ventes en attente.")
        else:
            next_step = "Rien à faire : Gaboshop vous verse ce montant à la main."
        return _message(
            f"Versement en attente : {money(payout.amount)}",
            f"Votre part de la commande #{order.order_number} ({money(payout.amount)}) n'est pas encore envoyée.",
            level='warning', reason=note or 'Versement pas encore lancé.', next_step=next_step,
        )
    if payout.status == 'failed':
        return _message(
            f"Versement échoué : {money(payout.amount)}",
            f"L'envoi de votre part de la commande #{order.order_number} ({money(payout.amount)}) a échoué.",
            level='error', reason=note or "L'opérateur a refusé le transfert.",
            next_step="Vérifiez votre numéro Mobile Money dans « Profil du commerce ». Gaboshop relancera le versement.",
        )
    return None
