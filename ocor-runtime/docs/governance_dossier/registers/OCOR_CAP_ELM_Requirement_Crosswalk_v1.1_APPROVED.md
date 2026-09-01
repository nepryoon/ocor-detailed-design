# OCOR — CAP/ELM Requirement Crosswalk v1.1 — APPROVED ADD v1.3

> **Snapshot autoritativo promosso atomicamente da `DEC-208` con efficacia 2026-09-01.** Deriva dal candidato `reports/governance_candidates/OCOR_CAP_ELM_Requirement_Crosswalk_v1.1_FULL_MEMORY_CANDIDATE.md`, ancorato ai registri approvati di `main@098c680615cf8d8b57cd367386bac10d8acdc715`. La promozione riguarda il design `ELM-084 = CORE/P0/PoC`; preserva `E1=0`, `E2=0`, zero requisiti globalmente `Verified`, `E1_runtime_slice=PRESENT` confinato a `DEC-207` e il runtime full-memory `NO-GO` fino alla chiusura governata di `FGM-01`–`FGM-20`.
# OCOR — CAP/ELM Requirement Crosswalk v1.0 — APPROVED ADD v1.2

> **Snapshot derivato e autoritativo per ADD v1.2.** Generato il 2026-08-30 dal sorgente immutabile `inputs/normative/OCOR_CAP_ELM_Requirement_Crosswalk_v0.9.md` mediante change control `ocor-runtime/docs/governance_dossier/ARA_DECISION_RECORD_v1.1.md`. Le modifiche normative sono limitate alle decisioni `DEC-197`–`DEC-206`; per ogni altro contenuto prevale semanticamente il sorgente incorporato qui sotto.

# OCOR — Crosswalk capacità/elementi verso requisiti effettivi

**Sorgente delle righe:** `work/coverage_matrices.md`  
**Sorgenti dei requisiti:** `requirements_2_4.md`, `requirements_5_6.md`, `requirements_7_10.md`, `requirements_11_13.md`, `requirements_14_17.md`  
**Stato:** crosswalk di integrazione con ID temporanei; gli ID saranno rinumerati soltanto durante il merge globale controllato.  
**Regola:** ogni riga `CAP-*` ed `ELM-*` è associata ad almeno un requisito `BR-*`, `FR-*` o `NFR-*` realmente presente nei registri di fase. La mappatura esprime copertura di requisito, non evidenza di conformità né parità già raggiunta.

## A. Capability coverage — CAP-001–CAP-026

