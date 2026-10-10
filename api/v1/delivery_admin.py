"""Espace admin > Livraison : tarifs (zones, véhicules, distances), attribution, courses en cours,
statistiques et incidents. Tout ce qui fixe le prix d'une livraison se règle ici."""
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.db import IntegrityError, transaction
from django.db.models import Avg, Count, F, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import SystemSettings
from api.v1.admin import IsPlatformAdmin
from delivery.models import CityDistance, Delivery, DeliveryZone, VehicleType, ZoneVehicleRate
from orders.models import Order
from payments.models import DeliveryPayout
from stores.models import Store
from users.models import LivreurProfile, User

WAITING_STATUSES = ('waiting', 'pending', 'ready_for_assignment', 'awaiting_delivery_payment', 'pending_vehicle_validation')
ACTIVE_STATUSES = ('assigned', 'accepted_by_driver', 'accepted', 'picked_up', 'in_delivery', 'in_transit')


def _error(message, reason='', next_step='', details=None, code=status.HTTP_400_BAD_REQUEST):
    return Response({'success': False, 'error': {
        'message': message, 'reason': reason, 'next_step': next_step, 'details': details or {},
    }}, status=code)


def _money(value, field, errors, minimum=Decimal('0')):
    try:
        amount = Decimal(str(value).replace(' ', '').replace(',', '.'))
    except (InvalidOperation, TypeError, ValueError):
        errors[field] = ['Montant invalide.']
        return None
    if amount < minimum:
        errors[field] = [f'Doit être au moins {minimum}.']
        return None
    return amount.quantize(Decimal('0.01'))


def _vehicle_data(vehicle):
    return {
        'id': vehicle.id, 'code': vehicle.name, 'label': vehicle.get_name_display(), 'is_active': vehicle.is_active,
        'max_weight_kg': float(vehicle.max_weight_kg), 'max_length_m': float(vehicle.max_length_m),
        'max_items': vehicle.max_items, 'max_distance_km': float(vehicle.max_distance_km),
        'allow_intercity': vehicle.allow_intercity,
        'base_price_intra_city': float(vehicle.base_price_intra_city),
        'price_per_km_intra_city': float(vehicle.price_per_km_intra_city),
        'base_price_inter_city': float(vehicle.base_price_inter_city),
        'price_per_km_inter_city': float(vehicle.price_per_km_inter_city),
    }


def _zone_data(zone, vehicles):
    rates = {rate.vehicle_id: rate for rate in zone.vehicle_rates.all()}
    return {
        'id': zone.id, 'name': zone.name, 'city': zone.city, 'description': zone.description,
        'is_active': zone.is_active, 'inter_city_surcharge': float(zone.inter_city_surcharge),
        'rates': [{
            'vehicle_id': vehicle.id, 'vehicle': vehicle.get_name_display(),
            'price': float(rates[vehicle.id].base_price) if vehicle.id in rates else None,
            'is_active': rates[vehicle.id].is_active if vehicle.id in rates else False,
        } for vehicle in vehicles],
    }


class DeliveryTariffsView(APIView):
    """Vue d'ensemble des tarifs : zones et prix par véhicule, véhicules, distances, prix par défaut."""
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        vehicles = list(VehicleType.objects.order_by('max_weight_kg'))
        zones = DeliveryZone.objects.prefetch_related('vehicle_rates').order_by('city', 'name')
        rules = SystemSettings.get_settings()
        return Response({'success': True, 'data': {
            'zones': [_zone_data(zone, vehicles) for zone in zones],
            'vehicles': [_vehicle_data(v) for v in vehicles],
            'distances': [{
                'id': d.id, 'from_city': d.from_city, 'to_city': d.to_city,
                'distance_km': float(d.distance_km), 'estimated_time_minutes': d.estimated_time_minutes,
            } for d in CityDistance.objects.order_by('from_city', 'to_city')],
            'defaults': {
                'default_delivery_fee': float(rules.default_delivery_fee),
                'default_express_delivery_fee': float(rules.default_express_delivery_fee),
                'default_intercity_surcharge': float(rules.default_intercity_surcharge),
                'courier_share_percent': float(rules.courier_share_percent),
            },
            'cities': rules.get_enabled_cities_list(),
            'stores_count': Store.objects.count(),
        }})


