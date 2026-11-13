# HANDOFF — Mappa Italia

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

## Da fare, in ordine
1. Fonte dati LiDAR/DTM italiana: Geoportale Nazionale (PST, DTM 1-2 m, copertura parziale) e geoportali regionali
   (Toscana, Emilia-Romagna, Veneto, Lombardia, Piemonte, Friuli...). Verificare licenza e come scaricare a tessere.
2. Layer dei siti gia noti (Wikidata/OSM `historic=archaeological_site`, Vincoli in Rete) per scartare i falsi positivi.
3. Pipeline: tessera DTM -> rilievo (hillshade/SVF) -> Claude guarda l'immagine e segnala anomalie -> candidati.
4. Verifica a mano di ogni candidato prima di qualsiasi segnalazione.

## Note
- Il video usa dati NASA sulla giungla Maya: in Italia la copertura LiDAR e a macchia, quindi si parte dalle regioni con dati aperti.
