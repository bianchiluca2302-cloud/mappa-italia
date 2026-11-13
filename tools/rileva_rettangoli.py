"""Cerca strutture ad angoli retti (recinti, mura, terrazzamenti rettangolari) in un mosaico di quote.

Uso: python -I tools/rileva_rettangoli.py NOME [SOGLIA=0.55]
Legge dati/blocchi/NOME/quote.npy e scrive rettangoli.json (lat, lon, ortogonalita, direzione, energia).
Metodo: rilievo locale (quota meno sfondo sfocato a 20 m); in finestre di 2*FIN m si pesano gli orientamenti del
gradiente con la sua intensita. Con theta l'angolo, R4 = |media(w e^{4i theta})| e R2 = |media(w e^{2i theta})|:
una struttura ad angoli retti ha R4 alto e R2 basso (due direzioni a 90 gradi), un fosso o un versante ha R2 alto.
Punteggio = R4 - R2, solo dove l'energia del gradiente supera ENERGIA_MIN (per evitare il rumore piatto).
Non distingue coltivi e vigne (filari rettilinei): serve il filtro uso del suolo e le foto storiche.
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter, maximum_filter, uniform_filter

RADICE = Path(__file__).resolve().parent.parent
FIN = 30
ENERGIA_MIN = 0.03
PASSO = 1000


def mappa(z):
    z = np.where(np.isnan(z), np.nanmean(z) if np.isfinite(z).any() else 0, z)
    lrm = gaussian_filter(z, 1.0) - gaussian_filter(z, 20)
    gy, gx = np.gradient(lrm)
    w = np.hypot(gx, gy)
    th = np.arctan2(gy, gx)
    w = np.where(w > 0.05, w, 0)
    k = 2 * FIN + 1
    s = uniform_filter(w, k)
    c4, s4 = uniform_filter(w * np.cos(4 * th), k), uniform_filter(w * np.sin(4 * th), k)
    c2, s2 = uniform_filter(w * np.cos(2 * th), k), uniform_filter(w * np.sin(2 * th), k)
    r4 = np.hypot(c4, s4) / (s + 1e-9)
    r2 = np.hypot(c2, s2) / (s + 1e-9)
    punt = np.where(s > ENERGIA_MIN, r4 - r2, 0)
    dirz = np.degrees(np.arctan2(s4, c4) / 4) % 90
    return punt, dirz, s


def main():
    nome = sys.argv[1]
    soglia = float(sys.argv[2]) if len(sys.argv) > 2 else 0.55
    cart = RADICE / 'dati' / 'blocchi' / nome
    z = np.load(cart / 'quote.npy')
    info = json.loads((cart / 'quote.json').read_text(encoding='utf-8'))
    lato, righe = info['lato'], info['righe']
    lat_n = info['lat0'] + righe * info['dlat']
    out = []
    for y0 in range(0, z.shape[0], PASSO):
        for x0 in range(0, z.shape[1], PASSO):
            ya, xa = max(0, y0 - 2 * FIN), max(0, x0 - 2 * FIN)
            rit = z[ya:min(z.shape[0], y0 + PASSO + 2 * FIN), xa:min(z.shape[1], x0 + PASSO + 2 * FIN)]
            if np.isnan(rit).mean() > 0.5:
                continue
            p, d, e = mappa(rit)
            picchi = (p == maximum_filter(p, size=2 * FIN + 1)) & (p > soglia)
            for y, x in zip(*np.nonzero(picchi)):
                gy, gx = ya + y, xa + x
                if y0 <= gy < y0 + PASSO and x0 <= gx < x0 + PASSO:
                    out.append({'lat': round(lat_n - (gy + .5) / lato * info['dlat'], 6),
                                'lon': round(info['lon0'] + (gx + .5) / lato * info['dlon'], 6),
                                'ortogonalita': round(float(p[y, x]), 3), 'direzione': round(float(d[y, x]), 1),
                                'energia': round(float(e[y, x]), 3)})
    out.sort(key=lambda r: -r['ortogonalita'])
    (cart / 'rettangoli.json').write_text(json.dumps(out), encoding='utf-8')
    km2 = z.shape[0] * z.shape[1] / 1e6
    print(f'{nome}: {len(out)} punti sopra {soglia} su {km2:.0f} km2 ({len(out) / km2:.2f}/km2)')


if __name__ == '__main__':
    main()
