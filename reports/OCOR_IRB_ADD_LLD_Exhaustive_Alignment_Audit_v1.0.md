# OCOR — Audit esaustivo di allineamento IRB → ADD v1.2 → LLD v1.0 — SUPERSEDED

> **SUPERSEDED HISTORICAL AUDIT.** Questo referto descrive ADD v1.2 e LLD v1.0 prima di `DEC-208`. Non è il risultato corrente. L'autorità corrente è `reports/OCOR_IRB_ADD_LLD_Authoritative_Audit_v1.1.md` con risultato machine-readable `reports/tests/irb_add_lld_authoritative_audit_results.json`.

## 1. Verdetto esecutivo

**Esito complessivo: `NO-GO` per l'approvazione formale dell'LLD v1.0.**

L'ADD v1.2 conserva una copertura formale completa dei 285 requisiti IRB mediante 158 riferimenti diretti e 127 allocazioni per range. L'LLD v1.0, invece, non contiene alcuna allocazione individuale o per range dei 285 requisiti e riduce la tracciabilità a 11 macro-voci tematiche.

Il problema non è soltanto documentale. Sono state confermate divergenze semantiche bloccanti fra ADD e LLD, fra cui:

- `GovernedContext` con field set incompatibile;
- `CapabilityLease` non riprodotto come record chiuso approvato;
- FSM limitata alle 44 tuple source/destination, senza evento/guardia ed effetto durevole per transizione;
- contratti OpenAPI/Proto dichiarati autoritativi dall'LLD ma assenti dalla repository;
- unità atomica C3 priva dell'esplicito idempotency binding imposto da `DEC-201`;
- requisiti `FR-118` e `FR-119` P0/PoC in tensione con il differimento ADD di `ELM-084`.

Il precedente gate 46/46 resta valido esclusivamente come controllo strutturale di presenza. Non dimostra l'allineamento semantico e non può sostenere l'approvazione dell'LLD.

## 2. Baseline esaminata

Audit eseguito sul branch `main`, commit `92de7d20496eed52ad770de01f7148b6217cf80c`.

| Artefatto | Identità verificata |
|---|---|
| ADD v1.2 Approved Baseline | SHA-256 `c3f432ae0d172f2b4f70be8220d0ae4a134ec14716bccc6a12d75dfee438b84f` |
| ARA Decision Record v1.1 | SHA-256 `35579536a67122700ff09f6be33874163f5872a199f853b557d28c71af9a0eae` |
| Requirement Register v1.0 Approved | SHA-256 `eb3c3bca4c0e88a2a7c70a6c5a7c45ab1cf51fd72329a2b6c2d877939c43b7d2` |
| Requirement Traceability Index v1.0 Approved | SHA-256 `44b54a577a6d6c3342af85fced1ee98662b79f783a8b22ab5c655feca113c0f7` |
| CAP/ELM Crosswalk v1.0 Approved | SHA-256 `89a365262909e734c19512e799d78632b72ab6452ad0f5e7c11661f5819f101e` |
| LLD v1.0 esaminato | SHA-256 `9400d05c4eadc7f36df940d565f35ffe7bdf7d0400b3bf938444d6b9f793025d` |

Il file aggregato `OCOR_Initial_Requirements_Baseline_v1.0.md`, richiamato dalla governance storica, non è presente nel tree corrente. L'audit IRB è stato quindi eseguito sugli snapshot approvati e manifestati di Requirement Register, Requirement Traceability Index, Decision Register, Decision Traceability Index e CAP/ELM Crosswalk. Questa base consente di verificare i 285 requisiti, ma l'assenza dell'artefatto aggregato resta un finding di configuration management.

## 3. Metodo

L'audit ha applicato cinque livelli di verifica:

1. integrità e identità degli artefatti approvati;
2. enumerazione requisito-per-requisito di 18 `BR`, 174 `FR` e 93 `NFR`;
3. espansione dei range normativi ADD, oltre ai riferimenti letterali;
4. confronto semantico di tipi, field set, cardinalità, invarianti, FSM, port, store, failure mode e acceptance behaviour;
5. verifica dell'esistenza delle dipendenze documentali e dei contratti dichiarati autoritativi.

La matrice completa è prodotta da `reports/tests/audit_irb_add_lld.py` e registra per ogni requisito priorità, release, allocazione nell'indice approvato, allocazione ADD e allocazione LLD.

## 4. Risultati quantitativi

