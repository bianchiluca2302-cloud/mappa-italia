"""Scarta dai punti di rileva_anomalie.py quelli con una spiegazione moderna (OpenStreetMap) e segna i siti gia noti.

Uso: python -I tools/filtra_rilevati.py NOME
Legge dati/blocchi/NOME/rilevati.json e quote.json, scarica da Overpass (cache in osm.json) edifici, acque, cave,
strade e oggetti storici del blocco e scrive filtrati.json: ogni punto con `esito` (tenuto/scartato), `motivo`
e, se c'e un oggetto storico OSM entro 150 m, `noto_vicino`. Scarta se: un edificio, specchio d'acqua, cava,
discarica o serbatoio sta entro 1,3 raggi dal centro; una strada (non sentiero) passa entro 0,8 raggi.
Le coordinate restano in dati/blocchi/ (ignorato dal git).
"""
import json
import math
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np

RADICE = Path(__file__).resolve().parent.parent
ENDPOINTS = ['https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter']
STRADE_ESCLUSE = {'path', 'footway', 'track', 'bridleway', 'steps', 'cycleway', 'pedestrian', 'service'}
Q_MODERNO = """[out:json][timeout:180];
(way["building"]({b});
 way["natural"="water"]({b}); way["water"]({b}); way["leisure"="swimming_pool"]({b});
 way["landuse"~"^(quarry|reservoir|basin|landfill|construction|industrial|cemetery)$"]({b});
 way["man_made"~"^(water_tank|storage_tank|reservoir_covered|wastewater_plant|silo)$"]({b});
 way["highway"]({b}); way["railway"]({b}); way["waterway"="dam"]({b});
 rel["natural"="water"]({b}); rel["landuse"~"^(quarry|reservoir|landfill)$"]({b}););
out geom;"""
Q_STORICO = """[out:json][timeout:120];
nwr["historic"]({b}); nwr["site_type"]({b}); nwr["tourism"="viewpoint"]({b});
out center tags;"""


def overpass(query, tentativi=6):
    dati = urllib.parse.urlencode({'data': query}).encode()
    for t in range(tentativi):
        req = urllib.request.Request(ENDPOINTS[t % 2], dati, {'User-Agent': 'MappaItalia/0.1 (uso personale)'})
        try:
            with urllib.request.urlopen(req, timeout=240) as r:
                return json.load(r)
        except Exception as e:
            print('overpass:', e)
            time.sleep(10 * (t + 1))
    raise SystemExit('Overpass non risponde')


def osm(cart, info):
    f = cart / 'osm.json'
    if f.exists():
        return json.loads(f.read_text(encoding='utf-8'))
    s, w = info['lat0'], info['lon0']
    n, e = s + info['righe'] * info['dlat'], w + info['colonne'] * info['dlon']
    b = f'{s:.5f},{w:.5f},{n:.5f},{e:.5f}'
    out = {'moderno': overpass(Q_MODERNO.format(b=b))['elements'], 'storico': overpass(Q_STORICO.format(b=b))['elements']}
    f.write_text(json.dumps(out), encoding='utf-8')
    return out


def catalogo(elementi):
    """Lista di (tipo, motivo, array Nx2 di punti (lat, lon), chiuso) per ogni linea/poligono OSM."""
    voci = []
    for e in elementi:
        t = e.get('tags', {})
        geoms = [e['geometry']] if e['type'] == 'way' and 'geometry' in e else \
            [m['geometry'] for m in e.get('members', []) if m.get('geometry') and m.get('role') in ('outer', '')]
        for g in geoms:
            pts = np.array([[p['lat'], p['lon']] for p in g])
            if len(pts) < 2:
                continue
            if 'highway' in t or 'railway' in t:
                if t.get('highway') in STRADE_ESCLUSE:
                    continue
                voci.append(('strada', t.get('highway') or t.get('railway'), pts, False))
            else:
                motivo = t.get('building') and 'edificio' or t.get('landuse') or t.get('man_made') or t.get('water') \
                    or t.get('natural') or t.get('leisure') or t.get('waterway') or 'altro'
                voci.append(('area', 'edificio' if 'building' in t else motivo, pts, True))
    return voci


def dentro(p, poly):
    x, y = p[1], p[0]
    xs, ys = poly[:, 1], poly[:, 0]
    x2, y2 = np.roll(xs, -1), np.roll(ys, -1)
    cond = ((ys > y) != (y2 > y)) & (x < (x2 - xs) * (y - ys) / (y2 - ys + 1e-18) + xs)
    return bool(cond.sum() % 2)


def distanza(p, pts, kx):
    """Distanza minima (m) da p a una spezzata, con lon scalata da kx (m per grado) e lat da 111000."""
    a = np.c_[(pts[:, 1] - p[1]) * kx, (pts[:, 0] - p[0]) * 111_000]
    ab = np.diff(a, axis=0)
    t = np.clip(-(a[:-1] * ab).sum(1) / ((ab ** 2).sum(1) + 1e-9), 0, 1)
    return float(np.hypot(*(a[:-1] + t[:, None] * ab).T).min())


def main():
    nome = sys.argv[1]
    cart = RADICE / 'dati' / 'blocchi' / nome
    info = json.loads((cart / 'quote.json').read_text(encoding='utf-8'))
    punti = json.loads((cart / 'rilevati.json').read_text(encoding='utf-8'))
    dati = osm(cart, info)
    voci = catalogo(dati['moderno'])
    storici = []
    for e in dati['storico']:
        c = e.get('center') or e
        if 'lat' in c:
            t = e.get('tags', {})
            storici.append((c['lat'], c['lon'], t.get('name') or t.get('historic') or t.get('site_type') or 'storico'))
    conto = {}
    for p in punti:
        kx = 111_000 * math.cos(math.radians(p['lat']))
        c = (p['lat'], p['lon'])
        p['esito'] = 'tenuto'
        for tipo, motivo, pts, chiuso in voci:
            if np.abs((pts[:, 0] - c[0]) * 111_000).min() > 400 and np.abs((pts[:, 1] - c[1]) * kx).min() > 400:
                continue
            d = 0.0 if chiuso and dentro(c, pts) else distanza(c, pts, kx)
            if d < (1.3 if tipo == 'area' else 0.8) * p['raggio']:
                p['esito'], p['motivo'] = 'scartato', f'{tipo}: {motivo}'
                break
        conto[p.get('motivo', 'tenuto') if p['esito'] == 'scartato' else 'tenuto'] = \
            conto.get(p.get('motivo', 'tenuto') if p['esito'] == 'scartato' else 'tenuto', 0) + 1
        vicini = sorted((math.hypot((la - c[0]) * 111_000, (lo - c[1]) * kx), n) for la, lo, n in storici)
        if vicini and vicini[0][0] < 150:
            p['noto_vicino'] = {'metri': round(vicini[0][0]), 'nome': vicini[0][1]}
    (cart / 'filtrati.json').write_text(json.dumps(punti), encoding='utf-8')
    print(f'{nome}: {len(punti)} punti ->', {k: v for k, v in sorted(conto.items(), key=lambda kv: -kv[1])[:12]})
    print('noti vicini:', sum('noto_vicino' in p for p in punti), '| tenuti:', conto.get('tenuto', 0))


if __name__ == '__main__':
    main()
