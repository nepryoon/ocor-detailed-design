# OCOR Runtime — Low-Level Design v1.1 — APPROVED

## 0. Controllo del documento

| Campo | Valore |
|---|---|
| Identificativo | `OCOR-LLD-1.1-APPROVED` |
| Stato | `APPROVED TECHNICAL BASELINE — DEC-208` |
| Baseline architetturale | `OCOR-ADD-1.3-APPROVED`, SHA-256 `dca9e218914a310ac53f92cded61ae29a40323b98daacb51028077d6c15cd2fb` |
| Decisione architetturale | `DEC-208`, change set `CC-FULL-GOVERNED-AGENT-MEMORY` |
| Sostituisce | LLD v1.0 come specifica tecnica effettiva dal 2026-09-01 |
| Evidence claim | Specifica esecutiva; non dichiara implementazione né production readiness |

### 0.1 Precedenza e confine normativo

L'IRB approvato prevale sull'ADD; l'ADD v1.3 approvato prevale sull'LLD. `DEC-208` ratifica il change set sulla memoria governata. Le disposizioni relative a `GovernedMemoryItem` sono quindi norme di design approvate, ma non costituiscono evidenza di implementazione: il runtime full-memory resta `NO-GO` fino alla chiusura governata di `FGM-01`–`FGM-20`.

Ogni conflitto fra questo documento e l'ADD produce `LLD_CONFORMANCE_FAILURE`; non sono ammesse correzioni implicite tramite codice, configurazione, alias di campo o fallback tecnologico. Le parole DEVE, NON DEVE, DOVREBBE e PUÒ hanno valore normativo nella baseline tecnica approvata.

### 0.2 Artefatti contrattuali materializzati

| Contratto | Path approvato | Regola |
|---|---|---|
| Governed Context | `ocor-runtime/docs/governance_dossier/contracts/governed-context.schema.json` | record chiuso ADD v1.2, 11 campi |
| Capability Lease | `ocor-runtime/docs/governance_dossier/contracts/capability-lease.schema.json` | record chiuso, monouso per emission attempt |
| Full Governed Agent Memory | `ocor-runtime/docs/governance_dossier/contracts/governed-memory-item.schema.json` | full PoC design profile approvato da `DEC-208`; runtime activation subordinata a `FGM-01`–`FGM-20` |
| Governed Memory API | `ocor-runtime/docs/governance_dossier/contracts/ocor-governed-memory.openapi.yaml` | API 1.0.0 per admission, search, consolidation, lifecycle, promotion, deletion e context assembly |
| Named Query Gateway | `ocor-runtime/docs/governance_dossier/contracts/ocor-named-query-gateway.openapi.yaml` | OpenAPI 3.1, sei query nominate |
| Registry | `ocor-runtime/docs/governance_dossier/contracts/ocor_registry.proto` | Proto3 package `ocor.registry.v1` |

I digest di questi file sono fissati nel manifest di approvazione governato. Generazione di codice e fixture partono esclusivamente dai file manifestati.

## 1. Tipi trasversali e invarianti

### 1.1 Canonicalizzazione, digest e tempo

- Ogni oggetto firmato o confrontato usa JSON RFC 8785 e SHA-256, rappresentato come `urn:sha256:<64 lowercase hex>`.
- Timestamp sul wire: RFC 3339 UTC; persistenza: `TIMESTAMPTZ`; confronto temporale su clock monotono più timestamp UTC osservabile.
- Gli array semanticamente insiemistici sono ordinati lessicograficamente prima del digest e rifiutano duplicati.
- Un digest ricevuto viene ricalcolato prima di policy, authority, mutation, dispatch, replay o retrieval. Mismatch: fail-closed.
- `effective_principal_id` e `actor_chain` sono derivati dall'identità autenticata e dalla delegation chain, mai accettati come autorità da input client.

### 1.2 GovernedContext canonico

Il record è chiuso e contiene esattamente:

```text
tenant_id
organization_id
domain_id
compartments[]
classification_marking_ref
purpose
effective_principal_id
actor_chain[]
ontology_release_digest
policy_bundle_digest
correlation_id
```

`GovernedContextCodec.decode()` rifiuta proprietà ulteriori, alias e coercizioni. `canonicalBytes()` ordina gli array insiemistici e serializza RFC 8785. `digest()` produce l'URN SHA-256. Ogni boundary verifica schema, digest, identity binding, release pin e policy bundle; cache e indici sono partizionati almeno sull'intera tupla.

Campi di trasporto come causation ID, trace ID, deadline, schema pin o lease appartengono a un envelope separato e non cambiano il record canonico.

### 1.3 Marking algebra

`Marking = (classification_level, compartments, releasability, handling_caveats, policy_ref)`. `join(a,b)` restituisce il least upper bound conservativo; unione di compartimenti e caveat non può ridurre la restrizione. Marking mancante, incomparabile o non risolvibile produce `MARKING_UNRESOLVED`. Derivazioni, query, eventi, export, explanation, memory e provenance ereditano almeno il join degli input.

### 1.4 CapabilityLease

Il record chiuso contiene `lease_id`, `capability_id`, `effective_principal_id`, `delegation_ref`, `action_instance_id`, `governed_context_digest`, `gate_package_digest`, `stop_epoch`, `fencing_token`, `issued_at`, `expires_at`.

`LeaseValidator.consume(lease, emission_attempt)` esegue nella stessa transazione locale del `DeliveryAttempt`:

