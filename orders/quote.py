"""Devis complet avant commande : chaque montant, qui le reçoit, quand payer et ce qui bloquerait la commande.

Même calcul que la création de commande (OrderCreateSerializer.create + Order.calculate_totals +
payments.direct_service.create_arrangement), sans rien enregistrer : le prix affiché est le prix payé.
"""
from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError

from orders.invoice import METHOD_LABELS

FLOW_LABELS = {
    'platform_online': 'Paiement en ligne Gaboshop',
    'direct_split': 'Articles au commerce, livraison au livreur',
    'store_collects_all': 'Tout payer au commerce',
    'courier_cash': 'Espèces au livreur à la livraison',
}
MOBILE_METHODS = ('mobile_money', 'airtel_money', 'moov_money')


def _franc(value):
    return Decimal(value or 0).quantize(Decimal('1'), rounding=ROUND_HALF_UP)


def _money(value):
    return f"{int(_franc(value)):,}".replace(',', ' ') + ' F'


def _error_text(exc):
    """Texte lisible d'une erreur de validation Django ou DRF (dict, liste ou texte)."""
    detail = getattr(exc, 'detail', None)
    if detail is None:
        detail = getattr(exc, 'messages', None) or str(exc)
    parts = []

    def walk(value):
        if isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                walk(item)
        elif str(value) not in parts:
            parts.append(str(value))
    walk(detail)
    return ' '.join(parts)


def _has_forfait(user):
    from payments.client_forfaits import active_forfait
    try:
        return bool(active_forfait(user))
    except Exception:
        return False


def _fee_details(*, online, payment_flow, method, delivery_by, delivery_requested, items_total, delivery_fee,
                 operator_fee, small, forfait, user, has_forfait):
    """Lignes d'explication des frais : ``status`` = charged (dans le total), free (offert) ou info (ne change pas le total)."""
    from api.models import SystemSettings
    from payments.economics import small_order_fee
    settings = SystemSettings.get_settings()
    rows = []

    # Frais de l'opérateur Mobile Money.
    if not payment_flow:
        pass
    elif not online:
        rows.append({'label': 'Frais Mobile Money', 'amount': '0', 'status': 'info',
                     'note': "Aucun : vous payez directement le commerce et le livreur, sans passer par Gaboshop."})
    elif operator_fee > 0:
        rows.append({'label': f"Frais {METHOD_LABELS.get(method, 'Mobile Money')}", 'amount': str(operator_fee),
                     'status': 'charged', 'note': 'Frais de l\'opérateur sur les articles et la livraison.'})
    else:
        rows.append({'label': f"Frais {METHOD_LABELS.get(method, 'Mobile Money')}", 'amount': '0', 'status': 'free',
                     'note': 'Offerts : Gaboshop prend ces frais à sa charge.'})

    # Frais petit panier (petites courses).
    fee = _franc(settings.small_order_fee or 0)
    threshold = _franc(settings.small_order_threshold or 0)
    if fee <= 0:
        rows.append({'label': 'Frais petit panier', 'amount': '0', 'status': 'free',
                     'note': 'Aucun frais sur les petites courses.'})
    elif small > 0:
        rows.append({'label': f"Frais petit panier (articles sous {_money(threshold)})", 'amount': str(small),
                     'status': 'charged', 'note': 'Petite course payée en ligne : participation aux frais de traitement.'})
    elif Decimal(items_total or 0) >= threshold:
        rows.append({'label': 'Frais petit panier', 'amount': '0', 'status': 'free',
                     'note': f"Non appliqué : vos articles dépassent {_money(threshold)}."})
    elif payment_flow and not online:
        rows.append({'label': 'Frais petit panier', 'amount': '0', 'status': 'info',
                     'note': f"Non appliqué : il ne concerne que le paiement en ligne ({_money(fee)} sous {_money(threshold)} d'articles)."})
    else:
        rows.append({'label': f"Frais petit panier ({_money(fee)})", 'amount': '0', 'status': 'info',
                     'note': f"S'applique en paiement en ligne quand les articles sont sous {_money(threshold)}."})

    # Réduction du forfait client sur la livraison.
    if has_forfait and delivery_requested:
        if forfait > 0:
            rows.append({'label': 'Réduction de votre forfait livraison', 'amount': str(-forfait), 'status': 'charged',
                         'note': 'Déduite des frais de livraison, offerte par Gaboshop.'})
        elif online and delivery_by == 'store':
            rows.append({'label': 'Réduction de votre forfait livraison', 'amount': '0', 'status': 'info',
                         'note': 'Non appliquée : le commerce livre lui-même.'})
        elif payment_flow and not online:
            rows.append({'label': 'Réduction de votre forfait livraison', 'amount': '0', 'status': 'info',
                         'note': 'Réservée au paiement en ligne.'})

    # Commission : payée par le commerce, jamais ajoutée au total du client.
    rows.append({'label': 'Commission Gaboshop', 'amount': '0', 'status': 'info',
                 'note': "Prélevée sur la vente du commerce : elle n'est pas ajoutée à votre total."})
    return rows


