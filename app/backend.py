"""
TchooTchoo — API Flask de la page "Partez au calme, en train".

Les indicateurs proviennent du jeu préparé par pipeline/build_dataset.py.
L'API SNCF (Navitia) n'est appelée qu'à la demande, pour le trajet réel vers la gare sélectionnée.
"""
import io
import os
from datetime import datetime, timedelta

import pandas as pd
import requests
from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request

import charts
from rail_router import get_router
from scoring import (COMPONENTS, DEFAULT_WEIGHTS, PEPITE_THRESHOLD, Filters, StationStore, clean_record,
                     co2_comparison)

load_dotenv()
API_KEY = os.getenv("SNCF_API_KEY")
SNCF_JOURNEYS_URL = "https://api.sncf.com/v1/coverage/sncf/journeys"

app = Flask(__name__, static_folder="static", template_folder="templates")
app.json.sort_keys = False
store = StationStore()
router = get_router()   # Chargement unique du réseau ferroviaire au démarrage
journey_cache: dict = {}
rail_cache: dict = {}

LIST_COLUMNS = ["id_gare", "nom_gare", "commune", "region", "score", "lieux", "remarquables", "voyageurs",
                "acces_fauteuil", "acces_pmr_partiel", "distance_km", "calme", "culture", "latitude", "longitude"]
EXPORT_COLUMNS = ["nom_gare", "commune", "region", "gcd_label", "score", "rang_national", "lieux", "remarquables",
                  "voyageurs", "acces_fauteuil", "distance_km"] + COMPONENTS + ["latitude", "longitude"]
DETAIL_COLUMNS = ["id_gare", "nom_gare", "commune", "region", "gcd", "gcd_label", "latitude", "longitude", "voyageurs",
                  "acces_fauteuil", "acces_pmr_partiel", "nb_ascenseurs", "score", "rang_national", "lieux",
                  "remarquables", "distance_km"] + COMPONENTS

# Préréglages de la démonstration (route /oral) : modifier ici pour changer de scénario.
DEMO = {
    "origin": "Marseille Saint-Charles",
    "max_km": 200,
    "preset": "equilibre",
    "compare": ["Théoule-sur-Mer", "Èze"],
}


def theme_arg() -> str:
    return "dark" if request.args.get("theme") == "dark" else "light"


def is_pepite(df: pd.DataFrame) -> pd.Series:
    return (df["calme"] >= PEPITE_THRESHOLD) & (df["culture"] >= PEPITE_THRESHOLD)


@app.route("/")
def index():
    return render_template("index.html", demo=None)


@app.route("/oral")
def oral():
    """Même page, avec départ, distance et comparaison préréglés pour la soutenance."""
    ids = store.df.set_index("nom_gare")["id_gare"]
    demo = dict(DEMO, compare=[ids[n] for n in DEMO["compare"] if n in ids.index])
    return render_template("index.html", demo=demo)


@app.route("/api/meta")
def meta():
    stations = store.df[["id_gare", "nom_gare", "commune", "latitude", "longitude"]].sort_values("nom_gare")
    return jsonify({
        "stations": [clean_record(r) for r in stations.round(5).to_dict(orient="records")],
        "default_weights": DEFAULT_WEIGHTS,
        "quality": {k: v for k, v in store.quality.items() if k != "freq_unmatched"},
        "medians": store.medians,
        "live_journeys": bool(API_KEY),
    })


@app.route("/api/dashboard")
def dashboard():
    """Résumé, liste des meilleures idées et points de la carte pour les filtres choisis."""
    f = Filters.from_args(request.args)
    scored = store.score(f)
    sel = store.apply_filters(scored, f)
    pepites = is_pepite(sel)
    rows = sel[LIST_COLUMNS].assign(pepite=pepites).round({"score": 1, "calme": 0, "culture": 0})
    return jsonify({
        "summary": {
            "n_gares": int(len(sel)),
            "n_pepites": int(pepites.sum()),
            "n_fauteuil": int(sel["acces_fauteuil"].sum()),
        },
        # Quintiles nationaux de la note : classes de couleur de la carte, stables quel que soit le filtre
        "bins": [round(float(q), 1) for q in scored["score"].quantile([0.2, 0.4, 0.6, 0.8])],
        "stations": [clean_record(r) for r in rows.to_dict(orient="records")],
    })


@app.route("/api/station/<path:station_id>")
def station(station_id):
    """Fiche destination : chiffres clés, lieux à visiter et graphiques."""
    if station_id not in store.by_id.index:
        return jsonify({"error": "Gare inconnue"}), 404
    f = Filters.from_args(request.args)
    theme = theme_arg()
    scored = store.score(f)
    sel = store.apply_filters(scored, f)
    row = clean_record(scored.set_index("id_gare").loc[station_id].to_dict())
    row["id_gare"] = station_id
    context = sel if station_id in set(sel["id_gare"]) else pd.concat([sel, scored[scored["id_gare"] == station_id]])

    detail = {
        "station": {k: row.get(k) for k in DETAIL_COLUMNS},
        "pepite": bool(row["calme"] >= PEPITE_THRESHOLD and row["culture"] >= PEPITE_THRESHOLD),
        "pois": store.pois.get(station_id, []),
        "charts": {
            "composition": charts.composition_chart(row, f.radius, theme),
            "position": charts.position_chart(context, station_id, theme),
        },
        "co2": None,
    }
    if row.get("distance_km"):
        rows = co2_comparison(row["distance_km"])
        detail["co2"] = rows
        detail["charts"]["co2"] = charts.co2_chart(rows, theme)
    return jsonify(detail)


