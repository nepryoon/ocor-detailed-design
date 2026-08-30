# OCOR ADD v1.2 — Remediation Ledger

## Control

Oggetto: remediation candidata derivata da ADD v1.1 SHA-256 `3e7532c7101e80c74b511cedc56a0563ca0938a3fe259911a91245cb19dedc7f`.

Authority fence: nessun nuovo `DEC-*`; nessuna approvazione `DRAFT-*`; nessuna chiusura `OI-*`, `ASM-*`, `RSK-*`; `E1=0`, `E2=0`, zero `Verified`. `CLOSED_IN_CANDIDATE` significa soltanto che il difetto interno è corretto e testato nella candidata; non equivale ad approvazione di baseline.

## Findings

| Finding | Confermato? | Severity | Root cause | Sezioni coinvolte | Dipendenze | Change control? | Correzione candidata | Test di chiusura | Stato |
|---|---|---|---|---|---|---|---|---|---|
| `DRF-001` | Sì | `BLOCKER` | GCS dichiarato universale senza record canonico/mapping completo | §1.4, §3.0.1, §3.2–§3.5, §3.7–§3.8, §4.1–§4.3, §5.3, §6.3 | authority fence | Sì | `GovernedContext` canonico; inventario surface→field/origin/enforcement/mismatch | inventory completo + positivi/negativi per surface | `PENDING_CHANGE_CONTROL` |
| `DRF-002` | Sì | `CRITICAL` | Principal body equiparato al Principal autenticato | §1.4, §3.0.1, §3.2, §5.1 | `DRF-001` | Sì | `effective_principal_id` solo da transport; asserted source separata; mismatch deny/quarantine+audit | body/transport mismatch respinto | `PENDING_CHANGE_CONTROL` |
| `DRF-003` | Sì | `CRITICAL` | ramo canonical non impone risk floor/Human Gate | §3.7, §4.1, §5.4 | `DRF-008` | Sì | canonical ⇒ R2/R3, Human Gate/Dual Control, quorum/ruoli non vuoti | R0/R1/NONE respinti; caso valido accettato | `PENDING_CHANGE_CONTROL` |
| `DRF-004` | Sì | `CRITICAL` | freshness e dispatch valutati in punti diversi/incompleti | §4.1, §5.2, §5.4 | `DRF-001`, `003`, `008` | Sì | rivalidazione atomica `G-FRESHNESS ∧ G-DISPATCH` su emission/retry/compensation | drift, lease scaduta e GatePackage mismatch respinti | `PENDING_CHANGE_CONTROL` |
| `DRF-005` | Sì | `CRITICAL` | marking metamodel parziale e operatori non totalizzati | §3.0.2, §3.1.1, §3.2, §5.3 | authority fence | Sì | algebra chiusa per famiglia, unknown/incomparabili fail-closed, declassification governata | property/golden/adversarial tests | `PENDING_CHANGE_CONTROL` |
| `DRF-006` | Sì | `MINOR` | verifier confronta stati, non archi; tabella aggregata | §4.1, §4.1.2 | `DRF-004`, `007` | No | una riga per arco con source/destination; T22/T27 separati | uguaglianza tuple diagramma↔tabella | `CLOSED_IN_CANDIDATE` |
| `DRF-007` | Sì | `MAJOR` | terminalità senza adjudication/unblock; conflict key coarse | §3.7, §4.1 | `DRF-004` | Sì | `IndeterminateEffectAdjudication` append-only e `ConflictScope` tipizzata | unknown scope fail-closed; unblock solo con record valido | `PENDING_CHANGE_CONTROL` |
| `DRF-008` | Sì | `MAJOR` | binding canonical dichiarativo, evidence minima zero, errori C3 ambigui | §3.7, §4.1 | `DRF-003` | Sì | field binding Claim/Evidence/Decision/Authority/aggregate/revision; reason code deterministici | assenze e failure class respinte/mappate | `PENDING_CHANGE_CONTROL` |
| `DRF-009` | Sì | `MAJOR` | BA-01 cambia atomicità ma è classificata adapter-only | §2.3, §2.6, §6.2, §8 | authority fence | Sì | `ARCHITECTURAL_ALTERNATIVE_REQUIRING_CHANGE_CONTROL`, NO-GO senza failure analysis | scan classificazione e package CC | `PENDING_CHANGE_CONTROL` |
| `DRF-010` | Sì | `MINOR` | conteggi/locator manuali e coverage DEC semantica incompleta | §1.1, §7, §8 | `DRF-015` | No | 9 CC v1.1; 183 subsystem + 13 governance = 196 globale; locator esatti | conteggi generati e diff-log coverage | `CLOSED_IN_CANDIDATE` |
| `DRF-011` | Sì | `MAJOR` | DAG draft incompleto e direzione non definita | §8 e package CC | authority fence | Sì | arco `X depends_on Y`; baseline vs inferred separati; change-set atomici | topological/dependency check | `PENDING_CHANGE_CONTROL` |
| `DRF-012` | Sì | `BLOCKER` | `FR-095` P0/PoC vs `ELM-070` differita | §1.5, §4.2, §7.1; registri sorgente | authority fence | Sì obbligatorio | mantenere `ELM-070` differita; proporre `FR-095` P0/MVP fuori PoC; elenco esatto registri da aggiornare | scope consistency + package CC completo | `PENDING_CHANGE_CONTROL` |
| `DRF-013` | Sì | `MAJOR` | required OpenAPI non realizza “ogni risultato” di FR-007 | §3.3 | — | No | rendere obbligatori relazioni, uncertainty, identity candidates, explanation | omissioni respinte; valori espliciti vuoti/None accettati | `CLOSED_IN_CANDIDATE` |
| `DRF-014` | Sì | `MAJOR` | fuori profilo PoC confuso con stato Differito | §6.1, §7.1 | — | No | `NFR-078` confermato P0/MVP, fuori solo dal PoC | scope scan e register comparison | `CLOSED_IN_CANDIDATE` |
| `DRF-015` | Sì | `MAJOR` | decisioni sostantive classificate gate; gate veri solo coperti da range larghi | §4.3, §7 | — | Sì per riallocazione | `DEC-173/175` a subsystem; disposition tipizzata `RUNTIME`, `PROGRAMME_GOVERNANCE`, `DOCUMENT_CONTROL` derivata dal registro (inclusi 17 `GATE-IRB`); coverage globale 196/196 | semantic allocation check | `PENDING_CHANGE_CONTROL` |
| `V12-RF-001` | Sì | `MAJOR` | replay event ammesso senza finestra bounded | §3.8 | — | No | `replay_allowed=true` ⇒ `max_replay_window` obbligatoria; false ⇒ vietata | positivi e negativi simmetrici | `CLOSED_IN_CANDIDATE` |
| `V12-RF-002` | Sì | `MAJOR` | evidence/quorum possono essere strutturalmente vuoti in Action/MCP | §3.5, §3.7 | `DRF-003`, `008` | No | evidence `REQUIRED` ⇒ count≥1; approval umano ⇒ ruoli/quorum non vuoti | fixture empty respinte | `CLOSED_IN_CANDIDATE` |

