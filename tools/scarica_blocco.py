"""Scarica un blocco rettangolare di tessere LiDAR (DTM 1 m ombreggiato, Toscana) in parallelo.

Uso: python -I tools/scarica_blocco.py NOME LAT_SUD LON_OVEST RIGHE COLONNE
Le tessere (1 km x 1 km, 1000x1000 px) vanno in dati/blocchi/<NOME>/r<riga>_c<colonna>.png (riga 0 = sud, colonna 0 = ovest).
dati/blocchi/<NOME>/blocco.json tiene l'origine, il passo e l'elenco delle tessere senza dati (file sotto 20 kB).
Rilanciandolo salta le tessere gia scaricate. Ogni tessera ha una scritta di fonte lungo il bordo sinistro (~25 px).
"""
import json
import math
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
WMS = 'https://www502.regione.toscana.it/wmsraster/com.rt.wms.RTmap/wms?map=wmsmorfologia'
LAYER = 'rt_morfologia.iddtm.1m.hs.irs'
DLAT = 1000 / 111_000


def scarica(lat, lon, dlon, tentativi=4):
    q = {'service': 'WMS', 'request': 'GetMap', 'version': '1.3.0', 'layers': LAYER, 'styles': '',
         'crs': 'EPSG:4326', 'bbox': f'{lat:.5f},{lon:.5f},{lat + DLAT:.5f},{lon + dlon:.5f}',
         'width': 1000, 'height': 1000, 'format': 'image/png'}
    for t in range(tentativi):
        try:
            with urllib.request.urlopen(WMS + '&' + urllib.parse.urlencode(q), timeout=90) as r:
                return r.read()
        except Exception:
            if t == tentativi - 1:
                raise


def main():
    nome = sys.argv[1]
    lat0, lon0, righe, colonne = float(sys.argv[2]), float(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
    dlon = 1000 / (111_000 * math.cos(math.radians(lat0 + righe * DLAT / 2)))
    cartella = RADICE / 'dati' / 'blocchi' / nome
    cartella.mkdir(parents=True, exist_ok=True)

    def uno(rc):
        r, c = rc
        f = cartella / f'r{r:02d}_c{c:02d}.png'
        if not f.exists():
            f.write_bytes(scarica(lat0 + r * DLAT, lon0 + c * dlon, dlon))
        return rc, f.stat().st_size

    with ThreadPoolExecutor(8) as ex:
        esiti = list(ex.map(uno, [(r, c) for r in range(righe) for c in range(colonne)]))
    vuote = [list(rc) for rc, n in esiti if n < 20_000]
    (cartella / 'blocco.json').write_text(json.dumps(
        {'nome': nome, 'lat0': lat0, 'lon0': lon0, 'dlat': DLAT, 'dlon': dlon, 'righe': righe, 'colonne': colonne,
         'vuote': vuote}), encoding='utf-8')
    print(f'{nome}: {len(esiti)} tessere, {len(vuote)} vuote')


if __name__ == '__main__':
    main()
