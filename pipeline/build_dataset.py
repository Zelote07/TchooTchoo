"""
Pipeline de préparation des données — TchooTchoo.

Construit, pour chaque gare voyageurs SNCF, un profil "tourisme culturel discret" :
  - offre culturelle touristique dans un rayon de 5 et 10 km (Base des lieux et équipements culturels, Ministère de la Culture)
  - fréquentation annuelle de la gare 2015-2024 (SNCF Voyageurs)
  - ruralité de la commune (grille communale de densité INSEE à 7 niveaux, reprise dans la base culture)
  - accessibilité PMR / fauteuil roulant (SNCF Gares & Connexions)
  - commune réelle de chaque gare (géocodage inverse, API Adresse — data/gares_communes.csv)

Sorties (data/processed/) :
  - gares.csv        : une ligne par gare, indicateurs bruts (les scores sont calculés à la volée par l'API selon les pondérations choisies)
  - gares_pois.json  : pour chaque gare, les lieux culturels touristiques les plus remarquables à moins de 10 km
  - quality.json     : indicateurs de qualité des jointures (affichés dans l'onglet Méthode du dashboard)

Usage : python pipeline/build_dataset.py
"""
import json
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data"
OUT = ROOT / "data" / "processed"

RADII_KM = (5, 10)
EARTH_RADIUS_KM = 6371.0

# Regroupement des types d'équipements en familles d'intérêt touristique.
# Les équipements sans vocation touristique (papeteries, archives, conservatoires,
# enseignement supérieur) sont volontairement exclus du décompte.
CATEGORIES = {
    "patrimoine": ["Monument", "Lieu archéologique", "Lieu de mémoire", "Parc et jardin", "Espace protégé"],
    "musees": ["Musée", "Centre d'art", "Centre de création artistique", "Centre culturel"],
    "spectacle": ["Théâtre", "Scène", "Opéra", "Cinéma", "Centre de création musicale"],
    "livre": ["Bibliothèque", "Librairie"],
}
TYPE_TO_CAT = {t: cat for cat, types in CATEGORIES.items() for t in types}

# Labels nationaux / internationaux signalant un lieu "remarquable" pour un visiteur.
LABELS_REMARQUABLES = {
    "Patrimoine mondial de l'Unesco",
    "Musée de France",
    "Jardin remarquable",
    "Site patrimonial remarquable",
    "Maison des illustres",
    "Monument national",
    "Itinéraire culturel européen",
}

GCD_LABELS = {
    1: "Grands centres urbains",
    2: "Centres urbains intermédiaires",
    3: "Petites villes",
    4: "Ceintures urbaines",
    5: "Bourgs ruraux",
    6: "Rural à habitat dispersé",
    7: "Rural à habitat très dispersé",
}

FREQ_YEARS = list(range(2015, 2025))


def normalize_name(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def haversine_matrix(lat1, lon1, lat2, lon2):
    """Distances (km) entre chaque point (lat1, lon1) et chaque point (lat2, lon2)."""
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    dlat = lat2[None, :] - lat1[:, None]
    dlon = lon2[None, :] - lon1[:, None]
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1)[:, None] * np.cos(lat2)[None, :] * np.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))


def load_culture() -> pd.DataFrame:
    cols = ["Nom", "libelle_geographique", "code_insee", "Type équipement ou lieu",
            "Label et appellation", "Région", "Domaine", "GCD", "Latitude", "Longitude"]
    df = pd.read_csv(RAW / "base-des-lieux-et-des-equipements-culturels.csv", sep=";",
                     usecols=cols, dtype={"code_insee": str}, low_memory=False)
    df = df.rename(columns={"Type équipement ou lieu": "type", "Label et appellation": "label",
                            "libelle_geographique": "commune", "Région": "region"})
    df = df.dropna(subset=["Latitude", "Longitude"])
    df["gcd"] = pd.to_numeric(df["GCD"].str.extract(r"^(\d)")[0], errors="coerce")
    df["categorie"] = df["type"].map(TYPE_TO_CAT)
    df["remarquable"] = df["label"].isin(LABELS_REMARQUABLES)
    return df


