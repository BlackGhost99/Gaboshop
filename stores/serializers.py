import re
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from urllib.parse import urlparse
from .models import StoreCategory, Store
from payments.plan_features import plan_for_sale, has, required_message, store_has

# Frais de livraison du commerce : jamais négatifs, plafonnés (FCFA).
DELIVERY_FEE_LIMITS = {
    'delivery_fee': {'min_value': 0, 'max_value': 100000},
    'delivery_fee_express': {'min_value': 0, 'max_value': 100000},
}

# Page de boutique personnalisée : champs réservés aux forfaits qui incluent l'outil « custom_page ».
CUSTOM_PAGE_FIELDS = ['accent_color', 'tagline', 'about', 'facebook_url', 'instagram_url', 'tiktok_url', 'website_url']
# Domaines acceptés par réseau (le lien doit mener au bon réseau) ; None = n'importe quel site web.
SOCIAL_DOMAINS = {
    'facebook_url': ('facebook.com', 'fb.com', 'fb.me', 'fb.watch'),
    'instagram_url': ('instagram.com', 'instagr.am'),
    'tiktok_url': ('tiktok.com',),
    'website_url': None,
}
SOCIAL_NAMES = {
    'facebook_url': 'Facebook', 'instagram_url': 'Instagram', 'tiktok_url': 'TikTok', 'website_url': 'site web',
}


def clean_link(field, value):
    """Adresse web propre : https:// ajouté si absent, http(s) seulement, bon domaine pour le réseau."""
    value = (value or '').strip()
    if not value:
        return ''
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9+.\-]*:', value):
        value = 'https://' + value.lstrip('/')
    parsed = urlparse(value)
    host = (parsed.hostname or '').lower()
    name = SOCIAL_NAMES[field]
    if parsed.scheme not in ('http', 'https') or '.' not in host or ' ' in value:
        raise serializers.ValidationError(_("Lien %(name)s invalide : copiez l'adresse complète depuis votre navigateur.") % {'name': name})
    domains = SOCIAL_DOMAINS[field]
    if domains and not any(host == d or host.endswith('.' + d) for d in domains):
        raise serializers.ValidationError(_("Ce lien ne mène pas à %(name)s : collez l'adresse de votre page %(name)s.") % {'name': name})
    if len(value) > 200:
        raise serializers.ValidationError(_('Lien trop long (200 caractères au maximum).'))
    return value


def custom_page_info(store):
    """État de l'outil pour l'écran du commerçant : actif, ou forfait à prendre pour l'obtenir."""
    plan = store.get_current_plan()
    if has(plan, 'custom_page'):
        return {'enabled': True, 'upgrade_hint': '', 'plan_name': ''}
    target = plan_for_sale(plan, lambda candidate: has(candidate, 'custom_page'))
    return {
        'enabled': False,
        'upgrade_hint': required_message('custom_page', plan),
        'plan_name': target.name if target is not None else '',
    }


class StoreCategorySerializer(serializers.ModelSerializer):
    store_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = StoreCategory
        fields = ['id', 'name', 'description', 'icon', 'is_active', 'store_count']

class StoreListSerializer(serializers.ModelSerializer):
    """Serializer pour la liste des magasins (données réduites)"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    is_open = serializers.BooleanField(read_only=True)
    total_products = serializers.IntegerField(read_only=True)
    sponsored = serializers.SerializerMethodField()
    
    class Meta:
        model = Store
        fields = [
            'id', 'name', 'category', 'category_name', 'city', 'zone', 
            'phone', 'logo', 'is_active', 'is_open', 'total_products',
            'offers_delivery', 'delivery_fee', 'min_order_amount', 'commission_rate',
            'subscription_plan', 'sponsored'
        ]

    def get_sponsored(self, obj):
        # Annoté par la liste publique ; ailleurs, pas de mention « Sponsorisé ».
        return bool(getattr(obj, 'sponsored_now', False))

class StoreDetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour un magasin spécifique"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    manager_name = serializers.SerializerMethodField()
    manager_details = serializers.SerializerMethodField()
    is_open = serializers.BooleanField(read_only=True)
    total_products = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Store
        fields = [
            'id', 'name', 'description', 'category', 'category_name',
            'manager', 'manager_name', 'manager_details', 'phone', 'email', 'address', 'city', 'zone',
            'latitude', 'longitude', 'logo', 'banner_image',
            'commission_rate', 'offers_delivery', 'delivery_fee', 'min_order_amount',
            'is_active', 'is_verified', 'is_open', 'total_products',
            'opening_time', 'closing_time', 'created_at',
            *CUSTOM_PAGE_FIELDS,
        ]
        read_only_fields = ['created_at', 'is_verified']
        extra_kwargs = DELIVERY_FEE_LIMITS
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Le commerçant (et l'admin) voient toujours leurs réglages, avec l'état de l'outil ; le public,
        # lui, ne les voit que tant que le forfait inclut l'outil : la personnalisation s'éteint avec lui.
        if self._can_see_manager_contact(instance):
            data['custom_page'] = custom_page_info(instance)
        elif not store_has(instance, 'custom_page'):
            for field in CUSTOM_PAGE_FIELDS:
                data[field] = ''
        # Livraison express : le panier du client sait s'il doit proposer le choix ; seul le commerçant voit ses frais.
        from delivery.express import express_info
        data['express_available'] = store_has(instance, 'express_delivery')
        if self._can_see_manager_contact(instance):
            data['express'] = express_info(instance)
        return data

    def _can_see_manager_contact(self, obj):
        # Le téléphone du magasin reste public ; les coordonnées personnelles du gérant, non.
        user = getattr(self.context.get('request'), 'user', None)
        if not user or not user.is_authenticated:
            return False
        return user.id == obj.manager_id or user.is_superuser or getattr(user, 'user_type', '') == 'admin'

    def get_manager_name(self, obj):
        if obj.manager.first_name and obj.manager.last_name:
            return f"{obj.manager.first_name} {obj.manager.last_name}"
        return obj.manager.phone if self._can_see_manager_contact(obj) else ''

    def get_manager_details(self, obj):
        private = self._can_see_manager_contact(obj)
        return {
            'first_name': obj.manager.first_name,
            'last_name': obj.manager.last_name,
            'email': obj.manager.email if private else '',
            'phone': obj.manager.phone if private else '',
        }

class StoreCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création de magasin"""
    class Meta:
        model = Store
        fields = [
            'name', 'description', 'category', 'phone', 'email', 
            'address', 'zone', 'latitude', 'longitude', 'logo',
            'opening_time', 'closing_time', 'delivery_fee', 'min_order_amount'
        ]
        extra_kwargs = DELIVERY_FEE_LIMITS
    
    def validate(self, attrs):
        user = self.context['request'].user
        
        # Vérifier que l'utilisateur est un store_manager
        if not getattr(user, 'is_store_manager', lambda: False)():
            raise serializers.ValidationError({
                'user': _('Seuls les commerçants peuvent créer des magasins.')
            })
        
        # Assigner automatiquement le manager
        attrs['manager'] = user
        
        return attrs

