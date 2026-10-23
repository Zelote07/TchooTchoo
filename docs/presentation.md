# Présentation orale — plan et script (≈ 15 min + questions)

Chaque section correspond à une diapositive. Les chiffres viennent de `data/processed/` (réglages par défaut).
Les attendus de l'évaluation sont : traitement des données, réponse à la question métier, démo, conception (stack, layout, règles respectées ou non).
Le détail de chaque graphique et de chaque calcul est dans [documentation.md](documentation.md).

---

> Lien de démo : `http://127.0.0.1:5000/oral` (départ Marseille Saint-Charles préréglé). Pour changer de scénario, modifier `DEMO` dans `app/backend.py`.

## 1. Titre (30 s)
**TchooTchoo — Partez au calme, en train.**
Open Data University, saison 4, défis Culture et Mobilités. Noms du groupe.

## 2. Contexte et question métier (1 min 30)
- Le surtourisme se concentre sur quelques sites (Mont-Saint-Michel, Étretat, Paris…), alors que de nombreux territoires ruraux ont un patrimoine riche mais peu visité.
- Le train est le mode le moins carboné, à condition que la destination ait une gare.
- **Question** : où partir en train pour trouver un endroit calme, à la campagne, avec beaucoup de choses à visiter ?
- **Utilisateur** : le voyageur, quel que soit son âge ou son aisance avec le numérique. D'où trois contraintes : une seule page sans défilement, un vocabulaire courant et un style d'application de voyage familier.
- **Bénéfice collectif** : répartir les flux vers des territoires desservis, sans voiture.

## 3. Données (1 min 30)
Quatre sources ouvertes, croisées à la maille de la gare :

| Source | Apport |
|---|---|
| Base des lieux culturels (Culture, 86 366 lieux) | lieux à visiter, labels, densité INSEE |
| Accessibilité des gares (SNCF G&C, 2 798 gares) | référentiel, coordonnées, PMR |
| Fréquentation des gares 2015-2024 (SNCF) | calme |
| API Adresse | commune réelle de chaque gare |

## 4. Traitement des données (2 min) — montrer l'esprit critique
- **Jointure de la fréquentation** sur le nom normalisé et le département : 99,75 % des gares appariées. Les 7 gares non appariées sont listées dans `quality.json`.
- **Piège découvert** : le code INSEE de l'identifiant de gare est faux pour 3,75 % des gares (La Barasse, à Marseille, portait le code des Baux-de-Provence et ressortait comme « rurale »). Correction par géocodage inverse.
- **Erreur dans la source Culture** : un conservatoire de Trappes est géolocalisé dans l'Oise. Pour la densité de repli, on passe donc du plus proche voisin à un vote majoritaire dans un rayon de 5 km.
- **Calcul spatial** : 2 798 × 77 158 distances de haversine, vectorisées par blocs (≈ 30 s).
- Seules les **familles touristiques** sont retenues : on exclut papeteries, archives, conservatoires et enseignement.

## 5. La note sur 10, une construction assumée (1 min 30)
- Quatre critères sur 100 : culture, calme, campagne, accès. Les poids dépendent de l'**envie** choisie (« Un peu de tout » = 40/30/20/10).
- Calcul déroulé sur Boisleux-au-Mont : 0,4 × 85,4 + 0,3 × 93,8 + 0,2 × 83,3 + 0,1 × 0 = 79,0, soit **7,9/10**.
- Rangs centiles calculés sur **toutes** les gares, pour qu'une note ne change pas quand on filtre.
- **Test de sensibilité** : avec des poids égaux, seules 4 gares du top 15 restent en place, contre 28 sur 50 pour le top 50.
  → La note est une aide pour trouver des idées, pas un palmarès ; d'où les envies et le détail critère par critère.

