# OCOR ADD v1.1 — FASE 1 Delta Review in cieco

## 1. Control

| Campo | Valore |
|---|---|
| Branch | `fase-1` |
| Data | 2026-08-30, Europe/Rome |
| Scope | Sola superficie di delta v1.1 dichiarata da `DELTA_MANIFEST.json`; nessun confronto con v1.0 o review precedente |
| Oggetto | `inputs/normative/OCOR_Architectural_Design_Document_v1.1.md` |
| Digest ADD | `3e7532c7101e80c74b511cedc56a0563ca0938a3fe259911a91245cb19dedc7f` — coincide col valore atteso |
| Altre sorgenti lette integralmente | `OCOR_DEC_197_plus_Draft_v0.1.md`; `DELTA_MANIFEST.json` |
| Registri | Consultati solo per gli ID necessari; nessuna lettura lineare |
| Materiale prior | Non aperto, non ricostruito e non cercato |
| Standard/criteri | ISO/IEC/IEEE 42010, IEEE 1016, ISO/IEC/IEEE 12207, C4, formal systems, secure-by-design, fail-safe, least privilege |
| Evidence status | Invariato: `E1=0`, `E2=0`, zero requisiti `Verified`; capability `Design Target`; tecnologie `Candidate Implementation` |

### Controlli tool-backed

`sha256sum -c inputs/normative/SHA256SUMS`: 8/8 digest `PASS`.

`./.venv/bin/python3 scripts/verify.py --json`: 13 `PASS`, 0 `FAIL`, 1 `NOT_EXECUTED`. Sono passati: integrità; meta-validazione di cinque JSON Schema; risoluzione `$ref` OpenAPI; compilazione Protobuf; parsing Turtle; scan `RV-01`; set di stati FSM e contiguità `ACT-T`; tracciabilità; universo; rimandi; evidence fence; assenza di assegnazione `DEC-197`.

`NOT_EXECUTED`: **validazione semantica OpenAPI 3.1 con validator ufficiale**. Questo controllo non è dichiarato superato.

### Conformance test indipendenti

Suite: `reports/tests/test_schema_conformance.py`; risultato: `reports/tests/conformance_results.json`.

| Schema | Rami `if/then` | Positivi | Negativi | Insoddisfacibili | Esito |
|---|---:|---:|---:|---:|---|
| `signed-canonical-ir:1.0` | 0 | 1 | 1 | 0 | `PASS` strutturale |
| `canonical-ingestion-envelope:1.1` | 4 | 11 | 9 | 0 | `PASS` |
| `mcp-tool-contract:1.1` | 11 | 11 | 13 | 0 | `PASS` sui vincoli codificati |
| `action-type-contract:1.0` | 9 | 9 | 11 | 0 | `FAIL`: canonical commit `R1` senza Approval accettato |
| `event-subscription-contract:1.0` | 0 | 1 | 4 | 0 | `PASS` strutturale |
| OpenAPI 1.1.0 | 3 | 15 | 11 | 0 | Component schema `PASS`; validator ufficiale `NOT_EXECUTED` |

Totale: 98 casi; 97 conformi all'oracolo, 1 fallito. Sono coperte anche le alternative `oneOf`. Nessun test costituisce evidenza di implementazione o incrementa `E1`/`E2`.

### Finalizzazione repository

`git add -A && git commit -m "review: fase 1 — delta in cieco"`: `NOT_EXECUTED` come operazione completa. Il primo e unico tentativo è fallito prima dello staging con `fatal: Unable to create '.git/index.lock': Read-only file system`. Il comando non è stato ripetuto.

`git push origin fase-1`: `NOT_EXECUTED`. Non esiste un commit da inviare e il remote è HTTPS, mentre l'ambiente impone il divieto di rete. I deliverable sono presenti nel worktree sotto `reports/` ma non risultano committati.

## 2. Findings Register