class DeliveryDefaultsView(APIView):
    """Prix utilisés quand aucune zone ne correspond ; peut aussi les appliquer à tous les commerces."""
    permission_classes = [IsPlatformAdmin]

    def patch(self, request):
        rules = SystemSettings.get_settings()
        errors = {}
        for field in ('default_delivery_fee', 'default_express_delivery_fee', 'default_intercity_surcharge'):
            if field in request.data:
                value = _money(request.data[field], field, errors)
                if value is not None:
                    setattr(rules, field, value)
        if errors:
            return _error('Prix non enregistrés.', 'Certains montants ne sont pas valides.', 'Corrigez les champs indiqués.', errors)
        rules.save()
        updated = 0
        if str(request.data.get('apply_to_all_stores', '')).lower() in ('true', '1', 'yes', 'oui'):
            updated = Store.objects.update(
                delivery_fee=rules.default_delivery_fee, delivery_fee_express=rules.default_express_delivery_fee,
            )
        return Response({'success': True, 'data': {'stores_updated': updated}})


class DeliveryZonesAdminView(APIView):
    permission_classes = [IsPlatformAdmin]

    def post(self, request):
        return self._save(request, DeliveryZone())

    def patch(self, request, zone_id):
        return self._save(request, get_object_or_404(DeliveryZone, pk=zone_id))

    def delete(self, request, zone_id):
        zone = get_object_or_404(DeliveryZone, pk=zone_id)
        used = Order.objects.filter(delivery_zone__iexact=zone.name).exclude(status__in=('delivered', 'cancelled')).count()
        if used:
            return _error('Zone encore utilisée.', f'{used} commande(s) en cours y sont livrées.',
                          'Désactivez la zone : elle ne sera plus proposée, sans gêner les commandes en cours.',
                          code=status.HTTP_409_CONFLICT)
        zone.delete()
        return Response({'success': True})

    def _save(self, request, zone):
        data = request.data
        errors = {}
        for field in ('name', 'city'):
            if field in data or not zone.pk:
                value = str(data.get(field) or '').strip()
                if not value:
                    errors[field] = ['Champ obligatoire.']
                else:
                    setattr(zone, field, value[:100])
        if 'description' in data:
            zone.description = str(data.get('description') or '')
        if 'is_active' in data:
            zone.is_active = str(data['is_active']).lower() in ('true', '1', 'yes', 'on')
        if 'inter_city_surcharge' in data:
            value = _money(data['inter_city_surcharge'], 'inter_city_surcharge', errors)
            if value is not None:
                zone.inter_city_surcharge = value
        rates = data.get('rates') or []
        cleaned_rates = []
        for rate in rates:
            vehicle = VehicleType.objects.filter(pk=rate.get('vehicle_id')).first()
            if not vehicle:
                continue
            price = rate.get('price')
            if price in (None, ''):
                cleaned_rates.append((vehicle, None))
                continue
            amount = _money(price, f'rate_{vehicle.id}', errors)
            if amount is not None:
                cleaned_rates.append((vehicle, amount))
        if errors:
            return _error('Zone non enregistrée.', 'Certaines valeurs ne sont pas valides.', 'Corrigez les champs indiqués.', errors)
        try:
            with transaction.atomic():
                zone.save()
                for vehicle, amount in cleaned_rates:
                    if amount is None:
                        ZoneVehicleRate.objects.filter(zone=zone, vehicle=vehicle).delete()
                    else:
                        ZoneVehicleRate.objects.update_or_create(
                            zone=zone, vehicle=vehicle, defaults={'base_price': amount, 'is_active': True},
                        )
        except IntegrityError:
            return _error('Zone déjà existante.', f'Une zone « {zone.name} » existe déjà à {zone.city}.',
                          'Modifiez la zone existante ou choisissez un autre nom.', code=status.HTTP_409_CONFLICT)
        vehicles = list(VehicleType.objects.order_by('max_weight_kg'))
        zone = DeliveryZone.objects.prefetch_related('vehicle_rates').get(pk=zone.pk)
        return Response({'success': True, 'data': _zone_data(zone, vehicles)})


