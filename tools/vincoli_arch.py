"""Controlla se un punto cade vicino a un'area archeologica vincolata (Vincoli in Rete, MiC), via WMS.

Uso come modulo: distanza_vincolo(lat, lon, raggio_m=300) -> metri dal bordo piu vicino dell'area vincolata, o None.
Da riga di comando: python -I tools/vincoli_arch.py LAT LON
Fonte: http://vincoliinrete.beniculturali.it/geoserver/ows, layer wms_public:geo_aree_archeol_vincolate (solo WMS: il WFS
chiede credenziali). Si scarica una finestra trasparente e si cerca il pixel colorato piu vicino al centro.
"""
import io
import math
import sys
import urllib.parse
import urllib.request

import numpy as np
from PIL import Image

URL = 'http://vincoliinrete.beniculturali.it/geoserver/ows'
LAYER = 'wms_public:geo_aree_archeol_vincolate'
PX = 200


def distanza_vincolo(lat, lon, raggio_m=300, tentativi=3):
    dlat = raggio_m / 111_000
    dlon = raggio_m / (111_000 * math.cos(math.radians(lat)))
    q = {'service': 'WMS', 'version': '1.1.1', 'request': 'GetMap', 'layers': LAYER, 'styles': '', 'srs': 'EPSG:4326',
         'bbox': f'{lon - dlon:.6f},{lat - dlat:.6f},{lon + dlon:.6f},{lat + dlat:.6f}', 'width': PX, 'height': PX,
         'format': 'image/png', 'transparent': 'true'}
    rich = urllib.request.Request(URL + '?' + urllib.parse.urlencode(q), headers={'User-Agent': 'MappaItalia/0.1'})
    for t in range(tentativi):
        try:
            with urllib.request.urlopen(rich, timeout=60) as r:
                a = np.array(Image.open(io.BytesIO(r.read())).convert('RGBA'))[..., 3] > 0
            break
        except Exception:
            if t == tentativi - 1:
                return None
    if not a.any():
        return None
    ys, xs = np.nonzero(a)
    return float(np.hypot(ys - PX / 2, xs - PX / 2).min() * 2 * raggio_m / PX)


if __name__ == '__main__':
    print(distanza_vincolo(float(sys.argv[1]), float(sys.argv[2])))