def load_stations(quality: dict) -> pd.DataFrame:
    g = pd.read_csv(RAW / "accessibilite_gares.csv", sep=";", dtype=str)
    # Le code INSEE contenu dans l'identifiant NeTEx n'est pas toujours celui de la commune d'implantation
    # (ex. La Barasse, à Marseille, porte le code des Baux-de-Provence) : on lui préfère le géocodage inverse
    # obtenu une fois pour toutes via https://api-adresse.data.gouv.fr/reverse/csv/
    rev = pd.read_csv(RAW / "gares_communes.csv", dtype=str)[["id_gare", "result_citycode", "result_city"]]
    g = g.merge(rev, on="id_gare", how="left")
    id_code = g["id_gare"].str.split(":").str[1]
    quality["insee_id_mismatch_rate"] = round(float((id_code != g["result_citycode"]).mean()), 4)
    g["insee"] = g["result_citycode"].fillna(id_code)
    g["commune"] = g["result_city"]
    g["latitude"] = g["latitude"].astype(float)
    g["longitude"] = g["longitude"].astype(float)
    g["acces_fauteuil"] = g["acces_fauteuil_roulant"].str.lower().eq("true")
    g["acces_pmr_partiel"] = g["acces_pmr"].eq("partial")
    g["guidage_podotactile"] = g["guidage_podotactile"].str.lower().eq("true")
    g["nb_ascenseurs"] = pd.to_numeric(g["nb_ascenseurs"], errors="coerce").fillna(0).astype(int)
    return g[["id_gare", "nom_gare", "insee", "commune", "latitude", "longitude", "acces_fauteuil",
              "acces_pmr_partiel", "guidage_podotactile", "nb_ascenseurs"]]


def attach_frequentation(g: pd.DataFrame, quality: dict) -> pd.DataFrame:
    f = pd.read_csv(RAW / "frequentation_gares.csv", sep=";", dtype={"code_postal": str})
    f = f.rename(columns={"totalvoyageurs2017": "total_voyageurs_2017"})
    f["k"] = f["nom_gare"].map(normalize_name)
    f["dep"] = f["code_postal"].str[:2]
    year_cols = [f"total_voyageurs_{y}" for y in FREQ_YEARS]
    f = f[["k", "dep", "segmentation_drg"] + year_cols]

    g = g.copy()
    g["k"] = g["nom_gare"].map(normalize_name)
    g["dep"] = g["insee"].str[:2]
    # 1) appariement nom + département (lève les homonymes), 2) repli sur le nom seul s'il est unique
    m1 = g.merge(f.drop_duplicates(["k", "dep"]), on=["k", "dep"], how="left")
    unique_names = f[~f["k"].duplicated(keep=False)].drop(columns="dep")
    missing = m1[year_cols[-1]].isna() & m1[year_cols[0]].isna()
    m2 = g.loc[missing.values].merge(unique_names, on="k", how="left")
    m1.loc[missing.values, ["segmentation_drg"] + year_cols] = m2[["segmentation_drg"] + year_cols].values

    m1["voyageurs"] = m1[year_cols[-1]]
    quality["freq_match_rate"] = round(float(m1["voyageurs"].notna().mean()), 4)
    quality["freq_unmatched"] = m1.loc[m1["voyageurs"].isna(), "nom_gare"].tolist()
    return m1.drop(columns=["k", "dep"])


