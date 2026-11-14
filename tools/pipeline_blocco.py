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
Lo stato in diretta e in dati/stato_scansione.json (ignorato dal git): la pagina index.html lo legge ogni pochi secondi.
"""
import json
import math
import os
import subprocess
import sys
import threading
import time
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


STATO = RADICE / 'dati' / 'stato_scansione.json'
BLOCCO_STATO = threading.Lock()
FASI = ['quote', 'rilevatore', 'filtro OSM', 'uso del suolo', 'fogli']


def scrivi_stato(stato):
    """Scrittura atomica (la pagina non deve leggere un file a meta); un solo thread alla volta, e su Windows si riprova se il file e aperto da chi lo legge."""
    with BLOCCO_STATO:
        stato['aggiornato'] = time.time()
        tmp = STATO.with_suffix('.tmp')
        tmp.write_text(json.dumps(stato), encoding='utf-8')
        for tentativo in range(20):
            try:
                os.replace(tmp, STATO)
                return
            except PermissionError:
                time.sleep(0.1)
        print('stato_scansione.json occupato: aggiornamento saltato')


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
    try:
        lavora()
    except BaseException as e:
        if STATO.exists():
            st = json.loads(STATO.read_text(encoding='utf-8'))
            st.update(attivo=False, errore=f'{type(e).__name__}: {e}'[:200])
            scrivi_stato(st)
        raise


def lavora():
    args = [a for a in sys.argv[1:] if a != '--rifai']
    rifai = '--rifai' in sys.argv
    nome, lat0, lon0, righe, colonne = args[:5]
    max_fogli = int(args[5]) if len(args) > 5 else 40
    cart = RADICE / 'dati' / 'blocchi' / nome
    fatti = []
    if STATO.exists():
        try:
            fatti = json.loads(STATO.read_text(encoding='utf-8')).get('fatti', [])
        except ValueError:
            pass
    st = {'attivo': True, 'nome': nome, 'lat0': float(lat0), 'lon0': float(lon0), 'righe': int(righe), 'colonne': int(colonne),
          'fasi': FASI, 'fase': 0, 'avanzamento': None, 'inizio': time.time(), 'fatti': [b for b in fatti if b['nome'] != nome]}

    def fase(i, avanz=None):
        st['fase'], st['avanzamento'] = i, avanz
        scrivi_stato(st)

    fase(0)
    if rifai or not (cart / 'quote.npy').exists():
        esegui('scarica_quote.py', nome, lat0, lon0, righe, colonne)
    fase(1)
    if rifai or not (cart / 'rilevati.json').exists():
        esegui('rileva_anomalie.py', nome, 0.5)
    fase(2)
    if rifai or not (cart / 'filtrati.json').exists():
        if not esegui('filtra_rilevati.py', nome):
            print('filtro OSM non riuscito: si prosegue senza')
    fase(3)
    f = cart / 'filtrati.json'
    punti = json.loads((f if f.exists() else cart / 'rilevati.json').read_text(encoding='utf-8'))
    tenuti = [p for p in punti if p.get('esito', 'tenuto') == 'tenuto']
    tenuti.sort(key=lambda p: -p['punteggio'])
    tenuti = fondi_doppioni(tenuti)
    usati = tenuti[:MAX_USO]

    fatto = [0]

    def suolo(p):
        try:
            p['suolo'] = indicatori(p['lat'], p['lon'], p['raggio'])
            p['classe'] = classe(p['suolo'])
            p['vincolo_m'] = distanza_vincolo(p['lat'], p['lon'])
        except Exception as e:
            p['classe'] = 'sconosciuto'
            print('uso del suolo non riuscito:', e)
        fatto[0] += 1
        st['avanzamento'] = [fatto[0], len(usati)]
        scrivi_stato(st)
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
    fase(4, [0, min(max_fogli, len(buoni))])
    disegnati = [0]

    def disegna(ip):
        i, p = ip
        p['posizione'] = i
        if i <= max_fogli:
            p['foglio'] = f'fogli_rilievo/{i:02d}.png'
            foglio(p['lat'], p['lon'], FINESTRA, cart / p['foglio'])
            disegnati[0] += 1
            st['avanzamento'] = [disegnati[0], min(max_fogli, len(buoni))]
            scrivi_stato(st)
        return p

    with ThreadPoolExecutor(3) as ex:
        buoni = list(ex.map(disegna, enumerate(buoni, 1)))
    (cart / 'pipeline.json').write_text(json.dumps(buoni), encoding='utf-8')
    nuovi = [{'lat': p['lat'], 'lon': p['lon'], 'raggio': p['raggio'], 'punteggio': round(p['punteggio'], 2), 'posizione': p['posizione']}
             for p in buoni if p['regola_c'] and not p.get('gia_noto')]
    st['fatti'].append({'nome': nome, 'lat0': st['lat0'], 'lon0': st['lon0'], 'righe': st['righe'], 'colonne': st['colonne'],
                        'rilevati': len(punti), 'valutati': len(usati), 'nuovi': nuovi, 'fine': time.time()})
    st.update(attivo=False, fase=len(FASI), avanzamento=None)
    scrivi_stato(st)
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