1. verifica firma, schema, time window e revoca;
2. confronta principal, delegation, action, GCS, GatePackage e stop epoch;
3. acquisisce lock sul fencing counter dell'action instance;
4. verifica che `(lease_id, action_instance_id, emission_attempt)` non sia consumato;
5. inserisce il consumo e il DeliveryAttempt oppure effettua rollback completo.

Reason code: `LEASE_INVALID`, `LEASE_EXPIRED`, `LEASE_REVOKED`, `LEASE_CONTEXT_MISMATCH`, `STOP_EPOCH_MISMATCH`, `FENCING_TOKEN_STALE`, `LEASE_ALREADY_CONSUMED`. Non esiste fallback permissivo.

### 1.5 Atomicità C3, single writer e idempotenza

L'unico comando mutativo è:

```text
GovernedCanonicalCommitCommand {
  command_id, action_instance_id, aggregate_type, aggregate_ref,
  expected_revision, canonical_delta, decision_ref, authority_ref,
  evidence_refs[], claim_source_bindings[], precondition_bindings[],
  invariant_bindings[], idempotency_key, governed_context,
  governed_context_digest, gate_package_digest, branch
}
```

Prima della transazione C3 valida record chiuso, digest, `branch=main`, provenienza C6, Decision, Authority, Evidence, revision e binding. Nella stessa transazione scrive canonical state, nuova revision, canonical commit, idempotency binding e outbox. Una constraint unica su `(tenant_id, aggregate_type, aggregate_ref, idempotency_key)` restituisce la receipt originale se command digest coincide e `IDEMPOTENCY_CONFLICT` altrimenti. Nessuna outbox di scenario viene relayata; C7 è l'unico writer dei branch scenario.

## 2. Decomposizione C1–C8

### 2.1 C1 — Ontology Compiler & IR Pipeline

Package: `ocor.c1.oac`, `ocor.c1.ir`, `ocor.c1.codegen`, `ocor.c1.migration`, `ocor.c1.conformance`.

Classi/porte: `OacParser`, `SemanticValidator`, `CanonicalIrBuilder`, `IrSigner`, `ReleasePublisher`, `SemanticDiffEngine`, `MigrationPlanner`, `ArtifactGenerator`, `CompatibilityChecker`, `ConformanceSuitePort`.

Pipeline deterministica: parse → schema validation → semantic validation → resolve authority/naming/cardinality → build Canonical IR → RFC8785 digest → signature → immutable release. La IR include type, property, relation, event, command, policy hook, authority, owner di esecuzione, capability disposition, schema/version pin e lifecycle. Semantic diff classifica additive/compatible/breaking; breaking change richiede migration plan, dual control e nuovo major. I generatori producono JSON Schema, OpenAPI, AsyncAPI, Proto, MCP descriptor e SDK Python/TypeScript dalla stessa IR; drift fra generated artifact e IR blocca la release.

### 2.2 C2 — Unified Semantic Gateway

Package: `ocor.c2.gateway`, `ocor.c2.query`, `ocor.c2.policy`, `ocor.c2.cache`, `ocor.c2.explain`.

Porte: `NamedQueryPort`, `ProjectionReadPort`, `PolicyDecisionPort`, `AuthorityResolutionPort`, `EvidenceReadPort`, `WatermarkPort`.

Algoritmo query:

1. autentica principal e costruisce il GCS canonico;
2. verifica allow-list di nome/versione/parametri e stima cost budget;
3. valuta policy/authority prima della query;
4. seleziona projection e consistenza;
5. esegue con row/edge/field filtering;
6. applica marking join e post-filter policy;
7. costruisce provenance/explanation policy-safe;
8. restituisce served branch, release, commit/watermark, staleness e GCS digest.

`BEST_AVAILABLE` usa l'ultimo watermark compatibile e dichiara staleness. `AT_LEAST_COMMIT(c,t)` attende bounded finché watermark ≥ c, poi `PROJECTION_NOT_READY`. `EXACT_AT_COMMIT(c)` usa snapshot/version pin esatto o rifiuta; non degrada. `main` e scenario sono sempre dichiarati. Cache key: digest dell'intero GCS + query/version + param digest + consistency + served branch/release/watermark; deny e miss non rivelano count, rank, cache hit o timing fine.

### 2.3 C3 — Canonical State Service & Outbox Worker

Package: `ocor.c3.command`, `ocor.c3.store`, `ocor.c3.outbox`, `ocor.c3.idempotency`, `ocor.c3.recovery`.

Porte: `GovernedCommitPort`, `CanonicalReadPort`, `OutboxRelayPort`, `RevisionPort`, `RecoveryPort`. Implementa l'invariante §1.5. Lock order: aggregate → idempotency binding → commit → outbox. Optimistic concurrency usa `expected_revision`; zero aggiornamenti produce `REVISION_CONFLICT`. Relay acquisisce righe `main` con `SKIP LOCKED`, pubblica con event ID stabile e marca delivered soltanto dopo ACK. Crash fra publish e mark produce replay con stesso ID; consumer deduplica.

Schema logico minimo:

| Tabella | Chiavi/vincoli essenziali |
|---|---|
| `canonical_aggregate` | `(tenant, type, ref)`, revision monotona, state digest |
| `canonical_commit` | commit ID, aggregate, from/to revision, Decision/Authority/Evidence/GCS/GatePackage |
| `canonical_idempotency` | unique aggregate+key, command digest, receipt |
| `canonical_outbox` | event ID, `branch CHECK main`, commit FK, payload digest, delivery state |
| `canonical_source_binding` | commit FK, claim/source/evidence refs |

### 2.4 C4 — Projection Adapters

Package: `ocor.c4.typedb`, `ocor.c4.jena`, `ocor.c4.watermark`, `ocor.c4.drift`.