| ID | Capacità | Requisiti effettivi associati | Razionale della mappatura |
|---|---|---|---|
| `CAP-001` | Governance della baseline | `FR-014`, `FR-020`, `NFR-010`, `NFR-093` | Congela la baseline Palantir, impone una matrice atomica, definisce l’evidenza minima per lo stato Verified e conserva l’evidence package di release. |
| `CAP-002` | Risorse di schema | `FR-015`, `FR-024`, `FR-040`, `FR-043`, `NFR-018` | Copre equivalenza semantico-funzionale, primitive di schema nella IR, sorgente OaC, generazione backend e build deterministica. |
| `CAP-003` | Sistema dei tipi delle Property | `FR-024`, `FR-042`, `FR-043`, `NFR-019` | Il type system canonico, il type checker e i generatori coprono famiglie e vincoli; il fail-closed impedisce degradazioni non dichiarate. |
| `CAP-004` | Object, Link e stato corrente | `FR-025`, `FR-053`, `FR-062`, `FR-064`, `NFR-024` | Identità stabile, ammissione governata, concorrenza, projector idempotenti e disclosure del watermark definiscono il current state osservabile. |
| `CAP-005` | Mapping e proiezioni | `FR-043`, `FR-064`, `FR-065`, `FR-168`, `NFR-084` | Generazione mapping, projection idempotente, reconciliation/rebuild e boundary W3C con conformance degli adapter coprono l’intero percorso. |
| `CAP-006` | Object Set e query | `FR-027`, `FR-055`, `FR-057`, `FR-016`, `NFR-071` | Meta-modello di query, contratti tipizzati, consistency token, contratti derivati dalla IR e SLO bounded coprono funzione e qualità del query path. |
| `CAP-007` | Function | `FR-027`, `FR-058`, `NFR-025`, `FR-059` | Distingue Function e inferenza, registra firme/effetti, applica sandbox e obbliga una Function-backed Action per le mutazioni. |
| `CAP-008` | Model e deployment | `FR-060`, `FR-061`, `FR-086`, `FR-087` | Registry/version pinning e divieto di promozione implicita coprono Model/Deployment; i contratti analitici e l’etichetta epistemica classificano gli output. |
| `CAP-009` | Action e autorizzazione | `FR-031`, `FR-077`, `FR-078`, `FR-079`, `NFR-029`, `FR-162` | La pipeline tipizzata, la rivalidazione, il calcolo del Human Gate, il divieto di bypass e il controllo pre-dispatch realizzano Action governate. |
| `CAP-010` | Transaction e affidabilità | `FR-032`, `FR-062`, `FR-080`, `FR-081`, `FR-163` | Copre transaction/outbox/Saga, idempotenza, retry/compensation, fencing e gestione fail-safe degli esiti esterni ambigui. |
| `CAP-011` | Automation e workflow | `FR-032`, `FR-084`, `FR-085`, `FR-072` | Workflow/lifecycle, trigger/run e automazioni mutative governate sono supportati da replay deterministico degli eventi. |
| `CAP-012` | Sicurezza e classificazione | `FR-037`, `FR-006`, `FR-130`, `FR-131`, `NFR-040`, `NFR-041` | Il modello di governance, la compartimentazione, la Policy Decision uniforme, la propagazione dei marking e i test di non-leakage/isolamento coprono la capability. |
| `CAP-013` | Norme, autorità e privacy | `FR-002`, `FR-037`, `FR-112`, `FR-113`, `FR-135` | Authority per concern, Policy/Norm/Delegation, divieto di authority derivata dal contenuto e lifecycle/residency dei dati coprono governance e privacy. |
| `CAP-014` | Audit e view | `FR-134`, `NFR-043`, `FR-166`, `FR-167` | Audit end-to-end e tamper evidence sono affiancati da viste del mission thread e strumenti role-oriented soggetti alle policy. |
| `CAP-015` | Evidenza ed epistemica a livello di Assertion | `FR-028`, `FR-029`, `FR-007`, `FR-149`, `NFR-054` | Bitemporalità, Evidence/Provenance, query evidence-backed e lineage claim-to-outcome garantiscono conoscenza tracciata e riproducibile. |
| `CAP-016` | Identity Resolution | `FR-030`, `FR-012`, `NFR-055` | Il modello reversibile, il comportamento fail-safe e la reversibilità di identity/adjudication coprono risoluzione, merge e split. |
| `CAP-017` | Constraint e inferenza spiegabile | `FR-027`, `NFR-013`, `FR-053`, `FR-087` | Constraint, Inference Rule, Proof Graph ed execution owner unico sono collegati all’ammissione dello stato e all’etichetta epistemica degli output. |
| `CAP-018` | Scenario e branching | `FR-035`, `NFR-015`, `FR-066`, `FR-154`, `FR-092`, `NFR-032` | World/Scenario, pinning e isolamento sono completati da time travel, lineage e separazione branch di governance/scenario. |
| `CAP-019` | Inferenza causale e Intervention | `FR-034`, `FR-088`, `FR-090`, `FR-091`, `FR-094`, `FR-095`, `FR-096`, `FR-098`, `NFR-030` | Manifest, identify-or-abstain, do(X), separazione Action/Intervention, validity envelope e integrità coprono il runtime causale. FR-095 e la capacità controfattuale AAP sono P0/MVP per DEC-205 e non sono rivendicate nel PoC. |
| `CAP-020` | Agenti e tool governati | `FR-038`, `FR-047`, `FR-106`, `FR-108`, `FR-110`, `FR-124`, `NFR-036` | Meta-modello agentico, MCP/SDK, identità, Tool Contract, autonomy tier, trace e kill switch coprono governo e osservabilità degli agenti. |
| `CAP-021` | Lifecycle e conformità OaC | `FR-040`, `FR-041`, `FR-042`, `FR-043`, `FR-045`, `FR-046`, `FR-050`, `FR-051`, `NFR-018`, `NFR-021` | Copre DSL/IR, package, compiler, generatori, diff/migration, release fence, CLI/CI, conformance, riproducibilità e firma. |
| `CAP-022` | API, SDK, subscription e tool | `FR-044`, `FR-047`, `NFR-022`, `FR-055`, `FR-069`, `FR-073`, `FR-169` | Contratti API/eventi generati, SDK/MCP coerenti, query tipizzate, event envelope, compatibility policy e formati interoperabili coprono tutte le superfici. |
| `CAP-023` | Osservabilità semantica | `FR-051`, `NFR-068`, `NFR-069`, `NFR-077` | Conformance/drift evidence, anti-drift operativo, osservabilità tecnica/semantica e consistenza osservabile coprono health e diagnostica. |
| `CAP-024` | Deployment, resilienza e operatività disconnessa | `NFR-059`, `NFR-060`, `NFR-061`, `NFR-062`, `NFR-064`, `NFR-065`, `NFR-071`, `NFR-072`, `NFR-074`, `NFR-078`, `NFR-079` | I profili sovrani/air-gap, sync osservabile, deployment ripetibile, HA/recovery, classi di workload, scaling per celle e degradazione sicura coprono il ciclo operativo. |
| `CAP-025` | OSS, licensing e supply chain | `NFR-086`, `NFR-087`, `NFR-073`, `NFR-021`, `NFR-044` | Trasparenza e sostenibilità delle dipendenze, gate licenza/capability, release firmate e assurance offline coprono il rischio legale e tecnico. |
| `CAP-026` | Ampiezza completa Foundry/AIP/Apollo | `BR-013`, `FR-021`, `NFR-050`, `NFR-089` | Profili per release e claim automaticamente circoscritti rendono esplicita l’esclusione dello stack completo e impediscono claim operativi o di parità eccessivi. |

