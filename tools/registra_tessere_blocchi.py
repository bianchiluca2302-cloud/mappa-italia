"""Aggiunge a dati/scansione.json le tessere da 1 km dei blocchi della pipeline (celle con almeno il 50% di quote).

Uso: python -I tools/registra_tessere_blocchi.py PREFISSO [--scrivi]
Senza --scrivi mostra solo quante tessere nuove ci sarebbero. Poi lanciare registra_scansione.py per rigenerare scansione.js.
Salta le celle gia registrate (entro 0,3 di cella da una tessera esistente) e i blocchi senza pipeline.json.
"""
import json
import sys
from pathlib import Path

import numpy as np

RADICE = Path(__file__).resolve().parent.parent
D = RADICE / 'dati'
ESITO = 'visto (rilevatore automatico su quote DTM 1 m, blocco spirale Livorno)'


def main():
    pref = sys.argv[1]
    scrivi = '--scrivi' in sys.argv
    reg = json.loads((D / 'scansione.json').read_text(encoding='utf-8'))
    esistenti = {(round(t['lat'] / 0.009009), round(t['lon'] / 0.0123)) for t in reg['tessere']}
    nuove, blocchi = [], 0
    for cart in sorted((D / 'blocchi').glob(pref + '_*')):
        if not (cart / 'pipeline.json').exists() or not (cart / 'quote.npy').exists():
            continue
        q = json.loads((cart / 'quote.json').read_text(encoding='utf-8'))
        quote = np.load(cart / 'quote.npy', mmap_mode='r')
        lato, righe, colonne = q['lato'], q['righe'], q['colonne']
        blocchi += 1
        for r in range(righe):  # r = 0 a sud, le righe della matrice partono dal nord
            for c in range(colonne):
                cella = quote[(righe - 1 - r) * lato:(righe - r) * lato, c * lato:(c + 1) * lato]
                if np.isfinite(cella).mean() < 0.5:
                    continue
                lat, lon = round(q['lat0'] + r * q['dlat'], 4), round(q['lon0'] + c * q['dlon'], 4)
                chiave = (round(lat / 0.009009), round(lon / 0.0123))
                if chiave in esistenti:
                    continue
                esistenti.add(chiave)
                nuove.append({'lat': lat, 'lon': lon, 'esito': ESITO})
    print(f'{blocchi} blocchi, {len(nuove)} tessere nuove (ora {len(reg["tessere"])})')
    if scrivi:
        reg['tessere'] += nuove
        (D / 'scansione.json').write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding='utf-8')
        print('scritto dati/scansione.json')


main()