def compute_culture_profile(g: pd.DataFrame, c: pd.DataFrame, quality: dict):
    tour = c[c["categorie"].notna()].reset_index(drop=True)
    commune_ref = c.dropna(subset=["gcd"]).drop_duplicates("code_insee").set_index("code_insee")

    counts = {f"{cat}_{r}km": np.zeros(len(g), dtype=int) for cat in CATEGORIES for r in RADII_KM}
    counts.update({f"remarquables_{r}km": np.zeros(len(g), dtype=int) for r in RADII_KM})
    vote_gcd = np.full(len(g), np.nan)
    vote_region = np.empty(len(g), dtype=object)
    all_gcd, all_region = c["gcd"].to_numpy(), c["region"].to_numpy()
    top_pois = {}

    cat_codes = tour["categorie"].map({cat: i for i, cat in enumerate(CATEGORIES)}).to_numpy()
    remarquable = tour["remarquable"].to_numpy()
    all_lat, all_lon = c["Latitude"].to_numpy(), c["Longitude"].to_numpy()
    t_lat, t_lon = tour["Latitude"].to_numpy(), tour["Longitude"].to_numpy()

    chunk = 150
    for start in range(0, len(g), chunk):
        sl = slice(start, start + chunk)
        s_lat, s_lon = g["latitude"].to_numpy()[sl], g["longitude"].to_numpy()[sl]

        # Vote majoritaire des lieux voisins (densité à 5 km, région à 10 km) : robuste aux erreurs
        # ponctuelles de géocodage de la base culture, contrairement au seul plus proche voisin.
        d_all = haversine_matrix(s_lat, s_lon, all_lat, all_lon)
        idx_near = d_all.argmin(axis=1)
        for row in range(d_all.shape[0]):
            near5 = all_gcd[d_all[row] <= 5]
            near5 = near5[~np.isnan(near5)]
            vote_gcd[start + row] = np.bincount(near5.astype(int)).argmax() if near5.size else all_gcd[idx_near[row]]
            near10 = all_region[d_all[row] <= 10]
            vote_region[start + row] = (pd.Series(near10).mode().iat[0] if near10.size
                                        else all_region[idx_near[row]])

        d = haversine_matrix(s_lat, s_lon, t_lat, t_lon)
        for r in RADII_KM:
            within = d <= r
            for i, cat in enumerate(CATEGORIES):
                counts[f"{cat}_{r}km"][sl] = (within & (cat_codes == i)[None, :]).sum(axis=1)
            counts[f"remarquables_{r}km"][sl] = (within & remarquable[None, :]).sum(axis=1)

        # Lieux à mettre en avant : remarquables d'abord, puis musées/patrimoine, les plus proches
        within10 = d <= 10
        for row, gi in enumerate(range(start, min(start + chunk, len(g)))):
            idx = np.flatnonzero(within10[row])
            if idx.size == 0:
                continue
            sub = tour.iloc[idx].assign(dist_km=d[row, idx])
            sub["prio"] = np.where(sub["remarquable"], 0, np.where(sub["categorie"] == "musees", 1, 2))
            sub = sub.sort_values(["prio", "dist_km"]).drop_duplicates("Nom").head(8)
            top_pois[g["id_gare"].iat[gi]] = [
                {"nom": r.Nom, "type": r.type, "label": r.label if isinstance(r.label, str) else None,
                 "commune": r.commune, "dist_km": round(float(r.dist_km), 1),
                 "lat": round(float(r.Latitude), 5), "lon": round(float(r.Longitude), 5)}
                for r in sub.itertuples()
            ]

    out = g.copy()
    for k, v in counts.items():
        out[k] = v
    for r in RADII_KM:
        out[f"lieux_{r}km"] = sum(out[f"{cat}_{r}km"] for cat in CATEGORIES)

    # Ruralité / région : référentiel communal si la commune de la gare figure dans la base culture,
    # sinon vote majoritaire des lieux voisins
    known = out["insee"].isin(commune_ref.index)
    quality["gcd_from_commune_rate"] = round(float(known.mean()), 4)
    out["gcd"] = np.where(known, out["insee"].map(commune_ref["gcd"]), vote_gcd).astype(int)
    out["region"] = np.where(known, out["insee"].map(commune_ref["region"]), vote_region)
    out["commune"] = out["commune"].fillna(out["insee"].map(commune_ref["commune"]))
    out["gcd_label"] = out["gcd"].map(GCD_LABELS)
    out["rurale"] = out["gcd"] >= 5
    return out, top_pois


def attach_cycling(g: pd.DataFrame) -> pd.DataFrame:
    # Nombre de segments d'aménagements cyclables par nom de commune (cf. process_geojson.py).
    # Indicateur de contexte uniquement : l'agrégation par nom fusionne les communes homonymes.
    path = RAW / "cycle_stats_by_city.json"
    stats = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    g = g.copy()
    g["segments_cyclables"] = g["commune"].map(stats).fillna(0).astype(int)
    return g


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    quality = {}

    culture = load_culture()
    stations = load_stations(quality)
    quality["n_gares"] = int(len(stations))
    quality["n_lieux_culturels"] = int(len(culture))
    quality["n_lieux_touristiques"] = int(culture["categorie"].notna().sum())
    print(f"{len(stations)} gares, {len(culture)} lieux culturels ({quality['n_lieux_touristiques']} touristiques)")

    stations = attach_frequentation(stations, quality)
    print(f"Fréquentation appariée pour {quality['freq_match_rate']:.1%} des gares")

    stations, top_pois = compute_culture_profile(stations, culture, quality)
    print(f"Ruralité issue de la commune de la gare pour {quality['gcd_from_commune_rate']:.1%} des gares")

    stations = attach_cycling(stations)

    stations.to_csv(OUT / "gares.csv", index=False)
    (OUT / "gares_pois.json").write_text(json.dumps(top_pois, ensure_ascii=False), encoding="utf-8")
    (OUT / "quality.json").write_text(json.dumps(quality, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Écrit : {OUT / 'gares.csv'} ({len(stations)} lignes)")


if __name__ == "__main__":
    main()
