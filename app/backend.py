from flask import Flask, request, jsonify, render_template
import requests
import altair as alt
import pandas as pd
from datetime import datetime

app = Flask(__name__, static_folder='static', template_folder='templates')

import os
import random
import json
from dotenv import load_dotenv

# Charge les variables d'environnement
load_dotenv()

search_cache = {}

API_KEY = os.getenv('SNCF_API_KEY')
if not API_KEY:
    print("ATTENTION : Aucune clé API trouvée. Avez-vous créé le fichier .env ?")
BASE_URL_SNCF = 'https://api.sncf.com/v1/coverage/sncf'

# Chargement de la base de données culturelle au démarrage
csv_path = os.path.join(os.path.dirname(__file__), '../data/base-des-lieux-et-des-equipements-culturels.csv')
df_culture = pd.read_csv(csv_path, sep=';', low_memory=False)

# Chargement des stats cyclables
cycle_path = os.path.join(os.path.dirname(__file__), '../data/cycle_stats_by_city.json')
cycle_stats = {}
if os.path.exists(cycle_path):
    with open(cycle_path, 'r', encoding='utf-8') as f:
        cycle_stats = json.load(f)

# Nettoyage et calcul des coordonnées par ville
df_culture['Latitude'] = pd.to_numeric(df_culture['Latitude'].astype(str).str.replace(',', '.'), errors='coerce')
df_culture['Longitude'] = pd.to_numeric(df_culture['Longitude'].astype(str).str.replace(',', '.'), errors='coerce')
city_coords = df_culture.groupby('libelle_geographique')[['Latitude', 'Longitude']].mean()

city_counts = df_culture['libelle_geographique'].value_counts()
# Villes moyennes avec un potentiel touristique raisonnable (entre 5 et 40 lieux culturels)
potential_cities = city_counts[(city_counts >= 5) & (city_counts <= 40)].index.tolist()

import math

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def get_city_pois(city, default_lat=None, default_lon=None, limit=12):
    try:
        sub = df_culture[df_culture['libelle_geographique'] == city].dropna(subset=['Nom'])
        pois = []
        for _, row in sub.head(limit).iterrows():
            lat_val = row['Latitude']
            lon_val = row['Longitude']
            p_lat = float(lat_val) if (pd.notna(lat_val) and str(lat_val).strip() != '') else default_lat
            p_lon = float(lon_val) if (pd.notna(lon_val) and str(lon_val).strip() != '') else default_lon
            
            nom = str(row['Nom']).replace('\ufffd', 'e')
            domaine = str(row['Domaine']).replace('\ufffd', 'e') if pd.notna(row['Domaine']) else "Culture"
            adresse = str(row['Adresse']).replace('\ufffd', 'e') if pd.notna(row['Adresse']) else ""
            
            pois.append({
                "nom": nom,
                "domaine": domaine,
                "adresse": adresse,
                "lat": p_lat,
                "lon": p_lon
            })
        return pois
    except Exception as e:
        print(f"Erreur get_city_pois pour {city}: {e}")
        return []

def search_station(query):
    url = f"{BASE_URL_SNCF}/places"
    params = {'q': query}
    response = requests.get(url, params=params, auth=(API_KEY, ''))
    if response.status_code == 200:
        return response.json().get('places', [])
    return []

def get_coords(place):
    if not place: return None
    t = place.get('embedded_type')
    if t and t in place and 'coord' in place[t]:
        return float(place[t]['coord']['lat']), float(place[t]['coord']['lon'])
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/autocomplete')
def autocomplete():
    q = request.args.get('q', '')
    if len(q) < 2:
        return jsonify([])
    places = search_station(q)
    results = [{"id": p['id'], "name": p['name']} for p in places if 'id' in p][:6]
    return jsonify(results)

