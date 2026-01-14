"""
Finance views - API endpoints for sales, expenses, and summary
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from orders.models import Order
from .models import Expense, Supplier
from .services import get_plan_features, apply_history_limit, enforce_feature
from .selectors import get_sales_summary, get_expenses_summary, get_top_categories, get_category_detailed_report
from .permissions import IsStoreManager
from .serializers import (
    ExpenseSerializer, SupplierSerializer, SalesSerializer
)


class FinanceSummaryView(APIView):
    """Vue résumé financier : ventes, dépenses, profit estimé"""
    permission_classes = [IsStoreManager]
    
    def get(self, request):
        store = request.user.managed_stores.first()
        if not store:
            return Response({'error': 'Aucun magasin associé'}, status=status.HTTP_404_NOT_FOUND)
        features = get_plan_features(store)
        
        # Filtres de date
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        # Agrégats ventes
        sales = get_sales_summary(store, date_from, date_to)
        
        # Agrégats dépenses
        expenses = get_expenses_summary(store, date_from, date_to)
        
        # Résultat estimé (profit = net reçu - dépenses)
        profit_estimate = sales['net_received'] - expenses['expenses_total']
        
        # Top catégories (seulement pour Pro/Business ou B2B avec can_view_finance_detailed)
        top_categories = []
        category_detailed_report = []
        # Pour B2B, utiliser can_view_finance_detailed, pour B2C utiliser can_view_detailed_reports
        can_view_detailed = features.get('can_view_finance_detailed', False) or features.get('can_view_detailed_reports', False)
        if can_view_detailed:
            top_categories = get_top_categories(store, date_from, date_to)
            # Rapport détaillé par catégorie (uniquement pour Business B2B)
            if features.get('can_view_finance_detailed', False):
                category_detailed_report = get_category_detailed_report(store, date_from, date_to)
        
        return Response({
            'success': True,
            'data': {
                'sales': sales,
                'expenses': expenses,
                'profit_estimate': profit_estimate,
                'top_categories': top_categories,
                'category_detailed_report': category_detailed_report  # Rapport détaillé par catégorie
            },
            'plan_features': features
        })


class SalesListView(APIView):
    """Liste détaillée des ventes avec pagination et filtres"""
    permission_classes = [IsStoreManager]
    
    def get(self, request):
        store = request.user.managed_stores.first()
        if not store:
            return Response({'error': 'Aucun magasin associé'}, status=status.HTTP_404_NOT_FOUND)
        features = get_plan_features(store)
        
        # Vérifier l'accès à la vue détaillée pour les stores B2B
        from b2b.models import B2BSubscriptionPlan
        plan = store.get_current_plan()
        is_b2b_plan = isinstance(plan, B2BSubscriptionPlan)
        if is_b2b_plan:
            # Pour B2B, vérifier can_view_finance_detailed pour la vue détaillée
            if not features.get('can_view_finance_detailed', False):
                # Si pas de vue détaillée, limiter les données retournées
                enforce_feature(store, 'can_view_finance_basic')
        
        # Queryset de base
        orders = Order.objects.filter(store=store).select_related('client').order_by('-created_at')
        orders = apply_history_limit(orders, store, 'created_at')
        
        # Filtres
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        status_filter = request.query_params.get('status')
        is_b2b = request.query_params.get('is_b2b')
        min_amount = request.query_params.get('min_amount')
        max_amount = request.query_params.get('max_amount')
        search = request.query_params.get('search')
        
        if date_from:
            orders = orders.filter(created_at__gte=date_from)
        if date_to:
            orders = orders.filter(created_at__lte=date_to)
        if status_filter:
            orders = orders.filter(status=status_filter)
        if is_b2b is not None:
            orders = orders.filter(is_b2b=is_b2b.lower() == 'true')
        if min_amount:
            orders = orders.filter(total_amount__gte=min_amount)
        if max_amount:
            orders = orders.filter(total_amount__lte=max_amount)
        if search:
            orders = orders.filter(
                Q(order_number__icontains=search) |
                Q(client__first_name__icontains=search) |
                Q(client__last_name__icontains=search) |
                Q(client__phone__icontains=search)
            )
        
        # Pagination
        paginator = PageNumberPagination()
        paginator.page_size = 50
        page = paginator.paginate_queryset(orders, request)
        
        # Serialization
        serializer = SalesSerializer(page, many=True, context={'features': features})
        
        # Get paginated response
        response = paginator.get_paginated_response(serializer.data)
        # Add plan features to response data
        response.data['plan_features'] = features
        return response


class SalesExportBaseView(APIView):
    """Vue de base pour l'export des ventes"""
    permission_classes = [IsStoreManager]
    
    def get_orders(self, request, store):
        """Récupère les commandes avec les filtres appliqués"""
        orders = Order.objects.filter(store=store).select_related('client').order_by('-created_at')
        orders = apply_history_limit(orders, store, 'created_at')
        
        # Apply filters (same as SalesListView)
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        status_filter = request.query_params.get('status')
        is_b2b = request.query_params.get('is_b2b')
        min_amount = request.query_params.get('min_amount')
        max_amount = request.query_params.get('max_amount')
        search = request.query_params.get('search')
        
        if date_from:
            orders = orders.filter(created_at__gte=date_from)
        if date_to:
            orders = orders.filter(created_at__lte=date_to)
        if status_filter:
            orders = orders.filter(status=status_filter)
        if is_b2b is not None:
            orders = orders.filter(is_b2b=is_b2b.lower() == 'true')
        if min_amount:
            orders = orders.filter(total_amount__gte=min_amount)
        if max_amount:
            orders = orders.filter(total_amount__lte=max_amount)
        if search:
            orders = orders.filter(
                Q(order_number__icontains=search) |
                Q(client__first_name__icontains=search) |
                Q(client__last_name__icontains=search) |
                Q(client__phone__icontains=search)
            )
        
        return orders


