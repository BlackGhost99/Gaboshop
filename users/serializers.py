from rest_framework import serializers
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from django.db import transaction
from stores.models import Store, StoreCategory
from .models import User, UserProfile, GerantProfile, LivreurProfile
from .mobile_money import normalize_mobile_money
from .models import DeliveryAgentApiKey

# Choices réutilisables pour les véhicules livreur
VEHICLE_CHOICES = [
    ('moto', 'Moto'),
    ('scooter', 'Scooter'),
    ('velo', 'Vélo'),
    ('voiture', 'Voiture'),
]

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            'address', 'city', 'zone', 'date_of_birth', 
            'profile_picture', 'preferred_payment_method'
        ]
        read_only_fields = ['user']

class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'phone', 'email', 'first_name', 'last_name', 
            'user_type', 'city', 'is_verified', 'is_available', 'current_location', 'singpay_disbursement_id',
            'profile', 'date_joined'
        ]
        read_only_fields = ['id', 'date_joined', 'is_verified']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Un compte superutilisateur / staff (ex. créé avec createsuperuser, dont le
        # user_type reste « client » par défaut) est l'administrateur : le frontend
        # l'envoie vers l'espace admin. Les permissions admin du backend acceptent déjà is_staff.
        if instance.is_superuser or instance.is_staff:
            data['user_type'] = 'admin'
        return data

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True, min_length=6)
    
    # Champs pour le profil
    address = serializers.CharField(write_only=True, required=False, allow_blank=True)
    city = serializers.CharField(write_only=True, required=False, default="Libreville")
    zone = serializers.CharField(write_only=True, required=False, allow_blank=True)

    # Champs pour gérant (création magasin obligatoire)
    store_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    # store_category_id peut être vide ("") venant du frontend, donc on utilise CharField et on convertit
    store_category_id = serializers.CharField(write_only=True, required=False, allow_blank=True)
    store_phone = serializers.CharField(write_only=True, required=False, allow_blank=True)
    store_address = serializers.CharField(write_only=True, required=False, allow_blank=True)
    store_city = serializers.CharField(write_only=True, required=False, default="Libreville")
    store_zone = serializers.CharField(write_only=True, required=False, allow_blank=True)
    store_min_order_amount = serializers.DecimalField(write_only=True, required=False, max_digits=8, decimal_places=2)

    # Champs pour livreur
    vehicle_type = serializers.ChoiceField(choices=VEHICLE_CHOICES, write_only=True, required=False)
    vehicle_plate = serializers.CharField(write_only=True, required=False, allow_blank=True)
    # Numéro où le livreur reçoit ses gains (obligatoire pour un livreur)
    mobile_money_phone = serializers.CharField(write_only=True, required=False, allow_blank=True)
    # GPS requis pour les livreurs
    # max_digits=18 permet jusqu'à 18 chiffres au total (ex: 180.123456789012345 = 18 chiffres)
    # decimal_places=15 permet jusqu'à 15 décimales pour la précision GPS
    position_lat = serializers.DecimalField(write_only=True, required=False, allow_null=True, max_digits=18, decimal_places=15)
    position_lng = serializers.DecimalField(write_only=True, required=False, allow_null=True, max_digits=18, decimal_places=15)
    
    class Meta:
        model = User
        fields = [
            'phone', 'email', 'first_name', 'last_name', 'user_type',
            'password', 'password_confirm', 'address', 'city', 'zone',
            'store_name', 'store_category_id', 'store_phone', 'store_address', 'store_city', 'store_zone', 'store_min_order_amount',
            'vehicle_type', 'vehicle_plate', 'mobile_money_phone', 'position_lat', 'position_lng'
        ]
    
    def validate(self, attrs):
        
        # Validation et normalisation du numéro de téléphone (comme Login)
        phone = attrs.get('phone', '').strip().replace(' ', '')
        
        if phone.startswith('+241'):
            phone = phone
        elif phone.startswith('241'):
            phone = '+' + phone
        elif phone.startswith('0'):
            phone = '+241' + phone[1:]
        elif phone.isdigit() and len(phone) == 8:
            phone = '+241' + phone
        else:
             # Fallback pour autres formats ou échec
             if not phone.startswith('+241') and not phone.startswith('0'):
                raise serializers.ValidationError({
                    'phone': _('Le numéro doit être au format Gabon: +241... ou 0...')
                })
        
        attrs['phone'] = phone
        
        # Validation mot de passe
        if attrs['password'] != attrs.pop('password_confirm'):
            raise serializers.ValidationError({
                'password': _('Les mots de passe ne correspondent pas.')
            })
        
        # Validation type utilisateur
        user_type = attrs.get('user_type')
        if user_type not in ['client', 'store_manager', 'delivery_agent']:
            raise serializers.ValidationError({
                'user_type': _('Type d\'utilisateur invalide.')
            })

        # Contraintes spécifiques
        if user_type == 'store_manager':

            required_fields = ['store_name', 'store_address', 'store_zone']
            missing = [f for f in required_fields if not attrs.get(f)]
            if missing:
                raise serializers.ValidationError({
                    'store': _(f'Champs requis pour le magasin: {", ".join(missing)}')
                })
            # Remove GPS fields for non-delivery users
            attrs.pop('position_lat', None)
            attrs.pop('position_lng', None)
        elif user_type == 'client':
            # Remove GPS fields for non-delivery users
            attrs.pop('position_lat', None)
            attrs.pop('position_lng', None)
        if user_type == 'delivery_agent':

            if not attrs.get('vehicle_plate'):
                raise serializers.ValidationError({
                    'vehicle_plate': _('Immatriculation du véhicule requise pour le livreur.')
                })
            if not (attrs.get('mobile_money_phone') or '').strip():
                raise serializers.ValidationError({
                    'mobile_money_phone': _('Numéro Mobile Money requis : vos gains de livraison y sont envoyés.')
                })
            try:
                attrs['mobile_money_phone'] = normalize_mobile_money(attrs['mobile_money_phone'])
            except ValueError as exc:
                raise serializers.ValidationError({'mobile_money_phone': str(exc)})
            if not attrs.get('vehicle_type'):
                attrs['vehicle_type'] = 'moto'
            # GPS activation required at signup for delivery agents
            position_lat = attrs.get('position_lat')
            position_lng = attrs.get('position_lng')
            if not position_lat or not position_lng:
                raise serializers.ValidationError({
                    'gps': _('Les coordonnées GPS (position_lat, position_lng) sont requises pour l\'inscription des livreurs.')
                })
        

        # Optional email uniqueness check: avoid multiple accounts with same email
        email = attrs.get('email', '').strip() if attrs.get('email') else ''
        if email:
            if User.objects.filter(email__iexact=email).exists():
                raise serializers.ValidationError({
                    'email': _('Un compte utilisant cet email existe déjà.')
                })
        
        return attrs
    
    def create(self, validated_data):

        # Extraire les données du profil
        profile_data = {
            'address': validated_data.pop('address', ''),
            'city': validated_data.get('city', 'Libreville'),
            'zone': validated_data.pop('zone', ''),
        }

        # Extraire données magasin / livreur
        store_payload = {
            'name': validated_data.pop('store_name', ''),
            'category_id': validated_data.pop('store_category_id', None),
            'phone': validated_data.pop('store_phone', ''),
            'address': validated_data.pop('store_address', ''),
            'city': validated_data.pop('store_city', 'Libreville'),
            'zone': validated_data.pop('store_zone', ''),
            'min_order_amount': validated_data.pop('store_min_order_amount', None),
        }
        vehicle_type = validated_data.pop('vehicle_type', 'moto')
        vehicle_plate = validated_data.pop('vehicle_plate', '')
        mobile_money_phone = validated_data.pop('mobile_money_phone', '')

        with transaction.atomic():
            # Créer l'utilisateur
            user = User.objects.create_user(
                phone=validated_data['phone'],
                email=validated_data.get('email', ''),
                password=validated_data['password'],
                first_name=validated_data.get('first_name', ''),
                last_name=validated_data.get('last_name', ''),
                user_type=validated_data.get('user_type', 'client'),
                city=validated_data.get('city', 'Libreville')
            )

            # Créer le profil commun
            UserProfile.objects.create(user=user, **profile_data)

            # Cas gérant: créer un magasin minimal
            if user.user_type == 'store_manager':

                category = None
                try:
                    if store_payload['category_id']:
                        category = StoreCategory.objects.filter(id=store_payload['category_id']).first()
                    if not category:
                        category = StoreCategory.objects.order_by('id').first()
                    if not category:
                        category = StoreCategory.objects.create(name='Général')
                except Exception as e:
                    raise

                from api.models import SystemSettings
                app_settings = SystemSettings.get_settings()
                try:
                    store = Store.objects.create(
                        name=store_payload['name'],
                        description='Magasin auto-créé lors de l\'inscription',
                        category=category,
                        manager=user,
                        phone=store_payload['phone'] or user.phone,
                        email=user.email,
                        address=store_payload['address'],
                        city=store_payload['city'],
                        zone=store_payload['zone'] or 'Libreville',
                        min_order_amount=store_payload['min_order_amount'] or 0,
                    )
                except Exception as e:
                    raise
                GerantProfile.objects.get_or_create(user=user)
                # Réglage admin : un nouveau commerce peut attendre l'activation par l'admin.
                store.is_active = not app_settings.store_verification_required
                store.is_verified = False
                store.save(update_fields=['is_active', 'is_verified'])

            # Cas livreur: créer profil livreur
            if user.user_type == 'delivery_agent':
                # Create LivreurProfile with provided GPS
                from django.utils import timezone
                # Le profil vide existe déjà (signal users.signals) : on le complète.
                LivreurProfile.objects.update_or_create(
                    user=user,
                    defaults=dict(
                        type_vehicule=vehicle_type,
                        immatriculation=vehicle_plate,
                        mobile_money_phone=mobile_money_phone,
                        disponible=True,
                        documents_verifies=False,
                        position_lat=validated_data.get('position_lat'),
                        position_lng=validated_data.get('position_lng'),
                        last_position_update=timezone.now(),
                    ),
                )
                # Create an API key for the delivery agent so mobile client can authenticate
                try:
                    DeliveryAgentApiKey.create_for_user(user)
                except Exception:
                    pass

            # Cas client: rien de plus

        return user

