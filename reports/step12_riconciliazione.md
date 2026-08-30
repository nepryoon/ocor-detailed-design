# STEP 12 — Riconciliazione dei finding

## Esito

La riconciliazione conserva **15 finding**: 2 `BLOCKER`, 4 `CRITICAL`, 7 `MAJOR` e 2 `MINOR`. Per origine: 8 `NEW_IN_V1.1`, 6 `SURVIVING_FROM_V1.0`, 1 `REGRESSION`. Quattordici hanno disposition `VALID`; `DRF-012` ha disposition `SOURCE_LIMITATION`, ma resta nel registro perché la contraddizione della baseline è riprodotta nello scope fence dell'ADD e impedisce al DDD di scegliere legittimamente una realizzazione.

Sono stati eliminati duplicati e separati i temi che hanno failure mode diversi. Nessun finding deriva dalla sola assenza di evidenza: `E1=0`, `E2=0` e zero requisiti `Verified` restano invariati.

## Registro riconciliato

| ID | Severity | Confidence | Origine | Disposition | Nucleo sopravvissuto | Provenienza della verifica |
|---|---|---|---|---|---|---|
| `DRF-001` | `BLOCKER` | `HIGH` | `SURVIVING_FROM_V1.0` | `VALID` | La tabella GCS dichiara copertura universale falsa: tra l'altro `QueryContext` non contiene `classification_marking_ref`; Scenario, Handoff, Security e trace usano forme di dominio diverse e/o omettono campi dichiarati coperti. | FASE 1; `ARF-001`; STEP 8; controllo indipendente |
| `DRF-002` | `CRITICAL` | `HIGH` | `NEW_IN_V1.1` | `VALID` | `principal_id` viene equiparato al producer dichiarato nel body senza binding normativo al Principal di trasporto. | FASE 1; STEP 8 |
| `DRF-003` | `CRITICAL` | `HIGH` | `NEW_IN_V1.1` | `VALID` | Lo schema Action accetta `CANONICAL_COMMIT`, `R1_ANALYZE`, `approval.mode=NONE`. | Conformance test FASE 1; STEP 8 |
| `DRF-004` | `CRITICAL` | `HIGH` | `SURVIVING_FROM_V1.0` | `VALID` | `G-FRESHNESS` non è rivalidata alle emissioni `T14`/`T29` né al retry `T19`; quest'ultimo non richiama neppure tutto `G-DISPATCH`. | FASE 1; `ARF-006`; STEP 8 |
| `DRF-005` | `CRITICAL` | `HIGH` | `NEW_IN_V1.1` | `VALID` | Il nuovo metamodel ammette semantica `PERMISSION`, ma §5.3 applica sempre gli operatori da restrizione. | FASE 1; STEP 8 su `ARF-004`/`012` |
| `DRF-006` | `MINOR` | `HIGH` | `SURVIVING_FROM_V1.0` | `VALID` | Il claim di bijezione diagramma↔tabella è falso a livello di archi; `T22` confligge materialmente con il percorso via `OUTCOME_PENDING`. | FASE 1; `ARF-018`; STEP 8. Downgrade da `MAJOR`: molte divergenze sono aggregazioni/self-loop, non lifecycle alternativi |
| `DRF-007` | `MAJOR` | `HIGH` | `NEW_IN_V1.1` | `VALID` | L'over-correction degli stati indeterminati usa una conflict key coarse e promette adjudication senza record, authority, esiti e unblock. | FASE 1; `ARF-007`; STEP 8 |
| `DRF-008` | `MAJOR` | `HIGH` | `NEW_IN_V1.1` | `VALID` | Il binding canonical non lega Claim, Evidence, Decision e revision al parameters schema; l'error model non distingue i rifiuti `C3`. | FASE 1; STEP 8 |
| `DRF-009` | `MAJOR` | `HIGH` | `REGRESSION` | `VALID` | `BA-01` presenta come adapter-only un fallback che perde l'atomicità e richiede la riscrittura di §2.3. | FASE 1; STEP 10: precedente `PASS` sulla sostituibilità scende a `PASS WITH CONDITION` |
| `DRF-010` | `MINOR` | `HIGH` | `NEW_IN_V1.1` | `VALID` | I conteggi di document/change control non sono derivati: “sette” emendamenti contro nove `CC=Sì`; `AM-13` dichiara 182 `DEC`, mentre lo stato è 181 e quello corretto dopo `DRF-015` sarebbe 183. | FASE 1; STEP 9; STEP 11 |
| `DRF-011` | `MAJOR` | `MEDIUM` | `NEW_IN_V1.1` | `VALID` | Il DAG delle bozze omette almeno la dipendenza di `E` dal percorso `T29` introdotto da `B` e quella di `F` dal contratto Action introdotto da `G`; `E→I` richiede conferma dell'authority. | FASE 1; controllo indipendente |
| `DRF-012` | `BLOCKER` | `HIGH` | `SURVIVING_FROM_V1.0` | `SOURCE_LIMITATION` | `DEC-103`/`FR-095` congelano AAP come `P0/PoC`, mentre `DEC-196` differisce `ELM-070` e l'ADD respinge ogni caso positivo. | STEP 11; confronto baseline/ADD v1.0/v1.1 |
| `DRF-013` | `MAJOR` | `HIGH` | `SURVIVING_FROM_V1.0` | `VALID` | `ObjectSnapshot.required` omette relazioni, incertezza e spiegazione che `FR-007` richiede per ogni risultato. | `ARF-014`; STEP 8; STEP 11 |
| `DRF-014` | `MAJOR` | `HIGH` | `NEW_IN_V1.1` | `VALID` | `AM-17` chiama `NFR-078` differito e afferma che nessun P0/`DEVE` lo è; il registro lo classifica `Confermato`, `P0`, release MVP. | STEP 11; diff v1.0→v1.1 |
| `DRF-015` | `MAJOR` | `HIGH` | `SURVIVING_FROM_V1.0` | `VALID` | §7 classifica `DEC-173` e `DEC-175` come gate non allocabili, benché siano decisioni sostantive su superfici per ruolo e conformance kit. | `ARF-013`; STEP 8; STEP 11 |

