"""
Filtrage des gares et calcul du score de "potentiel touristique discret".

Le score est une moyenne pondérée de quatre composantes ramenées sur 0-100 :
  - culture        : rang centile de (lieux touristiques + 4 x lieux labellisés) dans le rayon choisi
  - calme          : 100 - rang centile de la fréquentation 2024 de la gare
  - ruralite       : position de la commune dans la grille de densité INSEE (1 = grand centre urbain -> 0, 7 = rural très dispersé -> 100)
  - accessibilite  : 50 pts si accès fauteuil roulant + 50 pts si accès PMR partiel

Les rangs centiles sont calculés sur l'ensemble des 2 798 gares (et non sur la sélection filtrée)
pour qu'une gare garde le même score quel que soit le filtre appliqué.
"""
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data" / "processed"

COMPONENTS = ["culture", "calme", "ruralite", "accessibilite"]
DEFAULT_WEIGHTS = {"culture": 40, "calme": 30, "ruralite": 20, "accessibilite": 10}
REMARKABLE_WEIGHT = 4
DETOUR_FACTOR = 1.2  # distance réelle ≈ 1,2 x distance à vol d'oiseau (route comme rail)
AVG_TRAIN_SPEED_KMH = 80  # vitesse commerciale moyenne estimée (TER avec arrêts)
PEPITE_THRESHOLD = 50  # "pépite" : au moins aussi calme ET aussi riche en culture que la moitié des gares


def pct_rank(s: pd.Series) -> pd.Series:
    return s.rank(pct=True, method="average") * 100


def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * np.arcsin(np.sqrt(a))


@dataclass
class Filters:
    origin: str | None = None
    max_duration: int = 0                # 0 = pas de limite, durée max en heures (ex: 1, 2, 3, 4)
    max_km: int = 0                      # rétro-compatibilité si fourni
    regions: list[str] = field(default_factory=list)
    gcd: list[int] = field(default_factory=lambda: [5, 6, 7])
    pmr_only: bool = False
    radius: int = 10
    min_lieux: int = 0
    weights: dict = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))

    @classmethod
    def from_args(cls, args):
        def ints(name, default):
            raw = args.get(name)
            if raw is None:
                return default
            return [int(x) for x in raw.split(",") if x.strip().isdigit()]

        weights = {}
        for c in COMPONENTS:
            try:
                weights[c] = max(0.0, float(args.get(f"w_{c}", DEFAULT_WEIGHTS[c])))
            except ValueError:
                weights[c] = DEFAULT_WEIGHTS[c]
        regions = [r for r in (args.get("regions") or "").split("|") if r]
        radius = int(args.get("radius", 10))
        return cls(
            origin=args.get("origin") or None,
            max_duration=max(0, int(args.get("max_duration", 0) or 0)),
            max_km=max(0, int(args.get("max_km", 0) or 0)),
            regions=regions,
            gcd=ints("gcd", [5, 6, 7]),
            pmr_only=args.get("pmr_only") in ("1", "true"),
            radius=radius if radius in (5, 10) else 10,
            min_lieux=max(0, int(args.get("min_lieux", 0) or 0)),
            weights=weights,
        )


