# STEP 10 — Regression audit degli invarianti hard

## Esito sintetico

La review v1.0 dichiara in §4 una sintesi di **38 `PASS`, 8 `PASS WITH CONDITION`, 2 `FAIL`**. Il conteggio verificabile delle righe della stessa sezione è invece **46 `PASS`, 8 `PASS WITH CONDITION`, 2 `FAIL`**, per un totale di 56 invarianti. La differenza di otto coincide esattamente con gli otto `PASS` di §4.1 «Separazione epistemica», omessi dal totale riepilogativo ma presenti come righe della tabella.

Per non selezionare arbitrariamente quali righe ignorare, questo audit ricontrolla:

- le **38** righe `PASS` di §4.2–§4.6, che riconciliano il numero prescritto dal prompt;
- separatamente, gli **8** ulteriori `PASS` effettivi di §4.1;
- quindi tutte le **46** righe che la sorgente marca materialmente `PASS`.

Esito riconciliato dopo il controllo cross-register dello STEP 11: **44 `PASS`, 1 `PASS WITH CONDITION`, 1 `FAIL`, 0 `NOT EVALUABLE`**. La sola regressione di stato è circoscritta alla sostituibilità della reference triad: la nuova riga `BA-01` rende esplicito un fallback che fa decadere l'atomicità local-state+outbox e richiede la riscrittura di §2.3, ma §2.6 lo presenta comunque come sostituzione di adapter. È lo stesso difetto già registrato in FASE 1 come `DRF-009`; qui non viene duplicato. Il `FAIL` su `ELM-070`/`FR-095` (`DRF-012`) non è una regressione: la contraddizione era già presente nella v1.0 ed era stata falsamente classificata `PASS` perché il controllo precedente non aveva riconciliato lo scope fence con `DEC-103`, `DEC-196` e il Requirement Register.

Lo stato probatorio resta invariato: `E1=0`, `E2=0`, zero requisiti `Verified`. I risultati del harness attestano soltanto proprietà documentali, sintattiche o strutturali.

## Metodo e sorgenti

| Elemento | Controllo |
|---|---|
| Review di origine | `inputs/supporting/prior/OCOR_ADD_Critical_Review_v1.0.md`, letta integralmente fino a EOF; invarianti estratti da §4, righe 121–200 |
| ADD v1.0 | `inputs/supporting/prior/OCOR_Architectural_Design_Document_v1.0.md`; SHA-256 emesso dal harness: `1e0fe999d66b0133638293d9568f79fb861636f81bc939e170e7d6fa392d8fed` |
| ADD v1.1 | `inputs/normative/OCOR_Architectural_Design_Document_v1.1.md`; SHA-256 del referto FASE 1: `3e7532c7101e80c74b511cedc56a0563ca0938a3fe259911a91245cb19dedc7f` |
| Referto v1.1 | `reports/verify_report.json`, `reports/step2_conformance.md`, `reports/step4_contesto_marking.md`, `reports/step5_fsm.md`, `reports/step6_redteam.md` |
| Semantica di “regressione” | Un invariante realmente soddisfatto dalla v1.0 e non più pienamente soddisfatto dalla v1.1. Una rivalutazione di un gap già presente non viene falsamente classificata come regressione testuale |

I locator `L…` nelle tabelle seguenti sono numeri di riga dell'ADD v1.1 corrente e accompagnano sempre il locator di sezione.

## Riconciliazione del conteggio della review v1.0

| Gruppo della review v1.0 | `PASS` effettivi | Inclusi nel “38” riepilogativo | Nota |
|---|---:|---:|---|
| §4.1 Separazione epistemica | 8 | 0 | Le otto righe sono `PASS`, ma non entrano nel totale dichiarato |
| §4.2 Consistenza distribuita | 10 | 10 | Il `FAIL` «Single writer» non è incluso |
| §4.3 Adapter isolation | 4 | 4 | Il `FAIL` sul vocabolario delle capability non è incluso |
| §4.4 Governed agents | 10 | 10 | Due righe erano `PASS WITH CONDITION` e non sono incluse |
| §4.5 Causal safety | 8 | 8 | La riga sui reason code era `PASS WITH CONDITION` |
| §4.6 Action safety | 6 | 6 | Quattro righe erano `PASS WITH CONDITION` |
| **Totale** | **46** | **38** | Errore aritmetico/documentale della sintesi v1.0, non proprietà dell'ADD |

## Confronto dei due harness