| ID | Severity | Confidence | ADD locator | Related IDs | Finding | Evidence | Impact | Exact remediation | Disposition |
|---|---|---|---|---|---|---|---|---|---|
| `DRF-001` | `BLOCKER` | `HIGH` | §3.0.1, §3.0.3; §4.2 `ScenarioRunSpec`; §4.3 `HandoffEnvelope`; §5.3 `SecurityContext`; §6.3 trace fields | `AM-01`, `DRAFT-A`, `FR-006`, `NFR-006`, `NFR-040`, `TB-CXT-05` | La tabella GCS dichiara copertura integrale che i record non realizzano. | `domain_id` è dichiarato `✔`, ma le superfici usano `domain`, `domains[]` o lo omettono; Scenario manca anche di Principal, actor chain e correlation pur dichiarando di realizzare il set. | La chiave di isolamento e i policy/audit input non hanno forma univoca; la prova di chiusura del BLOCKER originario è falsa. | Uniformare `domain_id`; separare eventuale domain scope; aggiungere o derivare attestatamente ogni campo mancante; generare la tabella da inventory e testare tutte le superfici. | `VALID` |
| `DRF-002` | `CRITICAL` | `HIGH` | §3.0.1 riga `principal_id`; §3.2 `integrity.producer_principal_ref` e regole runtime | `AM-01`, `DRAFT-A`, `FR-006`, `RSK-006`, `TB-CXT-02` | Il Principal GCS è collassato nel producer dichiarato nel body senza binding normativo al transport Principal. | Il JSON richiede `producer_principal_ref`; il testo dice che `principal_id` non è mai asserito dal body, ma le regole boundary non impongono confronto/sovrascrittura di quel campo. | Impersonificazione/provenance falsa e confused authority all'ingress. | Distinguere source producer da effective Principal; creare il secondo dal trasporto; vincolare il primo al binding o quarantinare il mismatch. | `VALID` |
| `DRF-003` | `CRITICAL` | `HIGH` | §3.7 ramo `target=CANONICAL_COMMIT`; §4.1; §5.4 | `AM-02`, `AM-09`, `DRAFT-B`, `DRAFT-G`, `ARC-014`, `FR-150` | Lo schema accetta una mutazione canonica `R1_ANALYZE` con `approval.mode=NONE`. | Caso `negativo semantico: CANONICAL_COMMIT R1 senza Human Gate`: atteso `REJECT`, ottenuto `ACCEPT`. | Bypass strutturale del Human Gate sul solo writer canonico; canonicalizzazione non governata non esclusa dal contratto. | Nel ramo canonical imporre risk ≥`R2`, Approval umano/quorum e ruoli; aggiungere negativo obbligatorio alla suite compiler. | `VALID` |
| `DRF-004` | `CRITICAL` | `HIGH` | §4.1.1; §4.1.2 `ACT-T12`, `T14`, `T19`, `T29` | `AM-06`, `DRAFT-E`, `RSK-037`, `RSK-050`, `RSK-054` | Le emissioni rivalidano stop/dispatch ma non l'intera freshness; il retry duplica solo un subset delle guardie. | `G-FRESHNESS∧G-DISPATCH` è a T12; T14/T29 richiamano solo `G-DISPATCH`; T19 omette freshness, circuit breaker, adapter conformance e deadline. | Command esterno o commit canonico può essere emesso dopo drift di state, policy, Authority, Approval, release o watermark. | Rivalidare atomicamente `G-FRESHNESS∧G-DISPATCH` a ogni emissione/retry/compensation; drift ⇒ `INVALIDATED`; legare il check al GatePackage. | `VALID` |
| `DRF-005` | `CRITICAL` | `HIGH` | §3.1.1 `MarkingSchemeDefinition`; §5.3 formule | `AM-04`, `AM-12`, `DRAFT-D`, `DRAFT-H`, `FR-131`, `NFR-006`, `OI-021` | Il metamodello ammette semantica `PERMISSION`, mentre le formule trattano sempre caveat/dissemination come restrizioni e applicano union. | Enum `{RESTRICTION,PERMISSION}` contro testo “sono restrizioni” e formula di unione. | Uno scheme formalmente valido può ampliare permessi in un derivato e causare leakage. | Fissare `RESTRICTION` oppure definire operatore per famiglia coerente con la semantica; validare algebra e monotonia su tutti i valori ammessi. | `VALID` |
| `DRF-006` | `MAJOR` | `HIGH` | §4.1 diagramma; §4.1.2 tabella | `AM-18`, `ACT-T02`, `T19`–`T23`, `T27`, `T31` | Il claim di bijezione edge-level è falso; il harness confronta solo nomi di stato. | Più archi per singola riga; self-loop/“resta unknown” assenti; T22 salta nominalmente `OUTCOME_PENDING`, diversamente dal diagramma/T27. | Implementazioni generate possono produrre lifecycle diversi; il `PASS` meccanico sovrastima la verifica. | Una riga per arco con source/destination espliciti; correggere T22; harness su tuple di archi. | `VALID` |
| `DRF-007` | `MAJOR` | `HIGH` | §4.1.1 `G-FRESHNESS`; §4.1.2 `T24/T25` e testo seguente | `AM-07`, `DRAFT-F`, `FR-163`, `RSK-023`, `RSK-050` | Gli stati terminali aprono un Human Gate ma non definiscono adjudication/unblock; la conflict key è troppo coarse. | Nessuna transizione/record/authority/esito di adjudication; target enum identifica solo la classe external/internal, non il footprint. | Recovery ambiguity e blocco indefinito di azioni legittime indipendenti sullo stesso aggregate. | Definire `IndeterminateEffectAdjudication` append-only e una `conflict_scope` tipizzata; fail-closed solo quando il footprint non è calcolabile. | `VALID` |
| `DRF-008` | `MAJOR` | `HIGH` | §3.7 `canonical_commit_binding`, evidence e `error_codes`; §4.1.2 `T31` | `AM-02`, `AM-09`, `DRAFT-B`, `DRAFT-G`, `FR-149`, `FR-150` | Il binding canonical dichiara booleani ma non lega Claim/Evidence/Decision/revision ai parametri; l'error model non distingue i rifiuti di C3. | Nessun field binding/operation; `minimum_count=0` ammesso; assenti codici per precondition, invariant e revision conflict. | Il DDD dovrebbe inventare semantiche di admission e mapping degli errori sul percorso canonico. | Aggiungere binding tipizzato, evidence non-vuota dove richiesta e mappa deterministica dei reason code di C3. | `VALID` |
| `DRF-009` | `MAJOR` | `HIGH` | §2.6 `BA-01` e paragrafo conclusivo | `AM-28`, `NFR-084`, `RSK-013`, `RSK-019` | Il fallback `BA-01` è presentato come adapter substitution ma cambia il modello di atomicità. | Due commit logici, finestra di incoerenza e dichiarazione che §2.3 va riscritta. | Un fallback non conforme potrebbe essere adottato senza change control e riaprire perdita di eventi. | Marcarlo alternativa architetturale soggetta a change control e nuova crash-window analysis; mantenere `NO-GO`. | `VALID` |
| `DRF-010` | `MINOR` | `HIGH` | §1.1 nota v1.1; §8 colonna `CC` | `DRAFT-A`–`I` | Document Control conta sette emendamenti con decisione, mentre le bozze e §8 ne contano nove. | `AM-01,02,03,04,06,07,09,12,16` = 9. | Superficie di change control sottostimata nel punto di controllo del documento. | Sostituire “Sette” con “Nove” e derivare il conteggio dal log. | `VALID` |
| `DRF-011` | `MAJOR` | `HIGH` | Nota finale di `OCOR_DEC_197_plus_Draft_v0.1.md` | `DRAFT-B`, `E`, `F`, `G`, `I` | Il DAG di dipendenze fra bozze è incompleto. | Omesse `B→E`, `E→I`, `F→G`; tutte toccano T29/stop/error contract. | Approval parziale formalmente ammessa può lasciare una safety chain incoerente. | Pubblicare DAG e change-set atomici `{B,G,E,I}`, `{D,H}`; decidere inclusione di F con E/G. | `VALID` |