class VehicleTypeAdminView(APIView):
    permission_classes = [IsPlatformAdmin]
    MONEY = ('base_price_intra_city', 'price_per_km_intra_city', 'base_price_inter_city', 'price_per_km_inter_city')
    LIMITS = ('max_weight_kg', 'max_length_m', 'max_distance_km')

    def patch(self, request, vehicle_id):
        vehicle = get_object_or_404(VehicleType, pk=vehicle_id)
        errors = {}
        for field in self.MONEY + self.LIMITS:
            if field in request.data:
                value = _money(request.data[field], field, errors)
                if value is not None:
                    setattr(vehicle, field, value)
        if 'max_items' in request.data:
            try:
                vehicle.max_items = max(0, int(request.data['max_items']))
            except (TypeError, ValueError):
                errors['max_items'] = ['Nombre entier attendu.']
        for field in ('allow_intercity', 'is_active'):
            if field in request.data:
                setattr(vehicle, field, str(request.data[field]).lower() in ('true', '1', 'yes', 'on'))
        if errors:
            return _error('Véhicule non enregistré.', 'Certaines valeurs ne sont pas valides.', 'Corrigez les champs indiqués.', errors)
        vehicle.save()
        return Response({'success': True, 'data': _vehicle_data(vehicle)})


class CityDistanceAdminView(APIView):
    permission_classes = [IsPlatformAdmin]

    def post(self, request):
        return self._save(request, CityDistance())

    def patch(self, request, distance_id):
        return self._save(request, get_object_or_404(CityDistance, pk=distance_id))

    def delete(self, request, distance_id):
        get_object_or_404(CityDistance, pk=distance_id).delete()
        return Response({'success': True})

    def _save(self, request, distance):
        data = request.data
        errors = {}
        for field in ('from_city', 'to_city'):
            if field in data or not distance.pk:
                value = str(data.get(field) or '').strip()
                if not value:
                    errors[field] = ['Ville obligatoire.']
                setattr(distance, field, value[:100])
        if distance.from_city and distance.from_city == distance.to_city:
            errors['to_city'] = ['Choisissez deux villes différentes.']
        if 'distance_km' in data or not distance.pk:
            value = _money(data.get('distance_km'), 'distance_km', errors, minimum=Decimal('0.1'))
            if value is not None:
                distance.distance_km = value
        if 'estimated_time_minutes' in data or not distance.pk:
            try:
                distance.estimated_time_minutes = max(1, int(data.get('estimated_time_minutes') or 0))
            except (TypeError, ValueError):
                errors['estimated_time_minutes'] = ['Nombre de minutes attendu.']
        if errors:
            return _error('Distance non enregistrée.', 'Certaines valeurs ne sont pas valides.', 'Corrigez les champs indiqués.', errors)
        try:
            distance.save()
        except IntegrityError:
            return _error('Trajet déjà enregistré.', f'{distance.from_city} → {distance.to_city} existe déjà.',
                          'Modifiez la ligne existante.', code=status.HTTP_409_CONFLICT)
        return Response({'success': True, 'data': {
            'id': distance.id, 'from_city': distance.from_city, 'to_city': distance.to_city,
            'distance_km': float(distance.distance_km), 'estimated_time_minutes': distance.estimated_time_minutes,
        }})


class DeliveryPriceSimulatorView(APIView):
    """Prix qu'un client paierait, avec le même calcul que la commande."""
    permission_classes = [IsPlatformAdmin]

    def post(self, request):
        zone = DeliveryZone.objects.filter(pk=request.data.get('zone_id')).first()
        vehicle = VehicleType.objects.filter(pk=request.data.get('vehicle_id')).first()
        store_city = str(request.data.get('store_city') or '').strip()
        rules = SystemSettings.get_settings()
        express = request.data.get('delivery_type') == 'express'
        fallback = rules.default_express_delivery_fee if express else rules.default_delivery_fee
        steps = []
        rate = ZoneVehicleRate.objects.filter(zone=zone, vehicle=vehicle, is_active=True).first() if zone and vehicle else None
        if zone and not zone.is_active:
            rate = None
            steps.append(f'La zone {zone.name} est désactivée : elle n’est pas proposée aux clients.')
        if rate:
            price = Decimal(rate.base_price)
            steps.append(f'Tarif de la zone {zone.name} pour {vehicle.get_name_display()} : {int(price)} FCFA.')
        else:
            price = Decimal(fallback)
            steps.append(f'Pas de tarif de zone pour ce véhicule : prix du commerce ({int(price)} FCFA par défaut).')
        client_city = zone.city if zone else ''
        if store_city and client_city and store_city != client_city:
            surcharge = Decimal(zone.inter_city_surcharge) if zone else Decimal(rules.default_intercity_surcharge)
            price += surcharge
            steps.append(f'Autre ville que le commerce ({store_city} → {client_city}) : +{int(surcharge)} FCFA.')
        courier = SystemSettings.courier_share(price)
        return Response({'success': True, 'data': {
            'price': float(price), 'courier_share': float(courier), 'gaboshop_share': float(price - courier), 'steps': steps,
        }})


