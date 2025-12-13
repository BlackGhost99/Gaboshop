"""API v1: stores endpoints."""

from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import ListAPIView, RetrieveAPIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter

from stores.models import Store, StoreCategory
from stores.serializers import (
	StoreListSerializer, StoreDetailSerializer, 
	StoreCategorySerializer, StoreCreateSerializer
)
from core.models import AuditLog

class StoreCategoryListView(ListAPIView):
	permission_classes = [permissions.AllowAny]
	serializer_class = StoreCategorySerializer
	queryset = StoreCategory.objects.filter(is_active=True)
    
	def list(self, request, *args, **kwargs):
		queryset = self.get_queryset()
		serializer = self.get_serializer(queryset, many=True)
        
		return Response({
			'success': True,
			'data': serializer.data
		})

class StoreListView(ListAPIView):
	permission_classes = [permissions.AllowAny]
	serializer_class = StoreListSerializer
	filter_backends = [DjangoFilterBackend, SearchFilter]
	filterset_fields = ['category', 'zone', 'city']
	search_fields = ['name', 'description']
    
	def get_queryset(self):
		queryset = Store.objects.filter(is_active=True)
		
		# B2B Visibility Logic
		user = self.request.user
		if user.is_authenticated and hasattr(user, 'user_type') and user.user_type == 'store_manager':
			# Gérants: Voient Grossistes et Industries (pour s'approvisionner)
			queryset = queryset.filter(store_type__in=['wholesaler', 'industry'])
		else:
			# Clients (et autres): Voient uniquement le Détail
			queryset = queryset.filter(store_type='retail')
        
		# Filtrer par ville si spécifiée
		city = self.request.query_params.get('city')
		if city:
			queryset = queryset.filter(city__iexact=city)
        
		# Filtrer par zone si spécifiée
		zone = self.request.query_params.get('zone')
		if zone:
			queryset = queryset.filter(zone__iexact=zone)
        
		return queryset.select_related('category')
    
	def list(self, request, *args, **kwargs):
		queryset = self.filter_queryset(self.get_queryset())
		page = self.paginate_queryset(queryset)
        
		if page is not None:
			serializer = self.get_serializer(page, many=True)
			return self.get_paginated_response(serializer.data)
        
		serializer = self.get_serializer(queryset, many=True)
		return Response({
			'success': True,
			'data': serializer.data
		})

class StoreDetailView(RetrieveAPIView):
	permission_classes = [permissions.AllowAny]
	serializer_class = StoreDetailSerializer
	queryset = Store.objects.filter(is_active=True)
    
	def retrieve(self, request, *args, **kwargs):
		instance = self.get_object()
		serializer = self.get_serializer(instance)
        
		return Response({
			'success': True,
			'data': serializer.data
		})

class StoreCreateView(APIView):
	permission_classes = [permissions.IsAuthenticated]
    
	def post(self, request):
		# Vérifier que l'utilisateur est un gérant de magasin
		if not request.user.is_store_manager():
			return Response({
				'success': False,
				'error': {
					'code': status.HTTP_403_FORBIDDEN,
					'message': 'Seuls les gérants de magasin peuvent créer des magasins.'
				}
			}, status=status.HTTP_403_FORBIDDEN)
        
		serializer = StoreCreateSerializer(
			data=request.data, 
			context={'request': request}
		)
        
		if serializer.is_valid():
			store = serializer.save()
            
			# Log store creation
			AuditLog.log_action(
				action_type='store_created',
				user=request.user,
				object_type='store',
				object_id=store.id,
				old_value=None,
				new_value=store.name,
				ip_address=request.META.get('REMOTE_ADDR'),
				user_agent=request.META.get('HTTP_USER_AGENT', ''),
				reason=f'Création magasin: {store.name}'
			)
            
			return Response({
				'success': True,
				'message': 'Magasin créé avec succès.',
				'data': StoreDetailSerializer(store).data
			}, status=status.HTTP_201_CREATED)
        
		return Response({
			'success': False,
			'error': {
				'code': status.HTTP_400_BAD_REQUEST,
				'message': 'Données invalides.',
				'details': serializer.errors
			}
		}, status=status.HTTP_400_BAD_REQUEST)

class StoreUpdateView(APIView):
	permission_classes = [permissions.IsAuthenticated]
    
	def patch(self, request, pk):
		# Vérifier que l'utilisateur est le gérant de ce magasin
		try:
			store = Store.objects.get(
				id=pk, 
				manager=request.user
			)
		except Store.DoesNotExist:
			return Response({
				'success': False,
				'error': {
					'code': status.HTTP_403_FORBIDDEN,
					'message': 'Vous n\'êtes pas autorisé à modifier ce magasin.'
				}
			}, status=status.HTTP_403_FORBIDDEN)
        
		from stores.serializers import StoreUpdateSerializer
		serializer = StoreUpdateSerializer(
			store, 
			data=request.data, 
			partial=True
		)
        
		if serializer.is_valid():
			old_name = store.name
			store = serializer.save()

			# Update Manager Details if provided
			manager = store.manager
			manager_updated = False
			
			if 'manager_first_name' in request.data:
				manager.first_name = request.data['manager_first_name']
				manager_updated = True
			
			if 'manager_last_name' in request.data:
				manager.last_name = request.data['manager_last_name']
				manager_updated = True
				
			if 'manager_email' in request.data:
				manager.email = request.data['manager_email']
				manager_updated = True
				
			if manager_updated:
				manager.save()
            
			# Log store update
			AuditLog.log_action(
				action_type='store_updated',
				user=request.user,
				object_type='store',
				object_id=store.id,
				old_value=old_name,
				new_value=store.name,
				ip_address=request.META.get('REMOTE_ADDR'),
				user_agent=request.META.get('HTTP_USER_AGENT', ''),
				reason=f'Mise à jour magasin: {store.name}'
			)
            
			return Response({
				'success': True,
				'message': 'Magasin et profil gérant mis à jour avec succès.',
				'data': StoreDetailSerializer(store).data
			})
        
		print("Store Update Errors:", serializer.errors)
		return Response({
			'success': False,
			'error': {
				'code': status.HTTP_400_BAD_REQUEST,
				'message': 'Données invalides.',
				'details': serializer.errors
			}
		}, status=status.HTTP_400_BAD_REQUEST)
