"""Scansione a macchia d'olio: blocchi 6x6 km attorno a un centro, dal centro verso l'esterno, con pipeline_blocco.py.

Uso: python -I tools/scansione_spirale.py PREFISSO LAT LON ANELLI [MAX_FOGLI=24] [DA_COLONNA_EST]
Con DA_COLONNA_EST (es. 3) scansiona solo le colonne a est da quella in poi, fino a ANELLI, una colonna alla volta.
Il blocco 0 e centrato su LAT,LON; l'anello k ha i blocchi a distanza k (in blocchi) dal centro, dal piu vicino al piu
lontano. Per ogni blocco scarica le quote (scarica_quote.py), salta quelli con meno del 30% di dato (mare, fuori
Toscana) e poi lancia la pipeline. Blocchi gia fatti (pipeline.json) si saltano: si puo rilanciare. Stato in
dati/blocchi/spirale_PREFISSO.json (ignorato dal git: contiene coordinate).
"""
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np

QUI = Path(__file__).resolve().parent
BLOCCHI = QUI.parent / 'dati' / 'blocchi'
LATO_KM = 6


def main():
    pref, lat, lon, anelli = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), int(sys.argv[4])
    fogli = sys.argv[5] if len(sys.argv) > 5 else '24'
    dlat = LATO_KM / 111
    dlon = LATO_KM / (111 * math.cos(math.radians(lat)))
    est = int(sys.argv[6]) if len(sys.argv) > 6 else None  # solo colonne a est, da J=est in poi, una colonna alla volta
    celle = sorted(((i, j) for i in range(-anelli, anelli + 1) for j in range(-anelli, anelli + 1) if est is None or j >= est),
                   key=lambda c: (max(abs(c[0]), abs(c[1])), math.hypot(*c)) if est is None else (c[1], abs(c[0])))
    stato_f = BLOCCHI / f'spirale_{pref}.json'
    stato = json.loads(stato_f.read_text()) if stato_f.exists() else {}
    for i, j in celle:
        nome = f'{pref}_{i}_{j}'.replace('-', 'm')
        sud, ovest = lat + (i - 0.5) * dlat, lon + (j - 0.5) * dlon
        cart = BLOCCHI / nome
        if (cart / 'pipeline.json').exists():
            stato[nome] = stato.get(nome, 'fatto')
            continue
        if not (cart / 'quote.npy').exists():
            subprocess.run([sys.executable, '-I', str(QUI / 'scarica_quote.py'), nome, f'{sud:.5f}', f'{ovest:.5f}',
                            str(LATO_KM), str(LATO_KM)], check=False)
        try:
            dato = float(np.isfinite(np.load(cart / 'quote.npy')).mean())
        except Exception:
            dato = 0.0
        if dato < 0.3:
            stato[nome] = f'saltato (dato {dato:.0%})'
        else:
            r = subprocess.run([sys.executable, '-I', str(QUI / 'pipeline_blocco.py'), nome, f'{sud:.5f}',
                                f'{ovest:.5f}', str(LATO_KM), str(LATO_KM), fogli], check=False)
            stato[nome] = 'fatto' if r.returncode == 0 else f'errore {r.returncode}'
        stato[nome + '_origine'] = [round(sud, 5), round(ovest, 5)]
        stato_f.write_text(json.dumps(stato, indent=1))
        print(nome, stato[nome], flush=True)


main()