def _delivery_row(delivery, now):
    order = delivery.order
    agent = delivery.delivery_agent
    started = delivery.assigned_at or delivery.created_at
    return {
        'id': delivery.id, 'status': delivery.status, 'status_label': delivery.get_status_display(),
        'order_id': order.id if order else None, 'order_number': order.order_number if order else '',
        'order_status': order.status if order else '',
        'store': order.store.name if order and order.store else '', 'store_phone': order.store.phone if order and order.store else '',
        'client_phone': order.delivery_phone if order else '', 'zone': order.delivery_zone if order else '',
        'city': getattr(order, 'city', '') or '', 'address': order.delivery_address if order else '',
        'delivery_fee': float(order.delivery_fee or 0) if order else 0,
        'agent_id': agent.id if agent else None, 'agent_name': (agent.get_full_name() or agent.phone) if agent else '',
        'agent_phone': agent.phone if agent else '',
        'created_at': delivery.created_at, 'assigned_at': delivery.assigned_at,
        'minutes_waiting': int((now - started).total_seconds() // 60) if started else None,
        'proof_photos': _proof_photos(delivery),
    }


def _proof_photos(delivery):
    """Quelles photos de preuve existent ; l'admin les ouvre via la vue protégée."""
    proof = getattr(delivery, 'proof', None) if hasattr(delivery, 'proof') else None
    kinds = []
    if proof is not None and proof.id_card_photo:
        kinds.append('id_card')
    if proof is not None and proof.package_photo:
        kinds.append('package')
    if proof is not None and proof.signature:
        kinds.append('signature')
    if delivery.delivery_proof_photo:
        kinds.append('photo')
    return kinds


class DeliveryOperationsView(APIView):
    """Attribution (courses sans livreur) et courses en cours."""
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        now = timezone.now()
        base = Delivery.objects.select_related('order__store', 'delivery_agent', 'proof').exclude(order__status='cancelled')
        waiting = base.filter(Q(delivery_agent__isnull=True) | Q(status__in=WAITING_STATUSES)).filter(
            order__status__in=('ready', 'assigned', 'confirmed', 'preparing')).exclude(status__in=('delivered', 'cancelled', 'failed'))
        active = base.filter(status__in=ACTIVE_STATUSES, delivery_agent__isnull=False)
        couriers = []
        busy = dict(
            Delivery.objects.filter(status__in=ACTIVE_STATUSES, delivery_agent__isnull=False)
            .values_list('delivery_agent').annotate(n=Count('id'))
        )
        for profile in LivreurProfile.objects.select_related('user').filter(user__is_active=True).order_by('-disponible', 'user__first_name'):
            couriers.append({
                'id': profile.user_id, 'name': profile.user.get_full_name() or profile.user.phone, 'phone': profile.user.phone,
                'city': profile.user.city or '', 'available': bool(profile.disponible and profile.user.is_available),
                'active_deliveries': busy.get(profile.user_id, 0),
                'has_mobile_money': bool(profile.mobile_money_phone),
            })
        return Response({'success': True, 'data': {
            'waiting': [_delivery_row(d, now) for d in waiting.order_by('created_at')[:100]],
            'active': [_delivery_row(d, now) for d in active.order_by('assigned_at')[:200]],
            'couriers': couriers,
            'max_active_per_courier': SystemSettings.current('max_orders_per_delivery', 3),
        }})


class DeliveryStatsView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        try:
            days = min(max(int(request.query_params.get('days', 7)), 1), 365)
        except ValueError:
            days = 7
        since = timezone.now() - timedelta(days=days)
        period = Delivery.objects.filter(created_at__gte=since)
        delivered = period.filter(status='delivered')
        durations = delivered.filter(delivered_at__isnull=False, assigned_at__isnull=False).annotate(
            took=F('delivered_at') - F('assigned_at')).aggregate(avg=Avg('took'))['avg']
        payouts = DeliveryPayout.objects.filter(created_at__gte=since)
        per_courier = []
        rows = (
            period.filter(delivery_agent__isnull=False).values('delivery_agent', 'delivery_agent__first_name',
                                                                 'delivery_agent__last_name', 'delivery_agent__phone')
            .annotate(total=Count('id'), done=Count('id', filter=Q(status='delivered')),
                      failed=Count('id', filter=Q(status__in=('failed', 'cancelled'))))
            .order_by('-done')
        )
        paid = dict(payouts.filter(status='completed').values_list('delivery_agent').annotate(s=Sum('calculated_payout')))
        owed = dict(payouts.exclude(status='completed').values_list('delivery_agent').annotate(s=Sum('calculated_payout')))
        for row in rows[:100]:
            agent_id = row['delivery_agent']
            name = f"{row['delivery_agent__first_name'] or ''} {row['delivery_agent__last_name'] or ''}".strip()
            per_courier.append({
                'id': agent_id, 'name': name or row['delivery_agent__phone'], 'total': row['total'],
                'delivered': row['done'], 'failed': row['failed'],
                'paid': float(paid.get(agent_id) or 0), 'owed': float(owed.get(agent_id) or 0),
            })
        return Response({'success': True, 'data': {
            'days': days,
            'total': period.count(),
            'delivered': delivered.count(),
            'failed': period.filter(status__in=('failed', 'cancelled')).count(),
            'average_minutes': int(durations.total_seconds() // 60) if durations else None,
            'delivery_fees': float(delivered.aggregate(s=Sum('order__delivery_fee'))['s'] or 0),
            'courier_paid': float(payouts.filter(status='completed').aggregate(s=Sum('calculated_payout'))['s'] or 0),
            'courier_owed': float(payouts.exclude(status='completed').aggregate(s=Sum('calculated_payout'))['s'] or 0),
            'per_courier': per_courier,
        }})


class DeliveryIncidentsView(APIView):
    """Ce qui demande l'attention de l'admin, avec la raison et quoi faire."""
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        now = timezone.now()
        rules = SystemSettings.get_settings()
        items = []
        recent = now - timedelta(days=30)

        late_limit = now - timedelta(hours=rules.late_delivery_hours)
        for d in Delivery.objects.select_related('order__store', 'delivery_agent', 'proof').filter(
                status__in=ACTIVE_STATUSES, assigned_at__lt=late_limit):
            items.append({**_delivery_row(d, now), 'kind': 'late', 'title': 'Livraison en retard',
                          'reason': f'En cours depuis plus de {rules.late_delivery_hours} h.',
                          'next_step': 'Appelez le livreur, puis le client si besoin.'})
        wait_limit = now - timedelta(minutes=rules.broadcast_after_minutes)
        for d in Delivery.objects.select_related('order__store', 'delivery_agent', 'proof').filter(
                delivery_agent__isnull=True, order__status='ready', created_at__lt=wait_limit):
            items.append({**_delivery_row(d, now), 'kind': 'no_courier', 'title': 'Aucun livreur trouvé',
                          'reason': f'Commande prête depuis plus de {rules.broadcast_after_minutes} min sans livreur.',
                          'next_step': 'Attribuez un livreur dans l’onglet Attribution.'})
        for d in Delivery.objects.select_related('order__store', 'delivery_agent', 'proof').filter(
                status='failed', updated_at__gte=recent):
            items.append({**_delivery_row(d, now), 'kind': 'failed', 'title': 'Livraison échouée',
                          'reason': 'Le livreur a déclaré un échec.', 'next_step': 'Contactez le client et le commerce pour relivrer ou rembourser.'})
        confirm_limit = now - timedelta(hours=24)
        for d in Delivery.objects.select_related('order__store', 'delivery_agent', 'proof').filter(
                order__status='delivered', delivered_at__lt=confirm_limit, delivered_at__gte=recent,
                proof__client_received_status=False):
            items.append({**_delivery_row(d, now), 'kind': 'unconfirmed', 'title': 'Réception pas confirmée',
                          'reason': 'Livrée depuis plus de 24 h, le client n’a pas confirmé : le livreur n’est pas encore payé.',
                          'next_step': 'Appelez le client pour qu’il confirme la réception.'})
        for payout in DeliveryPayout.objects.select_related('delivery_agent', 'order').filter(
                status__in=('pending', 'failed'), created_at__gte=recent):
            agent = payout.delivery_agent
            items.append({
                'kind': 'payout', 'title': 'Livreur pas encore payé' if payout.status == 'pending' else 'Paiement livreur échoué',
                'reason': payout.note or 'Versement en attente.',
                'next_step': 'Créez son décaissement SingPay ou payez-le à la main, puis marquez le versement payé dans Finances.',
                'order_number': payout.order.order_number if payout.order_id else '', 'agent_name': (agent.get_full_name() or agent.phone) if agent else '',
                'agent_phone': agent.phone if agent else '', 'amount': float(payout.calculated_payout or 0),
                'created_at': payout.created_at,
            })
        return Response({'success': True, 'data': items})
