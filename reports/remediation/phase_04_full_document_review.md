# FASE 6 — Full Document Review della v1.2 Candidate

## Metodo

Passata end-to-end su tutte le sezioni, non limitata agli hunk modificati. Ogni rilievo è stato confrontato con baseline, registri e contratti. I soli nuovi difetti validi sono `V12-RF-001` e `V12-RF-002`, entrambi corretti e testati; nessun ulteriore finding ADD-level è rimasto dopo la seconda passata.

## §1 — Document Control & System Context

`PASS IN CANDIDATE`. Stato candidato, derivazione e digest sono espliciti. Authority ed evidence fence impediscono approvazioni implicite. Il GCS è un record unico; trust boundary e Principal binding sono fail-closed. Scope PoC/MVP/deferred è distinto. La contraddizione `FR-095`/`ELM-070` è tecnicamente risolta con una singola opzione candidata ma resta `PENDING_CHANGE_CONTROL`.

## §2 — Container Architecture

`PASS IN CANDIDATE`. Vista C4, ownership e port restano coerenti. Single writer, local state+outbox, relay e reconciler sono distinti; branch scenario non pubblica sul relay main. Backend isolation e assumption register non promuovono tecnologie. `BA-01` è ora `ARCHITECTURAL_ALTERNATIVE_REQUIRING_CHANGE_CONTROL` e `NO-GO`, non fallback adapter-only.

## §3 — Metamodels & Critical Interfaces

`PASS IN CANDIDATE`. Canonical IR/OaC conservano neutralità backend. GCS e marking hanno una forma canonica. Ingestion, OpenAPI, Protobuf, MCP, Action ed Event parsano e hanno versioni candidate. `ObjectSnapshot` realizza strutturalmente FR-007. Canonical admission e replay sono fail-closed. Non sono presenti dialect backend nei contratti pubblici.

## §4 — Runtime & Workflows

`PASS IN CANDIDATE`. Tutti gli archi FSM hanno ID, source e destination; diagramma e tabella coincidono su 44 tuple. Stati raggiungibili, ID contigui `ACT-T01–T31`, terminalità e self-loop di inquiry sono espliciti. ACK, execution e outcome restano separati. `EMISSION-FENCE` è rivalidata su invio/retry/compensation. Indeterminate effect non viene inferito né sbloccato per timeout.

## §5 — Zero Trust & Human Gate

`PASS IN CANDIDATE`. Identity, delegation, actor chain e effective Principal sono distinti. Authority è l'intersezione dei binding verificati. CapabilityLease è non trasferibile e pin-nata. High Impact/canonical commit richiedono Human Gate o Dual Control. Break-glass ed emergency stop non persistono oltre scadenza/stop epoch. Audit indisponibile blocca l'emissione.

## §6 — Deployment, Operations & Resilience

`PASS IN CANDIDATE`. Tecnologie restano `Candidate Implementation`; capability `Design Target`. Consistency, degraded mode, backup/replay/recovery gate non fanno claim di performance o production readiness. `NFR-078` è correttamente fuori PoC ma non differita. Le alternative che cambiano invarianti richiedono authority.

## §7 — Traceability

`PASS IN CANDIDATE`. Universo core 693: 196 DEC, 18 BR, 174 FR, 93 NFR, 23 ARC, 26 CAP, 103 ELM, 60 RSK. Coverage subsystem/programme: 183 DEC; 13 decisioni document/programme hanno disposition separata; globale 196/196. `CAP-026` è tracciata `OUT_OF_SCOPE`, non contata come capability allocata. `DEC-173/175` hanno allocazione candidata esplicita. Nessun requisito core è orfano secondo il verifier.

## §8 — Amendment Log

`PASS IN CANDIDATE`. Il log v1.1→v1.2 identifica causa, locator, natura, versioni e change control; lo storico v1.0→v1.1 è preservato. `CLOSED_IN_CANDIDATE` non significa baseline approved. Il package esterno contiene il testo decisionale esatto e il DAG.

## Adversarial review

| Attacco/errore | Esito |
|---|---|
| body/prompt-derived authority, confused deputy | Principal body non concede Authority; mismatch respinto |
| stale context, lease expiry, stop bypass | `INVALIDATED` prima dell'invio |
| duplicate effect / unsafe retry / lost ACK | idempotency, DeliveryAttempt, unknown/reconciliation separati |
| recovery ambiguity | recovery gate e authority-aware replay; nessun successo inferito |
| cross-compartment/branch contamination | GCS digest + relay main-only |
| causal overclaim / effect estimate in ABSTAIN | reason code e output constraints conservati |
| capability escalation / break-glass persistente | lease/policy/expiry/SoD e stop epoch |
| backend lock-in / fallback architetturale | public contracts neutral; `BA-01` richiede CC |
| scope leakage | `FR-095` authority-blocked; `NFR-078` corretta; deferred invariati |
| unsupported evidence claim | `E1=0`, `E2=0`, zero `Verified`; scan verde |

## Esito

Zero difetti interni `BLOCKER/CRITICAL` correggibili restano. Le decisioni normative non approvate sono isolate come `PENDING_CHANGE_CONTROL` e non rendono ambigua la soluzione candidata. La fase successiva deve validare patch, Amendment Log, digest e immutabilità delle sorgenti.
