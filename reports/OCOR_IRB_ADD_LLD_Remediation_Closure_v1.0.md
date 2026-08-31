# OCOR — Chiusura tecnica della remediation IRB → ADD → LLD

## 1. Verdetto

**Esito: `TECHNICALLY READY FOR GOVERNED APPROVAL`.**

La candidata LLD v1.1 rimuove le divergenze tecniche individuate dall'audit esaustivo e dispone individualmente tutti i 285 requisiti IRB. Il gate riproducibile termina con:

- 285/285 requisiti enumerati e allocati;
- 283 `FULLY_SPECIFIED`;
- 2 `CONDITIONALLY_SPECIFIED` (`FR-118`, `FR-119`);
- 0 `GAP`;
- 37/37 controlli semantici e di integrità superati;
- FSM 44/44 byte-semanticamente identica alla tabella ADD;
- OpenAPI e Proto materializzati byte-per-byte dai blocchi incorporati nell'ADD v1.2.

L'unica condizione residua non è tecnica ma normativa: `CC-BOUNDED-GOVERNED-MEMORY` deve essere ratificato prima di consolidare ADD v1.3 e approvare LLD v1.1. Fino a quella decisione l'ADD v1.2 e l'LLD v1.0 restano gli artefatti pubblicati vigenti.

## 2. Baseline e artefatti prodotti

| Artefatto | Ruolo | Stato |
|---|---|---|
| ADD v1.2 Approved Baseline | autorità architetturale corrente | immutata |
| `OCOR_Change_Control_Bounded_Governed_Memory_v1.0.md` | risoluzione proposta di `FR-118/119` ↔ `ELM-084` | awaiting governed decision |
| `OCOR_ADD_v1.3_Candidate.md` | emendamento candidato, non baseline | awaiting governed decision |
| `OCOR_LLD_v1.1_Candidate.md` | specifica esecutiva rettificata | ready for governed review |
| matrice IRB→ADD→LLD Markdown/JSON | tracciabilità 285/285 | generated and checked |
| contratti OpenAPI/Proto/JSON Schema | authority materializzata sotto `reports/contracts/` | checked; candidate package |
| `lld_v1_1_assurance_results.json` | risultato machine-readable | `PASS_WITH_GOVERNANCE_CONDITION` |

Nessun file sotto `inputs/` è stato modificato. Non è stato creato alcun nuovo ID `DEC-*`, né attribuita un'autorità non presente nella baseline.

## 3. Disposizione dei finding

| Finding | Rettifica | Disposizione |
|---|---|---|
| `IALLD-001` | matrice nominativa 285/285 con priorità, release, ADD allocation, anchor LLD, metodo e disposition | `CLOSED_TECHNICALLY` |
| `IALLD-002` | `GovernedContext` chiuso con gli 11 campi ADD, alias vietati | `CLOSED` |
| `IALLD-003` | OpenAPI e Proto estratti dai blocchi normativi ADD e materializzati | `CLOSED` |
| `IALLD-004` | `CapabilityLease` chiusa, temporal guard, fencing e consumo atomico | `CLOSED` |
| `IALLD-005` | 44 righe con ID, source, evento/guardia, effetto durevole e destination | `CLOSED` |
| `IALLD-006` | `GovernedCanonicalCommitCommand`; state+revision+commit+idempotency+outbox atomici; `main` only | `CLOSED` |
| `IALLD-007` | change set bounded memory e ADD v1.3 candidate | `CLOSED_TECHNICALLY / OPEN_GOVERNANCE` |
| `IALLD-008` | C1: IR, cardinalità, generatori, migration, SDK e conformance | `CLOSED` |
| `IALLD-009` | C2/C4: tre consistency mode, watermark, cache isolation, drift e fail-closed | `CLOSED` |
| `IALLD-010` | C5: envelope, failure taxonomy, retry, DLQ/quarantine, checkpoint, replay e backpressure | `CLOSED` |
| `IALLD-011` | C6: record distinti per control, execution, outcome e adjudication | `CLOSED` |
| `IALLD-012` | C7: estimand, identification, OOD, uncertainty, sensitivity e abstention | `CLOSED` |
| `IALLD-013` | C8: run/task/assignment/commitment/handoff/dissent/memory | `CLOSED` |
| `IALLD-014` | R0–R3, GatePackage, SoD, break-glass ed emergency-stop FSM | `CLOSED` |
| `IALLD-015` | topology, CI configuration, degraded mode, backup, restore e recovery gate | `CLOSED` |
| `IALLD-016` | branch discriminator `main`, registry FSM e vincoli di outbox/idempotency | `CLOSED` |
| `IALLD-017` | configuration contract per CI con pin, trust, timeout, retry, storage e startup fail-closed | `CLOSED` |

