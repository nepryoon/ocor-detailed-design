# OCOR — Full Memory Atomic Register Promotion Package v1.0

## 1. Esito

**Stato: `READY FOR AUTHORITY PROMOTION — DECISION ID UNASSIGNED`.**

Il pacchetto rende coerenti i cinque registri con la scelta di realizzare nel PoC la memoria
agentica governata completa. Gli snapshot approvati restano immutati; le versioni complete
candidate sono in `reports/governance_candidates/` e devono essere promosse insieme.

La promozione non dichiara il runtime implementato o verificato. Conserva `E1=0`, `E2=0`,
la separazione epistemica e tutti i gate di autorità, sicurezza e azione.

## 2. Rettifica normativa

| Oggetto | Baseline corrente | Disposizione candidata |
|---|---|---|
| `FR-118` | P0/PoC; schema minimo e expiry | P0/PoC; full governed memory, otto kind, sette scope, persistenza cross-run, lifecycle completo, context receipt e promozione soltanto via C6/C3 |
| `FR-119` | P0/PoC; isolamento cross-tenant/compartment | P0/PoC; non-interferenza su structured/full-text/vector/hybrid retrieval, inclusi rank, count, cache, error shape, timing e federazione |
| `ELM-084` | differito da `DEC-196`, nonostante `FR-118/119` PoC | `CORE/P0/PoC`, profilo `FULL_GOVERNED_AGENT_MEMORY` |
| `DEC-116` | memoria scoped, governata e non canonica | preservata e resa esecutiva nel PoC; nessuna retroattività |
| Evidenze | `E1=0`, `E2=0` | invariate; `FGM-01`–`FGM-20` restano obblighi di verifica |

Il nuovo provvedimento dovrà supersedere esclusivamente la clausola di differimento di
`ELM-084` contenuta in `DEC-196`. Non annulla né riscrive `DEC-116` o l’approvazione IRB.

## 3. Snapshot atomici

| Registro | Snapshot candidato completo | Mutazione controllata |
|---|---|---|
| Requirement Register | `OCOR_Requirement_Register_v1.1_FULL_MEMORY_CANDIDATE.md` | testo normativo e acceptance di `FR-118/119`; ID, priorità, release e stato preservati |
| Requirement Traceability Index | `OCOR_Requirement_Traceability_Index_v1.1_FULL_MEMORY_CANDIDATE.md` | componenti, metodi e FGM allocati; evidence state invariato |
| Decision Register | `OCOR_Decision_Register_v1.2_FULL_MEMORY_CANDIDATE.md` | proposta change-control senza ID inventato; storia immutata |
| Decision Traceability Index | `OCOR_Decision_Traceability_Index_v1.2_FULL_MEMORY_CANDIDATE.md` | catena proposta verso obiettivi, componenti, requisiti, contratti e test |
| CAP/ELM Crosswalk | `OCOR_CAP_ELM_Requirement_Crosswalk_v1.1_FULL_MEMORY_CANDIDATE.md` | `ELM-084 = CORE/P0/PoC` e mapping esteso |

Digest e risultato dei controlli sono registrati in
`OCOR_FULL_MEMORY_GOVERNANCE_CANDIDATE_SHA256SUMS` e
`reports/tests/full_memory_governance_candidate_results.json`.

## 4. Testo decisionale proposto

L’autorità può assegnare il prossimo identificativo libero a una disposizione equivalente:

> È approvata la promozione di `ELM-084` da elemento differito a `CORE/P0/PoC` con profilo
> `FULL_GOVERNED_AGENT_MEMORY`. Il PoC deve implementare tutti i kind e gli scope di memoria,
> persistenza cross-run, retrieval structured/full-text/vector/hybrid, consolidamento,
> correzione, supersession, revoca, expiry, forgetting, legal hold, deletion saga e receipt di
> influenza. Memory resta non canonica, tainted e priva di Authority. Ogni promozione verso lo
> stato canonico percorre C6 e C3. Sono differiti soltanto scala, HA, SLO e prove E2, non le
> capacità semantiche o di governance. La decisione supersede esclusivamente il differimento
> di `ELM-084` registrato in `DEC-196` e promuove atomicamente i cinque snapshot candidati.

Il testo non assegna qui alcun numero `DEC-*`: l’allocazione e l’effective date appartengono
all’autorità di approvazione.

## 5. Condizioni di promozione

La promozione è valida soltanto se, nello stesso change set:

1. viene assegnato e registrato un identificativo decisionale libero;
2. i cinque snapshot vengono consolidati senza modifiche parziali;
3. ADD v1.3 e LLD v1.1 sono rigenerati contro i digest promossi;
4. JSON Schema e Memory OpenAPI superano la validazione governata;
5. il checker dei registri e l’assurance IRB→ADD→LLD restano verdi;
6. manifest e decision record riportano gli stessi digest;
7. nessun esito `FGM-*` viene dichiarato superato senza evidenza runtime acquisita.

Qualsiasi promozione parziale lascia `ELM-084` non risolto e blocca l’approvazione congiunta
ADD v1.3 / LLD v1.1.

## 6. Invarianti non negoziabili

- Memory, Message, Goal e tool output non concedono Authority.
- Contenuto umano, esterno o generato da modello è tainted e non è istruzione eseguibile per
  default.
- Claim, Observation, Hypothesis, Model Output, Decision, ExecutionResult e
  OutcomeAssessment restano distinti.
- Nessun agente possiede credenziali datastore o un percorso di scrittura canonica diretto.
- Ogni mutazione canonica usa il single writer C3 e il commit locale state/revision/outbox.
- Human Gate, dual control, `ABSTAIN`, `EXECUTION_UNKNOWN`, kill switch e
  `EMISSION-FENCE` restano fail-closed.
- Nessuna affermazione di Production readiness, compliance, parità o superiorità deriva da
  questa rettifica documentale.
