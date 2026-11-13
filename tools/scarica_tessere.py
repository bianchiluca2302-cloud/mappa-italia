"""Scarica tessere di rilievo LiDAR (DTM 1 m ombreggiato, Toscana) da guardare una a una.

Uso: python -I tools/scarica_tessere.py LAT_SUD LON_OVEST [RIGHE] [COLONNE]
Ogni tessera e circa 1 km x 1 km, 1000x1000 pixel, salvata in dati/tessere/<lat>_<lon>.png.
Le immagini hanno una scritta di fonte lungo il bordo sinistro (circa 25 px): va ignorata.
"""
import math
import sys
import urllib.parse
import urllib.request
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
WMS = 'https://www502.regione.toscana.it/wmsraster/com.rt.wms.RTmap/wms?map=wmsmorfologia'
LAYER = 'rt_morfologia.iddtm.1m.hs.irs'
PASSO_LAT = 1000 / 111_000  # gradi per 1 km in latitudine


def passo_lon(lat):
    return 1000 / (111_000 * math.cos(math.radians(lat)))


def scarica(lat, lon, dlon):
    q = {'service': 'WMS', 'request': 'GetMap', 'version': '1.3.0', 'layers': LAYER, 'styles': '',
         'crs': 'EPSG:4326', 'bbox': f'{lat:.5f},{lon:.5f},{lat + PASSO_LAT:.5f},{lon + dlon:.5f}',
         'width': 1000, 'height': 1000, 'format': 'image/png'}
    with urllib.request.urlopen(WMS + '&' + urllib.parse.urlencode(q), timeout=90) as r:
        return r.read()


def main():
    lat0, lon0 = float(sys.argv[1]), float(sys.argv[2])
    righe = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    colonne = int(sys.argv[4]) if len(sys.argv) > 4 else 3
    dlon = passo_lon(lat0)
    cartella = RADICE / 'dati' / 'tessere'
    cartella.mkdir(parents=True, exist_ok=True)
    for r in range(righe):
        for c in range(colonne):
            lat, lon = lat0 + r * PASSO_LAT, lon0 + c * dlon
            nome = cartella / f'{lat:.4f}_{lon:.4f}.png'
            if nome.exists():
                continue
            dati = scarica(lat, lon, dlon)
            nome.write_bytes(dati)
            print(nome.name, len(dati), 'VUOTA' if len(dati) < 20_000 else '')


if __name__ == '__main__':
    main()
