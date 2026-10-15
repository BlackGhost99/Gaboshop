"""Mise en avant payante (sponsoring) : un produit ou tout le commerce passe en tête des listes, marqué « Sponsorisé ».

Le commerce paie par Airtel Money ou Moov Money (SingPay) ; la mise en avant démarre quand SingPay confirme
le paiement. Tant que l'admin n'a pas allumé ``sponsoring_enabled``, l'offre est visible mais grisée.
"""
import logging
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Exists, OuterRef
from django.utils import timezone

logger = logging.getLogger(__name__)

MAX_WEEKS = 8
PRODUCT_TYPES = ('product', 'featured')  # « featured » : ancien type, créé par l'admin pour un produit
TARGETS = ('product', 'store')


class SponsoringError(Exception):
    def __init__(self, message, code=400, next_step=None):
        super().__init__(message)
        self.message, self.code, self.next_step = message, code, next_step


def offer():
    """Ce que voit le commerce : offre ouverte ou non, et les prix à la semaine."""
    from api.models import SystemSettings
    s = SystemSettings.get_settings()
    return {
        'enabled': bool(s.sponsoring_enabled),
        'max_weeks': MAX_WEEKS,
        'prices': {
            'product': str(_franc(s.sponsor_product_week_price)),
            'store': str(_franc(s.sponsor_store_week_price)),
        },
    }


def _franc(value):
    return Decimal(str(value or 0)).quantize(Decimal('1'), rounding=ROUND_HALF_UP)


def _live(now=None):
    now = now or timezone.now()
    from payments.models import SponsoredProduct
    return SponsoredProduct.objects.filter(status='active', start_date__lte=now, end_date__gt=now)


def sponsored_product_exists(now=None):
    """Annotation : ce produit est mis en avant en ce moment (à utiliser avec ``.annotate(sponsored_now=...)``)."""
    return Exists(_live(now).filter(product=OuterRef('pk'), sponsor_type__in=PRODUCT_TYPES))


def sponsored_store_exists(now=None):
    return Exists(_live(now).filter(store=OuterRef('pk'), sponsor_type='store'))


def _same_target(qs, sponsorship):
    if sponsorship.sponsor_type == 'store':
        return qs.filter(store_id=sponsorship.store_id, sponsor_type='store')
    return qs.filter(product_id=sponsorship.product_id, sponsor_type__in=PRODUCT_TYPES)


def activate(sponsorship, now=None):
    """Démarre la mise en avant ; si la même cible est déjà en avant, elle s'ajoute à la suite."""
    from payments.models import SponsoredProduct
    now = now or timezone.now()
    latest = _same_target(SponsoredProduct.objects.filter(status='active', end_date__gt=now), sponsorship) \
        .exclude(pk=sponsorship.pk).order_by('-end_date').values_list('end_date', flat=True).first()
    start = max(now, latest) if latest else now
    sponsorship.start_date = start
    sponsorship.end_date = start + timedelta(days=7 * max(1, sponsorship.weeks))
    sponsorship.status = 'active'
    sponsorship.save(update_fields=['start_date', 'end_date', 'status'])
    return sponsorship


def mine(store):
    """Mises en avant du commerce, les plus récentes d'abord."""
    from payments.models import SponsoredProduct
    now = timezone.now()
    rows = []
    for s in SponsoredProduct.objects.filter(store=store).select_related('product').order_by('-created_at')[:20]:
        state = s.status
        if state == 'active' and s.end_date and s.end_date <= now:
            state = 'expired'
        elif state == 'active' and s.start_date and s.start_date > now:
            state = 'scheduled'
        rows.append({
            'id': s.id, 'target': 'store' if s.sponsor_type == 'store' else 'product',
            'product_id': s.product_id, 'product_name': s.product.name if s.product_id else None,
            'weeks': s.weeks, 'price_paid': str(_franc(s.price_paid)), 'status': state,
            'start_date': s.start_date if s.status != 'pending_payment' else None, 'end_date': s.end_date,
        })
    return rows


