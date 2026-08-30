# STEP 5 — FSM, guardie e safety dell'azione

## Esito sintetico

La famiglia `ACT-T01`–`ACT-T31` è contigua e tutti i 29 stati nominati dalla tabella compaiono anche nel diagramma. Tutti gli stati sono raggiungibili dal percorso iniziale e gli stati di indeterminatezza sono terminali per scelta esplicita. Tuttavia il controllo automatico chiamato “bijezione” confronta **insiemi di nomi di stato**, non archi e transizioni: la corrispondenza edge-level dichiarata dal testo non sussiste. Soprattutto, la rivalidazione al momento dell'emissione copre `G-DISPATCH` ma non `G-FRESHNESS`, lasciando una finestra di stale-context execution.

## Diagramma e tabella

| Controllo | Esito | Nota |
|---|---|---|
| Stati diagramma ↔ stati tabella | `PASS` | 29 stati in comune, confermato dal harness |
| Contiguità `ACT-T*` | `PASS` | `T01`–`T31`, incluse `T21a/b/c` |
| Raggiungibilità | `PASS` | Nessuno stato isolato nel grafo dichiarato |
| Terminalità attesa | `PASS WITH CONDITION` | Indeterminatezza terminale è intenzionale, ma manca la disposizione operativa di adjudication/unblock |
| Bijezione arco ↔ transizione | `FAIL` | Il claim è più forte di ciò che diagramma e tabella realizzano |

Evidenza della non-bijezione:

- `ACT-T09`, `ACT-T10`, `ACT-T17`, `ACT-T20`, `ACT-T21a`, `ACT-T21c`, `ACT-T23` e `ACT-T31` aggregano più destinazioni o più origini in una singola riga, mentre il diagramma usa archi distinti;
- `ACT-T02` (stato invariato), il retry `ACT-T19` e gli esiti “resta unknown” di `ACT-T20`/`T21c` non hanno un arco corrispondente;
- `ACT-T22` indica come condizione/origine “Execution confermata” e porta direttamente a `OUTCOME_ASSESSED`, mentre il diagramma richiede prima `EXECUTION_CONFIRMED → OUTCOME_PENDING` (`ACT-T27`) e poi `OUTCOME_PENDING → OUTCOME_ASSESSED`; la riga non nomina `OUTCOME_PENDING` come origine.

Classificazione: `DRF-006`, `MAJOR`, confidence `HIGH`, locator §4.1 diagramma e §4.1.2; related `AM-18`, `ACT-T02`, `ACT-T19`–`T23`, `ACT-T27`, `ACT-T31`.

Remediation esatta: adottare una riga per ogni arco con colonne `source_state`, `event`, `guard`, `effect`, `destination_state`; rappresentare esplicitamente self-loop/no-transition; correggere `ACT-T22` con origine `OUTCOME_PENDING`; modificare il harness affinché confronti tuple `(source,destination)` e non soli nomi di stato.

## Rivalidazione al momento dell'emissione

`ACT-T12` valuta `G-FRESHNESS ∧ G-DISPATCH` e crea il command. Le emissioni successive:

- `ACT-T14` e `ACT-T29` rivalidano soltanto `G-DISPATCH`;
- `ACT-T19` elenca un sottoinsieme ad hoc (`same key`, fencing, `stop_epoch`, audit e budget), senza richiamare integralmente né `G-DISPATCH` né `G-FRESHNESS`.

Durante `predispatch_fence_ttl` possono cambiare canonical revision/commit, policy digest, Authority, Approval set, ontology release, adapter binding o watermark. Lo stop è rivalidato, ma un command può ancora essere emesso con contesto divenuto stale. Sul retry mancano inoltre, nel testo della guardia, circuit breaker, adapter conformance e command deadline che fanno parte di `G-DISPATCH`.

Classificazione: `DRF-004`, `CRITICAL`, confidence `HIGH`, locator §4.1.1 `G-FRESHNESS`/`G-DISPATCH`, §4.1.2 `ACT-T12`, `T14`, `T19`, `T29`; related `AM-06`, `DRAFT-E`, `RSK-037`, `RSK-050`, `RSK-054`.

Remediation esatta: guardare ogni emissione fisica (`T14`, `T19`, `T29` e ogni compensation command) con `G-FRESHNESS ∧ G-DISPATCH` rivalidate atomicamente rispetto all'acquisizione del delivery lease/fencing token; confrontare i digest col `GatePackage`; su drift transitare a `INVALIDATED` senza invio. Il retry deve richiamare le guardie nominate, non duplicarne un sottoinsieme.

## `G-FRESHNESS` e stati indeterminati

La scelta di non inferire un esito dall'assenza di risposta è corretta e chiude il deadlock nominale con `ACT-T24`/`T25`. La disposizione resta però incompleta:

- `EXECUTION_INDETERMINATE` e `COMPENSATION_INDETERMINATE` sono terminali e non hanno una transizione/record normativo di adjudication;
- `ACT-T24` dice che il blocco resta finché un Principal umano adjudica, ma non specifica Authority, evidenza minima, esiti possibili, audit record o effetto dell'adjudication sul predicato di `G-FRESHNESS`;
- la chiave di conflitto è “stesso `aggregate_ref` e stesso target esterno”, ma `ActionInstance.action_target` distingue solo `EXTERNAL_ADAPTER` e `CANONICAL_COMMIT`; non identifica risorsa, adapter binding o footprint dell'effetto. Di conseguenza due azioni indipendenti sullo stesso aggregate possono essere bloccate come se confliggessero.

Classificazione: `DRF-007`, `MAJOR`, confidence `HIGH`, locator §4.1.1 `G-FRESHNESS`, §4.1.2 `ACT-T24`/`T25`, testo successivo; related `AM-07`, `DRAFT-F`, `FR-163`, `RSK-023`, `RSK-050`.

Remediation esatta: introdurre un `IndeterminateEffectAdjudication` append-only con authority, evidence set, outcome (`CONFIRMED`, `FAILED`, `UNRESOLVED_ACCEPTED_RISK`), scope e audit; definire come produce una nuova istanza/stato senza riscrivere lo storico terminale. Sostituire il blocco coarse con una `conflict_scope` dichiarata dall'ActionType (target resource, effect domain e aggregate members), mantenendo fail-closed quando il footprint non è calcolabile.

## Percorso `CANONICAL_COMMIT`

Non esiste una seconda via esplicita da `C5` o `C7` a un commit canonico: §2.5 regola 10 e gli archi `C6→C3` sono coerenti. La nuova via non è quindi una scorciatoia topologica. È però una scorciatoia **di policy** finché lo schema accetta `R1_ANALYZE/approval=NONE` (`DRF-003`) e non lega in modo tipizzato Claim/Evidence/Decision alla commit request (`DRF-008`).

La FSM è pertanto nominalmente unica ma non ancora sufficientemente governata per sostenere il claim “stesso Human Gate” in ogni istanza valida.
