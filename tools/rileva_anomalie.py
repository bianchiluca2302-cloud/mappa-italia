"""Cerca strutture circolari (tumuli, recinti ad anello, fossati) in un mosaico di quote, con punteggio.

Uso: python -I tools/rileva_anomalie.py NOME [SOGLIA=0.5]
Legge dati/blocchi/NOME/quote.npy (da scarica_quote.py) e scrive dati/blocchi/NOME/rilevati.json:
punti con lat, lon, raggio (m), punteggio, polarita (tumulo/conca), altezza (m).
Metodo: rilievo locale (quota meno sfondo sfocato); stadio 1 = voto di Hough sul gradiente, raggi 10-45 m, per
trovare i candidati; stadio 2 = si campiona l'anello su 48 angoli e il punteggio e il 10 percentile del dislivello
interno-esterno diviso per la ruvidita locale del terreno (ritrova V11 al 99,7 percentile: i valori alti
richiedono un anello regolare e netto su quasi tutta la circonferenza). Candidati vicini si fondono tenendo il
migliore. Non scarta strade, cave, edifici: lo fara il filtro successivo.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates, maximum_filter, uniform_filter

RADICE = Path(__file__).resolve().parent.parent
RAGGI = [10, 13, 16, 20, 25, 31, 38, 45]
MARGINE = 80
PEND_MIN = 0.10
ANGOLI = np.linspace(0, 2 * math.pi, 48, endpoint=False)


def candidati(lrm):
    """Stadio 1: (voti, y, x, raggio, segno) dei massimi della mappa dei voti, per ogni raggio e polarita."""
    h, w = lrm.shape
    gy, gx = np.gradient(lrm)
    mod = np.hypot(gx, gy)
    ys, xs = np.nonzero(mod > PEND_MIN)
    dx, dy = gx[ys, xs] / mod[ys, xs], gy[ys, xs] / mod[ys, xs]
    trovati = []
    for r in RAGGI:
        for segno in (1, -1):
            ty = np.rint(ys + segno * r * dy).astype(int)
            tx = np.rint(xs + segno * r * dx).astype(int)
            ok = (ty >= 0) & (ty < h) & (tx >= 0) & (tx < w)
            acc = np.bincount(ty[ok] * w + tx[ok], minlength=h * w).reshape(h, w).astype(np.float32)
            v = gaussian_filter(acc, 1.5) * (2 * math.pi * 1.5 ** 2) / (2 * math.pi * r)
            for y, x in zip(*np.nonzero((v == maximum_filter(v, size=2 * r + 1)) & (v > 0.5))):
                trovati.append((float(v[y, x]), y, x, r, segno))
    return trovati


def coerenza(lrm, y, x, r):
    """Coerenza di orientamento del gradiente nel disco 1,5 r (0 = anello/isotropo, 1 = fosso o versante lineare)."""
    gy, gx = np.gradient(lrm)
    out = np.zeros(len(y))
    for rr in set(r.tolist()):
        w = int(3 * rr) | 1
        jxx, jyy, jxy = (uniform_filter(a, w) for a in (gx * gx, gy * gy, gx * gy))
        m = r == rr
        a, b, c = jxx[y[m], x[m]], jyy[y[m], x[m]], jxy[y[m], x[m]]
        out[m] = np.sqrt((a - b) ** 2 + 4 * c ** 2) / (a + b + 1e-9)
    return out


def blocco(z):
    """Lista di (punteggio, y, x, raggio, segno, altezza, regolarita, coerenza) fusa, per un ritaglio di quote."""
    z = np.where(np.isnan(z), np.nanmean(z) if np.isfinite(z).any() else 0, z)
    lrm = gaussian_filter(z, 1.5) - gaussian_filter(z, 20)
    rough = np.sqrt(gaussian_filter(lrm ** 2, 60)) + 0.05
    c = np.array(candidati(lrm))
    if not len(c):
        return []
    y, x, r, s = c[:, 1], c[:, 2], c[:, 3], c[:, 4]
    sen, cos = np.sin(ANGOLI)[None], np.cos(ANGOLI)[None]
    dentro = map_coordinates(lrm, [(y[:, None] + .75 * r[:, None] * sen), (x[:, None] + .75 * r[:, None] * cos)], order=1)
    fuori = map_coordinates(lrm, [(y[:, None] + 1.3 * r[:, None] * sen), (x[:, None] + 1.3 * r[:, None] * cos)], order=1)
    d = s[:, None] * (dentro - fuori)
    punt = np.percentile(d, 10, axis=1) / rough[y.astype(int), x.astype(int)]
    alt = np.median(d, axis=1)
    reg = d.mean(axis=1) / (d.std(axis=1) + 1e-6)
    coe = coerenza(lrm, y.astype(int), x.astype(int), r.astype(int))
    tenuti = []
    for i in np.argsort(-punt):
        if not any(math.hypot(y[i] - t[1], x[i] - t[2]) < max(r[i], t[3]) for t in tenuti):
            tenuti.append((float(punt[i]), int(y[i]), int(x[i]), int(r[i]), int(s[i]), float(alt[i]), float(reg[i]), float(coe[i])))
    return tenuti


def main():
    nome = sys.argv[1]
    soglia = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5
    cart = RADICE / 'dati' / 'blocchi' / nome
    z = np.load(cart / 'quote.npy')
    info = json.loads((cart / 'quote.json').read_text(encoding='utf-8'))
    lato, righe = info['lato'], info['righe']
    lat_nord = info['lat0'] + righe * info['dlat']
    punti = []
    for y0 in range(0, z.shape[0], lato):
        for x0 in range(0, z.shape[1], lato):
            ya, xa = max(0, y0 - MARGINE), max(0, x0 - MARGINE)
            ritaglio = z[ya:min(z.shape[0], y0 + lato + MARGINE), xa:min(z.shape[1], x0 + lato + MARGINE)]
            if np.isnan(ritaglio).mean() > 0.5:
                continue
            for p, y, x, r, segno, alt, reg, coe in blocco(ritaglio):
                gy, gx = ya + y, xa + x
                if p >= soglia and y0 <= gy < y0 + lato and x0 <= gx < x0 + lato:
                    punti.append({'lat': round(lat_nord - (gy + 0.5) / lato * info['dlat'], 6),
                                  'lon': round(info['lon0'] + (gx + 0.5) / lato * info['dlon'], 6),
                                  'raggio': r, 'punteggio': round(p, 3),
                                  'polarita': 'tumulo' if segno > 0 else 'conca', 'altezza': round(alt, 2), 'regolarita': round(reg, 2),
                                  'coerenza': round(coe, 3)})
    punti.sort(key=lambda p: (-p['punteggio'], -p['altezza']))
    (cart / 'rilevati.json').write_text(json.dumps(punti), encoding='utf-8')
    km2 = z.shape[0] * z.shape[1] / 1e6
    print(f'{nome}: {len(punti)} punti sopra {soglia} su {km2:.0f} km2 ({len(punti) / km2:.2f}/km2)')
    for p in punti[:10]:
        print(p)


if __name__ == '__main__':
    main()
