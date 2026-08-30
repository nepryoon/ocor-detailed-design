# FASE 1 — Mappa normativa completa

## Control statement

La mappa è stata costruita sulle sorgenti normative v1.1, sui registri, sul delta manifest e sugli artefatti di review esistenti, senza aprire `inputs/supporting/prior/` durante questa fase. Il dettaglio machine-readable è in `reports/remediation/checkpoints/baseline_map.json`, generato da `reports/tests/build_baseline_map.py`; contiene digest, locator, righe originali, riferimenti e mapping per ogni ID.

Lo stato probatorio rimane invariato: `E1=0`, `E2=0`, zero requisiti `Verified`, capability `Design Target`, tecnologie `Candidate Implementation`.

## Indice completo ADD v1.1

| Sezione | Titolo | Linea baseline |
|---|---|---:|
| §1 | Document Control & System Context (C4 Level 1) | 1 |
| §1.1 | Controllo del documento | 3 |
| §1.2 | System context | 36 |
| §1.3 | Autorità e separazione dei concern | 76 |
| §1.4 | Trust boundaries e isolamento multi-compartimento | 101 |
| §1.5 | Scope fence | 137 |
| §2 | Container Architecture & Decomposition (C4 Level 2) | 146 |
| §2.1 | Vista dei container | 148 |
| §2.2 | Specifica degli otto subsystem | 194 |
| §2.2.1 | Moduli interni e port logici | 209 |
| §2.3 | Atomicità locale e propagazione asincrona | 222 |
| §2.4 | Reference triad isolation e capability matrix | 234 |
| §2.5 | Regole di interazione | 262 |
| §2.6 | Registro delle assunzioni sui backend candidati | 277 |
| §3 | Core Data Metamodels & Critical Interfaces | 298 |
| §3.0 | Regole trasversali dei contratti | 302 |
| §3.0.1 | Realizzazione del Governed Context Set | 304 |
| §3.0.2 | Forma unica del marking | 324 |
| §3.0.3 | Naming e cardinalità | 333 |
| §3.0.4 | Versionamento dei contratti corretti in v1.1 | 337 |
| §3.1 | Ontology-as-Code e Canonical IR | 341 |
| §3.1.1 | Metamodello OaC | 343 |
| §3.1.2 | Struttura della Canonical IR firmata | 371 |
| §3.2 | Canonical Ingestion Envelope | 457 |
| §3.3 | Named Query Gateway — OpenAPI 3.1 | 755 |
| §3.4 | Function & Model Registry — Protobuf/gRPC | 1262 |
| §3.5 | MCP Governed Tool Contract | 1480 |
| §3.6 | Provenance & Evidence Metamodel | 1875 |
| §3.7 | Action Type Contract | 1942 |
| §3.8 | Event Subscription Contract | 2344 |
| §3.9 | Conformance target | 2474 |
| §4 | Runtime Execution Engines & Workflows | 2489 |
| §4.1 | Action Pipeline Finite State Machine | 2493 |
| §4.1.1 | Guardie formali | 2576 |
| §4.1.2 | Transizioni normative | 2587 |
| §4.1.3 | Profilo temporale candidato PoC | 2634 |
| §4.2 | Causal Inference & Scenario Branching | 2655 |
| §4.3 | Governed Multi-Agent Collaboration | 2761 |
| §4.3.1 | Invarianti multi-agente | 2839 |
| §5 | Zero-Trust Security, Governance & Human Gate | 2854 |
| §5.1 | Sovereign identity and security control plane | 2858 |
| §5.2 | Cryptographic Delegation and capability enforcement | 2891 |
| §5.3 | Compartimentazione e propagazione conservativa dei markings | 2946 |
| §5.4 | Human Gate e Separation of Duties | 3005 |
| §5.5 | Break-glass ed Emergency Stop | 3054 |
| §6 | Deployment, Operations & Resilience Architecture | 3073 |
| §6.1 | Profilo PoC single-site isolato | 3077 |
| §6.2 | Consistenza eventuale osservabile | 3135 |
| §6.3 | Observability e safe-degraded operation | 3172 |
| §6.4 | Backup authority-aware | 3210 |
| §6.5 | Restore, deterministic replay e recovery gate | 3228 |
| §7 | Subsystem Traceability & Crosswalk Matrix | 3255 |
| §7.1 | Scope disposition verificabile | 3276 |
| §7.2 | Acceptance allocation ed evidence status | 3292 |
| §7.3 | Chiusura architetturale | 3305 |
| §8 | Amendment Log v1.0 → v1.1 | 3311 |
| §8.0 | Difetti introdotti dalla revisione e corretti prima della consegna | 3348 |
| §8.1 | Versioni dei contratti | 3359 |
| §8.2 | Cosa questa revisione non fa | 3373 |

