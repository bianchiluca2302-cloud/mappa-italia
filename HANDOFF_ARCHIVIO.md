# HANDOFF — Mappa Italia

## RIPARTENZA (leggi prima questo) — aggiornato 2026-11-13
**Obiettivo:** replicare sull'Italia il video TikTok (AI trova rovine Maya da LiDAR NASA): scansionare a tessere il LiDAR aperto, segnalare anomalie, scartare i falsi positivi, verificare a mano. Si parte dalla Toscana.
**Stato:** pagina online https://bianchiluca2302-cloud.github.io/mappa-italia/ (repo pubblico, ultimo push con Livorno e C5-C8; push solo con ok di Luca). Locale: `index.html` (parametro `?v=lat,lon,zoom`).
**Richiesta in corso:** Luca ha scelto "Guardare D2 e D3 piu da vicino" (candidati privati, vedi sezione Colline). Non ancora fatto. Piano: (1) rileggere `dati/scansione.json` per le coordinate; (2) scaricare con `tools/scarica_tessere.py` o GetMap la tessera/finestra piu stretta (100 m, 800 px) di D2 e D3 con DTM e DSM; (3) ortofoto 2013 e 1954 a quella scala, piu le altre annate `rt_ofc.10k75/78/88/96/99/00..10` per vedere quando compare/scompare il recinto; (4) cercare indizi: toponimi (OSM/IGM), carta geologica, sentieri, strade storiche; (5) giudizio finale e aggiornare `scansione.json` + `registra_scansione.py`. Niente push con D2/D3.
**Cosa ha funzionato:** WMS Geoscopio con layer `rt_morfologia.iddtm.1m.hs.irs`, DSM 2021 `...iddsm2021.1m.hs.rt`, ortofoto `wmsofc` (`rt_ofc.10k13`, `10k54`); la foto 1954 scarta quasi tutte le opere moderne; fogli 2x2 con reticolo ogni 200 px per coordinate precise; screenshot con Chrome headless (`--headless=new --allow-file-access-from-files --virtual-time-budget=20000 --screenshot=...`).
**Cosa NO:** DTM in quota non scaricabile (niente luci multiple); `rt_ofc.2k15/2k16/2k17` vuote; nessun WMS pubblico dei vincoli trovato; foglio ridotto = coordinate imprecise.
**Trappole:** i file scritti sono CRLF, sostituzioni testo con Python falliscono: usare lo strumento Edit. Script del progetto: solo libreria standard (PIL solo a mano per i fogli). `python -I`. Il working dir del shell torna spesso a LokiOS: usare percorsi assoluti.
**Regole:** mai coordinate di candidati nuovi sul repo pubblico; D2 e D3 solo in `dati/scansione.json` (ignorato), `dati/scansione-privata.js` (ignorato), `dati/viste/D2_*`, `D3_*` (ignorati). Layer hillshade CC BY-NC-SA, citare la fonte.

## Fatto (2026-11-13)
- Cartella creata, `index.html` con mappa Italia + griglia + candidati (da aprire a doppio clic, serve internet per le tessere).

## Toscana (2026-11-13)
- Fonte trovata: WMS Geoscopio Regione Toscana, licenza CC BY.
  `https://www502.regione.toscana.it/wmsraster/com.rt.wms.RTmap/wms?map=wmsmorfologia`
  Layer: `rt_morfologia.iddtm.1m.hs.irs` (DTM 1 m ombreggiato), `rt_morfologia.iddtm.1m.irs` (DTM 1 m), `rt_morfologia.iddsm2021.1m.rt` (DSM).
  Supporta EPSG:4326 e 3857. Provato un GetMap: funziona. Metadati: voli LiDAR 2019-2021; la copertura va verificata a zone.
- Le immagini GetMap hanno una scritta di fonte a sinistra: ritagliarla prima di darle da analizzare.
- Layer inserito in `index.html` (visibile da zoom 11), vista centrata sulla Toscana.

