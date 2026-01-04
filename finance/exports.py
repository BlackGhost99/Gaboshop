"""
Export handlers for Finance module - CSV and PDF generation
"""
import csv
from django.http import HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa
from io import BytesIO
from datetime import datetime


def export_sales_csv(orders, store):
    """
    Export sales data to CSV format
    """
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    filename = f'ventes_{store.slug}_{datetime.now().strftime("%Y%m%d")}.csv'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # Add BOM for Excel UTF-8 support
    response.write('\ufeff')
    
    writer = csv.writer(response)
    
    # Header
    writer.writerow([
        'Date',
        'N° Commande',
        'Client',
        'Téléphone',
        'Montant HT',
        'Frais de livraison',
        'Frais de service',
        'Commission',
        'Montant total',
        'Net reçu',
        'Statut',
        'Type',
    ])
    
    # Data rows
    for order in orders:
        net_received = (
            order.items_total + order.delivery_fee 
            - order.service_fee - order.commission_amount
        )
        
        writer.writerow([
            order.created_at.strftime('%Y-%m-%d %H:%M'),
            order.order_number,
            order.client.get_full_name() if order.client else 'N/A',
            order.client.phone if order.client else 'N/A',
            f"{order.items_total:.2f}",
            f"{order.delivery_fee:.2f}",
            f"{order.service_fee:.2f}",
            f"{order.commission_amount:.2f}",
            f"{order.total_amount:.2f}",
            f"{net_received:.2f}",
            order.get_status_display(),
            'B2B' if order.is_b2b else 'B2C',
        ])
    
    return response


def export_sales_pdf(orders, store, summary):
    """
    Export sales data to PDF format (Business plan only)
    """
    # Prepare data
    orders_data = []
    for order in orders:
        net_received = (
            order.items_total + order.delivery_fee 
            - order.service_fee - order.commission_amount
        )
        orders_data.append({
            'date': order.created_at.strftime('%d/%m/%Y %H:%M'),
            'order_number': order.order_number,
            'client': order.client.get_full_name() if order.client else 'N/A',
            'items_total': order.items_total,
            'delivery_fee': order.delivery_fee,
            'service_fee': order.service_fee,
            'commission': order.commission_amount,
            'total': order.total_amount,
            'net': net_received,
            'status': order.get_status_display(),
            'type': 'B2B' if order.is_b2b else 'B2C',
        })
    
    context = {
        'store': store,
        'orders': orders_data,
        'summary': summary,
        'generated_at': datetime.now(),
        'report_title': 'Rapport des Ventes'
    }
    
    # Render HTML template
    html_string = render_to_string('finance/sales_export_pdf.html', context)
    
    # Create PDF
    response = HttpResponse(content_type='application/pdf')
    filename = f'ventes_{store.slug}_{datetime.now().strftime("%Y%m%d")}.pdf'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # Generate PDF
    pisa_status = pisa.CreatePDF(
        html_string,
        dest=response
    )
    
    if pisa_status.err:
        return HttpResponse('Erreur lors de la génération du PDF', status=500)
    
    return response


def export_expenses_csv(expenses, store):
    """
    Export expenses data to CSV format
    """
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    filename = f'depenses_{store.slug}_{datetime.now().strftime("%Y%m%d")}.csv'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # Add BOM for Excel UTF-8 support
    response.write('\ufeff')
    
    writer = csv.writer(response)
    
    # Header
    writer.writerow([
        'Date',
        'Type',
        'Fournisseur',
        'Référence',
        'Montant',
        'Méthode paiement',
        'Notes',
        'Auto-tracking',
    ])
    
    # Data rows
    for expense in expenses:
        supplier_name = ''
        if expense.supplier:
            supplier_name = expense.supplier.name
        elif expense.supplier_name:
            supplier_name = expense.supplier_name
        else:
            supplier_name = 'N/A'
        
        writer.writerow([
            expense.expense_date.strftime('%Y-%m-%d'),
            expense.get_expense_type_display(),
            supplier_name,
            expense.reference or 'N/A',
            f"{expense.amount:.2f}",
            expense.get_payment_method_display() if hasattr(expense, 'get_payment_method_display') else expense.payment_method,
            expense.notes or '',
            'Oui' if expense.b2b_order_id else 'Non',
        ])
    
    return response


def export_expenses_pdf(expenses, store, summary):
    """
    Export expenses data to PDF format (Business plan only)
    """
    # Prepare data
    expenses_data = []
    for expense in expenses:
        supplier_name = ''
        if expense.supplier:
            supplier_name = expense.supplier.name
        elif expense.supplier_name:
            supplier_name = expense.supplier_name
        else:
            supplier_name = 'N/A'
        
        expenses_data.append({
            'date': expense.expense_date.strftime('%d/%m/%Y'),
            'type': expense.get_expense_type_display(),
            'supplier': supplier_name,
            'reference': expense.reference or 'N/A',
            'amount': expense.amount,
            'payment_method': expense.get_payment_method_display() if hasattr(expense, 'get_payment_method_display') else expense.payment_method,
            'auto_tracked': 'Oui' if expense.b2b_order_id else 'Non',
        })
    
    context = {
        'store': store,
        'expenses': expenses_data,
        'summary': summary,
        'generated_at': datetime.now(),
        'report_title': 'Rapport des Dépenses'
    }
    
    # Render HTML template
    html_string = render_to_string('finance/expenses_export_pdf.html', context)
    
    # Create PDF
    response = HttpResponse(content_type='application/pdf')
    filename = f'depenses_{store.slug}_{datetime.now().strftime("%Y%m%d")}.pdf'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # Generate PDF
    pisa_status = pisa.CreatePDF(
        html_string,
        dest=response
    )
    
    if pisa_status.err:
        return HttpResponse('Erreur lors de la génération du PDF', status=500)
    
    return response
