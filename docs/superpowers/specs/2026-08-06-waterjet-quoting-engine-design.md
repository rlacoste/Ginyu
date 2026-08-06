# Moteur de soumission waterjet — Design V1

## Contexte et objectif

Prototype en Python pur qui lit un fichier DXF 2D, en extrait la géométrie
des pièces, et calcule une estimation de soumission grossière (temps de
coupe, matière nécessaire, prix). C'est une V1 : l'entrée "fichier DXF
uploadé" sera remplacée plus tard par une connexion à un pipeline en amont
(probablement iGEMS ou équivalent), donc la source du fichier doit être une
frontière propre et facilement remplaçable, séparée de la logique de calcul.

Pas de base de données, pas d'interface web. Exécution en ligne de commande
qui prend un chemin DXF + métadonnées en arguments et affiche un résultat
lisible ainsi qu'un dict/JSON structuré destiné à être consommé par d'autres
composants plus tard.

## Contraintes

- Python 3, `ezdxf` pour parser le DXF. Dépendances minimales — pas de
  `shapely` ni d'autre librairie géométrie/CAO.
- Code organisé en modules clairs et courts, à responsabilité unique.
- La table matériaux est un fichier de données séparé (JSON), pas codée en
  dur — elle doit pouvoir migrer vers une base de données sans toucher au
  moteur de calcul.
- Signaler clairement (erreur explicite) un couple matériau/épaisseur/
  finition manquant plutôt que deviner une valeur.

## Décisions de conception (issues du brainstorming)

1. **Une pièce par DXF, quantité en argument CLI.** Le DXF représente un
   design de pièce (potentiellement avec plusieurs groupes de contours
   disjoints détectés par le moteur). La quantité commandée est fournie via
   `--qty` et s'applique uniformément à chaque groupe de pièce détecté dans
   le fichier — pas de détection de doublons entre pièces.
2. **Matériau, épaisseur, finition et quantité fournis en arguments CLI**,
   pas déduits du DXF (pas de convention de nommage de calque à respecter
   côté amont).
3. **Chaînage de contours nécessaire.** Certains DXF contiennent des
   contours fermés déjà groupés (LWPOLYLINE/POLYLINE fermée, CIRCLE), mais
   d'autres contiennent des segments LINE/ARC isolés qui forment une boucle
   fermée bout-à-bout sans être regroupés en une seule entité. Le moteur
   doit détecter et rechaîner ces segments.
4. **Table matériaux à 3 niveaux** : matériau → épaisseur → finition (clé
   `quality`, défaut `"standard"`). Anticipe le fait que le moteur de
   nesting iGEMS utilisé par l'utilisateur encode les feed rates selon le
   niveau de finition — la table est déjà structurée pour recevoir plusieurs
   finitions par couple matériau/épaisseur sans migration de schéma cassante
   plus tard.
5. **Approche géométrie : ezdxf pur, pas de shapely.** Voir section
   Extraction géométrique.

## Architecture — structure de fichiers

```
waterjet_quoter/
├── main.py              # CLI : parse arguments, orchestre le pipeline, affiche le résultat
├── ingestion.py          # Frontière de source du fichier (remplaçable plus tard)
├── geometry.py            # Extraction géométrique par pièce
├── materials.py            # Chargement + lookup de la table matériaux
├── materials.json           # Données de référence (feed rate, pierce time)
├── costing.py                 # Temps de coupe, estimation matière, calcul de prix
├── config.py                    # Constantes ajustables
├── reporting.py                   # Sortie lisible (CLI) + dict/JSON structuré
├── make_test_dxf.py                # Génère le DXF de test
```

### `ingestion.py` — frontière de source

Expose une fonction (ou petite classe) `load_dxf(source: str) -> ezdxf.Drawing`
qui aujourd'hui prend un chemin de fichier local et retourne un objet
`ezdxf.Drawing` chargé. C'est la SEULE partie du code qui sait que la source
est un fichier local — `geometry.py` et tout ce qui suit ne reçoit qu'un
`Drawing` déjà chargé et n'a aucune connaissance de sa provenance. Quand le
pipeline amont sera branché, seule cette fonction change (ou une nouvelle
implémentation du même contrat), rien d'autre.