class SalesExportCSVView(SalesExportBaseView):
    """Export des ventes en CSV"""
    
    def get(self, request):
        try:
            store = request.user.managed_stores.first()
            if not store:
                from django.http import HttpResponse
                return HttpResponse('Aucun magasin associé', status=404)
            
            # Enforce permissions
            enforce_feature(store, 'can_export_excel')
            
            # Get orders
            orders = self.get_orders(request, store)
            
            # Import export function
            from .exports import export_sales_csv
            return export_sales_csv(orders, store)
        except Exception as e:
            import traceback
            from django.http import HttpResponse
            error_msg = f"Erreur lors de l'export CSV: {str(e)}\n{traceback.format_exc()}"
            return HttpResponse(error_msg, status=500, content_type='text/plain')


class SalesExportPDFView(SalesExportBaseView):
    """Export des ventes en PDF"""
    
    def get(self, request):
        try:
            store = request.user.managed_stores.first()
            if not store:
                from django.http import HttpResponse
                return HttpResponse('Aucun magasin associé', status=404)
            
            # Enforce permissions
            enforce_feature(store, 'can_export_pdf')
            
            # Get orders
            orders = self.get_orders(request, store)
            
            # Get date filters for summary
            date_from = request.query_params.get('date_from')
            date_to = request.query_params.get('date_to')
            
            # Import export function
            from .exports import export_sales_pdf
            summary = get_sales_summary(store, date_from, date_to)
            return export_sales_pdf(orders, store, summary)
        except Exception as e:
            import traceback
            from django.http import HttpResponse
            error_msg = f"Erreur lors de l'export PDF: {str(e)}\n{traceback.format_exc()}"
            return HttpResponse(error_msg, status=500, content_type='text/plain')


