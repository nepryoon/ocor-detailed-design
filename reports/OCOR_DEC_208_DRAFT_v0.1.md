# OCOR — DEC-208 DRAFT v0.1 — Full Governed Agent Memory design disposition

## 1. Control record

| Campo | Valore |
|---|---|
| Identificativo proposto | `DEC-208` — etichetta di bozza; non costituisce assegnazione nel Decision Register |
| Titolo proposto | Full Governed Agent Memory: design-baseline disposition and runtime evidence fence |
| Change set | `CC-FULL-GOVERNED-AGENT-MEMORY` |
| Stato | **Proposed — awaiting change control** |
| Approval mode richiesto | approvazione umana esplicita e congiunta del Product Owner e della Architecture Review Authority |
| Evidenza di approvazione corrente | nessuna; questa redazione non è un'approvazione e non esercita autorità decisionale |
| Effective from | non applicabile finché non approvata; anche dopo l'approvazione umana, l'efficacia richiede la promozione atomica content-addressed definita al §8 |
| Supersedes corrente | nessuno |
| Supersedes proposto, solo se approvata ed efficace | esclusivamente la disposizione di differimento di `ELM-084` contenuta in `DEC-196`; non sostituisce l'approvazione della IRB, `DEC-116` o altre disposizioni di `DEC-196` |
| Data di redazione | 2026-08-31 |
| Baseline sorgente | `origin/main@098c680615cf8d8b57cd367386bac10d8acdc715` |

`DEC-208` è il prossimo identificativo dichiarato libero dal supplemento di chiusura
`DEC-207`, ma questo file non lo alloca. Immediatamente prima dell'eventuale approvazione
l'autorità deve verificare nuovamente l'intera cronologia e tutti i ref remoti. Se
`DEC-208` non fosse più libero, questa proposta non può essere registrata con tale ID e
deve essere sottoposta a change control con il successivo identificativo realmente
libero. Nessuna decisione storica può essere rinumerata.

## 2. Non-approval fence e disposizione corrente

La presente bozza ha effetto normativo **nullo**. In particolare:

- full-memory resta **NO-GO**;
- `ELM-084` resta differito secondo `DEC-196`;
- `E1=0`, `E2=0` e zero requisiti globalmente `Verified` restano invariati;
- `E1_runtime_slice=PRESENT` resta confinato alla slice e alle evidenze accettate da
  `DEC-207` e non si estende alla full-memory;
- ADD v1.3, LLD v1.1, i cinque registri candidati e i contratti memory restano non
  approvati e non autoritativi;
- nessuna capability è attivata e nessuna tecnologia passa da `Candidate
  Implementation` a decisa.

La mera presenza, revisione, merge o pubblicazione di questo file non soddisfa
l'approval mode e non produce alcuna delle conseguenze prospettiche descritte nei
paragrafi successivi.

## 3. Decisione normativa proposta

Se, e soltanto se, entrambe le autorità indicate al §1 la approvano esplicitamente e
l'intero update set del §8 viene promosso atomicamente con digest verificati, la
decisione dispone quanto segue.

1. `ELM-084 — Agent Memory` diventa un elemento di design `CORE / P0 / PoC` con
   profilo `FULL_GOVERNED_AGENT_MEMORY`. La completezza riguarda semantica, contratti,
   confini di fiducia e failure semantics; volume, alta disponibilità, SLO di
   produzione e resilienza multi-region restano fuori dal profilo PoC.
2. La disposizione supersede soltanto il differimento di `ELM-084` in `DEC-196`.
   Restano vigenti `DEC-116`, la natura scoped, policy-governed e non canonica della
   memoria, i requisiti `FR-118` e `FR-119`, e tutti i fence epistemici e di Authority.
3. Il design PoC comprende memoria `WORKING`, `EPISODIC`, `SEMANTIC`, `PROCEDURAL`,
   `PREFERENCE`, `REFLECTION`, `DISSENT` e `TEAM_SHARED`; gli scope indipendenti sono
   `RUN`, `TASK`, `AGENT`, `TEAM`, `PROJECT`, `DOMAIN` e `FEDERATED`.
4. Il design comprende persistenza cross-run, retrieval `STRUCTURED`, `FULL_TEXT`,
   `VECTOR` e `HYBRID`, versioning immutabile, consolidamento, correzione,
   supersession, revoca, expiry, forgetting, legal hold, deletion saga e ricevute di
   context assembly riproducibili.