### Flux de données

```
main.py (CLI args)
  → ingestion.load_dxf(path) → ezdxf.Drawing
  → geometry.extract_pieces(drawing) → list[Piece]
  → materials.lookup(material, thickness, quality) → feed_rate, pierce_time
  → costing.compute_quote(pieces, material_params, qty, config) → résultat structuré
  → reporting.print_report(résultat) + reporting.to_json(résultat)
```

## Extraction géométrique (`geometry.py`)

### Unification des types d'entités

Toutes les entités (LINE, ARC, CIRCLE, LWPOLYLINE, POLYLINE, SPLINE) sont
converties via `ezdxf.path.make_path(entity)` puis aplaties en polyligne de
points via `.flattening(distance)`. Un seul mécanisme gère tous les types
d'entités au lieu de formules de périmètre séparées par type — SPLINE est
ainsi approximée gratuitement par le même chemin.

### Chaînage des contours

- Les entités déjà fermées (CIRCLE, LWPOLYLINE/POLYLINE avec flag fermé)
  deviennent chacune un contour directement.
- Les entités ouvertes (LINE, ARC isolés, POLYLINE ouverte) sont aplaties en
  segments avec points de départ/fin. Le moteur construit un graphe où les
  nœuds sont les points d'extrémité (arrondis à une tolérance fixe pour
  gérer l'imprécision flottante) et chaîne les segments partageant un point
  d'extrémité jusqu'à refermer la boucle.
- Un contour qui ne se referme pas (segments orphelins) est signalé comme
  contour incomplet dans un avertissement plutôt que silencieusement ignoré.

### Regroupement en pièces (containment par profondeur)

Pour chaque contour fermé obtenu, un test point-dans-polygone (ray casting,
implémenté à la main) détermine sa profondeur d'imbrication : combien
d'autres contours le contiennent. Profondeur paire (0, 2, 4…) = contour
extérieur d'une pièce (ou îlot solide à l'intérieur d'un trou) ; profondeur
impaire = trou découpé dans le contour parent immédiat de profondeur
inférieure. Les contours de profondeur paire démarrent de nouveaux groupes
de "pièce" ; les contours de profondeur impaire sont rattachés comme trous
à leur parent direct.

### Par pièce, le moteur calcule

1. **Longueur totale de coupe** = somme des périmètres de tous ses contours
   (extérieur + trous), en sommant les longueurs des segments aplatis.
2. **Nombre de perçages** = nombre de contours fermés distincts appartenant
   à la pièce.
3. **Bounding box** (largeur X, hauteur Y) et aire, calculés sur l'ensemble
   des points de tous les contours de la pièce.

## Table matériaux (`materials.json` + `materials.py`)

Format à 3 niveaux : matériau → épaisseur → finition.

```json
{
  "aluminum": {
    "6mm": { "standard": { "feed_rate_ipm": 18.0, "pierce_time_sec": 3.0 } },
    "12mm": { "standard": { "feed_rate_ipm": 9.0, "pierce_time_sec": 6.0 } }
  },
  "mild_steel": {
    "6mm": { "standard": { "feed_rate_ipm": 14.0, "pierce_time_sec": 4.0 } },
    "12mm": { "standard": { "feed_rate_ipm": 7.0, "pierce_time_sec": 8.0 } }
  },
  "stainless_steel": {
    "6mm": { "standard": { "feed_rate_ipm": 10.0, "pierce_time_sec": 5.0 } },
    "12mm": { "standard": { "feed_rate_ipm": 5.0, "pierce_time_sec": 10.0 } }
  }
}
```

`materials.py` expose `lookup(material: str, thickness: str, quality: str = "standard") -> MaterialParams`
(feed rate, pierce time). Si le triplet n'existe pas dans la table, lève une
exception explicite (nom du triplet manquant dans le message) — pas de
valeur par défaut devinée. Le module ne fait que charger le JSON et
indexer dessus ; aucune valeur n'est codée en dur dans `materials.py`, pour
permettre une migration future vers une base de données sans toucher au
reste du moteur.

