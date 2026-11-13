"""Serie temporale Sentinel-2 L2A (NDVI) su una piccola finestra, per cercare crop marks nei campi.

Uso: python -I tools/serie_suolo.py LAT LON [--finestra 500] [--da 2023-01-01] [--a AAAA-MM-GG]
                                     [--nuvole 25] [--max-scene 200] [--estate 06-01:07-15]
Fonte: STAC aperto Earth Search (AWS, senza login); bande B04, B08 e SCL come COG su sentinel-cogs.s3.
Si legge solo il ritaglio: l'intestazione TIFF e poi solo le tessere 1024x1024 (deflate + predittore 2)
che toccano la finestra, con richieste HTTP range. Decodifica con zlib + numpy, nessun gdal/rasterio.
Le tessere decodificate vanno in cache (dati/blocchi/serie_suolo/cache) per rilanci rapidi.
Uscite in dati/blocchi/serie_suolo/: <nome>.png (NDVI estivo medio + anomalia + serie), <nome>.json (riepilogo).
Anomalia = NDVI del pixel meno la mediana locale (finestra 9x9 px = 90 m), mediata sulle scene di inizio estate.
Risoluzione: 10 m (SCL a 20 m, replicato).
"""
import argparse
import json
import math
import struct
import sys
import time
import urllib.request
import zlib
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

RADICE = Path(__file__).resolve().parent.parent
USCITA = RADICE / 'dati' / 'blocchi' / 'serie_suolo'
STAC = 'https://earth-search.aws.element84.com/v1/search'
MARGINE = 60          # m di margine attorno alla finestra, per la mediana locale
SCL_NO = {0, 1, 3, 8, 9, 10}   # nodata, saturo, ombra nuvola, nuvola media/alta, cirro


# ---------- rete ----------
def http(url, dati=None, intest=None, tentativi=5):
    for t in range(tentativi):
        try:
            rich = urllib.request.Request(url, data=dati, headers=intest or {})
            with urllib.request.urlopen(rich, timeout=60) as r:
                return r.read()
        except Exception:
            if t == tentativi - 1:
                raise
            time.sleep(1 + t)


def range_(url, a, b):
    return http(url, intest={'Range': f'bytes={a}-{b - 1}'})


# ---------- proiezione UTM (Kruger, WGS84) ----------
def utm(lat, lon, epsg):
    zona = epsg - 32600
    a, f = 6378137.0, 1 / 298.257223563
    n = f / (2 - f)
    A = a / (1 + n) * (1 + n**2 / 4 + n**4 / 64)
    al = [n / 2 - 2 * n**2 / 3 + 5 * n**3 / 16, 13 * n**2 / 48 - 3 * n**3 / 5, 61 * n**3 / 240]
    e = math.sqrt(f * (2 - f))
    ph, dl = math.radians(lat), math.radians(lon - ((zona - 1) * 6 - 180 + 3))
    t = math.sinh(math.atanh(math.sin(ph)) - e * math.atanh(e * math.sin(ph)))
    xi = math.atan2(t, math.cos(dl))
    eta = math.atanh(math.sin(dl) / math.sqrt(1 + t * t))
    x = eta + sum(al[j] * math.cos(2 * (j + 1) * xi) * math.sinh(2 * (j + 1) * eta) for j in range(3))
    y = xi + sum(al[j] * math.sin(2 * (j + 1) * xi) * math.cosh(2 * (j + 1) * eta) for j in range(3))
    return 500000 + 0.9996 * A * x, 0.9996 * A * y


