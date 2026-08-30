# OCOR ADD v1.2 Candidate — Implementation Request Gate Audit

## Control

| Campo | Valore |
|---|---|
| Data | 30 agosto 2026, Europe/Rome |
| Oggetto documentale | `reports/OCOR_Architectural_Design_Document_v1.2_Candidate.md` |
| SHA-256 oggetto | `d2a01b165785750ec62ef110dae9289cc3ef528f8e89748b5746b45c44e73a18` |
| Richiesta valutata | Implementazione C1–C8, simulatori, BA-01–BA-08, EV-001–EV-035 e promozione della candidata |
| Natura del controllo | Audit di ammissibilità ed esecuzione dei controlli documentali già autorizzati |
| Evidence fence | `E1=0`, `E2=0`, zero requisiti `Verified`; nessun `EV-*` promosso |
| Modifiche protette | Nessuna modifica in `inputs/`, `prompts/` o `docs/detailed_design/` |

Il repository è, per `AGENTS.md` righe 3–5, un contesto di review e non un
progetto software. La sola directory scrivibile è `reports/` (`AGENTS.md` riga
15 e riga 42). La richiesta di creare `ocor-core/`, `src/`, `schemas/`,
`simulators/`, `tests/` e documenti ratificati in `docs/` non è quindi
ammissibile in questo workspace. Questo referto registra il conflitto; non lo
aggira spostando surrettiziamente un prodotto software sotto `reports/`.

## Execution Result

| Controllo | Risultato | Dettaglio |
|---|---|---|
| Integrità sorgenti normative | `PASS` | 8/8 digest verificati con `sha256sum -c inputs/normative/SHA256SUMS` |
| Harness normativo v1.1 | `PASS WITH NOT_EXECUTED` | 13 `PASS`, 0 `FAIL`; validator semantico OpenAPI 3.1 `NOT_EXECUTED` |
| Integrità package v1.2 | `PASS` | 22/22 digest verificati con `sha256sum -c reports/OCOR_ADD_v1.2_SHA256SUMS` |
| Harness meccanico v1.2 | `PASS WITH NOT_EXECUTED` | 12 `PASS`, 0 `FAIL`, 2 `NOT_EXECUTED`; l'integrità è stata verificata separatamente dal manifest del package |
| Meta-validazione JSON Schema v1.2 | `PASS` | 5 schemi Draft 2020-12 validi |
| Risoluzione OpenAPI v1.2 | `PASS` | OpenAPI 3.1.0/1.2.0; 6 path, 25 component schema, 26 `$ref`, zero non risolti |
| Validator semantico OpenAPI 3.1 ufficiale | `NOT_EXECUTED` | Tool non disponibile nell'ambiente; nessuna installazione o rete tentata |
| Protobuf | `PASS` | Compilazione locale riuscita |
| Turtle/RDF | `PASS` | Parsing locale riuscito, 17 triple |
| RV-01 / conditional-required | `PASS` sulla candidata | Nessun required condizionale non dichiarato |
| Conformance contratti v1.1 | `FAIL` atteso e riprodotto | 97/98; `action-type-contract:1.0` accetta `CANONICAL_COMMIT` R1 senza Human Gate |
| Conformance contratti v1.2 | `PASS` | 105/105 casi positivi e negativi; il regression case precedente è rifiutato |
| Controlli semantici v1.2 | `PASS` | 29/29; authority binding, emission fence, canonical admission, marking, FSM, reference ed evidence fence |
| Gate che legge `inputs/supporting/prior/` | `NOT_EXECUTED` | Escluso deliberatamente da questa esecuzione indipendente |
| `pytest -v --cov=src tests/` | `NOT_EXECUTED` | `src/`, `tests/` e `ocor-core/` sono assenti; non esiste un'implementazione sulla quale eseguire il comando |
| BA-01–BA-08 runtime campaign | `NOT_EXECUTED` | Backend, adapter e simulatori eseguibili assenti |
| EV-001–EV-035 runtime campaign | `NOT_EXECUTED` | La candidata §7.2 dichiara tutti gli `EV-*` `NOT RUN — E1=0/E2=0` |