## 3. Delta Surface Review

### §2.6 Backend Assumption Register

Corretto: rende esplicita la non-evidenza, lega assunzione/test/NO-GO e non promuove backend. Difetto: `BA-01` offre un'alternativa che richiede riscrittura degli invarianti pur dichiarandola adapter-only (`DRF-009`). Le altre righe sono plausibili come target da verificare, non come feature presunte.

### §3.0–§3.0.4 regole trasversali

Il consolidamento di context, marking, naming e versioning è necessario. La tabella di copertura contiene però falsi `✔` e il Principal ingest è authority-ambiguous (`DRF-001/002`). La forma unica del marking è utile, ma l'algebra ammessa non è coerente (`DRF-005`). Il version bump è correttamente dichiarato senza claim di consumer esistenti.

### §3.7 Action Type

I nove rami sono soddisfacibili e retry/idempotenza/timeout/irreversibilità sono in gran parte enforceable. Il nuovo target canonico ha un bypass Human Gate (`DRF-003`) e un binding/error model incompleto (`DRF-008`). Non è pronto come contratto normativo del writer canonico.

### §3.8 Event Subscription

Adeguato: contract e cursor logici, at-least-once, deduplica, marking e replay policy-aware, nessun offset/topic/backend ID. Nessun finding autonomo.