# ---------- lettore COG minimale ----------
class COG:
    def __init__(self, url):
        self.url = url
        b = range_(url, 0, 131072)
        self.bo = '<' if b[:2] == b'II' else '>'
        big = struct.unpack(self.bo + 'H', b[2:4])[0] == 43
        if big:
            ifd = struct.unpack(self.bo + 'Q', b[8:16])[0]
            n = struct.unpack(self.bo + 'Q', b[ifd:ifd + 8])[0]
            vo, tsz, eoff, esz = 8, 20, ifd + 8, 8
        else:
            ifd = struct.unpack(self.bo + 'I', b[4:8])[0]
            n = struct.unpack(self.bo + 'H', b[ifd:ifd + 2])[0]
            vo, tsz, eoff, esz = 4, 12, ifd + 2, 4
        tipi = {1: 'B', 2: 'c', 3: 'H', 4: 'I', 5: 'II', 12: 'd', 16: 'Q'}
        self.tag = {}
        for i in range(n):
            e = b[eoff + i * tsz: eoff + (i + 1) * tsz]
            tag, tipo = struct.unpack(self.bo + 'HH', e[:4])
            cnt = struct.unpack(self.bo + ('Q' if big else 'I'), e[4:4 + (8 if big else 4)])[0]
            if tipo not in tipi or tipo == 5 or tipo == 2:
                continue
            fmt = tipi[tipo]
            dim = struct.calcsize(fmt)
            raw = e[4 + esz:4 + esz + vo]
            if cnt * dim > vo:
                off = struct.unpack(self.bo + ('Q' if big else 'I'), raw)[0]
                raw = b[off:off + cnt * dim] if off + cnt * dim <= len(b) else range_(url, off, off + cnt * dim)
            self.tag[tag] = struct.unpack(self.bo + str(cnt) + fmt, raw[:cnt * dim])
        t = self.tag
        self.W, self.H = t[256][0], t[257][0]
        self.tw, self.th = t[322][0], t[323][0]
        self.compr = t[259][0]
        self.pred = t.get(317, (1,))[0]
        self.bits = t[258][0]
        self.off, self.cnt = t[324], t[325]
        self.x0, self.y0 = t[33922][3], t[33922][4]
        self.res = t[33550][0]
        if self.compr not in (8, 32946) or self.bits != 8 * (self.bits // 8) or self.bits not in (8, 16):
            raise ValueError(f'formato COG non gestito: compr={self.compr} bit={self.bits}')

    def tessera(self, ty, tx):
        nx = -(-self.W // self.tw)
        k = ty * nx + tx
        d = zlib.decompress(range_(self.url, self.off[k], self.off[k] + self.cnt[k]))
        dt = np.dtype('<u2' if self.bits == 16 else 'u1')
        a = np.frombuffer(d, dtype=dt).reshape(self.th, self.tw).copy()
        if self.pred == 2:
            a = np.cumsum(a, axis=1, dtype=a.dtype)
        return a

    def finestra(self, E0, N1, E1, N0):
        """Ritaglio con bordo ovest/nord = (E0, N1) e est/sud = (E1, N0), in metri UTM. -> array int, riga0, col0."""
        c0, c1 = int(math.floor((E0 - self.x0) / self.res)), int(math.ceil((E1 - self.x0) / self.res))
        r0, r1 = int(math.floor((self.y0 - N1) / self.res)), int(math.ceil((self.y0 - N0) / self.res))
        if c0 < 0 or r0 < 0 or c1 > self.W or r1 > self.H:
            raise ValueError('finestra fuori dalla scena')
        out = np.zeros((r1 - r0, c1 - c0), dtype=np.uint16)
        for ty in range(r0 // self.th, (r1 - 1) // self.th + 1):
            for tx in range(c0 // self.tw, (c1 - 1) // self.tw + 1):
                t = self.tessera(ty, tx)
                ya, xa = max(r0, ty * self.th), max(c0, tx * self.tw)
                yb, xb = min(r1, (ty + 1) * self.th), min(c1, (tx + 1) * self.tw)
                out[ya - r0:yb - r0, xa - c0:xb - c0] = t[ya - ty * self.th:yb - ty * self.th,
                                                          xa - tx * self.tw:xb - tx * self.tw]
        return out, r0, c0


# ---------- STAC ----------
def cerca(lat, lon, da, a, nuvole, lim):
    d = 0.0002
    corpo = {'collections': ['sentinel-2-l2a'], 'bbox': [lon - d, lat - d, lon + d, lat + d],
             'datetime': f'{da}T00:00:00Z/{a}T23:59:59Z', 'limit': 200,
             'query': {'eo:cloud_cover': {'lt': nuvole}}, 'sortby': [{'field': 'properties.datetime', 'direction': 'desc'}]}
    items = []
    while corpo and len(items) < lim:
        r = json.loads(http(STAC, json.dumps(corpo).encode(), {'Content-Type': 'application/json'}))
        items += r['features']
        nxt = [l for l in r.get('links', []) if l.get('rel') == 'next']
        corpo = nxt[0].get('body') if nxt else None
    return items[:lim]


def scena(it, lat, lon, meta):
    """-> (data, ndvi[H,W] con NaN sulle nuvole, frazione_mascherata) oppure None."""
    p = it['properties']
    epsg = p.get('proj:epsg') or int(str(p['proj:code']).split(':')[1])
    E, N = utm(lat, lon, epsg)
    m = meta['mezzo'] + MARGINE
    ass = it['assets']
    cache = USCITA / 'cache' / f"{it['id']}_{lat:.5f}_{lon:.5f}_{meta['mezzo']}.npz"
    if cache.exists():
        z = np.load(cache)
        return z['ndvi'], float(z['mask'])
    bande = {}
    for nome in ('red', 'nir'):
        c = COG(ass[nome]['href'])
        arr, _, _ = c.finestra(E - m, N + m, E + m, N - m)
        rb = ass[nome].get('raster:bands', [{}])[0]
        valido = arr[arr > 0]
        off = rb.get('offset', 0.0) if valido.size and valido.min() >= 1000 else 0.0   # offset solo se i DN lo contengono
        bande[nome] = arr.astype(np.float64) * rb.get('scale', 1e-4) + off, arr == 0
    c = COG(ass['scl']['href'])
    scl, r0, c0 = c.finestra(E - m, N + m, E + m, N - m)
    scl = np.kron(scl, np.ones((2, 2), dtype=scl.dtype))   # 20 m -> 10 m (blocchi allineati alla griglia SCL)
    h, w = bande['red'][0].shape
    # allineamento: la griglia SCL parte da una cella a 20 m che puo' non coincidere con la finestra a 10 m
    scl = np.pad(scl, ((0, max(0, h - scl.shape[0])), (0, max(0, w - scl.shape[1]))), mode='edge')[:h, :w]
    r, nod_r = bande['red']
    n, nod_n = bande['nir']
    brutto = nod_r | nod_n | np.isin(scl, list(SCL_NO))
    with np.errstate(all='ignore'):
        ndvi = (n - r) / (n + r)
    ndvi[brutto] = np.nan
    ndvi[(ndvi < -1) | (ndvi > 1)] = np.nan
    mask = float(np.isnan(ndvi).mean())
    cache.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cache, ndvi=ndvi.astype(np.float32), mask=mask)
    return ndvi, mask


# ---------- analisi ----------
def mediana_locale(a, k=9):
    h = k // 2
    p = np.pad(a, h, constant_values=np.nan)
    v = np.lib.stride_tricks.sliding_window_view(p, (k, k)).reshape(a.shape[0], a.shape[1], -1)
    with np.errstate(all='ignore'):
        return np.nanmedian(v, axis=2)


def colore_div(a, lim):
    t = np.clip(a / lim, -1, 1)
    rgb = np.empty(a.shape + (3,))
    pos = t > 0
    rgb[..., 0] = np.where(pos, 255, 255 * (1 + t))
    rgb[..., 1] = 255 * (1 - np.abs(t) * 0.6)
    rgb[..., 2] = np.where(pos, 255 * (1 - t), 255)
    rgb[np.isnan(a)] = 128
    return rgb.astype(np.uint8)


def colore_ndvi(a):
    t = np.clip((a + 0.1) / 0.9, 0, 1)
    rgb = np.stack([230 - 200 * t, 220 - 60 * t, 150 - 110 * t], -1)
    rgb[np.isnan(a)] = 128
    return rgb.astype(np.uint8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('lat', type=float)
    ap.add_argument('lon', type=float)
    ap.add_argument('--finestra', type=float, default=500)
    ap.add_argument('--da', default='2023-01-01')
    ap.add_argument('--a', default=date.today().isoformat())
    ap.add_argument('--nuvole', type=float, default=25)
    ap.add_argument('--max-scene', type=int, default=200)
    ap.add_argument('--estate', default='06-01:07-15')
    ap.add_argument('--max-maschera', type=float, default=0.1, help='scarta scene con piu di questa frazione mascherata')
    a = ap.parse_args()
    mezzo = int(round(a.finestra / 2 / 10)) * 10
    meta = {'mezzo': mezzo}
    USCITA.mkdir(parents=True, exist_ok=True)
    items = cerca(a.lat, a.lon, a.da, a.a, a.nuvole, a.max_scene)
    # una sola scena per data (tessere MGRS sovrapposte: prima in elenco = preferita)
    viste, scelte = set(), []
    for it in items:
        d = it['properties']['datetime'][:10]
        if d not in viste:
            viste.add(d)
            scelte.append(it)
    print(f'{len(items)} scene trovate, {len(scelte)} date distinte', flush=True)

    def lavora(it):
        try:
            r = scena(it, a.lat, a.lon, meta)
            return it['properties']['datetime'][:10], r
        except Exception as e:
            return it['properties']['datetime'][:10], str(e)
    with ThreadPoolExecutor(8) as ex:
        ris = list(ex.map(lavora, scelte))
    serie = []
    for d, r in sorted(ris):
        if isinstance(r, str):
            print('  errore', d, r[:80])
        elif r[1] <= a.max_maschera:
            serie.append((d, r[0], r[1]))
    print(f'{len(serie)} scene utili (maschera <= {a.max_maschera:.0%})')
    if not serie:
        sys.exit('nessuna scena utile')
    c = (slice(MARGINE // 10, -(MARGINE // 10)),) * 2
    riepilogo = []
    for d, nd, mk in serie:
        z = nd[c]
        riepilogo.append({'data': d, 'ndvi_medio': round(float(np.nanmean(z)), 3), 'ndvi_dev_std': round(float(np.nanstd(z)), 3),
                          'maschera': round(mk, 3)})
    m1, d1 = a.estate.split(':')
    est = [(d, nd) for d, nd, _ in serie if m1 <= d[5:] <= d1]
    if len(est) < 2:
        est = [(d, nd) for d, nd, _ in serie if '05-01' <= d[5:] <= '07-31']
    anom = []
    for d, nd in est:
        anom.append(nd - mediana_locale(nd))
    A = np.nanmean(np.array(anom), axis=0)[c]
    Asd = np.nanstd(np.array(anom), axis=0)[c]
    ndvi_est = np.nanmean(np.array([nd for _, nd in est]), axis=0)[c]
    nome = f'serie_{a.lat:.4f}_{a.lon:.4f}_{int(a.finestra)}m'
    # immagine
    S = 8
    lato = ndvi_est.shape[0]
    pannelli = [colore_ndvi(ndvi_est), colore_div(A, max(0.05, float(np.nanpercentile(np.abs(A), 98)))),
                colore_div(Asd, float(np.nanmax(Asd)) or 1) if False else colore_ndvi(np.nan_to_num(Asd * 4, nan=np.nan))]
    pannelli = pannelli[:2]
    tela = Image.new('RGB', (lato * S * 2 + 30, lato * S + 150 + 14 * 0), 'white')
    for i, pn in enumerate(pannelli):
        tela.paste(Image.fromarray(pn).resize((lato * S, lato * S), Image.NEAREST), (10 + i * (lato * S + 10), 20))
    dr = ImageDraw.Draw(tela)
    dr.text((10, 4), f'NDVI medio inizio estate ({len(est)} scene)', fill='black')
    dr.text((lato * S + 20, 4), f'anomalia NDVI vs mediana 90 m (+-{max(0.05, float(np.nanpercentile(np.abs(A), 98))):.2f})', fill='black')
    # serie temporale
    y0, y1, x0, x1 = lato * S + 40, lato * S + 140, 10, tela.width - 10
    dr.rectangle([x0, y0, x1, y1], outline='gray')
    ds = [date.fromisoformat(r['data']) for r in riepilogo]
    t0, t1 = min(ds).toordinal(), max(ds).toordinal()
    pts = [(x0 + (d.toordinal() - t0) / max(1, t1 - t0) * (x1 - x0), y1 - (r['ndvi_medio'] + 0.1) / 1.1 * (y1 - y0))
           for d, r in zip(ds, riepilogo)]
    dr.line(pts, fill=(40, 120, 40))
    for p in pts:
        dr.ellipse([p[0] - 2, p[1] - 2, p[0] + 2, p[1] + 2], fill=(20, 80, 20))
    dr.text((x0, y0 - 14), f'NDVI medio per data {min(ds)} .. {max(ds)} ({len(ds)} scene)', fill='black')
    tela.save(USCITA / f'{nome}.png')
    ris_json = {'lat': a.lat, 'lon': a.lon, 'finestra_m': a.finestra, 'risoluzione_m': 10, 'scene_trovate': len(items),
                'scene_utili': len(serie), 'scene_estate': [d for d, _ in est], 'serie': riepilogo,
                'anomalia': {'dev_std': round(float(np.nanstd(A)), 4), 'min': round(float(np.nanmin(A)), 3),
                             'max': round(float(np.nanmax(A)), 3)}, 'dev_std_tra_scene_media': round(float(np.nanmean(Asd)), 4)}
    (USCITA / f'{nome}.json').write_text(json.dumps(ris_json, indent=1), encoding='utf8')
    print(json.dumps(ris_json['anomalia']), 'scene estate:', len(est))
    print('scritto', USCITA / f'{nome}.png')


if __name__ == '__main__':
    main()
