# OCOR — Bozze di decisione candidate per l'ADD v1.1

> ## ⚠ STATO: BOZZE NON APPROVATE — NESSUN IDENTIFICATIVO ASSEGNATO
>
> Questo documento **non è un Decision Register** e **non estende** `OCOR_Decision_Register_v1.0.md`.
> Contiene nove voci candidate redatte per il change control degli emendamenti dell'ADD v1.1
> che stabiliscono o chiariscono una scelta architetturale vincolante.
>
> - Nessun identificativo `DEC-197` o successivo è assegnato. Le bozze usano gli slug provvisori `DRAFT-A`…`DRAFT-I`.
> - Il progressivo definitivo è attribuito **soltanto** dall'Architecture Review Authority al momento
>   dell'approvazione, in ordine di approvazione e a partire da `DEC-197` come previsto da `DEC-196`.
> - Lo stato di ogni voce è `Proposed — awaiting change control`. Nessuna è `Approved`.
> - L'approvazione non è delegabile automaticamente: `DEC-196` ha chiuso la delega di approvazione autonoma
>   con il freeze della IRB v1.0.
> - Nessuna bozza chiude un `OI-*`, un `ASM-*` o un `RSK-*`, attiva una capability differita, promuove una
>   tecnologia candidata o modifica `E1`/`E2`.

| Campo | Valore |
|---|---|
| Documento | `OCOR DEC-197+ Draft` |
| Versione | `v0.1` |
| Data | 30 agosto 2026 |
| Origine | Emendamenti `AM-01`, `AM-02`, `AM-03`, `AM-04`, `AM-06`, `AM-07`, `AM-09`, `AM-12`, `AM-16` dell'ADD v1.1 §8 |
| Documento governato | `OCOR_Architectural_Design_Document_v1.1.md` |
| Baseline di riferimento | `Initial Requirements Baseline v1.0 — APPROVED BASELINE`, freeze `DEC-196` |
| Stato di tutte le voci | `Proposed — awaiting change control` |
| Approval mode richiesto | Approvazione umana esplicita di Product Owner e Architecture Review Authority; la delega autonoma è terminata con `DEC-196` |
| Stato probatorio | `E1=0`, `E2=0`, zero requisiti `Verified` — invariato |

---

## Indice delle bozze

| Slug | Titolo | Emendamento | Finding | Invariante toccato |
|---|---|---|---|---|
| `DRAFT-A` | Governed Context Set come set minimo obbligatorio dei contratti | `AM-01` | `ARF-001` | Isolamento multi-compartimento `TB-CXT-05` |
| `DRAFT-B` | Mutazione canonica come Action governata con target interno | `AM-02` | `ARF-002` | Pipeline governata `ARC-014`; non-promozione `ARC-010` |
| `DRAFT-C` | Scope del single-writer e branch scope del relay outbox | `AM-03` | `ARF-003` | Single writer `ARC-007`; isolamento scenario `TB-CXT-07` |
| `DRAFT-D` | Semantica direzionale del conservative join dei marking | `AM-04` | `ARF-004` | Propagazione conservativa dei marking |
| `DRAFT-E` | Punto di valutazione delle guardie di emissione | `AM-06` | `ARF-006` | Emergency stop `≤10 s`; audit fail-closed |
| `DRAFT-F` | Disposizione terminale degli esiti esterni indeterminati | `AM-07` | `ARF-007` | Assenza di doppia attuazione |
| `DRAFT-G` | Contrattualizzazione normativa di `ACTION` ed `EVENT` | `AM-09` | `ARF-009` | Completezza dei `ContractDefinition.kind` |
| `DRAFT-H` | Metamodello dello schema di marking | `AM-12` | `ARF-012` | Calcolabilità del conservative join |
| `DRAFT-I` | Capability Lease come controllo distinto da `ELM-080` | `AM-16` | `ARF-016` | Assenza di scope leakage sui controlli di safety |

---

## `DRAFT-A` — Governed Context Set come set minimo obbligatorio dei contratti

