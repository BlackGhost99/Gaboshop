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


# ===============================================================================
# TÂCHES DE GESTION DES ABONNEMENTS (FORFAITS TEMPS RÉEL)
# ===============================================================================

@shared_task(bind=True, max_retries=3)
def check_expired_subscriptions(self):
    """
    ⏰ Vérifier et marquer les forfaits expirés
    Exécutée quotidiennement à minuit
    
    - Marque les abonnements expirés
    - Envoie des notifications
    - Bloque les fonctionnalités premium
    """
    try:
        from payments.models import StoreSubscription
        
        now = timezone.now().date()
        
        # Chercher tous les abonnements ACTIFS mais EXPIRÉS
        expired_subscriptions = StoreSubscription.objects.filter(
            status='active',
            end_date__lt=now
        )
        
        count = 0
        for subscription in expired_subscriptions:
            subscription.status = 'expired'
            subscription.save()
            count += 1
            
            logger.info(f"✅ Abonnement #{subscription.id} marqué comme expiré")
            
            # Envoyer une notification au magasin
            send_subscription_expiry_notification.delay(subscription.id)
        
        logger.info(f"✅ {count} abonnements marqués comme expirés")
        
        return {
            'status': 'success',
            'message': f'{count} abonnements marqués comme expirés',
            'count': count
        }
    
    except Exception as exc:
        logger.error(f"❌ Erreur lors de la vérification des expirations: {exc}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_subscription_expiry_notification(self, subscription_id):
    """
    📧 Envoyer une notification d'expiration au commerçant
    """
    try:
        from payments.models import StoreSubscription
        from django.core.mail import send_mail
        
        subscription = StoreSubscription.objects.get(id=subscription_id)
        store = subscription.store
        manager = store.manager
        
        if not manager or not manager.email:
            return {'status': 'skipped', 'reason': 'No email found'}
        
        plan_name = subscription.plan.name if subscription.plan else subscription.plan_name
        
        subject = f"⏰ Votre abonnement {plan_name} a expiré - Gaboshop"
        message = f"""
Bonjour {manager.first_name or 'Commerçant'},

Votre abonnement au forfait {plan_name} a expiré le {subscription.end_date}.

Certaines de vos fonctionnalités peuvent être limitées.

Veuillez vous connecter à votre tableau de bord pour renouveler votre forfait:
https://gaboshop.app/dashboard/billing

Cordialement,
Équipe Gaboshop
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email='noreply@gaboshop.app',
            recipient_list=[manager.email],
            fail_silently=True
        )
        
        logger.info(f"📧 Notification d'expiration envoyée à {manager.email}")
        return {'status': 'sent', 'email': manager.email}
    
    except Exception as exc:
        logger.error(f"❌ Erreur lors de l'envoi de notification: {exc}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_subscription_expiry_reminder(self):
    """
    🔔 Rappel d'expiration : Envoyer une notification 7 jours avant l'expiration
    Exécutée quotidiennement
    """
    try:
        from payments.models import StoreSubscription
        from django.core.mail import send_mail
        
        now = timezone.now().date()
        expiry_date_in_7_days = now + timedelta(days=7)
        
        # Chercher les abonnements qui expirent dans 7 jours
        expiring_soon = StoreSubscription.objects.filter(
            status='active',
            end_date=expiry_date_in_7_days
        )
        
        count = 0
        for subscription in expiring_soon:
            store = subscription.store
            manager = store.manager
            
            if not manager or not manager.email:
                continue
            
            plan_name = subscription.plan.name if subscription.plan else subscription.plan_name
            
            subject = f"⏰ Rappel : Votre abonnement {plan_name} expire dans 7 jours"
            message = f"""
Bonjour {manager.first_name or 'Commerçant'},

Votre abonnement au forfait {plan_name} expirera le {subscription.end_date} (dans 7 jours).

Pour continuer à bénéficier de toutes les fonctionnalités, veuillez renouveler votre forfait:
https://gaboshop.app/dashboard/billing

Cordialement,
Équipe Gaboshop
            """
            
            send_mail(
                subject=subject,
                message=message,
                from_email='noreply@gaboshop.app',
                recipient_list=[manager.email],
                fail_silently=True
            )
            
            count += 1
            logger.info(f"🔔 Rappel d'expiration envoyé à {manager.email}")
        
        logger.info(f"✅ {count} rappels d'expiration envoyés")
        
        return {
            'status': 'success',
            'count': count
        }
    
    except Exception as exc:
        logger.error(f"❌ Erreur lors de l'envoi des rappels: {exc}")
        raise self.retry(exc=exc, countdown=60)
