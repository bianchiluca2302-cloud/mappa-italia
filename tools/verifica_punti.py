"""Per ogni punto di dati/blocchi/punti_segnalati.txt crea un foglio 2x2 (DTM, DSM, foto 2013, foto 1954; finestra 200 m)
in dati/blocchi/verifica/<N>_<blocco>.png e stampa lat, lon. Usa Pillow (come fogli_blocco.py).

Uso: python -I tools/verifica_punti.py N [N...]     (N = numero della riga di punto, da 1, nell'ordine del file)
"""
import io
import math
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fogli_blocco import coord  # noqa: E402
from vista_candidato import BASE, VISTE  # noqa: E402

RADICE = Path(__file__).resolve().parent.parent
META = 100


def scarica(mappa, layer, lat, lon):
    dlat = META / 111_000
    dlon = META / (111_000 * math.cos(math.radians(lat)))
    q = {'service': 'WMS', 'request': 'GetMap', 'version': '1.3.0', 'layers': layer, 'styles': '',
         'crs': 'EPSG:4326', 'bbox': f'{lat - dlat:.6f},{lon - dlon:.6f},{lat + dlat:.6f},{lon + dlon:.6f}',
         'width': 500, 'height': 500, 'format': 'image/png'}
    with urllib.request.urlopen(BASE + mappa + '&' + urllib.parse.urlencode(q), timeout=90) as r:
        return r.read()


def punti():
    out = []
    for riga in (RADICE / 'dati' / 'blocchi' / 'punti_segnalati.txt').read_text(encoding='utf-8').splitlines():
        m = re.match(r'(metallifere|chianti) f_r(\d\d)\S*? ?(?:\S*)?\s*', riga)
        m = re.match(r'(metallifere|chianti) (?:\S+ )?f_r(\d\d)_c(\d\d)\S* (\d+) (\d+) (\d) (.*)', riga)
        if m:
            out.append(m.groups())
    return out


def main():
    from PIL import Image
    pp = punti()
    cart = RADICE / 'dati' / 'blocchi' / 'verifica'
    cart.mkdir(exist_ok=True)
    for n in map(int, sys.argv[1:]):
        b, r, c, x, y, conf, nota = pp[n - 1]
        lat, lon = coord(b, f'f_r{r}_c{c}', float(x), float(y))
        fg = Image.new('RGB', (1000, 1000))
        for i, (mappa, layer) in enumerate(VISTE.values()):
            im = Image.open(io.BytesIO(scarica(mappa, layer, lat, lon))).convert('RGB')
            fg.paste(im, ((i % 2) * 500, (i // 2) * 500))
        fg.save(cart / f'{n}_{b}.png')
        print(n, b, lat, lon, conf, nota)


if __name__ == '__main__':
    main()
