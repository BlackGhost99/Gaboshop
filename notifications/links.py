"""Où mène une notification : chemin de l'application et texte du bouton (« Voir ma commande »)."""


def default_action(notification):
    """Renvoie (lien, libellé du bouton) selon le rôle de la personne et ce que la notification concerne."""
    role = getattr(notification.user, 'user_type', '') or ''
    order_id = notification.order_id
    meta = notification.metadata or {}
    needs_payment = notification.notif_type == 'payment' and meta.get('level') in ('error', 'warning')

    if role == 'client':
        if order_id and (needs_payment or meta.get('to') == 'pending_payment'):
            return f'/client/orders?pay={order_id}', 'Payer ma commande'
        if order_id:
            return f'/client/orders?order={order_id}', 'Voir ma commande'
        return '', ''
    if role == 'store_manager':
        if order_id:
            return f'/store/orders?order={order_id}', 'Voir la commande'
        if notification.notif_type == 'payment':
            return '/store/finance', 'Voir mes finances'
        return '', ''
    if role == 'delivery_agent':
        if notification.delivery_id or order_id:
            return '/delivery/dashboard', 'Voir mes livraisons'
        return '', ''
    if role == 'admin':
        return '/admin/dashboard', 'Ouvrir la console'
    return '', ''
