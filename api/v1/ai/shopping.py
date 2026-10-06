"""
Assistant d'achat Gaboshop.

Cherche dans le catalogue à partir de la question du client et répond avec de
vrais produits. Fonctionne sans aucune clé (réponses simples) ; avec une clé
gratuite Groq (GROQ_API_KEY), la réponse est rédigée naturellement par l'IA.
Ouvert aux visiteurs, avec une limite de messages par minute.
"""
import json
import re
import unicodedata

from django.db.models import Q
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

from products.models import Product
from .providers import AIProvider

MAX_RESULTS = 6

STOPWORDS = {
    'je', 'j', 'tu', 'il', 'elle', 'on', 'nous', 'vous', 'ils', 'elles', 'me', 'moi', 'te', 'se', 'mon', 'ma',
    'mes', 'ton', 'ta', 'tes', 'son', 'sa', 'ses', 'le', 'la', 'les', 'l', 'un', 'une', 'des', 'du', 'de', 'd',
    'au', 'aux', 'et', 'ou', 'a', 'en', 'pour', 'par', 'avec', 'sans', 'sur', 'dans', 'chez', 'que', 'qui',
    'quoi', 'quel', 'quelle', 'quels', 'quelles', 'est', 'sont', 'ce', 'cet', 'cette', 'ces', 'ca', 'cela',
    'y', 'ne', 'pas', 'plus', 'moins', 'tres', 'bien', 'bon', 'bonne', 'veux', 'voudrais', 'aimerais',
    'cherche', 'chercher', 'recherche', 'besoin', 'acheter', 'achete', 'trouver', 'trouve', 'avez', 'avoir',
    'ai', 'as', 'a', 'il', 'y', 'montre', 'montrez', 'propose', 'proposez', 'donne', 'donnez', 'svp', 'stp',
    'merci', 'bonjour', 'salut', 'bonsoir', 'hello', 'prix', 'cout', 'coute', 'combien', 'fcfa', 'cfa', 'f',
    'xaf', 'francs', 'franc', 'max', 'maximum', 'minimum', 'budget', 'cher', 'pas', 'peu', 'produit',
    'produits', 'article', 'articles', 'disponible', 'disponibles', 'stock', 'vend', 'vendez', 'gaboshop',
    'peux', 'pouvez', 'est-ce', 'comment', 'faire', 'quand', 'ou', 'autre', 'autres', 'encore', 'aussi',
    'genre', 'type', 'marque', 'taille', 'pointure', 'couleur', 'mettre', 'panier', 'commander',
}

# Petites questions : réponse fixe, vraie pour toute la plateforme.
FAQ = [
    (('livr', 'livreur', 'expedi', 'frais de port'),
     "La livraison dépend du commerce : chaque boutique fixe ses frais, affichés au moment de la commande. "
     "Vous pouvez choisir Standard (2-3 h) ou Express (1 h) quand le commerce les propose."),
    (('pay', 'paie', 'paiement', 'airtel', 'moov', 'mobile money', 'momo', 'regler', 'reglement'),
     "Le paiement se fait par Mobile Money (Airtel Money ou Moov Money) au moment de valider votre commande."),
    (('suivi', 'suivre', 'ou en est', 'ma commande', 'mes commandes', 'statut'),
     "Vous suivez vos commandes dans votre espace client, rubrique « Mes commandes ». "
     "Vous recevez aussi une notification à chaque étape."),
    (('inscri', 'compte', 'connect', 'mot de passe'),
     "Pour acheter, créez un compte gratuit avec « S'inscrire » en haut de la page, ou connectez-vous avec « Connexion »."),
    (('rembours', 'retour', 'annul', 'reclamation', 'probleme avec'),
     "Pour une annulation ou un problème sur une commande, contactez le commerce depuis votre espace client, "
     "ou l'équipe Gaboshop si le problème persiste."),
    (('horaire', 'ouvert', 'ferme', 'heure'),
     "Les horaires d'ouverture sont affichés sur la page de chaque commerce."),
]


def _plain(text):
    text = unicodedata.normalize('NFKD', text or '').encode('ascii', 'ignore').decode().lower()
    return re.sub(r'\s+', ' ', text).strip()


def _amount(raw):
    raw = raw.replace(' ', '').replace('.', '').replace(',', '')
    if raw.endswith('k'):
        return int(raw[:-1]) * 1000
    return int(raw) if raw.isdigit() else None


def extract_criteria(message):
    """Mots-clés et budget tirés d'une phrase comme « baskets nike moins de 20 000 F »."""
    text = _plain(message)
    max_price = min_price = None
    num = r'(\d+(?:[ .,]\d{3})*(?:k\b)?)'
    m = re.search(r"(?:moins de|max(?:imum)?|pas plus de|jusqu'a|budget(?: de)?|<|inferieur a)\s*" + num, text)
    if m:
        max_price = _amount(m.group(1))
    m = re.search(r"(?<!pas )(?:plus de|au moins|minimum|>|superieur a)\s*" + num, text)
    if m:
        min_price = _amount(m.group(1))
    words = re.findall(r"[a-z0-9]+", re.sub(num, ' ', text))
    keywords = []
    for w in words:
        if w in STOPWORDS or len(w) < 3 or w.isdigit():
            continue
        if w not in keywords:
            keywords.append(w)
    return {'keywords': keywords[:6], 'max_price': max_price, 'min_price': min_price}


