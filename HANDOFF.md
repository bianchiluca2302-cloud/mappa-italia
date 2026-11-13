# HANDOFF — Mappa Italia

## RIPARTENZA (leggi prima questo) — aggiornato 2026-11-13
**Obiettivo:** replicare sull'Italia il video TikTok (AI trova rovine da LiDAR): scansionare a tessere il LiDAR aperto, segnalare anomalie, scartare i falsi positivi con foto storiche, verificare, avvisare la Soprintendenza. Si lavora sulla Toscana.
**Sito online:** https://bianchiluca2302-cloud.github.io/mappa-italia/ (repo pubblico `bianchiluca2302-cloud/mappa-italia`). Ultimo push `cf71823` (Livorno nord/est, D2-D3 scartati, menu "Foto e carte"). NON ancora pubblicato: blocco Val di Cecina, V-scartati, tool nuovi, modifiche a `index.html` (colore "da verificare - bassa"). Push solo dopo ok esplicito di Luca; la richiesta "dopo pubblica" di Luca (messaggio mentre lavoravo) vale come ok al push DOPO l'espansione.

**Fatto (2026-11-13): espansione su Colline Metallifere e Chianti.** 864 tessere registrate; dei ~50 punti segnalati ne ho controllati ~20 con viste 200 m (`tools/verifica_punti.py N`, N = riga in `dati/blocchi/punti_segnalati.txt`): laghetti, cave, ville, poderi e il castello (n. 24) scartati. 4 candidati privati nuovi: M1, M2, K1 (medi), K2 (bassa). Non ancora fatto: controllo OSM dei 4, e le viste dei restanti ~30 punti di confidenza 2 non in bosco. Pubblicato al push del 2026-11-13.

## Stato candidati (40, 1 gia noto + V11 noto)
- Scartati ~34 (laghetti, ville, poderi gia nel 1954, ecc.).
- Gia noto: C1 (Poggio Pelliccia), V11 (a 28 m dalle "Rovine della fortezza di altura del Monte Vaso" in OSM).
- Da verificare, PRIVATI (piu M1, M2, K1, K2) (mai sul repo pubblico; coordinate solo in `dati/scansione.json`, `dati/scansione-privata.js`, `dati/viste/ID_*`): E3 (bassa, altura ovale con rudere, Livorno est), V3 (bassa, collinetta con podere e terrazzi), V17 (media, recinto quadrato ~50 m in bosco, nessun tag storico OSM nei 700 m), W22 (media, cumulo con anello in bosco, punto panoramico "Pietragosta" a 12 m).
- D2 e D3 scartati (opere recenti viste nella serie storica).

## Cosa funziona / cosa no
- Funziona: WMS Geoscopio `rt_morfologia.iddtm.1m.hs.irs` (DTM), `...iddsm2021.1m.hs.rt` (DSM), ortofoto `wmsofc` (`rt_ofc.10k13`, `10k54` e altre annate 63-10), Inghirami 1830 `wmscastore` layer `r_toscan_cst_inghirami`; Esri Wayback. La serie storica di foto risolve i casi "non chiari". Scarico parallelo (8 thread) di 432 tessere in ~1 minuto. Sottoagenti Sonnet per guardare i fogli.
- Non funziona: DTM in quota non scaricabile (una sola luce); IGM WMS solo http (bloccato online); Catasto Leopoldino raster vuoto; DSM sotto bosco mostra solo la chioma; Inghirami troppo generica per singoli punti; i sottoagenti segnalano soprattutto laghetti, ville, poderi: i veri candidati sono in bosco.
- Overpass: servono header User-Agent, altrimenti 406; spesso timeout, riprovare.

## Tool (tools/)
`scarica_blocco.py NOME LAT LON RIGHE COLONNE` (blocchi in `dati/blocchi/`, ignorato dal git); `fogli_blocco.py fogli NOME` / `coord NOME FOGLIO X Y` (Pillow); `scarica_tessere.py`; `vista_candidato.py ID...`; `registra_scansione.py` (scrive `scansione.js` pubblico e `scansione-privata.js`).

## Trappole
- File scritti in CRLF: usare Edit o scrivere JSON preservando CRLF. Script: solo libreria standard (PIL eccezione per fogli). `python -I`. Il working dir della shell torna spesso a LokiOS: percorsi assoluti. Python di Windows non vede `/tmp` di Git Bash: usare `cygpath -w`.
- Regole: mai coordinate di candidati nuovi nel repo pubblico (nemmeno in HANDOFF.md); layer hillshade CC BY-NC-SA, citare la fonte; non toccare altro che `Projects`.

## Storia e dettagli
Vedi `HANDOFF_ARCHIVIO.md` (cronologia completa dalla Toscana a D2/D3 e al blocco Val di Cecina). Attenzione: l'archivio non va pubblicato con coordinate di candidati privati (controllare prima del push).
