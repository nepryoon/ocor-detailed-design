# FASE 3–5 — Correzioni normative della candidata

## Control

Oggetto: `reports/OCOR_Architectural_Design_Document_v1.2_Candidate.md`, derivata byte-for-byte dalla v1.1 prima delle modifiche. Baseline SHA-256: `3e7532c7101e80c74b511cedc56a0563ca0938a3fe259911a91245cb19dedc7f`.

Stato: `PROPOSED — AWAITING CHANGE CONTROL`. Le correzioni tecniche sono applicate soltanto alla candidata; `inputs/` è rimasta in sola lettura. `E1=0`, `E2=0`, zero `Verified`.

## Correzioni applicate

| Ordine causale | Finding | Correzione | Verifica intermedia | Disposizione |
|---:|---|---|---|---|
| 1 | `DRF-001/002` | `GovernedContext` unico, mapping di tutte le superfici, Principal da binding verificato, mismatch deny/quarantine | Principal coerente accettato; mismatch e binding non verificato respinti | `PENDING_CHANGE_CONTROL` |
| 2 | `DRF-005` | marking algebra per restriction/permission, valori unknown/incomparabili fail-closed, declassification separata | join restriction e permission positivi; misuse/unknown negati | `PENDING_CHANGE_CONTROL` |
| 3 | `DRF-003/008`, `V12-RF-002` | Action 1.1: canonical risk floor, Human Gate/Dual Control, quorum/ruoli, Evidence e binding completi, reason code C3 | canonical valido accettato; R1/NONE/missing binding respinti | `PENDING_CHANGE_CONTROL` |
| 4 | `DRF-004` | emission fence atomica su dispatch, retry e compensation; lease/audit/deadline/stop/policy/GatePackage | sei casi semantici, incluso drift e lease scaduta | `PENDING_CHANGE_CONTROL` |
| 5 | `DRF-007` | `ConflictScope` tipizzato e adjudication append-only authority/evidence-bound | scope incompleto descritto fail-closed; FSM terminale coerente | `PENDING_CHANGE_CONTROL` |
| 6 | `DRF-006` | FSM e tabella una riga per arco; `T22`/`T27` distinti | 44 tuple esattamente coincidenti; 31 famiglie contigue | `CLOSED_IN_CANDIDATE` |
| 7 | `DRF-013` | `ObjectSnapshot.required` completo | snapshot completo accettato; omissioni di relazioni/uncertainty/explanation respinte | `CLOSED_IN_CANDIDATE` |
| 8 | `V12-RF-001` | Event 1.1: replay window obbligatoria se replay ammesso e vietata altrimenti | quattro casi simmetrici | `CLOSED_IN_CANDIDATE` |
| 9 | `DRF-009` | `BA-01` alternativa architetturale, `NO-GO` e change control | classificazione e package espliciti | `PENDING_CHANGE_CONTROL` |
| 10 | `DRF-012/014` | `FR-095` candidata P0/MVP; `ELM-070` differita; `NFR-078` confermata P0/MVP fuori PoC | scope scan e change set registri esplicito | `PENDING_CHANGE_CONTROL` per `FR-095`; `CLOSED_IN_CANDIDATE` per `NFR-078` |
| 11 | `DRF-010/015` | decision coverage 183+13=196; allocazione proposta `DEC-173/175`; locator e conteggi | verifier: universo 693 e coverage completa secondo disposition | `PENDING_CHANGE_CONTROL` per riallocazione |
| 12 | `DRF-015` | Document Control, Amendment Log v1.1→v1.2 e versioni contrattuali | reference scan e evidence fence verdi | `CLOSED_IN_CANDIDATE` per difetti interni |

## Contratti risultanti

`signed-canonical-ir:1.0`, `canonical-ingestion-envelope:1.2`, OpenAPI `1.2.0`, Protobuf `ocor.registry.v1`, `mcp-tool-contract:1.2`, `action-type-contract:1.1`, `event-subscription-contract:1.1`.

Il verifier tool-backed intermedio estrae cinque JSON Schema Draft 2020-12 meta-validi, risolve 26 `$ref` OpenAPI su 25 component schema, compila Protobuf e parsa 17 triple Turtle. La suite candidata copre 31 rami JSON Schema (`4+11+11+2`, oltre allo schema senza condizionali) e tre rami OpenAPI con casi positivi e negativi.

## Checkpoint

La candidata non presentava `FAIL` al checkpoint di fine correzioni. Il validator OpenAPI 3.1 ufficiale resta `NOT_EXECUTED` perché non disponibile nell'ambiente; non è dichiarato superato. L'integrità della candidata viene consolidata soltanto nella fase finale con il file SHA256SUMS.