| Campo | Valore |
|---|---|
| Slug provvisorio | `DRAFT-A` |
| Titolo | Governed Context Set come set minimo obbligatorio e verificabile di ogni contratto OCOR |
| Stato | `Proposed — awaiting change control` |
| Approval mode | Approvazione umana esplicita richiesta |
| Effective from | Non applicabile finché non approvata |
| Supersedes | Nessuna. Precisa `DEC-036`, `DEC-089`, `DEC-124`, `DEC-126` senza sostituirle |
| Superseded by | — |

**Decisione proposta.** Il Governed Context Set — `tenant_id`, `organization_id`, `domain_id`, `compartments[]`, `classification_marking`, `purpose`, `principal_id`, `actor_chain`, `ontology_release_digest`, `policy_bundle_digest`, `correlation_id` — è normativo e ogni contratto pubblico OCOR lo realizza integralmente. `principal_id` e `actor_chain` sono sempre derivati dal transport security context e dalla Delegation chain verificata, e non compaiono nei contratti di richiesta sincrona, dove un campo dichiarativo costituirebbe un vettore di impersonificazione.

**Razionale.** L'ADD v1.0 dichiarava il set come obbligatorio in §1.4 ma nessun contratto lo trasportava: `organization_id` compariva una sola volta nell'intero documento e la Canonical Ingestion Envelope, essendo `additionalProperties: false`, rigettava cinque degli undici campi. La chiave di isolamento `(tenant_id, domain_id, compartments, purpose, marking, release_digest)` non era quindi costruibile per un evento ingerito, e l'enforcement di `TB-CXT-05` non era progettabile.

**Contenuto normativo.** Introduce §3.0.1 dell'ADD con la tabella di realizzazione per contratto e la regola di origine per campo. Estende `canonical-ingestion-envelope` a `1.1` con cinque campi obbligatori aggiuntivi, `QueryContext` con `organization_id`, `policy_bundle_digest` e `correlation_id`, `InvocationContext` con `organization_id` e `policy_bundle_digest`, `HandoffEnvelope` e `SecurityContext` con i campi mancanti.

**Requisiti serviti.** `FR-006`, `FR-129`, `FR-131`, `FR-134`; `NFR-006`, `NFR-040`, `NFR-043`. **Vincoli.** `ARC-004`, `ARC-015`, `ARC-016`. **Rischi mitigati.** `RSK-006`, `RSK-020`, `RSK-029`, `RSK-035`.

**Open issue non chiusi.** `OI-020` (isolamento fisico) e `OI-021` (tassonomia) restano aperti e non sono toccati.

**Criterio di verifica alla chiusura.** Un'istanza di envelope che porta tutti e undici i campi è accettata dal validator; la chiave di isolamento è costruibile per ogni evento ammesso; un envelope che dichiara `purpose` o `organization_id` incoerenti con il binding autorizzato dell'adapter è respinto con `Violation` e quarantena.

---

## `DRAFT-B` — Mutazione canonica come Action governata con target interno

| Campo | Valore |
|---|---|
| Slug provvisorio | `DRAFT-B` |
| Titolo | Ogni mutazione dello stato canonico è un'Action governata con `target=CANONICAL_COMMIT` prodotta da `C6` |
| Stato | `Proposed — awaiting change control` |
| Approval mode | Approvazione umana esplicita richiesta |
| Supersedes | Nessuna. Realizza `ARC-014` e precisa `DEC-084`, `DEC-142`, `DEC-143` |

**Decisione proposta.** L'ammissione di una Claim a `CanonicalAssertion`, le `MergeDecision` e `SplitDecision`, le ritrattazioni e ogni altra mutazione dello stato canonico percorrono la pipeline governata di §4.1 come `ActionType` con `target=CANONICAL_COMMIT`. `C6` è l'unico produttore della commit request; `C3` la accetta soltanto con `Decision` e `Authority ref` validi e coerenti con il `GatePackage` congelato. Non esiste un secondo percorso verso lo stato canonico.

**Razionale.** L'ADD v1.0 definiva la forma della commit request governata — l'input di `C3` include «Evidence, Decision e Authority ref» — ma non il percorso: nessun subsystem era incaricato di produrla, la FSM terminava soltanto in dispatch verso adapter esterno e il diagramma C4 L2 non aveva archi mutativi verso `C3`. Il ciclo Claim → `CanonicalAssertion`, richiesto da `FR-149` e `FR-150` e vincolato da `ARC-014`, era privo di control flow. La classe `R2_CONTROLLED` di §5.4 («mutazione interna reversibile e confinata, un approvatore umano indipendente») non era agganciata ad alcun flusso.

