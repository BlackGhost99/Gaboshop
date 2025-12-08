from celery import shared_task
from django.utils import timezone
from django.db import transaction
import logging
from datetime import timedelta

from payments.models import Payment, Reversement
from payments.services import PaymentService
from orders.models import Order
from django.db import models

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def verifier_paiements_en_attente(self):
    """
    Vérifier les paiements en attente et confirmer les succès
    Exécutée toutes les 2 minutes
    """
    try:
        with transaction.atomic():
            # Paiements en attente depuis plus de 5 minutes
            delai_verification = timezone.now() - timedelta(minutes=5)
            
            paiements_verifies = Payment.objects.filter(
                status='pending',
                created_at__lt=delai_verification
            ).select_related('order')
            
            if not paiements_verifies:
                logger.info("💳 Aucun paiement en attente à vérifier")
                return {"verifies": 0}
            
            paiements_confirmes = 0
            paiements_echoues = 0
            
            for paiement in paiements_verifies:
                try:
                    # 🔄 EN PRODUCTION: Appeler l'API de l'opérateur pour vérifier le statut
                    # Pour le MVP, on simule une confirmation automatique
                    
                    # Simulation: 90% de succès, 10% d'échec
                    import random
                    if random.random() < 0.9:  # 90% de chance de succès
                        # Paiement réussi
                        resultat = PaymentService.confirm_payment(
                            paiement.transaction_id,
                            'SUCCESS'
                        )
                        paiements_confirmes += 1
                        logger.info(f"✅ Paiement confirmé: #{paiement.order.order_number}")
                    else:
                        # Paiement échoué
                        paiement.status = 'failed'
                        paiement.save()
                        paiements_echoues += 1
                        logger.warning(f"❌ Paiement échoué: #{paiement.order.order_number}")
                        
                except Exception as e:
                    logger.error(f"❌ Erreur vérification paiement {paiement.transaction_id}: {e}")
                    continue
            
            resultat = {
                "verifies": len(paiements_verifies),
                "confirmes": paiements_confirmes,
                "echoues": paiements_echoues,
                "timestamp": timezone.now().isoformat()
            }
            
            logger.info(f"🔍 Vérification paiements terminée: {resultat}")
            return resultat
            
    except Exception as e:
        logger.error(f"❌ Erreur tâche vérification paiements: {e}")
        self.retry(countdown=120, exc=e)

@shared_task
def traiter_reversements_automatiques():
    """
    Traiter les reversements automatiques pour les magasins
    Exécutée quotidiennement à minuit
    """
    try:
        from stores.models import Store
        from datetime import datetime, timedelta
        
        # Période: hier
        date_fin = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        date_debut = date_fin - timedelta(days=1)
        
        # Récupérer tous les magasins actifs
        magasins_actifs = Store.objects.filter(is_active=True)
        
        reversements_traites = 0
        montant_total = 0
        
        for magasin in magasins_actifs:
            try:
                # Traiter le reversement pour ce magasin
                resultat = PaymentService.process_store_payout(
                    magasin.id,
                    date_debut,
                    date_fin
                )
                
                if resultat.get('success') and resultat.get('reversement'):
                    reversements_traites += 1
                    montant_total += resultat['reversement'].net_amount
                    
                    logger.info(
                        f"💰 Reversement traité pour {magasin.name}: "
                        f"{resultat['reversement'].net_amount} FCFA"
                    )
                    
            except Exception as e:
                logger.error(f"❌ Erreur reversement {magasin.name}: {e}")
                continue
        
        resultat_final = {
            "reversements_traites": reversements_traites,
            "montant_total": float(montant_total),
            "periode": f"{date_debut.date()} à {date_fin.date()}",
            "timestamp": timezone.now().isoformat()
        }
        
        logger.info(f"🏦 Reversements automatiques terminés: {resultat_final}")
        return resultat_final
        
    except Exception as e:
        logger.error(f"❌ Erreur tâche reversements: {e}")
        return {"erreur": str(e)}

@shared_task
def generer_rapport_financier_quotidien():
    """
    Générer un rapport financier quotidien pour l'admin
    """
    try:
        from django.db.models import Sum, Count
        from datetime import datetime, timedelta
        
        aujourd_hui = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        hier = aujourd_hui - timedelta(days=1)
        
        # Statistiques des paiements
        stats_paiements = Payment.objects.filter(
            created_at__range=[hier, aujourd_hui],
            status='completed'
        ).aggregate(
            total_paiements=Count('id'),
            montant_total=Sum('amount'),
            moyenne_commande=Sum('amount') / Count('id')
        )
        
        # Statistiques des commandes
        stats_commandes = Order.objects.filter(
            created_at__range=[hier, aujourd_hui]
        ).aggregate(
            total_commandes=Count('id'),
            commandes_livrees=Count('id', filter=models.Q(status='delivered')),
            commandes_annulees=Count('id', filter=models.Q(status='cancelled'))
        )
        
        # Calcul du taux de conversion
        taux_conversion = (
            (stats_paiements['total_paiements'] / stats_commandes['total_commandes'] * 100)
            if stats_commandes['total_commandes'] > 0 else 0
        )
        
        rapport = {
            "date": aujourd_hui.date().isoformat(),
            "paiements": {
                "total": stats_paiements['total_paiements'] or 0,
                "montant_total": float(stats_paiements['montant_total'] or 0),
                "moyenne_commande": float(stats_paiements['moyenne_commande'] or 0),
            },
            "commandes": {
                "total": stats_commandes['total_commandes'] or 0,
                "livrees": stats_commandes['commandes_livrees'] or 0,
                "annulees": stats_commandes['commandes_annulees'] or 0,
                "taux_conversion": round(taux_conversion, 2)
            },
            "timestamp": timezone.now().isoformat()
        }
        
        logger.info(f"📊 Rapport financier généré: {rapport}")
        
        # 🔔 EN PRODUCTION: Envoyer le rapport par email à l'admin
        # from django.core.mail import send_mail
        # send_mail(...)
        
        return rapport
        
    except Exception as e:
        logger.error(f"❌ Erreur génération rapport: {e}")
        return {"erreur": str(e)}
