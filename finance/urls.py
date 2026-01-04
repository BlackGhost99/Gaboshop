"""
Finance URLs - API endpoints for sales, expenses, and summary
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    FinanceSummaryView,
    SalesListView,
    SalesExportView,
    ExpenseViewSet,
    ExpensesExportView,
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
    path('sales/export/csv/', SalesExportView.as_view(), {'format': 'csv'}, name='sales-export-csv'),
    path('sales/export/pdf/', SalesExportView.as_view(), {'format': 'pdf'}, name='sales-export-pdf'),
    
    # Expenses export endpoints (CRUD is handled by the router)
    path('expenses/export/csv/', ExpensesExportView.as_view(), {'format': 'csv'}, name='expenses-export-csv'),
    path('expenses/export/pdf/', ExpensesExportView.as_view(), {'format': 'pdf'}, name='expenses-export-pdf'),
    
    # Router URLs (includes expenses/ and suppliers/ CRUD)
    path('', include(router.urls)),
]