**Alternative considerate e scartate.** *(i)* Un secondo workflow separato per le mutazioni interne: raddoppierebbe guardie, audit e Human Gate, con rischio di divergenza fra i due percorsi. *(ii)* Ammissione diretta da `C5` guidata dagli eventi: incompatibile con `ARC-010` e con l'invariante 1 di §3.6, perché un broker non detiene Authority e non può fornire un `acceptedByDecision`.

**Contenuto normativo.** Regola 10 di §2.5; campo `target` e binding `canonical_commit_binding` nell'Action Type Contract §3.7; stato `CANONICAL_COMMIT_PENDING` e transizioni `ACT-T29`–`ACT-T31`; arco `C6`→`C3` in §2.1.

**Requisiti serviti.** `FR-002`, `FR-005`, `FR-012`, `FR-130`, `FR-149`, `FR-150`. **Vincoli.** `ARC-010`, `ARC-014`. **Rischi mitigati.** `RSK-017`, `RSK-042`.

**Criterio di verifica alla chiusura.** Un test negativo dimostra che nessun evento, adapter o agente può indurre una mutazione canonica senza `Decision` e `Authority ref`; il mission thread mostra la `CanonicalAssertion` con `acceptedFromClaim` e `acceptedByDecision` popolati e correlati a un Audit Record.

---

## `DRAFT-C` — Scope del single-writer e branch scope del relay outbox

| Campo | Valore |
|---|---|
| Slug provvisorio | `DRAFT-C` |
| Titolo | Esclusività di scrittura di `C3` limitata a `main`; overlay di scenario confinati all'adapter di `C7`; relay outbox vincolato a `main` |
| Stato | `Proposed — awaiting change control` |
| Approval mode | Approvazione umana esplicita richiesta |
| Supersedes | Nessuna. Disambigua `DEC-148` e precisa `ARC-007` |

**Decisione proposta.** L'esclusività di scrittura di `C3` sul ruolo `VersionedAssertedState` è limitata ai commit su `main` per ownership boundary. I branch di scenario sono scritti esclusivamente dall'adapter `ScenarioOverlayStore` interno a `C7`, che non possiede la capability `main.write` e non produce `OutboxEntry` pubblicabili. Il relay dell'outbox pubblica esclusivamente entry appartenenti al branch `main`; le entry replicate in un branch di scenario da `forkScenario` non sono pubblicabili, non generano `DeliveryAttempt` e sono ignorate dal reconciler.

**Razionale.** L'ADD v1.0 conteneva quattro affermazioni normative con due scope diversi: §2.4 diceva «Solo `C3`, per ownership boundary **e branch**», mentre §2.5.2, §2.2 (`C7`), `TB-CXT-07` e §4.2 limitavano coerentemente il vincolo a `main` e contemplavano esplicitamente l'overlay «tramite branch TerminusDB». La lettura restrittiva rendeva §4.2 inattuabile; quella permissiva lasciava indefinito chi possa scrivere su un branch non-`main` e se le entry di outbox replicate da un fork siano pubblicabili — con conseguente rischio di ripubblicazione di eventi canonici da un ramo di scenario.

**Contenuto normativo.** Cella «Write policy» di §2.4; regola 11 di §2.5; nodo `OVL` e arco `C7`→`OVL` in §2.1.

**Requisiti serviti.** `FR-154`, `FR-064`. **Vincoli.** `ARC-002`, `ARC-007`, `ARC-009`, `ARC-020`. **Rischi mitigati.** `RSK-044` (contaminazione del world model da output simulati), `RSK-021` (retry storm), `RSK-053`.

**Open issue non chiusi.** La scelta fra overlay su branch dello stesso store e store fisicamente separato resta una decisione di DDD vincolata da questa regola; `OI-020` non è toccata.

**Criterio di verifica alla chiusura.** Un tentativo di commit su `main` da un'identità di `C7` è negato e auditato; un `forkScenario` da un commit con outbox non pubblicate non produce alcun `DeliveryAttempt` aggiuntivo.

---

## `DRAFT-D` — Semantica direzionale del conservative join dei marking

