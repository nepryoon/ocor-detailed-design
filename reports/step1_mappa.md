# STEP 1 — Mappa dell'ADD v1.1

Oggetto letto integralmente: `OCOR_Architectural_Design_Document_v1.1.md` (3.381 righe). Sono stati inoltre letti integralmente `OCOR_DEC_197_plus_Draft_v0.1.md` e `DELTA_MANIFEST.json`. I registri normativi non sono stati letti linearmente e saranno interrogati soltanto per ID quando necessario. In FASE 1 non è stato aperto né ricostruito alcun materiale `inputs/supporting/prior/`.

| Sezione | Cosa normalizza | Contratti o invarianti principali |
|---|---|---|
| §1.1 Controllo | Identità, stato, baseline, change control ed evidence fence del documento. | `PROPOSED — PENDING CHANGE CONTROL`; `Design Target`/`Candidate Implementation`; `E1=0`, `E2=0`, zero `Verified`; nessun nuovo `DEC-*`. |
| §1.2 System context | Attori, sistemi esterni e confine sovrano C4 L1. | Authority locale; separazione fra source, target, approver e agenti. |
| §1.3 Autorità | Autorità di definizioni, Observation/Claim, Canonical State, Projection, Prediction, Intervention, Action e Outcome. | `Observation/Claim ≠ Canonical State ≠ Projection ≠ Prediction ≠ Intervention ≠ Action ≠ Outcome`; niente master universale o ACID globale. |
| §1.4 Trust boundaries | Nove boundary, fail state e set minimo del contesto governato. | `TB-CXT-01`–`09`; Governed Context Set di 11 campi; isolamento per tenant/domain/compartment/purpose/marking/release; join conservativo. |
| §1.5 Scope fence | Perimetro PoC, elementi differiti/fuori scope ed evidence fence. | `FR-048`, hardening esteso `CAP-024` e nove `ELM-*` differiti; `CAP-026` out of scope. |
| §2.1 Container view | Flussi C4 L2 fra gli otto subsystem, release bundle, control plane e overlay. | `C6→C3` per commit canonico; `C7→OVL`; outbox/eventi asincroni. |
| §2.2 Subsystem | Responsabilità, porte, stato, backend candidati e posture degradate di `C1`–`C8`. | Single writer logico; proiezioni ricostruibili; at-least-once; no accesso backend diretto per agenti. |
| §2.2.1 Moduli e porte | Confini interni e SPI vendor-neutral. | Dipendenze attraverso port logici, non dialect o schema fisico. |
| §2.3 Atomicità locale | Finestre di crash e propagazione tramite outbox. | Stato canonico e outbox nello stesso commit locale; niente 2PC globale; riconciliazione obbligatoria. |
| §2.4 Triade e capability | Ruoli `VersionedAssertedState`, `LogicProjection`, `W3CBoundary` e disposizioni di capability. | Un solo master asserito; `exact` è semantica target; `unsupported` blocca il profilo salvo eccezione governata. |
| §2.5 Regole d'interazione | Dodici invarianti cross-container. | Version pin; idempotenza/fencing; C6 unico produttore di mutazioni canoniche; relay outbox solo `main`; nessuna promozione probatoria. |
| §2.6 Backend Assumption Register | Assunzioni non verificate `BA-01`–`BA-08`, test, fallback e impatto. | Nessuna riga è evidenza; un profilo dipendente è `NO-GO` finché il relativo test non ha esito. |
| §3.0.1 Governed Context | Dichiarazione campo-per-campo della realizzazione del set minimo. | Origine trusted/transport per `principal_id`, `actor_chain`, digest e binding; tabella di copertura per sei superfici. |
| §3.0.2 Marking | Forma canonica e relazione fra marking inline, ref e `SecurityContext`. | `*_marking_ref = urn:sha256:<marking_digest>`; ref irrisolvibile ⇒ `DENY`. |
| §3.0.3 Naming | Nome e cardinalità dei compartimenti. | Solo `compartments[]`, `minItems: 1`, `uniqueItems: true`. |
| §3.0.4 Versioning | Versioni corrette in v1.1 e applicabilità di `NFR-088`. | Bump envelope/MCP/OpenAPI; nessun consumer rilasciato dichiarato. |
| §3.1 OaC/IR | Metamodello OaC, normalizzazione deterministica e IR firmata. | `ContractDefinition`, `MarkingSchemeDefinition`, `CapabilityDisposition`; RFC 8785, SHA-256, DSSE e admission offline. |
| §3.2 Ingestion | JSON Schema dell'envelope batch/stream/CDC e regole runtime. | Schema chiuso; `CDC_CHANGE ↔ CDC`; payload non canonico; quarantine; at-least-once senza claim exactly-once. |
| §3.3 Query Gateway | OpenAPI 3.1 delle sei query nominate e relative risposte/errori. | Schemi chiusi generati; version/consistency fence; `served` obbligatorio per errori version-sensitive; niente query backend arbitrarie. |
| §3.4 Function/Model | Protobuf/gRPC del registry e dell'invocazione pin-nata. | Function non committa; model produce prediction/belief/recommendation o abstention; `oneof` runtime obbligatorio. |
| §3.5 MCP Tool | JSON Schema di tool governance separato dal binding. | Approval/quorum, retry, idempotenza, compensation, error model e tier coerenti; fence PoC contro `EXECUTE_APPROVED_ACTION`. |
| §3.6 Provenance/Evidence | Metamodello PROV-O, identity resolution e truth maintenance. | Nessuna promozione implicita; Claim e CanonicalAssertion sorelle; merge/split reversibili; marking/provenance conservati. |
| §3.7 Action Type | Nuovo JSON Schema `ACTION` per target esterno o commit canonico. | Timeout completi, risk/approval, retry/idempotenza, compensation; `canonical_commit_binding`; `CanonicalAssertion` richiede Claim ed evidence set. |
| §3.8 Event Subscription | Nuovo JSON Schema `EVENT` per change feed. | At-least-once, deduplica su `event_id`, ordering logico, filter nominato, cursor opaco, marking e replay autorizzato. |
| §3.9 Conformance target | Criteri e future evidence per contratti, marking e provenance. | Tutti `NOT RUN`; nessun incremento di `E1`/`E2`. |
| §4.1 Action FSM | Pipeline unica per azioni esterne e commit canonici. | Record append-only distinti; 29 stati; `ACT-T01`–`T31`; nessuna transazione distribuita. |
| §4.1.1 Guardie | Condizioni congiuntive di contract, authority, approval, decision, freshness e dispatch. | Rivalidazione fail-closed; blocco su effetti esterni irrisolti per stesso aggregate/target. |
| §4.1.2 Transizioni | Effetti durevoli, guardie e destinazioni normative. | `ACT-T14`/`T19`/`T29` rivalidano all'emissione; indeterminatezza terminale; `ACT-T23` precede dispatch. |
| §4.1.3 Tempi | Configurazioni temporali candidate PoC. | Valori non verificati; timeout espliciti obbligatori; nessuno SLO osservato. |
| §4.2 Causal/Scenario | Overlay COW, outcome causale, abstention e workload asincroni. | No `main.write`/ActionCommand; identify-or-abstain; `ELM-070` differito; result pin-nato e riproducibile come target. |
| §4.3 Multi-agent | Ruoli, typed handoff, lifecycle e invarianti del Kernel. | Autorità non deriva da prompt; no peer-to-peer/DB credentials; dissent preservato; tier PoC fino a `propose`. |
| §5.1 Control plane | Identity, PKI, policy, secret e audit con posture al guasto. | Autenticazione ≠ autorizzazione; policy/authority/delegation separati; mutazioni fail-closed. |
| §5.2 Delegation/lease | Delegation firmata e Capability Lease di sicurezza. | Nessuna amplificazione; lease ≤5 s legato a `stop_epoch`; distinto da `ELM-080` e writer fencing. |
| §5.3 Marking algebra | Propagazione di classificazione, restrizioni e permessi. | Join di reticolo; unione restrizioni; intersezione permessi; contesto incompleto/incomparabile non apre accesso. |
| §5.4 Human Gate | Classi di rischio e separation of duties. | `R2` un approvatore indipendente; `R3` due; Approval ≠ Decision ≠ Authority. |
| §5.5 Break-glass/stop | Eccezioni bounded e contenimento. | Break-glass non disabilita controlli hard; stop incrementa epoch; nessun retry cieco; reset dual-control. |
| §6.1 Deployment | Topologia PoC single-site e controlli di isolamento. | Nessun claim HA/multi-site; componenti restano candidati; Edge senza writer authority. |
| §6.2 Consistenza | Token di consistenza e mutation fence. | Watermark osservabile; `best-available`, `at-least-commit`, `exact-at-commit`; niente downgrade silenzioso. |
| §6.3 Observability | Campi minimi di trace e safe-degraded behavior. | Staleness esplicita; audit down blocca mutazioni; timeout adapter ⇒ unknown/reconciliation. |
| §6.4 Backup | Autorità di backup per classe di stato. | Nessun database universale; proiezioni ricostruibili; custody separata. |
| §6.5 Recovery | Sequenza di restore, replay e gate di riapertura. | Effetti indimostrabili ⇒ `EXECUTION_UNKNOWN`; target `NOT RUN`; Production fuori baseline. |
| §7 Crosswalk | Allocazione sintetica dell'universo normativo. | 693 ID core; `CAP-026` escluso dal claim; gate `DEC-*` non allocabili dichiarati. |
| §7.1 Scope disposition | Fence verificabile per differiti e out-of-scope. | Comportamento PoC tipizzato per ciascun elemento, senza attivarlo. |
| §7.2 Acceptance/evidence | Criteri, metodi e `EV-*` futuri per area. | Ogni stato `NOT RUN — E1=0/E2=0`. |
| §7.3 Closure | Limiti del claim architetturale. | `exact` non è evidenza; nessun claim di conformità/readiness prima dei gate. |
| §8 Amendment Log | Mappa `AM-01`–`AM-28` a finding, sezioni, tracciabilità e change control. | Nove bozze non approvate; emendamenti ancora proposti. |
| §8.0 Self-reported defects | Registra `RV-01` e `RV-02` e la lezione sui casi positivi. | Obbligo metodologico di un positivo per ogni ramo condizionale. |
| §8.1 Contract versions | Confronta versioni 1.0/1.1. | Nessuna breaking change su release dichiarata perché v1.0 non approvata e senza consumer. |
| §8.2 Non-goals | Elenca ciò che la revisione non chiude o promuove. | Nessun `OI/ASM/RSK` chiuso; nessuna capability attivata; evidence status invariato. |

## Superficie di delta dichiarata

Il manifest dichiara 28 emendamenti, le nuove sezioni §2.6, §3.0–§3.0.4, §3.7, §3.8 e §8–§8.2; due contratti nuovi; tre version bump; quattro stati e otto transizioni FSM aggiunti; due difetti self-reported. Questa è la superficie primaria degli STEP 2–6, con controlli di coerenza verso il testo preesistente dell'ADD v1.1.
