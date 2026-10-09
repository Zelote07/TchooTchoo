# Stack Technique : Points Forts et Défauts

Ce document analyse les technologies choisies pour le développement de l'application **TchooTchoo**, en détaillant leurs avantages et leurs limites.

## 🎨 Frontend (Interface Utilisateur)

### 1. HTML5, CSS3, JavaScript (Vanilla ES6)
* **Points Forts :**
  * **Légèreté et vitesse** : Aucune dépendance lourde, pas de processus de compilation complexe (pas besoin de Node.js, Webpack, etc.). Le chargement dans le navigateur est immédiat.
  * **Contrôle total** : L'accès direct au DOM permet de gérer très finement les animations et les interactions sans la surcouche d'un framework.
* **Défauts :**
  * **Maintenabilité** : La gestion manuelle du DOM et de l'état (state) peut rendre le fichier `app.js` verbeux et difficile à faire évoluer si l'application devient très complexe.
  * **Manque de composants** : L'absence de frameworks comme React ou Vue.js oblige à dupliquer parfois du code HTML ou à le générer manuellement via JavaScript.

### 2. Leaflet.js (Cartographie Interactive)
* **Points Forts :**
  * **Open Source et Indépendant** : Parfaitement compatible avec des fonds de carte gratuits comme OpenStreetMap. Ne nécessite aucune clé d'API, ce qui garantit la pérennité du projet.
  * **Léger et Mobile-Friendly** : Conçu dès le départ pour la performance et les interactions tactiles sur smartphone.
* **Défauts :**
  * **Limites 3D et vectorielles** : Contrairement à Mapbox GL JS, Leaflet n'est pas nativement conçu pour le rendu WebGL complexe (comme la 3D, les bâtiments extrudés ou l'inclinaison de la caméra).
  * **Performances sur gros volumes** : Afficher des milliers de points (POIs) simultanément peut ralentir le navigateur sans utiliser de plugin de *clustering*.

---

## ⚙️ Backend (Serveur & Traitement des Données)

### 3. Python avec Flask
* **Points Forts :**
  * **Simplicité et rapidité de développement** : Micro-framework minimaliste, idéal pour monter une API REST en quelques lignes de code.
  * **Flexibilité** : Ne force aucune architecture spécifique, s'adaptant parfaitement à la taille de notre projet.
  * **Pont avec la Data** : Étant en Python, il s'intègre nativement et parfaitement avec notre stack de traitement de données (Pandas).
* **Défauts :**
  * **Gestion de la concurrence** : Flask est synchrone par défaut. Il est moins performant que FastAPI ou Node.js pour gérer un très grand nombre de requêtes simultanées.
  * **Structure libre** : Cette liberté peut devenir un piège architectural si le projet grossit considérablement sans règles strictes de séparation du code.

### 4. Pandas (Analyse et traitement de données)
* **Points Forts :**
  * **Puissance d'analyse** : L'outil standard de l'industrie pour nettoyer, croiser et agréger nos datasets (gares, lieux culturels, bilans carbone).
  * **Expressivité** : Des manipulations complexes de données se font en quelques lignes hautement optimisées (en C sous le capot).
* **Défauts :**
  * **Gourmand en RAM** : Pandas charge l'intégralité du jeu de données en mémoire vive. Ce n'est pas un problème pour nos fichiers actuels, mais cela le deviendrait face à des bases de données massives (Big Data).
  * **Latence** : Les calculs "à la volée" via Pandas sur le serveur à chaque requête utilisateur peuvent ajouter un délai par rapport à des requêtes SQL classiques pré-indexées.

### 5. Requests & Altair
* **Points Forts :**
  * **Requests** : Syntaxe extrêmement claire et humaine pour effectuer les appels vers l'API de la SNCF.
  * **Altair** : Syntaxe déclarative élégante pour générer des visualisations (graphiques) basées sur la norme open-source Vega-Lite.
* **Défauts :**
  * **Requests** : Appels HTTP bloquants. Si l'API SNCF met 2 secondes à répondre, le serveur Flask reste bloqué 2 secondes sur cette requête.
  * **Altair** : L'intégration web nécessite souvent de charger des librairies front-end supplémentaires (Vega) pour faire le rendu des graphiques exportés en JSON.