| Campo | Valore |
|---|---|
| Slug provvisorio | `DRAFT-D` |
| Titolo | L'operatore di propagazione dipende dalla semantica del campo: unione per le restrizioni, intersezione per i permessi |
| Stato | `Proposed — awaiting change control` |
| Approval mode | Approvazione umana esplicita richiesta; classe `security authority` ai sensi di §5.4 |
| Supersedes | Nessuna. Corregge la formula di §5.3 dell'ADD v1.0; `DEC-126` resta invariata |

**Decisione proposta.** Nella propagazione a un derivato, i campi con semantica di restrizione — `caveats`, `mandatory_markings`, `dissemination_controls` — si combinano per **unione**; i campi con semantica di permesso — `permitted_purposes` — per **intersezione**; la classificazione per **join del reticolo**. Il `MarkingSchemeDefinition` dichiara esplicitamente la semantica di ciascuna famiglia e nessun default implicito è ammesso.

**Razionale.** L'ADD v1.0 prescriveva `Dissemination(d) = ⋂ᵢ Dissemination(xᵢ)` mentre il campo omonimo nello schema normativo si chiama `dissemination_controls`, cioè restrizioni. Con `x₁ = {NOFORN}` e `x₂ = {}`, l'intersezione produce `{}`: il derivato perde il controllo. Ne risultava una declassificazione silenziosa per derivazione, in contraddizione diretta con §1.4 («il marking derivato è il `conservative_join`»), con l'invariante 7 di §3.6 («marking non meno restrittivo del join degli input») e con il criterio di accettazione §7.2 «Marking non decresce». È un vettore di leakage cross-compartment su cache, explanation, embedding ed export.

**Contenuto normativo.** Formule di §5.3; rinomina di `SecurityContext.dissemination_rules[]` in `dissemination_controls[]`; campi `caveat_semantics` e `dissemination_control_semantics` nel `MarkingSchemeDefinition`.

**Requisiti serviti.** `FR-131`, `FR-132`. **Vincoli.** `ARC-016`. **Rischi mitigati.** `RSK-006`, `RSK-020`, `RSK-035`, `RSK-041`, `RSK-049`.

**Criterio di verifica alla chiusura.** Golden test di propagazione: un derivato da input con controlli di disseminazione disgiunti conserva l'unione dei controlli; nessun derivato risulta meno restrittivo di un qualsiasi input in nessuna delle quattro famiglie.

---

## `DRAFT-E` — Punto di valutazione delle guardie di emissione

| Campo | Valore |
|---|---|
| Slug provvisorio | `DRAFT-E` |
| Titolo | Emergency stop, fencing e disponibilità dell'audit sono rivalutati al momento dell'emissione, non alla creazione del command |
| Stato | `Proposed — awaiting change control` |
| Approval mode | Approvazione umana esplicita richiesta; classe `safety` |
| Supersedes | Nessuna. Precisa `DEC-132` e realizza `NFR-047` |

**Decisione proposta.** `G-DISPATCH` include lo `stop_epoch` corrente e la disponibilità dell'audit append durevole, ed è rivalidata al momento dell'emissione in `ACT-T14`, `ACT-T19` e `ACT-T29`, non soltanto alla transizione a `COMMAND_READY`. Lo `stop_epoch` al momento della creazione del command entra nella tupla `ActionInstance` e nell'effetto durevole di `ACT-T12`. `ACT-T23` ha precedenza esplicita su `ACT-T14` e `ACT-T29`.

**Razionale.** Nell'ADD v1.0 `G-DISPATCH` conteneva «Emergency stop inattivo» ma era valutata a `ACT-T12`; la transizione che emette realmente, `ACT-T14`, era guardata soltanto da «Command non scaduto», con `predispatch_fence_ttl = PT30S`. Esisteva quindi una finestra fino a trenta secondi in cui un command già pronto poteva raggiungere l'adapter dopo l'attivazione dell'emergency stop, senza alcuna rivalutazione: il target di contenimento `≤10 s` di `NFR-047` non era garantito dalla tabella normativa, e `ACT-T23` («prima del dispatch») non serializzava contro un relay concorrente. Parallelamente, nessuna guardia includeva la disponibilità dell'audit, che §5.1 e §6.3 rendono fail-closed per il dispatch.