## 4. Verifica dei contratti

### 4.1 OpenAPI

Il file standalone è byte-identico al blocco `yaml` della sezione ADD v1.2 §3.3. Contiene OpenAPI 3.1.0, versione 1.2.0 e sei named-query path. Il parse YAML locale è positivo. Poiché l'identità con il soggetto approvato è verificata, si applica senza trasformazioni l'evidenza governata già registrata da `VAL-ACT-002`: `openapi-spec-validator==0.9.0`, 3/3 subject pass, nessuna waiver.

### 4.2 Protobuf

Il file standalone è byte-identico al blocco `proto` della sezione ADD v1.2 §3.4. Package e servizi sono `ocor.registry.v1`, `FunctionRegistry` e `ModelRegistry`. L'evidenza post-approval già registrata riporta compilazione `protoc` senza errori sul medesimo blocco; l'identità sorgente evita di promuovere una variante non compilata.

### 4.3 JSON Schema

I tre schemi JSON sono sintatticamente validi, chiusi con `additionalProperties:false` e usano Draft 2020-12. Il gate verifica l'esatto field set di `GovernedContext` e `CapabilityLease`, oltre alle constraint bounded di `GovernedMemoryItem`.

## 5. Interpretazione della matrice

`FULLY_SPECIFIED` significa che la candidata LLD assegna una realizzazione esecutiva e un metodo di verifica al requisito; non significa che il codice l'abbia implementata o che l'evidence sia presente. `CONDITIONALLY_SPECIFIED` significa che la realizzazione è completa nella candidata ma dipende da una modifica normativa non ancora ratificata.

La matrice è costruita deterministicamente dal Requirement Register e dal Requirement Traceability Index approvati. Il gate controlla universo, unicità, priorità, release, allocazione ADD, anchor LLD e assenza di gap. L'approvazione finale deve comunque includere una review indipendente delle disposizioni semantiche, come richiesto dalla candidata stessa; il gate meccanico non sostituisce l'autorità di review.

## 6. Sequenza di promozione richiesta

1. Ratificare o respingere `CC-BOUNDED-GOVERNED-MEMORY`.
2. Se ratificato, aggiornare atomicamente Requirement Register, RTI, Decision Register, Decision Traceability Index e CAP/ELM Crosswalk.
3. Consolidare l'ADD v1.3 approvato eliminando lo status candidate e generando il nuovo digest.
4. Rieseguire il gate sul digest consolidato e svolgere review indipendente della matrice 285/285.
5. Consolidare l'LLD v1.1, generare manifest e decision record dell'autorità competente.

Se il change set viene respinto, `FR-118` e `FR-119` devono essere formalmente differiti e la candidata LLD deve rimuovere il profilo bounded anziché lasciare una contraddizione.

## 7. Fence dell'evidenza

La remediation riguarda coerenza e completezza documentale. Non modifica il runtime, non chiude gli implementation gap e non produce `E2`. Restano separati:

- approvazione ADD/LLD;
- conformità del runtime a C1–C8 e ai contratti;
- BA-01–BA-08 sui CI selezionati;
- production readiness.

Pertanto il corretto stato è: **candidata LLD tecnicamente approvabile dopo la decisione governata sulla memoria; runtime e Production non promossi.**
