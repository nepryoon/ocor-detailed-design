# OCOR ADD v1.2 Candidate — Change-Control Package

## Package Control

Stato del pacchetto: `Proposed — awaiting change control`.

Baseline: ADD v1.1, SHA-256 `3e7532c7101e80c74b511cedc56a0563ca0938a3fe259911a91245cb19dedc7f`.

Authority fence: questo pacchetto non assegna nuovi identificativi `DEC-*`, non approva `DRAFT-A`–`DRAFT-I`, non chiude `OI-*`, `ASM-*` o `RSK-*`, non modifica i registri sorgente e non incrementa `E1=0`, `E2=0` o il numero di requisiti `Verified` (zero). Le formulazioni sotto sono il testo esatto da sottoporre all'Architecture Review Authority.

## Dependency DAG

La direzione `X → Y` significa «X depends_on Y», quindi Y deve essere deciso prima di X.

```text
CC-CANONICAL-PATH → CC-GCS
CC-CANONICAL-PATH → DRAFT-G
CC-EMISSION-FENCE → CC-GCS
CC-EMISSION-FENCE → DRAFT-I
CC-INDETERMINATE-ADJUDICATION → CC-EMISSION-FENCE
CC-MARKING-ALGEBRA → DRAFT-H
CC-ACTION-EVENT-CONTRACTS → CC-GCS
CC-FR095-SCOPE → authority over DEC-103 and requirement registers
CC-BA01-ALTERNATIVE → CC-CANONICAL-PATH
CC-DEC-ALLOCATION → document traceability authority
```

Il change set emission/adjudication è atomico: `CC-EMISSION-FENCE` e `CC-INDETERMINATE-ADJUDICATION` non devono essere approvati in combinazioni che consentano nuovo dispatch durante un esito irrisolto. Il change set GCS/canonical path deve preservare contemporaneamente il binding del Principal, il GatePackage e l'unico percorso di mutazione.

## CC-GCS — Governed Context Set canonico

- Finding: `DRF-001`, `DRF-002`; estende `DRAFT-A` senza approvarla.
- Decisione richiesta — testo esatto: **«Approvare `GovernedContext` §1.4 della ADD v1.2 Candidate quale unico record normativo di contesto governato. Il Principal effettivo è derivato esclusivamente da un binding di trasporto autenticato; valori Principal dichiarati nel body sono assertion non autoritative. Tutte le superfici §3.0.1 devono produrre lo stesso digest canonico; assenza, mismatch o derivazione non verificabile causano deny/quarantine e audit, mai riduzione fail-open.»**
- Stato: `Proposed — awaiting change control`.
- Razionale: elimina confused deputy, scope drift e modelli di contesto concorrenti.
- Alternative: mantenere mapping per-surface; usare il body come authority; record canonico selezionato. Le prime due sono respinte perché non dimostrano equivalenza o autenticità.
- Opzione candidata: record unico a undici campi, origini `BODY`, `TRANSPORT`, `DERIVED_FROM_VERIFIED_BINDING` e digest deterministico.
- Impatti: contratti ingestion/query/registry/MCP/action/event, scenario, handoff, security e observability; migrazione additive/breaking come §8.2.
- Requisiti/decisioni: `FR-006`, `FR-131`, `NFR-006`, `NFR-040`; decisioni già tracciate in §1.4/§5.1.
- Registri da aggiornare: Decision Register e Decision Traceability Index con la decisione approvata; Requirement Traceability Index con i locator §1.4/§3.0.1; contract/version register futuro.
- Dipendenze: prerequisito di canonical path, emission fence e Action/Event.
- Rischio residuo: tassonomia concreta marking e profilo crittografico restano aperti.
- Rollback: rifiutare la candidata e conservare v1.1; non è ammesso rimuovere soltanto il transport binding.
- Criterio di approvazione: testo approvato senza ambiguità sull'origine del Principal e con tutti gli enforcement point nominati.
- Criterio di chiusura: conformance suite accetta un caso coerente e respinge body/transport mismatch per la ragione attesa su ogni surface.

## CC-CANONICAL-PATH — mutazione canonica governata

