# STEP 6 — Red-team sulla superficie di delta

## Risultato per categoria

| Categoria | Evidenza precisa | Disposizione |
|---|---|---|
| Authority ambiguity | §3.0.1 mappa il Principal al body `integrity.producer_principal_ref` senza binding runtime esplicito | `DRF-002 VALID` |
| Confused deputy | Principal/Delegation/Policy sono separati e prompt/Goal non concedono Authority (§4.3.1, §5.2) | `ALREADY_GOVERNED` |
| Stale-context execution | `G-FRESHNESS` valutata a `ACT-T12`, non rivalidata a `T14`/`T29`; `T19` usa un subset di guardie | `DRF-004 VALID` |
| Race condition | Stop-vs-relay è indirizzato con precedenza e `stop_epoch`; state/policy drift-vs-relay resta scoperto | `DRF-004 VALID` |
| Duplicate effect | Timeout non idempotente e reconciliation sono governati; unblock/footprint dopo indeterminatezza non lo sono | `DRF-007 VALID` |
| Inconsistent watermark | Token, served context e atomic facts+watermark sono coerenti come target; feature backend resta non verificata in `BA-02/03` | `ALREADY_GOVERNED` / evidence assente correttamente dichiarata |
| Circular dependency | La nota finale delle bozze omette dipendenze necessarie fra decisioni sulla stessa safety chain | `DRF-011 VALID` |
| Cross-compartment leakage | Naming/missing GCS e algebra permission/restriction incoerente | `DRF-001`, `DRF-005 VALID` |
| Fail-open | Un canonical commit `R1` senza Approval valida nello schema | `DRF-003 VALID` |
| Capability escalation | Nessuna escalation agentica esportabile nel profilo PoC; il bypass è nel contratto Action interno | `DRF-003 VALID` |
| Prompt-derived authority | Vietata esplicitamente in §3.5, §4.3.1 e §5.2 | `ALREADY_GOVERNED` |
| Branch contamination | Relay solo `main`, identity `C7` senza `main.write`, fork senza delivery | `ALREADY_GOVERNED`; `DRAFT-C` coerente |
| Causal overclaim | Estimate/ABSTAIN separati e capability differita tipizzata; evidence fence esplicita | `ALREADY_GOVERNED` |
| Unsafe retry | Regola non-idempotent→unknown corretta; retry emission revalidation incompleta | `DRF-004 VALID` |
| Recovery ambiguity | Human adjudication degli stati terminali non contrattualizzata | `DRF-007 VALID` |
| Backend lock-in | SPI e public contract sono neutrali; un fallback `BA-01` richiede però riscrittura architetturale | `DRF-009 VALID` |
| Feature non verificate | `BA-01`–`BA-08` le dichiarano non verificate e impongono NO-GO; nessuna promozione probatoria | Corretto, salvo qualità del fallback `BA-01` |
| Scope leakage | `CapabilityLease` è distinto da `ELM-080`; vector/memory/counterfactual restano differiti | `ALREADY_GOVERNED`; `DRAFT-I` coerente |
| Over-reach | Il blocco di `G-FRESHNESS` usa aggregate+target class senza effect footprint e può serializzare azioni indipendenti | `DRF-007 VALID` |

## Backend Assumption Register

Le otto righe coprono le principali assunzioni semantiche dei backend nominati: atomicità/outbox e branch isolation (`BA-01`), watermark (`BA-02`), time travel (`BA-03`), round-trip W3C (`BA-04`), workflow action (`BA-05`), storage scenario (`BA-06`), backbone (`BA-07`) e control plane/revoca (`BA-08`). La dichiarazione di non-evidenza e il `NO-GO` in assenza di test sono corretti.

Il fallback di `BA-01` non soddisfa però il criterio dichiarato che dovrebbe rendere la sostituzione “un'operazione di adapter e non una riprogettazione”:

- passa da un unico commit atomico state+outbox a due commit logici su store separati;
- ammette una finestra di incoerenza;
- la stessa riga dice che §2.3 «va riscritta» se la proprietà non è supportata.

Cambiare il modello di atomicità e riscrivere un invariante cross-container non è una sostituzione di adapter. Il fallback può essere una legittima architettura alternativa, ma richiede change control, nuova failure analysis e modifica di §2.3/§6.2; non può essere presentato come uscita già compatibile.

Classificazione: `DRF-009`, `MAJOR`, confidence `HIGH`, locator §2.6 `BA-01` e paragrafo conclusivo; related `AM-28`, `RSK-013`, `RSK-019`, `NFR-084`.

Remediation esatta: marcare `BA-01` fallback come `ARCHITECTURAL_ALTERNATIVE_REQUIRING_CHANGE_CONTROL`, rimuovere il claim di adapter-only e aggiungere un gate che rivaluti perdita/duplicazione di evento nelle nuove crash windows. Lasciare `NO-GO` il profilo corrente finché o la proprietà atomica è provata o l'alternativa è approvata.

## Change-control surface