Il comando sul documento v1.0 è stato eseguito **una sola volta** con `.venv/bin/python3`. È terminato con exit code 1 per i due `FAIL` sotto riportati e non è stato ripetuto.

| Controllo | ADD v1.0 | ADD v1.1 | Valutazione comparativa |
|---|---|---|---|
| Integrità sorgenti nel harness | `NOT_EXECUTED`: `SHA256SUMS` assente nella directory `prior/` risolta dal harness | `PASS`: 8 file, digest coincidenti | Il v1.0 non è un mismatch: il controllo non è stato eseguito. Non è dichiarato superato |
| JSON Schema | `PASS`: 3 schemi Draft 2020-12 | `PASS`: 5 schemi Draft 2020-12 | Due nuovi schemi; la sola meta-validazione non dimostra la semantica |
| OpenAPI `$ref` | `PASS`: 23/23 | `PASS`: 26/26 | Nessun `$ref` irrisolto in entrambi |
| Validazione semantica OpenAPI con validator ufficiale | `NOT_EXECUTED` | `NOT_EXECUTED` | Non dichiarata superata in nessuna versione |
| Protobuf | `PASS` | `PASS` | Compilazione documentale in entrambi |
| Turtle/RDF | `PASS`: 17 triple | `PASS`: 17 triple | Nessuna regressione di parsing |
| Classe RV-01, campi richiesti ma non dichiarati | `PASS` | `PASS` | Nessun ramo rilevato dalla sola euristica strutturale |
| Rami condizionali informativi | Ingestion 3; MCP 4 | Ingestion 4; MCP 11; Action 9; Event 0 | L'ampliamento è coperto dai conformance test FASE 1; `action-type-contract` ha un `FAIL` semantico, non un ramo insoddisfacibile |
| FSM diagramma/tabella | `FAIL`: tre stati solo diagramma, `CANCELLED` solo tabella | `PASS` meccanico: 29 stati in corrispondenza | Miglioramento del set di stati; il confronto non prova la bijezione degli archi (`DRF-006`) |
| Famiglia `ACT-T*` | `PASS`: `T01`–`T23` più varianti | `PASS`: `T01`–`T31` più varianti | Famiglia estesa e contigua |
| Tracciabilità §7 | `FAIL`: gap su `BR`, `FR`, `NFR`, `ARC` | `PASS`: `BR` 18/18, `FR` 174/174, `NFR` 93/93, `ARC` 23/23; `CAP` 25/26 per fence dichiarato | Chiusura meccanica della copertura; non prova correttezza semantica dei mapping |
| Universo normativo | `PASS`: 693 | `PASS`: 693 | Invariato |
| Rimandi di sezione | `PASS` | `PASS`: 44 rimandi, nessuno irrisolto | Nessuna regressione rilevata |
| Evidence fence | `PASS` | `PASS` | `E1`/`E2` invariati; nessun incremento probatorio |
| Nessun `DEC-197` assegnato | `PASS` | `PASS` | Le occorrenze v1.1 sono negative o nomi di file |
| **Sintesi harness** | **10 `PASS`, 2 `FAIL`, 2 `NOT_EXECUTED`** | **13 `PASS`, 0 `FAIL`, 1 `NOT_EXECUTED`** | Miglioramento strutturale, con le limitazioni sopra |

## Otto `PASS` di §4.1 omessi dalla sintesi v1.0

| # | Invariante già `PASS` | Esito v1.1 | Evidenza precisa nella v1.1 | Regressione? |
|---:|---|---|---|---|
| 1 | `Observation/Claim ≠ Canonical State ≠ Projection ≠ Prediction ≠ Intervention ≠ Action ≠ Outcome` | `PASS` | §1.3, L78–L99; divieto runtime §3.2, L749; nessuna promozione implicita §3.6, L1927 | No |
| 2 | `Receipt ≠ ExecutionResult` | `PASS` | §1.3, L89; `ACT-T15`, L2605; chiarimento ACK, L2630 | No |
| 3 | `ExecutionResult ≠ OutcomeAssessment` | `PASS` | §1.3, L89–L90; record distinti §4.1, L2518; semantica separata L2630 | No |
| 4 | `Recommendation ≠ Decision` | `PASS` | §1.3, L87; §2.5 regola 6, L269; §4.2, L2755 | No |
| 5 | `Approval ≠ Decision` | `PASS` | Record distinti §4.1, L2518; `ACT-T10`/`T11`, L2600–L2601; §5.4, L3043 | No |
| 6 | `Decision ≠ ActionIntent` | `PASS` | §4.1, L2518; `ACT-T10` registra la Decision e `ACT-T11` deriva l'intento, L2600–L2601 | No |
| 7 | `ActionIntent ≠ ActionCommand` | `PASS` | §4.1, L2518; `ACT-T11` registra l'intento «senza command», `ACT-T12` registra il command, L2601–L2602 | No |
| 8 | `Intervention ≠ Action` | `PASS` | §1.3, L86; formalizzazione `do(X)`, §4.2 L2698; divieto di Action Command L2755 | No |

