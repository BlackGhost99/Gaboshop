from rest_framework import serializers
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from django.db import transaction
from stores.models import Store, StoreCategory
from .models import User, UserProfile, GerantProfile, LivreurProfile

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
            'user_type', 'city', 'is_verified', 'is_available', 'current_location',
            'profile', 'date_joined'
        ]
        read_only_fields = ['id', 'date_joined', 'is_verified']

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
    
    class Meta:
        model = User
        fields = [
            'phone', 'email', 'first_name', 'last_name', 'user_type',
            'password', 'password_confirm', 'address', 'city', 'zone',
            'store_name', 'store_category_id', 'store_phone', 'store_address', 'store_city', 'store_zone', 'store_min_order_amount',
            'vehicle_type', 'vehicle_plate'
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
            # store_phone est optionnel (fallback sur user.phone)
            required_fields = ['store_name', 'store_address', 'store_zone']
            missing = [f for f in required_fields if not attrs.get(f)]
            if missing:
                raise serializers.ValidationError({
                    'store': _(f'Champs requis pour le magasin: {", ".join(missing)}')
                })
        if user_type == 'delivery_agent':
            if not attrs.get('vehicle_plate'):
                raise serializers.ValidationError({
                    'vehicle_plate': _('Immatriculation du véhicule requise pour le livreur.')
                })
            if not attrs.get('vehicle_type'):
                attrs['vehicle_type'] = 'moto'

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
                if store_payload['category_id']:
                    category = StoreCategory.objects.filter(id=store_payload['category_id']).first()
                if not category:
                    category = StoreCategory.objects.order_by('id').first()
                if not category:
                    category = StoreCategory.objects.create(name='Général')

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
                GerantProfile.objects.get_or_create(user=user)
                # Option: marquer store actif mais non vérifié
                store.is_active = True
                store.is_verified = False
                store.save(update_fields=['is_active', 'is_verified'])

            # Cas livreur: créer profil livreur
            if user.user_type == 'delivery_agent':
                LivreurProfile.objects.create(
                    user=user,
                    type_vehicule=vehicle_type,
                    immatriculation=vehicle_plate,
                    disponible=True,
                    documents_verifies=False,
                )

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
