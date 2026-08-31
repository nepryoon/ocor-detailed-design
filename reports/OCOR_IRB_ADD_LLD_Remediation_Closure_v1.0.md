# OCOR — Chiusura tecnica della remediation IRB → ADD → LLD

## 1. Verdetto

**Esito: `TECHNICALLY READY FOR GOVERNED BASELINE PROMOTION`.**

La candidata recepisce la disposizione del requester: il PoC implementa la memoria governata completa e limita soltanto scala, resilienza e SLO production-grade. Il precedente bounded profile è ritirato.

Il gate riproducibile verifica:

- 285/285 requisiti IRB enumerati e allocati;
- 283 `FULLY_SPECIFIED`;
- 2 `CONDITIONALLY_SPECIFIED` (`FR-118`, `FR-119`) fino alla promozione autoritativa dei cinque snapshot candidati ora materializzati;
- zero `GAP`;
- full memory kinds/scopes, vector binding, lifecycle, API e security invariants;
- FSM C6 44/44 semanticamente identica all'ADD v1.2;
- OpenAPI e Proto originari materializzati byte-per-byte dall'ADD approvato.

## 2. Decisione memory incorporata

`CC-FULL-GOVERNED-AGENT-MEMORY` sostituisce integralmente `CC-BOUNDED-GOVERNED-MEMORY`.

La candidata porta `ELM-084` a `CORE/P0/PoC` e include:

- working, episodic, semantic, procedural, preference, reflection, dissent e team-shared memory;
- scope run, task, agent, team, project, domain e federated;
- persistenza cross-run e retrieval cross-project governato;
- structured, full-text, vector e hybrid retrieval;
- embedding versionati, consolidation e reflection;
- correction, supersession, revocation, expiry, legal hold, forgetting e deletion saga;
- context-influence receipt e promotion proposal verso C6/C3.

Non sono differite all'MVP capacità semantiche della memoria. MVP e Production riguardano scale, availability, SLO, operational ownership ed E2.

## 3. Invarianti preservati

La memoria non diventa una seconda canonical authority. Non può creare direttamente Canonical Assertion, Authority, Delegation, Approval, Decision, CapabilityLease, ActionCommand o policy.

Claim, Observation, Hypothesis, Model Output, Decision, ExecutionResult e OutcomeAssessment restano distinti. Hidden chain-of-thought, scratchpad, credenziali, token e segreti non sono contenuti ammessi. Training/fine-tuning dalla memoria richiede un workflow distinto.

## 4. Artefatti della candidata

| Artefatto | Ruolo | Stato |
|---|---|---|
| `OCOR_Change_Control_Full_Governed_Agent_Memory_v1.0.md` | decision package completo | user-directed; awaiting governed promotion |
| `OCOR_ADD_v1.3_Candidate.md` | emendamento ADD | candidate |
| `OCOR_LLD_v1.1_Candidate.md` | specifica esecutiva | candidate |
| `governed-memory-item.schema.json` | record chiuso full memory | candidate contract |
| `ocor-governed-memory.openapi.yaml` | admission/search/consolidation/lifecycle/promotion/deletion/context API | candidate contract |
| matrice IRB→ADD→LLD Markdown/JSON | tracciabilità 285/285 | generated and checked |
| assurance results e manifest | evidence machine-readable | verified |
| cinque register snapshot in `governance_candidates/` | aggiornamento atomico RR/RTI/DR/DTI/CAP-ELM | candidate; 11/11 controlli |
| `OCOR_Full_Memory_Atomic_Register_Promotion_Package_v1.0.md` | istruzione di promozione e decision text | ready for authority promotion |

Nessun file sotto `inputs/` è modificato e nessun nuovo ID `DEC-*` è attribuito unilateralmente.

## 5. Disposizione dei finding originari

| Finding | Rettifica | Disposizione |
|---|---|---|
| `IALLD-001` | matrice nominativa 285/285 con priorità, release, ADD allocation, anchor e metodo | `CLOSED_TECHNICALLY` |
| `IALLD-002` | GCS chiuso con gli 11 campi ADD | `CLOSED` |
| `IALLD-003` | OpenAPI/Proto ADD materializzati; Memory OpenAPI aggiunta | `CLOSED` |
| `IALLD-004` | CapabilityLease chiusa, fencing e consumo atomico | `CLOSED` |
| `IALLD-005` | FSM completa con guardie ed effetti | `CLOSED` |
| `IALLD-006` | comando C3 chiuso e idempotency binding atomico | `CLOSED` |
| `IALLD-007` | full governed memory PoC, `ELM-084 CORE/P0/PoC` | `CLOSED_TECHNICALLY / PENDING_REGISTER_PROMOTION` |
| `IALLD-008`–`017` | C1–C8, consistency, event, causal, security, deployment e configuration completati | `CLOSED` |

## 6. Full memory assurance

Il gate controlla un record chiuso con almeno trenta campi obbligatori, otto memory kinds, sette scope, binding vettoriale completo e gli stati legal-hold/deletion. L'API 1.0.0 espone otto resource path e usa gli stessi schemi GCS e MemoryItem manifestati.

La campagna progettata `FGM-01`–`FGM-20` copre admission, cross-run/federated retrieval, vector model upgrade, poisoning, correction, revocation, legal hold, deletion failure, dissent, procedural activation, promotion, non-interference, kill switch, restore e context influence.

`FULLY_SPECIFIED` e `CONDITIONALLY_SPECIFIED` sono stati di design, non evidence runtime. `FR-118/119` restano specified/planned finché `FGM-01`–`FGM-20` non producono evidenze governate.

## 7. Contratti preesistenti

Il Named Query OpenAPI e il Registry Proto standalone restano byte-identici ai blocchi incorporati nell'ADD v1.2; continuano quindi a beneficiare dell'evidenza governata `VAL-ACT-002` e della compilazione `protoc` già registrata per gli stessi byte.

Il nuovo Memory OpenAPI non eredita impropriamente tali evidenze: è un contratto candidato nuovo, sottoposto in questo pacchetto a parse e controlli strutturali. La validazione semantica governata deve essere inclusa nel gate di promozione del nuovo baseline contract.

## 8. Promozione richiesta

Per rendere effettiva la decisione occorre:

1. registrare formalmente il change set secondo l'autorità vigente;
2. assegnare l'identificativo decisionale e promuovere atomicamente i cinque snapshot completi già materializzati in `reports/governance_candidates/`;
3. consolidare ADD v1.3 con `ELM-084 CORE/P0/PoC`;
4. validare semanticamente il Memory OpenAPI e il JSON Schema;
5. rieseguire assurance e review indipendente sul digest consolidato;
6. consolidare e approvare LLD v1.1 con nuovo manifest.

## 9. Evidence fence

La modifica completa il design della memoria, non il runtime. Non vengono dichiarati implementazione, E2, production readiness, HA, performance, security certification o legal compliance. Il runtime deve ancora realizzare i port, gli store, gli indici, gli algoritmi e la campagna FGM prima della conformità.
