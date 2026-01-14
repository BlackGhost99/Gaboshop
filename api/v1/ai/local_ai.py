"""
IA locale avec règles prédéfinies (fonctionne sans clé API externe)
"""
from typing import Dict, Any, Optional
from .services import AIContextService, ErrorAnalyzer


class LocalAI:
    """
    Système d'IA basé sur des règles prédéfinies
    Fonctionne sans clé API externe
    """
    
    @staticmethod
    def generate_response(message: str, context: Dict[str, Any], last_error: Optional[Dict] = None) -> str:
        """
        Génère une réponse basée sur des règles prédéfinies
        """
        message_lower = message.lower().strip()
        role = context.get("user", {}).get("role", "client")
        
        # Gestion des erreurs (seulement si l'utilisateur demande explicitement)
        if last_error and any(word in message_lower for word in ['erreur', 'error', 'problème', 'explique', 'explain']):
            error_explanation = ErrorAnalyzer.analyze_error(
                last_error.get("status"),
                last_error.get("endpoint", ""),
                last_error.get("details")
            )
            return f"Je vois qu'une erreur s'est produite. {error_explanation}\n\nSouhaitez-vous que je vous guide pour résoudre ce problème ?"
        
        # Réponses de suivi après une explication d'erreur
        if any(word in message_lower for word in ['oui', 'yes', 'ok', 'd\'accord', 'daccord', 'guide', 'aide']):
            if last_error:
                status_code = last_error.get("status")
                endpoint = last_error.get("endpoint", "")
                
                if status_code == 404:
                    if 'store-categories' in endpoint or 'categories' in endpoint:
                        return "L'endpoint des catégories a été corrigé. Essayez de rafraîchir la page. Si le problème persiste, vérifiez que les catégories sont bien configurées dans votre magasin."
                    elif 'product' in endpoint:
                        return "Le produit demandé n'existe peut-être plus. Vérifiez votre liste de produits ou contactez le support si nécessaire."
                    else:
                        return "La ressource demandée n'est pas disponible. Vérifiez l'URL ou contactez le support technique."
                elif status_code == 403:
                    return "Vous n'avez pas les permissions nécessaires. Vérifiez votre forfait d'abonnement dans les paramètres ou contactez l'administrateur."
                elif status_code == 401:
                    return "Votre session a expiré. Veuillez vous déconnecter et vous reconnecter pour continuer."
                else:
                    return "Je peux vous aider à résoudre ce problème. Pouvez-vous me donner plus de détails sur ce que vous essayiez de faire ?"
        
        # Salutations
        if any(word in message_lower for word in ['bonjour', 'salut', 'hello', 'hi']):
            return f"Bonjour ! Je suis l'assistant IA de Gaboshop. Comment puis-je vous aider aujourd'hui ?"
        
        # Questions sur les commandes
        if any(word in message_lower for word in ['commande', 'order', 'achat']):
            if role == 'client':
                return "Vous pouvez suivre vos commandes dans la section 'Mes Commandes'. Un livreur vous sera attribué dès confirmation de votre commande."
            elif role == 'store_manager':
                orders_7d = context.get("metrics", {}).get("orders_7d", 0)
                return f"Vous avez {orders_7d} commande(s) dans les 7 derniers jours. Consultez l'onglet 'Commandes' pour les gérer."
        
        # Questions sur les ventes/chiffres
        if any(word in message_lower for word in ['vente', 'chiffre', 'revenu', 'revenue']):
            if role == 'store_manager':
                return "Consultez votre tableau de bord pour voir vos statistiques de ventes. Vous pouvez aussi accéder à la section Finance pour plus de détails."
        
        # Questions sur le stock
        if any(word in message_lower for word in ['stock', 'inventaire', 'produit']):
            if role == 'store_manager':
                alerts = context.get("alerts", [])
                if "LOW_STOCK_PRODUCTS" in alerts or "OUT_OF_STOCK" in alerts:
                    return "⚠️ Vous avez des produits avec stock faible ou en rupture. Consultez la section 'Produits' pour gérer votre inventaire."
                return "Votre stock semble correct. Consultez la section 'Produits' pour voir tous vos articles."
        
        # Questions sur la livraison
        if any(word in message_lower for word in ['livraison', 'delivery', 'livreur']):
            if role == 'client':
                return "La livraison standard coûte 2000 FCFA. Pour une livraison Express, comptez 3500 FCFA. Un livreur vous sera assigné après confirmation de votre commande."
            elif role == 'delivery_agent':
                return "Consultez votre tableau de bord livreur pour voir les livraisons disponibles et celles qui vous sont assignées."
        
        # Questions sur B2B/approvisionnement
        if any(word in message_lower for word in ['b2b', 'grossiste', 'approvisionnement', 'appro']):
            if role == 'store_manager':
                subscription = context.get("subscription", {})
                b2b_plan = subscription.get("b2b", "free")
                if b2b_plan == "free":
                    return "L'accès B2B nécessite un forfait Business. Consultez vos forfaits dans la section Abonnements pour mettre à niveau."
                return "Pour vous réapprovisionner, rendez-vous dans l'onglet 'Approvisionnement B2B' de votre tableau de bord. Vous y trouverez nos partenaires grossistes."
        
        # Questions sur les erreurs
        if any(word in message_lower for word in ['erreur', 'error', 'problème', 'bug']):
            return "Je peux vous aider à comprendre les erreurs. Décrivez le problème que vous rencontrez et je vous guiderai vers une solution."
        
        # Questions sur l'aide générale
        if any(word in message_lower for word in ['aide', 'help', 'comment', 'guide']):
            if role == 'client':
                return "Je peux vous aider avec:\n- Passer des commandes\n- Suivre vos livraisons\n- Comprendre les erreurs\n- Utiliser la plateforme\n\nQue souhaitez-vous faire ?"
            elif role == 'store_manager':
                return "Je peux vous aider avec:\n- Gérer vos produits et stock\n- Suivre vos commandes et ventes\n- Comprendre vos statistiques\n- Accéder au B2B (si éligible)\n- Résoudre les problèmes\n\nQue souhaitez-vous faire ?"
        
        # Réponse par défaut
        return f"Je comprends votre question. En tant qu'assistant IA de Gaboshop, je peux vous aider avec:\n\n" + \
               f"- Explications d'erreurs\n" + \
               f"- Guidance sur l'utilisation de la plateforme\n" + \
               f"- Informations sur vos {('commandes' if role == 'client' else 'ventes et statistiques')}\n" + \
               f"- Résolution de problèmes\n\n" + \
               f"Pouvez-vous reformuler votre question de manière plus précise ?"