### §4.1 FSM e nuovi stati/transizioni

State set e contiguità passano; la bijezione dichiarata non passa a livello di archi (`DRF-006`). L'emergency stop è migliorato ma la freshness non viene rivalidata alle emissioni (`DRF-004`). Gli stati indeterminati evitano pending infinito nominale, ma adjudication e conflitto sono incompleti (`DRF-007`).

### §4.2/§4.3 e GCS

Scenario e Handoff mantengono separazione causale/agentica e prompt non autorevole. I rispettivi record smentiscono però la copertura GCS dichiarata (`DRF-001`). Nessuna branch contamination o causal overclaim ulteriore è stata trovata.

### §5.2/§5.3

La distinzione Capability Lease / writer fencing / `ELM-080` è corretta e non attiva l'elemento differito. La direzione restriction/permission è concettualmente corretta, ma il metamodel consente configurazioni che la formula tratta al contrario (`DRF-005`). `OI-021` resta formalmente aperta.

### §6–§7

Evidence fence, target non osservati e scope disposition restano corretti. L'harness conferma l'universo 693 e la copertura dichiarata, con `CAP-026` fuori scope. Nessuna promozione `exact` a evidenza è stata rilevata.

### §8 Amendment Log

La tracciabilità `AM-*` è estesa e i self-reported defect sono documentati. Il conteggio change-control in §1.1 è incoerente con §8 (`DRF-010`). Il fatto che non restino campi conditional-required non dichiarati è confermato, ma non intercetta il fail-open semantico di `DRF-003`.

## 4. Decision Draft Assessment

Nessuna bozza è approvata o ritirata da questa review.

| Draft | Assessment | Raccomandazione |
|---|---|---|
| `DRAFT-A` | Necessaria; scope e criterio non coprono le incoerenze GCS/principal | `REVISE` |
| `DRAFT-B` | Necessaria; pipeline unica valida, ma risk floor/binding incompleti | `REVISE` |
| `DRAFT-C` | Necessaria; branch/single-writer/relay coerenti e verificabili | `PROCEED TO CHANGE CONTROL` |
| `DRAFT-D` | Correzione necessaria; semantica contraddetta dal metamodel | `REVISE` con H |
| `DRAFT-E` | Necessaria; manca freshness e copertura completa retry/compensation | `REVISE` |
| `DRAFT-F` | Necessaria; terminalità valida, adjudication e conflict scope incomplete | `REVISE` |
| `DRAFT-G` | Necessaria; Event adeguato, Action non safety-complete | `REVISE` |
| `DRAFT-H` | Necessaria; non chiude OI-021, ma algebra non coerente su tutti i valori | `REVISE` con D |
| `DRAFT-I` | Necessaria; distinzione da ELM-080 corretta | `PROCEED TO CHANGE CONTROL` |

La nota delle dipendenze va corretta come da `DRF-011`. `PROCEED TO CHANGE CONTROL` non equivale ad approvazione: l'authority resta quella dichiarata dal documento.

## 5. Verdetto provvisorio sulla sola superficie di delta

**`NOT READY FOR DDD`**.

Conteggio: 1 `BLOCKER`, 4 `CRITICAL`, 5 `MAJOR`, 1 `MINOR`, 0 `OBSERVATION`.

Il `BLOCKER` è documentale e architetturale: la tabella introdotta per dimostrare copertura del Governed Context Set non corrisponde ai record normativi, quindi l'isolamento cross-surface non è specificabile in modo univoco. I `CRITICAL` includono un bypass riprodotto del Human Gate sul commit canonico, un Principal ingest non attestato, stale-context emission e un'algebra marking capace di trattare permessi come restrizioni. Questi difetti appartengono alla superficie nuova v1.1 e devono essere corretti prima dell'avvio del DDD.

Il verdetto non valuta la chiusura di `ARF-001`–`ARF-027`, perché la FASE 1 è deliberatamente cieca rispetto al materiale prior. Non chiude `OI-*`, `ASM-*` o `RSK-*`, non attiva capability differite, non promuove tecnologie e non incrementa lo stato probatorio: `E1=0`, `E2=0`, zero `Verified`.