**Contenuto normativo.** `G-DISPATCH` in §4.1.1; guardie di `ACT-T14`, `ACT-T19`, `ACT-T29`; effetto durevole di `ACT-T12`; tupla `ActionInstance`; regola di precedenza di `ACT-T23`.

**Requisiti serviti.** `FR-138`, `FR-139`, `FR-162`. **Vincoli.** `ARC-014`. **Rischi mitigati.** `RSK-037` (escalation di privilegi durante crisi), `RSK-054`.

**Open issue non chiusi.** `OI-018` (budget numerico di revoca) resta aperto: questa decisione fissa il **punto** di valutazione, non le soglie.

**Criterio di verifica alla chiusura.** Chaos/safety drill: nessun command accettato oltre il target `≤10 s` misurato dall'accettazione locale dell'evento firmato; un command in stato `COMMAND_READY` al momento dello stop non raggiunge l'adapter.

---

## `DRAFT-F` — Disposizione terminale degli esiti esterni indeterminati

| Campo | Valore |
|---|---|
| Slug provvisorio | `DRAFT-F` |
| Titolo | `EXECUTION_UNKNOWN` e `COMPENSATION_UNKNOWN` non risolti entro il deadline transitano in stati terminali di escalation e bloccano nuove azioni sullo stesso bersaglio |
| Stato | `Proposed — awaiting change control` |
| Approval mode | Approvazione umana esplicita richiesta; classe `safety` |
| Supersedes | Nessuna. Completa `DEC-169` e realizza `FR-163` |

**Decisione proposta.** Alla scadenza del `reconciliation_deadline` senza evidenza positiva, `EXECUTION_UNKNOWN` transita in `EXECUTION_INDETERMINATE` e `COMPENSATION_UNKNOWN` in `COMPENSATION_INDETERMINATE`: stati terminali che congelano retry e compensation automatiche e aprono un'escalation obbligatoria al Human Gate. `G-FRESHNESS` include la condizione che nessun effetto esterno indeterminato insista sullo stesso `aggregate_ref` e sullo stesso target esterno.

**Razionale.** L'ADD v1.0 fissava un `reconciliation deadline` di `PT15M` ma non definiva alcuna transizione alla sua scadenza: `ACT-T20` e `ACT-T21c` ammettevano l'esito «resta unknown» e il grafo della FSM confermava che gli unici archi uscenti richiedevano evidenza positiva. Un'`ActionInstance` poteva quindi restare indefinitamente indeterminata senza responsabile. Inoltre nessuna guardia impediva di dispacciare una seconda azione sullo stesso aggregate mentre la prima era irrisolta: `G-FRESHNESS` confrontava soltanto stati interni — revisione attesa, commit, policy digest, watermark — ciechi rispetto a un effetto esterno ignoto. Era esattamente lo scenario di `RSK-023`, dichiarato mitigato da «idempotency, fencing, confirmation event e reconciliation» senza che nulla impedisse la seconda proposta.

**Contenuto normativo.** Stati `EXECUTION_INDETERMINATE` e `COMPENSATION_INDETERMINATE`; transizioni `ACT-T24` e `ACT-T25`; condizione aggiuntiva di `G-FRESHNESS`; codici `EXECUTION_INDETERMINATE` e `COMPENSATION_INDETERMINATE` nell'Action Type Contract.

**Requisiti serviti.** `FR-163`, `FR-158`, `FR-155`. **Vincoli.** `ARC-011`, `ARC-014`. **Rischi mitigati.** `RSK-023` (doppia esecuzione), `RSK-050` (azione conflittuale su stato obsoleto), `RSK-054`.

**Open issue non chiusi.** `OI-017` e `OI-019` restano aperti: la durata del deadline è un valore candidato, non fissato da questa decisione.

**Criterio di verifica alla chiusura.** Failure injection: nessuna `ActionInstance` resta priva di stato terminale oltre il deadline; un tentativo di nuova azione su un aggregate con effetto irrisolto è negato con reason code e auditato.

---

## `DRAFT-G` — Contrattualizzazione normativa di `ACTION` ed `EVENT`