def request_purchase(store, user, data):
    """Crée la mise en avant en attente et envoie la demande de paiement sur le téléphone du commerce.

    Retourne (sponsorship, intent) ; intent vaut None quand le prix est 0 (activée tout de suite)."""
    from api.models import SystemSettings
    from payments.models import PaymentIntent, PaymentTransaction, SponsoredProduct
    from payments.utils import call_airtel_money_init, call_moov_money_init, payment_request_minutes
    from products.models import Product

    settings = SystemSettings.get_settings()
    if not settings.sponsoring_enabled:
        raise SponsoringError('La mise en avant sera bientôt disponible.', 403,
                              'Gaboshop vous préviendra dès son ouverture.')
    if not (store.is_active and store.is_verified):
        raise SponsoringError('Votre commerce doit être validé par Gaboshop avant d’être mis en avant.', 403)

    target = str(data.get('target') or '').lower()
    if target not in TARGETS:
        raise SponsoringError('Choisissez : un produit ou tout le commerce.')
    try:
        weeks = int(data.get('weeks') or 1)
    except (TypeError, ValueError):
        raise SponsoringError('Nombre de semaines invalide.')
    if not 1 <= weeks <= MAX_WEEKS:
        raise SponsoringError(f'Choisissez entre 1 et {MAX_WEEKS} semaines.')

    product = None
    if target == 'product':
        product = Product.objects.filter(id=data.get('product_id'), store=store).first()
        if product is None:
            raise SponsoringError('Produit introuvable dans votre commerce.', 404)
        if not product.is_available or product.market_type not in ('b2c', 'both'):
            raise SponsoringError('Ce produit n’est pas visible par les clients : rendez-le disponible d’abord.')
        week_price = settings.sponsor_product_week_price
    else:
        week_price = settings.sponsor_store_week_price
    amount = _franc(week_price) * weeks

    if amount <= 0:
        with transaction.atomic():
            sponsorship = SponsoredProduct.objects.create(
                store=store, product=product, sponsor_type=target, weeks=weeks, price_paid=0,
                status='pending_payment', start_date=None)
            activate(sponsorship)
        return sponsorship, None

    operator = str(data.get('operator') or '').lower()
    phone = str(data.get('phone_number') or user.phone or '').strip().replace(' ', '')
    if operator not in ('airtel', 'moov'):
        raise SponsoringError('Choisissez Airtel Money ou Moov Money.')
    if not phone:
        raise SponsoringError('Indiquez le numéro Mobile Money qui va payer.')
    if phone.startswith('0'):
        phone = '+241' + phone[1:]

    with transaction.atomic():
        sponsorship = SponsoredProduct.objects.create(
            store=store, product=product, sponsor_type=target, weeks=weeks, price_paid=amount,
            status='pending_payment', start_date=None)
        intent = PaymentIntent.objects.create(
            user=user, amount=int(amount), currency='XAF', provider='singpay',
            expires_at=timezone.now() + timedelta(minutes=payment_request_minutes()),
            metadata={'purpose': 'sponsoring', 'sponsorship_id': sponsorship.id, 'store_id': store.id,
                      'operator': operator},
        )
        sponsorship.payment_reference = intent.reference
        sponsorship.save(update_fields=['payment_reference'])

    init = call_airtel_money_init if operator == 'airtel' else call_moov_money_init
    response = init(phone=phone, amount=intent.amount, reference=intent.reference, metadata=intent.metadata)
    intent.raw_response = response
    intent.status = 'PENDING' if isinstance(response, dict) and not response.get('error') else 'FAILED'
    intent.save()
    PaymentTransaction.objects.create(intent=intent, status=intent.status, raw_response=response)
    if intent.status == 'FAILED':
        sponsorship.status = 'cancelled'
        sponsorship.save(update_fields=['status'])
        raise SponsoringError('La demande de paiement n’a pas pu être envoyée.', 502,
                              'Vérifiez le numéro et le solde, puis réessayez dans quelques minutes.')
    return sponsorship, intent


def activate_from_intent(intent):
    """Appelé quand SingPay confirme le paiement. Idempotent : une seule activation par paiement."""
    from payments.models import SponsoredProduct
    meta = intent.metadata or {}
    if meta.get('sponsoring_activated'):
        return None
    with transaction.atomic():
        sponsorship = SponsoredProduct.objects.select_for_update().filter(
            id=meta.get('sponsorship_id'), store_id=meta.get('store_id')).first()
        if sponsorship is None or sponsorship.payment_reference != intent.reference:
            logger.warning("Sponsoring introuvable pour le paiement %s", intent.reference)
            return None
        if sponsorship.status != 'pending_payment' or int(sponsorship.price_paid) != int(intent.amount):
            logger.warning("Sponsoring %s non activé (statut %s, montant %s)", sponsorship.id,
                           sponsorship.status, intent.amount)
            return None
        activate(sponsorship)
        meta['sponsoring_activated'] = True
        intent.metadata = meta
        intent.save(update_fields=['metadata'])
    return sponsorship


def cancel_from_intent(intent):
    """Paiement refusé ou expiré : la mise en avant en attente est annulée."""
    from payments.models import SponsoredProduct
    meta = intent.metadata or {}
    SponsoredProduct.objects.filter(id=meta.get('sponsorship_id'), payment_reference=intent.reference,
                                    status='pending_payment').update(status='cancelled')
