# Documentation — graphiques et calculs

Ce document explique **chaque élément de la page** TchooTchoo et **chaque calcul** qui se cache derrière.
Pour chaque graphique, il décrit ce qu'il montre, comment le lire, d'où viennent les données, ce qui est calculé, pourquoi cette forme a été choisie et ses limites.

L'exemple qui sert de fil rouge est la gare de **Boisleux-au-Mont** (Pas-de-Calais), première idée proposée avec les réglages par défaut. Pour le bilan carbone, on part de **Lyon Part Dieu**.

---

## Sommaire

1. [Vue d'ensemble de la page](#1-vue-densemble-de-la-page)
2. [La recherche](#2-la-recherche)
3. [La liste « Nos idées de destinations »](#3-la-liste-nos-idées-de-destinations)
4. [La carte](#4-la-carte)
5. [La fiche destination](#5-la-fiche-destination)
   - [Onglet « À visiter »](#51-onglet-à-visiter)
   - [Onglet « Pourquoi ici ? »](#52-onglet-pourquoi-ici-)
   - [Onglet « Situer »](#53-onglet-situer)
   - [Onglet « Y aller »](#54-onglet-y-aller)
6. [La vue « Comparer »](#6-la-vue-comparer)
7. [Les calculs en détail](#7-les-calculs-en-détail)
8. [Données sources et préparation](#8-données-sources-et-préparation)
9. [Limites à connaître](#9-limites-à-connaître)
10. [Choix de conception](#10-choix-de-conception)
11. [Mode démonstration (/oral)](#11-mode-démonstration-oral)

---

## 1. Vue d'ensemble de la page

**Question à laquelle répond la page** : *« Où partir en train pour trouver un endroit calme, à la campagne, avec beaucoup de choses à visiter ? »*

**Public** : tout voyageur, quel que soit son âge ou son aisance avec le numérique.

La page tient sur **un seul écran, sans défilement**. Deux vues partagent la même recherche : **Explorer**, pour trouver des idées, et **Comparer**, pour mettre deux destinations côte à côte depuis le même départ.

**Vue Explorer** (se lit de gauche à droite) :

```
┌───────────────────────────────────────────────────────────────────────────┐
│  En-tête : nom · [Explorer | Comparer] · « Comment ça marche ? » · thème  │
│  Recherche : Je pars de · Jusqu'à · Mes envies · options                  │
├──────────────────┬──────────────────────────────┬─────────────────────────┤
│ 1. Nos idées     │ 2. Carte                     │ 3. Fiche destination    │
│ (liste classée)  │ (où sont les idées)          │ À visiter · Pourquoi ici│
│                  │                              │ Situer · Y aller        │
└──────────────────┴──────────────────────────────┴─────────────────────────┘
```

Les trois zones sont **liées** : choisir une gare dans la liste ou sur la carte met à jour les deux autres zones.

**Vue Comparer** :

```
┌───────────────────────────────────────────────────────────────────────────┐
│  Depuis <départ>   [A ▾ destination]  ⇄  [B ▾ destination]   Verdict      │
├────────────────────────┬────────────────────────┬─────────────────────────┤
│ Où sont-elles ?        │ Les notes, critère     │ Lieux à visiter         │
│ (carte)                │ par critère (haltères) │ (barres groupées)       │
├────────────────────────┼────────────────────────┼─────────────────────────┤
│ Le voyage (tableau)    │ CO₂ d'un aller simple  │ Voyageurs par jour      │
│                        │ (barres groupées)      │ (petits multiples)      │
└────────────────────────┴────────────────────────┴─────────────────────────┘
```

Dans toute la vue, la destination **A est en bleu ardoise** (ronds) et la **B en terre cuite** (carrés), toujours accompagnées des lettres A et B.

---

## 2. La recherche

| Contrôle | Effet | Valeur par défaut |
|---|---|---|
| **Je pars de** | Gare de départ (liste des 2 798 gares). Active la distance, le prochain train et le bilan carbone. | vide (toute la France) |
| **Jusqu'à** | Distance maximale **à vol d'oiseau** depuis la gare de départ. Le champ est grisé tant qu'aucune gare de départ n'est choisie. | 300 km |
| **Mes envies** | Change l'importance des quatre critères de la note (voir [§ 7.6](#76-la-note-sur-10)). | Un peu de tout |
| **Gare accessible PMR** | Ne garde que les gares accessibles en fauteuil roulant ou avec un accès partiel pour les personnes à mobilité réduite. | non |
| **Inclure les petites villes** | Ajoute les petites villes et les périphéries de villes aux communes rurales. | non |

**Les quatre « envies »** correspondent à ces pondérations (total de 100) :

| Envie | Culture | Calme | Campagne | Accès PMR |
|---|---|---|---|---|
| Un peu de tout | 40 | 30 | 20 | 10 |
| Culture d'abord | 60 | 20 | 10 | 10 |
| Calme absolu | 20 | 60 | 15 | 5 |
| Facile d'accès | 30 | 20 | 10 | 40 |

> Pourquoi des envies plutôt que quatre curseurs ? Des curseurs en pourcentage obligent l'utilisateur à raisonner en pondérations, ce qui ne parle pas au grand public. Quatre profils nommés couvrent les usages principaux en un clic.

**Quelles communes sont « à la campagne » ?** On s'appuie sur la grille de densité de l'INSEE, qui classe chaque commune en 7 niveaux :

| Niveau INSEE | Libellé affiché | Retenu par défaut | Avec « petites villes » |
|---|---|---|---|
| 1 | grande ville | non | non |
| 2 | ville moyenne | non | non |
| 3 | petite ville | non | **oui** |
| 4 | périphérie de ville | non | **oui** |
| 5 | bourg rural | **oui** | oui |
| 6 | campagne | **oui** | oui |
| 7 | campagne très peu peuplée | **oui** | oui |

---

## 3. La liste Nos idées de destinations

**Ce qu'elle montre** : les gares qui correspondent à la recherche, de la meilleure note à la moins bonne.

**Comment la lire** :
- le **numéro** est le rang dans la sélection ;
- le **nom** est celui de la gare, suivi de sa région (ou de la distance si une gare de départ est choisie) ;
- l'étiquette **« Pépite »** signale une gare à la fois plus calme et plus riche en culture que la moitié des gares françaises ([§ 7.7](#77-pépite)) ;
- l'étiquette **« Accessible »** signale une gare accessible en fauteuil roulant ;
- à droite, la **note sur 10** ([§ 7.6](#76-la-note-sur-10)) ;
- un carré **A** ou **B** signale une gare placée dans la comparaison.

**Résumé en haut de la liste** : « *1 258 gares de campagne, dont 220 pépites* ». C'est le nombre de gares retenues par la recherche, et parmi elles le nombre de pépites.

**Pas de défilement** : la liste affiche autant de lignes que la hauteur de l'écran le permet (5 sur un portable, 9 sur un grand écran). Les flèches ‹ › font passer aux idées suivantes.

**Accessibilité** : chaque ligne est un bouton utilisable au clavier (Tab puis Entrée) et annoncé par les lecteurs d'écran, par exemple « Boisleux-au-Mont, note 7,9 sur 10, pépite ». La liste remplace la carte pour les personnes qui ne peuvent pas s'en servir.

---

## 4. La carte

**Ce qu'elle montre** : où se trouvent les idées de destinations.

**Comment la lire** :
- chaque **point bleu** est une gare proposée ; **plus le bleu est foncé, meilleure est la note** (en thème sombre, plus le bleu est clair, meilleure est la note) ;
- les **petits points gris** sont les autres gares de France, qui ne correspondent pas à la recherche ; ils donnent le contexte du réseau ;
- le **losange foncé** est votre gare de départ ;
- la gare **sélectionnée** est entourée et son nom s'affiche dans une étiquette.

**Calcul des couleurs** : les notes de **toutes** les gares françaises sont réparties en **5 groupes de même taille** (quintiles). Chaque groupe reçoit une nuance de bleu :

| Nuance | Libellé de la légende | Note (sur 100, envie « Un peu de tout ») | Part des gares françaises |
|---|---|---|---|
| la plus claire | Faible | ≤ 36,4 | 20 % |
| 2 | Moyenne | 36,4 – 43,0 | 20 % |
| 3 | Bonne | 43,0 – 48,5 | 20 % |
| 4 | Très bonne | 48,5 – 55,0 | 20 % |
| la plus foncée | Excellente | > 55,0 | 20 % |

Les seuils sont calculés sur toute la France et non sur la sélection : une gare garde la même couleur quand on change la distance ou les options. Ils changent seulement avec l'envie choisie.

**Choix de conception** :
- un **fond de carte gris** (Esri Canvas), pour que la couleur soit réservée aux données ;
- une **seule teinte, du clair au foncé**, pour une grandeur ordonnée : c'est la règle des palettes séquentielles, lisible par les daltoniens et à l'impression ;
- **5 classes** seulement, car l'œil distingue mal plus de 5 à 7 nuances.

---

## 5. La fiche destination

**En-tête** : nom de la gare, commune et région, étiquettes (Pépite, Accessible en fauteuil) et **note sur 10**.
Le bouton **« Ajouter à la comparaison »** place la gare en A (si A est libre) ou en B, puis propose d'ouvrir la vue Comparer.

### 5.1 Onglet À visiter

#### Graphique X lieux à visiter à moins de 10 km

| | |
|---|---|
| **Forme** | Barres horizontales, une couleur, valeur écrite au bout de chaque barre |
| **Ce qu'il montre** | Le nombre de lieux culturels à moins de 10 km de la gare, réparti en 4 familles |
| **Comment le lire** | Plus la barre est longue, plus il y a de lieux de cette famille. Le chiffre donne le nombre exact. |
| **Données** | Base des lieux et équipements culturels (Ministère de la Culture) |

**Calcul** : on compte les lieux dont la distance à la gare ([§ 7.1](#71-distance-entre-deux-points)) est inférieure ou égale à 10 km. Les types de lieux sont regroupés en familles :

| Famille affichée | Types de lieux de la base |
|---|---|
| Monuments & patrimoine | Monument, Lieu archéologique, Lieu de mémoire, Parc et jardin, Espace protégé |
| Musées & expositions | Musée, Centre d'art, Centre de création artistique, Centre culturel |
| Spectacles & cinéma | Théâtre, Scène, Opéra, Cinéma, Centre de création musicale |
| Bibliothèques & librairies | Bibliothèque, Librairie |
| *(non comptés)* | Papeteries et maisons de la presse, services d'archives, conservatoires, établissements d'enseignement supérieur : ce ne sont pas des lieux de visite |

*Exemple, Boisleux-au-Mont* : 239 monuments, 1 musée, 2 spectacles et 23 bibliothèques ou librairies, soit **265 lieux**.

**Pourquoi des barres horizontales ?** Les libellés sont longs et restent lisibles sans rotation, et les longueurs se comparent facilement. L'axe est supprimé parce que la valeur est écrite au bout de chaque barre (meilleur rapport encre / donnée).

#### Liste À ne pas manquer

Elle présente jusqu'à 8 lieux à moins de 10 km, triés ainsi :
1. d'abord les **lieux labellisés** (Patrimoine mondial de l'Unesco, Musée de France, Jardin remarquable, Site patrimonial remarquable, Maison des illustres, Monument national, Itinéraire culturel européen) ;
2. puis les **musées** ;
3. puis les autres lieux ;
4. à rang égal, **le plus proche d'abord**.

La distance est celle à vol d'oiseau depuis la gare. Seuls les lieux qui tiennent entièrement dans l'espace disponible sont affichés, pour ne jamais faire défiler la page.

### 5.2 Onglet Pourquoi ici ?

**Forme** : quatre jauges horizontales, une par critère, chacune accompagnée d'une note sur 10 et d'une phrase d'explication.

| Critère | Phrase affichée (exemple de Boisleux-au-Mont) | Note | Calcul |
|---|---|---|---|
| Culture | 265 lieux à moins de 10 km, dont 4 labellisés | 8,5/10 | [§ 7.2](#72-critère-culture) |
| Calme | 2 102 voyageurs par an en gare, 38 fois moins qu'une gare typique | 9,4/10 | [§ 7.3](#73-critère-calme) |
| Campagne | Commune de type « campagne » selon l'INSEE | 8,3/10 | [§ 7.4](#74-critère-campagne) |
| Accès | Gare sans équipement pour les fauteuils roulants | 0,0/10 | [§ 7.5](#75-critère-accès) |

**« X fois moins qu'une gare typique »** : la gare typique est la **gare médiane** de France (la moitié des gares ont moins de voyageurs, l'autre moitié plus), soit **80 316 voyageurs en 2024**. Pour Boisleux, 80 316 ÷ 2 102 ≈ **38**. Si le rapport est inférieur à 2, la phrase devient « un peu moins qu'une gare typique » ; si la gare a plus de voyageurs que la médiane, elle devient « plus qu'une gare typique ».

**Pourquoi des jauges et pas un radar ?** Un radar déforme la perception (l'aire grandit comme le carré des valeurs, et l'ordre des axes change la forme). Des barres alignées sur la même échelle se comparent directement.

### 5.3 Onglet Situer

| | |
|---|---|
| **Forme** | Nuage de points, deux axes de 0 à 100 |
| **Ce qu'il montre** | Où se situe la gare choisie parmi toutes les idées de la recherche |
| **Axe horizontal** | « Plus calme → » : critère Calme (sur 100) |
| **Axe vertical** | « Plus de culture → » : critère Culture (sur 100) |
| **Points gris** | Les autres gares de la sélection |
| **Gros point bleu** | La gare choisie, avec son nom |
| **Zone bleutée en haut à droite** | Les **pépites** : calme ≥ 50 **et** culture ≥ 50 |

**Comment le lire** : plus le point bleu est en haut à droite, plus la destination combine calme et culture. Les lignes au milieu marquent la valeur 50, c'est-à-dire la gare médiane de France pour chaque critère.

**Pourquoi ce graphique ?** Il rend visible la notion de pépite, que la note seule résume en un chiffre. Les axes sont linéaires et exprimés en positions sur 100, plus compréhensibles pour le grand public que des nombres bruts de voyageurs, qui demanderaient une échelle logarithmique.

### 5.4 Onglet Y aller

Sans gare de départ, l'onglet invite à en choisir une. Avec une gare de départ, il affiche :

**1. La distance** : distance à vol d'oiseau entre les deux gares ([§ 7.1](#71-distance-entre-deux-points)). *Exemple : Lyon Part Dieu → Boisleux-au-Mont = 519 km.*

**2. Le prochain train** (si la clé API SNCF est configurée) : durée, nombre de correspondances, date et heures de départ et d'arrivée du trajet le plus rapide parmi les prochains départs. Ces données viennent en temps réel de l'API SNCF (Navitia). Si aucun trajet n'existe dans les heures qui viennent, ce qui arrive souvent pour les petites haltes ou la nuit, la recherche est relancée pour le lendemain à 7 h.

**3. Le graphique « Empreinte carbone d'un aller simple »**

| | |
|---|---|
| **Forme** | Barres horizontales triées de la plus faible à la plus forte ; trains en **bleu**, autres modes en **gris** |
| **Ce qu'il montre** | Les kg de CO₂ émis par une personne pour le même trajet, selon le moyen de transport |
| **Comment le lire** | Plus la barre est courte, moins le trajet pollue. |

Calcul : [§ 7.8](#78-empreinte-carbone). *Exemple Lyon → Boisleux : train à grande vitesse 1,4 kg · voiture électrique 7,5 kg · TER 14,3 kg · covoiturage à 2 34,4 kg · voiture essence ou diesel 68,8 kg · avion 139,5 kg.*

**Phrase sous le graphique** : « *En train régional, vous émettez 5 fois moins de CO₂ qu'en voiture.* » Le rapport vaut voiture essence ou diesel ÷ TER = 68,8 ÷ 14,3 ≈ 4,8, arrondi à 5. On compare au **TER**, l'hypothèse la plus prudente, car les petites gares sont desservies par des trains régionaux.

---

## 6. La vue Comparer

**Question** : *« Depuis ma gare, laquelle de ces deux destinations me convient le mieux ? »*

**Choisir les deux destinations** : depuis la fiche (bouton « Ajouter à la comparaison »), ou directement avec les deux menus A et B en haut de la vue. Ces menus listent les idées de la recherche en cours, triées par note. Le bouton ⇄ inverse A et B. Si on ouvre la vue sans avoir rien choisi, les deux meilleures idées sont proposées.

La recherche (départ, distance, envies) reste active : changer d'envie recalcule les notes de A et B.

### 6.1 Verdict

Une ou deux phrases en haut à droite résument la comparaison. Elles sont construites ainsi :

| Phrase | Condition d'affichage |
|---|---|
| « *X est plus calme (6,6 contre 2,7)* » | l'écart sur le critère Calme atteint au moins 1 point sur 10 |
| « *Y a plus de lieux à visiter (250 contre 75)* » | les deux gares n'ont pas le même nombre de lieux à moins de 10 km |
| « *Selon vos envies, X l'emporte : 6,8 contre 6,1* » | l'écart de note est d'au moins 0,1 sur 10 |
| « *Selon vos envies, les deux se valent* » | l'écart de note est inférieur à 0,1 sur 10 |

Les noms sont écrits dans la couleur de leur destination (A bleu, B terre cuite).

### 6.2 Où sont-elles ? — carte

| | |
|---|---|
| **Ce qu'elle montre** | Le départ (losange noir) et les deux destinations, reliées au départ par un trait pointillé |
| **Comment la lire** | Étiquette bleue « A · nom » et étiquette terre cuite « B · nom ». Le pointillé est une ligne droite, pas le tracé de la voie. |
| **Choix** | Pointillé, pour ne pas laisser croire à un itinéraire réel ; étiquettes A à gauche et B à droite, pour qu'elles ne se chevauchent pas. |

### 6.3 Les notes, critère par critère — graphique en haltères

| | |
|---|---|
| **Forme** | Une ligne par critère, de 0 à 10 ; un rond bleu pour A, un carré terre cuite pour B, reliés par un trait gris |
| **Lignes** | Note globale, Culture, Calme, Campagne, Accès |
| **Comment le lire** | Plus le point est à droite, meilleure est la note. **La longueur du trait gris montre l'écart** entre les deux destinations. La valeur la plus haute est écrite à droite de son point, la plus basse à gauche. |
| **Égalité** | Les deux points se superposent ; l'étiquette l'indique : « 8,3 (A = B) ». |
| **Calculs** | Ce sont les critères de la fiche ([§ 7.2 à 7.6](#72-critère-culture)), divisés par 10. |

**Pourquoi des haltères ?** Pour comparer deux valeurs sur plusieurs critères, c'est la forme qui met l'écart en avant avec le moins d'encre : un trait et deux points par ligne, au lieu de huit barres.

### 6.4 Lieux à visiter à moins de 10 km — barres groupées

| | |
|---|---|
| **Forme** | Pour chaque famille de lieux, une barre bleue (A) au-dessus d'une barre terre cuite (B), valeur écrite au bout |
| **Données et calcul** | Identiques au graphique « À visiter » de la fiche ([§ 5.1](#51-onglet-à-visiter)) |
| **Exemple** | Monuments & patrimoine : Théoule-sur-Mer 32, Èze 164 |

### 6.5 Le voyage — tableau

| Ligne | Contenu | Meilleure valeur (✓) |
|---|---|---|
| Distance | Distance à vol d'oiseau depuis le départ ([§ 7.1](#71-distance-entre-deux-points)) | la plus courte |
| Prochain train | Durée du trajet le plus rapide et nombre de correspondances (API SNCF, temps réel). La date et l'heure de départ apparaissent au survol. | le plus rapide |
| Accès fauteuil | Oui / Non | « Oui » si une seule gare est accessible |
| Pépite | Oui / Non ([§ 7.7](#77-pépite)) | « Oui » si une seule gare est une pépite |

La coche ✓ n'apparaît que si les deux valeurs diffèrent. « aucun train proche » signifie que l'API SNCF ne trouve aucun trajet aujourd'hui ni demain matin.

**Pourquoi un tableau ?** Il y a quatre informations de natures différentes (km, durée, oui/non) : un tableau se lit plus vite qu'un graphique pour si peu de valeurs.

### 6.6 CO₂ d'un aller simple — barres groupées

| | |
|---|---|
| **Forme** | Trois modes (train régional, voiture, avion), avec pour chacun une barre A et une barre B, valeur en kg écrite au bout |
| **Calcul** | [§ 7.8](#78-empreinte-carbone), avec la distance propre à chaque destination |
| **Exemple depuis Marseille** | Train régional : Théoule 3,5 kg, Èze 4,6 kg · Voiture : 17,0 et 22,0 kg · Avion : 34,4 et 44,7 kg |
| **Choix** | Trois modes seulement, pour garder un graphique lisible : le train régional (le cas le plus fréquent vers une petite gare), la voiture (l'alternative habituelle) et l'avion (le cas extrême). Le détail des six modes reste dans l'onglet « Y aller » de la fiche. |

### 6.7 Voyageurs par jour en gare, 2015-2024 — petits multiples

| | |
|---|---|
| **Forme** | Deux petites courbes côte à côte : A à gauche (bleu), B à droite (terre cuite) |
| **Calcul** | `voyageurs par jour = voyageurs de l'année ÷ 365` (source : fréquentation SNCF) |
| **Comment le lire** | La forme de la courbe montre si la gare devient plus ou moins fréquentée ; le chiffre en gras est la valeur de 2024. Le creux de 2020 correspond au Covid. |
| **Exemple** | Théoule-sur-Mer : 88 voyageurs par jour en 2024 ; Èze : 826. |
| **Attention** | **Chaque vignette a sa propre échelle verticale.** Comparez les formes des courbes, et pour les niveaux, lisez les chiffres. |

**Pourquoi des petits multiples plutôt qu'un seul graphique ?** Les deux gares peuvent différer d'un facteur 10 à 100 : sur un même axe, la plus petite deviendrait une ligne plate. Un graphique à deux axes verticaux superposés est une erreur classique, car il fait croire à des croisements qui n'existent pas. Deux vignettes séparées évitent ces deux pièges.

---

## 7. Les calculs en détail

### 7.1 Distance entre deux points

On utilise la **formule de haversine** : c'est la distance « à vol d'oiseau » sur la sphère terrestre, avec un rayon de 6 371 km.

```
a = sin²(Δlat / 2) + cos(lat₁) · cos(lat₂) · sin²(Δlon / 2)
d = 2 · 6371 · arcsin(√a)        (latitudes et longitudes en radians)
```

Elle sert à quatre choses : compter les lieux autour d'une gare, mesurer la distance des lieux « à ne pas manquer », appliquer le filtre « Jusqu'à » et calculer le bilan carbone.

### 7.2 Critère Culture

1. On calcule un **indice** : `lieux à moins de 10 km + 4 × lieux labellisés à moins de 10 km`.
   Un lieu labellisé (Unesco, Musée de France…) compte donc 5 fois (1 + 4), pour qu'un grand site pèse plus qu'une chapelle classée.
2. On transforme cet indice en **rang centile** parmi les 2 798 gares de France : la part des gares qui ont un indice inférieur ou égal, ramenée sur 100.

*Exemple* : Boisleux a un indice de 265 + 4 × 4 = **281**, ce qui la place devant environ 85 % des gares, soit un critère Culture de **85,4/100 (8,5/10)**.

> Pourquoi un rang centile et pas une simple mise à l'échelle entre le minimum et le maximum ? Les valeurs sont très inégales (Paris compte 3 689 lieux, la gare médiane 55). Une mise à l'échelle min-max écraserait toutes les gares rurales près de 0. Le rang centile répartit les gares régulièrement entre 0 et 100.

### 7.3 Critère Calme

`Calme = 100 − rang centile du nombre de voyageurs de la gare en 2024`

Moins une gare a de voyageurs, plus son critère Calme est élevé. Pour les 7 gares dont la fréquentation est inconnue, la valeur est fixée à 50 (neutre).

*Exemple* : Boisleux compte 2 102 voyageurs en 2024 ; seules 172 gares sur 2 791 en ont moins, soit un critère Calme de **93,8/100 (9,4/10)**.

### 7.4 Critère Campagne

`Campagne = (niveau de densité INSEE − 1) ÷ 6 × 100`

| Niveau INSEE | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|
| Critère (sur 100) | 0 | 16,7 | 33,3 | 50 | 66,7 | 83,3 | 100 |

*Exemple* : Boisleux est en niveau 6 (« campagne »), soit **83,3/100 (8,3/10)**.

### 7.5 Critère Accès

`Accès = 50 si la gare est accessible en fauteuil roulant + 50 si elle a un accès partiel pour les personnes à mobilité réduite`

Les valeurs possibles sont donc 0, 50 ou 100. Source : référentiel d'accessibilité SNCF Gares & Connexions. *Exemple* : Boisleux n'a aucun des deux, soit **0/100**.

### 7.6 La note sur 10

La note est la **moyenne pondérée** des quatre critères, avec les poids de l'envie choisie, puis divisée par 10 :

```
note = (Pculture × Culture + Pcalme × Calme + Pcampagne × Campagne + Paccès × Accès) ÷ (somme des poids) ÷ 10
```

*Exemple, Boisleux-au-Mont avec l'envie « Un peu de tout » (40 / 30 / 20 / 10)* :

| Critère | Valeur /100 | Poids | Points apportés |
|---|---|---|---|
| Culture | 85,4 | 40 % | 34,2 |
| Calme | 93,8 | 30 % | 28,1 |
| Campagne | 83,3 | 20 % | 16,7 |
| Accès | 0 | 10 % | 0 |
| **Total** | | | **79,0 / 100, soit 7,9 / 10** |

Les critères sont calculés sur **toutes** les gares de France. La note d'une gare ne dépend donc ni de la distance choisie ni des options : elle change seulement avec l'envie.

**Sensibilité** : le classement fin dépend des poids. Entre « Un peu de tout » et des poids égaux (25/25/25/25), seules 4 des 15 premières gares restent en place, et 28 des 50 premières. C'est pourquoi la note est présentée comme une **aide pour trouver des idées**, et non comme un palmarès.

### 7.7 Pépite

Une gare est une pépite si **Calme ≥ 50 et Culture ≥ 50**. Autrement dit, elle est au moins aussi calme et au moins aussi riche en culture que la gare médiane de France. C'est la zone en haut à droite du graphique « Situer ».

*Avec les réglages par défaut* : 220 pépites parmi les 1 258 gares de campagne.

### 7.8 Empreinte carbone

```
distance du trajet  = distance à vol d'oiseau × 1,2     (détour moyen des routes et des voies ferrées)
CO₂ (kg)            = distance du trajet × facteur du mode ÷ 1000
```

| Mode | Facteur (g CO₂e par voyageur et par km) |
|---|---|
| Train à grande vitesse | 2,3 |
| Voiture électrique | 12,1 |
| Train régional (TER) | 22,9 |
| Covoiturage (2 personnes) | 55,3 |
| Voiture essence ou diesel | 110,6 |
| Avion | 224,2 |

Source : ADEME, Base Empreinte, via l'API [impactco2.fr](https://impactco2.fr), relevé en octobre 2026. Les facteurs incluent la fabrication des véhicules et des infrastructures en plus de l'usage.

*Exemple Lyon → Boisleux* : 518,6 km × 1,2 = 622 km. En TER : 622 × 22,9 ÷ 1000 = **14,3 kg**. En voiture essence ou diesel : 622 × 110,6 ÷ 1000 = **68,8 kg**.

---

## 8. Données sources et préparation

| Jeu de données | Producteur | Utilisé pour |
|---|---|---|
| Base des lieux et équipements culturels (86 366 lieux) | Ministère de la Culture | lieux à visiter, labels, densité INSEE des communes |
| Accessibilité des gares (2 798 gares) | SNCF Gares & Connexions | liste des gares, position, accessibilité |
| Fréquentation en gares 2015-2024 | SNCF Voyageurs | critère Calme |
| API Adresse (géocodage inverse) | data.gouv.fr | commune réelle de chaque gare |
| Facteurs d'émission | ADEME / impactco2.fr | empreinte carbone |
| Horaires temps réel | API SNCF (Navitia) | prochain train |

**Préparation** (`pipeline/build_dataset.py`, environ 30 secondes) :
1. **Commune de chaque gare** retrouvée par géocodage inverse. Le code commune contenu dans l'identifiant SNCF est faux pour 3,75 % des gares : La Barasse, à Marseille, portait par exemple le code des Baux-de-Provence.
2. **Fréquentation** rattachée à chaque gare par son nom (sans accents ni ponctuation) et son département : 99,75 % des gares ont trouvé leur fréquentation.
3. **Comptage des lieux** à 5 et 10 km de chaque gare : 2 798 × 77 158 distances calculées.
4. **Densité INSEE** connue pour 93,5 % des communes de gare. Pour les autres, c'est le niveau le plus fréquent parmi les lieux culturels à moins de 5 km. Ce vote est plus robuste qu'un seul voisin, car la base contient quelques erreurs de position (un conservatoire de Trappes est placé dans l'Oise).

---

## 9. Limites à connaître

- **Le calme est mesuré en gare**, pas sur le territoire : un site très touristique peut avoir une petite gare peu utilisée, parce que la plupart des visiteurs viennent en voiture.
- **Les monuments historiques dominent la base** (environ 56 % des lieux) : un village riche en petit patrimoine peut dépasser une ville dotée d'un grand musée. Le bonus des lieux labellisés corrige en partie ce biais.
- **La fréquence des trains n'est pas prise en compte** dans la note : certaines haltes n'ont que quelques trains par jour. L'onglet « Y aller » le montre au cas par cas.
- **Horaires d'ouverture, hébergement et restauration** ne sont pas connus.
- **Le bilan carbone est un ordre de grandeur** : distance approchée et facteurs moyens.
- **Le classement fin dépend des poids** ([§ 7.6](#76-la-note-sur-10)).
- **Risque éthique** : envoyer trop de visiteurs vers des lieux fragiles. L'outil sert à **répartir** le tourisme, pas à créer de nouveaux sites saturés.

---

## 10. Choix de conception

| Principe | Application dans la page |
|---|---|
| **Une page, zéro défilement** | Grille sur 100 % de la hauteur ; deux vues (Explorer, Comparer) au lieu d'une page longue ; liste paginée selon la place ; fiche en onglets ; lieux affichés seulement s'ils tiennent entièrement. Exception : sur téléphone (moins de 900 px de large) et sur les écrans très bas (moins de 560 px de haut), les blocs s'empilent et la page défile, faute de place. |
| **Lisible par tous** | Texte de 16 px, termes courants (« note sur 10 », « campagne », « gare typique ») au lieu de « centile », « médiane » ou « GCD » ; une idée par graphique ; valeurs écrites en toutes lettres. |
| **Style sobre, éditorial** | Fond papier, encre noire, filets fins plutôt que des cartes ombrées, titres en serif (Source Serif), texte en Source Sans, onglets soulignés, aucun dégradé, aucune ombre, coins à peine arrondis. Le but est d'éviter l'esthétique « dashboard générique » et de laisser la place aux données. |
| **Rapport encre / donnée** | Pas de 3D ni d'ombre portée sur les graphiques ; axes supprimés quand la valeur est écrite ; grilles absentes ou réduites aux repères utiles (lignes à 50 dans « Situer », repères 0/5/10 dans les haltères). |
| **Couleur porteuse de sens** | Bleu ardoise = la donnée importante (gare choisie, train, destination A) ; terre cuite = destination B ; gris = le contexte. Le duo A/B est validé pour le daltonisme (écart ≥ 18) et doublé par les lettres A/B et la forme (rond/carré). Rampe séquentielle à une seule teinte sur la carte. Les actions restent en noir et blanc. |
| **Accessibilité** | Contrastes conformes WCAG AA ; cibles tactiles de 40 à 46 px ; navigation complète au clavier (lien d'évitement, liste en boutons, onglets aux flèches ← →) ; descriptions des graphiques pour les lecteurs d'écran ; thème sombre ; animations coupées si le système le demande ; information jamais portée par la seule couleur (étiquettes texte, valeurs chiffrées). |
| **Transparence** | Guide « Comment ça marche ? » dans la page, ce document pour le détail, sources citées. |

**Stack** : Python (Pandas, NumPy) pour préparer les données ; Flask pour l'API ; **Altair / Vega-Lite** pour les graphiques ; Leaflet pour la carte. Les graphiques sont décrits en Python, au plus près des calculs, et s'adaptent à la taille de leur zone.

---

## 11. Mode démonstration (/oral)

L'adresse **`/oral`** ouvre la même page avec un scénario préréglé pour la soutenance :

| Réglage | Valeur |
|---|---|
| Départ | Marseille Saint-Charles |
| Jusqu'à | 200 km |
| Envie | Un peu de tout |
| Comparaison | A = Théoule-sur-Mer, B = Èze |
| Fiche ouverte | Théoule-sur-Mer |

Un repère « Démo · départ Marseille Saint-Charles · quitter » s'affiche dans l'en-tête. Tous les contrôles restent utilisables pendant la démonstration.

**Liens directs** : `/oral#comparaison` ouvre la vue Comparer ; `/oral#y-aller`, `#pourquoi` et `#situer` ouvrent un onglet de la fiche.

**Changer de scénario** : modifier le dictionnaire `DEMO` en haut de `app/backend.py` (noms de gares exacts tels qu'ils apparaissent dans la liste).

**Pourquoi ce duo ?** Deux villages de la Côte d'Azur desservis par le train, aux profils opposés : Èze, célèbre et très culturel (250 lieux, 8,8/10 en culture) mais très fréquenté (826 voyageurs par jour, 2,7/10 en calme), contre Théoule-sur-Mer, plus calme (88 voyageurs par jour) et plus proche, avec moins de lieux à visiter. Leurs notes globales sont presque égales (6,1 contre 6,0) : la comparaison montre que **le choix dépend des envies**. Passer sur « Calme absolu » ou « Culture d'abord » fait basculer le verdict.

**Pourquoi pas la première idée de la liste ?** Saint-Laurent-d'Aigouze, première idée depuis Marseille, n'a aucun train dans les 24 heures selon l'API SNCF, comme plusieurs gares voisines du Gard. C'est une limite à signaler : la note ne tient pas compte de la desserte ([§ 9](#9-limites-à-connaître)).