class StationStore:
    def __init__(self):
        self.df = pd.read_csv(DATA / "gares.csv", dtype={"insee": str})
        self.pois = json.loads((DATA / "gares_pois.json").read_text(encoding="utf-8"))
        self.quality = json.loads((DATA / "quality.json").read_text(encoding="utf-8"))
        df = self.df
        for r in (5, 10):
            df[f"culture_{r}"] = pct_rank(df[f"lieux_{r}km"] + REMARKABLE_WEIGHT * df[f"remarquables_{r}km"])
        df["calme"] = (100 - pct_rank(df["voyageurs"])).fillna(50)
        df["ruralite"] = (df["gcd"] - 1) / 6 * 100
        df["accessibilite"] = 50 * df["acces_fauteuil"].astype(int) + 50 * df["acces_pmr_partiel"].astype(int)
        self.medians = {
            "voyageurs": float(df["voyageurs"].median()),
            "lieux_5km": float(df["lieux_5km"].median()),
            "lieux_10km": float(df["lieux_10km"].median()),
        }
        self.regions = sorted(df["region"].dropna().unique().tolist())
        self.by_id = df.set_index("id_gare")

    def score(self, f: Filters) -> pd.DataFrame:
        """Score de toutes les gares (non filtrées) avec la contribution de chaque composante."""
        df = self.df.copy()
        df["culture"] = df[f"culture_{f.radius}"]
        total_w = sum(f.weights.values()) or 1.0
        for c in COMPONENTS:
            df[f"contrib_{c}"] = df[c] * f.weights[c] / total_w
        df["score"] = sum(df[f"contrib_{c}"] for c in COMPONENTS)
        df["rang_national"] = df["score"].rank(ascending=False, method="min").astype(int)
        df["lieux"] = df[f"lieux_{f.radius}km"]
        df["remarquables"] = df[f"remarquables_{f.radius}km"]

        if f.origin and f.origin in self.by_id.index:
            o = self.by_id.loc[f.origin]
            df["distance_km"] = haversine_km(o["latitude"], o["longitude"], df["latitude"], df["longitude"]).round(1)
            # Durée estimée en minutes : distance réelle (détour x1.2) / vitesse moyenne (80 km/h) * 60
            df["duree_min"] = (df["distance_km"] * DETOUR_FACTOR / AVG_TRAIN_SPEED_KMH * 60).round().astype(int)
        else:
            df["distance_km"] = np.nan
            df["duree_min"] = np.nan
        return df

    def apply_filters(self, df: pd.DataFrame, f: Filters) -> pd.DataFrame:
        mask = df["gcd"].isin(f.gcd) if f.gcd else pd.Series(True, index=df.index)
        if f.regions:
            mask &= df["region"].isin(f.regions)
        if f.pmr_only:
            mask &= df["acces_fauteuil"] | df["acces_pmr_partiel"]
        if f.min_lieux:
            mask &= df["lieux"] >= f.min_lieux
        if f.max_duration and df["duree_min"].notna().any():
            mask &= df["duree_min"] <= f.max_duration * 60
        elif f.max_km and df["distance_km"].notna().any():
            mask &= df["distance_km"] <= f.max_km
        if f.origin:
            mask &= df["id_gare"] != f.origin
        return df[mask].sort_values("score", ascending=False)


def co2_comparison(distance_km: float) -> list[dict]:
    """Émissions (kg CO2e / passager) d'un trajet porte-à-porte approché par distance x facteur de détour.

    Facteurs : ADEME, Base Empreinte via impactco2.fr (g CO2e / passager.km, construction + usage), relevés en octobre 2026.
    """
    factors = [
        ("Train à grande vitesse", 2.3, "train"),
        ("Train régional (TER)", 22.9, "train"),
        ("Voiture électrique", 12.1, "autre"),
        ("Covoiturage (2 personnes)", 55.3, "autre"),
        ("Voiture essence ou diesel", 110.6, "autre"),
        ("Avion", 224.2, "autre"),
    ]
    km = distance_km * DETOUR_FACTOR
    return [{"mode": m, "kg": round(g * km / 1000, 1), "groupe": grp} for m, g, grp in factors]


def clean_record(rec: dict) -> dict:
    """Rend un enregistrement sérialisable en JSON (NaN -> None, types numpy -> natifs)."""
    out = {}
    for k, v in rec.items():
        if isinstance(v, (np.integer,)):
            v = int(v)
        elif isinstance(v, (np.floating, float)):
            v = None if math.isnan(v) else float(v)
        elif isinstance(v, np.bool_):
            v = bool(v)
        out[k] = v
    return out
