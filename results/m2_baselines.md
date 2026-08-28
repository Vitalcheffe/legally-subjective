# M2 — Baselines statistiques (Corpus-Monde v1)

Répartition : entraînement OT2015..OT2019 (304 affaires étiquetées), test OT2020..OT2023 (225 affaires étiquetées).
Toutes les précisions sont accompagnées d'un intervalle de confiance Wilson à 95 %.

## Direction de la décision (SCDB decisionDirection : 1 conservateur, 2 libéral)

| Mandat | Conservateur | Libéral | % conservateur |
|---|---|---|---|
| OT2015 | 33 | 33 | 50.0 % |
| OT2016 | 30 | 32 | 48.4 % |
| OT2017 | 29 | 30 | 49.2 % |
| OT2018 | 30 | 35 | 46.2 % |
| OT2019 | 26 | 26 | 50.0 % |
| OT2020 | 31 | 22 | 58.5 % |
| OT2021 | 39 | 22 | 63.9 % |
| OT2022 | 29 | 25 | 53.7 % |
| OT2023 | 28 | 29 | 49.1 % |

## Résultats des baselines (jeu de test)

| Baseline | Précision | IC 95 % |
|---|---|---|
| B1 Classe majoritaire (libéral) | 43.6 % | [37.2, 50.1] % |
| B2 Toujours conservateur | 56.4 % | [49.9, 62.8] % |
| B2 Toujours libéral | 43.6 % | [37.2, 50.1] % |
| B3 Toujours infirmer | 60.1 % | [51.8, 67.9] % |
| B4 Idéologie par juge (vote) | 63.7 % | [61.3, 65.9] % |
| B4 Idéologie par juge (affaire) | 55.8 % | [49.3, 62.2] % |

Kappa de Cohen (B1) : 0.0

## Accord inter-juges (direction du vote, n >= 50)

| Paire | Accord | IC 95 % |
|---|---|---|
| ACBarrett — BMKavanaugh | 89.2 % | [84.3, 92.7] % |
| ACBarrett — CThomas | 83.9 % | [78.3, 88.2] % |
| ACBarrett — EKagan | 68.1 % | [61.5, 74.0] % |
| ACBarrett — JGRoberts | 86.9 % | [81.7, 90.8] % |
| ACBarrett — KBJackson | 70.6 % | [61.5, 78.4] % |
| ACBarrett — NMGorsuch | 81.5 % | [75.7, 86.2] % |
| ACBarrett — SAAlito | 83.7 % | [78.1, 88.1] % |
| ACBarrett — SGBreyer | 57.8 % | [48.1, 67.0] % |
| ACBarrett — SSotomayor | 62.9 % | [56.2, 69.1] % |
| AMKennedy — CThomas | 77.6 % | [71.0, 83.0] % |
| AMKennedy — EKagan | 83.2 % | [77.0, 87.9] % |
| AMKennedy — JGRoberts | 87.9 % | [82.4, 91.9] % |
| AMKennedy — NMGorsuch | 85.5 % | [75.3, 91.9] % |
| AMKennedy — RBGinsburg | 76.5 % | [69.8, 82.1] % |
| AMKennedy — SAAlito | 82.9 % | [76.7, 87.7] % |
| AMKennedy — SGBreyer | 80.3 % | [74.0, 85.4] % |
| AMKennedy — SSotomayor | 74.0 % | [67.2, 79.9] % |
| BMKavanaugh — CThomas | 78.8 % | [74.1, 82.8] % |
| BMKavanaugh — EKagan | 69.5 % | [64.3, 74.2] % |
| BMKavanaugh — JGRoberts | 94.6 % | [91.6, 96.5] % |
| BMKavanaugh — KBJackson | 75.2 % | [66.4, 82.4] % |
| BMKavanaugh — NMGorsuch | 79.0 % | [74.3, 83.1] % |
| BMKavanaugh — RBGinsburg | 63.3 % | [53.9, 71.8] % |
| BMKavanaugh — SAAlito | 86.3 % | [82.2, 89.6] % |
| BMKavanaugh — SGBreyer | 67.1 % | [60.7, 73.0] % |
| BMKavanaugh — SSotomayor | 64.2 % | [58.9, 69.1] % |
| CThomas — EKagan | 59.0 % | [54.7, 63.2] % |
| CThomas — JGRoberts | 77.9 % | [74.1, 81.2] % |
| CThomas — KBJackson | 57.4 % | [48.0, 66.3] % |
| CThomas — NMGorsuch | 81.5 % | [77.5, 85.0] % |
| CThomas — RBGinsburg | 56.9 % | [51.2, 62.4] % |
| CThomas — SAAlito | 87.4 % | [84.3, 90.0] % |
| CThomas — SGBreyer | 57.4 % | [52.6, 62.1] % |
| CThomas — SSotomayor | 54.2 % | [49.9, 58.5] % |
| EKagan — JGRoberts | 74.0 % | [70.1, 77.6] % |
| EKagan — KBJackson | 88.1 % | [80.7, 92.9] % |
| EKagan — NMGorsuch | 64.0 % | [59.2, 68.5] % |
| EKagan — RBGinsburg | 89.4 % | [85.4, 92.5] % |
| EKagan — SAAlito | 61.1 % | [56.8, 65.2] % |
| EKagan — SGBreyer | 90.4 % | [87.1, 92.9] % |
| EKagan — SSotomayor | 89.5 % | [86.6, 91.9] % |
| JGRoberts — KBJackson | 73.4 % | [64.4, 80.8] % |
| JGRoberts — NMGorsuch | 77.3 % | [73.0, 81.1] % |
| JGRoberts — RBGinsburg | 70.6 % | [65.2, 75.4] % |
| JGRoberts — SAAlito | 84.3 % | [81.0, 87.2] % |
| JGRoberts — SGBreyer | 72.1 % | [67.6, 76.2] % |
| JGRoberts — SSotomayor | 68.1 % | [63.9, 71.9] % |
| KBJackson — NMGorsuch | 65.7 % | [56.4, 74.0] % |
| KBJackson — SAAlito | 61.7 % | [52.2, 70.3] % |
| KBJackson — SSotomayor | 90.8 % | [83.9, 94.9] % |
| NMGorsuch — RBGinsburg | 60.3 % | [53.1, 67.1] % |
| NMGorsuch — SAAlito | 81.2 % | [77.1, 84.7] % |
| NMGorsuch — SGBreyer | 59.1 % | [53.4, 64.6] % |
| NMGorsuch — SSotomayor | 59.8 % | [54.9, 64.4] % |
| RBGinsburg — SAAlito | 61.1 % | [55.4, 66.4] % |
| RBGinsburg — SGBreyer | 87.3 % | [83.1, 90.6] % |
| RBGinsburg — SSotomayor | 90.6 % | [86.7, 93.4] % |
| SAAlito — SGBreyer | 61.4 % | [56.6, 66.0] % |
| SAAlito — SSotomayor | 55.5 % | [51.2, 59.8] % |
| SGBreyer — SSotomayor | 86.3 % | [82.7, 89.3] % |
