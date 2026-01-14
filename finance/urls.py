"""
Finance URLs - API endpoints for sales, expenses, and summary
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    FinanceSummaryView,
    SalesListView,
    SalesExportCSVView,
    SalesExportPDFView,
    ExpenseViewSet,
    ExpensesExportCSVView,
    ExpensesExportPDFView,
    SupplierViewSet,
)

router = DefaultRouter()
router.register(r'expenses', ExpenseViewSet, basename='expense')
router.register(r'suppliers', SupplierViewSet, basename='supplier')

app_name = 'finance'

urlpatterns = [
    # Summary endpoint
    path('summary/', FinanceSummaryView.as_view(), name='finance-summary'),
    
    # Sales endpoints
    path('sales/', SalesListView.as_view(), name='sales-list'),
    # IMPORTANT: Les routes d'export doivent être AVANT le router pour éviter les conflits
    path('sales/export/csv/', SalesExportCSVView.as_view(), name='sales-export-csv'),
    path('sales/export/pdf/', SalesExportPDFView.as_view(), name='sales-export-pdf'),
    
    # Expenses export endpoints (DOIT être AVANT le router pour éviter les conflits)
    path('expenses/export/csv/', ExpensesExportCSVView.as_view(), name='expenses-export-csv'),
    path('expenses/export/pdf/', ExpensesExportPDFView.as_view(), name='expenses-export-pdf'),
    
    # Router URLs (includes expenses/ and suppliers/ CRUD)
    # Le router doit être en dernier pour ne pas intercepter les routes d'export
    path('', include(router.urls)),
]