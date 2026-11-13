"""Misura quanti siti noti (OSM e Wikidata) il rilevatore ritrova, per varianti di filtro.

Uso: python -I tools/valuta_rilevatore.py NOME [NOME...]
Per ogni blocco con rilevati.json e quote.npy conta i siti catalogati su terreno con dato e quanti hanno un punto
del rilevatore entro DIST_M m, per varianti di soglia su punteggio e coerenza (filtro fossi). Stampa anche i punti
per km2 della variante: un buon filtro alza la sensibilita relativa tenendo bassa la densita.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

RADICE = Path(__file__).resolve().parent.parent
DIST_M = 60
VARIANTI = {'tutti': lambda p: True,
            'coer<=0.5': lambda p: p['coerenza'] <= 0.5,
            'coer<=0.35': lambda p: p['coerenza'] <= 0.35,
            'coer<=0.5 e punt>=0.8': lambda p: p['coerenza'] <= 0.5 and p['punteggio'] >= 0.8}


def siti():
    out = []
    for f in ('siti-noti.json', 'siti-wikidata.json'):
        out += json.loads((RADICE / 'dati' / f).read_text(encoding='utf-8'))
    return out


def main():
    catalogo = siti()
    tot = {k: [0, 0, 0.0, 0] for k in VARIANTI}  # trovati, siti, km2, punti
    for nome in sys.argv[1:]:
        cart = RADICE / 'dati' / 'blocchi' / nome
        info = json.loads((cart / 'quote.json').read_text(encoding='utf-8'))
        z = np.load(cart / 'quote.npy', mmap_mode='r')
        punti = json.loads((cart / 'rilevati.json').read_text(encoding='utf-8'))
        lat_n = info['lat0'] + info['righe'] * info['dlat']
        dentro = []
        for s in catalogo:
            y = int((lat_n - s['lat']) / info['dlat'] * info['lato'])
            x = int((s['lon'] - info['lon0']) / info['dlon'] * info['lato'])
            if 0 <= y < z.shape[0] and 0 <= x < z.shape[1] and not np.isnan(z[y, x]):
                dentro.append(s)
        km2 = float(np.isfinite(z[::10, ::10]).mean()) * z.shape[0] * z.shape[1] / 1e6
        print(f'== {nome}: {len(dentro)} siti su terreno con dato, {km2:.1f} km2, {len(punti)} punti')
        for k, f in VARIANTI.items():
            sel = [p for p in punti if f(p)]
            trovati = sum(any(math.hypot((p['lat'] - s['lat']) * 111_000,
                                         (p['lon'] - s['lon']) * 111_000 * math.cos(math.radians(s['lat']))) < DIST_M
                              for p in sel) for s in dentro)
            for i, v in enumerate((trovati, len(dentro), km2, len(sel))):
                tot[k][i] += v
            print(f'   {k:24s} trovati {trovati}/{len(dentro)}  {len(sel) / km2:5.1f} punti/km2')
    print('== TOTALE')
    for k, (t, n, km2, pt) in tot.items():
        casuale = 1 - math.exp(-pt / km2 * math.pi * DIST_M ** 2 / 1e6) if km2 else 0
        print(f'   {k:24s} trovati {t}/{n} ({100 * t / max(n, 1):.0f}%)  {pt / max(km2, 1e-9):5.1f} punti/km2  '
              f'atteso a caso ~{100 * casuale:.0f}%')


if __name__ == '__main__':
    main()