| Controllo | Risultato |
|---|---:|
| Requisiti IRB enumerati | 285/285 |
| `BR` | 18 |
| `FR` | 174 |
| `NFR` | 93 |
| Allocazione nell'ADD | 285/285 |
| Riferimenti ADD diretti | 158 |
| Allocazioni ADD per range | 127 |
| Allocazione nell'LLD | **0/285** |
| Righe di tracciabilità tematica nell'LLD | 11 |
| Field comuni esatti in `GovernedContext` | 3/11 richiesti |
| Tuple FSM source/destination | 44/44 |
| Transizioni LLD con evento/guardia ed effetto durevole ADD | **0/44** |
| Contratti esterni dichiarati autoritativi e presenti | **0/2** |

L'allocazione ADD 285/285 dimostra copertura nominale, non automaticamente sufficienza del dettaglio. L'assenza totale di identificativi IRB nell'LLD impedisce invece la tracciabilità bidirezionale dichiarata in LLD §10.

## 5. Finding bloccanti

### `IALLD-001` — Tracciabilità IRB→LLD assente — `BLOCKER`

L'LLD non cita né alloca alcuno dei 285 requisiti. La tabella §10 contiene 11 temi architetturali, non una matrice requisito-per-requisito. Non è quindi possibile dimostrare:

- che ogni requisito sia `FULLY_SPECIFIED`, `NOT_APPLICABLE` o `GAP`;
- che priorità e release siano preservate;
- che i requisiti processuali e operativi non siano stati omessi;
- reverse traceability da classe, porta, schema, tabella o test al requisito sorgente.

**Rettifica richiesta:** matrice normativa 285/285, con anchor ADD, anchor LLD, design disposition, verifica, release e stato.

### `IALLD-002` — `GovernedContext` incompatibile — `BLOCKER`

L'ADD approva un record chiuso con 11 campi:

```text
tenant_id
organization_id
domain_id
compartments[]
classification_marking_ref
purpose
effective_principal_id
actor_chain
ontology_release_digest
policy_bundle_digest
correlation_id
```

L'LLD definisce invece 14 campi:

```text
principal_id
tenant_id
purpose_ids
authority_refs
policy_snapshot_digest
marking_ref
capability_lease_ids
correlation_id
causation_id
request_time
deadline
schema_pins
ontology_release_digest
trace_id
```

Coincidono soltanto `tenant_id`, `ontology_release_digest` e `correlation_id`. Mancano otto campi obbligatori ADD e sono introdotti alias/estensioni non autorizzati. Ciò viola il record chiuso, l'uguaglianza byte-canonica e il divieto di coercizioni/alias non dichiarati.

**Rettifica richiesta:** usare esattamente il record ADD; eventuali dati addizionali devono appartenere a un envelope distinto, non al `GovernedContext` canonico.

### `IALLD-003` — Contratti autoritativi inesistenti — `BLOCKER`

LLD §1.2 dichiara autoritativi:

- `schemas/openapi/ocor-named-query-gateway.openapi.yaml`;
- `schemas/proto/ocor_registry.proto`.

Entrambi i path sono assenti dal tree. I file `ocor-runtime/schemas/ocor.openapi.yaml` e `ocor-runtime/schemas/ocor_runtime.proto` sono espressamente qualificati dall'LLD come compatibility surface e non possono sostituirli.

**Rettifica richiesta:** materializzare i contratti approvati, fissarne digest e code generation, oppure incorporare nell'LLD una definizione completa e non ambigua. I semplici nomi di path/service non bastano.

### `IALLD-004` — `CapabilityLease` non conforme — `BLOCKER`

L'ADD definisce un record chiuso legato a `action_instance_id`, `governed_context_digest`, `gate_package_digest`, `stop_epoch`, `fencing_token`, `issued_at` ed `expires_at`.

L'LLD non riproduce il record. La sua regola di validazione usa invece `subject`, `allowed_operations`, `resource`, `usage_count`, `usage_limit`, `parent chain` e `policy_snapshot_digest`, campi propri di un diverso modello di capability token.

**Rettifica richiesta:** definizione identica del record ADD, algoritmo monouso per `(action_instance_id, emission_attempt)`, firma, revoca, consumo atomico e reason code esatti.

### `IALLD-005` — FSM non implementabile dalla sola tabella LLD — `BLOCKER`

Le 44 tuple source/destination coincidono, ma la tabella LLD elimina due colonne normative dell'ADD:

- evento/guardia;
- effetto durevole.

Questo perde, fra l'altro, la semantica distinta di idempotency replay/conflict, gate non richiesto, quorum, expiry, policy failure, lost acknowledgement, reconciliation, compensation e canonical commit.

**Rettifica richiesta:** riprodurre per tutte le 44 transizioni ID, source, evento/guardia, effetto durevole e destination, includendo precedence e terminalità.

### `IALLD-006` — Percorso canonico C3 insufficientemente vincolato — `BLOCKER`