5. L'ammissione, il retrieval, l'influenza sul contesto e ogni proposta di promozione
   devono essere fail-closed, policy-bound, content-addressed e auditabili. Nessun
   contenuto memory può concedere Authority o scrivere direttamente nello stato
   canonico.
6. OpenAPI e JSON Schema descrivono il contratto logico versionato; nomi o dettagli di
   backend non possono entrare nei contratti pubblici. Gli indici full-text e vector
   sono proiezioni ricostruibili, mai autorità dello stato.
7. Il supporto del mode `VECTOR` nel contratto non promuove `ELM-011 — Vector`, non
   sceglie un vector database e non modifica lo stato di alcuna tecnologia. Un adapter
   o una combinazione non supportata deve fallire esplicitamente e apparire nella
   capability matrix.
8. La ratifica della baseline di design non costituisce runtime conformance. Anche
   dopo l'eventuale efficacia della decisione, il runtime full-memory resta **NO-GO**
   finché una distinta chiusura governata non accetta evidenza eseguita per
   `FGM-01`–`FGM-20`.

### 3.1 Effetto proposto sullo stato

| Dimensione | Stato corrente della bozza | Effetto solo dopo approvazione ed efficacia |
|---|---|---|
| Full-memory design baseline | `NO-GO`; candidati non autoritativi | rimosso il solo blocker di baseline documentale; autorizzata la promozione atomica del design completo |
| Full-memory runtime | `NO-GO` | **NO-GO invariato** fino a distinta validation closure di `FGM-01`–`FGM-20` |
| `E1` / `E2` | `E1=0`, `E2=0` | invariati; nessuna evidenza nasce da una decisione documentale |
| Requirement evidence | zero requisiti globalmente `Verified` | invariato; i requisiti restano `specified/planned` finché le rispettive evidenze non sono accettate |
| `E1_runtime_slice` | `PRESENT` soltanto come da `DEC-207` | nessuna estensione alla full-memory |
| `ELM-084` | differito | `CORE / P0 / PoC` come **Design Target**; non è un'autorizzazione a operare un runtime |
| `FR-048` | `P2/Deferred`, Future | invariato |
| `ELM-011` | differito | invariato; `VECTOR` resta un mode contrattuale con implementazione fail-closed se unsupported |
| Capability differite | non attive | nessuna attivazione implicita oltre alla disposizione di design specifica per `ELM-084` |
| Tecnologie | `Candidate Implementation` | invariato; nessuna tecnologia è selezionata o promossa |
| Perimetro PoC | nessun `PoC-START` o `PoC-PASS` autorizzato | include il design completo di `ELM-084` in un PoC sintetico e bounded; non autorizza esecuzione, dati reali, effetti esterni, MVP o Production |

## 4. Razionale

`FR-118` e `FR-119` sono già P0/PoC e `DEC-116` impone memoria tipizzata,
policy-governed, segregata e non canonica. Un profilo limitato alla sola memoria di run
non eserciterebbe persistenza cross-run, isolamento di index/cache, lifecycle completo,
consolidamento, cancellazione e non-interference; validerebbe quindi un'architettura
diversa da quella richiesta e trasferirebbe il redesign ai gate successivi.

La proposta separa due decisioni che non devono essere confuse:

- la ratifica di una baseline di **design** completa e mutuamente coerente;
- l'accettazione successiva di evidenza di **runtime**, che richiede esecuzione e
  oracoli per tutti i casi `FGM-01`–`FGM-20`.

Questa separazione permette di consolidare ADD, LLD e contratti senza usare la
documentazione come evidenza. Conserva così il fence `E1=0`, `E2=0`, evita un claim di
runtime conformance e rende esplicita la condizione che mantiene full-memory `NO-GO`.

## 5. Contenuto normativo del profilo proposto

### 5.1 Contratto chiuso e versioning

Ogni `GovernedMemoryItem` deve contenere, con cardinalità e condizioni chiuse:

