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
		# #region agent log
		import json,time
		try:
			with open(r'c:\Users\Admin\source\repos\BlackGhost99\Gaboshop\.cursor\debug.log', 'a', encoding='utf-8') as f:
				f.write(json.dumps({'id':f'log_{int(time.time()*1000)}_backend','timestamp':int(time.time()*1000),'location':'api/v1/users.py:24','message':'RegisterView post method entered','data':{'request_data':dict(request.data) if hasattr(request.data,'dict') else str(request.data),'user_type':request.data.get('user_type'),'has_position_lat':'position_lat' in request.data,'position_lat':request.data.get('position_lat'),'has_position_lng':'position_lng' in request.data,'position_lng':request.data.get('position_lng')},'sessionId':'debug-session','runId':'initial-test','hypothesisId':'A'})+'\n')
		except:pass
		# #endregion

		serializer = RegisterSerializer(data=request.data)

		# #region agent log
		try:
			with open(r'c:\Users\Admin\source\repos\BlackGhost99\Gaboshop\.cursor\debug.log', 'a', encoding='utf-8') as f:
				f.write(json.dumps({'id':f'log_{int(time.time()*1000)}_backend','timestamp':int(time.time()*1000),'location':'api/v1/users.py:44','message':'Serializer created, about to validate','data':{'initial_data_keys':list(serializer.initial_data.keys()) if hasattr(serializer,'initial_data') else [],'position_lat_in_initial':serializer.initial_data.get('position_lat') if hasattr(serializer,'initial_data') else None,'position_lng_in_initial':serializer.initial_data.get('position_lng') if hasattr(serializer,'initial_data') else None,'all_initial_data':dict(serializer.initial_data) if hasattr(serializer,'initial_data') else {}},'sessionId':'debug-session','runId':'initial-test','hypothesisId':'B'})+'\n')
		except Exception as e:
			try:
				with open(r'c:\Users\Admin\source\repos\BlackGhost99\Gaboshop\.cursor\debug.log', 'a', encoding='utf-8') as f:
					f.write(json.dumps({'id':f'log_{int(time.time()*1000)}_backend','timestamp':int(time.time()*1000),'location':'api/v1/users.py:44','message':'Exception logging initial_data','data':{'error':str(e)},'sessionId':'debug-session','runId':'initial-test','hypothesisId':'B'})+'\n')
			except:pass
		# #endregion

		# #region agent log
		is_valid_result = None
		try:
			is_valid_result = serializer.is_valid()
			with open(r'c:\Users\Admin\source\repos\BlackGhost99\Gaboshop\.cursor\debug.log', 'a', encoding='utf-8') as f:
				f.write(json.dumps({'id':f'log_{int(time.time()*1000)}_backend','timestamp':int(time.time()*1000),'location':'api/v1/users.py:42','message':'is_valid() called','data':{'is_valid':is_valid_result,'has_errors':bool(serializer.errors),'error_keys':list(serializer.errors.keys()) if serializer.errors else [],'errors':dict(serializer.errors) if serializer.errors else {}},'sessionId':'debug-session','runId':'initial-test','hypothesisId':'F'})+'\n')
		except Exception as e:
			import traceback
			with open(r'c:\Users\Admin\source\repos\BlackGhost99\Gaboshop\.cursor\debug.log', 'a', encoding='utf-8') as f:
				f.write(json.dumps({'id':f'log_{int(time.time()*1000)}_backend','timestamp':int(time.time()*1000),'location':'api/v1/users.py:42','message':'Exception during is_valid()','data':{'error_type':type(e).__name__,'error_message':str(e),'traceback':traceback.format_exc()},'sessionId':'debug-session','runId':'initial-test','hypothesisId':'F'})+'\n')
			raise
		# #endregion

		if is_valid_result:
			# Debug log: Serializer is valid, about to save
			try:
				with open(r'c:\Users\BlackGhost\Desktop\Gaboshop\.cursor\debug.log', 'a', encoding='utf-8') as f:
					log_entry = {
						'id': f'log_{int(time.time() * 1000)}_backend',
						'timestamp': int(time.time() * 1000),
						'location': 'api/v1/users.py:32',
						'message': 'Serializer is valid, about to save',
						'data': {'validated_data': dict(serializer.validated_data)},
						'sessionId': 'debug-session',
						'runId': 'initial-test',
						'hypothesisId': 'A'
					}
					f.write(json.dumps(log_entry) + '\n')
			except Exception as e:
				pass

			try:
				user = serializer.save()
				# Debug log: User created successfully
				try:
					with open(r'c:\Users\BlackGhost\Desktop\Gaboshop\.cursor\debug.log', 'a', encoding='utf-8') as f:
						log_entry = {
							'id': f'log_{int(time.time() * 1000)}_backend',
							'timestamp': int(time.time() * 1000),
							'location': 'api/v1/users.py:37',
							'message': 'User created successfully',
							'data': {'user_id': user.id, 'user_type': user.user_type},
							'sessionId': 'debug-session',
							'runId': 'initial-test',
							'hypothesisId': 'A'
						}
						f.write(json.dumps(log_entry) + '\n')
				except Exception as e:
					pass
			except Exception as e:
				# Debug log: Exception during serializer.save()
				try:
					with open(r'c:\Users\BlackGhost\Desktop\Gaboshop\.cursor\debug.log', 'a', encoding='utf-8') as f:
						log_entry = {
							'id': f'log_{int(time.time() * 1000)}_backend',
							'timestamp': int(time.time() * 1000),
							'location': 'api/v1/users.py:40',
							'message': 'Exception during serializer.save()',
							'data': {'error_type': type(e).__name__, 'error_message': str(e)},
							'sessionId': 'debug-session',
							'runId': 'initial-test',
							'hypothesisId': 'A'
						}
						f.write(json.dumps(log_entry) + '\n')
				except Exception as e:
					pass
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


		# #region agent log
		try:
			with open(r'c:\Users\Admin\source\repos\BlackGhost99\Gaboshop\.cursor\debug.log', 'a', encoding='utf-8') as f:
				f.write(json.dumps({'id':f'log_{int(time.time()*1000)}_backend','timestamp':int(time.time()*1000),'location':'api/v1/users.py:154','message':'Serializer validation failed','data':{'errors':serializer.errors,'error_keys':list(serializer.errors.keys()) if serializer.errors else [],'request_data':dict(request.data) if hasattr(request.data,'dict') else str(request.data),'user_type':request.data.get('user_type'),'position_lat_value':request.data.get('position_lat'),'position_lng_value':request.data.get('position_lng')},'sessionId':'debug-session','runId':'initial-test','hypothesisId':'E'})+'\n')
		except:pass
		# #endregion

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