Ogni projector consuma eventi C3 in ordine per aggregate, verifica schema/release/GCS, applica idempotentemente, e avanza il watermark soltanto nella stessa transazione della projection. TypeDB espone facts/relations e snapshot query; Jena espone RDF/JSON-LD e SHACL con marking conservativo. `ProjectionDriftDetector` ricostruisce sample dal canonical commit, confronta digest semantico, mette in quarantine la projection divergente e impedisce `EXACT_AT_COMMIT`. Rebuild usa checkpoint firmato e replay bounded; nessuna projection è authoritative.

### 2.5 C5 — Event Backbone

Package: `ocor.c5.envelope`, `ocor.c5.kafka`, `ocor.c5.schema`, `ocor.c5.retry`, `ocor.c5.replay`, `ocor.c5.dlq`.

Il `CanonicalIngestionEnvelope` chiuso include event ID/type/version, producer principal, source ref, occurred/received time, payload schema/digest/ref, marking, provenance/evidence, GCS/digest, correlation/causation, ontology/policy pins e idempotency key. Producer firma envelope e digest.

Failure taxonomy:

| Classe | Azione |
|---|---|
| `TRANSIENT` | exponential backoff con jitter bounded e retry budget |
| `PERMANENT` | DLQ immutabile, nessun retry automatico |
| `POLICY_DENIED` | audit + quarantine non divulgante |
| `POISON` | partition quarantine e operator gate |

Checkpoint lega topic/partition/offset, schema registry digest, release e GCS. Replay dichiara window e reason, preserva event ID, non bypassa policy e non pubblica due volte un canonical effect. Backpressure applica quote per tenant e priority class; audit/security non vengono eliminati. Schema incompatibile blocca producer e consumer startup.

### 2.6 C6 — Action Engine & Saga Coordinator

Package: `ocor.c6.proposal`, `ocor.c6.control`, `ocor.c6.approval`, `ocor.c6.decision`, `ocor.c6.dispatch`, `ocor.c6.reconcile`, `ocor.c6.outcome`.

Record distinti e immutabili: `ActionProposal`, `PolicyAuthorityDecision`, `Approval`, `ApprovalSet`, `Decision`, `ActionIntent`, `GatePackage`, `ActionCommand`, `DeliveryAttempt`, `ExecutionResult`, `OutcomeAssessment`, `ConflictScope`, `IndeterminateEffectAdjudication`. Nessun record è alias di un altro. Il command al C3 usa §1.5; il dispatch esterno usa §1.4 e la `EMISSION-FENCE` §3.1.

### 2.7 C7 — Causal Runtime & Scenario Orchestrator

Package: `ocor.c7.scenario`, `ocor.c7.scm`, `ocor.c7.identification`, `ocor.c7.inference`, `ocor.c7.sensitivity`, `ocor.c7.scheduler`, `ocor.c7.result`.

`CausalQuery` include baseline commit, scenario branch, SCM/model/release digest, estimand, treatment, outcome, population, factual evidence set, assumptions, seed, validity envelope e resource budget. `IdentificationService.identify()` restituisce `IDENTIFIED(method, assumptions)` oppure `ABSTAIN(reason_code)`; solo il primo abilita estimation. OOD, positivity failure, unresolved confounding, missing factual set, incompatible release o contaminated main producono reason code disgiunti senza stima. Il risultato include uncertainty, sensitivity, lineage, inputs, seed e reproducibility digest. C7 scrive solo branch scenario; promozione su `main` richiede nuova proposta C6 e non è automatica.

### 2.8 C8 — Governed Agent Kernel

Package: `ocor.c8.run`, `ocor.c8.task`, `ocor.c8.assignment`, `ocor.c8.handoff`, `ocor.c8.dissent`, `ocor.c8.memory`, `ocor.c8.memory.content`, `ocor.c8.memory.index`, `ocor.c8.memory.consolidation`, `ocor.c8.memory.lifecycle`, `ocor.c8.budget`, `ocor.c8.tools`.

Record chiusi: `AgentRun`, `Task`, `Assignment`, `Commitment`, `Handoff`, `Dissent`, `DecisionProposal`, `ToolInvocation`, `GovernedMemoryItem`. Task graph rifiuta cicli e depth oltre policy; assignment verifica machine identity, capability, delegation, autonomy tier, budget e termination condition. Handoff conserva sender, recipient, schema, input/output refs, GCS digest e accepted/rejected status. Dissent non può essere sovrascritto: la risoluzione crea un record separato.

Il PoC specifica il profilo completo `FULL_GOVERNED_AGENT_MEMORY` con gli enum esatti `WORKING`, `EPISODIC`, `SEMANTIC`, `PROCEDURAL`, `PREFERENCE`, `REFLECTION`, `DISSENT`, `TEAM_SHARED` e gli scope esatti `RUN`, `TASK`, `AGENT`, `TEAM`, `PROJECT`, `DOMAIN`, `FEDERATED`; include persistenza cross-run, retrieval `STRUCTURED`/`FULL_TEXT`/`VECTOR`/`HYBRID`, consolidation, versioning, forgetting, legal hold, deletion e promotion proposal. Sono bounded soltanto volume, payload, dimensione degli indici, concorrenza e SLO PoC. Questa è completezza di design, non un claim di implementazione.

#### 2.8.1 Port e componenti memory