class StoreUpdateSerializer(serializers.ModelSerializer):
    """Serializer pour la mise à jour de magasin"""
    # Liens saisis en texte libre (le https:// est ajouté s'il manque) puis contrôlés par validate_*.
    facebook_url = serializers.CharField(required=False, allow_blank=True, max_length=300)
    instagram_url = serializers.CharField(required=False, allow_blank=True, max_length=300)
    tiktok_url = serializers.CharField(required=False, allow_blank=True, max_length=300)
    website_url = serializers.CharField(required=False, allow_blank=True, max_length=300)

    class Meta:
        model = Store
        fields = [
            'name', 'description', 'phone', 'email', 'address', 
            'zone', 'latitude', 'longitude', 'logo', 'banner_image',
            'opening_time', 'closing_time', 'offers_delivery', 'delivery_fee', 'delivery_fee_express', 'min_order_amount',
            'agent_code', 'payout_phone', 'stock_alert_threshold',
            *CUSTOM_PAGE_FIELDS,
        ]
        extra_kwargs = {
            **DELIVERY_FEE_LIMITS,
            'stock_alert_threshold': {'max_value': 1000},
            'accent_color': {'error_messages': {'max_length': 'Couleur invalide : indiquez un code hexadécimal à 6 chiffres, par exemple #1E40AF.'}},
            'tagline': {'error_messages': {'max_length': 'Le message d\'accueil est limité à 120 caractères.'}},
            'about': {'error_messages': {'max_length': 'La présentation est limitée à 2000 caractères.'}},
        }

    def validate_accent_color(self, value):
        value = (value or '').strip()
        if value and not re.fullmatch(r'#[0-9A-Fa-f]{6}', value):
            raise serializers.ValidationError(_('Couleur invalide : indiquez un code hexadécimal à 6 chiffres, par exemple #1E40AF.'))
        return value.upper()

    def validate_tagline(self, value):
        return ' '.join((value or '').split())

    def validate_about(self, value):
        return (value or '').strip()

    def validate_facebook_url(self, value):
        return clean_link('facebook_url', value)

    def validate_instagram_url(self, value):
        return clean_link('instagram_url', value)

    def validate_tiktok_url(self, value):
        return clean_link('tiktok_url', value)

    def validate_website_url(self, value):
        return clean_link('website_url', value)

    def validate(self, attrs):
        from delivery.express import check_express_fee_update
        check_express_fee_update(self.instance, attrs)
        # Personnaliser la vitrine fait partie de certains forfaits : toute modification est refusée sans l'outil
        # (renvoyer une valeur inchangée reste permis, pour ne pas bloquer un formulaire complet).
        store = self.instance
        changed = [f for f in CUSTOM_PAGE_FIELDS if f in attrs and attrs[f] != (getattr(store, f, '') or '')]
        if changed and store is not None and not store_has(store, 'custom_page'):
            message = required_message('custom_page', store.get_current_plan())
            raise serializers.ValidationError({field: [message] for field in changed})
        return attrs

    def validate_agent_code(self, value):
        value = (value or '').strip()
        if value and not re.fullmatch(r'[A-Za-z0-9_.\-]{3,100}', value):
            raise serializers.ValidationError(_('Code agent invalide (lettres, chiffres, - _ . uniquement).'))
        return value

    def validate_payout_phone(self, value):
        digits = re.sub(r'\D', '', value or '')
        if not digits:
            return ''
        if len(digits) == 11 and digits.startswith('241'):
            digits = digits[3:]
        if len(digits) == 8:
            digits = '0' + digits
        if not re.fullmatch(r'0[67]\d{7}', digits):
            raise serializers.ValidationError(
                _('Numéro Mobile Money invalide : un numéro Airtel (074, 076, 077) ou Moov (060, 062, 065, 066).')
            )
        return '+241' + digits[1:]
        
