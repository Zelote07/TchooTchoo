import os
from datetime import datetime

import requests
from dotenv import load_dotenv

# Clé lue depuis le fichier .env (voir .env.example) — ne jamais la versionner
load_dotenv()
API_KEY = os.getenv('SNCF_API_KEY')
BASE_URL_SNCF = 'https://api.sncf.com/v1/coverage/sncf'

def search_station(query):
    """
    Recherche une gare (ou lieu) par son nom pour récupérer son identifiant (nécessaire pour les trajets).
    """
    url = f"{BASE_URL_SNCF}/places"
    params = {'q': query}
    
    # Authentification: Username = API_KEY, Password = vide
    response = requests.get(url, params=params, auth=(API_KEY, ''))
    
    if response.status_code == 200:
        data = response.json()
        places = data.get('places', [])
        return places
    else:
        print(f"Erreur de l'API ({response.status_code}): {response.text}")
        return []

def get_itineraries(departure_id, arrival_id, date_time=None):
    """
    Récupère les itinéraires (journeys) entre deux gares.
    """
    url = f"{BASE_URL_SNCF}/journeys"
    params = {
        'from': departure_id,
        'to': arrival_id,
        'min_nb_journeys': 3 # Demande au moins 3 trajets
    }
    
    if date_time:
        # L'API s'attend au format YYYYMMDDTHHMMSS
        params['datetime'] = date_time.strftime('%Y%m%dT%H%M%S')
        
    response = requests.get(url, params=params, auth=(API_KEY, ''))
    
    if response.status_code == 200:
        return response.json().get('journeys', [])
    else:
        print(f"Erreur de l'API ({response.status_code}): {response.text}")
        return []

if __name__ == "__main__":
    if not API_KEY:
        print("⚠️  Renseigne SNCF_API_KEY dans le fichier .env (voir .env.example) !")
    else:
        # --- 1. Chercher l'identifiant pour la gare de départ ---
        ville_depart = "Paris"
        print(f"Recherche de la gare '{ville_depart}'...")
        places_depart = search_station(ville_depart)
        
        if not places_depart:
            exit("Gare de départ non trouvée.")
            
        id_depart = places_depart[0]['id']
        nom_depart = places_depart[0]['name']
        print(f"[OK] Départ trouvé : {nom_depart} (ID: {id_depart})")
        
        # --- 2. Chercher l'identifiant pour la gare d'arrivée (ex: zone touristique rurale) ---
        ville_arrivee = "Aurillac" 
        print(f"\nRecherche de la gare '{ville_arrivee}'...")
        places_arrivee = search_station(ville_arrivee)
        
        if not places_arrivee:
            exit("Gare d'arrivée non trouvée.")
            
        id_arrivee = places_arrivee[0]['id']
        nom_arrivee = places_arrivee[0]['name']
        print(f"[OK] Arrivée trouvée : {nom_arrivee} (ID: {id_arrivee})")
        
        # --- 3. Calculer l'itinéraire ---
        print("\nCalcul des itinéraires...")
        journeys = get_itineraries(id_depart, id_arrivee, datetime.now())
        
        print(f"\n===== {len(journeys)} trajets trouvés =====")
        for i, journey in enumerate(journeys):
            duration_minutes = journey['duration'] // 60 # secondes en minutes
            
            # Conversion des dates
            dep_date = datetime.strptime(journey['departure_date_time'], '%Y%m%dT%H%M%S')
            arr_date = datetime.strptime(journey['arrival_date_time'], '%Y%m%dT%H%M%S')
            
            # --- KPI : CO2 Emission ---
            # Idéal pour ton "badge écologique (moins de X de CO2)" mentionné dans ton doc.md
            co2 = journey.get('co2_emission', {}).get('value', 'N/A')
            
            print(f"\n[Trajet {i+1}] :")
            print(f"  Départ   : {dep_date.strftime('%d/%m/%Y à %H:%M')}")
            print(f"  Arrivée  : {arr_date.strftime('%d/%m/%Y à %H:%M')}")
            print(f"  Temps    : {duration_minutes} minutes")
            print(f"  Bilan CO2: {co2} g")
