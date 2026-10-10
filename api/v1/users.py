from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _

from users.serializers import (
	UserSerializer, RegisterSerializer, LoginSerializer, 
	UserUpdateSerializer
)
from users.models import User
from users.throttles import AuthIPThrottle, LoginPhoneThrottle
from core.models import AuditLog
from users.models import DeliveryAgentApiKey
from rest_framework import permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

class RegisterView(APIView):
	permission_classes = [permissions.AllowAny]
	throttle_classes = [AuthIPThrottle]

	def post(self, request):
		serializer = RegisterSerializer(data=request.data)

		if serializer.is_valid():
			try:
				user = serializer.save()
			except Exception as e:
				return Response({
					'success': False,
					'error': {
						'code': status.HTTP_500_INTERNAL_SERVER_ERROR,
						'message': 'Erreur interne lors de la création du compte.',
						'details': str(e)
					}
				}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
			# Log user registration
			AuditLog.log_action(
				action_type='user_registered',
				user=user,
				object_type='user',
				object_id=user.id,
				old_value=None,
				new_value=user.user_type,
				ip_address=request.META.get('REMOTE_ADDR'),
				user_agent=request.META.get('HTTP_USER_AGENT', ''),
				reason=f'Inscription: {user.username} ({user.user_type})'
			)
            
			# Générer les tokens JWT
			refresh = RefreshToken.for_user(user)
            
			return Response({
				'success': True,
				'message': _('Compte créé avec succès.'),
				'data': {
					'user': UserSerializer(user).data,
					'tokens': {
						'access': str(refresh.access_token),
						'refresh': str(refresh),
					}
				}
			}, status=status.HTTP_201_CREATED)


		return Response({
				'success': False,
				'error': {
					'code': status.HTTP_400_BAD_REQUEST,
					'message': _('Données invalides.'),
					'details': serializer.errors
				}
			}, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
	permission_classes = [permissions.AllowAny]
	throttle_classes = [AuthIPThrottle, LoginPhoneThrottle]
    
	def post(self, request):
		serializer = LoginSerializer(data=request.data, context={'request': request})
        
		if serializer.is_valid():
			user = serializer.validated_data['user']
            
			# Log user login
			AuditLog.log_action(
				action_type='user_login',
				user=user,
				object_type='user',
				object_id=user.id,
				old_value=None,
				new_value='login_success',
				ip_address=request.META.get('REMOTE_ADDR'),
				user_agent=request.META.get('HTTP_USER_AGENT', ''),
				reason=f'Connexion réussie: {user.username}'
			)
            
			# Générer les tokens JWT
			refresh = RefreshToken.for_user(user)
            
			return Response({
				'success': True,
				'message': _('Connexion réussie.'),
				'data': {
					'user': UserSerializer(user).data,
					'tokens': {
						'access': str(refresh.access_token),
						'refresh': str(refresh),
					}
				}
			})
        
		return Response({
			'success': False,
			'error': {
				'code': status.HTTP_401_UNAUTHORIZED,
				'message': _('Échec de l\'authentification.'),
				'details': serializer.errors
			}
		}, status=status.HTTP_401_UNAUTHORIZED)

class ProfileView(APIView):
	def get(self, request):
		"""Récupérer le profil de l'utilisateur connecté"""
		serializer = UserSerializer(request.user)
		return Response({
			'success': True,
			'data': serializer.data
		})
    
	def put(self, request):
		"""Mettre à jour le profil de l'utilisateur connecté"""
		serializer = UserUpdateSerializer(
			request.user, 
			data=request.data, 
			partial=True
		)
        
		if serializer.is_valid():
			serializer.save()
			
			# Log profile update
			AuditLog.log_action(
				action_type='user_profile_updated',
				user=request.user,
				object_type='user',
				object_id=request.user.id,
				old_value='profile',
				new_value='updated',
				ip_address=request.META.get('REMOTE_ADDR'),
				user_agent=request.META.get('HTTP_USER_AGENT', ''),
				reason=f'Mise à jour profil: {request.user.username}'
			)
			
			return Response({
				'success': True,
				'message': _('Profil mis à jour avec succès.'),
				'data': UserSerializer(request.user).data
			})
        
		return Response({
			'success': False,
			'error': {
				'code': status.HTTP_400_BAD_REQUEST,
				'message': _('Données invalides.'),
				'details': serializer.errors
			}
		}, status=status.HTTP_400_BAD_REQUEST)

class DeleteAccountView(APIView):
	"""Suppression de compte demandée par l'utilisateur (exigée par Google Play).

	Le compte est désactivé et anonymisé : les commandes restent pour la comptabilité,
	sans nom, téléphone ni e-mail rattachés."""
	permission_classes = [permissions.IsAuthenticated]
	throttle_classes = [AuthIPThrottle]
	DONE_ORDER = ('delivered', 'cancelled', 'refunded')
	DONE_DELIVERY = ('delivered', 'failed', 'cancelled')

	def blocker(self, user):
		from orders.models import Order
		from delivery.models import Delivery
		from payments.direct_models import PaymentObligation
		if user.is_superuser or user.is_staff or user.user_type == 'admin':
			return "Un compte administrateur se supprime par un autre administrateur."
		if Order.objects.filter(client=user).exclude(status__in=self.DONE_ORDER).exists():
			return "Vous avez une commande en cours. Attendez sa livraison ou annulez-la avant de supprimer le compte."
		if Order.objects.filter(store__manager=user).exclude(status__in=self.DONE_ORDER).exists():
			return "Votre commerce a des commandes en cours. Terminez-les avant de supprimer le compte."
		if PaymentObligation.objects.filter(arrangement__store__manager=user, kind='commission', status__in=['unpaid', 'overdue', 'partially_paid']).exists():
			return "Votre commerce doit encore des commissions à Gaboshop. Réglez-les avant de supprimer le compte."
		if Delivery.objects.filter(delivery_agent=user).exclude(status__in=self.DONE_DELIVERY).exists():
			return "Vous avez une livraison en cours. Terminez-la avant de supprimer le compte."
		return ''

	def post(self, request):
		user = request.user
		if not user.check_password(request.data.get('password') or ''):
			return Response({'success': False, 'error': {'code': 400, 'message': 'Mot de passe incorrect.'}}, status=status.HTTP_400_BAD_REQUEST)
		reason = self.blocker(user)
		if reason:
			return Response({'success': False, 'error': {'code': 409, 'message': reason}}, status=status.HTTP_409_CONFLICT)
		from stores.models import Store
		Store.objects.filter(manager=user).update(is_active=False)
		DeliveryAgentApiKey.objects.filter(user=user).delete()
		for relation in ('client_profile', 'livreur_profile', 'gerant_profile'):
			profile = getattr(user, relation, None)
			if profile is not None:
				profile.delete()
		if user.profile_picture:
			user.profile_picture.delete(save=False)
		user.phone = f'supprime-{user.id}'
		user.username = f'supprime-{user.id}'
		user.first_name = user.last_name = user.email = ''
		user.current_location = ''
		user.is_active = False
		user.set_unusable_password()
		user.save()
		AuditLog.log_action(
			action_type='user_account_deleted', user=user, object_type='user', object_id=user.id,
			old_value='active', new_value='deleted', ip_address=request.META.get('REMOTE_ADDR'),
			user_agent=request.META.get('HTTP_USER_AGENT', ''), reason='Suppression demandée par l’utilisateur',
		)
		return Response({'success': True, 'message': 'Votre compte a été supprimé.'})


class RefreshTokenView(APIView):
	permission_classes = [permissions.AllowAny]
    
	def post(self, request):
		from rest_framework_simplejwt.serializers import TokenRefreshSerializer
		from rest_framework_simplejwt.exceptions import TokenError
		serializer = TokenRefreshSerializer(data={'refresh': request.data.get('refresh') or ''})
		try:
			serializer.is_valid(raise_exception=True)
		except (TokenError, Exception):
			return Response({'success': False, 'error': {'code': 401, 'message': 'Session expirée, reconnectez-vous.'}}, status=status.HTTP_401_UNAUTHORIZED)
		return Response({'success': True, 'data': serializer.validated_data})


class MyApiKeyView(APIView):
	"""GET returns the delivery agent's API key (if any).
	POST regenerates the key.

	Routes:
	- GET /api/v1/me/api-key/
	- POST /api/v1/me/api-key/  # regenerate
	"""
	permission_classes = [permissions.IsAuthenticated]

	def get(self, request):
		user = request.user
		if not user.is_delivery_agent():
			return Response({'success': False, 'error': 'Accès réservé aux livreurs'}, status=status.HTTP_403_FORBIDDEN)

		api = getattr(user, 'api_key', None)
		if not api:
			return Response({'success': True, 'data': {'api_key': None}}, status=status.HTTP_200_OK)

		return Response({'success': True, 'data': {'api_key': api.key}}, status=status.HTTP_200_OK)

	def post(self, request):
		user = request.user
		if not user.is_delivery_agent():
			return Response({'success': False, 'error': 'Accès réservé aux livreurs'}, status=status.HTTP_403_FORBIDDEN)

		# Regenerate: delete existing and create a new one
		try:
			old = getattr(user, 'api_key', None)
			if old:
				old.delete()
			new = DeliveryAgentApiKey.create_for_user(user)
			AuditLog.log_action(action_type='api_key_regenerated', user=user, object_type='api_key', object_id=new.id, old_value=None, new_value='regenerated', ip_address=request.META.get('REMOTE_ADDR'), user_agent=request.META.get('HTTP_USER_AGENT',''))
			return Response({'success': True, 'data': {'api_key': new.key}}, status=status.HTTP_201_CREATED)
		except Exception as e:
			return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
		if not refresh_token:
			return Response({
				'success': False,
				'error': {
					'code': status.HTTP_400_BAD_REQUEST,
					'message': _('Le token de rafraîchissement est requis.')
				}
			}, status=status.HTTP_400_BAD_REQUEST)
        
		try:
			refresh = RefreshToken(refresh_token)
			access_token = str(refresh.access_token)
            
			return Response({
				'success': True,
				'data': {
					'access': access_token
				}
			})
        
		except Exception as e:
			return Response({
				'success': False,
				'error': {
					'code': status.HTTP_401_UNAUTHORIZED,
					'message': _('Token invalide ou expiré.')
				}
			}, status=status.HTTP_401_UNAUTHORIZED)



class PasswordResetRequestView(APIView):
	"""« Mot de passe oublié », étape 1 : envoie un code au numéro, sans dire si le compte existe."""
	permission_classes = [permissions.AllowAny]
	authentication_classes = []
	throttle_classes = [AuthIPThrottle, LoginPhoneThrottle]

	def get(self, request):
		from users.password_reset import email_available, sms_available
		return Response({'success': True, 'data': {'sms_available': sms_available(), 'email_available': email_available()}})

	def post(self, request):
		from users.password_reset import CODE_MINUTES, request_code
		if not str(request.data.get('phone') or '').strip():
			return Response({'success': False, 'error': {'code': 400, 'message': 'Entrez votre numéro de téléphone.'}}, status=status.HTTP_400_BAD_REQUEST)
		request_code(request.data.get('phone'))
		return Response({'success': True, 'message': (
			f"Si ce numéro a un compte, un code vient de lui être envoyé. Il est valable {CODE_MINUTES} minutes."
		)})


class PasswordResetConfirmView(APIView):
	"""« Mot de passe oublié », étape 2 : le code reçu et le nouveau mot de passe."""
	permission_classes = [permissions.AllowAny]
	authentication_classes = []
	throttle_classes = [AuthIPThrottle, LoginPhoneThrottle]

	def post(self, request):
		from users.password_reset import reset_password
		password = str(request.data.get('password') or '')
		if len(password) < 6:
			return Response({'success': False, 'error': {'code': 400, 'message': 'Le mot de passe doit faire au moins 6 caractères.'}}, status=status.HTTP_400_BAD_REQUEST)
		ok, reason = reset_password(request.data.get('phone'), request.data.get('code'), password)
		if not ok:
			return Response({'success': False, 'error': {'code': 400, 'message': reason}}, status=status.HTTP_400_BAD_REQUEST)
		return Response({'success': True, 'message': 'Mot de passe changé. Vous pouvez vous connecter.'})
