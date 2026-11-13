"""Indicatori di uso del suolo moderno attorno a un punto: piatto interno (laghetti, piazzali), edifici, bosco, coltivi.

Uso come modulo: indicatori(lat, lon, raggio) -> dict. Da riga di comando: python -I tools/uso_suolo.py candidati
(tabella per tutti i candidati di dati/scansione.json, per tarare le soglie).
Fonti: DTM e DSM 2021 in quote (WMS Geoscopio, image/tiff), ortofoto 2013 (RGB) e 1954 (grigio).
Indicatori, calcolati nel cerchio di raggio `raggio` attorno al punto:
  piano     deviazione standard (m) del DTM dentro 0,5 r tolto il piano medio: ~0 per specchi d'acqua e piazzali
  chioma    frazione di pixel con DSM-DTM > 2,5 m dentro 1,3 r (alberi o edifici)
  liscio    deviazione standard di DSM-DTM nei pixel alti: bassa = tetti, alta = chioma
  acqua13   frazione di pixel 2013 dentro 0,5 r scuri e non verdi (azzurro/grigio-verde)
  verde13   indice di verde 2013 dentro 1,3 r
  lum54     luminosita media 1954 dentro 1,3 r (bosco = scuro)
  tess54    deviazione standard locale della luminosita 1954 (bosco = alta, campo arato = bassa e a righe)
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rilievo_dtm import quote  # noqa: E402

RADICE = Path(__file__).resolve().parent.parent
BASE = 'https://www502.regione.toscana.it/wmsraster/com.rt.wms.RTmap/wms?map='
LATO = 300
DSM = 'rt_morfologia.iddsm2021.1m.rt'


def ortofoto(layer, lat, lon, tentativi=4):
    dlat = LATO / 2 / 111_000
    dlon = LATO / 2 / (111_000 * math.cos(math.radians(lat)))
    q = {'service': 'WMS', 'request': 'GetMap', 'version': '1.3.0', 'layers': layer, 'styles': '',
         'crs': 'EPSG:4326', 'bbox': f'{lat - dlat:.6f},{lon - dlon:.6f},{lat + dlat:.6f},{lon + dlon:.6f}',
         'width': LATO, 'height': LATO, 'format': 'image/png'}
    for t in range(tentativi):
        try:
            with urllib.request.urlopen(BASE + 'wmsofc&' + urllib.parse.urlencode(q), timeout=90) as r:
                return np.array(Image.open(io.BytesIO(r.read())).convert('RGB'), dtype=np.float64)
        except Exception:
            if t == tentativi - 1:
                raise


def indicatori(lat, lon, raggio):
    with ThreadPoolExecutor(4) as ex:
        f = [ex.submit(quote, lat, lon, LATO), ex.submit(quote, lat, lon, LATO, 4, DSM),
             ex.submit(ortofoto, 'rt_ofc.10k13', lat, lon), ex.submit(ortofoto, 'rt_ofc.10k54', lat, lon)]
        dtm, dsm, o13, o54 = (x.result() for x in f)
    yy, xx = np.mgrid[:LATO, :LATO]
    d = np.hypot(yy - LATO / 2, xx - LATO / 2)
    dentro, area = d < 0.5 * raggio, d < 1.3 * raggio
    # piano: residuo del DTM dopo un piano ai minimi quadrati
    A = np.c_[xx[dentro], yy[dentro], np.ones(dentro.sum())]
    z = dtm[dentro]
    piano = float(np.std(z - A @ np.linalg.lstsq(A, z, rcond=None)[0]))
    ndsm = dsm - dtm
    alto = area & (ndsm > 2.5)
    r, g, b = o13[..., 0], o13[..., 1], o13[..., 2]
    lum13 = (r + g + b) / 3
    verde = (g - (r + b) / 2) / (r + g + b + 1)
    acqua = dentro & (lum13 < 110) & (verde < 0.04)
    l54 = o54.mean(axis=2)
    gy, gx = np.gradient(l54)
    return {'piano': round(piano, 3), 'chioma': round(float(alto.sum() / area.sum()), 2),
            'liscio': round(float(ndsm[alto].std()) if alto.sum() > 20 else -1, 2),
            'acqua13': round(float(acqua.sum() / dentro.sum()), 2), 'verde13': round(float(verde[area].mean()), 3),
            'lum54': round(float(l54[area].mean()), 1), 'tess54': round(float(np.hypot(gx, gy)[area].mean()), 1)}


def classe(e):
    """'piatto' (laghetto, piazzale: piano < 0,1 m), poi 'bosco' (chioma >= 50%) o 'aperto' (campi, prati)."""
    if e['piano'] < 0.1:
        return 'piatto'
    return 'bosco' if e['chioma'] >= 0.5 else 'aperto'


def main():
    d = json.loads((RADICE / 'dati' / 'scansione.json').read_text(encoding='utf-8'))
    op = json.loads((RADICE / 'dati' / 'blocchi' / 'seconda_opinione_candidati.json').read_text(encoding='utf-8'))
    raggi = {x['id']: (x['rilevatore'] or {}).get('raggio') or 20 for x in op}
    cand = d.get('candidati', d)
    with ThreadPoolExecutor(3) as ex:
        esiti = list(ex.map(lambda c: indicatori(c['lat'], c['lon'], raggi.get(c['id'], 20)), cand))
    out = []
    for c, e in zip(cand, esiti):
        out.append({'id': c['id'], 'esito': c['affidabilita'], 'verifica': c.get('verifica', '')[:80], **e})
        print(f"{c['id']:4s} {c['affidabilita'][:14]:14s}", {k: v for k, v in e.items()})
    conto = {}
    for o in out:
        k = (classe(o), 'positivo' if o['esito'] in ('gia noto', 'da verificare - media') else
             'bassa' if o['esito'].startswith('da verificare') else 'scartato')
        conto[k] = conto.get(k, 0) + 1
    print('classe x esito:', dict(sorted(conto.items())))
    (RADICE / 'dati' / 'blocchi' / 'uso_suolo_candidati.json').write_text(json.dumps(out), encoding='utf-8')


if __name__ == '__main__':
    main()
