# STEP 9 — Modifiche non documentate

## Perimetro e metodo

Sono stati confrontati integralmente:

- `inputs/supporting/DIFF_v1.0_to_v1.1.patch` — 1.731 righe, 48 hunk;
- ADD v1.1 §8 (`AM-01`–`AM-28`, §8.0–§8.2);
- `inputs/supporting/DELTA_MANIFEST.json` — 28 emendamenti, sezioni/contratti/stati/transizioni dichiarati.

Per ogni hunk è stata individuata la sezione di destinazione nella v1.1 e verificata la corrispondenza con almeno una riga `AM-*` o, per le sole informazioni trasversali di versione e limitation, con §8.1/§8.2. La presenza nel diff non è stata confusa con sostanzialità: rinumerazioni, version bump già dichiarati e rinforzi dell'evidence fence non sono modifiche architetturali autonome.

## Copertura diff → Amendment Log

| Superficie modificata nel diff | Copertura dichiarata in §8 | Esito |
|---|---|---|
| §1.4 e §3.0–§3.0.4 — Governed Context Set, marking, naming, versioni | `AM-01`, `AM-12`, `AM-20`, `AM-21`; §8.1 | `COVERED` per la sostanza |
| §2.1–§2.5 — percorso canonico, single writer, C4, capability dispositions | `AM-02`, `AM-03`, `AM-11`, `AM-15`, `AM-16` | `COVERED`, con un locator incompleto su §2.2 (nota sotto) |
| §2.6 — Backend Assumption Register | `AM-28` | `COVERED` |
| §3.1.1–§3.6 — metamodel, envelope, OpenAPI, Protobuf, MCP | `AM-01`, `AM-04`, `AM-05`, `AM-08`, `AM-10`–`AM-12`, `AM-14`, `AM-19`–`AM-22`, `AM-25`, `AM-27` | `COVERED` |
| §3.7–§3.9 — Action/Event Contract e conformance target | `AM-02`, `AM-09`, `AM-23` | `COVERED` |
| §4.1–§4.3 — FSM, guardie, causal reason code, GCS, lease | `AM-01`, `AM-02`, `AM-06`, `AM-07`, `AM-16`, `AM-18`, `AM-24`, `AM-26` | `COVERED` |
| §5.1–§5.3 — policy validity, Capability Lease, marking algebra | `AM-01`, `AM-04`, `AM-12`, `AM-16`, `AM-21`, `AM-22` | `COVERED` |
| §6.1, §6.3 — slice `CAP-024` e osservabilità GCS | `AM-01`, `AM-17` | `COVERED` |
| §7–§7.3 — allocazione completa, scope fence, `EV-*`, evidence fence | `AM-13`, `AM-17`, `AM-23`; §8.2 | `COVERED` |
| §8 — log, self-reported defect, versioni e limitation | nuova sezione dichiarata nel manifest | `COVERED` |

## Deviazioni rilevate

### `UC-01` — §1.1 modificata ma non inclusa in alcun locator `AM-*`

I primi due hunk (`@@ -5,12 +5,16 @@` e `@@ -25,7 +29,9 @@`) modificano §1.1 con origine della revisione, stato `PROPOSED — PENDING CHANGE CONTROL`, riferimento alle bozze e una dichiarazione sul numero di emendamenti soggetti a decisione. Nessuna riga di §8 include §1.1 fra le «Sezioni modificate» e `DELTA_MANIFEST.json` non attribuisce questa modifica a un `AM-*`.

La modifica è materiale per il change control perché il testo aggiunto afferma «Sette emendamenti» mentre le righe con `CC = Sì` sono nove: `AM-01`, `AM-02`, `AM-03`, `AM-04`, `AM-06`, `AM-07`, `AM-09`, `AM-12`, `AM-16`. Il difetto coincide con `DRF-010` della FASE 1; non viene duplicato.

- Classificazione: modifica di document control non completamente registrata, non nuova scelta architetturale.
- Impatto: sottostima la superficie che richiede change control e rende §1.1 non riconciliabile con §8 e con le nove bozze.
- Remediation esatta: aggiungere §1.1 ai locator degli emendamenti che ne aggiornano il controllo (o una riga `AM-*` amministrativa senza nuova decisione) e sostituire «Sette» con «Nove», facendo derivare il conteggio dalle righe `CC = Sì`.
- Finding correlato: `DRF-010`, `MINOR`, origine `NEW_IN_V1.1`.

### `UC-02` — locator incompleto di `AM-02` per §2.2

Il hunk `@@ -179,7 +199,7 @@` modifica la riga `C3` di §2.2 dichiarando che la commit request governata è «emessa da `C6`». La natura di `AM-02` descrive espressamente `C6`→`C3`, quindi la modifica non è nascosta; tuttavia la colonna «Sezioni modificate» di `AM-02` elenca §2.1, §2.5 r.10, §3.7, §4.1 e §4.1.2, omettendo §2.2. La stessa riga cambia inoltre «writer lease» in `writer_epoch`, sostanza coperta da `AM-16`, che invece elenca correttamente §2.2.

- Classificazione: errore di locator, non modifica sostanziale assente dal log.
- Impatto: un reviewer che segua solo i locator di `AM-02` non esamina una sua modifica normativa.
- Remediation esatta: aggiungere §2.2 alla riga `AM-02`; mantenere §2.2 anche in `AM-16` per la distinta correzione terminologica.
- Disposition: assorbito nel problema di accuratezza del change log; nessun finding autonomo oltre `DRF-010`.

## Esito

Non sono state trovate modifiche **architetturali sostanziali** completamente assenti sia dall'Amendment Log sia dal `DELTA_MANIFEST`. È stata trovata una modifica materiale di document control non attribuita a un emendamento (`UC-01`) e un locator incompleto (`UC-02`). Il finding sopravvissuto è `DRF-010`; non si moltiplica il conteggio per due manifestazioni della stessa carenza di change-control accuracy.

Questo controllo non approva gli emendamenti, non assegna `DEC-*`, non incrementa `E1`/`E2` e non trasforma le bozze in baseline.
