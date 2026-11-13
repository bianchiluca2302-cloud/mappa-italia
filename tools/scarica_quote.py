"""Scarica un mosaico di QUOTE (DTM 1 m, float32, Toscana) in dati/blocchi/NOME/quote.npy.

Uso: python -I tools/scarica_quote.py NOME LAT_SUD LON_OVEST RIGHE COLONNE
Come scarica_blocco.py (tessere 1 km, riga 0 = sud) ma il risultato e un'unica matrice (righe dal nord, 1 px = 1 m)
e il dato sono i metri, non un'immagine; dove manca il dato c'e NaN. quote.json tiene origine e passo.
"""
import io
import json
import math
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image

RADICE = Path(__file__).resolve().parent.parent
WMS = 'https://www502.regione.toscana.it/wmsraster/com.rt.wms.RTmap/wms?map=wmsmorfologia'
LAYER = 'rt_morfologia.iddtm.1m.irs'
DLAT = 1000 / 111_000
LATO = 1000


def tessera(lat, lon, dlon, tentativi=4):
    q = {'service': 'WMS', 'request': 'GetMap', 'version': '1.3.0', 'layers': LAYER, 'styles': '',
         'crs': 'EPSG:4326', 'bbox': f'{lat:.6f},{lon:.6f},{lat + DLAT:.6f},{lon + dlon:.6f}',
         'width': LATO, 'height': LATO, 'format': 'image/tiff'}
    rich = urllib.request.Request(WMS + '&' + urllib.parse.urlencode(q), headers={'User-Agent': 'Mozilla/5.0'})
    for t in range(tentativi):
        try:
            with urllib.request.urlopen(rich, timeout=90) as r:
                a = np.array(Image.open(io.BytesIO(r.read())), dtype=np.float32)
            a[a <= 0] = np.nan
            return a
        except Exception:
            if t == tentativi - 1:
                raise


def main():
    nome = sys.argv[1]
    lat0, lon0, righe, colonne = float(sys.argv[2]), float(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
    dlon = 1000 / (111_000 * math.cos(math.radians(lat0 + righe * DLAT / 2)))
    mosaico = np.full((righe * LATO, colonne * LATO), np.nan, dtype=np.float32)

    def uno(rc):
        r, c = rc
        a = tessera(lat0 + r * DLAT, lon0 + c * dlon, dlon)
        y0 = (righe - 1 - r) * LATO
        mosaico[y0:y0 + LATO, c * LATO:(c + 1) * LATO] = a

    with ThreadPoolExecutor(6) as ex:
        list(ex.map(uno, [(r, c) for r in range(righe) for c in range(colonne)]))
    cartella = RADICE / 'dati' / 'blocchi' / nome
    cartella.mkdir(parents=True, exist_ok=True)
    np.save(cartella / 'quote.npy', mosaico)
    (cartella / 'quote.json').write_text(json.dumps(
        {'nome': nome, 'lat0': lat0, 'lon0': lon0, 'dlat': DLAT, 'dlon': dlon, 'righe': righe,
         'colonne': colonne, 'lato': LATO}), encoding='utf-8')
    print(f'{nome}: {mosaico.shape}, vuoto {np.isnan(mosaico).mean():.1%}')


if __name__ == '__main__':
    main()