## Siti noti (2026-11-13)
- `tools/scarica_siti_noti.py` scarica da OpenStreetMap (Overpass) i siti archeologici della Toscana: 480 punti in `dati/siti-noti.js` e `.json`.
- Layer "Siti noti (OSM)" in `index.html`. Fonte parziale: OSM non e il censimento ufficiale. Da aggiungere Wikidata e Vincoli in Rete.

- Wikidata: `tools/scarica_siti_wikidata.py` (riquadro Toscana, tipi: sito archeologico, rovine, fortezza di collina...), 338 punti in `dati/siti-wikidata.js`; 252 non hanno un sito OSM entro 300 m. Layer blu in `index.html`. Il server Wikidata va spesso in timeout: lo script riprova da solo.
- Vincoli ufficiali (MiC Vincoli in Rete, Geoscopio): NON trovato un WMS/WFS pubblico. Provati a caso i nomi `map=` di Geoscopio, nessuno esiste; la ricerca nel Geonetwork regionale da fuori da 403. Da cercare a mano nel portale o chiedere alla Soprintendenza.

## Scansione di prova (2026-11-13)
- Il LiDAR 1 m toscano NON copre tutto: manca gran parte della costa (es. Val di Cornia 43.0N 10.5E tessere vuote). Mappa in `dati/copertura-1m.png` (layer "Copertura 1 m").
- `tools/scarica_tessere.py LAT LON [righe] [colonne]` scarica tessere 1 km in `dati/tessere/` (scritta di fonte a sinistra, ~25 px).
- Zona provata: 42.90N 11.00E, 6 tessere (5 con dati). Esito in `dati/scansione.json`; `tools/registra_scansione.py` lo trasforma in `dati/scansione.js` e calcola il sito noto piu vicino.
- 4 candidati: C1 (media) coincide a 5 m col Tumulo Etrusco di Poggio Pelliccia, gia noto: il metodo ritrova un sito vero. C2, C3 (basse) e C4 (molto bassa, probabile opera moderna) non verificati.
- Limite: guardo un solo rilievo ombreggiato (una luce); per essere serio servono piu direzioni di luce/SVF e un confronto con ortofoto.

## Verifica con foto aeree (2026-11-13)
- Il DTM in quota NON e scaricabile (solo WMS ombreggiato), quindi niente luci multiple. Alternative usate: DSM 2021 hillshade (`rt_morfologia.iddsm2021.1m.hs.rt`) e ortofoto Geoscopio `wmsofc`: `rt_ofc.10k13` (2013), `rt_ofc.10k54` (1954, utilissima per scartare opere moderne). Le `2k15/2k16/2k17` rispondono vuote.
- `tools/vista_candidato.py ID...` scarica 4 viste 300 m; i fogli 2x2 (rilievo, DSM, foto 2013, foto 1954) sono in `dati/viste/<ID>_foglio.png` (composti con PIL a mano, non e nello script).
- Esito: C1 = tumulo gia noto (Poggio Pelliccia); C2 casa colonica, C3 vecchia fattoria, C4 laghetto post-1954: tutti scartati. Nessun candidato nuovo in queste 6 tessere.
- Licenza: la scheda del layer hillshade dice CC BY-NC-SA (non commerciale, stessa licenza); la scheda del catalogo diceva CC BY. Uso personale ok; mai usarlo a scopo commerciale e citare la fonte.
- Prossimo miglioramento: automatizzare il confronto con la foto 1954 per scartare in serie, e allargare le tessere.

## Pubblicazione (2026-11-13)
- Online su GitHub Pages: https://bianchiluca2302-cloud.github.io/mappa-italia/ (repo pubblico `bianchiluca2302-cloud/mappa-italia`, ramo main, cartella radice). Per aggiornare: commit e push, la pagina si rifa in ~1 minuto. Prima di ogni push chiedere a Luca.
- Non pubblicati (`.gitignore`): `dati/tessere/` e `schermate/`. Pubblicati i fogli di confronto in `dati/viste/` (dati CC BY-NC-SA con fonte citata).
- Regola: coordinate di candidati NUOVI mai sul repo pubblico; oggi ci sono solo un sito noto e tre scartati.

