"""
Agrège le nombre de segments d'aménagements cyclables par nom de commune -> data/cycle_stats_by_city.json.
Source : export national des aménagements cyclables (data/france-20261001.geojson, non versionné car volumineux).
Usage (depuis la racine du dépôt) : python pipeline/process_cycling.py
"""
import json
import pandas as pd
import os
from collections import defaultdict

print("Loading GeoJSON...")
with open('data/france-20261001.geojson', 'r', encoding='utf-8') as f:
    data = json.load(f)

cycle_by_insee = defaultdict(int)

print("Counting cycle paths by INSEE...")
for feature in data.get('features', []):
    props = feature.get('properties', {})
    code_d = props.get('code_com_d')
    code_g = props.get('code_com_g')
    
    # On compte le nombre de segments (on pourrait aussi calculer la longueur avec les coordonnées, mais le nombre de segments donne déjà une bonne idée de l'infrastructure)
    if code_d:
        cycle_by_insee[code_d] += 1
    if code_g and code_g != code_d:
        cycle_by_insee[code_g] += 1

print("Loading CSV...")
df_culture = pd.read_csv('data/base-des-lieux-et-des-equipements-culturels.csv', sep=';', low_memory=False)

# On veut associer le nb d'aménagements cyclables par nom de ville (car on utilise libelle_geographique dans l'application)
insee_to_city = df_culture[['code_insee', 'libelle_geographique']].dropna().drop_duplicates()

cycle_by_city = defaultdict(int)
for idx, row in insee_to_city.iterrows():
    insee = str(row['code_insee'])
    city = str(row['libelle_geographique'])
    
    cycle_by_city[city] += cycle_by_insee.get(insee, 0)

with open('data/cycle_stats_by_city.json', 'w', encoding='utf-8') as f:
    json.dump(cycle_by_city, f, ensure_ascii=False)

print("Done! File data/cycle_stats_by_city.json created.")
