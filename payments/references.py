"""Références marchandes SingPay des paiements de commande.

SingPay veut une référence unique par transaction : relancer la même référence après un échec
ou une demande expirée est refusé. Chaque essai a donc la sienne :
``GABOSHOP_<commande>`` pour le premier, puis ``GABOSHOP_<commande>_2``, ``_3``...
Les références déjà utilisées restent notées sur le paiement pour retrouver un essai validé tard.
"""
REFERENCE_PREFIX = 'GABOSHOP_'
REFERENCES_KEY = 'singpay_references'
PAID_REFERENCE_KEY = 'singpay_paid_reference'


def base_reference(order_number):
    return f'{REFERENCE_PREFIX}{order_number}'


def order_number_from_reference(reference):
    """Numéro de commande contenu dans une référence (avec ou sans numéro d'essai), sinon ''."""
    reference = str(reference or '').strip()
    if not reference.startswith(REFERENCE_PREFIX):
        return ''
    return reference[len(REFERENCE_PREFIX):].split('_', 1)[0].strip()


def payment_references(payment):
    """Toutes les références SingPay envoyées pour ce paiement, la première en tête."""
    base = base_reference(payment.order.order_number)
    stored = (payment.webhook_data or {}).get(REFERENCES_KEY)
    refs = [str(r) for r in stored if r] if isinstance(stored, list) else []
    return refs if base in refs else [base] + refs


def next_reference(payment, first_attempt):
    """Réserve la référence du prochain essai sur le paiement (enregistrée avec lui ensuite).

    ``first_attempt`` faux : un essai a déjà eu lieu (même avant que les références soient notées),
    la référence de base est donc considérée comme prise.
    """
    base = base_reference(payment.order.order_number)
    stored = (payment.webhook_data or {}).get(REFERENCES_KEY)
    used = [str(r) for r in stored if r] if isinstance(stored, list) else []
    if not first_attempt and base not in used:
        used.insert(0, base)
    reference, n = base, 1
    while reference in used:
        n += 1
        reference = f'{base}_{n}'
    payment.webhook_data = {**(payment.webhook_data or {}), REFERENCES_KEY: used + [reference]}
    return reference


def paid_reference(payment):
    """Référence de l'essai qui a réussi (pour reverser au commerce), sinon la dernière envoyée."""
    data = payment.webhook_data or {}
    return data.get(PAID_REFERENCE_KEY) or payment_references(payment)[-1]