## Universo normativo espanso

I range sono stati espansi e confrontati con righe canoniche dei registri, non con conteggi narrativi.

| Famiglia | Conteggio |
|---|---:|
| `DEC` | 196 |
| `BR` | 18 |
| `FR` | 174 |
| `NFR` | 93 |
| `ARC` | 23 |
| `CAP` | 26 |
| `ELM` | 103 |
| `RSK` | 60 |
| `EV` | 35 |
| `OI` | 34 |
| `ASM` | 13 |
| `DEP` | 26 |
| `BA` | 8 |
| `AM` | 28 |
| `DRAFT` | 9 |

L'universo core dichiarato dall'ADD è `196 DEC + 18 BR + 174 FR + 93 NFR + 23 ARC + 26 CAP + 103 ELM + 60 RSK = 693`. Gli altri registri governano evidenza, issue, assunzioni, dipendenze e change control senza entrare nel totale core.

Il totale di tutte le famiglie richieste è 846. I registri canonici non presentano buchi o duplicati. Le decisioni sono 180 `Approved` e 16 `Approved with conditions`; le 23 `ARC-*` sono `Confirmed`. Le 34 `OI-*` comprendono 29 `Open` e cinque risolte dalla baseline (`OI-002`–`OI-005`, `OI-007`). `ASM-001` è `Accepted — da verificare`; `ASM-002`–`ASM-013` sono `Accepted — validation pending`. `RSK-001` è `Mitigated`, gli altri 59 sono `Active`; 26 `DEP-*` sono `Active`; 35 `EV-*` sono planned/non eseguiti.

## Requisiti: stato, priorità e release

Sono state lette 285 righe requisito: 284 `Confermato`, una `Differito` (`FR-048`). La distribuzione di priorità è: 247 `P0`; 27 `P1`; 4 `P0/P1`; 2 `P2`; 2 `P1 MVP; P0 Production`; una per ciascuna variante `P1 thin slice`, `P2/Deferred`, `P1 PoC; P0 MVP`. Le release testuali sono preservate integralmente nel JSON; le classi prevalenti sono PoC (193), MVP (47), Production (12), multi-release PoC/MVP/Production (11) e PoC thin slice/MVP completo (7).

Per ogni requisito la mappa JSON conserva titolo, stato, priorità, release, sorgente/linea, tutte le celle normative e i riferimenti aggregati verso `DEC`, `ELM`, `CAP`, `RSK`, `EV`, `ARC`, `DEP`, `ASM`, `OI`. Esempi critici verificati:

| Requisito | Decisioni | Elementi/capability | Stato/release | Rilievo |
|---|---|---|---|---|
| `FR-095` | `DEC-103` | `ELM-070`, `CAP-019` | `Confermato`, `P0`, PoC | Contraddizione: capability AAP differita |
| `NFR-078` | `DEC-020`, `DEC-168` | `CAP-024`, `ARC-021` | `Confermato`, `P0`, MVP | Fuori profilo PoC, non `Differito` |
| `FR-166` | `DEC-017/018/023/173` | `ELM-051/103`, `CAP-014` | `Confermato`, `P0`, PoC | richiede allocazione sostantiva `DEC-173` |
| `FR-167` | `DEC-173` | `ELM-051/103`, `CAP-014` | `Confermato`, `P1`, MVP | richiede allocazione sostantiva `DEC-173` |
| `NFR-082` | `DEC-015/020/175` | `ELM-052`, `CAP-014/020/022`, `DEP-024` | `Confermato`, multi-release | richiede allocazione sostantiva `DEC-175` |

Gli indici sorgente dichiarano e realizzano 285/285 requisiti, 196/196 decisioni e 26/26 capability + 103/103 elementi, senza orfani sintattici. L'ADD §7 ha invece coverage decisionale 181/196 e `CAP` 25/26 perché `CAP-026` è intenzionalmente out of scope. Il `PASS` numerico non prova la correttezza semantica delle allocazioni.

## Hard invariants e authority fence

