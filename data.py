"""Données CFLP transcrites de l'annexe A.1 du PDF, pages 31–33.

Coordonnées (latitude, longitude) en degrés, demandes et capacités en
palettes/an, coûts fixes en euros/an et manutention en euros/palette.
Seules les données du CFLP sont conservées.
"""

import math

PORT = ("Genes (port)", 44.41, 8.93)

# nom, latitude, longitude, demande annuelle
CLIENTS = [
    ("Wolfsburg (VW)", 52.42, 10.79, 7800),
    ("Emden (VW)", 53.37, 7.21, 3200),
    ("Bremen (Mercedes)", 53.08, 8.80, 4600),
    ("Koeln (Ford)", 50.94, 6.96, 3900),
    ("Saarlouis (Ford)", 49.31, 6.75, 2100),
    ("Ruesselsheim (Opel)", 49.99, 8.41, 2800),
    ("Sindelfingen (Mercedes)", 48.71, 9.00, 7200),
    ("Neckarsulm (Audi)", 49.19, 9.22, 3600),
    ("Ingolstadt (Audi)", 48.77, 11.42, 6900),
    ("Muenchen (BMW)", 48.18, 11.56, 5200),
    ("Dingolfing (BMW)", 48.63, 12.50, 6100),
    ("Regensburg (BMW)", 49.01, 12.10, 3800),
    ("Leipzig (BMW/Porsche)", 51.34, 12.37, 4400),
    ("Zwickau (VW)", 50.72, 12.49, 3300),
    ("Eisenach (Opel)", 50.98, 10.32, 1900),
    ("Schweinfurt (ZF)", 50.05, 10.23, 2600),
    ("Herzogenaurach (Schaeffler)", 49.57, 10.89, 2300),
    ("Bamberg (Bosch)", 49.89, 10.90, 2000),
    ("Friedrichshafen (ZF)", 47.65, 9.48, 2400),
    ("Salzgitter (VW)", 52.15, 10.33, 2700),
    ("Baunatal (VW)", 51.25, 9.41, 3100),
]

# nom, latitude, longitude, coût fixe, capacité annuelle, manutention
DEPOTS = [
    ("Hamburg", 53.55, 10.00, 520_000, 45_000, 6.5),
    ("Hannover", 52.37, 9.73, 430_000, 40_000, 5.8),
    ("Dortmund", 51.51, 7.47, 440_000, 40_000, 5.8),
    ("Kassel", 51.31, 9.50, 380_000, 35_000, 5.2),
    ("Frankfurt", 50.11, 8.68, 560_000, 45_000, 6.8),
    ("Erfurt", 50.98, 11.03, 350_000, 35_000, 4.6),
    ("Nuernberg", 49.45, 11.08, 450_000, 40_000, 5.6),
    ("Mannheim", 49.49, 8.47, 470_000, 40_000, 5.9),
    ("Ulm", 48.40, 9.99, 400_000, 35_000, 5.4),
]

CIRCUITY = 1.25
TRUCK_COST_KM = 1.70
PALLETS_PER_TRUCK = 33
# Fraction exacte de l'annexe, conformément au choix final de l'utilisateur.
# La valeur 0,052 indiquée dans le texte du PDF est un arrondi.
INBOUND_EUR_PAL_KM = TRUCK_COST_KM / PALLETS_PER_TRUCK
OUTBOUND_EUR_PAL_KM = 0.14


def haversine_km(lat1, lon1, lat2, lon2):
    """Distance orthodromique en km ; rayon terrestre de 6 371 km (annexe)."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def road_km(a, b):
    """Estimation routière du PDF : distance à vol d'oiseau × 1,25."""
    return CIRCUITY * haversine_km(a[1], a[2], b[1], b[2])