| Campo | Valore |
|---|---|
| Slug provvisorio | `DRAFT-G` |
| Titolo | Tutti e sei i `ContractDefinition.kind` ricevono un contratto normativo generato dalla Canonical IR |
| Stato | `Proposed — awaiting change control` |
| Approval mode | Approvazione umana esplicita richiesta |
| Supersedes | Nessuna. Completa `DEC-053`, `DEC-092`–`DEC-096` |

**Decisione proposta.** `ACTION` ed `EVENT` ricevono contratti normativi con la stessa fedeltà degli altri kind: `action-type-contract:1.0` e `event-subscription-contract:1.0`, entrambi generati dalla Canonical IR e privi di dialect, offset fisici e identificativi di backend.

**Razionale.** L'ADD v1.0 dichiarava sei kind in §3.1.1 e ne contrattualizzava quattro. `G-CONTRACT` richiedeva però che un `ActionType` dichiarasse «effect_class, risk_class, timeout, retry, idempotency, compensabilità e irreversibilità» — campi di un contratto che il documento non definiva — e §4.1.3 stabiliva che «il compilatore rifiuta un `ActionType` privo di timeout espliciti». L'asimmetria era interna: il contratto meno critico per la safety, `MCP_TOOL`, era specificato al massimo dettaglio, quello più critico non esisteva. Per `EVENT`, `C1` generava AsyncAPI e `C5` esponeva il port `Subscribe`, ma nessun contratto pubblico di sottoscrizione era specificato, benché `FR-016` (P0) richieda subscription e change feed derivati dalla Canonical IR.

**Contenuto normativo.** §3.7 e §3.8 dell'ADD v1.1; rinumerazione della precedente §3.7 «Conformance target» in §3.9.

**Requisiti serviti.** `FR-016`, `FR-031`–`FR-033`, `FR-075`–`FR-083`, `FR-148`. **Vincoli.** `ARC-004`, `ARC-014`. **Capability.** `CAP-009`–`CAP-011`. **Rischi mitigati.** `RSK-013`, `RSK-021`, `RSK-058`.

**Criterio di verifica alla chiusura.** Il compilatore rifiuta un `ActionType` privo anche di un solo timeout, con quorum vuoto su `R2_CONTROLLED` o `R3_HIGH_IMPACT`, o con `IRREVERSIBLE` e compensation dichiarata; un consumer di change feed non riceve mai offset, topic o identificativi di broker.

---

## `DRAFT-H` — Metamodello dello schema di marking

| Campo | Valore |
|---|---|
| Slug provvisorio | `DRAFT-H` |
| Titolo | `MarkingSchemeDefinition` come costrutto OaC che dichiara reticolo, semantica dei campi e regola di join |
| Stato | `Proposed — awaiting change control` |
| Approval mode | Approvazione umana esplicita richiesta; classe `security authority` |
| Supersedes | Nessuna. Rende calcolabile `DEC-126` |

**Decisione proposta.** Un nuovo costrutto OaC `MarkingSchemeDefinition` dichiara `levels[]` ordinati, `dominance_relation`, `caveat_semantics`, `dissemination_control_semantics`, `join_rule`, `incomparable_behavior` e `declassification_authority_ref`. In assenza di uno scheme attivo e risolvibile, la classificazione di un derivato non è calcolabile e la richiesta è negata.

**Razionale.** L'ADD v1.0 prescriveva `Classification(d) = ⊔ᵢ Classification(xᵢ)` e un `conservative_join`, entrambi dipendenti da un reticolo che nessun contratto definiva: `marking.labels` era un array di stringhe non ordinato con `uniqueItems`, e §3.1.1 non conteneva alcun costrutto che dichiarasse l'ordinamento parziale, l'elemento massimo o la regola di join. `SecurityContext` introduceva una terza forma ancora, con `classification_level` e `caveats[]`. Il criterio di accettazione §7.2 «Marking non decresce» non era quindi verificabile, perché «decrescere» non era definito. `OI-021` governa la **tassonomia nazionale** — quali livelli, quali caveat, quali regole di disseminazione — non l'**algebra** che li combina, che è una questione di metamodello e appartiene all'ADD.

**Contenuto normativo.** Riga `MarkingSchemeDefinition` in §3.1.1; §3.0.2 sulla forma unica del marking; riformulazione di §5.3.

