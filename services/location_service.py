import math
import logging
from typing import List, Optional
from users.models import User

logger = logging.getLogger(__name__)

class LocationService:
    """Service de gestion de la géolocalisation"""
    
    @staticmethod
    def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculer la distance en km entre deux points GPS
        Utilise la formule de Haversine
        """
        R = 6371  # Rayon de la Terre en km
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = (math.sin(dlat / 2) * math.sin(dlat / 2) +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon / 2) * math.sin(dlon / 2))
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = R * c
        
        return distance
    
    @staticmethod
    def find_nearest_delivery_agents(store_lat: float, store_lon: float, limit: int = 5) -> List[User]:
        """
        Trouver les livreurs les plus proches d'un magasin
        """
        try:
            # Récupérer les livreurs disponibles
            available_agents = User.objects.filter(
                user_type='delivery_agent',
                is_available=True
            ).exclude(current_location__isnull=True).exclude(current_location='')
            
            agents_with_distance = []
            
            for agent in available_agents:
                # Extraire les coordonnées du livreur
                # Format attendu: "lat,lon" dans current_location
                if ',' in agent.current_location:
                    try:
                        agent_lat, agent_lon = map(float, agent.current_location.split(','))
                        distance = LocationService.calculate_distance(
                            store_lat, store_lon, agent_lat, agent_lon
                        )
                        
                        agents_with_distance.append((agent, distance))
                    except (ValueError, TypeError):
                        continue
            
            # Trier par distance et retourner les plus proches
            agents_with_distance.sort(key=lambda x: x[1])
            return [agent for agent, distance in agents_with_distance[:limit]]
            
        except Exception as e:
            logger.error(f"❌ Erreur recherche livreurs: {e}")
            return []
    
    @staticmethod
    def estimate_delivery_time(distance_km: float, traffic_factor: float = 1.2) -> int:
        """
        Estimer le temps de livraison en minutes
        """
        # Vitesse moyenne à Libreville: 20-30 km/h en scooter
        average_speed_kmh = 25
        base_time_minutes = (distance_km / average_speed_kmh) * 60
        
        # Appliquer le facteur trafic
        estimated_time = base_time_minutes * traffic_factor
        
        # Arrondir à la minute supérieure, minimum 10 minutes
        return max(10, math.ceil(estimated_time))
