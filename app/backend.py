import dash
from dash import html, dcc, Input, Output, State, callback
import dash_leaflet as dl
import plotly.express as px
import pandas as pd
import requests
from datetime import datetime
import os
import random
import json
import math
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from dash_extensions.javascript import assign

load_dotenv()
API_KEY = os.getenv('SNCF_API_KEY')
BASE_URL_SNCF = 'https://api.sncf.com/v1/coverage/sncf'

# Data load
csv_path = os.path.join(os.path.dirname(__file__), '../data/base-des-lieux-et-des-equipements-culturels.csv')
df_culture = pd.read_csv(csv_path, sep=';', low_memory=False)

cycle_path = os.path.join(os.path.dirname(__file__), '../data/cycle_stats_by_city.json')
cycle_stats = {}
if os.path.exists(cycle_path):
    with open(cycle_path, 'r', encoding='utf-8') as f:
        cycle_stats = json.load(f)

df_culture['Latitude'] = pd.to_numeric(df_culture['Latitude'].astype(str).str.replace(',', '.'), errors='coerce')
df_culture['Longitude'] = pd.to_numeric(df_culture['Longitude'].astype(str).str.replace(',', '.'), errors='coerce')
city_coords = df_culture.groupby('libelle_geographique')[['Latitude', 'Longitude']].mean()
city_counts = df_culture['libelle_geographique'].value_counts()
potential_cities = city_counts[(city_counts >= 5) & (city_counts <= 40)].index.tolist()

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
            
            pois.append({"nom": nom, "domaine": domaine, "lat": p_lat, "lon": p_lon})
        return pois
    except:
        return []

def search_station(query):
    url = f"{BASE_URL_SNCF}/places"
    params = {'q': query}
    try:
        response = requests.get(url, params=params, auth=(API_KEY, ''), timeout=5)
        if response.status_code == 200:
            return response.json().get('places', [])
    except:
        pass
    return []

def get_coords(place):
    if not place: return None
    t = place.get('embedded_type')
    if t and t in place and 'coord' in place[t]:
        return float(place[t]['coord']['lat']), float(place[t]['coord']['lon'])
    return None

app = dash.Dash(__name__, suppress_callback_exceptions=True)