## 6. Réponse à la question métier (2 min)
- **1 258 gares de campagne**, dont **220 pépites** (calme ≥ 50 **et** culture ≥ 50). Elles sont surtout en Nouvelle-Aquitaine (36), Bourgogne-Franche-Comté (28), Bretagne (26) et Hauts-de-France (25).
- Exemples : Boisleux-au-Mont (beffroi et citadelle d'Arras, Unesco, à moins de 9 km), Les Eyzies (vallée de la Vézère, 18 lieux labellisés, 20 k voyageurs par an), Menars (Val de Loire : sites patrimoniaux remarquables, château de Blois à 9 km).
- **Le point bloquant est l'accessibilité** : 3,3 % des gares rurales sont accessibles en fauteuil, contre 30,5 % des gares urbaines. Sur les 220 pépites, **une seule** l'est (L'Hermitage - Mordelles).
- **Recommandation** : promouvoir les pépites desservies, et cibler la mise en accessibilité sur cette liste.

## 7. Démo (5 min) — script
Ouvrir **`http://127.0.0.1:5000/oral`** : départ Marseille Saint-Charles, 200 km, comparaison Théoule-sur-Mer (A) / Èze (B) déjà préparés.
Plan B si le réseau tombe : sans connexion à l'API SNCF, seule la ligne « Prochain train » est vide ; tout le reste fonctionne.

**Explorer (2 min)**
1. **Arrivée** : tout tient sur un écran. Résumé : « 54 gares de campagne, dont 7 pépites » à moins de 200 km de Marseille.
2. **Liste** : la première idée, Saint-Laurent-d'Aigouze (Camargue), est notée 6,3… mais aucun train n'y va dans les 24 heures. C'est l'occasion de dire honnêtement que la note ne tient pas compte de la desserte.
3. **Fiche Théoule-sur-Mer** (déjà ouverte, repère **A** dans la liste) : onglet **À visiter** (graphique des familles de lieux, lieux labellisés), puis **Pourquoi ici ?** (critères en phrases simples), puis **Y aller** : 128 km, prochain train réel en 2 h 41 avec une correspondance, « 5 fois moins de CO₂ qu'en voiture ».

**Comparer (3 min)**
4. Cliquer **Comparer (2)** en haut. Lire le **verdict** : « Théoule-sur-Mer est plus calme (6,6 contre 2,7) ; Èze a plus de lieux à visiter (250 contre 75). Selon vos envies, les deux se valent. »
5. **Haltères** : la longueur du trait gris montre l'écart ; Calme et Culture s'opposent, Campagne et Accès sont à égalité (« A = B »).
6. **Lieux** (barres groupées) : Èze compte 164 monuments, contre 32 pour Théoule.
7. **Le voyage** : Théoule est plus proche (128 contre 166 km) et plus rapide (2 h 41 contre 3 h 11), et c'est une pépite. Les coches ✓ désignent la meilleure valeur.
8. **CO₂** : 3,5 kg en train régional contre 17 kg en voiture pour Théoule.
9. **Voyageurs par jour** : 88 à Théoule contre 826 à Èze en 2024. Expliquer les échelles séparées (petits multiples, pas de double axe).
10. **Moment clé** : passer **Mes envies** sur « Culture d'abord » : Èze l'emporte (6,7 contre 5,8). Passer sur « Calme absolu » : Théoule l'emporte (6,4 contre 4,7). **Le bon choix dépend du voyageur**, et l'outil le montre au lieu d'imposer un palmarès.
11. **Accessibilité** (si le temps le permet) : bouton ⇄ pour inverser A et B, thème sombre, navigation clavier, « Comment ça marche ? ».

## 8. Conception : stack (1 min)
- Pipeline **Pandas/NumPy** séparé de l'affichage : reproductible, rapide, versionné.
- **Flask + Altair (Vega-Lite) + Leaflet** : Altair, vu en cours, était nouveau pour nous hors notebook. Les graphiques sont générés en Python et s'adaptent à la taille de leur zone.
- Pourquoi pas Streamlit : défilement imposé et mise en page trop contrainte pour une page unique. Pourquoi pas Power BI : outil propriétaire, peu reproductible, peu adapté au grand public.

## 9. Conception : layout et bonnes pratiques (1 min 30)
- **Une page, zéro défilement** : recherche en haut, puis deux vues. Explorer présente trois zones liées (idées → carte → fiche) ; Comparer présente six panneaux A/B. Liste paginée selon la hauteur, fiche en onglets.
- **Style sobre, volontairement non « dashboard IA »** : fond papier, encre noire, filets fins, titres en serif, aucune ombre ni dégradé, aucune pastille colorée. La couleur est réservée aux données.
- **Respectées** : vocabulaire courant, une idée par graphique, valeurs écrites au bout des barres (axes supprimés), couleur réservée à l'essentiel (bleu ardoise = A / donnée, terre cuite = B, gris = contexte), duo A/B validé pour le daltonisme et doublé par les lettres et les formes, une forme de graphique par question (haltères pour un écart, barres groupées pour des quantités, petits multiples pour des évolutions d'échelles différentes), rampe séquentielle à une teinte sur la carte, contrastes AA, cibles tactiles de 44 px, clavier, thème sombre, guide intégré.
- **Retirés volontairement** : le radar (aires trompeuses) et le nuage en échelle logarithmique (illisible pour le grand public), remplacé par un nuage de positions sur 100.
- **Non respectées, et pourquoi** : les onglets masquent une partie de l'information (prix du zéro défilement) ; la carte n'est pas navigable au clavier (la liste compense) ; la note est composite ; les petits multiples ont des échelles différentes (signalé dans la documentation, les valeurs 2024 sont écrites).

## 10. Limites, éthique et suites (1 min)
- La fréquentation d'une gare n'est pas la fréquentation touristique ; les monuments sont sur-représentés ; la fréquence des trains et l'hébergement manquent. Cas concret vu en démo : Saint-Laurent-d'Aigouze, Gallargues et Le Cailar (Gard) sont bien notées, mais l'API SNCF n'y trouve aucun train dans les 24 heures.
- **Risque éthique** : déplacer la saturation vers des lieux fragiles. L'outil sert à répartir les flux et doit être croisé avec les capacités d'accueil.
- **Suites** : fréquence de desserte (GTFS SNCF), hébergements (Atout France), fréquentation touristique réelle (Flux Vision Tourisme), saisonnalité.

---

### Questions probables
- *Pourquoi 10 km ?* C'est la distance d'un trajet à vélo ou en bus local depuis la gare. Elle est fixée pour garder la page simple ; le pipeline calcule aussi 5 km et l'API accepte `radius=5`.
- *Pourquoi ×4 pour les labels ?* Pour qu'un lieu labellisé pèse plus qu'une chapelle classée. Le choix est arbitraire et documenté ; sa sensibilité se voit en changeant d'envie.
- *Pourquoi les rangs centiles plutôt que des valeurs normalisées min-max ?* Les distributions sont très asymétriques (Paris : 3 689 lieux contre une médiane de 55) ; le min-max écraserait toutes les gares rurales vers 0.
- *Pourquoi des envies et pas des curseurs ?* Quatre curseurs en pourcentage demandent de raisonner en pondérations ; quatre profils nommés couvrent les usages en un clic.
