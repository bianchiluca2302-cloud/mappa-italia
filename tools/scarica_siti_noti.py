"""Scarica da OpenStreetMap (Overpass) i siti archeologici noti della Toscana.

Scrive dati/siti-noti.js (var SITI_NOTI = [...]) letto da index.html, e dati/siti-noti.json.
Uso: python -I tools/scarica_siti_noti.py
"""
import json
import urllib.parse
import urllib.request
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
ENDPOINT = 'https://overpass-api.de/api/interpreter'
QUERY = """
[out:json][timeout:180];
area["ISO3166-2"="IT-52"]->.a;
(
  nwr["historic"="archaeological_site"](area.a);
  nwr["historic"~"^(ruins|castle|tomb|wayside_shrine|city_gate|fort)$"]["site_type"](area.a);
  nwr["historic"="tomb"]["tomb"~"tumulus|hypogeum|rock-cut"](area.a);
);
out center tags;
"""


def main():
    dati = urllib.parse.urlencode({'data': QUERY}).encode()
    req = urllib.request.Request(ENDPOINT, dati, {'User-Agent': 'MappaItalia/0.1 (uso personale)'})
    with urllib.request.urlopen(req, timeout=240) as r:
        risposta = json.load(r)
    siti = []
    for e in risposta['elements']:
        lat = e.get('lat') or e.get('center', {}).get('lat')
        lon = e.get('lon') or e.get('center', {}).get('lon')
        if lat is None:
            continue
        t = e.get('tags', {})
        siti.append({
            'lat': round(lat, 5), 'lon': round(lon, 5),
            'nome': t.get('name', ''),
            'tipo': t.get('site_type') or t.get('historic', ''),
            'periodo': t.get('historic:civilization') or t.get('start_date', ''),
            'osm': f"{e['type']}/{e['id']}",
        })
    (RADICE / 'dati').mkdir(exist_ok=True)
    (RADICE / 'dati' / 'siti-noti.json').write_text(json.dumps(siti, ensure_ascii=False), encoding='utf-8')
    (RADICE / 'dati' / 'siti-noti.js').write_text(
        'var SITI_NOTI = ' + json.dumps(siti, ensure_ascii=False) + ';\n', encoding='utf-8')
    print(len(siti), 'siti scritti')


if __name__ == '__main__':
    main()