Queste otto righe spiegano integralmente lo scarto `46 − 38`. Nessuna di esse regredisce.

## I 38 `PASS` riconciliati col numero prescritto

### Consistenza distribuita — 10/10

| # | Invariante già `PASS` | Esito v1.1 | Evidenza precisa nella v1.1 | Regressione? |
|---:|---|---|---|---|
| 1 | Transazione locale State Delta + Outbox | `PASS` | §2.3, L224–L232; §6.2 punti 1–2, L3139–L3140; `BA-01` mantiene la proprietà come requisito non verificato, L285 | No; target invariato, conformance backend ancora assente correttamente |
| 2 | Assenza di 2PC/XA | `PASS` | §1.3, L99; `C3`, L202; §6.2, L3137 | No |
| 3 | Assenza di ACID globale | `PASS` | §1.3, L99; §4.1, L2518; §6.2, L3137 | No |
| 4 | Assenza di triple-write sincrono | `PASS` | §1.3, L99; §6.2, L3137 | No |
| 5 | Assenza di multi-master | `PASS` | §1.3, L99; §6.2, L3137 e L3170 | No |
| 6 | At-least-once delivery | `PASS` | `C5`, L204; §2.5 regola 4, L267; §3.2 runtime L747–L748; §6.2 punto 3, L3141 | No |
| 7 | Idempotency e fencing | `PASS` | `C3`/`C5`, L202–L204; §2.5 regola 4, L267; `G-DISPATCH`, L2585; §6.2 L3139 e `MutationFence` L3152–L3167 | No |
| 8 | Ordering limitato alla partition key | `PASS` | `C5`, L204; §3.2, L748; event contract §3.8, L2392–L2395 | No |
| 9 | Watermark e facts atomicamente visibili | `PASS` | §2.3, L231; §2.5 regola 3, L266; §6.2 punto 5, L3143; assunzione esplicitamente non verificata `BA-02`, L286 | No |
| 10 | Nessun reverse-write dalle proiezioni | `PASS` | §2.3, L232; §6.2 vieta la promozione automatica di Projection Result, L3145 | No |

### Adapter isolation — 3 `PASS`, 1 `PASS WITH CONDITION`

| # | Invariante già `PASS` | Esito v1.1 | Evidenza precisa nella v1.1 | Regressione? |
|---:|---|---|---|---|
| 11 | Triade come reference adapter sostituibili | `PASS WITH CONDITION` | Ruoli pubblici e sostituibilità restano in §2.4, L234–L260, e nel criterio §7.2 L3297. Tuttavia `BA-01` propone un fallback con due commit logici e finestra d'incoerenza, poi dichiara che l'atomicità decade e §2.3 va riscritta, L285; §2.6 afferma invece che il fallback rende la sostituzione adapter-only, L294 | **Sì — regressione di coerenza introdotta in v1.1; `MAJOR`, confidence `HIGH`, già `DRF-009`** |
| 12 | Nessun dialect nei contratti pubblici | `PASS` | Trust boundary §1.4 L110; regola generale §3 L300; `ContractDefinition` L358; nuovo Event contract L2346 | No; i due contratti nuovi sono neutrali |
| 13 | Nessun backend ID o schema fisico nei contratti | `PASS` | §1.4 L110; §3 L300; `Namespace` L350; Event contract usa subscription/cursor opachi L2346 | No |
| 14 | Dialect confinati alle implementazioni private degli adapter | `PASS` | Capability `forbidden_by_design`, §2.4 L246–L260; adapter scenario §4.2 L2668 | No |

### Governed agents — 10/10