app.layout = html.Div(className="dashboard-wrapper", children=[
    dcc.Store(id='search-results-store'),
    
    html.Header(className="app-header", children=[
        html.Div(className="brand", children=[
            html.Div(className="brand-badge", children=[html.Span("🚆", className="train-icon")]),
            html.Div(className="brand-text", children=[
                html.H1(["TchooTchoo", html.Span("Connect")]),
                html.P("L'explorateur ferroviaire & culturel bas-carbone (Version Dash)", className="tagline")
            ])
        ]),
        html.Div(className="header-status", children=[
            html.Div(className="status-indicator", children=[
                html.Span(className="status-dot"),
                html.Span("Prêt à explorer", className="status-text", id="status-label")
            ])
        ])
    ]),
    
    html.Main(className="dashboard-grid", children=[
        html.Section(className="top-row", children=[
            html.Div(className="dash-card card-search", id="card-search", children=[
                html.Div(className="card-header", children=[
                    html.Div(className="card-title-group", children=[
                        html.Span("🎯", className="card-icon"),
                        html.Div([
                            html.H2("Ville de départ & Durée", className="card-title"),
                            html.Span("Trouvez votre prochaine escapade en train", className="card-subtitle")
                        ])
                    ])
                ]),
                html.Div(className="search-form", children=[
                    html.Div(className="form-inputs-row", children=[
                        html.Div(className="form-group autocomplete-group", children=[
                            html.Label("Gare de départ"),
                            dcc.Dropdown(
                                id='depart-dropdown',
                                placeholder="Ex: Paris, Lyon...",
                                options=[{'label': 'Paris', 'value': 'Paris'}],
                                value='Paris',
                                searchable=True,
                            )
                        ]),
                        html.Div(className="form-group duration-group", children=[
                            html.Div(className="duration-label-row", children=[
                                html.Label("Durée max :"),
                                html.Span("3h00 (180 min)", className="duration-display", id="duration-display")
                            ]),
                            html.Div(className="duration-slider-container", children=[
                                dcc.Slider(
                                    id='max-duration-slider',
                                    min=30, max=480, step=15, value=180,
                                    marks=None, tooltip={"placement": "bottom", "always_visible": False}
                                )
                            ])
                        ]),
                        html.Div(className="form-submit-group", children=[
                            html.Button("Explorer 🚀", id="submit-btn", className="btn-primary", n_clicks=0)
                        ])
                    ])
                ])
            ]),
            
            html.Div(className="dash-card card-eco-combined", id="card-eco-combined", children=[
                html.Div(className="eco-combined-layout", children=[
                    html.Div(className="eco-left-col", children=[
                        html.Div(className="card-header", children=[
                            html.Div(className="card-title-group", children=[
                                html.Span("🌱", className="card-icon"),
                                html.Div([
                                    html.H2("Bilan Écologique", className="card-title"),
                                    html.Span("Gain carbone de votre voyage", className="card-subtitle")
                                ])
                            ]),
                            html.Span("Éco", className="eco-badge-pill", id="eco-score-badge")
                        ]),
                        html.Div(className="eco-body", id="eco-body", children=[
                            html.Div(className="eco-metric-main", children=[
                                html.Span("-", className="eco-percentage", id="eco-saved-pct"),
                                html.Span("de CO₂ en moins vs voiture", className="eco-metric-label")
                            ]),
                            html.Div(className="eco-stats-sub", children=[
                                html.Div(className="eco-sub-item", children=[
                                    html.Span("-", className="eco-sub-value", id="eco-saved-kg"),
                                    html.Span("CO₂ évités", className="eco-sub-label")
                                ]),
                                html.Div(className="eco-sub-divider"),
                                html.Div(className="eco-sub-item", children=[
                                    html.Span("-", className="eco-sub-value", id="eco-trees"),
                                    html.Span("Arbres équivalents", className="eco-sub-label")
                                ]),
                                html.Div(className="eco-sub-divider"),
                                html.Div(className="eco-sub-item", children=[
                                    html.Span("-", className="eco-sub-value", id="eco-train-co2"),
                                    html.Span("Émission train", className="eco-sub-label")
                                ])
                            ])
                        ])
                    ]),
                    html.Div(className="eco-main-divider"),
                    html.Div(className="eco-right-col", children=[
                        html.Div(className="card-header", children=[
                            html.Div(className="card-title-group", children=[
                                html.Span("📊", className="card-icon"),
                                html.Div([
                                    html.H2("Comparatif Transports", className="card-title"),
                                    html.Span("Empreinte carbone (kg CO₂)", className="card-subtitle")
                                ])
                            ])
                        ]),
                        html.Div(className="chart-body", id="chart-body", children=[
                            dcc.Graph(id='co2-chart', config={'displayModeBar': False}, style={'height': '160px'})
                        ])
                    ])
                ])
            ])
        ]),
        
        html.Section(className="bottom-row", children=[
            html.Div(className="dash-card card-destination-details", id="card-destination", children=[
                html.Div(className="destination-header-block", children=[
                    html.Div(className="destination-select-wrapper", children=[
                        html.Div(className="select-label-row", children=[
                            html.Label([html.Span("🏙️", className="pin-icon"), " Ville à visiter :"], className="dest-label"),
                        ]),
                        html.Div(className="custom-select-container", children=[
                            dcc.Dropdown(id='destination-select', placeholder="Sélectionnez une destination...", style={'width': '100%'})
                        ])
                    ]),
                    html.Div(className="active-city-banner", id="active-city-banner", children=[
                        html.Div(className="banner-content", children=[
                            html.Div(className="city-main-info", children=[
                                html.H3("-", className="city-name", id="city-title"),
                                html.Span("-", className="city-station", id="station-title")
                            ]),
                            html.Div(className="city-badges-row", children=[
                                html.Span("-", className="badge badge-duration", id="badge-duration"),
                                html.Span("-", className="badge badge-culture", id="badge-culture"),
                                html.Span("-", className="badge badge-cycle", id="badge-cycle"),
                                html.Span("-", className="badge badge-dist", id="badge-dist")
                            ])
                        ])
                    ]),
                    html.Div(className="content-tabs", children=[
                        html.Button([html.Span("🏛️ Points d'intérêt culturels")], className="tab-btn active")
                    ])
                ]),
                html.Div(className="tab-content-container", children=[
                    html.Div(className="tab-panel active", id="panel-pois", children=[
                        html.Div(className="pois-scroll-list", id="pois-list")
                    ])
                ])
            ]),
            
            html.Div(className="dash-card card-map", id="card-map", children=[
                html.Div(
                    dcc.Checklist(
                        id='toggle-choropleth',
                        options=[{'label': ' Afficher la fréquentation touristique', 'value': 'show'}],
                        value=[]
                    ),
                    style={'position': 'absolute', 'top': '20px', 'right': '20px', 'zIndex': 1000, 'backgroundColor': 'white', 'padding': '10px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.2)'}
                ),
                dl.Map(id="leaflet-map", center=[46.603354, 1.888334], zoom=6, children=[
                    dl.TileLayer(url='https://tile.openstreetmap.org/{z}/{x}/{y}.png', attribution='&copy; OpenStreetMap'),
                    dl.LayerGroup(id='choropleth-layer'),
                    dl.LayerGroup(id='map-layer-markers'),
                    dl.LayerGroup(id='map-layer-route')
                ], style={'width': '100%', 'height': '100%', 'borderRadius': '12px'})
            ], style={'position': 'relative'})
        ])
    ])
])