## Calcul du temps de coupe (`costing.py`)

Temps de coupe unitaire d'une pièce :

```
temps_unitaire = (longueur_totale_coupe / feed_rate) + (nombre_perçages × pierce_time)
```

Agrégé par pièce (type distinct, pas par occurrence) : `temps_unitaire`,
`quantité` (depuis `--qty`), `temps_total = temps_unitaire × quantité`, tous
rendus explicites dans la sortie.

## Estimation matière (`costing.py` + `config.py`)

```
aire_totale = Σ (aire_bbox_pièce × quantité_pièce)
feuilles_nécessaires = ceil(aire_totale / (aire_feuille_standard × facteur_utilisation))
```

- Feuille standard : 48×96 po (configurable dans `config.py`).
- `NESTING_UTILIZATION_FACTOR = 0.75`, modifiable en haut de `config.py`.
- Avertissement par pièce si sa plus grande dimension bbox dépasse
  `LARGE_PIECE_DIMENSION_THRESHOLD_IN = 40` po : message "nesting manuel
  recommandé — estimation matière peu fiable pour cette pièce", inclus dans
  la sortie structurée (`material_estimate.warnings`).

## Calcul du prix (`costing.py` + `config.py`)

```
prix = (temps_machine_total_heures × MACHINE_RATE_PER_HOUR)
     + (feuilles_nécessaires × SHEET_COST_BY_MATERIAL[matériau])
     + Σ LABOR_FLAT_FEES.values()
```

Valeurs par défaut dans `config.py` (ajustables) :
- `MACHINE_RATE_PER_HOUR = 125`
- `SHEET_COST_BY_MATERIAL` : valeurs plausibles par matériau (ex. aluminum,
  mild_steel, stainless_steel)
- `LABOR_FLAT_FEES = {"programming": ..., "setup": ..., "shipping": ...}`
  (montants plausibles)

La sortie détaille la ventilation (matière / temps machine / main-d'œuvre),
pas juste un total.

## CLI (`main.py`)

```
python main.py <chemin.dxf> --material aluminum --thickness 6mm [--quality standard] [--qty 1]
```

`material`, `thickness` requis. `qty` optionnel (défaut 1). `quality`
optionnel (défaut `"standard"`).

## Contrat de sortie structurée

```json
{
  "input": {"file": "...", "material": "aluminum", "thickness": "6mm", "quality": "standard", "quantity": 50},
  "pieces": [
    {"piece_id": 0, "cut_length_in": 35.14, "pierce_count": 2, "bbox_width_in": 10.0, "bbox_height_in": 6.0, "area_in2": 60.0, "unit_time_min": 2.53}
  ],
  "cutting_time": {"quantity": 50, "total_time_min": 126.5},
  "material_estimate": {"total_area_in2": 3000.0, "sheets_needed": 2, "utilization_factor": 0.75, "warnings": []},
  "geometry_warnings": [],
  "pricing": {
    "machine_time_cost": 263.5,
    "material_cost": 400.0,
    "labor_cost": 150.0,
    "total_price": 813.5
  }
}
```

`pieces` est une liste même si le cas typique en V1 est une seule pièce par
DXF, pour couvrir le cas où le chaînage/containment détecte plusieurs
groupes de contours disjoints dans le même fichier.

## Pièce de test (`make_test_dxf.py`)

Génère un DXF en pouces : plaque rectangulaire 10×6 po avec un trou
circulaire de 1 po de diamètre centré. Valeurs attendues (documentées en
commentaire dans le script, pour comparaison avec la sortie du moteur) :

- Périmètre extérieur : 32 po
- Circonférence du trou : ≈ 3.14 po
- Longueur de coupe totale attendue : ≈ 35.14 po
- Bounding box : 10 × 6 po
- Nombre de perçages : 2

## Hors scope V1

- Détection de doublons de pièces (géométrie identique) — rejetée au profit
  de `--qty` explicite en CLI.
- Blocs/INSERT DXF pour la détection de quantité.
- Base de données, interface web.
- Nesting réel (l'estimation matière est un calcul grossier par aire, pas un
  algorithme de nesting).