I `PASS` sopra qualificano esclusivamente i documenti, i contratti incorporati e
le funzioni semantiche di test isolate già presenti in `reports/tests/`. Non
dimostrano che C1–C8 esistano o che una proprietà runtime sia soddisfatta.

## Findings Register

| ID | Severity | Confidence | Locator | Related IDs | Finding | Evidence | Impact | Exact remediation | Disposition |
|---|---|---|---|---|---|---|---|---|---|
| `IRG-001` | `BLOCKER` | `HIGH` | `AGENTS.md` righe 3–5, 15, 42–43 | C1–C8 | La delivery software richiesta è fuori dal perimetro scrivibile e dalla natura del repository. | `src/`, `tests/` e `ocor-core/` risultano assenti; il repository autorizza soltanto output di audit in `reports/`. | Creare il layout richiesto violerebbe il controllo di configurazione della review. | Provisionare un repository software separato con baseline v1.2 approvata, policy di scrittura e toolchain esplicitamente autorizzate; mantenere questo repository come input immutabile di review. | `VALID` |
| `IRG-002` | `BLOCKER` | `HIGH` | ADD v1.2 Candidate §1.1, righe 14–19 e 30–35; §7.2 | `E1`, `E2`, `EV-*` | La candidata non è una specifica approvata né evidenza di implementazione. | Stato `PROPOSED — AWAITING CHANGE CONTROL`, stato tecnico `Design Target`, zero `Verified`; tutte le righe §7.2 sono `NOT RUN — E1=0/E2=0`. | Dichiarare 100% pass o produrre un Evidence Report di sistema sarebbe una promozione probatoria non supportata. | Ottenere change control dall'authority competente; poi eseguire gli `EV-*` contro artefatti buildati e conservare raw output, trace, receipt e manifest firmati. | `VALID` |
| `IRG-003` | `BLOCKER` | `HIGH` | ADD v1.2 Candidate §2.6 `BA-01`, righe 289 e 298 | C3, `RSK-013`, `RSK-019` | La base transazionale di C3 ha un `NO-GO` esplicito non risolvibile dal revisore. | `BA-01` richiede failure analysis, una sola alternativa e approvazione dell'authority; il fallback cambia l'invariante di atomicità. | Scegliere autonomamente storage o dual-commit produrrebbe una decisione architetturale non autorizzata. | L'Architecture Review Authority deve selezionare e approvare una sola alternativa dopo i crash-window test; solo allora il DDD può fissare C3. | `VALID` |
| `IRG-004` | `BLOCKER` | `HIGH` | `AGENTS.md` righe 16–21; ADD v1.2 Candidate §1.1, righe 16–18 e 33–35 | `DRAFT-A`–`DRAFT-I` | La promozione automatica delle bozze e l'approvazione della baseline sono vietate e prive dell'authority indicata dal documento. | La candidata dice espressamente che l'approval non è registrata e che le bozze restano non approvate. | Un agente di review non può creare authority, approvare decisioni o chiudere issue/rischi. | Presentare il Change-Control Package agli owner indicati; registrare separatamente gli esiti autorizzati senza riscrivere retroattivamente gli artefatti di review. | `VALID` |
| `IRG-005` | `MAJOR` | `HIGH` | ADD v1.2 Candidate §7.2 e §8 `AM-23` | `EV-001`–`EV-035` | Esistono definizioni normative degli `EV-*`, ma non una suite runtime eseguibile né un SUT in questo repository. | Gli ID sono `Planned` nei registri; §7.2 li alloca e li marca `NOT RUN`; non esistono `src/` o `tests/`. | Una suite documentale/schema-level non può essere rinominata acceptance evidence C1–C8. | Nel repository software autorizzato creare mapping test-ID→requisito→oracle→fixture→raw evidence per tutti i 35 ID e impedire il `PASS` quando il SUT non è buildato. | `VALID` |
| `IRG-006` | `MAJOR` | `HIGH` | ADD v1.2 Candidate §4.1.1, diagramma e tabella FSM | `ACT-T01`–`ACT-T31` | La frase “tutte le 31 transizioni” sottoconta la superficie reale. | Il confronto corrente diagramma↔tabella rileva 44 tuple, perché diversi numeri hanno varianti `a/b/c`; la sola contiguità 01–31 non dà transition coverage. | Un harness fermo a 31 casi può omettere recovery, unknown e compensation branch. | Enumerare e coprire tutte le 44 tuple `(transition_id, source, destination)`, inclusi ogni guard outcome positivo e negativo, non soltanto i 31 numeri base. | `VALID` |
| `IRG-007` | `MAJOR` | `HIGH` | ADD v1.2 Candidate §2.6 `BA-08`; §7.2 Security & Governance | `BA-08`, `NFR-047` | La richiesta introduce una soglia `T ≤ 5 s` diversa dal target documentato `≤10 s`. | `BA-08` e §7.2 fissano il target candidato a `≤10 s`; nessun change control autorizza `5 s`. | Usare `5 s` come criterio normativo modificherebbe l'acceptance baseline; usarlo senza qualifica produrrebbe un falso failure o un overclaim. | Mantenere `≤10 s` come criterio candidato finché l'authority non approva una soglia diversa; un test a `5 s` può essere solo esplorativo e non probatorio. | `VALID` |
| `IRG-008` | `MAJOR` | `HIGH` | Harness corrente; requisito di completion “100% passed” | OpenAPI 3.1 | Non è disponibile un validator semantico OpenAPI 3.1 ufficiale. | Il verifier lo marca esplicitamente `NOT_EXECUTED`; l'assenza non è stata colmata tramite rete o installazione, entrambe vietate. | Non è lecito concludere “all schemas pass strict OpenAPI 3.1 validation”. | Preinstallare e pin-nare offline il validator approvato nel futuro ambiente software, registrandone versione e digest; rieseguire e conservare l'output raw. | `SOURCE_LIMITATION` |