class ExpenseViewSet(viewsets.ModelViewSet):
    """CRUD pour les dépenses"""
    permission_classes = [IsStoreManager]
    serializer_class = ExpenseSerializer
    
    def get_queryset(self):
        store = self.request.user.managed_stores.first()
        if not store:
            return Expense.objects.none()
        queryset = Expense.objects.filter(store=store).select_related('supplier', 'created_by', 'b2b_order')
        queryset = apply_history_limit(queryset, store, 'expense_date')
        
        # Filtres
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        expense_type = self.request.query_params.get('expense_type')
        supplier_search = self.request.query_params.get('supplier_search')
        min_amount = self.request.query_params.get('min_amount')
        max_amount = self.request.query_params.get('max_amount')
        payment_method = self.request.query_params.get('payment_method')
        
        if date_from:
            queryset = queryset.filter(expense_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(expense_date__lte=date_to)
        if expense_type:
            queryset = queryset.filter(expense_type=expense_type)
        if supplier_search:
            queryset = queryset.filter(
                Q(supplier__name__icontains=supplier_search) |
                Q(supplier_name__icontains=supplier_search)
            )
        if min_amount:
            queryset = queryset.filter(amount__gte=min_amount)
        if max_amount:
            queryset = queryset.filter(amount__lte=max_amount)
        if payment_method:
            queryset = queryset.filter(payment_method=payment_method)
        
        return queryset.order_by('-expense_date', '-created_at')
    
    def perform_create(self, serializer):
        store = self.request.user.managed_stores.first()
        if not store:
            raise ValueError("Aucun magasin associé à cet utilisateur")
        serializer.save(
            store=store,
            created_by=self.request.user
        )


class ExpensesExportBaseView(APIView):
    """Vue de base pour l'export des dépenses"""
    permission_classes = [IsStoreManager]
    
    def get_expenses(self, request, store):
        """Récupère les dépenses avec les filtres appliqués"""
        expenses = Expense.objects.filter(store=store).select_related('supplier').order_by('-expense_date')
        expenses = apply_history_limit(expenses, store, 'expense_date')
        
        # Apply filters
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        expense_type = request.query_params.get('expense_type')
        
        if date_from:
            expenses = expenses.filter(expense_date__gte=date_from)
        if date_to:
            expenses = expenses.filter(expense_date__lte=date_to)
        if expense_type:
            expenses = expenses.filter(expense_type=expense_type)
        
        return expenses


class ExpensesExportCSVView(ExpensesExportBaseView):
    """Export des dépenses en CSV"""
    
    def get(self, request):
        store = request.user.managed_stores.first()
        if not store:
            from django.http import HttpResponse
            return HttpResponse('Aucun magasin associé', status=404)
        
        # Enforce permissions
        enforce_feature(store, 'can_export_excel')
        
        # Get expenses
        expenses = self.get_expenses(request, store)
        
        # Import export function
        from .exports import export_expenses_csv
        return export_expenses_csv(expenses, store)


class ExpensesExportPDFView(ExpensesExportBaseView):
    """Export des dépenses en PDF"""
    
    def get(self, request):
        try:
            store = request.user.managed_stores.first()
            if not store:
                from django.http import HttpResponse
                return HttpResponse('Aucun magasin associé', status=404)
            
            # Enforce permissions
            enforce_feature(store, 'can_export_pdf')
            
            # Get expenses
            expenses = self.get_expenses(request, store)
            
            # Get date filters for summary
            date_from = request.query_params.get('date_from')
            date_to = request.query_params.get('date_to')
            
            # Import export function
            from .exports import export_expenses_pdf
            summary = get_expenses_summary(store, date_from, date_to)
            return export_expenses_pdf(expenses, store, summary)
        except Exception as e:
            import traceback
            from django.http import HttpResponse
            error_msg = f"Erreur lors de l'export PDF: {str(e)}\n{traceback.format_exc()}"
            return HttpResponse(error_msg, status=500, content_type='text/plain')


class SupplierViewSet(viewsets.ModelViewSet):
    """CRUD pour les fournisseurs"""
    permission_classes = [IsStoreManager]
    serializer_class = SupplierSerializer
    
    def get_queryset(self):
        store = self.request.user.managed_stores.first()
        if not store:
            return Supplier.objects.none()
        queryset = Supplier.objects.filter(store=store)
        
        # Filtres
        is_active = self.request.query_params.get('is_active')
        search = self.request.query_params.get('search')
        
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(contact_person__icontains=search) |
                Q(phone__icontains=search)
            )
        
        return queryset.order_by('name')
    
    def perform_create(self, serializer):
        store = self.request.user.managed_stores.first()
        if not store:
            raise ValueError("Aucun magasin associé à cet utilisateur")
        serializer.save(store=store)