@app.callback(
    Output('depart-dropdown', 'options'),
    Input('depart-dropdown', 'search_value')
)
def update_options(search_value):
    if not search_value or len(search_value) < 2:
        return dash.no_update
    places = search_station(search_value)
    return [{'label': p['name'], 'value': p['id'] if 'id' in p else p['name']} for p in places][:6]

@app.callback(
    Output('duration-display', 'children'),
    Input('max-duration-slider', 'value')
)
def update_dur_display(val):
    hours = val // 60
    mins = val % 60
    return f"{hours}h{mins:02d} ({val} min)"

@app.callback(
    Output('search-results-store', 'data'),
    Output('status-label', 'children'),
    Output('destination-select', 'options'),
    Input('submit-btn', 'n_clicks'),
    State('depart-dropdown', 'value'),
    State('depart-dropdown', 'options'),
    State('max-duration-slider', 'value'),
    prevent_initial_call=True
)
def perform_search(n_clicks, depart_val, depart_opts, max_duration):
    if not depart_val: return dash.no_update, "Sélectionnez un départ", []
    
    depart_name = depart_val
    depart_id = depart_val
    if depart_opts:
        for opt in depart_opts:
            if opt['value'] == depart_val:
                depart_name = opt['label']
                break
                
    places_depart = search_station(depart_name)
    if not places_depart: return dash.no_update, "Gare introuvable", []
    
    dep_coords = get_coords(places_depart[0])
    if not depart_id.startswith('stop_area') and 'id' in places_depart[0]:
        depart_id = places_depart[0]['id']
        
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
            
    if not valid_cities: valid_cities = potential_cities
    sample_size = min(len(valid_cities), 10)
    sampled_cities = random.sample(valid_cities, sample_size)
    destinations_dict = {}

    def process_city(city):
        places_arrivee = search_station(city)
        if not places_arrivee: return None
        id_arrivee = places_arrivee[0]['id']
        nom_arrivee = places_arrivee[0]['name']
        arr_coords = get_coords(places_arrivee[0])
        
        url = f"{BASE_URL_SNCF}/journeys"
        params = {'from': depart_id, 'to': id_arrivee, 'min_nb_journeys': 2}
        try:
            resp = requests.get(url, params=params, auth=(API_KEY, ''), timeout=8)
            journeys = resp.json().get('journeys', [])
            valid_journeys = []
            for j in journeys:
                duration_min = j['duration'] // 60
                if duration_min <= max_duration:
                    dep_dt = datetime.strptime(j['departure_date_time'], '%Y%m%dT%H%M%S')
                    co2 = j.get('co2_emission', {}).get('value', 0)
                    valid_journeys.append({"Durée (min)": duration_min, "CO2 (g)": co2, "dep_dt_iso": dep_dt.isoformat()})
                    
            if valid_journeys:
                valid_journeys.sort(key=lambda x: x["dep_dt_iso"])
                min_duration = min(j["Durée (min)"] for j in valid_journeys)
                min_co2 = min(j["CO2 (g)"] for j in valid_journeys)
                dest_lat = arr_coords[0] if arr_coords else None
                dest_lon = arr_coords[1] if arr_coords else None
                if dest_lat is None and city in city_coords.index:
                    dest_lat = float(city_coords.loc[city]['Latitude'])
                    dest_lon = float(city_coords.loc[city]['Longitude'])
                
                dist_km = 0
                if dep_coords and dest_lat and dest_lon:
                    dist_km = round(haversine_distance(dep_coords[0], dep_coords[1], dest_lat, dest_lon), 1)
                
                road_km = round(dist_km * 1.25 if dist_km > 0 else (min_duration / 60.0 * 95), 1)
                train_kg = round(min_co2 / 1000.0, 2) if min_co2 > 0 else round(max(0.2, dist_km * 0.012), 2)
                voiture_kg = round(max(1.2, road_km * 0.190), 2)
                
                pois = get_city_pois(city, default_lat=dest_lat, default_lon=dest_lon, limit=10)
                
                return {
                    "nom_arrivee": nom_arrivee,
                    "id": nom_arrivee,
                    "city": city,
                    "coords": [dest_lat, dest_lon],
                    "min_duration": min_duration,
                    "co2": train_kg,
                    "voiture_co2": voiture_kg,
                    "dist_km": dist_km,
                    "culture_count": int(city_counts[city]),
                    "cycle_count": cycle_stats.get(city, 0),
                    "pois": pois
                }
        except:
            pass
        return None
            
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(process_city, c) for c in sampled_cities]
        for f in as_completed(futures):
            res = f.result()
            if res: destinations_dict[res['nom_arrivee']] = res
            
    if not destinations_dict:
        return {}, "Aucune destination trouvée", []
        
    df = pd.DataFrame(list(destinations_dict.values())).sort_values(by="min_duration")
    results = df.to_dict(orient="records")
    opts = [{'label': f"{r['nom_arrivee']} ({r['min_duration']} min)", 'value': r['id']} for r in results]
    
    return {"depart_coords": dep_coords, "depart_name": depart_name, "destinations": results}, f"{len(results)} villes trouvées", opts