def _hours(store):
    opening, closing = store.opening_time, store.closing_time
    if not opening or not closing:
        return ''
    if opening == closing:
        return 'Ouvert 24 h/24'
    return f"{opening.strftime('%H:%M')} – {closing.strftime('%H:%M')}"


def _vehicle_label(code):
    from delivery.models import VehicleType
    return dict(VehicleType.VEHICLE_NAME_CHOICES).get(code, code or '')


def _payment_lines(flow, method, delivery_by, delivery_requested, items, delivery, operator_fee, total, policy):
    """Qui le client paie, combien, comment et quand (mêmes parts que create_arrangement)."""
    how = METHOD_LABELS.get(method, method or '')
    mobile = method in MOBILE_METHODS
    # Même règle que payments.direct_service.can_dispatch : tout sauf les espèces se paie avant l'envoi.
    prepaid = method != 'cash' or policy.get('payment_timing') == 'before_dispatch'
    if mobile:
        to_store_how = f"{how}, au code marchand du commerce"
        to_store_when = "Avant la préparation : vous déclarez l'ID de transaction reçu par SMS, le commerce confirme."
    elif method != 'cash':
        to_store_how = f"{how or 'Virement'}, aux coordonnées données par le commerce"
        to_store_when = "Avant l'envoi : vous déclarez la référence du paiement, le commerce confirme."
    else:
        to_store_how = 'Espèces'
        if not delivery_requested:
            to_store_when = 'Au retrait au commerce.'
        elif prepaid:
            to_store_when = "Avant l'envoi de la commande."
        else:
            to_store_when = 'À la livraison.'
    lines = []
    if flow == 'platform_online':
        lines.append({'payee': 'Gaboshop (paiement en ligne)', 'amount': total, 'how': how,
                      'when': 'Juste après la commande : une seule demande arrive sur votre téléphone, '
                              'validez-la avec votre code secret.',
                      'then': ("Gaboshop reverse ensuite les articles au commerce (après votre confirmation de réception) "
                               + ("et la livraison au commerce, qui livre lui-même." if delivery_by == 'store'
                                  else "et la livraison au livreur.")) if delivery_requested else
                              "Gaboshop reverse ensuite les articles au commerce après votre confirmation de réception."})
    elif flow == 'direct_split':
        lines.append({'payee': 'Le commerce', 'amount': items, 'how': to_store_how, 'when': to_store_when})
        if delivery_requested and delivery:
            lines.append({'payee': 'Le livreur', 'amount': delivery,
                          'how': 'Espèces' if method == 'cash' else 'Au livreur directement',
                          'when': 'À la livraison.'})
    elif flow == 'store_collects_all':
        lines.append({'payee': 'Le commerce', 'amount': items + delivery, 'how': to_store_how,
                      'when': to_store_when})
    elif flow == 'courier_cash':
        lines.append({'payee': 'Le livreur', 'amount': items + delivery, 'how': 'Espèces',
                      'when': 'À la livraison, quand vous avez le colis en main.'})
    return [{**line, 'amount': str(_franc(line['amount']))} for line in lines if _franc(line['amount']) > 0]