| Port/componente | Responsabilità |
|---|---|
| `MemoryAdmissionPort` | closed-schema admission, source/evidence/provenance, marking, taint, scope e idempotency |
| `MemoryMetadataStore` | item/version/lifecycle/scope/digest e link immutabili |
| `MemoryContentStore` | payload content-addressed, cifrati e policy-bound |
| `MemoryLexicalIndexPort` | full-text projection policy-partitioned |
| `MemoryVectorIndexPort` | embedding/ANN projection versionata e policy-partitioned |
| `MemorySearchPort` | structured/full-text/vector/hybrid named queries |
| `MemoryConsolidationWorker` | derived summary/reflection con lineage, uncertainty e dissent |
| `MemoryLifecycleCoordinator` | supersession, revocation, expiry, legal hold e deletion saga |
| `MemoryPromotionPort` | crea `MemoryPromotionProposal`; nessuna scrittura C3 diretta |
| `MemoryContextAssembler` | selezione, redazione, ordering, truncation e influence receipt |

Indici lessicali e vettoriali sono proiezioni ricostruibili. L'autorità dei metadata memory non è autorità sullo stato canonico. Gli ID backend non attraversano i port.

#### 2.8.2 Admission e versioning

`admitMemory` costruisce il GCS da binding autenticato, valida schema/digest, rifiuta chain-of-thought/segreti/credenziali/raw history non governata, risolve Evidence/Provenance, calcola marking e taint, verifica scope/retention/quota/policy e scrive atomicamente metadata, content ref, lifecycle event e audit. Le proiezioni sono asincrone e legate allo stesso item/version digest.

Idempotency key: `(tenant_id, memory_scope, source_digest, content_digest, operation_id)`. Stessa key e digest restituisce la receipt originale; digest diverso produce `MEMORY_IDEMPOTENCY_CONFLICT`.

Ogni modifica semantica crea una nuova versione. `supersedes_ref`, `correction_of_ref`, `derived_from_refs` e `consolidates_refs` preservano la storia. Nessun update in-place del contenuto è ammesso.

#### 2.8.3 Retrieval e non-interference

La richiesta dichiara contract/version, mode, kind/scope, time window, top-k e ranking profile. Policy pre-query produce una partizione autorizzata; policy post-query rivalida ogni item prima della materializzazione. Item non autorizzati non influenzano ANN graph, score normalization, rank, count, pagination, diversity, cache, explanation, error o timing bucket.

`HYBRID` conserva separatamente lexical score, vector score, recency, confidence, source quality, diversity e policy factors. Il risultato espone item/version, content/evidence/provenance refs, marking, score factors e explanation policy-safe. Score non equivale a verità.

#### 2.8.4 Embedding lifecycle

`EmbeddingDescriptor` lega item/version/content digest a model/version/digest, tokenizer, dimensioni, normalization profile, purpose e marking. Upgrade del modello crea una representation version parallela e una rebuild deterministica. Cross-compartment centroid, ANN graph e cache condivisi sono vietati senza una specifica prova di non-interference. Revoca, expiry, reclassification o deletion invalidano la representation prima della successiva materializzazione.

#### 2.8.5 Consolidation, reflection e dissent

`MemoryConsolidationJob` contiene input query/digest, item/version refs, algorithm/model pins, target kind/scope, budget e reviewer policy. Produce un nuovo item derivato con uncertainty e lineage. Non sovrascrive gli input e non abilita istruzioni. Contraddizioni producono `DISSENT`/conflict records; frequency e majority non eliminano alternative.

`PROCEDURAL` memory richiede `instruction_approval_ref` per `instruction_eligible=true`, ma ogni uso rivalida policy, capability, delegation, purpose e kill switch. `REFLECTION` resta tainted e instruction-ineligible di default.

#### 2.8.6 Lifecycle, forgetting e deletion

FSM: `PROPOSED → ACTIVE|QUARANTINED`; `ACTIVE → SUPERSEDED|REVOKED|EXPIRED|LEGAL_HOLD|DELETION_PENDING`; terminalizzazione tramite `DELETION_PENDING → DELETED|DELETION_INCOMPLETE`, con retry governato da `DELETION_INCOMPLETE`. Uscire da legal hold ripristina la disposition precedente registrata.

Il deletion saga cancella content, embeddings, full-text/vector entries, cache, repliche ed export; scrive deletion epoch e tombstone non-content. Fino al completamento, retrieval fallisce chiuso. Restore applica i tombstone prima di riaprire gli indici per impedire resurrection.

#### 2.8.7 Context influence e promotion

Ogni inserimento nel contesto produce `MemoryContextAssembly` con query digest, item/version selezionati, policy decisions, redactions, ordering, truncation, context ref/digest e audit ref. Non viene memorizzato il ragionamento interno del modello.

Promotion path obbligatorio: `MemoryItem → MemoryPromotionProposal → C6 control/approval/decision → GovernedCanonicalCommitCommand → C3`. Memory non concede Authority, Approval, Decision, CapabilityLease o ActionCommand.

#### 2.8.8 Threat model memory

Test e controlli coprono prompt injection, poisoning, provenance laundering, embedding inversion, membership inference, cross-scope leakage, confused deputy, delegation replay, capability escalation, agent collusion/conformity, dissent suppression, malicious consolidation, procedural activation, stale policy, marking downgrade, deletion resurrection e kill-switch race.

### 2.9 Superfici operatore e developer tooling

Le UI sono client non autoritativi di C1, C2, C6 e C8. Non accedono direttamente ai backend, non costruiscono `effective_principal_id` e trasformano ogni modifica in change proposal firmata. `MissionThreadView` mostra trace, release, authority, marking, evidence e stato senza appiattire conflitti o astensioni. Le viste role-oriented applicano lo stesso GCS delle API e non nascondono reason code di governance agli utenti autorizzati.

