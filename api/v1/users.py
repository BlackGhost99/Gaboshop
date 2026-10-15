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
					'message': _('Inscription impossible : vérifiez les informations indiquées.'),
					'details': serializer.errors
				}
			}, status=status.HTTP_400_BAD_REQUEST)

def _minutes(seconds):
	return max(1, int(-(-float(seconds or 0) // 60)))


class LoginView(APIView):
	permission_classes = [permissions.AllowAny]
	throttle_classes = [AuthIPThrottle, LoginPhoneThrottle]

	def _attempts(self, request):
		"""Essais déjà faits sur ce numéro dans le quart d'heure (celui-ci compris)."""
		from django.core.cache import cache
		throttle = LoginPhoneThrottle()
		key = throttle.get_cache_key(request, self)
		try:
			return len(cache.get(key) or []) if key else 0
		except Exception:
			return 0

	def handle_exception(self, exc):
		from rest_framework.exceptions import Throttled
		if isinstance(exc, Throttled):
			minutes = _minutes(exc.wait)
			phone_locked = self._attempts(self.request) >= LoginPhoneThrottle.ATTEMPTS
			return Response({'success': False, 'error': {
				'code': status.HTTP_429_TOO_MANY_REQUESTS,
				'message': f'Connexion bloquée pendant encore {minutes} min.',
				'reason': (f'Trop de mots de passe faux sur ce numéro ({LoginPhoneThrottle.ATTEMPTS} essais en 15 minutes) : '
					'le compte est protégé contre les tentatives de piratage.') if phone_locked
					else 'Trop de tentatives de connexion depuis ce réseau en peu de temps.',
				'next_step': f'Attendez {minutes} min puis réessayez avec le bon mot de passe. '
					'Mot de passe oublié : contactez le support Gaboshop.',
				'locked': True, 'retry_after_seconds': int(exc.wait or 0),
			}}, status=status.HTTP_429_TOO_MANY_REQUESTS)
		return super().handle_exception(exc)

	def _warn_locked(self, request):
		"""Blocage atteint : le titulaire du numéro et les admins sont prévenus."""
		from users.serializers import normalize_login_phone
		from core.guardian import _admins
		from notifications.service import NotificationService
		phone = normalize_login_phone(request.data.get('phone') or '')
		core = phone[4:].lstrip('0') if phone.startswith('+241') else ''
		owner = User.objects.filter(phone__in=[phone] + ([f'+241{core}', f'+2410{core}'] if core else [])).first()
		try:
			if owner:
				NotificationService.notify_user(owner, {
					'title': 'Connexion bloquée 15 minutes',
					'body': f'{LoginPhoneThrottle.ATTEMPTS} mots de passe faux ont été tapés sur votre numéro.',
					'level': 'warning', 'reason': 'Protection contre les tentatives de piratage.',
					'next_step': 'Si ce n’était pas vous, changez votre mot de passe dès que vous êtes connecté.',
				}, notif_type='warning', metadata={'action': 'login_locked'})
			who = f"{owner.get_full_name() or owner.phone} ({owner.get_user_type_display()})" if owner else f'{phone} (aucun compte)'
			for admin in _admins():
				NotificationService.notify_user(admin, {
					'title': f'Connexion bloquée : {who}',
					'body': f'{LoginPhoneThrottle.ATTEMPTS} mots de passe faux en 15 minutes. Le numéro est bloqué 15 minutes.',
					'level': 'warning', 'reason': 'Oubli du mot de passe ou tentative de piratage.',
					'next_step': 'Si la personne vous contacte, vérifiez son identité avant de l’aider à changer son mot de passe.',
				}, notif_type='warning', metadata={'action': 'login_locked', 'phone': phone})
			AuditLog.log_action(
				action_type='user_login', user=owner, object_type='user', object_id=owner.id if owner else 0,
				old_value=None, new_value='login_locked', ip_address=request.META.get('REMOTE_ADDR'),
				user_agent=request.META.get('HTTP_USER_AGENT', ''), reason=f'Connexion bloquée : {phone}', is_suspicious=True,
			)
		except Exception:
			pass

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
        
		errors = serializer.errors.get('non_field_errors') or []
		message = str(errors[0]) if errors else str(_('Numéro de téléphone ou mot de passe incorrect.'))
		left = max(0, LoginPhoneThrottle.ATTEMPTS - self._attempts(request))
		if left == 0:
			self._warn_locked(request)
			reason = 'C’était le dernier essai : ce numéro est maintenant bloqué 15 minutes.'
			next_step = 'Attendez 15 min. Mot de passe oublié : contactez le support Gaboshop.'
		else:
			reason = f'Il vous reste {left} essai{"s" if left > 1 else ""} avant un blocage de 15 minutes.'
			next_step = 'Vérifiez le numéro (avec le 0 du début) et le mot de passe, puis réessayez.'
		return Response({
			'success': False,
			'error': {
				'code': status.HTTP_401_UNAUTHORIZED,
				'message': message,
				'reason': reason,
				'next_step': next_step,
				'attempts_left': left,
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
		from users.password_reset import email_available, sms_available, whatsapp_available
		return Response({'success': True, 'data': {
			'whatsapp_available': whatsapp_available(), 'sms_available': sms_available(), 'email_available': email_available(),
		}})

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


class PhoneVerificationView(APIView):
	"""Vérification facultative du numéro : envoie un code (POST) puis le contrôle (POST confirm)."""
	permission_classes = [permissions.IsAuthenticated]
	throttle_classes = [AuthIPThrottle]

	def get_throttles(self):
		# Lire l'état (appelé à chaque page) ne doit pas consommer les essais de connexion de l'adresse IP.
		return [] if self.request.method == 'GET' else super().get_throttles()

	def get(self, request):
		from users.password_reset import channels_available
		return Response({'success': True, 'data': {
			'phone_verified': bool(request.user.phone_verified_at), 'available': channels_available(),
		}})

	def post(self, request):
		from users.password_reset import CODE_MINUTES, send_phone_verification
		if request.user.phone_verified_at:
			return Response({'success': True, 'message': 'Votre numéro est déjà vérifié.'})
		if not send_phone_verification(request.user):
			return Response({'success': False, 'error': {'code': 503, 'message': "Le code n'a pas pu être envoyé.",
				'next_step': 'Réessayez dans quelques minutes.'}}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
		return Response({'success': True, 'message': f'Code envoyé au {request.user.phone}. Il est valable {CODE_MINUTES} minutes.'})


class PhoneVerificationConfirmView(APIView):
	permission_classes = [permissions.IsAuthenticated]
	throttle_classes = [AuthIPThrottle]

	def post(self, request):
		from users.password_reset import confirm_phone_verification
		ok, reason = confirm_phone_verification(request.user, request.data.get('code'))
		if not ok:
			return Response({'success': False, 'error': {'code': 400, 'message': reason}}, status=status.HTTP_400_BAD_REQUEST)
		return Response({'success': True, 'message': 'Numéro vérifié.'})
