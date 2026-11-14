"""Verifica storica di punti: crops 600x600 (finestra 300 m) da ortofoto 1954..2013, DTM, CTR 10k, IGM 25k.
Uso: python -I tools/verifica_storica.py   (punti e coordinate stanno nel file locale ignorato dal git
dati/blocchi/verifica/punti.json: {"A": [lat, lon, raggio_m], ...}; se manca, vengono letti dalla riga di comando
come ID=lat,lon,raggio). Output in dati/blocchi/verifica/storica/.
"""
import io
import json
import math
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw

RADICE = Path(__file__).resolve().parent.parent
VER = RADICE / 'dati' / 'blocchi' / 'verifica'
OUT = VER / 'storica'
RASTER = 'https://www502.regione.toscana.it/wmsraster/com.rt.wms.RTmap/wms?map='
CTR = 'https://www502.regione.toscana.it/ows_ctr/com.rt.wms.RTmap/ows?map=owsctr'
VISTE = [  # nome, base url + mappa, layer
    ('ofc54', RASTER + 'wmsofc', 'rt_ofc.10k54'), ('ofc78', RASTER + 'wmsofc', 'rt_ofc.10k78'),
    ('ofc88', RASTER + 'wmsofc', 'rt_ofc.10k88'), ('ofc96', RASTER + 'wmsofc', 'rt_ofc.10k96'),
    ('ofc13', RASTER + 'wmsofc', 'rt_ofc.10k13'),
    ('dtm', RASTER + 'wmsmorfologia', 'rt_morfologia.iddtm.1m.hs.irs'),
    ('igm25', CTR, 'rt_ctr.igm.q25'), ('ctr10k', CTR, 'rt_ctr.10k'), ('ctr_impianto', CTR, 'rt_ctr.10k_impianto'),
]
META = 150


def scarica(base, layer, lat, lon, tentativi=3):
    dlat = META / 111_000
    dlon = META / (111_000 * math.cos(math.radians(lat)))
    q = {'service': 'WMS', 'request': 'GetMap', 'version': '1.3.0', 'layers': layer, 'styles': '',
         'crs': 'EPSG:4326', 'bbox': f'{lat - dlat:.6f},{lon - dlon:.6f},{lat + dlat:.6f},{lon + dlon:.6f}',
         'width': 600, 'height': 600, 'format': 'image/png'}
    for t in range(tentativi):
        try:
            with urllib.request.urlopen(base + '&' + urllib.parse.urlencode(q), timeout=90) as r:
                im = Image.open(io.BytesIO(r.read())).convert('RGBA')
                fondo = Image.new('RGBA', im.size, 'white')
                return Image.alpha_composite(fondo, im).convert('RGB')
        except Exception as e:
            if t == tentativi - 1:
                print('  fallito', layer, e)
    return None


def punti():
    f = VER / 'punti.json'
    if len(sys.argv) > 1:
        d = {}
        for a in sys.argv[1:]:
            k, v = a.split('=')
            d[k] = [float(x) for x in v.split(',')]
        return d
    return json.loads(f.read_text(encoding='utf-8'))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for pid, (lat, lon, raggio) in punti().items():
        with ThreadPoolExecutor(5) as ex:
            imgs = list(ex.map(lambda v: scarica(v[1], v[2], lat, lon), VISTE))
        ok = []
        for (nome, _, _), im in zip(VISTE, imgs):
            if im is None:
                continue
            # immagine vuota (tutta bianca/uniforme) = annata non disponibile
            if im.convert('L').getextrema()[1] - im.convert('L').getextrema()[0] < 4:
                print(pid, nome, 'vuota')
                continue
            im.save(OUT / f'{pid}_{nome}.png')
            ok.append((nome, im))
            print(pid, nome, 'ok')
        if not ok:
            continue
        # mosaico: 3 colonne, cerchio sul raggio indicato, etichette
        cols = 3
        righe = math.ceil(len(ok) / cols)
        mos = Image.new('RGB', (cols * 600, righe * 600), 'white')
        r_px = raggio / (2 * META) * 600
        for i, (nome, im) in enumerate(ok):
            im = im.copy()
            d = ImageDraw.Draw(im)
            d.ellipse([300 - r_px, 300 - r_px, 300 + r_px, 300 + r_px], outline=(255, 0, 0), width=2)
            d.rectangle([0, 0, 150, 22], fill='black')
            d.text((6, 5), f'{pid} {nome}', fill='white')
            mos.paste(im, ((i % cols) * 600, (i // cols) * 600))
        mos.save(OUT / f'{pid}_mosaico.png')


if __name__ == '__main__':
    main()