CLI, IDE/LSP, SDK Python/TypeScript e import/export sono generati o verificati contro la Canonical IR. Localizzazione separa chiavi stabili da traduzioni; accessibilità segue WCAG 2.2 AA per keyboard, focus, contrasto, semantic labels e annunci di stato. Test cross-SDK confrontano canonical bytes, digest, errori e retry semantics. Export contiene manifest, schema/release pin, marking, provenance e digest; reimport verifica tutto prima di materializzare.

## 3. Workflow C6 normativo

### 3.1 Guardie

`G-CONTRACT` valida ActionType firmato, parametri, risk/effect class, timeout/retry/idempotenza/compensabilità, marking e provenance. `G-AUTHORITY` richiede principal, capability, delegation, purpose, risk ceiling e control-plane disponibili. `G-APPROVAL` applica quorum/SoD/firme/scope/TTL. `G-DECISION` accetta soltanto Decision firmata e non scaduta. `G-FRESHNESS` confronta revision, commit, GCS, policy, authority, approval, ontology, adapter e watermark. `G-DISPATCH` confronta stop epoch, lease, fencing, audit, circuit breaker, adapter, key, deadline e command digest.

`EMISSION-FENCE = G-FRESHNESS ∧ G-DISPATCH` è valutata atomicamente immediatamente prima di primo dispatch, retry, compensation e canonical commit. Errore o drift produce `INVALIDATED` prima dell'effetto.

### 3.2 Tabella completa delle 44 transizioni

| ID | Source | Evento/guardia | Effetto durevole | Destination |
|---|---|---|---|---|
| `ACT-T01` | `[*]` | nuova proposta; `G-CONTRACT` | registra proposta, GCS, fingerprint ed Evidence | `PROPOSAL_RECORDED` |
| `ACT-T02` | `PROPOSAL_RECORDED` | stessa idempotency key e fingerprint | restituisce receipt originale | `PROPOSAL_RECORDED` |
| `ACT-T03` | `[*]` | stessa key, fingerprint diverso | reason code `IDEMPOTENCY_CONFLICT` | `DENIED` |
| `ACT-T04` | `PROPOSAL_RECORDED` | avvio; `G-AUTHORITY` valutabile | registra policy snapshot | `CONTROL_CHECK` |
| `ACT-T05` | `CONTROL_CHECK` | deny/timeout/control unavailable | reason code fail-closed | `DENIED` |
| `ACT-T06` | `CONTROL_CHECK` | Human Gate richiesto | work item + Evidence + expiry | `APPROVAL_PENDING` |
| `ACT-T07` | `CONTROL_CHECK` | gate non richiesto e target non canonical | disposition `NOT_REQUIRED` | `APPROVAL_RESOLVED` |
| `ACT-T08` | `APPROVAL_PENDING` | `G-APPROVAL` | quorum/firme/scope/TTL | `APPROVAL_RESOLVED` |
| `ACT-T09a` | `APPROVAL_PENDING` | rifiuto esplicito | rejection record | `APPROVAL_REJECTED` |
| `ACT-T09b` | `APPROVAL_PENDING` | expiry | expiry record | `APPROVAL_EXPIRED` |
| `ACT-T10a` | `DECISION_PENDING` | Decision reject/expire | Decision + rationale | `DECISION_REJECTED` |
| `ACT-T10b` | `DECISION_PENDING` | `G-DECISION`, ACCEPT | Decision + rationale | `INTENT_RECORDED` |
| `ACT-T11` | `INTENT_RECORDED` | Decision valida | ActionIntent senza command | `PRE_DISPATCH_CHECK` |
| `ACT-T12` | `PRE_DISPATCH_CHECK` | `EMISSION-FENCE` | command, GatePackage digest, lease, stop epoch e outbox atomici | `COMMAND_READY` |
| `ACT-T13` | `PRE_DISPATCH_CHECK` | drift materiale | invalida; nessun command | `INVALIDATED` |
| `ACT-T14` | `COMMAND_READY` | external target; `EMISSION-FENCE` atomica | DeliveryAttempt + invio | `DISPATCHED` |
| `ACT-T15` | `DISPATCHED` | ACK correlato | receipt, non successo | `ACKNOWLEDGED` |
| `ACT-T16` | `ACKNOWLEDGED` | conferma positiva | ExecutionResult confirmed | `EXECUTION_CONFIRMED` |
| `ACT-T17a` | `DISPATCHED` | fallimento definitivo | ExecutionResult failed | `EXECUTION_FAILED` |
| `ACT-T17b` | `ACKNOWLEDGED` | fallimento definitivo | ExecutionResult failed | `EXECUTION_FAILED` |
| `ACT-T18a` | `DISPATCHED` | timeout ambiguo | sospende retry e apre reconciliation | `EXECUTION_UNKNOWN` |
| `ACT-T18b` | `ACKNOWLEDGED` | confirmation timeout | sospende retry e apre reconciliation | `EXECUTION_UNKNOWN` |
| `ACT-T19` | `COMMAND_READY` | retry autorizzato; `EMISSION-FENCE` atomica; stessa key | nuovo DeliveryAttempt, stesso logical command | `DISPATCHED` |
| `ACT-T20a` | `EXECUTION_UNKNOWN` | Evidence positiva di effetto | reconciliation record | `EXECUTION_CONFIRMED` |
| `ACT-T20b` | `EXECUTION_UNKNOWN` | Evidence positiva di non-effetto/failure | reconciliation record | `EXECUTION_FAILED` |
| `ACT-T20c` | `EXECUTION_UNKNOWN` | nessuna Evidence prima del deadline | inquiry record, nessuna inferenza | `EXECUTION_UNKNOWN` |
| `ACT-T21` | `EXECUTION_FAILED` | compensation autorizzata | crea command correlata, poi `EMISSION-FENCE` prima dell'invio | `COMPENSATING` |
| `ACT-T21a` | `COMPENSATING` | Evidence di successo | result record | `COMPENSATED` |
| `ACT-T21b` | `COMPENSATING` | Evidence di failure | result record | `COMPENSATION_FAILED` |
| `ACT-T21c` | `COMPENSATING` | timeout ambiguo | sospende retry, apre reconciliation | `COMPENSATION_UNKNOWN` |
| `ACT-T21d` | `COMPENSATION_UNKNOWN` | Evidence di effetto | reconciliation record | `COMPENSATED` |
| `ACT-T21e` | `COMPENSATION_UNKNOWN` | Evidence di failure | reconciliation record | `COMPENSATION_FAILED` |
| `ACT-T22` | `OUTCOME_PENDING` | Observation/Evidence correlata | OutcomeAssessment separato | `OUTCOME_ASSESSED` |
| `ACT-T23a` | `PRE_DISPATCH_CHECK` | cancel/stop | nessun command | `CANCELLED` |
| `ACT-T23b` | `COMMAND_READY` | stop prima dell'emissione; precedenza | nessun DeliveryAttempt | `CANCELLED` |
| `ACT-T24` | `EXECUTION_UNKNOWN` | reconciliation deadline | apre adjudication, conserva ConflictScope | `EXECUTION_INDETERMINATE` |
| `ACT-T25` | `COMPENSATION_UNKNOWN` | reconciliation deadline | apre adjudication, conserva ConflictScope | `COMPENSATION_INDETERMINATE` |
| `ACT-T26` | `APPROVAL_RESOLVED` | Approval assessment risolta | congela pin decisionali | `DECISION_PENDING` |
| `ACT-T27` | `EXECUTION_CONFIRMED` | confirmation record | apre assessment window | `OUTCOME_PENDING` |
| `ACT-T28` | `OUTCOME_PENDING` | assessment window expired | assenza osservata, nessun valore inferito | `OUTCOME_UNOBSERVED` |
| `ACT-T29` | `COMMAND_READY` | canonical target; `EMISSION-FENCE` atomica | invia a C3 Decision/Authority/Evidence/binding/revision/GCS | `CANONICAL_COMMIT_PENDING` |
| `ACT-T30` | `CANONICAL_COMMIT_PENDING` | commit receipt C3 | canonical commit ID + accepted refs | `EXECUTION_CONFIRMED` |
| `ACT-T31a` | `CANONICAL_COMMIT_PENDING` | precondition/invariant failure | reason code `PRECONDITION_FAILED` o `INVARIANT_VIOLATION` | `EXECUTION_FAILED` |
| `ACT-T31b` | `CANONICAL_COMMIT_PENDING` | revision/GatePackage/GCS drift | reason code `REVISION_CONFLICT`, `GATE_PACKAGE_MISMATCH` o `GOVERNED_CONTEXT_MISMATCH` | `INVALIDATED` |