- Finding: `DRF-003`, `DRF-008`; estende `DRAFT-B` e `DRAFT-G`.
- Decisione richiesta — testo esatto: **«Approvare `target=CANONICAL_COMMIT` quale unico percorso di mutazione dello stato canonico. Ogni commit richiede risk class almeno `R2_CONTROLLED`, Human Gate o Dual Control con quorum e ruoli non vuoti, `Decision ref`, `Authority ref`, Evidence non vuota, claim/source binding, aggregate type/ref, expected revision, precondition/invariant bindings, idempotency key, GCS digest e GatePackage immutabile. `approval.mode=NONE`, dati mancanti o mismatch sono respinti prima della mutazione con reason code deterministico.»**
- Stato: `Proposed — awaiting change control`.
- Razionale: chiude il bypass C3 e rende enforceable l'admission.
- Alternative: mutazione C3 diretta; workflow separato; Action pipeline unica. Selezionata la terza per unicità delle guardie.
- Impatti: §2.5 r.10, Action 1.1, `ACT-T29`–`ACT-T31`, C3/C6 e audit.
- Requisiti/decisioni: `FR-002`, `FR-005`, `FR-012`, `FR-149`, `FR-150`, `ARC-014`; decisioni correlate già in §3.7.
- Registri da aggiornare: Decision Register/Index; Requirement Traceability Index; contract catalogue.
- Dipendenze: `CC-GCS`, `DRAFT-G`.
- Rischio residuo: implementazione e failure injection restano senza Evidence.
- Rollback: v1.1 immutata; nessun adapter può introdurre un percorso alternativo durante il rollback.
- Criterio di approvazione: accettazione esplicita dell'unico writer e di tutti i binding obbligatori.
- Criterio di chiusura: fixture canonica valida accettata; R0/R1, `NONE` e assenza di Decision/Authority/Evidence respinte.

## CC-EMISSION-FENCE — rivalidazione al momento dell'emissione

- Finding: `DRF-004`; estende `DRAFT-E` e `DRAFT-I`.
- Decisione richiesta — testo esatto: **«Approvare `EMISSION-FENCE := G-FRESHNESS ∧ G-DISPATCH`, valutata atomicamente immediatamente prima di ogni primo invio, retry e compensation. La rivalidazione include state revision, policy digest e validity, Authority, Approval, ontology release, watermark, stop epoch, CapabilityLease, audit append availability, command deadline, circuit breaker, adapter conformance e GatePackage immutabile. Qualunque drift o errore di valutazione produce `INVALIDATED` prima dell'invio.»**
- Stato: `Proposed — awaiting change control`.
- Razionale: impedisce stale-context execution e bypass dello stop fra decisione e dispatch.
- Alternative: validazione a proposal/command creation; validazione best-effort; fence atomica selezionata.
- Impatti: `ACT-T12`, `T14`, `T19`, `T21`, `T29`, dispatcher/outbox/lease/audit.
- Requisiti/decisioni: `FR-138`, `NFR-047`, `NFR-079`, `RSK-023`, `RSK-037`, `RSK-050`.
- Registri da aggiornare: Decision Register/Index e traceability dei requisiti sopra.
- Dipendenze: `CC-GCS`, CapabilityLease `DRAFT-I`.
- Rischio residuo: race nell'implementazione da provare con fault injection; `E1/E2` restano zero.
- Rollback: blocco di tutti gli effetti se la fence non è implementabile; vietato degradare a warning.
- Criterio di approvazione: tutti i pin e tutti e tre i punti di emissione sono espliciti.
- Criterio di chiusura: casi state/policy/stop drift, lease scaduta e audit indisponibile producono `INVALIDATED`; caso immutato emette.

## CC-MARKING-ALGEBRA — metamodello calcolabile

- Finding: `DRF-005`; estende `DRAFT-D` e `DRAFT-H`.
- Decisione richiesta — testo esatto: **«Approvare il metamodello `MarkingSchemeDefinition` §5.3: le famiglie restriction usano union/join verso il più restrittivo; le famiglie permission usano intersection; dominance, top, bottom, valori ammessi, mandatory markings, caveat, dissemination controls, permitted purposes, handling instructions e declassification authority sono dichiarati. Valori unknown, label incomparabili o operatori incompatibili negano/quarantinano. `OI-021` resta aperta per la tassonomia nazionale concreta.»**
- Stato: `Proposed — awaiting change control`.
- Razionale: rende il join deterministico senza anticipare la tassonomia nazionale.
- Alternative: algoritmo fisso per tutti i campi; policy ad hoc; algebra per famiglia selezionata.
- Impatti: ingestion, derivazioni, query, export, logging, declassification.
- Requisiti/decisioni: `FR-131`, `FR-132`, `NFR-006`; `OI-021` invariata.
- Registri da aggiornare: Decision Register/Index e locator dei requisiti marking.
- Dipendenze: `DRAFT-H`; nessuna dipendenza dall'esito tassonomico di `OI-021`.
- Rischio residuo: fixture nazionali non ancora disponibili.
- Rollback: deny di ogni join non valutabile; nessun default permissivo.
- Criterio di approvazione: operatori e comportamento unknown sono completi per famiglia.
- Criterio di chiusura: golden test restriction/permission e adversarial unknown/incomparable verdi.

