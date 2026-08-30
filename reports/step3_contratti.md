# STEP 3 — Valutazione dei due contratti nuovi

## Esito sintetico

`event-subscription-contract:1.0` è sostanzialmente adeguato al livello ADD: espone una subscription logica, non il broker, impone at-least-once e deduplica, limita i filtri a contratti nominati e rende cursor, marking e replay governabili. `action-type-contract:1.0` è strutturalmente valido e tutti i nove rami sono soddisfacibili, ma **non è safety-complete**: accetta un commit canonico senza Human Gate e lascia indeterminate parti della semantica di admission e del relativo error model.

## Coerenza con `ContractDefinition` e `G-CONTRACT`

| Aspetto | Action Type | Event Subscription | Valutazione |
|---|---|---|---|
| Identità/versione/digest | Presenti | Presenti | Conforme |
| Input/output schema | `parameters_schema` e `expected_effect_schema` | `payload_schema` | Conforme come pin; per Action manca il binding semantico dei campi critici del commit |
| Error model | Enum presente | Enum presente | Action incompleto rispetto a `ACT-T31`; Event adeguato alla superficie dichiarata |
| Effect class | Presente | Implicita nella delivery event | Conforme al diverso kind |
| Risk class | Presente | Non definita | Per Event è legittimo demandare il rischio alla subscription/policy; per Action il risk floor non è vincolato al target |
| Policy/approval refs | Entrambi nell'Action | Enforcement descritto nel delivery ma nessun `policy_refs` nel contract | Accettabile per Event solo se il binding runtime trasporta Policy/Authority; questa dipendenza va resa esplicita nel DDD |
| Timeout/retry/idempotenza | Otto timeout, retry e idempotenza obbligatori | Delivery/replay senza retry budget contrattuale | Conforme a `G-CONTRACT` per Action; per Event il retry/backpressure appartiene al binding/consumer group, non al contratto semantico |
| Backend neutrality | Nessun dialect o ID fisico | Cursor opaco; nessun topic, partition offset o broker ID | Conforme |

## `action-type-contract:1.0`

### Difetto safety riprodotto

Il ramo §3.7 `target=CANONICAL_COMMIT` richiede il binding, impone `effect_class=CANONICAL_COMMIT` e vieta `IRREVERSIBLE`, ma non impone un risk floor. Il validator accetta un'istanza `R1_ANALYZE` con `approval.mode=NONE`; si veda il caso fallito in `reports/tests/conformance_results.json`. Ciò contraddice:

- §4.1, che dichiara la stessa FSM, le stesse guardie e lo stesso Human Gate per mutazioni canoniche ed effetti esterni;
- §5.4, che classifica la mutazione interna reversibile almeno `R2_CONTROLLED` e richiede un approvatore umano indipendente;
- §2.5 regola 10, che ammette la mutazione soltanto tramite Decision e Authority coerenti con il `GatePackage`.

Classificazione proposta: `DRF-003`, `CRITICAL`, confidence `HIGH`.

### Admission di Claim ancora indeterminata

`canonical_commit_binding` nomina ownership boundary, aggregate type e classe prodotta; i due booleani per `CanonicalAssertion` attestano soltanto che Claim ed evidence set «sono richiesti». Non specifica:

- quale campo del `parameters_schema` sia la Claim sorgente e come sia legato a `acceptedFromClaim`;
- come l'Evidence set sia individuato e se debba essere non vuoto (`minimum_count` può essere `0`);
- quale operazione `C3` debba invocare (`AdmitClaim` oppure `CommitAggregate`);
- come `expected_revision`, precondition e invarianti siano legati al target aggregate;
- come il `Decision`/`Authority ref` congelato sia referenziato dal command schema.

Un DDD può generare un parameters schema specifico, ma senza una regola di binding normativa dovrebbe inventare la corrispondenza fra quei campi e gli effetti canonici. È un'ambiguità di livello ADD, non un semplice formato wire da demandare al DDD. Classificazione proposta: `DRF-008`, `MAJOR`, confidence `HIGH`.

### `error_codes`

`ACT-T31` distingue rifiuto per precondizione, invariante o revisione attesa e impone la registrazione di un reason code. L'enum del contratto non contiene codici distinti per questi esiti (`PRECONDITION_FAILED`, `INVARIANT_VIOLATION`, `REVISION_CONFLICT` o equivalenti). `STALE_CONTEXT` può coprire parte del revision drift, ma non rende distinguibili gli altri due stati. La remediation di `DRF-008` deve aggiungere codici tipizzati e la mappa deterministica `C3 rejection → error_code → EXECUTION_FAILED/INVALIDATED`.

## `event-subscription-contract:1.0`

Il contratto è coerente con §3.8 e con il port `Subscribe` di `C5`:

- `AT_LEAST_ONCE`, deduplica obbligatoria su `event_id` e ordering per logical key evitano claim exactly-once;
- `filter_contract_id` e `arbitrary_predicates_allowed=false` impediscono query/dialect injection;
- cursor opaco e schema pin-nato impediscono leakage di topic, partizione e offset fisico;
- marking propagation, redazione dichiarata e replay autorizzato coprono le principali posture fail-closed;
- l'enum errori copre deny/authority/schema/release, subscription/cursor e control-plane failure.

Non emerge un finding autonomo sul contratto Event. Il Governed Context Set non è incorporato nel *definition object*, ma §3.8 lo richiede su ogni evento consegnato: è una separazione legittima fra contract definition e delivery envelope, purché il DDD renda il binding verificabile. Le incoerenze di naming e copertura dei record runtime sono trattate separatamente in `step4_contesto_marking.md`.

## Remediation esatta richiesta per Action

1. Nel `then` di `target=CANONICAL_COMMIT`, imporre `risk_class ∈ {R2_CONTROLLED,R3_HIGH_IMPACT}`; per `R2` richiedere `HUMAN_GATE` o `DUAL_CONTROL`, quorum ≥1 e almeno un ruolo; per `R3` conservare il dual control esistente.
2. Sostituire i booleani dichiarativi con un binding tipizzato che nomini `operation`, `source_claim_ref_field`, `evidence_set_field`, `expected_revision_field`, `decision_ref_field`, `authority_ref_field` e la regola di produzione di `acceptedFromClaim`/`acceptedByDecision`.
3. Imporre `evidence_requirements.minimum_count ≥ 1` quando `requires_evidence_set=true`, oppure definire esplicitamente la semantica di un set vuoto se realmente ammesso.
4. Estendere `error_codes` e §4.1.2 con una mappa univoca dei rifiuti di `C3`.

Queste correzioni richiedono change control sulla bozza `DRAFT-B` e sul contratto introdotto da `DRAFT-G`; non producono evidenza e non cambiano `E1=0`/`E2=0`.