@app.route("/api/compare")
def compare():
    """Comparaison de deux destinations depuis le même point de départ."""
    a, b = request.args.get("a"), request.args.get("b")
    if a not in store.by_id.index or b not in store.by_id.index:
        return jsonify({"error": "Choisissez deux gares"}), 400
    f = Filters.from_args(request.args)
    theme = theme_arg()
    scored = store.score(f).set_index("id_gare")
    rows = []
    for sid in (a, b):
        row = clean_record(scored.loc[sid].to_dict())
        row["id_gare"] = sid
        rows.append(row)

    def side(row):
        return {
            "station": {k: row.get(k) for k in DETAIL_COLUMNS} | {
                "voyageurs_par_an": {y: row.get(f"total_voyageurs_{y}") for y in range(2015, 2025)}},
            "pepite": bool(row["calme"] >= PEPITE_THRESHOLD and row["culture"] >= PEPITE_THRESHOLD),
            "pois": store.pois.get(row["id_gare"], [])[:3],
            "co2": co2_comparison(row["distance_km"]) if row.get("distance_km") else None,
        }

    return jsonify({
        "a": side(rows[0]),
        "b": side(rows[1]),
        "charts": {
            "profile": charts.profile_compare(rows, theme),
            "composition": charts.composition_compare(rows, f.radius, theme),
            "trend": charts.trend_compare(rows, theme),
            "co2": charts.co2_compare(rows, theme) if all(r.get("distance_km") for r in rows) else None,
        },
    })


@app.route("/api/journey")
def journey():
    """Trajet réel le plus rapide entre deux gares (API SNCF). Optionnel : nécessite SNCF_API_KEY."""
    if not API_KEY:
        return jsonify({"error": "Clé API SNCF absente : temps de trajet réel indisponible."}), 503
    o, d = request.args.get("from"), request.args.get("to")
    if o not in store.by_id.index or d not in store.by_id.index:
        return jsonify({"error": "Gare inconnue"}), 404
    if (o, d) in journey_cache:
        return jsonify(journey_cache[(o, d)])

    a, b = store.by_id.loc[o], store.by_id.loc[d]
    params = {"from": f"{a.longitude};{a.latitude}", "to": f"{b.longitude};{b.latitude}", "min_nb_journeys": 3}
    # Les petites haltes sont peu desservies : sans solution immédiate, on cherche à partir de demain 7 h
    tomorrow = (datetime.now() + timedelta(days=1)).replace(hour=7, minute=0, second=0)
    journeys = []
    try:
        for when in (None, tomorrow):
            if when:
                params["datetime"] = when.strftime("%Y%m%dT%H%M%S")
            resp = requests.get(SNCF_JOURNEYS_URL, params=params, auth=(API_KEY, ""), timeout=12)
            journeys = resp.json().get("journeys", [])
            if journeys:
                break
    except (requests.RequestException, ValueError):
        return jsonify({"error": "API SNCF injoignable"}), 502
    if not journeys:
        return jsonify({"error": "Aucun trajet trouvé aujourd'hui ni demain matin"}), 404

    best = min(journeys, key=lambda j: j["duration"])
    fmt = lambda s: datetime.strptime(s, "%Y%m%dT%H%M%S").strftime("%H:%M")  # noqa: E731
    legs = []
    for s in best.get("sections", []):
        if s.get("type") != "public_transport":
            continue
        info = s.get("display_informations", {})
        legs.append({
            "mode": info.get("commercial_mode") or info.get("physical_mode") or "Train",
            "numero": info.get("headsign") or info.get("trip_short_name") or "",
            "from": s.get("from", {}).get("name", ""), "to": s.get("to", {}).get("name", ""),
            "dep": fmt(s["departure_date_time"]), "arr": fmt(s["arrival_date_time"]),
        })
    result = {
        "duration_min": best["duration"] // 60,
        "nb_transfers": best.get("nb_transfers", max(0, len(legs) - 1)),
        "co2_kg": round(best.get("co2_emission", {}).get("value", 0) / 1000, 2),
        "date": datetime.strptime(best["departure_date_time"], "%Y%m%dT%H%M%S").strftime("%d/%m"),
        "departure": fmt(best["departure_date_time"]),
        "arrival": fmt(best["arrival_date_time"]),
        "legs": legs,
    }
    journey_cache[(o, d)] = result
    return jsonify(result)



@app.route("/api/rail-path")
def rail_path():
    """Tracé ferroviaire réel entre deux gares (GeoJSON réseau SNCF exploité)."""
    o, d = request.args.get("from"), request.args.get("to")
    if o not in store.by_id.index or d not in store.by_id.index:
        return jsonify({"error": "Gare inconnue"}), 404
    cache_key = (o, d)
    if cache_key in rail_cache:
        return jsonify(rail_cache[cache_key])
    a, b = store.by_id.loc[o], store.by_id.loc[d]
    coords = router.find_rail_path(a.latitude, a.longitude, b.latitude, b.longitude)
    result = {"coordinates": coords or []}
    if coords:
        rail_cache[cache_key] = result
    return jsonify(result)


@app.route("/api/export.csv")
def export_csv():
    f = Filters.from_args(request.args)
    sel = store.apply_filters(store.score(f), f)
    buf = io.StringIO()
    sel[EXPORT_COLUMNS].round(2).to_csv(buf, index=False, sep=";")
    return Response("﻿" + buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=tchootchoo_gares.csv"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
