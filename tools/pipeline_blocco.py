"""Un comando per blocco: quote -> rilevatore -> filtro OSM -> uso del suolo -> lista ordinata + fogli multi-luce.

Uso: python -I tools/pipeline_blocco.py NOME LAT_SUD LON_OVEST RIGHE COLONNE [MAX_FOGLI=40] [--rifai]
I passi gia fatti (quote.npy, rilevati.json, filtrati.json) si saltano, salvo --rifai. Il risultato e in
dati/blocchi/NOME/ (ignorato dal git: contiene coordinate): pipeline.json, con i punti da guardare in ordine
(prima quelli in bosco, poi in aperto; dentro ogni gruppo per punteggio), e fogli_rilievo/NN.png, il 2x2
(una luce, 8 luci, rilievo locale, SVF; finestra 200 m) dei primi MAX_FOGLI punti, NN = posizione in lista.
I punti vicini a siti OSM o ad aree vincolate (vincoli_arch.py) restano in fondo alla lista col flag gia_noto.
Regola C (coerenza<=0,3, punteggio>=0,5, raggio>=20 m) = flag regola_c, in testa alla lista dopo i gia_noto in fondo.
Esclusi: punti su opere moderne di OSM e punti "piatti" (laghetti, piazzali: DTM interno liscio, vedi uso_suolo.py).
Servono numpy, scipy e Pillow.
"""
import json
import math
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

QUI = Path(__file__).resolve().parent
sys.path.insert(0, str(QUI))
from rilievo_dtm import foglio  # noqa: E402
from uso_suolo import classe, indicatori  # noqa: E402
from vincoli_arch import distanza_vincolo  # noqa: E402

RADICE = QUI.parent
MAX_USO = 200
FINESTRA = 200


def esegui(*args):
    r = subprocess.run([sys.executable, '-I', str(QUI / args[0]), *map(str, args[1:])], capture_output=True, text=True)
    if r.returncode:
        print(r.stdout[-500:], r.stderr[-500:])
    return r.returncode == 0


def fondi_doppioni(punti):
    """Tiene il punto di punteggio piu alto tra quelli vicini (distanza < raggio maggiore + 20 m); `fusi` conta gli scartati."""
    tenuti = []
    for p in punti:  # gia in ordine di punteggio decrescente
        for q in tenuti:
            d = math.hypot((p['lat'] - q['lat']) * 111_000, (p['lon'] - q['lon']) * 111_000 * math.cos(math.radians(p['lat'])))
            if d < max(p['raggio'], q['raggio']) + 20:
                q['fusi'] = q.get('fusi', 0) + 1
                break
        else:
            tenuti.append(p)
    return tenuti


def regola_c(p):
    """Regola C: punti da guardare per primi (tumuli grandi e coerenti, ~0,4 punti/km2)."""
    return p['coerenza'] <= 0.3 and p['punteggio'] >= 0.5 and p['raggio'] >= 20


def main():
    args = [a for a in sys.argv[1:] if a != '--rifai']
    rifai = '--rifai' in sys.argv
    nome, lat0, lon0, righe, colonne = args[:5]
    max_fogli = int(args[5]) if len(args) > 5 else 40
    cart = RADICE / 'dati' / 'blocchi' / nome
    if rifai or not (cart / 'quote.npy').exists():
        esegui('scarica_quote.py', nome, lat0, lon0, righe, colonne)
    if rifai or not (cart / 'rilevati.json').exists():
        esegui('rileva_anomalie.py', nome, 0.5)
    if rifai or not (cart / 'filtrati.json').exists():
        if not esegui('filtra_rilevati.py', nome):
            print('filtro OSM non riuscito: si prosegue senza')
    f = cart / 'filtrati.json'
    punti = json.loads((f if f.exists() else cart / 'rilevati.json').read_text(encoding='utf-8'))
    tenuti = [p for p in punti if p.get('esito', 'tenuto') == 'tenuto']
    tenuti.sort(key=lambda p: -p['punteggio'])
    tenuti = fondi_doppioni(tenuti)
    usati = tenuti[:MAX_USO]

    def suolo(p):
        try:
            p['suolo'] = indicatori(p['lat'], p['lon'], p['raggio'])
            p['classe'] = classe(p['suolo'])
            p['vincolo_m'] = distanza_vincolo(p['lat'], p['lon'])
        except Exception as e:
            p['classe'] = 'sconosciuto'
            print('uso del suolo non riuscito:', e)
        return p

    with ThreadPoolExecutor(3) as ex:
        usati = list(ex.map(suolo, usati))
    buoni = [p for p in usati if p['classe'] != 'piatto']
    for p in buoni:
        if (p.get('vincolo_m') is not None and p['vincolo_m'] < 100) or p.get('noto_vicino'):
            p['gia_noto'] = True
    for p in buoni:
        p['regola_c'] = regola_c(p)
    buoni.sort(key=lambda p: (p.get('gia_noto', False), not p['regola_c'], p['classe'] != 'bosco', -p['punteggio']))
    (cart / 'fogli_rilievo').mkdir(exist_ok=True)

    def disegna(ip):
        i, p = ip
        p['posizione'] = i
        if i <= max_fogli:
            p['foglio'] = f'fogli_rilievo/{i:02d}.png'
            foglio(p['lat'], p['lon'], FINESTRA, cart / p['foglio'])
        return p

    with ThreadPoolExecutor(3) as ex:
        buoni = list(ex.map(disegna, enumerate(buoni, 1)))
    (cart / 'pipeline.json').write_text(json.dumps(buoni), encoding='utf-8')
    conto = {}
    for p in buoni:
        conto[p['classe']] = conto.get(p['classe'], 0) + 1
    print(f'{nome}: {len(punti)} rilevati -> {len(tenuti)} dopo OSM -> {len(usati)} valutati '
          f'-> {len(buoni)} dopo scarto piatti {conto}; fogli per i primi {min(max_fogli, len(buoni))}')
    print(f"regola C: {sum(p['regola_c'] and not p.get('gia_noto') for p in buoni)} punti nuovi da guardare")
    for p in buoni[:10]:
        print(f"  #{p['posizione']:02d} {p['classe']:6s} punteggio {p['punteggio']:.2f} raggio {p['raggio']} m"
              + (' REGOLA C' if p['regola_c'] else '') + (' GIA NOTO' if p.get('gia_noto') else ''))


if __name__ == '__main__':
    main()
