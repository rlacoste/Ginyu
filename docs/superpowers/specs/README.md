# Guide d'usage — Moteur de soumission waterjet

Guide pratique pour utiliser le CLI au quotidien. Pour l'historique des
décisions de design, voir
[2026-08-06-waterjet-quoting-engine-design.md](2026-08-06-waterjet-quoting-engine-design.md).
Ce README-ci est la référence à jour ; le doc de design ne l'est plus
entièrement (table matériaux JSON → Postgres, `pierce_time` retiré).

## Ce que fait l'outil

Lit un fichier DXF, en extrait la géométrie de coupe (contours, perçages,
bounding box), calcule un temps de coupe / une estimation de matière / un
prix à partir d'une table de matériaux (Postgres/Supabase, alimentée par un
export iGEMS), et affiche le résultat en texte lisible + JSON structuré.

C'est un prototype : les prix de feuilles (`SHEET_COST_BY_MATERIAL`) et les
forfaits de main-d'œuvre (`LABOR_FLAT_FEES`) dans `waterjet_quoter/config.py`
sont encore des valeurs inventées à remplacer par tes vrais chiffres.

## Installation / setup

```bash
cd /Users/raphaellacoste-cordeau/Projects/Ginyu/Ginyu
source venv/bin/activate          # ou utilise ./venv/bin/python directement
pip install -r requirements.txt   # si le venv n'est pas déjà à jour
```

Un fichier `.env` à la racine du projet doit contenir la chaîne de connexion
à la base Postgres (Supabase → *Project Settings* → *Database* → *Connection
string*) :

```
DATABASE_URL=postgresql://...
```

`.env` est ignoré par git — jamais commité. Si la connexion directe
(`db.xxxx.supabase.co:5432`) échoue, utilise plutôt le **Session pooler**
(même écran Supabase) — la connexion directe exige IPv6, souvent indisponible
sur un réseau résidentiel standard.

## Trouver les bons arguments (`--material`, `--thickness`, `--quality`)

Ne devine pas ces valeurs — utilise l'outil de référence, qui lit
directement la table en base :

```bash
# Tout afficher (1559 lignes, plutôt utiliser --material pour filtrer)
python -m waterjet_quoter.list_materials

# Filtrer par matériau (sous-chaîne, insensible à la casse)
python -m waterjet_quoter.list_materials --material Aluminium

# Exporter la table complète en CSV (pour Excel, etc.)
python -m waterjet_quoter.list_materials --csv reference.csv
```

Exemple de sortie filtrée :

```
Matériau                  Grade                 Épaisseur (po)   Vitesse (po/min)
---------------------------------------------------------------------------------
Aluminium                 6061 T6                       0.2500             90.424
Stainless Steel           304 Fini 2B                   0.0310            147.320
```

- `--material` doit correspondre **exactement** au nom dans la colonne
  "Matériau" (ex. `Aluminium`, pas `aluminum`).
- `--quality` désigne l'alliage/grade réel (ex. `6061 T6`, `304 Fini 2B`,
  `A1008`) — **pas** un niveau de finition. Il n'y a pas de valeur par
  défaut : un matériau peut avoir plusieurs grades avec des vitesses de
  coupe différentes, deviner serait dangereux.
- `--thickness` est l'épaisseur exacte en pouces décimaux telle
  qu'elle apparaît dans la table (ex. `0.25`, `0.0630`) — une valeur qui ne
  correspond à aucune entrée exacte du catalogue déclenche une erreur
  listant les épaisseurs disponibles pour ce matériau/grade, plutôt que de
  prendre la plus proche.

## Faire une soumission

```bash
python -m waterjet_quoter.main <chemin.dxf> \
  --material Aluminium --thickness 0.25 --quality "6061 T6" --qty 50
```

```
usage: python -m waterjet_quoter.main [-h] --material MATERIAL
                                      --thickness THICKNESS --quality QUALITY
                                      [--qty QTY] [--json]
                                      dxf_path

positional arguments:
  dxf_path              Chemin vers le fichier DXF

options:
  -h, --help            show this help message and exit
  --material MATERIAL   Nom du matériau (ex: aluminum)
  --thickness THICKNESS
                        Épaisseur en pouces (ex: 0.25)
  --quality QUALITY     Alliage/grade du matériau (ex: 6061-T6) -- aucune
                        valeur par défaut sensée
  --qty QTY             Quantité commandée (défaut: 1)
  --json                Affiche uniquement la sortie JSON
```