def _stem(word):
    return word[:-1] if len(word) > 4 and word[-1] in 'sx' else word


def search_catalog(criteria, limit=MAX_RESULTS):
    keywords = [_stem(k) for k in criteria.get('keywords') or []]
    qs = Product.objects.filter(
        is_available=True, store__is_active=True, market_type__in=['b2c', 'both'],
    ).select_related('store', 'category')
    if criteria.get('max_price'):
        qs = qs.filter(price__lte=criteria['max_price'])
    if criteria.get('min_price'):
        qs = qs.filter(price__gte=criteria['min_price'])
    if criteria.get('store_id'):
        qs = qs.filter(store_id=criteria['store_id'])
    if criteria.get('in_stock'):
        qs = qs.filter(stock__gt=0)
    if criteria.get('brand'):
        b = str(criteria['brand'])
        qs = qs.filter(Q(attributes__brand__icontains=b) | Q(name__icontains=b) | Q(description__icontains=b))
    if criteria.get('size'):
        qs = qs.filter(attributes__sizes__icontains=str(criteria['size']))
    if keywords:
        cond = Q()
        for k in keywords:
            cond |= (Q(name__icontains=k) | Q(description__icontains=k)
                     | Q(category__name__icontains=k) | Q(store__name__icontains=k)
                     | Q(attributes__brand__icontains=k) | Q(attributes__model__icontains=k)
                     | Q(attributes__color__icontains=k))
        qs = qs.filter(cond)
    elif not any(criteria.get(k) for k in ('max_price', 'min_price', 'brand', 'size', 'store_id')):
        return []

    candidates = list(qs[:80])

    def score(p):
        name, desc = _plain(p.name), _plain(p.description)
        extra = _plain(' '.join([p.category.name if p.category else '', p.store.name,
                                 ' '.join(str(v) for v in (p.attributes or {}).values())]))
        s = 0
        for k in keywords:
            s += 3 if k in name else (2 if k in extra else (1 if k in desc else 0))
        return (s, 1 if p.stock > 0 else 0, -float(p.price))

    candidates.sort(key=score, reverse=True)
    return candidates[:limit]


def product_payload(p, request=None):
    image = None
    if p.image:
        try:
            image = p.image.url
            if request is not None and image.startswith('/'):
                image = request.build_absolute_uri(image)
        except ValueError:
            image = None
    attrs = p.attributes or {}
    return {
        'id': p.id,
        'name': p.name,
        'price': float(p.price),
        'compare_price': float(p.compare_price) if p.compare_price else None,
        'stock': p.stock,
        'image': image,
        'store': p.store_id,
        'store_name': p.store.name,
        'store_zone': p.store.zone,
        'category_name': p.category.name if p.category else None,
        'brand': attrs.get('brand'),
        'sizes': attrs.get('sizes'),
        'color': attrs.get('color'),
    }


def faq_answer(message):
    text = _plain(message)
    for needles, answer in FAQ:
        if any(n in text for n in needles):
            return answer
    return None


def _price(value):
    return f"{int(round(value)):,}".replace(',', ' ') + ' FCFA'


def local_reply(message, products, criteria, faq):
    """Réponse sans IA externe."""
    if products:
        n = len(products)
        cheapest = min(p['price'] for p in products)
        stores = sorted({p['store_name'] for p in products})
        where = stores[0] if len(stores) == 1 else f"{len(stores)} commerces"
        found = (f"J'ai trouvé {n} produit{'s' if n > 1 else ''} chez {where}, "
                 f"à partir de {_price(cheapest)}. Touchez un produit pour voir sa fiche et l'ajouter au panier.")
        return (faq + "\n\n" if faq else '') + found
    if faq:
        return faq
    text = _plain(message)
    if re.search(r'\b(bonjour|salut|bonsoir|hello|coucou)\b', text) and not criteria['keywords']:
        return ("Bonjour ! Je suis l'assistant Gaboshop. Dites-moi ce que vous cherchez "
                "(par exemple « riz moins de 5000 F » ou « baskets taille 42 ») et je vous montre les produits.")
    if criteria['keywords']:
        return (f"Je n'ai trouvé aucun produit pour « {' '.join(criteria['keywords'])} ». "
                "Essayez un autre mot, plus simple, ou un budget différent.")
    return ("Je peux chercher des produits pour vous et répondre aux questions sur la livraison, "
            "le paiement ou vos commandes. Que cherchez-vous ?")