@app.callback(
    Output('eco-saved-pct', 'children'),
    Output('eco-saved-kg', 'children'),
    Output('eco-trees', 'children'),
    Output('eco-train-co2', 'children'),
    Output('co2-chart', 'figure'),
    Output('city-title', 'children'),
    Output('station-title', 'children'),
    Output('badge-duration', 'children'),
    Output('badge-culture', 'children'),
    Output('badge-cycle', 'children'),
    Output('badge-dist', 'children'),
    Output('pois-list', 'children'),
    Output('map-layer-markers', 'children'),
    Output('map-layer-route', 'children'),
    Output('leaflet-map', 'center'),
    Output('leaflet-map', 'zoom'),
    Input('destination-select', 'value'),
    State('search-results-store', 'data'),
    prevent_initial_call=True
)
def update_dashboard(dest_id, data):
    if not data or not dest_id:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
    dest = next((d for d in data['destinations'] if d['id'] == dest_id), None)
    if not dest: return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
    
    saved_kg = round(max(0.1, dest['voiture_co2'] - dest['co2']), 1)
    saved_pct = int(round((1.0 - (dest['co2'] / max(0.1, dest['voiture_co2']))) * 100))
    trees_equiv = round(saved_kg / 25.0, 1)
    
    fig = px.bar(
        x=["Train", "Voiture"], 
        y=[dest['co2'], dest['voiture_co2']],
        color=["Train", "Voiture"],
        color_discrete_map={"Train": "#0088ce", "Voiture": "#ef4444"},
        text=[f"{dest['co2']}kg", f"{dest['voiture_co2']}kg"]
    )
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", yaxis_visible=False, xaxis_title=None)
    fig.update_traces(textposition='outside')
    
    hours = dest['min_duration'] // 60
    mins = dest['min_duration'] % 60
    dur_str = f"{hours}h{mins:02d}"
    
    pois_children = []
    for p in dest.get('pois', []):
        pois_children.append(html.Div(className="poi-item", children=[
            html.Div(className="poi-icon", children="📍"),
            html.Div(className="poi-details", children=[
                html.H4(p['nom'], className="poi-name", style={'margin': 0}),
                html.Span(p['domaine'], className="poi-category", style={'fontSize': '0.8rem', 'color': '#666'})
            ])
        ]))
        
    markers = []
    route = []
    center = [46.6, 1.8]
    zoom = 6
    if data.get('depart_coords'):
        markers.append(dl.Marker(position=data['depart_coords'], children=[dl.Tooltip(data['depart_name'])]))
    if dest.get('coords'):
        markers.append(dl.Marker(position=dest['coords'], children=[dl.Tooltip(dest['nom_arrivee'])]))
        center = dest['coords']
        zoom = 12
    if data.get('depart_coords') and dest.get('coords'):
        route = [dl.Polyline(positions=[data['depart_coords'], dest['coords']], color="#0088ce", weight=3, dashArray="10, 10")]
        
    return (
        f"-{saved_pct}%",
        f"{saved_kg} kg",
        f"{trees_equiv} 🌳",
        f"{dest['co2']} kg",
        fig,
        dest['city'],
        dest['id'],
        f"⏱️ {dur_str}",
        f"🏛️ {dest['culture_count']} lieux",
        f"🚲 {dest['cycle_count']} pistes",
        f"📏 {dest['dist_km']} km",
        pois_children,
        markers,
        route,
        center,
        zoom
    )

