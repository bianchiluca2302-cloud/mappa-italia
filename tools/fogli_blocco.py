"""Compone i fogli 2x2 (1200x1200 px, reticolo giallo ogni 120 px) delle tessere di un blocco e converte pixel in coordinate.
Questo script usa Pillow (unica eccezione alla regola "solo libreria standard").

Uso: python -I tools/fogli_blocco.py fogli NOME             -> dati/blocchi/NOME/fogli/f_r<riga>_c<colonna>.png
     python -I tools/fogli_blocco.py coord NOME FOGLIO X Y  -> lat, lon del pixel X,Y del foglio (es. f_r04_c06)
Un foglio f_rRR_cCC copre le righe RR (sotto) e RR+1 (sopra), le colonne CC (sinistra) e CC+1 (destra).
Ogni tessera e ritagliata dei 25 px di scritta e ridotta a 600 px: 1 px del foglio = circa 1,67 m; il reticolo e ogni ~195 m.
"""
import json
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent


def carica(nome):
    cartella = RADICE / 'dati' / 'blocchi' / nome
    return cartella, json.loads((cartella / 'blocco.json').read_text(encoding='utf-8'))


def fogli(nome):
    from PIL import Image, ImageDraw
    cartella, b = carica(nome)
    vuote = {tuple(v) for v in b['vuote']}
    (cartella / 'fogli').mkdir(exist_ok=True)
    n = 0
    for r0 in range(0, b['righe'], 2):
        for c0 in range(0, b['colonne'], 2):
            celle = [(r0 + 1 - i, c0 + j) for i in range(2) for j in range(2)]  # riga in alto = latitudine maggiore
            if all(rc in vuote or rc[0] >= b['righe'] or rc[1] >= b['colonne'] for rc in celle):
                continue
            foglio = Image.new('RGB', (1200, 1200), 'black')
            d = ImageDraw.Draw(foglio)
            for i, (r, c) in enumerate(celle):
                f = cartella / f'r{r:02d}_c{c:02d}.png'
                if (r, c) in vuote or not f.exists():
                    continue
                im = Image.open(f).convert('RGB').crop((25, 0, 1000, 1000)).resize((600, 600))
                x, y = (i % 2) * 600, (i // 2) * 600
                foglio.paste(im, (x, y))
                for k in range(0, 600, 120):
                    d.line([(x + k, y), (x + k, y + 600)], fill=(255, 255, 0))
                    d.line([(x, y + k), (x + 600, y + k)], fill=(255, 255, 0))
                d.text((x + 4, y + 4), f'r{r} c{c}', fill=(255, 0, 0))
            foglio.save(cartella / 'fogli' / f'f_r{r0:02d}_c{c0:02d}.png')
            n += 1
    print(n, 'fogli')


def coord(nome, foglio, x, y):
    _, b = carica(nome)
    r0, c0 = int(foglio[3:5]), int(foglio[7:9])
    r, c = r0 + 1 - int(y // 600), c0 + int(x // 600)
    px, py = 25 + (x % 600) * 975 / 600, (y % 600) * 1000 / 600
    lat = b['lat0'] + r * b['dlat'] + (1 - py / 1000) * b['dlat']
    lon = b['lon0'] + c * b['dlon'] + px / 1000 * b['dlon']
    return round(lat, 5), round(lon, 5)


if __name__ == '__main__':
    if sys.argv[1] == 'fogli':
        fogli(sys.argv[2])
    else:
        print(*coord(sys.argv[2], sys.argv[3], float(sys.argv[4]), float(sys.argv[5])))
