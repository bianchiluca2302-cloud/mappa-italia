"""Scrive dati/scansione.js (tessere viste e candidati) leggendo dati/scansione.json, a mano o da Claude.

Uso: python -I tools/registra_scansione.py
Per ogni candidato calcola il sito noto piu vicino (OSM e Wikidata) cosi si vede subito se e gia censito.
"""
import json
import math
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
D = RADICE / 'dati'


def metri(a, b):
    return math.hypot((a[0] - b[0]) * 111_000, (a[1] - b[1]) * 111_000 * math.cos(math.radians(a[0])))


def main():
    reg = json.loads((D / 'scansione.json').read_text(encoding='utf-8'))
    noti = []
    for f in ('siti-noti.json', 'siti-wikidata.json'):
        noti += json.loads((D / f).read_text(encoding='utf-8'))
    for c in reg['candidati']:
        m, s = min(((metri((c['lat'], c['lon']), (x['lat'], x['lon'])), x) for x in noti), key=lambda t: t[0])
        c['noto_vicino'] = {'metri': round(m), 'nome': s.get('nome', ''), 'tipo': s.get('tipo', '')}
    (D / 'scansione.json').write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding='utf-8')
    (D / 'scansione.js').write_text('var SCANSIONE = ' + json.dumps(reg, ensure_ascii=False) + ';\n', encoding='utf-8')
    for c in reg['candidati']:
        print(c['id'], c['affidabilita'], c['noto_vicino'])


if __name__ == '__main__':
    main()