## Scansione allargata, Livorno (2026-11-13)
- Luca ha chiesto di avvicinarsi a Livorno. Il LiDAR 1 m c'e solo a nord-est della citta (Montenero, colline livornesi, piana di Stagno): lungo la costa sotto 43.517N e a ovest di 10.317E le tessere sono vuote.
- 15 tessere con dati tra 43.526-43.553N e 10.317-10.355E, guardate in 4 fogli 2x2 ridotti (`dati/fogli/`, non pubblicati). Metà dei fogli e centro urbano: poco da vedere.
- 4 punti sospetti (C5-C8) controllati con DSM e foto 2013/1954: tutti scartati (campo arato, pendio con strada campestre, argine di vasca recente, piccola vasca). Totale finora: 8 candidati, 1 gia noto, 7 scartati, 0 nuovi.
- Lezione: dal foglio ridotto le coordinate escono imprecise (C5 fuori centro di decine di metri). Per segnalare un candidato rifare il punto sulla tessera intera a 1000 px.
- 16 tessere del Senese (42.864-42.900N, 10.975-11.024E) scaricate in `dati/tessere-senese/` ma NON guardate.

## Colline a est di Livorno (2026-11-13)
- 16 tessere (43.526-43.562N, 10.367-10.417E), tutte con dati, guardate in 4 fogli 2x2 con reticolo ogni 200 px (`dati/fogli/colline_*.png`, non pubblicati). Con il reticolo le coordinate escono precise. Molte cave e terrazzamenti.
- 6 punti sospetti (D1-D6) controllati con DSM e foto 2013/1954: D1, D4, D5, D6 scartati (frana con piste, affioramento roccioso con cava, tornante forestale, piccola cava con capanna nel 1954).
- D2 (recinto quadrato ~40 m in oliveto) e D3 (piattaforma triangolare ~45 m a un bivio di piste nel bosco) restano "da verificare - media": sono i primi candidati senza spiegazione ovvia. Non c'e nessun sito noto entro ~3 km.
- PRIVACY: D2 e D3 hanno `"privato": true` in `dati/scansione.json`. `tools/registra_scansione.py` li scrive solo in `dati/scansione-privata.js`; `scansione.json`, `scansione-privata.js` e i loro fogli `dati/viste/D2_*`, `D3_*` sono in `.gitignore`. Sul repo pubblico non vanno MAI. L'`index.html` in locale li mostra in arancione, online mancano.
- Totale: 14 candidati, 1 gia noto, 11 scartati, 2 da verificare. Prossimo passo logico: verifica sul campo o con chi conosce la zona (Soprintendenza) prima di qualunque segnalazione.

## Allargamento nord/est di Livorno (2026-11-13)
- Luca ha chiesto di espandere la scansione dalle caselle di Livorno. Scaricate 94 tessere (`tools/scarica_tessere.py`, ora salta le gia scaricate e segnala `VUOTA`): fascia est 43.526-43.607N x 10.417-10.491E (54) e fascia nord 43.562-43.607N x 10.317-10.417E (40). Tutte con dati; l'unico bordo senza dati e a sud-est (~43.52N, 10.46-10.49E).
- 24 fogli 2x2 con reticolo in `dati/fogli/ampio_*.png` (non pubblicati). Nord-ovest e pianura bonificata/urbano (Stagno, Pisa): niente. Est: cave, strade, industria. Poco terreno interessante.
- 8 punti (G1-G4 nord, E1-E3 e F1 est) controllati con DTM/DSM/foto 2013/1954: 7 scartati (casali e poderi gia nel 1954, colli boscati, affioramento). E3 (coordinate solo in `dati/scansione.json`, altura ovale ~60 m con gradino e rudere in cima) resta "da verificare - bassa", privato (`E3_*` in `.gitignore`). Sito noto piu vicino: Torretta Vecchia a 1,8 km.
- Totale: 22 candidati, 1 gia noto, 18 scartati, 3 da verificare (D2, D3 medi; E3 basso). Coordinate degli scartati nuovi nel registro pubblico `scansione.js`; non ancora pushato.
- Lezione: per i fogli della fascia nord i nomi file hanno lat/lon con arrotondamenti diversi dalla fascia est (43.5800 vs 43.5801, 10.3795 vs 10.3794): comporre i fogli leggendo l'elenco reale dei file.
- Prossimi passi: la Toscana sotto 43.52N a Livorno e vuota; per espandere ancora conviene a sud-est (Colline Metallifere, Val di Cecina) o tornare a D2/D3 (richiesta pendente).