§1.1 afferma che **sette** emendamenti richiedono una decisione di baseline; §8 e il documento delle bozze ne identificano **nove** (`AM-01`, `02`, `03`, `04`, `06`, `07`, `09`, `12`, `16`). Il conteggio nel Document Control è quindi errato.

Classificazione: `DRF-010`, `MINOR`, confidence `HIGH`, locator §1.1 nota v1.1 e §8 colonna `CC`; related `DRAFT-A`–`I`.

Remediation esatta: sostituire “Sette” con “Nove” e derivare il conteggio dalla colonna `CC` dell'Amendment Log.

## Valutazione `DRAFT-A`–`DRAFT-I`

Nessuna voce è approvata da questa review; le raccomandazioni indicano soltanto la disposizione proposta all'authority competente.

| Draft | Necessità della decisione | Razionale e scope | Dipendenze/criterio di chiusura | Raccomandazione |
|---|---|---|---|---|
| `DRAFT-A` | Sì: origine e set minimo cross-contract sono scelte vincolanti, non solo correzioni lessicali | Razionale corretto; scope incompleto/incoerente per Scenario, Handoff, Security e Observability; principal ingest ambiguo | Dipende dalla correzione `DRF-001/002`; criterio “tutti e undici i campi” va espresso come mapping, non come proprietà letterali del body | `REVISE` |
| `DRAFT-B` | Sì: scegliere una pipeline unica per tutte le mutazioni è architetturale | Razionale forte e no-bypass corretto; scope insufficiente su risk floor, Approval e binding Claim/Evidence/Decision | Dipende da `DRAFT-G` **e `DRAFT-E`**; criterio deve includere test negativo `CANONICAL_COMMIT R1/approval NONE` | `REVISE` |
| `DRAFT-C` | Sì: chiarisce ownership e branch authority | Scope proporzionato; non chiude `OI-020`; regola relay `main` attuabile | Criteri di forbidden-write e fork/outbox verificabili | `PROCEED TO CHANGE CONTROL` |
| `DRAFT-D` | La correzione unione-vs-intersezione è necessaria; la parametrizzazione semantica è scelta di baseline | Razionale leakage corretto, ma decisione e metamodello si contraddicono consentendo `PERMISSION` e applicando sempre union | Dipende da `DRAFT-H`; golden test deve includere scheme con ogni valore ammesso | `REVISE`, preferibilmente consolidare con H |
| `DRAFT-E` | Sì: il punto di serializzazione stop/dispatch è una scelta safety | Rivalidare all'emissione è corretto ma lo scope copre solo `G-DISPATCH`, non freshness; retry incompleto | Dipende operativamente da `DRAFT-I`; deve coprire `T14`, `T19`, `T29` e compensation emission | `REVISE` |
| `DRAFT-F` | Sì: terminalità e conflitto su effetti ignoti sono policy safety | Razionale corretto; scope eccessivo sul target coarse e incompleto sull'adjudication/unblock | Dipende da `DRAFT-G` per error codes e va valutata con E; closure deve verificare azioni indipendenti non bloccate | `REVISE` |
| `DRAFT-G` | Sì: aggiungere i kind contract mancanti è architetturale | Event contract adeguato; Action contract contiene il bypass e le omissioni di `DRF-003/008` | Dipendenza reciproca con B per il target interno; criterio attuale non testa il risk floor | `REVISE` |
| `DRAFT-H` | Sì: rendere l'algebra esprimibile senza scegliere la tassonomia concreta è livello ADD | Non chiude `OI-021`, ma operatori e semantiche ammesse non sono coerenti | Dipende da D; closure deve provare tutte le configurazioni ammesse, non una sola fixture | `REVISE` |
| `DRAFT-I` | Sì: il controllo di sicurezza non può dipendere da `ELM-080` differito | Distinzione lease/fencing/reservation chiara e scope corretto | È dipendenza di E per il target di stop; criterio di prova indipendente dalla revoca push è verificabile | `PROCEED TO CHANGE CONTROL` |

### Dipendenze mancanti nella nota finale

La nota finale dichiara solo `B→G`, `D→H` ed evaluation congiunta `E↔F`. Sono mancanti almeno:

- `B→E`: `B` introduce l'emissione interna `ACT-T29`, mentre `E` ne stabilisce la rivalidazione stop/audit;
- `E→I`: il target di contenimento usa il Capability Lease definito da `I`;
- `F→G`: `F` aggiunge stati/error codes al contratto Action introdotto da `G`.

Classificazione: `DRF-011`, `MAJOR`, confidence `HIGH`, locator nota finale `OCOR_DEC_197_plus_Draft_v0.1.md`; impact: una approval parziale ammessa dal grafo dichiarato può lasciare un percorso safety incompleto.

Remediation esatta: pubblicare un DAG normativo di dipendenze e imporre change-set atomici `{B,G,E,I}` per il percorso canonical/dispatch e `{D,H}` per marking; specificare se `F` è nello stesso change-set di `E/G` o se i relativi error codes sono rimossi fino alla sua approvazione.