@app.route('/api/search')
def search():
    depart = request.args.get('depart')
    id_depart = request.args.get('id_depart')
    max_duration = int(request.args.get('max_duration', 600))
    
    cache_key = (depart, id_depart, max_duration)
    if cache_key in search_cache:
        return jsonify(search_cache[cache_key])
        
    places_depart = search_station(depart)
    
    if not id_depart:
        if not places_depart: return jsonify({"error": f"Gare de départ introuvable"}), 404
        id_depart = places_depart[0]['id']
        nom_depart = places_depart[0]['name']
    else:
        nom_depart = depart
        
    dep_coords = get_coords(places_depart[0] if places_depart else None)
    
    valid_cities = potential_cities
    if dep_coords:
        import numpy as np
        lat, lon = dep_coords
        dist_deg = max_duration / 60.0 * 1.5
        
        distances = np.sqrt((city_coords['Latitude'] - lat)**2 + (city_coords['Longitude'] - lon)**2)
        nearby = distances[distances <= dist_deg].index.tolist()
        valid_cities = list(set(nearby) & set(potential_cities))
        
        if len(valid_cities) < 5:
            nearby = distances[distances <= dist_deg * 2].index.tolist()
            valid_cities = list(set(nearby) & set(potential_cities))
            
    if not valid_cities:
        valid_cities = potential_cities
        
    sample_size = min(len(valid_cities), 30)
    sampled_cities = random.sample(valid_cities, sample_size)
    destinations_dict = {}
    
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def process_city(city):
        try:
            places_arrivee = search_station(city)
            if not places_arrivee:
                return None
                
            id_arrivee = places_arrivee[0]['id']
            nom_arrivee = places_arrivee[0]['name']
            arr_coords = get_coords(places_arrivee[0])
            
            url = f"{BASE_URL_SNCF}/journeys"
            params = {'from': id_depart, 'to': id_arrivee, 'min_nb_journeys': 5}
            response = requests.get(url, params=params, auth=(API_KEY, ''), timeout=10)
            
            journeys = response.json().get('journeys', [])
            valid_journeys = []
            
            for j in journeys:
                duration_min = j['duration'] // 60
                if duration_min <= max_duration:
                    dep_dt = datetime.strptime(j['departure_date_time'], '%Y%m%dT%H%M%S')
                    arr_dt = datetime.strptime(j['arrival_date_time'], '%Y%m%dT%H%M%S')
                    co2 = j.get('co2_emission', {}).get('value', 0)
                    
                    valid_journeys.append({
                        "Départ": dep_dt.strftime('%H:%M'),
                        "Arrivée": arr_dt.strftime('%H:%M'),
                        "Durée (min)": duration_min,
                        "CO2 (g)": co2,
                        "dep_dt_iso": dep_dt.isoformat()
                    })
            
            if valid_journeys:
                valid_journeys.sort(key=lambda x: x["dep_dt_iso"])
                min_duration = min(j["Durée (min)"] for j in valid_journeys)
                min_co2 = min(j["CO2 (g)"] for j in valid_journeys)
                
                # Coordonnées destination
                dest_lat = arr_coords[0] if arr_coords else None
                dest_lon = arr_coords[1] if arr_coords else None
                if dest_lat is None and city in city_coords.index:
                    dest_lat = float(city_coords.loc[city]['Latitude'])
                    dest_lon = float(city_coords.loc[city]['Longitude'])
                
                # Distance et calcul CO2 comparatif
                dist_km = 0
                if dep_coords and dest_lat is not None and dest_lon is not None:
                    dist_km = round(haversine_distance(dep_coords[0], dep_coords[1], dest_lat, dest_lon), 1)
                
                road_km = round(dist_km * 1.25 if dist_km > 0 else (min_duration / 60.0 * 95), 1)
                train_kg = round(min_co2 / 1000.0, 2) if min_co2 > 0 else round(max(0.2, dist_km * 0.012), 2)
                voiture_kg = round(max(1.2, road_km * 0.190), 2)
                covoit_kg = round(max(0.5, road_km * 0.065), 2)
                voiture_elec_kg = round(max(0.4, road_km * 0.045), 2)
                avion_kg = round(max(2.5, (dist_km if dist_km > 0 else road_km) * 0.230), 2)

                saved_kg = round(max(0.1, voiture_kg - train_kg), 1)
                saved_pct = int(round((1.0 - (train_kg / max(0.1, voiture_kg))) * 100))
                saved_pct = max(10, min(99, saved_pct))
                trees_equiv = round(saved_kg / 25.0, 1)

                pois = get_city_pois(city, default_lat=dest_lat, default_lon=dest_lon, limit=12)

                return {
                    "nom_arrivee": nom_arrivee,
                    "data": {
                        "Gare Destination": nom_arrivee,
                        "Ville": city,
                        "Points Culturels": int(city_counts[city]),
                        "Aménagements Cyclables": cycle_stats.get(city, 0),
                        "Durée (min)": min_duration,
                        "CO2 (g)": min_co2,
                        "coords": [dest_lat, dest_lon] if (dest_lat is not None and dest_lon is not None) else None,
                        "distance_km": dist_km,
                        "co2_comparison": {
                            "train_kg": train_kg,
                            "voiture_kg": voiture_kg,
                            "covoit_kg": covoit_kg,
                            "voiture_elec_kg": voiture_elec_kg,
                            "avion_kg": avion_kg,
                            "saved_kg": saved_kg,
                            "saved_pct": saved_pct,
                            "trees_equiv": trees_equiv,
                            "modes": [
                                {"mode": "🚆 Train", "co2_kg": train_kg, "color": "#0088ce"},
                                {"mode": "⚡ Voiture élec.", "co2_kg": voiture_elec_kg, "color": "#10b981"},
                                {"mode": "👥 Covoiturage", "co2_kg": covoit_kg, "color": "#f59e0b"},
                                {"mode": "🚘 Voiture thermique", "co2_kg": voiture_kg, "color": "#ef4444"},
                                {"mode": "✈️ Avion", "co2_kg": avion_kg, "color": "#8b5cf6"}
                            ]
                        },
                        "pois": pois,
                        "Trajets": valid_journeys
                    }
                }
        except Exception as e:
            print(f"Erreur pour la ville {city}: {e}")
            return None
        return None

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(process_city, city) for city in sampled_cities]
        for future in as_completed(futures):
            res = future.result()
            if res:
                destinations_dict[res["nom_arrivee"]] = res["data"]
            if len(destinations_dict) >= 15:
                break
            
    if not destinations_dict:
        return jsonify({"error": f"Aucune destination trouvée sous {max_duration} min vers nos villes culturelles. Essayez d'augmenter la durée."}), 404
        
    df = pd.DataFrame(list(destinations_dict.values())).sort_values(by="Durée (min)")
    df['Durée (min)'] = df['Durée (min)'].astype(int)
    
    chart = alt.Chart(df).mark_bar(
        cornerRadiusTopLeft=2, 
        cornerRadiusTopRight=2,
        size=35,
        color='#0088ce'
    ).encode(
        x=alt.X('Gare Destination:N', title="Destinations", sort=None, axis=alt.Axis(labelAngle=-45)),
        y=alt.Y('Durée (min):Q', title="Durée min (minutes)"),
        tooltip=['Gare Destination', 'Durée (min)', 'Points Culturels', 'Aménagements Cyclables', 'CO2 (g)']
    ).properties(
        width='container',
        height=350
    ).configure_view(strokeOpacity=0).configure_axis(grid=False)
    
    response_data = {
        "info": {
            "depart": nom_depart,
            "dep_coords": dep_coords
        },
        "journeys": df.to_dict(orient="records"),
        "chart_json": chart.to_dict()
    }
    
    if len(search_cache) > 1000:
        search_cache.clear()
    search_cache[cache_key] = response_data
    
    return jsonify(response_data)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