if __name__ == '__main__':
    app.run(debug=True, port=5000)

@app.callback(
    Output('choropleth-layer', 'children'),
    Input('toggle-choropleth', 'value')
)
def update_choropleth(toggle_value):
    if not toggle_value or 'show' not in toggle_value:
        return []
        
    try:
        with open('app/assets/departements.geojson', 'r', encoding='utf-8') as f:
            geojson_data = json.load(f)
            
        polygons = []
        
        # Realistic mock data for "Score de Tranquillité"
        red_deps = ['75', '92', '93', '94', '13', '06', '33', '69', '31', '59', '06', '83', '34', '64'] # Paris, Lyon, Marseille, Bordeaux, Côte d'Azur...
        orange_deps = ['77', '78', '91', '95', '35', '44', '67', '38', '37', '45', '76', '14', '17', '74', '73', '84'] # Grandes banlieues, Alpes, côtes...
        
        for feature in geojson_data['features']:
            code = feature['properties'].get('code', '01')
            
            if code in red_deps:
                color = '#dc2626' # Red fort (Haute fréquentation)
            elif code in orange_deps:
                color = '#f59e0b' # Orange (Moyen)
            else:
                color = '#16a34a' # Vert vif (Tranquille, rural)
                
            geom = feature['geometry']
            if geom['type'] == 'Polygon':
                positions = [[[pt[1], pt[0]] for pt in ring] for ring in geom['coordinates']]
                polygons.append(dl.Polygon(positions=positions, color='#111111', weight=1, fillColor=color, fillOpacity=0.9))
            elif geom['type'] == 'MultiPolygon':
                for poly in geom['coordinates']:
                    positions = [[[pt[1], pt[0]] for pt in ring] for ring in poly]
                    polygons.append(dl.Polygon(positions=positions, color='#111111', weight=1, fillColor=color, fillOpacity=0.9))
                    
        return polygons
    except Exception as e:
        print("Erreur chargement GeoJSON: ", e)
        return []

