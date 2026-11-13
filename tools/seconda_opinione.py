"""Dice cosa ne pensa il rilevatore di punti gia segnalati (candidati di scansione.json o righe di punti_segnalati.txt).

Uso: python -I tools/seconda_opinione.py candidati        -> tutti i candidati di dati/scansione.json con il loro esito
     python -I tools/seconda_opinione.py punti            -> le righe di dati/blocchi/punti_segnalati.txt
Per ogni punto scarica 500 m di quote, applica rileva_anomalie.blocco e prende la struttura piu vicina (entro MAX_M m):
punteggio, coerenza, raggio e percentile del punteggio tra tutte le strutture della finestra.
Scrive dati/blocchi/seconda_opinione_<modo>.json (ignorato dal git: contiene coordinate).
"""
import json
import math
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fogli_blocco import coord  # noqa: E402
from rileva_anomalie import blocco  # noqa: E402
from rilievo_dtm import quote  # noqa: E402

RADICE = Path(__file__).resolve().parent.parent
LATO = 500
MAX_M = 40


def giudica(lat, lon):
    z = quote(lat, lon, LATO)
    tutte = blocco(z)
    if not tutte:
        return None
    pt = np.array([t[0] for t in tutte])
    vicine = [t for t in tutte if math.hypot(t[1] - LATO / 2, t[2] - LATO / 2) < MAX_M]
    if not vicine:
        return {'punteggio': 0.0, 'percentile': 0.0, 'coerenza': None, 'raggio': None, 'strutture': len(tutte)}
    p, y, x, r, segno, alt, reg, coe = max(vicine, key=lambda t: t[0])
    return {'punteggio': round(p, 3), 'percentile': round(float((pt < p).mean()) * 100, 1), 'coerenza': round(coe, 3),
            'raggio': r, 'strutture': len(tutte)}


def elenco(modo):
    if modo == 'candidati':
        d = json.loads((RADICE / 'dati' / 'scansione.json').read_text(encoding='utf-8'))
        for c in (d.get('candidati', d) if isinstance(d, dict) else d):
            yield c['id'], c['lat'], c['lon'], c['affidabilita']
    else:
        riga = 0
        for t in (RADICE / 'dati' / 'blocchi' / 'punti_segnalati.txt').read_text(encoding='utf-8').splitlines():
            m = re.match(r'(\S+) (f_r\d+_c\d+) (\d+) (\d+) (\d) (.*)', t)
            if m:
                riga += 1
                lat, lon = coord(m[1], m[2], float(m[3]), float(m[4]))
                yield f'{riga}:{m[1]}', lat, lon, f'conf{m[5]} {m[6][:60]}'


def main():
    modo = sys.argv[1]
    voci = list(elenco(modo))
    with ThreadPoolExecutor(3) as ex:
        esiti = list(ex.map(lambda v: giudica(v[1], v[2]), voci))
    out = []
    for (i, lat, lon, nota), e in zip(voci, esiti):
        out.append({'id': i, 'lat': lat, 'lon': lon, 'nota': nota, 'rilevatore': e})
        print(f'{i:14s} {nota[:34]:34s}', e)
    (RADICE / 'dati' / 'blocchi' / f'seconda_opinione_{modo}.json').write_text(json.dumps(out), encoding='utf-8')


if __name__ == '__main__':
    main()
