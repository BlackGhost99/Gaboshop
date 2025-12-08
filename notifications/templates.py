"""Templates prédéfinis pour les notifications GABOSHOP
"""
from django.utils.translation import gettext_lazy as _

class NotificationTemplates:
    """Templates de messages pour toutes les notifications"""
    
    # ===== NOUVELLE COMMANDE =====
    @staticmethod
    def new_order_store(order):
        """Notification au magasin - Nouvelle commande"""
        return {
            'whatsapp': {
                'template_name': 'nouvelle_commande',
                'parameters': [{
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": f"#{order.order_number}"},
                        {"type": "text", "text": f"{order.total_amount} FCFA"},
                        {"type": "text", "text": f"{order.client.phone}"},
                        {"type": "text", "text": f"{order.delivery_zone}"}
                    ]
                }]
            },
            'sms': _(
                "🛍️ NOUVELLE COMMANDE #{order_number} - {total_amount} FCFA\n"
                "Client: {client_phone} - Zone: {delivery_zone}\n"
                "GABOSHOP"
            ).format(
                order_number=order.order_number,
                total_amount=order.total_amount,
                client_phone=order.client.phone,
                delivery_zone=order.delivery_zone
            )
        }
    
    # ===== STATUT COMMANDE =====
    @staticmethod
    def order_status_client(order, old_status, new_status):
        """Notification au client - Changement de statut"""
        status_display = order.get_status_display()
        
        return {
            'whatsapp': {
                'template_name': 'statut_commande',
                'parameters': [{
                    "type": "body", 
                    "parameters": [
                        {"type": "text", "text": f"#{order.order_number}"},
                        {"type": "text", "text": status_display},
                        {"type": "text", "text": f"{order.store.name}"}
                    ]
                }]
            },
            'sms': _(
                "📦 COMMANDE #{order_number}\n"
                "Statut: {status}\n"
                "Magasin: {store_name}\n"
                "GABOSHOP"
            ).format(
                order_number=order.order_number,
                status=status_display,
                store_name=order.store.name
            )
        }
    
    # ===== LIVRAISON ASSIGNÉE =====
    @staticmethod
    def delivery_assigned_agent(delivery):
        """Notification au livreur - Nouvelle livraison"""
        return {
            'whatsapp': {
                'template_name': 'livraison_assignee',
                'parameters': [{
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": f"#{delivery.tracking_number}"},
                        {"type": "text", "text": f"{delivery.delivery_fee} FCFA"},
                        {"type": "text", "text": delivery.pickup_address},
                        {"type": "text", "text": delivery.delivery_address}
                    ]
                }]
            },
            'sms': _(
                "🚗 LIVRAISON #{tracking_number}\n"
                "Commission: {delivery_fee} FCFA\n"
                "Magasin: {pickup_address}\n" 
                "Client: {delivery_address}\n"
                "GABOSHOP"
            ).format(
                tracking_number=delivery.tracking_number,
                delivery_fee=delivery.delivery_fee,
                pickup_address=delivery.pickup_address[:30] + "...",
                delivery_address=delivery.delivery_address[:30] + "..."
            )
        }
    
    # ===== PAIEMENT RÉUSSI =====
    @staticmethod
    def payment_success_client(order, payment):
        """Notification au client - Paiement confirmé"""
        return {
            'whatsapp': {
                'template_name': 'paiement_confirme',
                'parameters': [{
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": f"#{order.order_number}"},
                        {"type": "text", "text": f"{payment.amount} FCFA"},
                        {"type": "text", "text": f"{order.store.name}"}
                    ]
                }]
            },
            'sms': _(
                "✅ PAIEMENT CONFIRMÉ\n"
                "Commande: #{order_number}\n"
                "Montant: {amount} FCFA\n"
                "Merci pour votre achat !\n"
                "GABOSHOP"
            ).format(
                order_number=order.order_number,
                amount=payment.amount
            )
        }
    
    # ===== PAIEMENT ÉCHOUÉ =====
    @staticmethod
    def payment_failed_client(order):
        """Notification au client - Paiement échoué"""
        return {
            'whatsapp': {
                'template_name': 'paiement_echec',
                'parameters': [{
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": f"#{order.order_number}"},
                        {"type": "text", "text": f"{order.total_amount} FCFA"},
                        {"type": "text", "text": "Veuillez réessayer ou contacter le support"}
                    ]
                }]
            },
            'sms': _(
                "❌ PAIEMENT ÉCHOUÉ\n"
                "Commande: #{order_number}\n"
                "Veuillez réessayer ou contacter le support\n"
                "GABOSHOP - 07 XX XX XX XX"
            ).format(order_number=order.order_number)
        }
    
    # ===== LIVRAISON EN COURS =====
    @staticmethod
    def delivery_in_transit_client(delivery):
        """Notification au client - Livraison en route"""
        return {
            'whatsapp': {
                'template_name': 'livraison_en_route',
                'parameters': [{
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": f"#{delivery.tracking_number}"},
                        {"type": "text", "text": delivery.delivery_agent.phone if delivery.delivery_agent else "Livreur"},
                        {"type": "text", "text": "Votre commande arrive bientôt !"}
                    ]
                }]
            },
            'sms': _(
                "🚗 VOTRE COMMANDE ARRIVE !\n"
                "Livreur: {agent_phone}\n"
                "Tracking: #{tracking_number}\n"
                "Préparez {amount} FCFA\n"
                "GABOSHOP"
            ).format(
                agent_phone=delivery.delivery_agent.phone if delivery.delivery_agent else "07 XX XX XX XX",
                tracking_number=delivery.tracking_number,
                amount=delivery.order.total_amount
            )
        }
