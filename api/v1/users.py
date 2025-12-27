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
from core.models import AuditLog
from users.models import DeliveryAgentApiKey
from rest_framework import permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

class RegisterView(APIView):
	permission_classes = [permissions.AllowAny]
    
	def post(self, request):
		serializer = RegisterSerializer(data=request.data)
		if serializer.is_valid():
			user = serializer.save()
            
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
        
		print("REGISTRATION ERRORS:", serializer.errors)
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

class RefreshTokenView(APIView):
	permission_classes = [permissions.AllowAny]
    
	def post(self, request):
		refresh_token = request.data.get('refresh')


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

