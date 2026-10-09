# Carte Choroplèthe des Fréquentations Touristiques

Pour afficher les zones de haute fréquentation sous forme de carte choroplèthe (coloration des territoires selon une valeur), j'utilise les technologies suivantes :

## 1. Dash-Leaflet (`dl.GeoJSON`)
Le composant `dl.GeoJSON` de la librairie **Dash-Leaflet** permet d'afficher des polygones (les frontières des départements) directement sur notre fond de carte existant.

## 2. Fichier GeoJSON (Départements Français)
J'ai téléchargé un fichier `departements.geojson` open source contenant les frontières de tous les départements français. Il est stocké dans le dossier `app/assets/` pour être directement accessible par l'application.

## 3. Dash Extensions (`assign`)
Pour gérer l'échelle de couleurs, j'utilise la fonction `assign` de `dash_extensions.javascript`. Leaflet fonctionnant en JavaScript côté client, `assign` permet de passer une fonction de style (qui choisit la couleur en fonction du score de fréquentation) depuis notre code Python vers le navigateur.

## 4. Données de fréquentation (Tranquillité)
Dans le code Python (`app/backend.py`), nous lisons le fichier GeoJSON et nous attribuons manuellement une couleur à chaque département en fonction de la fréquentation touristique réelle (simulée pour le moment avec des listes prédéfinies) :
- **Rouge foncé (Saturé)** : Les grands pôles et littoraux (Paris, Lyon, Marseille, Bordeaux, Côte d'Azur).
- **Orange (Moyen)** : Les grandes banlieues, les Alpes, certaines côtes.
- **Vert vif (Tranquille)** : Tout le reste du territoire, principalement rural (la "diagonale du vide", le centre de la France), idéal pour des explorations bas-carbone tranquilles.

L'opacité est réglée à 90% (`fillOpacity=0.9`) avec de fines bordures sombres (`weight=1`, `color='#111111'`) pour que la carte soit extrêmement lisible et réponde parfaitement à votre KPI de "Score de tranquillité".
