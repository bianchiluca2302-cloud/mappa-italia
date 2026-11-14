"""Misura la sensibilita del rilevatore sui tumuli noti di dati/ricerche_tumuli/tumuli_noti.json.

Uso: python -I tools/taratura_tumuli.py [TIPI=tumulo]   (es. tumulo,tomba)
Per ogni sito (doppioni entro 40 m fusi) scarica 600 m di quote, applica rileva_anomalie.blocco e prende la struttura
piu vicina entro DIST_M m. Come riferimento di caso stima la densita di strutture della stessa finestra (a piu di
DIST_M m dal sito) e dice se la regola C (coerenza<=0,3, punteggio>=0,5, raggio>=20 m) le prenderebbe.
Scrive dati/ricerche_tumuli/taratura.json (ignorato dal git).
"""
import json
import math
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rileva_anomalie import blocco  # noqa: E402
from rilievo_dtm import quote  # noqa: E402

RADICE = Path(__file__).resolve().parent.parent
LATO = 600
DIST_M = 60


def regola_c(coe, p, r):
    return coe <= 0.3 and p >= 0.5 and r >= 20


def distanza(a, b):
    return math.hypot((a['lat'] - b['lat']) * 111_000, (a['lon'] - b['lon']) * 111_000 * math.cos(math.radians(a['lat'])))


def siti(tipi):
    b = (RADICE / 'dati' / 'ricerche_tumuli' / 'tumuli_noti.json').read_bytes()
    try:
        d = json.loads(b.decode('utf-8'))
    except UnicodeDecodeError:
        d = json.loads(b.decode('cp1252'))
    out = []
    for s in d['siti'] if 'siti' in d else d:
        if s.get('tipo') in tipi and not any(distanza(s, o) < 40 for o in out):
            out.append(s)
    return out


def valuta(s):
    try:
        z = quote(s['lat'], s['lon'], LATO)
    except Exception as e:
        return {**s, 'esito': 'errore', 'errore': str(e)[:80]}
    ok = float(np.isfinite(z).mean()) if z.size else 0
    if ok < 0.9 or np.nanstd(z) < 0.01:
        return {**s, 'esito': 'senza_dato', 'dato': round(ok, 2)}
    tutte = blocco(z)
    c = LATO / 2
    vic = [t for t in tutte if math.hypot(t[1] - c, t[2] - c) < DIST_M]
    lontane = [t for t in tutte if math.hypot(t[1] - c, t[2] - c) >= DIST_M]
    area = max(1e-9, (LATO / 1000) ** 2 - math.pi * (DIST_M / 1000) ** 2)
    pt = np.array([t[0] for t in tutte]) if tutte else np.array([0.0])
    base = {**s, 'esito': 'ok', 'strutture': len(tutte), 'dens_km2': round(len(lontane) / area, 1),
            'dens_C_km2': round(sum(regola_c(t[7], t[0], t[3]) for t in lontane) / area, 2)}
    if not vic:
        return {**base, 'trovato': False}
    p, y, x, r, segno, alt, reg, coe = max(vic, key=lambda t: t[0])
    return {**base, 'trovato': True, 'punteggio': round(p, 3), 'coerenza': round(coe, 3), 'raggio': r,
            'percentile': round(float((pt < p).mean()) * 100, 1), 'regola_c': bool(regola_c(coe, p, r)),
            'dist_m': round(math.hypot(x - c, y - c), 1)}


def main():
    tipi = (sys.argv[1] if len(sys.argv) > 1 else 'tumulo').split(',')
    elenco = siti(tipi)
    print(len(elenco), 'siti', flush=True)
    with ThreadPoolExecutor(4) as ex:
        ris = list(ex.map(valuta, elenco))
    (RADICE / 'dati' / 'ricerche_tumuli' / 'taratura.json').write_text(json.dumps(ris, ensure_ascii=False, indent=1),
                                                                        encoding='utf-8')
    ok = [r for r in ris if r['esito'] == 'ok']
    tr = [r for r in ok if r['trovato']]
    print(f"con dato {len(ok)}, senza dato {sum(r['esito'] == 'senza_dato' for r in ris)}, errori "
          f"{sum(r['esito'] == 'errore' for r in ris)}")
    print(f"trovati entro {DIST_M} m: {len(tr)}/{len(ok)}; con regola C: {sum(r['regola_c'] for r in tr)}/{len(ok)}")
    if ok:
        print(f"densita media strutture {np.mean([r['dens_km2'] for r in ok]):.1f}/km2, regola C "
              f"{np.mean([r['dens_C_km2'] for r in ok]):.2f}/km2")
        p = [r['percentile'] for r in tr]
        print('percentile dei trovati:', sorted(p))


main()