## D2 e D3 da vicino (2026-11-13)
- Finestre 120 m a 720 px (DTM, DSM e ortofoto 1954, 1975, 1978, 1988, 1996, 1999, 2000, 2003, 2010, 2013; layer `rt_ofc.10k75/78/88/96/99/00/03/10`; `10k06` vuoto, `10k99`/`10k03` vuoti in alcune zone). Fogli `dati/viste/D2_stretto.png`, `D3_stretto.png` (ignorati dal git).
- D2: nel 1954 non c'e, nel 1975-1996 e una piattaforma quadrata con fossato in un oliveto nuovo: opera agricola (vasca/serbatoio). SCARTATO.
- D3: nel 1954 c'e la pista ma non la piattaforma, dal 1975 radura triangolare arginata: piazzola forestale. SCARTATO.
- Il confronto con la serie storica (non solo 1954 e 2013) e il metodo giusto: risolve i casi "non chiari".
- Totale: 22 candidati, 1 gia noto, 20 scartati, 1 da verificare (E3, bassa). Nessun candidato nuovo forte.

## Foto e carte storiche nel sito (2026-11-13)
- `index.html`: il tasto "Vista satellitare" e sostituito da un menu "Foto e carte" + cursore di trasparenza (una sola alla volta, sopra rilievo/LiDAR). Voci: satellite oggi (Esri) e Esri Wayback 2014/2016/2018/2020/2023; foto aeree Toscana 1954, 1963, 1965, 1968, 1975, 1978, 1988, 1996, 2000, 2003, 2010, 2013 (WMS `wmsofc`, a macchia: 63/65/68/03 non verificati); Carta geometrica della Toscana di Inghirami 1830 (WMS `wmscastore`, layer `r_toscan_cst_inghirami`, verificato); IGM 1:25.000 (Geoportale Nazionale, `CB.IGM25000.32,33`) solo in locale perche il server reindirizza a http e online il browser lo blocca.
- URL: `?s=1` apre in satellitare, `?f=ofc54` (o `ing`, `wb14`...) apre con quella voce.
- Corretto un bug: `griglia` era usata nel controllo dei layer prima di essere dichiarata (errore all'avvio, la pagina si fermava).
- Non trovato: Catasto Leopoldino raster (`r_toscan_raster_impianto_catasto_gr` in `wmscastore` risponde vuoto, forse serve altro livello di scala), nessuna carta IGM storica (prima levata) con WMS pubblico. Idee: Catasto Leopoldino da Castore, Catasto Napoleonico, carte IGM storiche da Geoportale.
- Testato con Chrome headless in locale (ofc54, ing, wb14 ok). Non ancora pushato.

## Blocco Val di Cecina / Volterra (2026-11-13)
- "Espandi molto": scaricato il blocco 43.34-43.50N x 10.58-10.88E, 432 tessere (418 con dati, 14 vuote ai bordi) con `tools/scarica_blocco.py val-cecina 43.34 10.58 18 24` (8 thread, ~1 minuto, 288 MB in `dati/blocchi/`, ignorato dal git; file `rRR_cCC.png`, riga 0 = sud, `blocco.json` con origine e passi).
- `tools/fogli_blocco.py fogli NOME` compone 107 fogli 2x2 con reticolo (`dati/blocchi/val-cecina/fogli/f_rRR_cCC.png`, richiede Pillow); `... coord NOME FOGLIO X Y` converte un pixel del foglio in lat/lon (provato).
- Metodo: 6 sottoagenti Sonnet (18 fogli ciascuno) hanno segnalato max 3 punti per foglio con confidenza 1-3 (~72 punti, 17 con confidenza 3, in `dati/blocchi/val-cecina/viste/punti.json` e `V*_foglio.png` con rilievo/DSM/foto 2013/1954 a 200 m). Verificati io i 17 piu forti.
- Esito: V1, V2, V4-V10, V12-V16 scartati (laghetti e vasche recenti, ville e poderi gia nel 1954). Restano da verificare, tutti PRIVATI (`V3_*`, `V11_*`, `V17_*` in `.gitignore`): V11 (cumulo con anello in bosco, media), V17 (recinto quadrato ~50 m in bosco, media; sito noto Molino Rasponi a 1,3 km), V3 (collinetta con podere e terrazzi concentrici, bassa).
- Lezione: i sottoagenti trovano soprattutto pozze d'acqua, ville e poderi: i veri candidati sono quelli dentro il bosco, dove la foto non spiega nulla. Per i prossimi blocchi dire ai sottoagenti di dare priorita a bosco e cime, e per ogni punto scartare in automatico quelli con edificio o acqua nel 2013/1954.
- Restano ~55 punti con confidenza 1-2 non verificati (nei fogli, non salvati): i piu interessanti sono quelli in bosco. Totale: 39 candidati, 1 gia noto, 34 scartati, 4 da verificare (E3, V3, V11, V17).
- Non pushato.

## Punti in bosco del blocco Val di Cecina (2026-11-13)
- Ripresi i 54 punti a confidenza 1-2 non verificati; filtro automatico (foto 2013 scura e verde nel centro) ne ha isolati 12 sotto bosco (`dati/blocchi/val-cecina/viste2/`, W1-W54 con `punti.json`).
- Esito: 11 scartati (boschetti su dossi e frane naturali, pendii, un laghetto, una zona di ville con terrazzi). Resta W22: cumulo conico ~40 m con anello concentrico e incavo, in bosco fitto, stessa forma di V11; privato (`W22_*` in `.gitignore`). Gli altri 42 punti non in bosco hanno nella foto 2013 casa, campo o acqua che li spiega: non controllati uno a uno.
- Totale: 40 candidati, 1 gia noto, 34 scartati, 5 da verificare (E3, V3, V11, V17, W22). V11 e W22 sono simili (cumulo con anello in bosco): potrebbero essere tumuli o carbonaie; la verifica vera e sul campo o con la Soprintendenza.
- Il DSM sotto bosco mostra solo la chioma: l'unico strumento utile per il bosco e il DTM LiDAR ombreggiato, con una sola luce.

## Da fare, in ordine
1. Fonte dati LiDAR/DTM italiana: Geoportale Nazionale (PST, DTM 1-2 m, copertura parziale) e geoportali regionali
   (Toscana, Emilia-Romagna, Veneto, Lombardia, Piemonte, Friuli...). Verificare licenza e come scaricare a tessere.
2. Layer dei siti gia noti (Wikidata/OSM `historic=archaeological_site`, Vincoli in Rete) per scartare i falsi positivi.
3. Pipeline: tessera DTM -> rilievo (hillshade/SVF) -> Claude guarda l'immagine e segnala anomalie -> candidati.
4. Verifica a mano di ogni candidato prima di qualsiasi segnalazione.

## Note
- Il video usa dati NASA sulla giungla Maya: in Italia la copertura LiDAR e a macchia, quindi si parte dalle regioni con dati aperti.