def build_quote(store, user, pairs, *, delivery_requested=True, city='Libreville', zone_text='',
                neighborhood_id=None, landmark_id=None, details='', payment_flow='', payment_method='',
                delivery_by='', missing_products=0, delivery_type='standard'):
    """Devis d'un panier (``pairs`` : liste de (produit, quantité)). Ne lève pas : ce qui bloquerait la commande
    est listé dans ``blocking`` pour que le client le voie avant de commander."""
    from api.models import SystemSettings
    from delivery.zones import active_zones, city_neighborhoods, resolve_landmark, resolve_neighborhood, resolve_zone, zone_name_for
    from orders.models import Order
    from payments.client_forfaits import delivery_discount
    from payments.configuration import available_payment_options, matching_option
    from payments.economics import small_order_fee

    blocking = []
    city = (city or 'Libreville').strip()
    zones = list(active_zones(city).values_list('name', flat=True))

    # Articles : prix, disponibilité et stock, comme à la commande.
    lines = []
    items_total = Decimal('0')
    # Le stock se vérifie sur la quantité totale d'un produit (deux tailles = deux lignes, un seul stock).
    wanted = {}
    for product, quantity in pairs:
        wanted[product.id] = wanted.get(product.id, 0) + quantity
    if missing_products:
        blocking.append(f"{missing_products} article(s) du panier n'existe(nt) plus : retirez-les du panier.")
    for product, quantity in pairs:
        subtotal = Decimal(product.price or 0) * quantity
        items_total += subtotal
        line = {'product_id': product.id, 'name': product.name, 'unit_price': str(_franc(product.price)),
                'quantity': quantity, 'subtotal': str(_franc(subtotal)), 'stock': product.stock}
        if not product.is_available or product.market_type not in ('b2c', 'both'):
            line['problem'] = "Cet article n'est plus en vente."
        elif product.stock is not None and product.stock < wanted[product.id]:
            line['problem'] = f"Stock insuffisant : il reste {product.stock} unité(s)."
        if line.get('problem') and f"{product.name} : {line['problem']}" not in blocking:
            blocking.append(f"{product.name} : {line['problem']}")
        lines.append(line)

    # Livraison : adresse, zone de prix, véhicule et prix (même calcul que la commande).
    delivery = {'requested': bool(delivery_requested)}
    neighborhood = landmark = None
    message = ''
    zone = ''
    if delivery_requested:
        try:
            if neighborhood_id:
                neighborhood = resolve_neighborhood(neighborhood_id)
                city, zone = neighborhood.city.name, zone_name_for(neighborhood)
                landmark = resolve_landmark(landmark_id, neighborhood)
            elif not (zone_text or '').strip() and city_neighborhoods(city).exists():
                message = 'Choisissez votre quartier dans la liste pour voir le prix de la livraison.'
            else:
                zone = resolve_zone(city, zone_text)
        except ValueError as exc:
            message = str(exc)
    # Livraison express : outil du forfait du commerce (payments/plan_features.py), seulement avec livraison.
    from payments.plan_features import store_has
    express_available = bool(delivery_requested and store_has(store, 'express_delivery'))
    delivery_type = delivery_type if delivery_type in ('standard', 'express') else 'standard'
    if delivery_type == 'express' and not express_available:
        blocking.append("La livraison express ne concerne que les commandes livrées : choisissez la livraison ou le mode standard."
                        if not delivery_requested else
                        "Ce commerce ne propose pas la livraison express : choisissez la livraison standard.")
        delivery_type = 'standard'

    def delivery_order(kind):
        return Order(store=store, city=city, delivery_zone=zone, delivery_type=kind,
                     delivery_requested=bool(delivery_requested))

    order = delivery_order(delivery_type)
    delivery_fee = None
    delivery_options = []
    if not delivery_requested:
        delivery_fee = Decimal('0')
    elif not message:
        delivery_fee = _franc(order.quote_delivery(pairs))
        if express_available:
            # Les deux prix côte à côte : le client voit ce que coûte l'express avant de choisir.
            fees_by_type = {delivery_type: delivery_fee}
            other = 'standard' if delivery_type == 'express' else 'express'
            fees_by_type[other] = _franc(delivery_order(other).quote_delivery(pairs))
            delivery_options = [
                {'type': 'standard', 'label': 'Standard', 'fee': str(fees_by_type['standard']),
                 'estimate': '2 à 3 h', 'selected': delivery_type == 'standard'},
                {'type': 'express', 'label': 'Express', 'fee': str(fees_by_type['express']),
                 'estimate': 'environ 1 h', 'selected': delivery_type == 'express'},
            ]
    if delivery_requested:
        address = [neighborhood.label] if neighborhood else [p for p in (zone, city) if p]
        if landmark is not None:
            address.append(f"près de {landmark.name}")
        if (details or '').strip():
            address.append(details.strip())
        delivery.update({
            'address': ' — '.join(address), 'city': city, 'price_zone': zone,
            'price_zone_rate': bool(zone and zone in zones),
            'vehicle': order.vehicle_type if delivery_fee is not None else '',
            'vehicle_label': _vehicle_label(order.vehicle_type) if delivery_fee is not None else '',
            'intercity': bool(delivery_fee is not None and store.city and city and store.city != city),
            'delivered_by': 'Le commerce' if delivery_by == 'store' else 'Un livreur Gaboshop',
            'fee': str(delivery_fee) if delivery_fee is not None else None,
            'type': delivery_type, 'is_express': delivery_type == 'express',
        })
    else:
        delivery.update({'address': f"Retrait au commerce : {store.address}".strip(), 'fee': '0'})

    # Paiement choisi et frais qui en dépendent.
    try:
        policy, options = available_payment_options(store, delivery_requested, user=user)
    except (DjangoValidationError, DRFValidationError) as exc:
        # Réglage de paiement incohérent (ex. paiement en ligne coché sans compte SingPay) : le devis reste lisible.
        policy, options = {}, []
        blocking.append(f"Paiement indisponible pour ce commerce : {_error_text(exc)}")
    option = matching_option(options, payment_flow, payment_method, delivery_by or '') if payment_flow else None
    if not options and policy:
        blocking.append("Aucun moyen de paiement n'est proposé pour ce commerce en ce moment.")
    elif options and not payment_flow:
        blocking.append('Choisissez un moyen de paiement dans la liste.')
    elif payment_flow and option is None and options:
        blocking.append("Ce moyen de paiement n'est pas proposé pour ce commerce : choisissez-en un autre dans la liste.")
    online = payment_flow == 'platform_online'
    fees = []
    operator_fee = forfait = small = Decimal('0')
    if delivery_fee is not None:
        order.items_total, order.delivery_fee = items_total, delivery_fee
        operator = 'moov' if payment_method == 'moov_money' else 'airtel'
        fee_method = payment_method if online else 'cash'  # comme OrderCreateSerializer.create
        operator_fee = _franc(order.calculate_operator_fee(operator=operator, payment_method=fee_method))
        if operator_fee > 0:
            fees.append({'label': f"Frais {METHOD_LABELS.get(payment_method, 'Mobile Money')}", 'amount': str(operator_fee)})
        if online and delivery_by != 'store' and user is not None and getattr(user, 'is_authenticated', False):
            forfait = min(_franc(delivery_discount(user, delivery_fee)), delivery_fee)
            if forfait > 0:
                fees.append({'label': 'Réduction de votre forfait livraison', 'amount': str(-forfait)})
        if online:
            small = _franc(small_order_fee(items_total))
            if small > 0:
                settings = SystemSettings.get_settings()
                fees.append({'label': f"Frais petit panier (articles sous {_money(settings.small_order_threshold)})",
                             'amount': str(small)})
    total = None
    if delivery_fee is not None:
        total = _franc(items_total + delivery_fee + operator_fee + small - forfait)

    # Chaque frais expliqué, même quand il vaut 0 ou ne s'applique pas : le client sait pourquoi.
    fee_details = _fee_details(
        online=online, payment_flow=payment_flow, method=payment_method, delivery_by=delivery_by,
        delivery_requested=bool(delivery_requested), items_total=items_total, delivery_fee=delivery_fee,
        operator_fee=operator_fee, small=small, forfait=forfait, user=user,
        has_forfait=bool(user is not None and getattr(user, 'is_authenticated', False)
                         and _has_forfait(user)),
    )

    # Ce qui bloquerait la commande, dit avant d'appuyer sur « Passer la commande ».
    if not store.is_active:
        blocking.append("Ce commerce n'est pas actif.")
    elif not store.is_verified:
        blocking.append('Ce commerce est en cours de vérification par Gaboshop et ne peut pas encore recevoir de commandes.')
    is_open = store.is_open()
    if not is_open:
        hours = _hours(store)
        blocking.append(f"Le commerce est fermé en ce moment{f' (horaires : {hours})' if hours else ''}. "
                        "Revenez pendant ses heures d'ouverture.")
    if store.min_order_amount and items_total < Decimal(store.min_order_amount):
        missing = Decimal(store.min_order_amount) - items_total
        blocking.append(f"Minimum de commande du commerce : {_money(store.min_order_amount)}. "
                        f"Ajoutez encore {_money(missing)} d'articles.")
    from django.core.exceptions import PermissionDenied
    from payments.subscription_check import SubscriptionChecker
    try:
        SubscriptionChecker.check_can_create_order(store)
    except PermissionDenied as exc:
        blocking.append(str(exc))
    app = SystemSettings.get_settings()
    if app.order_hours_enabled:
        from stores.models import within_hours
        if not within_hours(app.order_opening_time, app.order_closing_time):
            blocking.append(f"Les commandes sont ouvertes de {app.order_opening_time.strftime('%H:%M')} "
                            f"à {app.order_closing_time.strftime('%H:%M')}.")

    # Après la commande : ce que le client doit savoir.
    notes = []
    if delivery_requested:
        notes.append('Un code de livraison à 6 chiffres vous sera donné : ne le communiquez au livreur '
                     'qu’une fois le colis en main.')
    if online and not store.is_trusted:
        notes.append('Votre argent est gardé par Gaboshop : le commerce est payé après votre confirmation de réception.')
    notes.append('Un souci ? Ouvrez la commande et touchez « Signaler un problème » dans les 48 h après la livraison.')
    notes.append('Une facture PDF Gaboshop est disponible dès la commande passée.')

    payment = None
    if payment_flow:
        payment = {
            'flow': payment_flow, 'flow_label': FLOW_LABELS.get(payment_flow, payment_flow),
            'method': payment_method, 'method_label': METHOD_LABELS.get(payment_method, payment_method),
            'simulated': bool(option and option.get('simulated')),
            'split': _payment_lines(payment_flow, payment_method, delivery_by, delivery_requested, items_total,
                                    delivery_fee or Decimal('0'), operator_fee, total or Decimal('0'), policy)
            if total is not None else [],
        }

    return {
        # Champs historiques (écrans et application déjà installés).
        'delivery_fee': str(delivery_fee) if delivery_fee is not None else None,
        'vehicle_type': order.vehicle_type if delivery_fee is not None else '',
        'zone': zone, 'zones': zones, 'message': message,
        'small_order_fee_online': str(small_order_fee(items_total)),
        # Devis complet.
        'store': {
            'name': store.name, 'category': store.category.name if store.category_id else '',
            'phone': store.phone, 'address': store.address, 'city': store.city,
            'is_open': is_open, 'hours': _hours(store),
        },
        'lines': lines,
        'items_total': str(_franc(items_total)),
        'delivery': delivery,
        # Choix Standard / Express : proposé seulement quand le commerce a l'outil et que la commande est livrée.
        'express_available': express_available,
        'delivery_type': delivery_type,
        'delivery_options': delivery_options,
        'fees': fees,
        'fee_details': fee_details,
        'total': str(total) if total is not None else None,
        'payment': payment,
        'blocking': blocking,
        'notes': notes,
    }
