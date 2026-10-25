"""
TchooTchoo — Routage ferroviaire sur le réseau réel (GeoJSON SNCF).

Chargé une seule fois au démarrage. Expose une fonction find_rail_path(lat1, lon1, lat2, lon2)
qui retourne une liste de coordonnées [[lon, lat], ...] formant le chemin ferroviaire.

Algorithme :
1. Charger les lignes EXPLOITÉES du GeoJSON réseau ferré.
2. Construire un graphe de connectivité : les extrémités de segments à moins de
   SNAP_KM sont fusionnées en un même nœud.
3. BFS (breadth-first search) entre le nœud le plus proche du départ et celui
   le plus proche de la destination.
4. Retourner les coordonnées concaténées des segments du chemin.
"""
import json
import math
import os
from collections import defaultdict, deque

SNAP_KM = 0.5       # Distance max pour fusionner deux extrémités en un nœud
SNAP_STATION_KM = 3.0  # Distance max pour snapper une gare sur le réseau

_GEOJSON_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'reseau_ferre_lignes.geojson')


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class RailRouter:
    def __init__(self, geojson_path: str = _GEOJSON_PATH):
        raw = json.load(open(geojson_path, encoding='utf-8'))
        self.features = [f for f in raw['features'] if f['properties']['mnemo'] == 'EXPLOITE']
        self._build_graph()

    def _build_graph(self):
        """Construire le graphe de connectivité des segments ferroviaires."""
        # Collecter toutes les extrémités (début + fin de chaque segment)
        endpoints = []  # (lon, lat, feat_idx, is_end_flag)
        for i, f in enumerate(self.features):
            coords = f['geometry']['coordinates']
            endpoints.append((coords[0][0], coords[0][1], i, False))
            endpoints.append((coords[-1][0], coords[-1][1], i, True))

        # Fusion des extrémités proches → noeuds communs
        node_id = [-1] * len(endpoints)
        node_count = 0
        for i in range(len(endpoints)):
            if node_id[i] >= 0:
                continue
            node_id[i] = node_count
            for j in range(i + 1, len(endpoints)):
                if node_id[j] >= 0:
                    continue
                d = _haversine(endpoints[i][1], endpoints[i][0], endpoints[j][1], endpoints[j][0])
                if d < SNAP_KM:
                    node_id[j] = node_count
            node_count += 1

        # Graphe: noeud -> [(noeud_voisin, feat_idx)]
        self.graph: dict[int, list[tuple[int, int]]] = defaultdict(list)
        for ep_idx, (lon, lat, feat_idx, is_end) in enumerate(endpoints):
            nid = node_id[ep_idx]
            other_ep_idx = ep_idx + 1 if not is_end else ep_idx - 1
            other_nid = node_id[other_ep_idx]
            self.graph[nid].append((other_nid, feat_idx))

        # Coordonnées de chaque nœud (centroïde du groupe)
        sums: dict[int, list] = defaultdict(lambda: [0.0, 0.0, 0])
        for ep_idx, (lon, lat, feat_idx, is_end) in enumerate(endpoints):
            nid = node_id[ep_idx]
            sums[nid][0] += lon
            sums[nid][1] += lat
            sums[nid][2] += 1
        self.node_coords: dict[int, tuple[float, float]] = {
            nid: (s[0] / s[2], s[1] / s[2]) for nid, s in sums.items()
        }

    def _snap(self, lat: float, lon: float) -> tuple[int | None, float]:
        """Trouver le nœud réseau le plus proche de (lat, lon)."""
        best_d = float('inf')
        best_nid = None
        for nid, (nlon, nlat) in self.node_coords.items():
            d = _haversine(lat, lon, nlat, nlon)
            if d < best_d:
                best_d = d
                best_nid = nid
        return (best_nid if best_d <= SNAP_STATION_KM else None), best_d

    def _bfs(self, start: int, end: int) -> list[int] | None:
        """BFS retournant la liste des indices de features formant le chemin."""
        if start == end:
            return []
        queue: deque[tuple[int, list[int], set[int]]] = deque([(start, [], {start})])
        while queue:
            node, path, visited = queue.popleft()
            for neighbor, feat_idx in self.graph[node]:
                if feat_idx in path:
                    continue
                new_path = path + [feat_idx]
                if neighbor == end:
                    return new_path
                if neighbor not in visited:
                    queue.append((neighbor, new_path, visited | {neighbor}))
        return None

    def find_rail_path(self, lat1: float, lon1: float, lat2: float, lon2: float) -> list[list[float]] | None:
        """
        Retourne [[lon, lat], ...] du chemin ferroviaire entre les deux points,
        ou None si aucun chemin n'est trouvé.
        """
        start_nid, d1 = self._snap(lat1, lon1)
        end_nid, d2 = self._snap(lat2, lon2)
        if start_nid is None or end_nid is None:
            return None
        feat_indices = self._bfs(start_nid, end_nid)
        if feat_indices is None:
            return None
        coords: list[list[float]] = []
        for fi in feat_indices:
            coords.extend(self.features[fi]['geometry']['coordinates'])
        return coords


# Instance globale (chargée une fois)
_router: RailRouter | None = None


def get_router() -> RailRouter:
    global _router
    if _router is None:
        _router = RailRouter()
    return _router
