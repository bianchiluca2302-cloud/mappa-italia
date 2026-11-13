"""Scarica le QUOTE vere (DTM 1 m, float32, Toscana) di una finestra e ne ricava viste di rilievo.

Uso: python -I tools/rilievo_dtm.py LAT LON [LATO_M=300] [NOME=prova]
Il layer `rt_morfologia.iddtm.1m.irs` in formato image/tiff restituisce metri, non un'immagine ombreggiata.
Scrive dati/viste/NOME_rilievo.png: 2x2 con hillshade da 315 gradi (come il server), media di 8 direzioni,
rilievo locale (quota meno media mobile ~15 m) e apertura del cielo approssimata (SVF a 8 raggi).
Servono numpy, scipy e Pillow.
"""
import io
import math
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

RADICE = Path(__file__).resolve().parent.parent
WMS = 'https://www502.regione.toscana.it/wmsraster/com.rt.wms.RTmap/wms?map=wmsmorfologia'
LAYER = 'rt_morfologia.iddtm.1m.irs'


def quote(lat, lon, lato_m, tentativi=4, layer=LAYER):
    """Matrice di quote (m), righe dal nord, 1 pixel = 1 m, centrata su lat/lon."""
    dlat = lato_m / 2 / 111_000
    dlon = lato_m / 2 / (111_000 * math.cos(math.radians(lat)))
    q = {'service': 'WMS', 'request': 'GetMap', 'version': '1.3.0', 'layers': layer, 'styles': '',
         'crs': 'EPSG:4326', 'bbox': f'{lat - dlat:.6f},{lon - dlon:.6f},{lat + dlat:.6f},{lon + dlon:.6f}',
         'width': lato_m, 'height': lato_m, 'format': 'image/tiff'}
    rich = urllib.request.Request(WMS + '&' + urllib.parse.urlencode(q), headers={'User-Agent': 'Mozilla/5.0'})
    for t in range(tentativi):
        try:
            with urllib.request.urlopen(rich, timeout=90) as r:
                return np.array(Image.open(io.BytesIO(r.read())), dtype=np.float64)
        except Exception:
            if t == tentativi - 1:
                raise


def hillshade(z, azimut, altezza=40):
    gy, gx = np.gradient(z)
    pend = np.arctan(np.hypot(gx, gy))
    esp = np.arctan2(-gx, gy)
    az, al = math.radians(azimut), math.radians(altezza)
    return np.clip(np.sin(al) * np.cos(pend) + np.cos(al) * np.sin(pend) * np.cos(az - esp), 0, 1)


def svf(z, raggio=20, direzioni=8):
    """Apertura del cielo approssimata: 1 - media del seno dell'angolo d'orizzonte massimo sui raggi."""
    h, w = z.shape
    ang = np.zeros_like(z)
    for k in range(direzioni):
        a = 2 * math.pi * k / direzioni
        dx, dy = math.cos(a), math.sin(a)
        mx = np.zeros_like(z)
        for d in range(1, raggio + 1):
            sx, sy = int(round(dx * d)), int(round(dy * d))
            sh = np.roll(np.roll(z, -sy, 0), -sx, 1)
            mx = np.maximum(mx, np.arctan((sh - z) / d))
        ang += np.sin(np.clip(mx, 0, None))
    return 1 - ang / direzioni


def norma(a, lo=2, hi=98):
    p, q = np.percentile(a, [lo, hi])
    return (np.clip((a - p) / (q - p + 1e-9), 0, 1) * 255).astype(np.uint8)


def foglio(lat, lon, lato, uscita):
    """Scrive il 2x2 (una luce, 8 luci, rilievo locale, SVF) di una finestra `lato` m centrata su lat/lon."""
    z = quote(lat, lon, lato)
    h1 = hillshade(z, 315)
    h8 = np.mean([hillshade(z, a) for a in range(0, 360, 45)], axis=0)
    lrm = z - gaussian_filter(z, 15)
    cielo = svf(z)
    viste = [norma(h1), norma(h8), norma(lrm, 5, 95), norma(cielo, 5, 99)]
    f = lato * 2
    im = Image.new('L', (f, f))
    for i, v in enumerate(viste):
        im.paste(Image.fromarray(v), ((i % 2) * lato, (i // 2) * lato))
    im.resize((f * 2, f * 2), Image.LANCZOS).save(uscita)
    return z


def main():
    lat, lon = float(sys.argv[1]), float(sys.argv[2])
    lato = int(sys.argv[3]) if len(sys.argv) > 3 else 300
    nome = sys.argv[4] if len(sys.argv) > 4 else 'prova'
    uscita = RADICE / 'dati' / 'viste' / f'{nome}_rilievo.png'
    z = foglio(lat, lon, lato, uscita)
    print(uscita, f'quote {z.min():.1f}-{z.max():.1f} m')


if __name__ == '__main__':
    main()
