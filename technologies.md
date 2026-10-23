# Stack technique : points forts et défauts

Ce document argumente les technologies retenues pour **TchooTchoo** (voir aussi la section « Choix de conception » du README).

## Préparation des données — Pandas + NumPy (`pipeline/`)
* **Points forts**
  * Pipeline reproductible, exécuté une fois (≈ 30 s) : le dashboard lit des données préparées et ne dépend plus d'appels API aléatoires.
  * Calcul spatial vectorisé (haversine par blocs) : 2 798 gares × 77 158 lieux sans dépendance géospatiale lourde.
* **Défauts**
  * Tout est chargé en mémoire. C'est adapté à ces volumes (≈ 50 Mo), pas à un entrepôt de données.
  * Sans index spatial (BallTree, PostGIS), le calcul passerait mal à l'échelle européenne.

## API — Flask
* **Points forts**
  * Micro-framework minimal : quatre routes (`/api/dashboard`, `/api/station`, `/api/journey`, `/api/export.csv`).
  * Contrôle total du layout HTML/CSS, contrairement à Streamlit.
* **Défauts**
  * Synchrone : un appel lent à l'API SNCF bloque un worker. Le cache en mémoire atténue le problème.
  * Le serveur de développement n'est pas fait pour la production : il faudrait gunicorn ou waitress.

## Visualisation — Altair → Vega-Lite (vega-embed)
* **Points forts**
  * Grammaire des graphiques déclarative, vue en cours. Les specs sont produites en Python, au plus près des données.
  * Graphiques en `width/height: container` : ils remplissent exactement leur zone, condition du « zéro défilement ».
  * Thème clair/sombre centralisé (`charts.theme_config`) et descriptions ARIA intégrées aux specs.
* **Défauts**
  * Specs JSON embarquant leurs données (≈ 170 Ko par fiche) : il faudrait passer par des URL de données en production.
  * Un graphique placé dans un onglet masqué n'a pas de taille : il faut l'afficher au moment où l'onglet s'ouvre.

## Cartographie — Leaflet
* **Points forts**
  * Léger, sans clé d'API, rendu canvas performant pour environ 2 800 points.
  * Fonds gris neutres (Esri Canvas) : la couleur reste réservée aux données.
* **Défauts**
  * Navigation clavier limitée sur les marqueurs ; la liste des idées compense.
  * Pas de rendu vectoriel WebGL (contrairement à MapLibre).

## Données temps réel — API SNCF (Navitia) via Requests
* **Points forts**
  * Temps de trajet, correspondances et CO₂ réels vers la gare choisie, appelés à la demande uniquement.
* **Défauts**
  * Nécessite une clé (fichier `.env`, jamais versionné) ; sans clé, le bloc affiche un message explicite.
  * Les petites haltes sont peu desservies : sans solution immédiate, on relance la recherche pour le lendemain à 7 h.