SYSTEM_PROMPT = """Tu es l'assistant d'achat de Gaboshop, une place de marché en ligne au Gabon (Libreville).
Tu aides les clients à trouver des produits et tu réponds aux petites questions.
Règles :
- Réponds en français simple, en 1 à 4 phrases courtes, avec un ton chaleureux.
- Ne cite QUE les produits de la liste fournie, avec leur prix en FCFA et le commerce. N'invente jamais de produit, de prix ni de stock.
- Si la liste est vide, dis-le simplement et propose de reformuler.
- Pour la livraison, le paiement ou les commandes, utilise uniquement les informations fournies.
- Les produits s'affichent sous ta réponse : invite le client à toucher un produit pour voir sa fiche.
- Si la question n'a rien à voir avec les achats, réponds brièvement puis ramène la conversation sur les achats."""


def keywords_from_ai(message, config):
    """Demande à l'IA des mots-clés de recherche quand la recherche simple ne trouve rien."""
    raw = AIProvider.call_ai(
        "Tu transformes une demande d'achat en mots-clés de recherche. Réponds UNIQUEMENT en JSON.",
        f'Demande : "{message}"\nDonne {{"keywords": [3 à 5 mots simples en français au singulier, '
        f'dont des synonymes], "max_price": nombre ou null}}',
        config,
    )
    if not raw:
        return None
    m = re.search(r'\{.*\}', raw, re.DOTALL)
    try:
        data = json.loads(m.group()) if m else None
    except (ValueError, AttributeError):
        return None
    if not isinstance(data, dict):
        return None
    words = [_plain(str(w)) for w in data.get('keywords') or [] if str(w).strip()]
    max_price = data.get('max_price')
    return {
        'keywords': [w for w in words if w and w not in STOPWORDS][:6],
        'max_price': max_price if isinstance(max_price, (int, float)) and max_price > 0 else None,
        'min_price': None,
    }


def ai_reply(message, history, products, faq, config):
    facts = "\n".join(answer for _, answer in FAQ)
    convo = "\n".join(
        f"{'Client' if h.get('role') == 'user' else 'Assistant'} : {str(h.get('text', ''))[:300]}"
        for h in history[-6:] if isinstance(h, dict)
    )
    listing = json.dumps([
        {k: p[k] for k in ('name', 'price', 'compare_price', 'stock', 'store_name', 'store_zone',
                           'category_name', 'brand', 'sizes', 'color') if p.get(k) not in (None, '')}
        for p in products
    ], ensure_ascii=False)
    user_message = (
        f"Informations Gaboshop :\n{facts}\n\n"
        + (f"Conversation récente :\n{convo}\n\n" if convo else '')
        + f"Produits trouvés dans le catalogue pour cette question :\n{listing}\n\n"
        + f"Question du client : {message}"
    )
    return AIProvider.call_ai(SYSTEM_PROMPT, user_message, config)


class _SafeThrottleMixin:
    # Si le cache (Redis) est indisponible, on laisse passer plutôt que de planter.
    def allow_request(self, request, view):
        try:
            return super().allow_request(request, view)
        except Exception:
            return True


class ShopAnonThrottle(_SafeThrottleMixin, AnonRateThrottle):
    rate = '20/min'


class ShopUserThrottle(_SafeThrottleMixin, UserRateThrottle):
    rate = '30/min'


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@throttle_classes([ShopAnonThrottle, ShopUserThrottle])
def ai_shop(request):
    """
    POST /api/v1/ai/shop/
    Body : {"message": "...", "history": [{"role": "user"|"bot", "text": "..."}]}
    Réponse : {"success": true, "data": {"message": "...", "products": [...], "provider": "local"|"groq"|...}}
    """
    message = str(request.data.get('message', '')).strip()[:500]
    history = request.data.get('history') or []
    if not isinstance(history, list):
        history = []
    if not message:
        return Response({'success': False, 'error': {'message': 'Écrivez votre question.'}},
                        status=status.HTTP_400_BAD_REQUEST)

    config = AIProvider.get_provider_config()
    use_ai = config.get('available') and config.get('name') != 'local'

    criteria = extract_criteria(message)
    faq = faq_answer(message)
    found = search_catalog(criteria) if not faq or criteria['keywords'] else []
    if not found and use_ai and not faq and criteria['keywords']:
        better = keywords_from_ai(message, config)
        if better and better['keywords']:
            criteria = {**better, 'max_price': better['max_price'] or criteria['max_price'],
                        'min_price': criteria['min_price']}
            found = search_catalog(criteria)

    products = [product_payload(p, request) for p in found]

    reply = ai_reply(message, history, products, faq, config) if use_ai else None
    provider = config['name'] if reply else 'local'
    if not reply:
        reply = local_reply(message, products, criteria, faq)

    return Response({'success': True, 'data': {
        'message': reply.strip(),
        'products': products,
        'provider': provider,
    }})