## Riconciliazione `ARF-*` / `AM-*`

| Esito v1.1 | `ARF-*` | Disposizione v1.2 |
|---|---|---|
| `CLOSED` | `ARF-003`, `005`, `008`, `010`, `011`, `015`, `016`, `019`, `020`, `021`, `022`, `023`, `024`, `025`, `026`, `027` | `ALREADY_GOVERNED`; mantenere test di regressione |
| `PARTIALLY_CLOSED` | `ARF-001`, `006`, `014`, `018` | confluiti in `DRF-001/002`, `DRF-004`, `DRF-013`, `DRF-006` |
| `CLOSED_WITH_NEW_DEFECT` | `ARF-002`, `004`, `009`, `012`, `013`, `017` | confluiti in `DRF-003/008`, `DRF-005`, `DRF-003/008`, `DRF-005`, `DRF-015/010`, `DRF-014` |
| `OVER_CORRECTED` | `ARF-007` | confluito in `DRF-007` |

`AM-01`–`AM-28` sono tutti riconciliati uno-a-uno con `ARF-001`–`ARF-027` più `AM-28`/Backend Assumption Register. `AM-28` resta valido come introduzione del registro, ma `BA-01` e la classificazione change-control sono corretti tramite `DRF-009`. La stringa troncata `Review §8, P1-12` nel `DELTA_MANIFEST.json` è `SOURCE_LIMITATION` editoriale e non viene propagata.

## `RV-*`

| Difetto | Esito | Stato |
|---|---|---|
| `RV-01` | campo condizionale ora dichiarato e ramo simmetrico presente; non prova la safety semantica, coperta da `DRF-003/008` | `ALREADY_GOVERNED` |
| `RV-02` | §2.6 esiste e il rimando è corretto | `ALREADY_GOVERNED` |

## `DRAFT-*` dependency control

La direzione è definita come `X depends_on Y` (Y deve precedere X). Baseline esplicita: `DRAFT-B depends_on DRAFT-G`; `DRAFT-C depends_on DRAFT-B`; `DRAFT-D depends_on DRAFT-H`; `DRAFT-E` e `DRAFT-F` sono un change-set atomico. Inferenze candidate da sottoporre all'authority: `DRAFT-E depends_on DRAFT-I` per il CapabilityLease; `DRAFT-B/C/E/F depends_on DRAFT-A` per il GCS; gli emendamenti Action safety dipendono dal contratto `DRAFT-G`; `BA-01` dipende dalla disposizione single-writer/branch-scope di `DRAFT-C`. `CC-SINGLE-WRITER-BRANCH-SCOPE` fornisce ora il percorso decisionale esplicito per `DRAFT-C`. Nessuna relazione equivale ad approvazione.