```text
memory_item_id, memory_version, memory_kind, memory_scope,
owner_principal_id, agent_run_id?, team_run_id?, task_id?,
agent_id?, team_id?, project_id?, tenant_id, organization_id, domain_id,
compartments[], classification_marking_ref, purpose,
content_schema_ref, content_ref, content_digest, language?,
source_kind, source_ref, source_digest,
evidence_refs[], provenance_refs[], derived_from_refs[], consolidates_refs[],
supersedes_ref?, correction_of_ref?,
created_at, valid_from, valid_until?, expires_at?,
retention_policy_ref, legal_hold_ref?, confidence, uncertainty_ref?,
policy_bundle_digest, ontology_release_digest, governed_context_digest,
instruction_eligible, taint_labels[], representation_kinds[],
embedding_model_ref?, embedding_model_digest?, embedding_ref?, embedding_digest?,
lifecycle_status
```

Proprietà non dichiarate e alias devono essere respinti. Correzione,
riclassificazione, cambio di instruction eligibility, consolidamento e re-embedding
producono nuove versioni immutabili; non sovrascrivono sorgenti o versioni precedenti.
L'idempotenza di ammissione è vincolata a `(tenant_id, memory_scope, source_digest,
content_digest, operation_id)`; stesso key/digest restituisce la ricevuta originaria,
mentre un digest differente produce `MEMORY_IDEMPOTENCY_CONFLICT`.

### 5.2 Autorità e influenza

Memory è non autoritativa. Non può creare direttamente Canonical Assertion,
Authority, Delegation, Approval, Decision, CapabilityLease, ActionCommand o policy.
Claim, Observation, Hypothesis, Model Output, Decision, ExecutionResult e
OutcomeAssessment restano tipi distinti. Contenuto umano, tool, modello o fonte
esterna è data e non istruzione per default; hidden chain-of-thought, scratchpad,
credenziali, token grezzi e segreti sono classi proibite.

L'influenza sul contesto richiede un `MemoryContextAssembly` che registri query digest,
item e versioni restituite, decisioni di policy, ordine, truncation, redazioni e digest
finale. La sola via di promozione è:

```text
MemoryItem -> MemoryPromotionProposal -> C6 control/approval/decision
           -> GovernedCanonicalCommitCommand -> C3 canonical commit