`ACT-T23` precede T14, T19 e T29. ACK non equivale a successo. Timeout post-dispatch non idempotente produce UNKNOWN e sospende retry. Compensation è una nuova operazione governata. Gli stati indeterminati preservano `ConflictScope` e bloccano proposte confliggenti fino a adjudication firmata con Evidence.

## 4. Security, governance e Human Gate

### 4.1 Classificazione e controllo

| Classe | Esempio | Gate minimo |
|---|---|---|
| `R0_READ` | query policy-filtered | identity + policy + purpose |
| `R1_DERIVE` | inferenza/scenario | R0 + model/function authority + provenance |
| `R2_MUTATE` | canonical mutation | Decision + Authority + C6 path + EMISSION-FENCE |
| `R3_HIGH_IMPACT` | azione interagenzia/irreversibile | due umani distinti, Domain e National Approver, SoD, expiry |

`GatePackage` contiene proposal/action digest, revision, GCS digest, policy bundle, ontology release, authority, approval set, adapter binding, watermark, stop epoch, validity window e ConflictScope. È immutabile e ogni consumer ricalcola il digest.

### 4.2 Break-glass

Break-glass richiede motivo tipizzato, incidente, scope minimo, TTL breve, due principal umani distinti e audit sincrono. Non può: creare Decision, ridurre marking, disabilitare provenance/audit, ignorare emergency stop, cambiare release pin, autorizzare R3 senza quorum o accedere fuori compartment. Ogni uso genera review obbligatoria e revoca automatica alla scadenza.

### 4.3 Emergency stop

FSM: `NORMAL → STOPPING → STOPPED → RESET_PENDING → NORMAL`. L'accettazione dello stop incrementa atomicamente `stop_epoch`, revoca lease e impedisce nuovi DeliveryAttempt. STOPPING drena solo operazioni esplicitamente safe; UNKNOWN/INDETERMINATE restano in reconciliation. Reset richiede dual control, verifica incident/recovery, nuovo epoch e non riabilita lease precedenti.

### 4.4 Zero trust e supply chain

Workload identity SPIFFE/SPIRE, user identity federata, policy OPA, secret reference OpenBao e mTLS sono fail-closed. Nessun secret compare nei config file o log. Immagini, SBOM, schema, policy, ontology e model sono firmati e pin-nati. Egress è deny-by-default; ogni eccezione è allow-listata, scoped e auditata.

## 5. Deployment, operazioni e recovery

