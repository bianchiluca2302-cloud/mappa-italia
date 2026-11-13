"""Scarica quattro viste di un candidato (finestra 300 m x 300 m, 600x600 px) in dati/viste/<ID>_<vista>.png.

Uso: python -I tools/vista_candidato.py ID [ID...]     (gli ID sono in dati/scansione.json)
Viste: dtm (rilievo LiDAR ombreggiato), dsm (rilievo da immagini 2021), ofc13 (foto aerea 2013), ofc54 (foto aerea 1954).
"""
import json
import math
import sys
import urllib.parse
import urllib.request
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
BASE = 'https://www502.regione.toscana.it/wmsraster/com.rt.wms.RTmap/wms?map='
VISTE = {
    'dtm': ('wmsmorfologia', 'rt_morfologia.iddtm.1m.hs.irs'),
    'dsm': ('wmsmorfologia', 'rt_morfologia.iddsm2021.1m.hs.rt'),
    'ofc13': ('wmsofc', 'rt_ofc.10k13'),
    'ofc54': ('wmsofc', 'rt_ofc.10k54'),
}
META = 150  # mezza finestra in metri


def scarica(mappa, layer, lat, lon):
    dlat = META / 111_000
    dlon = META / (111_000 * math.cos(math.radians(lat)))
    q = {'service': 'WMS', 'request': 'GetMap', 'version': '1.3.0', 'layers': layer, 'styles': '',
         'crs': 'EPSG:4326', 'bbox': f'{lat - dlat:.6f},{lon - dlon:.6f},{lat + dlat:.6f},{lon + dlon:.6f}',
         'width': 600, 'height': 600, 'format': 'image/png'}
    with urllib.request.urlopen(BASE + mappa + '&' + urllib.parse.urlencode(q), timeout=90) as r:
        return r.read()


def main():
    reg = json.loads((RADICE / 'dati' / 'scansione.json').read_text(encoding='utf-8'))
    cand = {c['id']: c for c in reg['candidati']}
    out = RADICE / 'dati' / 'viste'
    out.mkdir(parents=True, exist_ok=True)
    for cid in sys.argv[1:]:
        c = cand[cid]
        for nome, (mappa, layer) in VISTE.items():
            dati = scarica(mappa, layer, c['lat'], c['lon'])
            (out / f'{cid}_{nome}.png').write_bytes(dati)
            print(cid, nome, len(dati))


if __name__ == '__main__':
    main()
