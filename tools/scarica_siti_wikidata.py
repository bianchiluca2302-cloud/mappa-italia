"""Scarica da Wikidata i siti archeologici nel riquadro della Toscana e scrive dati/siti-wikidata.js.

Uso: python -I tools/scarica_siti_wikidata.py
"""
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
ENDPOINT = 'https://query.wikidata.org/sparql'
# riquadro della Toscana (lon lat)
SO, NE = 'Point(9.68 42.23)', 'Point(12.37 44.47)'
# tipi tenuti (etichetta italiana): "monumento", "palazzo di giustizia" ecc. sono rumore
TIPI_BUONI = {'sito archeologico', 'rovine', 'fortezza di collina', 'entità scomparsa', 'tomba', 'necropoli'}
QUERY = f"""
SELECT ?s ?sLabel ?lat ?lon ?tipoLabel WHERE {{
  SERVICE wikibase:box {{
    ?s wdt:P625 ?loc .
    bd:serviceParam wikibase:cornerSouthWest "{SO}"^^geo:wktLiteral .
    bd:serviceParam wikibase:cornerNorthEast "{NE}"^^geo:wktLiteral .
  }}
  VALUES ?tipo {{ wd:Q839954 wd:Q4989906 wd:Q109607 wd:Q1370598 wd:Q1550680 wd:Q1456083 wd:Q1329623
                  wd:Q744099 wd:Q1137809 wd:Q15893266 wd:Q2065736 wd:Q1129749 }}
  ?s wdt:P31 ?tipo .
  BIND(geof:latitude(?loc) AS ?lat) BIND(geof:longitude(?loc) AS ?lon)
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "it,en". }}
}}
"""


def chiedi(tentativi=4):
    dati = urllib.parse.urlencode({'query': QUERY}).encode()
    for n in range(tentativi):
        req = urllib.request.Request(ENDPOINT, dati, {
            'User-Agent': 'MappaItalia/0.1 (uso personale)', 'Accept': 'application/sparql-results+json'})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)['results']['bindings']
        except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as e:
            print('tentativo', n + 1, 'fallito:', e)
            time.sleep(10 * (n + 1))
    raise SystemExit('Wikidata non risponde, riprova piu tardi')


def main():
    visti = {}
    for b in chiedi():
        tipo = b['tipoLabel']['value']
        if tipo not in TIPI_BUONI:
            continue
        qid = b['s']['value'].rsplit('/', 1)[-1]
        visti[qid] = {
            'lat': round(float(b['lat']['value']), 5), 'lon': round(float(b['lon']['value']), 5),
            'nome': b['sLabel']['value'] if not b['sLabel']['value'].startswith('Q') else '',
            'tipo': tipo, 'wikidata': qid,
        }
    siti = list(visti.values())
    (RADICE / 'dati' / 'siti-wikidata.json').write_text(json.dumps(siti, ensure_ascii=False), encoding='utf-8')
    (RADICE / 'dati' / 'siti-wikidata.js').write_text(
        'var SITI_WIKIDATA = ' + json.dumps(siti, ensure_ascii=False) + ';\n', encoding='utf-8')
    print(len(siti), 'siti scritti')


if __name__ == '__main__':
    main()