## Decisioni di consolidamento

| Candidati/manifestazioni | Decisione |
|---|---|
| `DRF-001` e `DRF-002` | Separati: completezza cross-contract e authority binding hanno impatti e remediation distinti. |
| `DRF-003` e `DRF-008` | Separati: il primo è un bypass safety riprodotto; il secondo è incompletezza semantica del binding/error model. |
| Problemi `ARF-004` e `ARF-012` | Consolidati in `DRF-005`: stessa contraddizione enum↔algebra. |
| `BA-01` in FASE 1 e regressione STEP 10 | Un solo `DRF-009`, con origine finale `REGRESSION`. |
| `UC-01`, “sette/nove” e `AM-13` 182/181/183 | Consolidati in `DRF-010` come inaccuratezza dei conteggi; la sostanza delle `DEC` orfane resta `DRF-015`. |
| `S11-03` e residuo `ARF-013` | Consolidati in `DRF-015`. |
| `UC-02` — locator §2.2 omesso da `AM-02` | Non autonomo: errore di locator senza modifica sostanziale nascosta; documentato nello STEP 9. |
| `NFR-007`/`NFR-009` con soglie `TBD` | Non finding ADD: `SOURCE_LIMITATION`, correttamente non provata; criteri `NOT EVALUABLE` finché non congelati. |
| Shorthand `OI-022/004`, `NFR-065/008` | Non finding ADD: limitazione minore del registro sorgente, documentata nello STEP 11. |

## Chiusura dei finding precedenti dopo riconciliazione

| Stato | Conteggio |
|---|---:|
| `CLOSED` | 16 |
| `PARTIALLY_CLOSED` | 4 |
| `CLOSED_WITH_NEW_DEFECT` | 6 |
| `OVER_CORRECTED` | 1 |
| `NOT_CLOSED` | 0 |
| **Totale** | **27** |

Le undici righe non `CLOSED` sono `ARF-001`, `ARF-002`, `ARF-004`, `ARF-006`, `ARF-007`, `ARF-009`, `ARF-012`, `ARF-013`, `ARF-014`, `ARF-017`, `ARF-018`. La presenza di un emendamento non viene equiparata alla chiusura del finding.

## Gate risultante

Il gate resta **`NOT READY FOR DDD`**. `DRF-001` impedisce di generare una forma univoca del contesto governato; `DRF-012` lascia al DDD una scelta di baseline che richiede change control. I quattro `CRITICAL` espongono inoltre authority ambiguity, bypass del Human Gate, stale-context execution e algebra marking non conservativa. Nessuna di queste conclusioni approva bozze, assegna nuove decisioni o cambia lo stato probatorio.
