"""Alertes de stock (outil des forfaits Pro et Business) : le commerçant est prévenu quand une vente fait passer
un produit sous son seuil, puis à la rupture. Une alerte par passage de seuil, jamais une par vente."""
import logging

from django.db import transaction

logger = logging.getLogger(__name__)


def crossed(before, after, threshold):
    """'out' (dernière unité vendue), 'low' (passage sous le seuil) ou None."""
    if after <= 0 < before:
        return 'out'
    if threshold > 0 and after <= threshold < before:
        return 'low'
    return None


def _send(product_id, before, after):
    from notifications.models import Notification
    from payments.plan_features import store_has
    from products.models import Product

    product = Product.objects.select_related('store__manager').filter(pk=product_id).first()
    if product is None or product.store is None or product.store.manager_id is None:
        return
    store = product.store
    kind = crossed(before, after, store.stock_alert_threshold)
    if kind is None or not store_has(store, 'stock_alerts'):
        return
    if kind == 'out':
        title = f'Rupture de stock : {product.name}'
        body = (f"La dernière unité de « {product.name} » vient d'être vendue. Les clients ne peuvent plus "
                "l'acheter tant que vous n'ajoutez pas de stock.")
    else:
        title = f'Stock faible : {product.name}'
        body = (f"Il ne reste que {after} unité{'s' if after > 1 else ''} de « {product.name} ». "
                "Réapprovisionnez pour ne pas manquer de ventes.")
    Notification.objects.create(
        user=store.manager, title=title, body=body, notif_type='warning',
        link='/store/products', action_label='Mettre à jour le stock',
        metadata={'level': 'warning', 'kind': 'stock_alert', 'product_id': product.id, 'stock': after},
    )


def after_sale(changes):
    """``changes`` : {produit: (stock avant, stock après)}. Envoyé après validation de la commande."""
    def run():
        for product_id, (before, after) in changes.items():
            try:
                _send(product_id, before, after)
            except Exception:
                logger.exception("Alerte de stock impossible pour le produit %s", product_id)
    transaction.on_commit(run)