## B. Ontology element coverage — ELM-001–ELM-103

| ID | Elemento | Requisiti effettivi associati | Razionale della mappatura |
|---|---|---|---|
| `ELM-001` | Ontology | `FR-024`, `FR-040` | Ontology è una Definition canonica rappresentata nella IR e authorata tramite OaC. |
| `ELM-002` | Namespace, Module, Package | `FR-024`, `FR-041` | La semantica di base è nella IR; modularità, package e dipendenze sono gestiti dal resolver OaC. |
| `ELM-003` | Object Type e Object | `FR-024`, `FR-053` | Il meta-modello rappresenta Definition/Instance e il runtime governa l’ammissione dello stato canonico. |
| `ELM-004` | Primary Key e Title Key | `FR-025` | Il requisito distingue le chiavi di dominio dagli ID stabili e dai mapping backend. |
| `ELM-005` | Stable Resource ID | `FR-025`, `NFR-012` | Stable ID è obbligatorio e gli ID interni dei backend non possono attraversare i confini. |
| `ELM-006` | Property e Property Value | `FR-024` | Entrambi sono parte esplicita del type system e della Canonical IR. |
| `ELM-007` | Scalar base types, UUID, Duration e Binary | `FR-024`, `FR-042` | La famiglia è rappresentata nella IR e verificata staticamente dal type checker. |
| `ELM-008` | Array, Set e Map | `FR-024`, `FR-042` | I container canonici sono definiti e sottoposti a capability classification per backend. |
| `ELM-009` | Struct/Record, Enum e Codelist | `FR-024`, `FR-042` | Tipi strutturati e vocabolari controllati sono coperti dal modello canonico e dalla validazione. |
| `ELM-010` | Geopoint, Geoshape e Geotemporal Value | `FR-024`, `FR-042` | I tipi geospaziali/geotemporali sono inclusi nelle famiglie ratificate e nei test di portabilità. |
| `ELM-011` | Vector | `FR-024`, `NFR-019` | Vector resta nel catalogo tipizzato; eventuale backend unsupported è fail-closed e tracciato. |
| `ELM-012` | Attachment e Media Reference | `FR-024`, `FR-029` | Il riferimento media è tipizzato e la provenienza del relativo artefatto è collegabile alle Assertion. |
| `ELM-013` | Time Series e Geotemporal Series Reference | `FR-024`, `FR-043` | Il riferimento è canonico mentre mapping e target di proiezione sono generati. |
| `ELM-014` | Unit of Measure e Quantity Type | `FR-024`, `FR-042` | Unità e quantità sono tipi semantici validati, non stringhe libere. |
| `ELM-015` | Secret, Cipher e Sensitive Reference | `FR-024`, `FR-133`, `NFR-042` | Il tipo espone solo riferimenti governati; materiale segreto e chiavi restano fuori dall’ontologia e cifrati. |
| `ELM-016` | Value Type e Shared Property Type | `FR-024` | Entrambi sono Definition riutilizzabili del type system canonico. |
| `ELM-017` | Derived/Computed Property e Property Reducer | `FR-027`, `NFR-013` | Le derivazioni sono rappresentate esplicitamente e assegnate a un execution owner unico. |
| `ELM-018` | Metric e KPI Definition | `FR-027`, `FR-036` | Metric/KPI sono definizioni calcolabili collegate a obiettivi, setpoint e valutazione delle alternative. |
| `ELM-019` | Link Type e Link | `FR-026` | Definition e Instance delle relazioni binarie sono separate dalle relazioni causali. |
| `ELM-020` | Qualified e N-ary Relation | `FR-026` | Il requisito conserva ruoli, cardinalità, proprietà ed evidenza proprie della relazione. |
| `ELM-021` | Interface | `FR-026`, `FR-015` | Interface è parte del meta-modello e del profilo di equivalenza semantico-funzionale. |
| `ELM-022` | Object Type Group, Tag e Taxonomy | `FR-026`, `FR-039` | Organizzazione semantica e metadata di lifecycle restano governati e tracciati. |
| `ELM-023` | Object Set, Query e Saved View | `FR-027`, `FR-055` | Query e Object Set sono modellati e resi disponibili tramite contratti tipizzati vendor-neutral. |
| `ELM-024` | Action Type | `FR-031`, `FR-077` | Action Type è una Definition della pipeline mutativa uniforme. |
| `ELM-025` | Action Submission, Execution e Result | `FR-031`, `FR-033`, `FR-075`, `FR-076` | Submission, execution e result sono distinti, correlati e separati dall’Outcome. |
| `ELM-026` | Action Parameter, Rule ed Edit Specification | `FR-031`, `FR-077` | Parametri, regole ed edit plan sono parti tipizzate della Action governata. |
| `ELM-027` | Submission Criteria e Precondition | `FR-031`, `FR-077`, `FR-078` | Criteria/precondition sono valutati nella pipeline e rivalidati prima del comando. |
| `ELM-028` | Side Effect, Webhook ed External Command | `FR-031`, `FR-082`, `FR-083`, `FR-163` | Adapter mapping, stati esterni ed esiti ambigui rendono governabili side effect e webhook. |
| `ELM-029` | Function e Function-backed Action | `FR-027`, `FR-058`, `NFR-025`, `FR-059` | Copre metadati, sandbox e divieto di mutazione fuori dalla Function-backed Action. |
| `ELM-030` | Model, Deployment e Model Function | `FR-060`, `FR-061` | Registry, deployment/version pinning e mancata promozione implicita governano il lifecycle del modello. |
| `ELM-031` | Automation, Trigger, Schedule e Run | `FR-084`, `FR-085` | Trigger, schedule e Automation Run sono tipizzati; ogni mutazione rientra nella pipeline governata. |
| `ELM-032` | Workflow e Process Definition | `FR-032`, `FR-080` | Workflow/Process sono profili durevoli con policy esplicite di retry, timeout e compensation. |
| `ELM-033` | Lifecycle e State Machine Type | `FR-032`, `FR-063` | Il meta-modello include lifecycle/state machine e il runtime applica transizioni uniformi. |
| `ELM-034` | Change Set, Transaction e Transaction Record | `FR-032`, `FR-062` | Transaction e Change Set sono governati da revision, idempotency e invariant check. |
| `ELM-035` | Saga e Compensation | `FR-032`, `FR-080` | Il profilo di affidabilità dell’Action definisce condizioni e semantica delle compensation. |
| `ELM-036` | Transactional Outbox e Delivery Attempt | `FR-032`, `FR-064`, `FR-072` | Outbox e delivery sono proiettati idempotentemente e recuperabili tramite replay. |
| `ELM-037` | Execution Record, Result, Outcome e Trace | `FR-033`, `FR-075`, `FR-076`, `FR-011` | Correlation, distinzione result/outcome e replay audit coprono il lineage di esecuzione. |
| `ELM-038` | SimulationResult | `FR-035`, `FR-093` | Il record è first-class, immutabile, versionato e contiene output, uncertainty e lineage. |
| `ELM-039` | ActionIntent, ActionCommand ed External Command | `FR-031`, `FR-078`, `FR-082`, `FR-105` | Le tre fasi sono distinte, rivalidate e tradotte dall’adapter senza promozione automatica. |
| `ELM-040` | Principal Type e Principal | `FR-037`, `FR-129` | Principal è parte del meta-modello e ogni identità umana/machine è individuale e auditabile. |
| `ELM-041` | Organization, Domain, Tenant e Compartment | `FR-037`, `FR-006`, `NFR-041` | I confini federati sono modellati e sottoposti a compartimentazione e isolamento risk-tiered. |
| `ELM-042` | Security Role, Group e Permission | `FR-037`, `FR-001`, `FR-130` | Ruoli distinti e Policy Decision uniforme coprono autorizzazioni e responsabilità. |
| `ELM-043` | Access Policy, Granular Policy e Policy Decision | `FR-037`, `FR-130`, `NFR-040` | Policy e decisioni sono first-class e applicate centralmente senza leakage. |
| `ELM-044` | Object, Property, Link e Relation Security Policy | `FR-037`, `FR-130`, `NFR-040` | Le policy coprono tutte le granularità e i risultati derivati, non soltanto le ACL dei datastore. |
| `ELM-045` | Marking, Classification, Dissemination, Mandatory Control e CBAC | `FR-037`, `FR-131`, `FR-006` | Propagazione conservativa e compartimentazione uniforme rendono obbligatori i controlli di classificazione. |
| `ELM-046` | Action Authorization | `FR-037`, `FR-079`, `FR-136`, `FR-137` | Authorization e risk class calcolano Human Gate e dual control prima delle Action critiche. |
| `ELM-047` | Declassification e Sanitization | `FR-131`, `FR-132` | I marking sono propagati e la riduzione di sensibilità crea un nuovo artefatto con authority e trace. |
| `ELM-048` | Policy, Norm, Authority Rule, Authority e Delegation | `FR-037`, `FR-002`, `FR-112`, `FR-113`, `FR-130` | Meta-modello, authority per concern, schema di delegation e policy decision uniforme coprono tutta la catena. |
| `ELM-049` | Purpose, Legal Basis, Consent, Retention e Legal Hold | `FR-037`, `FR-135` | Il profilo privacy è rappresentato e applicato tramite policy di lifecycle/residency. |
| `ELM-050` | Audit Record, Action Log ed Edit History | `FR-033`, `FR-134`, `NFR-043` | Audit completo e integrità hash-linked coprono record operativi e storia delle modifiche. |
| `ELM-051` | Object View, Dashboard e Operational Hub | `FR-166`, `FR-167` | Vista del mission thread e strumenti role-oriented costituiscono le viste operative governate. |
| `ELM-052` | Semantic Metadata, Documentation e Ownership | `FR-039`, `FR-143`, `NFR-082` | Metadata/lifecycle, ownership federata e conformance kit coprono documentazione e responsabilità. |
| `ELM-053` | Valid Time, Transaction/System Time e bitemporalità | `FR-028`, `FR-066` | Il meta-modello bitemporale e il runtime di time travel rendono interrogabili entrambi gli assi. |
| `ELM-054` | Proposition, Assertion, Claim e varianti | `FR-028`, `FR-053`, `FR-054` | Le classi epistemiche sono distinte; acceptance e adjudication sono tracciate prima dello stato canonico. |
| `ELM-055` | Event Type ed Event | `FR-028`, `FR-069` | Event è distinto dallo stato e viaggia in un envelope canonico versionato. |
| `ELM-056` | Observation e Measurement | `FR-028`, `FR-013` | Il modello epistemico e il dataset sintetico versionato coprono osservazioni, misure e ground truth. |
| `ELM-057` | Evidence ed Evidential Support | `FR-029`, `FR-007` | Evidence è collegata alla singola Assertion ed è interrogabile con supporto/confutazione e citazioni. |
| `ELM-058` | Provenance, Source e Reliability Assessment | `FR-029`, `FR-149` | La provenance per Assertion è collegata al lineage claim-to-outcome. |
| `ELM-059` | Belief e Uncertainty Descriptor | `FR-028`, `FR-097` | Stato epistemico e uncertainty descriptor tipizzato preservano metodo, intervalli e propagazione. |
| `ELM-060` | Truth Status, Conflict e Adjudication | `FR-028`, `FR-030`, `FR-054`, `FR-150` | Conflitto, adjudication e acceptance sono espliciti, reversibili e auditabili. |
| `ELM-061` | Source Identity, Canonical Entity, Candidate Match, Resolution Assertion e merge/split | `FR-030`, `FR-012`, `NFR-055` | Copre modello, comportamento fail-safe e reversibilità completa di resolution/merge/split. |
| `ELM-062` | Constraint, Invariant, Validation Result e Violation | `FR-027`, `FR-053`, `FR-077` | Constraint e validation sono modellati e applicati all’ammissione dello stato e alla pipeline Action. |
| `ELM-063` | Inference Rule, Derived Assertion, Proof Graph e Truth Maintenance | `FR-027`, `NFR-013` | Inferenza e prova sono first-class e ogni derivazione ha un owner unico, quindi è ritirabile senza doppia esecuzione. |
| `ELM-064` | Semantic Regime, World Assumption e Completeness Statement | `FR-028`, `FR-027`, `FR-055` | Il regime epistemico è esplicito nel modello e nei contratti di query. |
| `ELM-065` | Causal Variable, Edge e Mechanism | `FR-034`, `FR-088`, `FR-089` | Manifest causale e separazione Link/Causal Edge coprono variabili, archi e meccanismi. |
| `ELM-066` | Causal Model, Assumption e ruoli causali | `FR-034`, `FR-088`, `FR-098` | Il modello registra assumption set, ruoli, versione e validity envelope runtime. |
| `ELM-067` | Causal Query, Estimand, Identification, Estimator, Effect e Diagnostics | `FR-034`, `FR-090`, `FR-091` | Identify-or-abstain e stati espliciti garantiscono query/estimand e diagnostics verificabili. |
| `ELM-068` | Causal Intervention Specification e Operational Intervention Plan | `FR-034`, `FR-094`, `FR-096` | do(X) e distinzione Intervention/Action preservano semantica causale e piano operativo. |
| `ELM-069` | World, Scenario Definition, Scenario e Baseline | `FR-035`, `FR-092`, `NFR-032` | Version pinning e isolamento rendono World/Scenario riproducibili e separati da `main`. |
| `ELM-070` | Counterfactual Query e Result | `FR-035`, `FR-095` | Differito fuori dal PoC; copertura FR-095 attiva in MVP via DEC-205. Il runtime applica abduction–action–prediction soltanto quando il profilo è attivato. |
| `ELM-071` | Simulation Experiment, Run, Trajectory, Ensemble e Outcome Distribution | `FR-035`, `FR-093`, `FR-103`, `NFR-033` | Contenuto, lifecycle asincrono e quote coprono record e gestione delle simulazioni. |
| `ELM-072` | Forecast, Scenario Estimate, Interventional Estimate e Counterfactual | `FR-035`, `FR-086`, `FR-087` | Contratti distinti ed etichetta epistemica impediscono di confondere le quattro classi di output. |
| `ELM-073` | Causal Validation e Model Governance | `FR-034`, `FR-088`, `FR-098`, `NFR-030` | Manifest, validity envelope e integrità degli artefatti coprono validazione e governance. |
| `ELM-074` | Agent Type e Agent come Principal | `FR-038`, `FR-106`, `FR-004` | Il meta-modello e i requisiti di identità machine rendono ogni agente un Principal distinto. |
| `ELM-075` | Capability e Tool Contract | `FR-038`, `FR-047`, `FR-108` | Capability/Tool sono modellati, generati via SDK/MCP e corredati dallo schema obbligatorio. |
| `ELM-076` | Tool Binding | `FR-038`, `FR-109`, `FR-127`, `FR-128` | Binding sostituibile e controlli strutturali/confused-deputy separano contratto, adapter e authority. |
| `ELM-077` | Goal e Objective | `FR-036`, `FR-038`, `FR-113`, `NFR-016` | Goal/Objectives sono modellati ma non possono derivare Authority. |
| `ELM-078` | Utility, Preference e Risk Appetite | `FR-036`, `FR-099`, `FR-101` | Il profilo deliberativo e il confronto multidimensionale rendono espliciti funzione, preferenze e rischio. |
| `ELM-079` | Plan e Plan Step | `FR-038`, `FR-114`, `FR-115` | Il piano è parte dello stato di coordinamento e può avanzare soltanto tramite transizioni governate. |
| `ELM-080` | Resource Reservation e Lease | `FR-038` | Il requisito multi-agente include Reservation/Lease nel profilo MVP anche se la thin slice PoC può differirli. |
| `ELM-081` | Task e Assignment | `FR-038`, `FR-114` | Task/Assignment sono record espliciti dello stato di coordinamento. |
| `ELM-082` | Commitment | `FR-038`, `FR-114`, `FR-124` | Commitment è modellato nel coordinamento e conservato nella trace dell’agent run. |
| `ELM-083` | Message, Conversation e Speech Act | `FR-038`, `FR-116`, `FR-117` | Schema e non-canonicalizzazione automatica preservano significato e governance dei messaggi. |
| `ELM-084` | Full Governed Agent Memory — Memory Policy e Memory Item | `FR-038`, `FR-113`, `FR-115`, `FR-118`, `FR-119`, `FR-140`, `NFR-016`, `NFR-048` | `CORE/P0/PoC`: working, episodic, semantic, procedural, preference, reflection, dissent e team-shared memory; scope run/task/agent/team/project/domain/federated; persistenza cross-run; retrieval structured/full-text/vector/hybrid; lifecycle, consolidation, forgetting, legal hold, deletion e context receipts. Memory resta non canonica, tainted e priva di Authority; promozione soltanto via C6/C3. Copertura di design approvata da `DEC-208`; non costituisce evidenza runtime. |
| `ELM-085` | Inference, Prediction e Recommendation | `FR-033`, `FR-061`, `FR-086`, `FR-087`, `FR-104` | Le classi di output restano distinte, non si auto-promuovono e alimentano una DecisionProposal tracciata. |
| `ELM-086` | Decision, Approval e Human Gate | `FR-033`, `FR-003`, `NFR-005`, `FR-136`, `FR-137` | Decision e Approval sono separate, con gate umano, dual control e test anti-bypass. |
| `ELM-087` | Team, Team Role Assignment e Coordination Protocol | `FR-038`, `FR-010`, `FR-114`, `FR-115` | Team e ruoli sono modellati e la missione usa orchestrazione multi-agente governata. |
| `ELM-088` | Trust Tier, Autonomy Tier, Risk Class, Budget, Quota, Scope, Expiry e Kill Switch | `FR-038`, `FR-110`, `FR-120`, `FR-121`, `NFR-036` | Enforcement, budget, termination e kill switch coprono tutti i controlli agentici elencati. |
| `ELM-089` | Resource Metadata e Resource Status | `FR-039`, `FR-041`, `FR-046` | Metadata/status sono governati nel catalogo, nei package e nelle release immutabili. |
| `ELM-090` | Import, Export, Dependency, lock e digest | `FR-041`, `NFR-018`, `NFR-021`, `NFR-086` | Risoluzione deterministica, integrità della release e inventario dipendenze coprono composizione e supply chain. |
| `ELM-091` | Ontology Alignment e Semantic Mapping | `FR-043`, `FR-018`, `FR-168`, `FR-171` | Mapping generato, import loss-accounted, boundary W3C e migrazione Palantir coprono alignment e perdite semantiche. |
| `ELM-092` | Schema Version e Immutable Release | `FR-046`, `NFR-021`, `FR-145` | Release immutabile, firma e semantic versioning/diff coprono versione e attivazione. |
| `ELM-093` | Migration, Backfill, Alias e Deprecation | `FR-045`, `FR-146`, `FR-147` | Migration plan, Migration-as-Code e controllo distruttivo coprono tutto il lifecycle. |
| `ELM-094` | Branch, Change Proposal, Review e Merge | `FR-045`, `FR-066`, `FR-067`, `FR-144`, `FR-154` | Governance OaC, time travel, merge governato e separazione scenario/branch coprono proposal e merge. |
| `ELM-095` | Compiler, Type Checker e Static Analysis | `FR-042`, `FR-043`, `FR-050` | Compiler, analisi statica, generatori e CLI/CI costituiscono la toolchain eseguibile. |
| `ELM-096` | Ontology Test, Conformance Suite e golden test | `FR-051`, `NFR-093` | La suite produce evidenze firmate e l’evidence package ne assicura conservazione/riproduzione. |
| `ELM-097` | Query Language e Object Set Runtime | `FR-027`, `FR-055`, `FR-056`, `NFR-034` | Il runtime espone contratti tipizzati e vieta query backend arbitrarie a utenti applicativi e agenti. |
| `ELM-098` | Event Envelope, Change Feed e Subscription | `FR-069`, `FR-071`, `FR-072`, `FR-073` | Envelope, ordering/deduplica, replay e compatibility policy coprono stream e subscription. |
| `ELM-099` | API schema, SDK e Agent Tool Export | `FR-044`, `FR-047`, `NFR-022`, `FR-108` | Schemi generati, SDK/MCP coerenti e Tool Contract tipizzato coprono API e agent export. |
| `ELM-100` | Data Mapping, Projection e Current-State Overlay | `FR-043`, `FR-064`, `FR-065`, `FR-168` | Mapping generato, projection idempotente, rebuild e boundary W3C coprono overlay e portabilità. |
| `ELM-101` | Semantic Observability e Data Health | `FR-051`, `NFR-068`, `NFR-069`, `NFR-077` | Drift/conformance evidence, osservabilità e consistency health rendono misurabili stato semantico e lag. |
| `ELM-102` | Project, Space e Ownership Boundary | `FR-037`, `FR-041`, `FR-143`, `NFR-041` | Confini di governance, package ownership, ownership federata e isolamento coprono Project/Space. |
| `ELM-103` | Object View Variants e Application Metadata | `FR-039`, `FR-166`, `FR-167` | Metadata applicativi e viste role-oriented coprono varianti, dashboard e vista del mission thread. |

## C. Controllo di completezza

- Righe `CAP-*`: `26/26`.
- Righe `ELM-*`: `103/103`.
- Totale righe mappate: `129/129`.
- Ogni riga contiene almeno un ID `BR-*`, `FR-*` o `NFR-*` presente in uno dei registri di fase indicati.
- Nessun riferimento di requisito generico o non allocato è usato nella matrice.
- La presenza di un requisito non modifica lo stato delle evidenze riportato in `coverage_matrices.md`: i claim di parità o superiorità restano vietati finché non sono disponibili evidenze `E1` e, dove richiesto, revisione `E2`.