## CC-INDETERMINATE-ADJUDICATION — unblock governato

- Finding: `DRF-007`; estende `DRAFT-F`.
- Decisione richiesta — testo esatto: **«Approvare `ConflictScope` tipizzato e `IndeterminateEffectAdjudication` append-only. Un effetto indeterminato blocca nuovi effetti confliggenti; scope assente o ambiguo blocca l'intero ownership boundary. Solo un record firmato con Authority, Decision ed Evidence non vuota può ricalcolare il blocco. Silenzio, timeout o modifica in-place non equivalgono a non-effetto.»**
- Stato: `Proposed — awaiting change control`.
- Razionale: evita doppia attuazione e sblocco arbitrario.
- Alternative: blocco globale permanente; timeout automatico; adjudication tipizzata selezionata.
- Impatti: FSM, action ledger, reconciler, operator work queue.
- Requisiti/decisioni: `FR-163`, `NFR-079`, `RSK-023`, `RSK-050`.
- Registri da aggiornare: Decision Register/Index, traceability e risk treatment locator senza chiudere rischi.
- Dipendenze: change set atomico con `CC-EMISSION-FENCE`.
- Rischio residuo: disponibilità dell'Authority umana; possibile blocco conservativo prolungato.
- Rollback: mantenere il blocco; non consentire unblock automatico.
- Criterio di approvazione: conflict relation versionata e authority per ogni disposition.
- Criterio di chiusura: unknown scope blocca; solo adjudication valida sblocca; timeout resta indeterminato.

## CC-ACTION-EVENT-CONTRACTS — change set dei contratti

- Finding: `DRF-008`, `V12-RF-001`, `V12-RF-002`; estende `DRAFT-G`.
- Decisione richiesta — testo esatto: **«Approvare le versioni candidate MCP 1.2, Action 1.1 ed Event 1.1, inclusi GCS obbligatorio, quorum/ruoli non vuoti, Evidence minima coerente, binding canonical, reason code C3 e finestra replay obbligatoria quando il replay è consentito.»**
- Stato: `Proposed — awaiting change control`.
- Razionale: allinea schema e semantica normativa.
- Alternative: validazione soltanto runtime; contratti versionati selezionati.
- Impatti: generatori, SDK, registry e migration notes; nessun consumer approvato esiste al cut-off.
- Requisiti/decisioni: `FR-003`, `FR-016`, `FR-137`, `FR-140`, `NFR-005`, `NFR-016`, `NFR-048`.
- Registri da aggiornare: Decision Register/Index, contract catalogue, Requirement Traceability Index.
- Dipendenze: `CC-GCS`, `CC-CANONICAL-PATH`.
- Rischio residuo: validator OpenAPI ufficiale `NOT_EXECUTED`; risoluzione `$ref` e Draft 2020-12 sono verdi.
- Rollback: mantenere contratti v1.1/v1.0 e bloccare release della candidata.
- Criterio di approvazione: versione e migration disposition esplicite.
- Criterio di chiusura: ogni ramo ha caso positivo/negativo; combinazioni vietate falliscono per la ragione attesa.

## CC-FR095-SCOPE — coerenza `FR-095` / `ELM-070`

- Finding: `DRF-012`.
- Decisione richiesta — testo esatto: **«Approvare la riclassificazione di `FR-095` da P0/PoC a P0/MVP, mantenendo `ELM-070` differita fuori dal PoC. Il PoC non dichiara una thin slice AAP, non dimostra controfattuali AAP e non attiva implicitamente `ELM-070`. `DEC-103` deve essere emendata nello stesso change set per sostituire la release PoC di `FR-095` con MVP; finché il change set non è approvato la discrepanza resta authority-blocked.»**
- Stato: `Proposed — awaiting change control`.
- Razionale: è l'opzione meno espansiva e non introduce una capability non finanziata nel PoC.
- Alternative: thin slice AAP positiva nel PoC; riclassificazione a MVP selezionata.
- Impatti: scope PoC, acceptance planning e traceability; nessuna variazione del testo funzionale o priorità P0.
- Requisiti/decisioni: `FR-095`, `ELM-070`, `CAP-019`, `DEC-103`.
- Registri da aggiornare, atomicamente: (1) Requirement Register riga `FR-095`, Release `PoC`→`MVP`; (2) Requirement Traceability Index riga `FR-095`, disposizione `Confermato; PoC`→`Confermato; MVP`; (3) Decision Register riga `DEC-103`, frase `FR-095 ... P0/PoC`→`P0/MVP`; (4) Decision Traceability Index riga `DEC-103`, aggiunta della release/disposition `FR-095=P0/MVP`; (5) CAP/ELM Requirement Crosswalk righe `CAP-019` e `ELM-070`, annotazione che la copertura `FR-095` è MVP e che `ELM-070` non è attiva nel PoC.
- Dipendenze: authority competente a modificare una decisione Approved e i registri normativi.
- Rischio residuo: il capability gap controfattuale permane fino a MVP; nessun claim AAP nel PoC.
- Rollback: conservare integralmente v1.1 e classificare il gate `NOT READY FOR DDD` per la contraddizione, oppure finanziare la thin slice con nuovo change control.
- Criterio di approvazione: tutte e cinque le modifiche registro sono approvate come change set atomico.
- Criterio di chiusura: scansione registri mostra un'unica release MVP per `FR-095` e `ELM-070` assente dal PoC.

