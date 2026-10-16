"""Adresses : Province › Ville › Arrondissement › Quartier.

GET /geo/ : tout le référentiel actif (listes de choix du client).
Admin : GET/POST/PATCH /admin/geo/<niveau>/[<id>/] pour ajouter, renommer, désactiver, ouvrir une ville
et rattacher un quartier à une zone de prix.
"""
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.v1.admin import IsPlatformAdmin
from delivery.models import Arrondissement, City, DeliveryZone, Landmark, Neighborhood, Province
from delivery.zones import geo_tree


def _bool(value):
    return str(value).lower() in ('true', '1', 'yes', 'on', 'oui')


def _error(message, next_step='', code=status.HTTP_400_BAD_REQUEST):
    return Response({'success': False, 'error': {'message': message, 'reason': '', 'next_step': next_step}}, status=code)


class GeoTreeView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({'success': True, 'data': geo_tree()})


# niveau -> (modèle, parent (champ, modèle) ou None, champs booléens modifiables)
LEVELS = {
    'provinces': (Province, None, ('is_active',)),
    'cities': (City, ('province', Province), ('is_active', 'is_open')),
    'arrondissements': (Arrondissement, ('city', City), ('is_active',)),
    'neighborhoods': (Neighborhood, ('city', City), ('is_active',)),
    'landmarks': (Landmark, ('neighborhood', Neighborhood), ('is_active',)),
}


class GeoAdminView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request, level):
        """Tout le référentiel, y compris ce qui est désactivé, plus les zones de prix."""
        if level != 'all':
            return _error('Liste inconnue.', code=status.HTTP_404_NOT_FOUND)
        return Response({'success': True, 'data': {
            'provinces': list(Province.objects.values('id', 'name', 'is_active', 'order')),
            'cities': list(City.objects.values('id', 'name', 'province_id', 'is_active', 'is_open', 'order')),
            'arrondissements': list(Arrondissement.objects.values('id', 'name', 'city_id', 'number', 'is_active')),
            'neighborhoods': list(Neighborhood.objects.values('id', 'name', 'city_id', 'arrondissement_id', 'zone_id', 'is_active')),
            'landmarks': list(Landmark.objects.values('id', 'name', 'neighborhood_id', 'is_active')),
            'zones': list(DeliveryZone.objects.values('id', 'name', 'city', 'is_active')),
        }})

    def post(self, request, level):
        if level not in LEVELS:
            return _error('Liste inconnue.', code=status.HTTP_404_NOT_FOUND)
        return self._save(request, level, LEVELS[level][0]())

    def patch(self, request, level, item_id=None):
        if level not in LEVELS or item_id is None:
            return _error('Liste inconnue.', code=status.HTTP_404_NOT_FOUND)
        return self._save(request, level, get_object_or_404(LEVELS[level][0], pk=item_id))

    def _save(self, request, level, obj):
        model, parent, flags = LEVELS[level]
        data = request.data
        if 'name' in data or not obj.pk:
            name = str(data.get('name') or '').strip()[:100]
            if not name:
                return _error('Le nom est obligatoire.', 'Tapez un nom puis enregistrez.')
            obj.name = name
        if parent and (not obj.pk or f'{parent[0]}_id' in data):
            parent_obj = parent[1].objects.filter(pk=data.get(f'{parent[0]}_id')).first()
            if parent_obj is None:
                return _error('Choisissez où ranger cet élément.', 'Sélectionnez la province ou la ville parente.')
            setattr(obj, parent[0], parent_obj)
        for flag in flags:
            if flag in data:
                setattr(obj, flag, _bool(data[flag]))
        if level == 'arrondissements' and 'number' in data:
            try:
                obj.number = max(0, int(data['number']))
            except (TypeError, ValueError):
                return _error('Numéro invalide.')
        if level == 'neighborhoods':
            # La cascade se suit : dans une ville à arrondissements, chaque quartier est rangé dans le sien.
            if not obj.pk and not data.get('arrondissement_id') and obj.city.arrondissements.exists():
                return _error("Choisissez l'arrondissement du quartier.",
                              "Sélectionnez l'arrondissement puis ajoutez le quartier.")
            if 'arrondissement_id' in data:
                value = data.get('arrondissement_id')
                arr = Arrondissement.objects.filter(pk=value).first() if value else None
                if value and (arr is None or arr.city_id != obj.city_id):
                    return _error("Cet arrondissement n'est pas dans la ville du quartier.")
                obj.arrondissement = arr
            if 'zone_id' in data:
                value = data.get('zone_id')
                zone = DeliveryZone.objects.filter(pk=value).first() if value else None
                if value and zone is None:
                    return _error('Zone de prix introuvable.')
                obj.zone = zone
        try:
            obj.save()
        except IntegrityError:
            return _error('Ce nom existe déjà à cet endroit.', 'Choisissez un autre nom.', code=status.HTTP_409_CONFLICT)
        return Response({'success': True, 'data': {'id': obj.pk}})