**Requisiti serviti.** `FR-131`, `FR-132`. **Vincoli.** `ARC-016`. **Rischi mitigati.** `RSK-006`, `RSK-020`, `RSK-035`.

**Open issue non chiusi.** `OI-021` resta **aperta e invariata**: il contenuto della tassonomia è configurato dall'authority competente. Questa decisione fornisce soltanto la struttura che rende quella configurazione esprimibile e verificabile.

**Criterio di verifica alla chiusura.** Su una fixture di `MarkingSchemeDefinition`, il join è calcolabile, monotono e riproducibile; due label incomparabili producono il comportamento dichiarato da `incomparable_behavior` e mai una postura permissiva.

---

## `DRAFT-I` — Capability Lease come controllo distinto da `ELM-080`

| Campo | Valore |
|---|---|
| Slug provvisorio | `DRAFT-I` |
| Titolo | Il Capability Lease è un controllo di sicurezza attivo nel PoC, distinto dalla `ResourceReservation/Lease` differita |
| Stato | `Proposed — awaiting change control` |
| Approval mode | Approvazione umana esplicita richiesta; classe `safety` |
| Supersedes | Nessuna. Precisa `DEC-132` e `DEC-133` |

**Decisione proposta.** Il `CapabilityLease` è definito come costrutto distinto — `lease_id`, `capability_id`, `principal_id`, `delegation_ref`, `stop_epoch`, `fencing_token`, `issued_at`, `expires_at ≤ PT5S` — attivo nel profilo PoC. Non è la `ResourceReservation/Lease` di `ELM-080`, che resta differita, né il `writer_epoch` fencing di `C3`. Il target di contenimento `≤10 s` dipende esclusivamente dal `CapabilityLease` e dalla revoca push, meccanismi indipendenti.

**Razionale.** L'ADD v1.0 fondava la contenzione dell'emergency stop su «una capability lease con `stop_epoch` corrente e TTL non superiore a 5 secondi» presentata da ogni chiamata mutativa, mentre §4.3.1.9 e §7.1 dichiaravano che nel PoC si usano «budget senza lease» perché `ELM-080` è differito, e §2.2 introduceva un terzo uso, «writer lease», senza definire nessuno dei tre. O il meccanismo di enforcement di un controllo di safety dipendeva da un elemento differito — scope leakage — o il documento usava lo stesso termine in tre accezioni non definite su un percorso critico. In entrambi i casi `NFR-047` non era implementabile senza una decisione implicita.

**Contenuto normativo.** Blocco `CapabilityLease` in §5.2; nota di disambiguazione dei tre usi; riformulazione dell'invariante 9 di §4.3.1 e della riga `ELM-080` di §7.1; rinomina di «writer lease» in «`writer_epoch` fencing» in §2.2.

**Requisiti serviti.** `FR-138`, `FR-140`. **Vincoli.** `ARC-014`, `ARC-015`. **Rischi mitigati.** `RSK-037`, `RSK-038`.

**Open issue non chiusi.** `ELM-080` resta **differito e invariato**; `OI-018` resta aperto sulle soglie numeriche di revoca.

**Criterio di verifica alla chiusura.** Un drill di emergency stop dimostra che la scadenza locale del `CapabilityLease` contiene le chiamate mutative anche con la revoca push disabilitata, e che nessuna funzionalità differita di `ELM-080` è richiesta dal percorso.

---

## Nota finale di governance

Le nove bozze sono indipendenti soltanto in apparenza. `DRAFT-B` presuppone `DRAFT-G`, perché la mutazione canonica è modellata come `ActionType` e richiede quindi il contratto `ACTION`. `DRAFT-D` presuppone `DRAFT-H`, perché la direzione dell'operatore è dichiarata dal `MarkingSchemeDefinition`. `DRAFT-E` e `DRAFT-F` agiscono sulla stessa tabella di transizioni e vanno valutate insieme. Un'approvazione parziale che accolga `DRAFT-B` senza `DRAFT-G`, o `DRAFT-D` senza `DRAFT-H`, lascerebbe l'ADD in uno stato meno coerente di quello attuale.

Nessuna di queste voci è approvata. Nessun identificativo è assegnato. Lo stato probatorio resta `E1=0`, `E2=0`, zero requisiti `Verified`.