| # | Invariante già `PASS` | Esito v1.1 | Evidenza precisa nella v1.1 | Regressione? |
|---:|---|---|---|---|
| 15 | Agente come Principal distinto | `PASS` | §1.2 L74; §4.3.1 punto 1, L2841; §5.1 Agent identity L2867 | No |
| 16 | Assenza di credenziali datastore | `PASS` | §4.3 L2763; §4.3.1 punto 1 L2841; §5.2 punto 6 L2943 | No |
| 17 | Capability allow-list | `PASS` | `TB-CXT-03`, L107; §4.3.1 punto 4 L2844; `G-AUTHORITY` L2581 | No |
| 18 | Delegation bounded | `PASS` | `DelegationGrant`, §5.2 L2893–L2918; vincoli di non-ampliamento e rivalidazione L2938–L2942 | No |
| 19 | Prompt, Goal, Message, Memory e tool output tainted | `PASS` | §2.5 regola 7 L270; §4.3.1 punto 3 L2843; §5.2 L2893 | No |
| 20 | Nessuna Authority derivata dal prompt | `PASS` | §1.3 L87; §4.3.1 L2843; §5.2 L2893; invocation rule §3.5 L1867 | No |
| 21 | Handoff tipizzati e mediati | `PASS` | §4.3 L2763; ruoli/output tipizzati L2778–L2785; `HandoffEnvelope` L2787–L2826 | No. Le incoerenze del Governed Context Set sono `DRF-001`, ma non eliminano mediazione o tipizzazione |
| 22 | Challenger indipendente | `PASS` | Ruolo Challenger L2784; snapshot e budget indipendenti §4.3.1 L2847 | No |
| 23 | Dissent non sopprimibile | `PASS` | Ruoli Challenger/Coordinator L2784–L2785; §4.3.1 L2847 | No |
| 24 | Critical Dissent bloccante per High-Impact | `PASS` | §4.3 L2837; la Decision Proposal conserva il dissent, L2850 | No. Il diverso bypass di risk floor del contratto Action resta `DRF-003` |

### Causal safety — 8/8

| # | Invariante già `PASS` | Esito v1.1 | Evidenza precisa nella v1.1 | Regressione? |
|---:|---|---|---|---|
| 25 | Identify-or-abstain | `PASS` | Diagramma §4.2 L2684–L2696; outcome tipizzato L2700–L2726 | No |
| 26 | Validity envelope | `PASS` | Secondo gate del diagramma L2689–L2691; reason code e failed conditions L2732–L2743 | No |
| 27 | `ABSTAIN` obbligatorio se non identificabile | `PASS` | Diagramma L2687–L2690; `NOT_IDENTIFIED` L2730 | No |
| 28 | Nessun effect estimate utilizzabile dentro `ABSTAIN` | `PASS` | Varianti disgiunte L2700–L2726; divieto ora strutturale L2745 | No; la v1.1 rafforza l'invariante |
| 29 | Isolamento copy-on-write | `PASS` | Baseline read-only e overlay isolato, §4.2 L2682; port adapter L2657–L2668 | No |
| 30 | Nessun commit su `main` dal runtime causale | `PASS` | `C7` L206; nessuna capability `canonical.main.write` L2753; merge diretto negato L2755 | No; il percorso `C6→C3` non attribuisce write authority a `C7` |
| 31 | `do(X) ≠ Action` | `PASS` | Formalizzazione SCM e divieto esplicito §4.2 L2698 | No |
| 32 | `ELM-070` correttamente differito | `FAIL` | §4.2 L2757 e §1.5 L142 lo differiscono, ma `DEC-103`/`FR-095` impongono AAP `P0/PoC` e `DEC-196` congela entrambi i vincoli | No regressione: source limitation già presente in v1.0; `DRF-012` |

### Action safety — 6/6

| # | Invariante già `PASS` | Esito v1.1 | Evidenza precisa nella v1.1 | Regressione? |
|---:|---|---|---|---|
| 33 | Pre-admission failure | `PASS` | §4.1 L2495: errore fail-closed e nessuna `ActionInstance` | No |
| 34 | Famiglia `ACT-T01`–`ACT-T23` | `PASS` | Tabella §4.1.2 L2589–L2624; harness v1.1: famiglia estesa `T01`–`T31` contigua | No; estensione, non rottura |
| 35 | Presenza di `ACT-T21a`, `ACT-T21b`, `ACT-T21c` | `PASS` | §4.1.2 L2612–L2614 | No |
| 36 | ACK distinto dal successo | `PASS` | `ACT-T15` L2605; chiarimento L2630 | No |
| 37 | Nessun retry cieco | `PASS` | `ACT-T19` richiede `retry_safe=true`, stessa key, fencing/stop epoch correnti, audit e budget, L2609; timeout non idempotente non abilita retry L2630 | No. La mancata rivalidazione completa di `G-FRESHNESS`/`G-DISPATCH` è il distinto `DRF-004`, già collegato in v1.0 alla riga «Tutte le guardie», che era `PASS WITH CONDITION` |
| 38 | Compensation come nuova azione governata | `PASS` | `ACT-T21` crea nuova command con autorizzazione L2611; semantica esplicita L2632 | No |