### 5.1 Profilo PoC

Single-site isolato, namespace e service account per subsystem, network policy deny-by-default, egress zero salvo endpoint simulati approvati. ResourceClass (`CONTROL`, `INTERACTIVE`, `BATCH`, `AUDIT`) determina quota, priority e backpressure. C6/control/audit non condividono pool esauribile con causal batch.

### 5.2 Configuration baseline fail-closed

Ogni CI ha endpoint/ref, version/digest, trust bundle, identity, timeout, retry budget, circuit breaker, storage prefix, backup policy e health contract: TerminusDB, TypeDB, Jena, Temporal/PostgreSQL, Kafka/Schema Registry, object store S3, memory metadata store, full-text index, vector index, embedding worker, OPA, Keycloak, SPIFFE, OpenBao, audit store, registries e simulatore. Memory backend e embedding model sono port-bound e manifestati; una sostituzione deve preservare non-interference, deletion epoch, representation version e rebuild semantics. Pin assente o incompatibile blocca startup. PostgreSQL resta adapter di verifica dell'atomicità e non sostituisce implicitamente TerminusDB.

### 5.3 Observability e safe-degraded

Log/metric/trace includono correlation ID, component, operation, release, policy digest e reason code, ma non payload classificati. Query può degradare soltanto se la modalità richiesta lo consente e dichiara staleness. Policy/authority/audit/identity indisponibili bloccano mutazioni e dispatch. Projection non pronta blocca exact consistency; causal model fuori envelope astiene.

### 5.4 Backup, restore e replay

Backup set lega canonical state/history, idempotency, outbox, audit, schemas, policy, ontology, registry, projection checkpoint, scenario metadata, memory metadata/content refs, representation versions, lifecycle/deletion epochs e object refs allo stesso recovery point. È cifrato, firmato, authority-aware e testato. Restore avviene in rete isolata: verifica manifest/digest/firme → ripristina authority stores → canonical state → idempotency/outbox → memory tombstone/deletion journal → projections via replay → audit reconciliation. Il recovery gate controlla revision, watermark, orphan/duplicate, marking, GCS, deletion resurrection e sample semantic digest prima di riaprire traffico. Replay usa event IDs originali e non emette effetti esterni.

## 6. Concorrenza e failure semantics

- C3: serializzazione per aggregate e optimistic revision; retry solo prima di side effect o con idempotency comprovata.
- C4/C5: ordering per aggregate/partition; watermark monotono; deduplica durable.
- C6: un action owner per fencing token; scheduler timeout non decide l'esito del mondo.
- C7: job cancellabile con resource release e sealed result; seed e inputs pin-nati.
- C8: task claim con lease bounded; cycle/depth/budget enforcement; cancellation cooperativa e kill switch preemptive.
- Control-plane timeout, unknown schema, invalid signature, ambiguous marking o missing authority sono permanent deny per la singola operazione, non retry permissivo.

## 7. Verifica e acceptance

### 7.1 Behavioural Acceptance BA-01–BA-08

| BA | Target e oracle |
|---|---|
| BA-01 | C3 selezionato: state+revision+commit+idempotency+outbox atomici sotto crash windows |
| BA-02 | TypeDB facts/relations e watermark atomici, policy-safe |
| BA-03 | TypeDB exact-at-commit o `PROJECTION_NOT_READY`, mai downgrade |
| BA-04 | Jena RDF/JSON-LD/SHACL e marking join senza leakage |
| BA-05 | Temporal/PostgreSQL esegue le 44 transizioni, guardie, unknown e precedence |
| BA-06 | S3/PostgreSQL sigilla causal result, lineage, identify-or-abstain e isolation |
| BA-07 | Kafka/Strimzi replay, dedup, backpressure, DLQ/quarantine e schema compatibility |
| BA-08 | OPA/Keycloak/SPIFFE/OpenBao applicano identity, delegation, policy, lease, stop e secret isolation |

### 7.2 Test obbligatori

Schema/meta tests verificano record chiusi, exact field set, canonical bytes, digest e negative corpus. Contract tests verificano OpenAPI/Proto/JSON Schema e generated SDK drift. Fault injection copre ogni crash window C3, lost ACK, duplicate delivery, control-plane timeout, stale watermark, expired Approval/lease, stop race, poison event, restore divergence e cross-compartment non-interference. `FGM-01`–`FGM-20` sono la futura campagna di evidenza runtime della memoria governata completa; `DEC-208` ha già promosso il design, non i relativi esiti.

| FGM | Fixture o fault | Oracle documentato |
|---|---|---|
| `FGM-01` | ogni memory kind/scope valido | schema chiuso, versione immutabile, provenance e audit |
| `FGM-02` | campo mancante/malformato o content class vietata | rigetto prima della persistenza |
| `FGM-03` | consolidation working→episodic/semantic | nuovo item derivato; sorgenti immutate e collegate |
| `FGM-04` | retrieval cross-run | versione esatta autorizzata e influence trace |
| `FGM-05` | retrieval cross-project/federated | Authority esplicita e zero leakage non autorizzato |
| `FGM-06` | equivalenza structured/full-text/vector/hybrid | risultato policy-filtered e representation/ranking pin |
| `FGM-07` | upgrade embedding model | representation parallela versionata e rebuild deterministico |
| `FGM-08` | prompt injection/poisoning | taint, non-eseguibilità, quarantine o rendering sicuro |
| `FGM-09` | correction/supersession | nuova versione immutabile ed exact-version replay |
| `FGM-10` | revocation/expiry/reclassification | assenza da result, rank, count, cache ed explanation |
| `FGM-11` | legal hold e rilascio | deletion bloccata e prior disposition ripristinata |
| `FGM-12` | deletion saga con failure parziale | `DELETION_INCOMPLETE` fail-closed, poi completamento |
| `FGM-13` | consolidation conflict/dissent | fonti conflittuali preservate, nessun majority merge silenzioso |
| `FGM-14` | procedural activation | approvazione separata e policy/capability live rivalidate |
| `FGM-15` | memory→canonical promotion | percorso C6/C3 completo, nessuna write diretta |
| `FGM-16` | non-interference cross-compartment | zero leakage content/existence/rank/count/cache/timing |
| `FGM-17` | race kill switch/revoca delega | nessuna retrieval o tool influence successiva |
| `FGM-18` | restore dopo deletion | nessuna resurrezione; tombstone riconciliato |
| `FGM-19` | quota/retention pressure | selezione deterministica; legal hold protetto |
| `FGM-20` | context assembly | replay esatto di item/version/redaction/order/truncation digest |