```

Non sono ammessi shortcut né promozioni automatiche.

### 5.3 Storage, retrieval e policy

Il Memory Service usa port logici per metadata store, content-addressed object store,
full-text index, vector index, event journal e audit store. Metadata e contenuto più
event journal devono poter ricostruire gli indici. Ogni entry d'indice conserva
item/version, content digest, representation digest, marking, policy, scope e deletion
epoch.

L'ordine di retrieval è vincolante:

1. autenticare e validare il Governed Context Set e il suo digest;
2. applicare pre-query policy e derivare la partizione autorizzata;
3. respingere representation capability non disponibile o non approvata;
4. cercare soltanto nella partizione autorizzata;
5. post-filtrare ogni candidato con identity, Authority, marking, purpose, lifecycle e
   policy correnti;
6. applicare un ranking profile deterministico e versionato;
7. materializzare contenuto, evidence e spiegazione policy-safe;
8. registrare influenza e accessi nel canale audit protetto.

Elementi non autorizzati non possono influenzare contenuto, esistenza, count, rank,
score, pagination, explanation, cache hit, error shape o observable timing bucket.
Cross-project e federation richiedono Authority esplicita, purpose compatibile,
marking conservativo e federation policy auditabile; cross-tenant è deny-by-default.

### 5.4 Consolidamento, lifecycle e cancellazione

Consolidamento, summarisation, embedding e reflection producono artefatti derivati con
input refs, algoritmi o modelli pinnati, purpose e uncertainty; non mutano le sorgenti.
Contraddizioni producono record separati di conflict/dissent. La maggioranza non può
cancellare evidenza minoritaria e la procedural memory non diventa
instruction-eligible senza approvazione distinta e capability check corrente.

Il lifecycle ammesso è:

```text
PROPOSED -> ACTIVE | QUARANTINED
ACTIVE -> SUPERSEDED | REVOKED | EXPIRED | LEGAL_HOLD | DELETION_PENDING
QUARANTINED -> ACTIVE | REVOKED | DELETION_PENDING
SUPERSEDED | REVOKED | EXPIRED -> LEGAL_HOLD | DELETION_PENDING
LEGAL_HOLD -> prior disposition | DELETION_PENDING
DELETION_PENDING -> DELETED | DELETION_INCOMPLETE
DELETION_INCOMPLETE -> DELETION_PENDING
```

`DELETED` è terminale. L'uscita da legal hold ripristina la disposizione precedente,
non sempre `ACTIVE`. Deletion copre contenuto, embedding, full-text/vector index,
cache, replica ed export; un fallimento parziale produce `DELETION_INCOMPLETE`, blocca
il retrieval e resta visibile fino alla riconciliazione. Un tombstone audit opaco e
privo di contenuto è conservato soltanto se policy o legal hold lo richiedono.

### 5.5 Security e tecnologia

Le difese devono coprire prompt injection diretta e indiretta, poisoning, provenance
laundering, embedding inversion, membership inference, leakage cross-tenant/domain/
compartment, side channel di ranking/count/cache/timing, confused deputy, escalation,
delegation replay, collusion, dissent suppression, consolidamento malevolo, stale
policy, marking downgrade, incomplete deletion, resurrection da backup e use after
revocation.

Embedding e rappresentazioni vector sono derivati legati a content digest, model
ID/version/digest, tokenizer, dimensione e normalization profile. Un cambio modello
crea una nuova representation version. Centroidi, ANN graph e cache condivisi tra
compartimenti sono vietati salvo prova di non-interference per quello specifico
profilo. Queste regole non scelgono un prodotto né promuovono una tecnologia.

## 6. Requisiti serviti e tracciabilità

| Requisito | Contributo della proposta | Decisioni/invarianti preservati | Verifica runtime richiesta |
|---|---|---|---|
| `FR-038` | completa `ELM-084` nel modello multi-agente governato | `DEC-007`, `DEC-066`, capability deny-by-default | trace di ogni operazione memory attraverso Agent Kernel e policy |
| `FR-113` | impedisce Authority derivata dal contenuto memory | `DEC-113` | prompt/content di elevazione non modifica effective capabilities |
| `FR-115` | impedisce memoria globale o datastore condiviso non governato | `DEC-114` | ogni scambio e retrieval è autorizzato, scoped e correlato |
| `FR-118` | chiude schema, kind/scope, versioning, provenance, lifecycle e receipts | `DEC-116` | `FGM-01`–`FGM-04`, `FGM-06`–`FGM-15`, `FGM-18`–`FGM-20` |
| `FR-119` | applica isolamento e policy anche a embedding, index e cache | `DEC-116`, `ARC-016` | `FGM-05`, `FGM-08`, `FGM-10`, `FGM-16`, `FGM-17`, con zero leakage |
| `FR-140` | rende provenance, marking, taint e instruction eligibility obbligatori | `DEC-133` | agent conformance e security test senza backend credential arbitrarie |
| `NFR-016` | conserva separazione fra Goal/Message/Memory e Authority | `DEC-066`, `ARC-015` | tutti i casi negativi restano denied |
| `NFR-048` | specifica le superfici memory della suite agentica avversaria | `DEC-133` | zero mutazioni non autorizzate e zero esfiltrazioni classificate |

Il profilo mitiga `RSK-031` mediante provenance, isolation, TTL, sanitisation,
versioning e promotion gate, e `RSK-038` mediante taint, content-as-data,
instruction-eligibility separata e zero-trust agent/tool boundary. La decisione di
design non chiude tali rischi: il rischio residuo rimane aperto fino all'accettazione
dell'evidenza runtime pertinente.

## 7. Vincoli e invarianti toccati

L'eventuale approvazione incorpora come vincolanti tutti i seguenti invarianti:

1. memory non è mai un'autorità canonica;
2. i tipi epistemici e operativi non vengono collassati in Memory Item;
3. source, evidence, provenance, marking, policy, validità, uncertainty, lifecycle e
   digest restano associati a ogni item/version;
4. il contenuto è data e non istruzione per default;
5. hidden reasoning, credenziali, raw token e segreti sono vietati;
6. ogni derivazione crea un nuovo artefatto immutabile;
7. la policy opera sia prima della ricerca sia prima della materializzazione;
8. vale non-interference anche per metadati, ranking, cache, error shape e timing;
9. federation richiede Authority e policy esplicite; cross-tenant è deny-by-default;
10. persistenza non autorizza training o fine-tuning;
11. deletion copre ogni copia e projection e fallisce chiusa;
12. ogni promozione memory-derived passa integralmente da C6 e C3;
13. input assente o divergente, adapter unsupported e combinazione non supportata
    producono errore esplicito; non esiste fallback silenzioso;
14. `E1=0`, `E2=0`, zero requisiti globalmente `Verified` e full-memory runtime
    `NO-GO` non possono essere modificati dalla promozione documentale;
15. `FR-048` e `ELM-011` restano differiti e nessuna tecnologia candidata è promossa.

## 8. Preconditions per l'approvabilità

Tutte le precondizioni di decisione `P-01`–`P-12` devono essere soddisfatte nello
stesso content-addressed change set. Uno stato diverso da `PASS` mantiene questa
proposta non approvabile; non è ammessa una waiver implicita.

| ID | Precondizione | Stato al 2026-08-31 | Evidenza verificabile |
|---|---|---|---|
| `P-01` | sorgenti dei cinque candidati univoche sotto `governance_dossier/registers/`, byte-matched a `origin/main`, senza fallback silenzioso | `PASS` | remediation C.1; strict generator commit `3ad0fdce7d3d8b6829c665acfa6e1a596fa59538` |
| `P-02` | cinque digest-base uguali ai cinque registri autoritativi di main | `PASS` | remediation C.2; 5/5 `MATCH`; commit `d86c7e07a4e2a8bdc7412390ca0a9013eb1d8e62` |
| `P-03` | due clone puliti producono output byte-identici | `PASS` | remediation C.3; 7/7 output identici; commit `bf3ca93699c24e4d119d819565ccc41a63937b4e` |
| `P-04` | lineage main → trasformazione → candidati e candidate manifest verificati | `PASS` | remediation C.4; manifest specifico 6/6 e aggregato 25/25; commit `a677d319c4e7bc6eb3184d0ca670dc60b35e1fe8` |
| `P-05` | validator OpenAPI ufficiale pinnato ed eseguito; harness senza skip inspiegati | `PASS` | remediation C.5; harness 14/0/0 e suite C.5 4/0/0; commit `b4b4a0b3ff3da31298151e25c656fd8076feb493` |
| `P-06` | Verification Evidence Report semanticamente immutato salvo normalizzazione editoriale dimostrata | `PASS` | remediation C.6; commit `28e2c70b28a7840da5e0ac840d923a8c4060b6e5`; equivalenza dopo normalizzazione byte |
| `P-07` | mapping DRAFT→DEC e provenienza `DEC-201`, `DEC-205`, `DEC-206` non collisivi | `PASS` | remediation C.7; 6/6 controlli; commit `32ba5bd1204feb662776d6f59df7684e984328e3` |
| `P-08` | cinque candidati completi, ADD v1.3, LLD v1.1 e contratti memory versionati sono coerenti, completi e tracciabili bidirezionalmente | `NOT SATISFIED` | ADD v1.3, LLD v1.1 e contratti memory sono espressamente fuori perimetro della presente esecuzione e non sono promossi |
| `P-09` | tutti i digest del futuro update set coincidono con manifest candidato definitivo e report di consistenza referenziale 100% | `NOT SATISFIED` | il manifest corrente copre la remediation dei cinque candidati; l'update set autoritativo completo non è stato composto |
| `P-10` | `DEC-208` è ancora il prossimo ID libero su main, su ogni ref remoto e nella cronologia completa immediatamente prima della registrazione | `NOT SATISFIED` | verifica intenzionalmente rinviata al momento dell'eventuale approvazione; questa bozza non riserva l'ID |
| `P-11` | Product Owner e Architecture Review Authority approvano umanamente ed esplicitamente la stessa revisione content-addressed | `NOT SATISFIED` | nessuna approvazione è contenuta o presupposta in questa esecuzione |
| `P-12` | gate CI del futuro change set completo concluso con zero failure e ogni `NOT_EXECUTED` nominato e motivato | `NOT SATISFIED` | la CI della presente PR dimostra soltanto la remediation e la qualità della bozza, non il futuro set di promozione |

I digest delle evidenze già sanate sono:

| Artefatto | SHA-256 |
|---|---|
| `reports/OCOR_Change_Control_Full_Governed_Agent_Memory_v1.0.md` | `c11e68c5cfdc2b63c5b51b382dba086687701467a50fbeb17d071e4056ee8366` |
| `reports/REMEDIATION_C_2026-08-31.md` | `675051efa032b263a8f82386423c7760d11d449ac9ce2b0dd492e0197388e6a4` |
| `reports/OCOR_FULL_MEMORY_GOVERNANCE_CANDIDATE_SHA256SUMS` | `52f9006aa0ceb2c56cb7f15f290e6568e449f783bdc62760be71e06b5d343a0d` |
| `reports/OCOR_IRB_ADD_LLD_REMEDIATION_SHA256SUMS` — candidato, non approvato | `94c82fa14ef0cd90d234565380ae0ec5d1b0c7684f4af6252e12840f28030e8e` |
| `reports/tests/full_memory_governance_candidate_results.json` | `4f6edf4320af0fc262ab31728d655f375a9886281c0da6cbdf6a8961371fc309` |
| `reports/tests/full_memory_reproducibility_results.json` | `1b8a796b7eda4b75df4d725d551d3f224801bf8ae776d406798f5227e2fca36a` |
| `reports/tests/c5_openapi_validation_results.json` | `c43e3d55c1ae771c76d34c06826ac29e56becad8444e7614ff1f2446d687dfe8` |
| `reports/tests/c7_decision_mapping_results.json` | `b521743b026f4d6307876555f38f82ddf7ca80c6a767efdb20f5352df2e37055` |
| `reports/contracts/governed-memory-item.schema.json` — candidato, non approvato | `8d0167be6467a8cfb4e41e4c7cc1e8f207b578456238a7da41f7a4da091e47b5` |
| `reports/contracts/ocor-governed-memory.openapi.yaml` — candidato, non approvato | `526caa147715aaffc6d4003889db1111e50d6cd17cd9fc61dbfad28f58343d9b` |

Le precondizioni runtime sono separate: `FGM-01`–`FGM-20` devono essere eseguite e
accettate da una successiva autorità di validation closure prima di qualunque
transizione del runtime full-memory da `NO-GO`. La soddisfazione di `P-01`–`P-12` non
sostituisce tali prove.

## 9. Atomic update set proposto

Dopo la soddisfazione di `P-01`–`P-12`, l'efficacia richiede un unico commit o merge
content-addressed che aggiorni in modo mutuamente coerente:

1. Requirement Register, preservando `FR-118` e `FR-119` P0/PoC;
2. Requirement Traceability Index;
3. Decision Register, con l'ID libero verificato, e Decision Traceability Index;
4. CAP/ELM Requirement Crosswalk, con `ELM-084 = CORE/P0/PoC`;
5. ADD v1.3, inclusi scope fence, C8, security, operations e acceptance allocation;
6. LLD v1.1, inclusi contratti, storage, algoritmi, lifecycle, threat model e test;
7. OpenAPI e JSON Schema memory versionati, relativi manifest/digest e riferimenti
   downstream;
8. ARA Decision Record e indici decisionali con autorità, data, approval evidence,
   supersession circoscritta e digest dell'intero set.

Una promozione parziale, una registrazione decisionale separata dagli artefatti o la
coesistenza ambigua del bounded profile e del full profile è invalida e deve fallire
rumorosamente. I manifest degli artefatti approvati esistenti non vengono riscritti:
il nuovo set usa versioni e manifest nuovi.

## 10. Criteri di verifica alla chiusura

La decisione può essere marcata `Approved` ed efficace soltanto quando un verificatore
indipendente dimostra con output macchina e review umana tutti i seguenti criteri:

1. `DEC-208`, oppure il successivo ID realmente libero, è verificato libero e compare
   una sola volta in Decision Register, Decision Traceability Index e ARA Decision
   Record con identico titolo, status, data e supersession;
2. esistono due approval statement umani espliciti riferiti allo stesso digest set,
   uno in ruolo Product Owner e uno in ruolo Architecture Review Authority;
3. `P-01`–`P-12` sono tutti `PASS` e nessun controllo mancante è contato come pass;
4. i cinque registri, ADD v1.3, LLD v1.1 e i contratti memory hanno consistenza
   referenziale 100% e tracciabilità bidirezionale verificata da script;
5. ogni digest dichiarato coincide con il file consegnato e due clean-clone build
   riproducono byte per byte ogni candidato derivato;
6. `inputs/` coincide con il tree autoritativo previsto e nessuna decisione
   `DEC-197`–`DEC-207` è modificata;
7. il gate registra esplicitamente `E1=0`, `E2=0`, zero requisiti globalmente
   `Verified`, `E1_runtime_slice=PRESENT` confinato a `DEC-207` e full-memory runtime
   `NO-GO`;
8. `FR-048` e `ELM-011` restano differiti, le capability non incluse nella
   disposizione specifica restano inattive e tutte le tecnologie restano `Candidate
   Implementation`;
9. `SL-01`–`SL-04` restano registrate finché le rispettive sorgenti non sono presenti;
10. la successiva runtime closure, e non questa decisione, esegue `FGM-01`–`FGM-20`,
    conserva gli output grezzi e richiede zero leakage per gli oracoli di `FR-119`.

## 11. Rischi mitigati e rischio residuo

| Rischio | Mitigazione introdotta dal design | Evidenza necessaria prima del runtime GO |
|---|---|---|
| `RSK-031` — context poisoning o leakage persistente | provenance obbligatoria, isolation, TTL, sanitisation, taint, immutable versioning, promotion gate | `FGM-02`, `FGM-05`, `FGM-08`, `FGM-10`, `FGM-12`, `FGM-16`–`FGM-18` |
| `RSK-038` — content-borne instruction e memory poisoning | content-as-data, instruction eligibility separata, capability allow-list, policy pre/post retrieval, audit | `FGM-08`, `FGM-14`, `FGM-15`, `FGM-17` e suite `NFR-048` |
| Leakage da projection e side channel | partitioning per policy, post-filter, non-interference su count/rank/cache/error/timing | `FGM-05`, `FGM-10`, `FGM-16` |
| Resurrection o cancellazione incompleta | deletion saga, deletion epoch, fail-closed incomplete state, replica/export reconciliation | `FGM-11`, `FGM-12`, `FGM-18`, `FGM-19` |
| Lineage non riproducibile | sorgenti main univoche, digest-base, generatori fail-loud, doppio clean-clone replay | riesecuzione delle prove C.1–C.4 sul commit sottoposto all'approvazione |
| Promozione probatoria indebita | separazione design/runtime, evidence fence e distinta validation closure | controllo esplicito `E1=0`, `E2=0`, zero global `Verified`, runtime `NO-GO` |

La specificazione riduce il rischio di design ma non prova l'efficacia delle
mitigazioni. Nessun rischio è chiuso dalla sola decisione.

## 12. Cosa questa proposta non autorizza

Anche se approvata come decisione di design, questa disposizione **non** autorizza:

- l'uso di questa bozza come approval evidence o la sua registrazione automatica;
- la modifica retroattiva, rinumerazione o reinterpretazione di `DEC-197`–`DEC-207`;
- una promozione parziale o fuori dall'atomic update set del §9;
- il passaggio del runtime full-memory da `NO-GO` a `GO`;
- l'incremento di `E1` o `E2`, l'estensione di `E1_runtime_slice`, o la promozione di
  qualsiasi requisito a `Verified`;
- `PoC-START`, `PoC-PASS`, dati reali, effetti esterni, MVP, Production, production
  readiness, HA, compliance, parity o superiority claim;
- Authority derivata da Goal, Plan, Message, Memory, recommendation o model output;
- activation automatica di procedural memory, training o fine-tuning da memory;
- l'attivazione di `FR-048`, `ELM-011` o di altre capability differite;
- la selezione o promozione di un database, vector engine, embedding model o altra
  tecnologia candidata;
- accessi cross-tenant, federation senza Authority, direct datastore access o direct
  canonical write;
- la chiusura di `RSK-031`, `RSK-038`, `SL-01`–`SL-04` o di qualunque gap senza la
  rispettiva evidenza;
- modifiche a `inputs/`, ai manifest approvati correnti o al governance dossier
  approvato al di fuori di una futura promozione esplicita e content-addressed.

## 13. Disposizione finale della bozza

Stato conclusivo di questo documento: **Proposed — awaiting change control**.

Non esistono approval statement associati, non esiste effective date, il Decision
Register non contiene una nuova riga e l'ARA Decision Record non è stato aggiornato.
Full-memory resta **NO-GO**. Il solo esito della redazione è una proposta completa e
verificabile che le autorità possono accettare, respingere o emendare mediante un
successivo atto umano esplicito.
