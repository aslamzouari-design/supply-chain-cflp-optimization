# Capacitated Facility Location Problem (CFLP)

Résolution du modèle initial de la section 3 du PDF `Projet5_Supply_Chain_MILP (1).pdf`, avec Python, PuLP 3.3.0 et CBC. Périmètre : localisation capacitaire à affectation unique uniquement.

## Exécution

Python 3.12 a été utilisé. Depuis la racine du dépôt (Linux/macOS) :

```bash
python3 -m venv ../.venv-cflp
source ../.venv-cflp/bin/activate
python -m pip install -r requirements.txt
PYTHONDONTWRITEBYTECODE=1 python cflp_model.py
```

CBC est fourni avec la distribution PuLP utilisée. Aucun service, secret ou autre bibliothèque Python n’est nécessaire. Dans l’environnement cloud préparé, le Python installé est `/workspace/.venvs/supply-chain-cflp/bin/python`.

Le programme affiche les résultats et écrit `results.json` dans le répertoire courant (remplacé à chaque exécution). Ce fichier conserve les 198 valeurs de décision, les affectations, les charges, les coûts, les distances Gênes–entrepôts, les statuts et le journal CBC. `--output CHEMIN` permet de choisir un autre fichier. Le code de sortie est non nul si l’optimalité n’est pas prouvée.

## Données et formulation

`data.py` reprend exactement les 21 clients, les 9 entrepôts et les coordonnées du port de l’annexe A.1 (pages 31–33), soit 81 900 palettes/an. Les distances sont calculées par Haversine (rayon 6 371 km), multipliées par 1,25, sans arrondi intermédiaire. Ce sont des estimations, pas des itinéraires routiers mesurés.

**Précision du coût amont :** le texte du PDF indique 0,052 €/palette/km, tandis que son code utilise `1.70 / 33`, soit 0,0515151515… . Le calcul principal utilise la fraction **`1.70 / 33`**, conformément à l’annexe et au choix final de l’utilisateur, sans arrondir le taux à 0,052. Le coût aval reste 0,14 €/palette/km. Aucune autre donnée n’est modifiée.

`cflp_model.py` minimise les coûts fixes et, pour chaque affectation, la demande multipliée par la somme transport amont + manutention + transport aval. Il utilise 9 variables binaires d’ouverture et 189 variables binaires d’affectation, avec 21 contraintes d’affectation unique, 9 contraintes de capacité conditionnées à l’ouverture et 189 liaisons `x_ij <= y_j`.

Le réseau et le nombre d’entrepôts ouverts sont choisis librement par CBC. Les références du PDF servent uniquement à la comparaison après résolution. L’optimalité exige les deux statuts PuLP (`status` et `sol_status`) et la confirmation dans le journal CBC. Les limites de gap relatif et absolu sont fixées à zéro, avec les tolérances numériques habituelles de CBC et une limite de 120 s. La faisabilité et la décomposition des coûts sont contrôlées avant publication des résultats.

## Résultats réellement calculés

CBC : **Optimal**, optimum prouvé, gap **0 %**, temps mesuré **0,0791 s** (variable selon la machine). **198 variables et 219 contraintes**.

| Entrepôt ouvert | Capacité (pal/an) | Charge (pal/an) | Utilisation | Clients |
|---|---:|---:|---:|---:|
| Kassel | 35 000 | 27 200 | 77,71 % | 7 |
| Nuernberg | 40 000 | 24 500 | 61,25 % | 7 |
| Ulm | 35 000 | 30 200 | 86,29 % | 7 |

| Client | Demande (pal/an) | Entrepôt |
|---|---:|---|
| Wolfsburg (VW) | 7 800 | Kassel |
| Emden (VW) | 3 200 | Kassel |
| Bremen (Mercedes) | 4 600 | Kassel |
| Koeln (Ford) | 3 900 | Kassel |
| Saarlouis (Ford) | 2 100 | Ulm |
| Ruesselsheim (Opel) | 2 800 | Ulm |
| Sindelfingen (Mercedes) | 7 200 | Ulm |
| Neckarsulm (Audi) | 3 600 | Ulm |
| Ingolstadt (Audi) | 6 900 | Ulm |
| Muenchen (BMW) | 5 200 | Ulm |
| Dingolfing (BMW) | 6 100 | Nuernberg |
| Regensburg (BMW) | 3 800 | Nuernberg |
| Leipzig (BMW/Porsche) | 4 400 | Nuernberg |
| Zwickau (VW) | 3 300 | Nuernberg |
| Eisenach (Opel) | 1 900 | Kassel |
| Schweinfurt (ZF) | 2 600 | Nuernberg |
| Herzogenaurach (Schaeffler) | 2 300 | Nuernberg |
| Bamberg (Bosch) | 2 000 | Nuernberg |
| Friedrichshafen (ZF) | 2 400 | Ulm |
| Salzgitter (VW) | 2 700 | Kassel |
| Baunatal (VW) | 3 100 | Kassel |

| Poste | Coût annuel (€) |
|---|---:|
| Coûts fixes | 1 230 000,00 |
| Transport amont | 3 143 822,35 |
| Manutention | 441 720,00 |
| Transport aval | 1 926 569,45 |
| **Total minimal** | 6 742 111,80 |

Le total calculé est **6 742 111,80 €**, soit **6 742 112 € à l’euro près**, conformément au PDF. Les trois entrepôts, les charges (27 200 / 24 500 / 30 200), les sept clients par entrepôt et les dimensions du modèle correspondent aussi aux références. L’écart de −0,20 € avec la référence publiée vient uniquement de son arrondi à l’euro.

La différence de précision du taux amont a été vérifiée par une seconde résolution : avec **0,052 exactement**, le coût passe à **6 771 700,71 €**, soit **29 588,92 € de plus**, avec les mêmes entrepôts et affectations. Pour reproduire cette comparaison sans remplacer le résultat principal :

```bash
PYTHONDONTWRITEBYTECODE=1 python cflp_model.py --inbound-rate 0.052 --output /tmp/cflp-rounded-results.json
```

Les composantes de coût sont arrondies séparément à l’affichage ; leur somme affichée peut différer d’un centime du total calculé sans arrondi.

Vérifications exécutées : transcription des 30 lignes clients/entrepôts et du port contre le PDF ; binarité, affectation unique, capacités et liaisons ; cohérence des quatre composantes de coût ; comparaison aux références. Des contrôles avec une limite de temps nulle et un modèle rendu infaisable confirment que le programme ne déclare pas indûment un optimum et ne présente pas de solution lorsque CBC n’en fournit aucune.