L'ADD impone che `C3` accetti mutazioni solo dal percorso governato `C6`, con `Decision`, `Authority`, Evidence, claim/source binding, aggregate type/ref, expected revision, precondition/invariant bindings, idempotency key, GCS digest e `GatePackage` immutabile.

Le firme LLD `commit(delta, expected_revision, entries, context)` e `commit_aggregate` non rendono obbligatori tali argomenti e non specificano il rifiuto prima della mutazione. La DDL di riferimento non contiene un idempotency binding distinto e durevole; l'idempotency key compare soltanto sull'outbox.

**Rettifica richiesta:** comando chiuso `GovernedCanonicalCommitCommand`, vincoli DB/adapter, verifica pre-transaction e commit atomico di state, revision, canonical commit, idempotency binding e outbox.

### `IALLD-007` — Contraddizione IRB/ADD su `FR-118`, `FR-119` ed `ELM-084` — `BLOCKER`

Gli snapshot approvati mantengono:

- `FR-118` — Schema della Memory — P0/PoC;
- `FR-119` — Isolamento del retrieval — P0/PoC;
- entrambi mappati a `ELM-084`.

L'ADD differisce `ELM-084` e dichiara «Nessuna memoria persistente generale», sostituendola con contesti effimeri ricostruibili da Evidence ref. Nessuna decisione `DEC-197`–`DEC-206` modifica `FR-118` o `FR-119`.

**Rettifica richiesta:** change control esplicito. Le alternative ammissibili sono implementare nel PoC un Memory Item bounded conforme a `FR-118/119`, oppure riclassificare formalmente i due requisiti fuori dal PoC e aggiornare atomicamente tutti i registri. L'LLD non può risolvere da solo una contraddizione IRB/ADD.

## 6. Finding maggiori di completezza LLD

### `IALLD-008` — Canonical IR e C1 sottospecificati — `MAJOR`

L'LLD elenca classi generiche ma non definisce il meta-modello, le 103 famiglie `ELM`, cardinalità, owner di esecuzione, capability dispositions, semantic diff/migration, AsyncAPI/MCP, SDK Python/TypeScript, mapping e artifact generator richiesti dall'ADD.

### `IALLD-009` — Consistency e query path C2 incompleti — `MAJOR`

Mancano algoritmi completi per `BEST_AVAILABLE`, `AT_LEAST_COMMIT` ed `EXACT_AT_COMMIT`, attesa bounded, watermark selection, branch disclosure, staleness, `PROJECTION_NOT_READY`, `STALE_CONTEXT`, isolamento della cache sulla tupla ADD completa e comportamento sulle proiezioni logiche indisponibili.

### `IALLD-010` — Event Backbone C5 incompleto — `MAJOR`

Non sono definiti il Canonical Ingestion Envelope completo, la tassonomia `transient/permanent/policy-denied/poison`, i contatori e limiti di retry, i record DLQ/quarantine, il checkpoint/replay window, la compatibilità dei contratti e gli invarianti di backpressure richiesti dall'ADD.

### `IALLD-011` — Modello C6 incompleto — `MAJOR`

I tipi LLD non preservano esplicitamente tutti i record distinti ADD: `PolicyAuthorityDecision`, `DeliveryAttempt`, `ExecutionResult`, `OutcomeAssessment`, `ConflictScope` e `IndeterminateEffectAdjudication`. Il generico `ExecutionEvidence` non è equivalente.

### `IALLD-012` — Causal Runtime C7 incompleto — `MAJOR`

Le interfacce non specificano estimand, identificabilità, assumptions, validity envelope, OOD, uncertainty, sensitivity, reason code disgiunti, `identify-or-abstain`, lineage e contamination fence su `main`. Non è sufficiente esporre `query` e `intervene`.

### `IALLD-013` — Agent Kernel C8 incompleto — `MAJOR`

Mancano i data contract completi di Task, Assignment, Commitment, Handoff, Dissent, Decision Proposal e Memory Item; non sono specificati retrieval isolation, instruction eligibility, preservation del dissent, cycle/delegation algorithm e durable run semantics richiesti dai requisiti IRB e dall'ADD.

### `IALLD-014` — Human Gate, break-glass ed emergency stop non progettati — `MAJOR`

L'LLD cita approval, lease e kill switch ma non decompone:

- classi `R0_READ`–`R3_HIGH_IMPACT`;
- quorum e SoD per operazione;
- contenuto minimo del `GatePackage`;
- scadenza dell'Approval Set;
- break-glass con TTL, dual control e divieti;
- FSM `NORMAL/STOPPING/STOPPED/RESET_PENDING`;
- incremento e reset governato di `stop_epoch`.

