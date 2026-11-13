# Mappa Italia — anomalie archeologiche da LiDAR

Replica sull'Italia l'idea del video in `riferimento/` (TikTok @imolelehmann: un'AI scansiona a tessere i dati
LiDAR pubblici NASA, segnala anomalie sotto la vegetazione, poi si verifica e si segnala alle autorita).

## Struttura
- `index.html` — mappa Leaflet dell'Italia con rilievo ombreggiato, griglia a tessere da 0,25 gradi
  (stato: da scansionare / scansionata / candidato), candidati con Maiusc+clic, esporta JSON. Stato in localStorage.
- `dati/` — dati scaricati (DTM/LiDAR, siti noti). Non versionare i file grandi.
- `riferimento/` — fotogrammi del video.

## Regole
- Script Python: solo libreria standard, Windows, Python 3.11.
- Mai pubblicare le coordinate esatte di un candidato: come nel video, prima si avvisa la Soprintendenza.