`--material`, `--thickness` et `--quality` sont tous les trois obligatoires.
`--qty` doit être un entier positif (0 ou négatif → erreur explicite).
`--json` limite la sortie au JSON structuré (utile pour brancher un autre
programme en aval) ; sans ce drapeau, le rapport lisible ET le JSON sont
affichés l'un après l'autre.

### Générer un DXF de test

```bash
python -m waterjet_quoter.make_test_dxf
```

Crée `test_plate.dxf` (plaque 10×6 po avec trou de 1 po de diamètre centré)
— périmètre extérieur 32 po, circonférence du trou ~3.14 po, longueur de
coupe totale attendue ~35.14 po, 2 perçages. Utile pour valider que
l'installation fonctionne avant de tester avec de vraies pièces.

## Lire le résultat

Le rapport texte affiche, par pièce : longueur de coupe, nombre de
perçages, bounding box, temps unitaire — puis le temps de coupe total, le
nombre de feuilles nécessaires, et la ventilation du prix (temps machine /
matière / main-d'œuvre). Le JSON structuré porte les mêmes données pour
consommation par un autre programme.

**Le temps de coupe est purement `longueur_de_coupe / feed_rate`** — il n'y
a plus de temps de perçage dans le calcul (retiré volontairement ; la table
iGEMS ne le fournissait pas et le concept a été abandonné). `pierce_count`
reste affiché par pièce à titre indicatif (nombre de contours/amorces de
coupe), mais ne pèse plus dans le temps calculé.

## Comprendre les avertissements (`geometry_warnings`)

Le moteur signale explicitement plutôt que de deviner. Types d'avertissement
possibles :

| Message (début) | Signification | Action |
|---|---|---|
| `Entité <type> ignorée : géométrie non exploitable` | Une entité DXF n'a pas pu être traitée (polymesh non supporté, spline dégénérée, etc.) | Vérifier cette entité dans le DXF source |
| `Contour de longueur quasi nulle ignoré` | Un contour dégénéré (ligne de longueur ~0, artefact de dessin) a été exclu | Généralement anodin, mais vérifier si une vraie petite pièce a pu être filtrée par erreur |
| `N contours incomplets détectés (X à Y points)` | Des segments qui ne se referment jamais en boucle — typiquement des lignes de cotation/annotation qui ont fini dans le calcul par erreur | **Signal important** : indique que le DXF contient probablement des éléments hors géométrie de coupe (cotes, cartouche) mélangés à la pièce |
| `Aucune pièce exploitable détectée` | Rien d'exploitable dans le DXF | Vérifier le fichier — probablement le mauvais fichier ou tout est sur des calques non pris en charge |
| `Pièces X et Y semblent identiques` | Deux pièces distinctes ont des dimensions et une longueur de coupe quasi identiques | **Vérifier manuellement** — cas réel rencontré : une pièce tracée deux fois dans le même DXF (une fois dans le cartouche) |

**Limite connue non résolue** : le moteur ne filtre pas encore
automatiquement le cartouche/les lignes de cotation par calque ou par
heuristique géométrique — tout ce qui est un contour fermé sur un type
d'entité supporté (LINE/ARC/CIRCLE/LWPOLYLINE/POLYLINE/SPLINE) est traité
comme une pièce à découper. Si un DXF client contient un cartouche dessiné
avec des contours fermés (pas seulement du texte/des cotes), il sera compté
comme une pièce supplémentaire. **Toujours vérifier le nombre de pièces et
les avertissements avant d'envoyer une soumission.**

## Mettre à jour les données matériaux

Quand un nouvel export iGEMS est disponible :

```bash
python -m waterjet_quoter.import_materials <export.csv>
```

Idempotent (upsert sur matériau/grade/épaisseur) — peut être relancé autant
de fois que nécessaire avec un export mis à jour.

## Lancer les tests

```bash
python -m pytest -v
```

La suite ne dépend pas d'une connexion DB en direct (les tests injectent des
tables en mémoire), sauf un test d'intégration qui se saute automatiquement
si `DATABASE_URL` n'est pas configuré.