## CC-BA01-ALTERNATIVE — atomicità local state+outbox

- Finding: `DRF-009`, `BA-01`.
- Decisione richiesta — testo esatto: **«Classificare il fallback `BA-01` come `ARCHITECTURAL_ALTERNATIVE_REQUIRING_CHANGE_CONTROL`. Se il backend candidato non realizza il commit atomico di aggregate revision, canonical commit e outbox, la release è `NO-GO` finché l'Authority non approva una sola alternativa, la relativa failure analysis, la riscrittura di §2.3/§6.2, i test crash-window e il rollback.»**
- Stato: `Proposed — awaiting change control`.
- Razionale: il fallback cambia un hard invariant e non è una sostituzione adapter-only.
- Alternative: versioned outbox atomica; RDBMS/event log; two-log + reconciler. Nessuna è approvata qui.
- Impatti: C3, relay, recovery, consistency e `RSK-013/019`.
- Requisiti/decisioni: `NFR-058`, `NFR-084`, `ARC-007`, `ARC-020`.
- Registri da aggiornare: Decision Register/Index, backend assumption register futuro, risk treatment locator.
- Dipendenze: `CC-CANONICAL-PATH`.
- Rischio residuo: proprietà del backend candidata non verificata.
- Rollback: non rilasciare C3; baseline v1.1 resta ricostruibile.
- Criterio di approvazione: una sola topologia e failure semantics esplicite.
- Criterio di chiusura: crash-window/concurrency/fork tests definiti e poi eseguiti nel DDD; al presente restano futuri.

## CC-DEC-ALLOCATION — `DEC-173` e `DEC-175`

- Finding: `DRF-015`.
- Decisione richiesta — testo esatto: **«Approvare l'allocazione architetturale di `DEC-173` ad Agent Kernel e superfici role-oriented, e di `DEC-175` a Compiler & Gateway per documentazione, sandbox e conformance kit. Mantenere separata la disposition delle 13 decisioni document/programme dalle 183 decisioni allocate a subsystem/programme, con coverage globale 196/196.»**
- Stato: `Proposed — awaiting change control`.
- Razionale: entrambe le decisioni Approved hanno impatto subsystem e non sono meri gate.
- Alternative: lasciare la copertura solo a range; allocazione semantica selezionata.
- Impatti: §7, ownership DDD e acceptance allocation.
- Requisiti/decisioni: `DEC-173`, `FR-166`, `FR-167`, `CAP-014`; `DEC-175`, `NFR-082`, `DEP-024`.
- Registri da aggiornare: ADD/DDD traceability; Decision Traceability Index solo se l'Authority richiede il locator ADD esplicito.
- Dipendenze: nessuna tecnica; authority documentale.
- Rischio residuo: owner organizzativi da confermare nel DDD.
- Rollback: mantenere le righe come proposed e non dichiarare coverage semantica approvata.
- Criterio di approvazione: subsystem e requirement allocation nominati.
- Criterio di chiusura: coverage globale 196/196 senza contare una decisione in una disposition incompatibile.

## Package Gate

Il pacchetto è completo per decisione, ma tutte le voci restano `Proposed — awaiting change control`. L'opzione candidata della ADD è unica e fail-closed; il rollback comune è la baseline v1.1 immutata. L'Authority può approvare per change set compatibili col DAG, rigettare o richiedere una nuova candidata. Non è consentita un'approvazione parziale che renda insoddisfatti i contratti o rimuova una guardia dipendente.