## Regressione sopravvissuta

### `DRF-009` — sostituibilità della reference triad solo condizionata

| Attributo | Valutazione |
|---|---|
| Severity | `MAJOR` |
| Confidence | `HIGH` |
| Origine | `NEW_IN_V1.1` e, rispetto al set degli invarianti già `PASS`, regressione di stato |
| Locator | ADD v1.1 §2.4 L234–L260; §2.6 `BA-01` L285; chiusura §2.6 L294 |
| Evidenza | Il fallback `BA-01` sostituisce il commit atomico state+outbox con due commit logici e ammette una finestra d'incoerenza; la stessa riga afferma che l'atomicità decade e §2.3 deve essere riscritta. La frase L294 dichiara però che ogni fallback rende la sostituzione una mera operazione di adapter |
| Impatto | Il DDD non può trattare il fallback come sostituzione trasparente: cambiano crash windows, rischio di perdita/duplicazione dell'evento e invariante distribuito cross-container |
| Remediation esatta | Marcare il fallback `BA-01` come `ARCHITECTURAL_ALTERNATIVE_REQUIRING_CHANGE_CONTROL`; rimuovere il claim adapter-only; imporre nuova failure analysis, crash-window suite e revisione di §2.3/§6.2 prima dell'adozione |

Il contratto pubblico resta backend-neutral e la tecnologia resta correttamente `Candidate Implementation`; la regressione riguarda la coerenza della strategia di sostituzione, non una conformance backend osservata.

## Finding FASE 1 che non sono regressioni di un precedente `PASS`

| Finding FASE 1 | Perché non è classificato qui come regressione di un `PASS` |
|---|---|
| `DRF-001`, `DRF-002` — Governed Context Set/origine Principal | Difetti del materiale nuovo §3.0 e di mapping cross-contract; gli invarianti su Principal agente e handoff mediato restano letteralmente soddisfatti |
| `DRF-003` — canonical commit `R1` senza Approval | Incide sul gate umano; la riga v1.0 «Human Gate e Dual Control» era già `PASS WITH CONDITION`, non fa parte dei 46 `PASS` |
| `DRF-004` — mancata rivalidazione di freshness all'emissione | Incide sulla completezza delle guardie; la riga v1.0 «Tutte le guardie» era `PASS WITH CONDITION`. `ACT-T19` resta non cieco nel senso stretto dell'invariante qui auditato |
| `DRF-005` — algebra marking incoerente | Il marking conservativo non era una riga autonoma `PASS` del §4 v1.0; il difetto è nuovo e resta valido |
| `DRF-006` — bijezione FSM edge-level falsa | La FSM v1.0 era già `FAIL` nel §4/harness; il `PASS` v1.1 del harness riguarda soltanto l'insieme degli stati |
| `DRF-007` — adjudication/footprint degli stati indeterminati | Le righe v1.0 su `EXECUTION_UNKNOWN` e `COMPENSATION_UNKNOWN` erano già `PASS WITH CONDITION` |
| `DRF-008` — binding Claim/Evidence/Decision | Il divieto di promozione automatica era già `PASS WITH CONDITION`, non `PASS` |
| `DRF-010`, `DRF-011` | Change-control count e dipendenze fra bozze non appartengono agli invarianti hard già `PASS` |

## Conclusione

Sul sottoinsieme numerico prescritto di 38 invarianti, dopo la riconciliazione STEP 11: **36 `PASS`, 1 `PASS WITH CONDITION`, 1 `FAIL`**. Includendo gli otto `PASS` di §4.1 materialmente presenti ma omessi dalla sintesi v1.0: **44 `PASS`, 1 `PASS WITH CONDITION`, 1 `FAIL`**.

Il `FAIL` `DRF-012` corregge un falso positivo della review v1.0 e non è una regressione; la sola regressione di stato introdotta dalla v1.1 è `DRF-009`. Non emergono `NOT EVALUABLE` fra i 38 invarianti. Gli esiti migliori del harness su FSM e tracciabilità sono miglioramenti documentali/strutturali, non evidenza di implementazione e non modificano `E1=0` o `E2=0`.