class LoginSerializer(serializers.Serializer):
    phone = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        phone = attrs.get('phone', '').strip().replace(' ', '')
        password = attrs.get('password')
        
        # Normalisation téléphone (formats acceptés: +241xxxxxx, 241xxxxxx, 0xxxxxxx, xxxxxxxx)
        if phone.startswith('+241'):
            phone = phone
        elif phone.startswith('241'):
            phone = '+' + phone
        elif phone.startswith('0'):
            phone = '+241' + phone[1:]
        elif phone.isdigit() and len(phone) == 8:
            phone = '+241' + phone
        
        user = authenticate(request=self.context.get('request'), phone=phone, password=password)
        
        if not user:
            raise serializers.ValidationError(_('Numéro de téléphone ou mot de passe incorrect.'))
        
        if not user.is_active:
            raise serializers.ValidationError(_('Ce compte est désactivé.'))
        
        attrs['user'] = user
        return attrs

class UserUpdateSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer()
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'profile'
        ]
    
    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', {})
        
        # Mettre à jour l'utilisateur
        instance = super().update(instance, validated_data)
        
        # Mettre à jour le profil
        if profile_data:
            profile_serializer = UserProfileSerializer(
                instance.profile, 
                data=profile_data, 
                partial=True
            )
            if profile_serializer.is_valid():
                profile_serializer.save()
        
        return instance