### `IALLD-015` — Deployment, resilienza e recovery incompleti — `MAJOR`

La sezione di concorrenza non sostituisce il design ADD per topologia single-site isolata, zero egress, network policy, workload identity, resource classes, safe-degraded operation, backup authority-aware, restore, deterministic replay, recovery gate, audit availability e osservabilità semantica.

### `IALLD-016` — DDL di riferimento non applica branch isolation/FSM — `MAJOR`

`ocor_outbox` non contiene un branch discriminator che consenta di dimostrare il relay esclusivo di `main` richiesto da `DEC-200`. `ocor_action_transition` non ha FK/check verso il registry delle 44 tuple e consente formalmente transition/state arbitrarie.

### `IALLD-017` — Configuration baseline insufficiente — `MAJOR`

Una singola `OCOR_DATABASE_DSN` non specifica TerminusDB, TypeDB, Jena, Temporal/PostgreSQL, Kafka/registry, S3, policy, identity, trust bundle, audit, backup e release pins. Mancano secret reference model, timeouts, retry budgets, storage isolation e fail-closed startup per ogni CI.

### `IALLD-018` — Artefatto IRB aggregato assente — `MAJOR`

Il tree corrente non contiene il file IRB aggregato richiamato dal controllo di baseline. Gli snapshot approvati consentono l'audit dei requisiti, ma la riproducibilità della baseline IRB come singolo artefatto content-addressed non è completa.

## 7. Valutazione del gate 46/46

Il checker `test_lld_add_alignment.py` verifica prevalentemente presenza di token:

- nomi C1–C8 e package;
- 44 tuple FSM;
- stringhe BA/RBA;
- sei path OpenAPI, package/service Proto e cinque schema ID;
- parole chiave come `GovernedContext`, `EMISSION-FENCE`, `TerminusDB`.

Non verifica:

- uguaglianza dei field set;
- cardinalità e closed-world constraints;
- esistenza dei file dichiarati autoritativi;
- 285 requisiti e 206 decisioni;
- evento/guardia/effetto delle transizioni;
- completezza di algoritmi, persistence schema, failure mode e test oracle;
- contraddizioni di scope IRB/ADD.

Di conseguenza, `46/46 PASS` e `Document alignment: PASS` sono risultati troppo forti rispetto a ciò che il checker misura. Devono essere superseduti da questo audit.

## 8. Disposizione raccomandata

| Oggetto | Stato dopo l'audit |
|---|---|
| IRB v1.0 | approvata; configuration package da completare con l'artefatto aggregato |
| ADD v1.2 | formalmente approvata, ma con `IALLD-007` che richiede change control correttivo |
| LLD v1.0 | **NOT APPROVABLE / NO-GO** |
| Precedente alignment review | **SUPERSEDED FOR SEMANTIC ASSURANCE** |
| Runtime conformance | resta `NO-GO`; non valutata come oggetto principale di questo audit |

L'approvazione ADD non viene revocata implicitamente da una review. Il finding IRB/ADD deve essere risolto dall'authority mediante un nuovo decision record e baseline versionata.

## 9. Piano di remediation obbligatorio

1. Aprire change control per `FR-118`/`FR-119`/`ELM-084` e ripristinare coerenza IRB↔ADD.
2. Produrre LLD v1.1 o una candidate v1.0.1 con i contratti esatti `GovernedContext` e `CapabilityLease`.
3. Materializzare OpenAPI/Proto autoritativi e fissarne i digest.
4. Aggiungere la matrice 285/285 e la tracciabilità delle decisioni applicabili.
5. Riprodurre la FSM completa a cinque colonne con algoritmi e persistence effects.
6. Rendere il comando C3 closed, C6-only e atomicamente idempotente.
7. Completare C1, C2, C4, C5, C6, C7, C8, sicurezza e operations fino al livello implementabile.
8. Sostituire il token checker con controlli semantici su field set, enum, cardinalità, path esistenti, schema digest, transition guards/effects e requirement allocation.
9. Rieseguire l'audit con criterio: zero `BLOCKER`, zero `MAJOR` non autorizzati e 285/285 `FULLY_SPECIFIED` o `NOT_APPLICABLE` motivati.
10. Solo dopo emettere il decision record di approvazione LLD.

## 10. Conclusione

L'LLD v1.0 è una buona skeleton architetturale e corregge alcuni difetti visibili della versione precedente, ma non è ancora un Low-Level Design completo e normativamente equivalente all'ADD v1.2. La dichiarazione corretta è:

> LLD v1.0 structural skeleton aligned on selected anchors; exhaustive IRB→ADD→LLD semantic alignment failed.

Pertanto l'LLD non deve essere dichiarato approvato nello stato corrente.