- Separazione epistemica: `Observation/Claim ≠ Canonical State ≠ Projection ≠ Prediction ≠ Intervention ≠ Action ≠ Outcome`.
- Nessun universal master, 2PC globale, triple-write sincrono o multi-master globale.
- `main` ha un solo writer logico; branch scenario non possiedono `main.write` e non pubblicano outbox.
- Policy/Authority/Approval/audit indisponibili producono deny o fail-closed sulle mutazioni.
- Prompt, Goal, Recommendation e agent output non concedono Authority.
- Ogni capability differita resta disattivata; tecnologie e backend sono candidate.
- Nessun nuovo `DEC-*`; nessuna approvazione `DRAFT-A`–`DRAFT-I`; nessuna chiusura `OI/ASM/RSK`.
- Evidence fence immutabile: `E1=0`, `E2=0`, zero `Verified` e zero `EV-*` eseguiti.

## Scope fence, issue e capability differite

Il PoC include otto subsystem, control plane, Human Gate, audit, PKI locale e simulatori sintetici. Restano differiti `FR-048`, hardening esteso `CAP-024`, `ELM-011/015/035/049/070/080/084/091`; `CAP-026` è out of scope. `NFR-078` è invece un requisito confermato P0/MVP fuori dal solo profilo PoC. `OI-001`, `OI-006`, `OI-008`–`OI-034`, tutte le `ASM-*` e tutti i `RSK-*` conservano lo stato sorgente.

## Contratti, versioni e rami

| Contratto | Versione baseline | Nota |
|---|---|---|
| `signed-canonical-ir` | `1.0` | JSON Schema Draft 2020-12 |
| `canonical-ingestion-envelope` | `1.1` | 4 rami condizionali |
| Named Query Gateway | OpenAPI `1.1.0` / OpenAPI 3.1.0 | 6 path, 25 schemi, 26 `$ref` |
| `FunctionRegistry`/`ModelRegistry` | `ocor.registry.v1` | Protobuf compilato dal harness |
| `mcp-tool-contract` | `1.1` | 11 rami condizionali |
| `action-type-contract` | `1.0` | 9 rami; un caso semantico illecito accettato |
| `event-subscription-contract` | `1.0` | nessun ramo condizionale dichiarato |
| Provenance metamodel | Turtle/RDF, 17 triple | parse baseline `PASS` |

La suite preesistente produce 97 `PASS` e 1 `FAIL`: accetta `CANONICAL_COMMIT/R1_ANALYZE` con `approval.mode=NONE`. Inoltre non copre adeguatamente l'assenza del marking in `QueryContext` né la non-obbligatorietà di `ObjectSnapshot.link_refs`, `uncertainty`, `explanation_ref`.

## FSM baseline

La baseline dichiara 29 stati e famiglia `ACT-T01`–`ACT-T31` con varianti `a/b/c`; il parser della mappa trova 34 righe ID. Il verifier corrente confronta gli insiemi dei nomi stato, non le tuple degli archi. La review identifica divergenza a livello di archi: `ACT-T22` e `ACT-T27` non rappresentano lo stesso percorso verso `OUTCOME_PENDING`; retry e compensation non applicano uniformemente `G-FRESHNESS ∧ G-DISPATCH`.

## Backend Assumption Register

`BA-01`–`BA-08` sono presenti. `BA-01` propone un fallback a due commit che modifica la semantica di atomicità state+outbox: non è adapter-only e deve essere trattato come `ARCHITECTURAL_ALTERNATIVE_REQUIRING_CHANGE_CONTROL`. Le altre assunzioni restano candidate e subordinate ai relativi conformance test; nessuna è dimostrata.

## Decisioni candidate e dipendenze

`DRAFT-A`–`DRAFT-I` sono nove bozze non approvate. Dipendenze minime già esplicite o causalmente necessarie: canonical mutation presuppone Action Contract; marking operator presuppone marking metamodel; emission safety e indeterminate recovery modificano la stessa safety chain; la relazione tra emission fence e CapabilityLease richiede conferma dell'authority. La direzione degli archi del DAG sarà definita senza ambiguità nel piano di remediation.

La classificazione dei gate in §7 deve essere ricostruita dal Decision Register: oltre a rimuovere `DEC-173/175` dall'elenco dei gate, vanno considerati i veri gate `DEC-049`, `DEC-078`, `DEC-136`, `DEC-164`, `DEC-185`, `DEC-195`, oggi omessi dall'elenco narrativo. Questa estensione è trattata nel piano come parte della stessa root cause di `DRF-015`, non come creazione di nuove decisioni.

## Gate FASE 1

`PASS`: mappa e conteggi sono riproducibili, il baseline digest coincide, il machine-readable artifact parsifica come JSON. Il gate non attesta coerenza architetturale della v1.1: i 15 `DRF-*` restano da riconciliare e correggere nella candidata.