Gli oracle sono specifiche per test futuri. Nessun esito FGM è dichiarato in questa baseline documentale.

E1 dimostra implementazione del runtime slice; E2 richiede ambiente production-like, scale/security/recovery evidence e resta distinto. Nessun test legacy `RBA-*` è rinominato in `BA-*`.

### 7.3 Mission thread ed evidence package

La fixture sintetica versionata attraversa realmente C1–C8: ingestion, query/fusion, identity hypotheses, causal comparison, agent deliberation, policy/authority, approval, Decision, action simulata, ExecutionResult e OutcomeAssessment condividono correlation/causation e riferimenti verificabili. La baseline di confronto e ogni claim di parity sono nominati, circoscritti e non promossi oltre l'evidence disponibile.

L'evidence package contiene requirement ID, metodo, metrica, soglia, baseline, dataset/scenario, release/digest, risultato, log grezzo, owner e firma. Ogni P0 ha esito individuale; un P0 fallito rende il gate `NO-GO` e non è compensabile da altri risultati. Stato `Verified` richiede evidence non vuota, riproducibile e manifestata.

### 7.4 Portabilità, interoperabilità e productization

Ogni adapter sostituibile implementa un port OCOR, non espone ID backend nei contratti pubblici e supera la stessa conformance suite. W3C RDF/JSON-LD/PROV/SHACL e i formati interoperabili restano boundary dichiarati, non modello canonico alternativo. Dipendenze, licenze, provenance, vulnerabilità, maintenance status e capability limitations sono registrate in SBOM/license/exception inventory; una licenza o capability incompatibile blocca il profilo che la richiede.

Il bundle air-gapped include immagini firmate, chart/manifest, schemas, policy, ontology, models, SDK/CLI, documentazione, runbook, migration mapping, synthetic fixtures e conformance kit. Nessuna dipendenza runtime richiede rete pubblica. Il supporto di release segue compatibility matrix, migration window e rollback verificato.

### 7.5 Profili di release e gate

Capability ed elemento hanno disposition `CORE`, `OPTIONAL` o `FUTURE` e release `PoC`, `MVP` o `Production`; combinazioni non dichiarate sono `UNSUPPORTED_CAPABILITY`. Il PoC dimostra la vertical slice completa nelle funzioni e bounded soltanto per scala/resilienza, chiudendo i P0 PoC. L'exit verso MVP richiede evidence package completo, gap e risk register governati, backup/restore e portability results. L'entry Production richiede E2, scale/security/recovery campaign, SLO ratificati, operational ownership, incident response e residual-risk acceptance. LLD approval non promuove automaticamente nessuno di questi gate.

## 8. Tracciabilità bidirezionale

La matrice normativa `reports/traceability/OCOR_IRB_ADD_LLD_v1.1_Matrix.md` contiene una riga per ciascuno dei 285 requisiti IRB approvati con anchor ADD, anchor LLD, metodo e disposition. Il JSON omologo è machine-readable. Il gate rifiuta:

- ID mancanti, duplicati o non presenti nel Requirement Register approvato;
- anchor LLD inesistenti;
- `FULLY_SPECIFIED` privo di design e metodo;
- `NOT_APPLICABLE` senza razionale e authority;
- qualunque `GAP` per P0/PoC;
- downgrade di priorità/release, riferimento al profilo bounded superseduto o trattamento del full memory profile approvato come ancora candidato.

Reverse traceability: ogni schema, port, tabella, transition e test dichiara almeno un requisito nella matrice; artefatti senza origine sono `ORPHAN_DESIGN`.

## 9. Disposizione di approvazione

`DEC-208` ha approvato questa LLD v1.1 e ha promosso atomicamente `CC-FULL-GOVERNED-AGENT-MEMORY`, i cinque registri, ADD v1.3 e i contratti manifestati. LLD v1.0 è pertanto superseduta come specifica tecnica corrente.

La matrice autoritativa assegna tutti i 285 requisiti IRB con disposition di design `FULLY_SPECIFIED`; per `FR-118` e `FR-119` lo stato probatorio resta `specified/planned`, `E1=0`, `E2=0`. L'approvazione documentale non costituisce implementazione: full-memory runtime, conformità runtime e Production readiness restano `NO-GO` fino alla chiusura governata delle campagne applicabili, incluse `FGM-01`–`FGM-20`.

L'errata editoriale `CC-IRB-ADD-LLD-AUTHORITY-SEAL`, approvata da `DEC-209`, elimina esclusivamente il testo pre-promozione residuo. Non modifica comportamento, priorità, release, contratti, capability disposition o stato probatorio approvati da `DEC-208`.