## Correzioni documentali confermate

Il regression test v1.1 ha riprodotto il difetto per cui un
`CANONICAL_COMMIT` a rischio R1 senza Human Gate veniva accettato. Lo stesso
caso è correttamente rifiutato da `action-type-contract:1.1` nella candidata.
Sono inoltre verdi, a livello documentale/schema-level:

- la meta-validazione dei cinque JSON Schema Draft 2020-12;
- la risoluzione locale di tutti i `$ref` OpenAPI;
- i casi positivi e negativi dei rami condizionali, 105/105;
- la compilazione Protobuf e il parsing Turtle;
- i controlli isolati fail-closed su principal binding, `EMISSION-FENCE`,
  canonical admission, marking algebra ed evidence fence;
- la corrispondenza esatta delle 44 tuple FSM fra diagramma e tabella.

Questi risultati dichiarano corretto il rimedio documentale osservato. Non
convertono `Candidate Implementation` in implementazione e non incrementano lo
stato probatorio.

## NOT_EXECUTED Register

1. Validazione semantica con validator OpenAPI 3.1 ufficiale: tool assente.
2. Gate che apre `inputs/supporting/prior/`: escluso da questa esecuzione.
3. Build, lint e coverage del core: SUT e directory richieste assenti.
4. BA-01–BA-08: backend e simulatori assenti.
5. EV-001–EV-035: SUT, fixture, oracle ed evidence sink runtime assenti.
6. Ratifica e change control: richiedono authority umana/organizzativa esterna
   al ruolo di revisore.

## Verdict

`NO-GO` per l'implementazione richiesta in questo repository e `NOT_EXECUTED`
per BA/EV runtime. Il candidate v1.2 supera i controlli documentali eseguibili
qui, con le limitazioni dichiarate, ma resta `PROPOSED — AWAITING CHANGE
CONTROL`, `E1=0`, `E2=0` e zero requisiti `Verified`.

Non sono stati creati identificativi decisionali, non sono state approvate
bozze, non sono stati chiusi `OI-*`, `ASM-*` o `RSK-*`, e nessuna capability
differita è stata attivata.
