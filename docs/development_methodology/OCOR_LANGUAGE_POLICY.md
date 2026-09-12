# OCOR — Politica normativa dei linguaggi di programmazione

`DEC-212` — `CC-OCOR-LANGUAGE-POLICY`. Adottata sotto la modalità di implementazione
autorizzata (`DEC-210`) con mandato esplicito del Product Owner del 2026-09-12.

## 1. Perimetro e distinzione normativa

Questo documento fissa, per ogni parte del progetto, il **linguaggio di
implementazione** autorizzato, la sua versione pinnata alla patch, la motivazione
ancorata a un requisito o a una decisione approvata, le alternative vietate e la
condizione misurabile che da sola autorizzerebbe una migrazione futura.

**Due piani distinti, da non confondere in nessun documento o commit:**

1. **Profilo degli SDK generati (normativo, non toccato da questo documento).**
   `DEC-075` e `FR-047` fissano Python e TypeScript come SDK generati P0 per il PoC,
   con contratti REST/gRPC/eventi/MCP generati e `NFR-022` che impone identità di
   tipi, versioni, policy context, consistency token, error model e semantica di
   idempotenza tra SDK. `FR-048` differisce Rust e A2A a P2/Future
   (`CAPABILITY_DEFERRED`). Questo profilo **non è modificabile** da `DEC-212` né da
   alcuna misura di benchmark: è l'esito di una decisione approvata sull'interfaccia
   esterna del sistema, non sull'implementazione interna.
2. **Linguaggio di implementazione interno dei componenti (perimetro di questo
   documento).** Nessuna decisione approvata aveva mai fissato in quale linguaggio
   sono scritti il kernel, i componenti C1–C8, l'harness, i qualificatori, il
   generatore di contratti, gli adapter o l'infrastruttura. `DEC-212` fissa questo
   perimetro per la prima volta ed è l'unico che una futura migrazione di
   implementazione (Fase 3) può modificare, componente per componente, con una nuova
   decisione dedicata che preservi API pubblica e profilo SDK invariati.

## 2. Tabella normativa

Tutte le versioni Python/Node/ruff coincidono con `infra/toolchain.lock.json`
(acquisito 2026-09-03); le versioni dei servizi backend coincidono con
`infra/services.lock.json`. Dove il pin non esiste ancora nel lock, la colonna
"Versione pinnata" fissa la versione che le Fasi 2.1–2.3 di questo mandato devono
installare esattamente: una divergenza è un difetto di implementazione, non una
licenza a scegliere un'altra versione.

| # | Area | Linguaggio autorizzato | Versione pinnata (patch) | Motivazione (requisito/decisione) | Alternative vietate |
|---|---|---|---|---|---|
| 1 | Kernel canonico e di digest (`ocor-runtime/src/ocor_runtime/canonical.py`) | Python | 3.12.11 | Unico linguaggio di C1–C8 per `AFF-001`/`AFF-005`; RFC 8785 canonicalization e SHA-256 digest devono restare nello stesso runtime del resto del kernel per non introdurre un confine di processo nel fast path L0 (`DEC-166`/`NFR-076`) | Qualsiasi altro linguaggio per lo stesso modulo; estensioni native non dichiarate da una decisione |
| 2 | Componenti C1–C8 (`ocor-runtime/src/ocor_runtime/c1_compiler.py` … `c8_agent.py`) | Python | 3.12.11 | `AFF-001` vincola gli import consentiti per modulo assumendo un unico runtime; `ARC-022`/`DEC-179` fissano ruoli logici indipendenti dal backend, non dal linguaggio | Riscrittura parziale in altro linguaggio di un singolo componente C1–C8 senza nuova decisione |
| 3 | Harness di verifica e validatori (`scripts/verify.py`, `scripts/validate_*.py`, `reports/tests/*.py`, oracoli degli spike G2 in `spikes/**`) | Python | 3.12.11 | Devono restare eseguibili senza build separata nell'ambiente `uv`/`.venv` già pinnato; `AFF-008`/`AFF-010` presuppongono introspezione AST Python (`ast.parse`); gli oracoli in `spikes/` (atomicità C3, fedeltà FSM, riproducibilità causale, delivery Kafka, partizione vettoriale) sono harness di verifica bounded per G2, non componenti di runtime | Shell script o altro linguaggio come sostituto delle verifiche fail-closed esistenti |
| 4 | Qualificatori dei servizi in `deploy/bootstrap/services/**/qualify*.py` | Python | 3.12.11 | Condividono il modello di evidenza content-addressed e i fixture di `scripts/ocor_bootstrap_lib.py`; `DEC-211` li tratta come tooling di sviluppo, non infrastruttura di produzione | Script di qualificazione in linguaggio diverso da quello dell'harness che consumano gli stessi fixture |
| 5 | Generatore di contratti (`ocor-runtime/tools/generate_contracts.py`) | Python | 3.12.11 | Unica sorgente di verità per `ocor_contracts.py`/`ocor_contracts.ts`/`contract-descriptor.json`; deve restare nello stesso runtime del resto della toolchain di build | Un secondo generatore, anche parziale, scritto in un altro linguaggio |
| 6 | SDK generati — profilo Python | Python | 3.12.11 (generazione); il pacchetto SDK dichiara il proprio `requires-python` compatibile a runtime dei consumatori | `DEC-075`/`FR-047` (P0, PoC) | Generazione manuale non derivata dal generatore |
| 7 | SDK generati — profilo TypeScript | TypeScript | 7.0.2 (compilatore `tsc`); Node 20.20.2 come runtime di build/test, coincidente con `infra/toolchain.lock.json` | `DEC-075`/`FR-047` (P0, PoC) impone il profilo; `NFR-022` impone identità di digest/errori/idempotenza tra SDK, verificabile solo se `ocor_contracts.ts` è realmente compilato da `tsc --strict`, non solo emesso come testo | Emissione di `.ts` non compilato come sostituto di un SDK reale; qualunque libreria di trascompilazione diversa da `tsc` per la verifica di conformità |
| 8 | Adapter verso TerminusDB, TypeDB, Jena/Fuseki, Kafka, Qdrant, PostgreSQL (`ocor-runtime/src/ocor_runtime/**/adapters/`) | Python | 3.12.11; librerie client: `psycopg` verso PostgreSQL 16, client Kafka verso `confluentinc/cp-kafka` 7.6.0, `qdrant-client` verso Qdrant 1.15.1, client TerminusDB verso 12.0.7-noroot, client TypeDB verso 3.12.3, client HTTP verso Apache Jena/Fuseki 6.2.0 (tutte le versioni backend da `infra/services.lock.json`) | `AFF-002`/`AFF-006` vincolano ogni client diretto al sotto-albero `adapters/`; `ARC-022`/`DEC-179` impongono ruoli logici (`VersionedAssertedState`, `LogicProjection`, `W3CBoundary`) indipendenti dal backend, realizzati come adapter sostituibili nello stesso linguaggio | Import diretto di un client backend fuori da `adapters/`; adapter scritti in un linguaggio diverso dal kernel che li invoca in-process |
| 9 | Policy OPA | Rego | Legato a OPA `1.20.1` (digest-pinned in `infra/services.lock.json`); nessuna versione di Rego è pinnata indipendentemente dal binario OPA | `NFR-081`/`DEC-174` (segregazione dei compiti, dual control) richiedono che le decisioni di autorizzazione siano dichiarative e verificabili fuori dal runtime applicativo | Logica di autorizzazione equivalente reimplementata in Python dentro il kernel invece che in policy Rego valutata da OPA |
| 10 | Infrastruttura e CI: GitHub Actions (`.github/workflows/*.yml`), Dockerfile (`infra/fuseki/Dockerfile`), Compose (`deploy/**/compose.yaml`), Kubernetes (`deploy/bootstrap/kubernetes/*.yaml`) | YAML (workflow/manifest) + Dockerfile syntax | GitHub Actions: sintassi corrente; `actions/setup-python`→3.12.11, `actions/setup-node`→20.20.2, ogni `uses:` pinnato al commit SHA per `DEC-211`; Dockerfile base image `eclipse-temurin@sha256:db1689535962d757a5adabf57387584ed543d38c0b9d1fe870123ea362ad73b0` | `DEC-181`/`ARC-023` (profilo strict-OSS, Kafka come backbone di riferimento); `DEC-211` (immagini digest-pinned, azioni commit-pinned) | Script di CI generati da un motore di terze parti che non produce YAML ispezionabile in Git; basi immagine non ufficiali o non digest-pinned |
| 11 | Formati dichiarativi: JSON Schema 2020-12 | JSON Schema (Draft 2020-12) | Draft 2020-12 esplicito in ogni `$schema` | `DEC-178`/`FR-168` (profilo di standard interoperabili) | Draft precedente o assente |
| 12 | Formati dichiarativi: OpenAPI | OpenAPI | 3.1.0 | `DEC-178`/`FR-169`; verificato da `scripts/verify.py` con `openapi-spec-validator` | OpenAPI 2.0/3.0.x |
| 13 | Formati dichiarativi: contratti RPC | Protocol Buffers | proto3; compilato con `grpcio-tools` 1.83.1 (già pinnato in `ocor-runtime/uv.lock`) | `DEC-178`/`FR-169` | proto2; gRPC-Web o altri IDL come sostituto del contratto canonico |
| 14 | Formati dichiarativi: grafo RDF | RDF 1.1 Turtle | Turtle (sintassi W3C RDF 1.1) | `DEC-178`/`FR-168` (import/export RDF 1.1 dichiarato) | JSON-LD come unico formato (ammesso in aggiunta, non in sostituzione, per `FR-168`) |
| 15 | Formati dichiarativi: validazione di grafo | SHACL | SHACL Core (W3C) | `DEC-178`/`FR-168` (validazione SHACL dichiarata) | ShEx o validatori proprietari come sostituto di SHACL per i contratti pubblicati |

## 3. Soglie di migrazione — fissate ora, prima di qualunque misura (Fase 3)

Le soglie seguenti sono le uniche condizioni che, se superate da un benchmark
riproducibile eseguito secondo `docs/development_methodology/OCOR_LANGUAGE_POLICY.md`
§3 e ancorato a `DEC-166`/`NFR-076` (budget ipotetico p95 < 50 ms per il fast path
L0) e `DEC-170`/`NFR-080` (regola di fissazione degli SLO, nessun tuning sul test),
autorizzano — da sole — l'apertura di una nuova decisione di migrazione per il
**solo** componente interessato. Sono fissate prima di eseguire qualunque misura,
per costruzione, così da escludere ogni tuning post-hoc.

| Componente | Soglia di migrazione | Ancoraggio |
|---|---|---|
| Kernel di canonicalizzazione RFC 8785 e digest | Mediana Python sul corpus di riferimento supera **3×** la mediana dell'oracolo Node.js pinnato sullo stesso corpus/hardware, **oppure** il p95 assoluto supera **2 ms** per documento al payload di riferimento (10 KB) | 2 ms equivale a più del 4% del budget ipotetico p95 < 50 ms di `NFR-076`; l'oracolo Node.js è già pinnato in CI per REM-0007 |
| Percorso di commit di C3 (canonicalizzazione + digest + scrittura atomica, esclusa latenza di rete esterna) | p95 supera **15 ms** al carico di riferimento del harness | 15 ms equivale al 30% del budget ipotetico p95 < 50 ms di `NFR-076` |
| Backbone eventi di C5 (pubblicazione fino ad ack, partizione pinnata di riferimento) | Throughput sostenuto sotto **5.000 messaggi/s** per partizione, **oppure** p95 pubblicazione-ack supera **20 ms** | 20 ms equivale al 40% del budget ipotetico p95 < 50 ms di `NFR-076`; il floor di throughput è scelto per restare ampiamente entro le capacità dichiarate di `confluentinc/cp-kafka` 7.6.0 su hardware di riferimento non specializzato |
| Proiezione di C4 | Projection lag p95 sotto carico sostenuto di riferimento supera **200 ms** | Budget di freshness implicito in `NFR-077` (branch/commit/watermark esposti devono restare utilizzabili per `at-least-commit`/`exact-at-commit` senza introdurre staleness percepibile oltre un ordine di grandezza rispetto al fast path) |

Nessuna soglia superata → esito `NO_MIGRATION_JUSTIFIED`, con i numeri pubblicati
nell'evidenza: è un esito corretto e non richiede alcuna azione ulteriore. Soglia
superata → si apre una nuova decisione per il solo componente, e si applica il
protocollo differenziale del mandato (suite byte-identica, property-based/fuzz,
doppia implementazione in albero, ripetizione del benchmark) prima di qualunque
merge.

## 4. Candidato segnalato, non deciso

La canonicalizzazione RFC 8785 riscrive in Python la semantica di
`Number.prototype.toString` di ECMAScript, incluse le soglie di esponente 21 e -7;
ha già richiesto la rimediazione `REM-0007` e un binario Node pinnato come oracolo
cross-language in CI. Questo è un candidato segnalato per la misura della Fase 3,
non una migrazione già decisa: si valuta con il benchmark e le soglie di questo
documento, non con l'aneddoto.

## 5. Evidence fence

`E1=0`, `E2=0`, zero requisiti globali `Verified`, `runtime_conformance`
`NOT_ESTABLISHED`, `PoC` e `Production` `NO-GO`. Nessuna voce di questa tabella
promuove un requisito, chiude un `OI-*`/`ASM-*`/`RSK-*`, o attiva una capability
differita (`CAP-*`). `FR-048`/Rust resta `CAPABILITY_DEFERRED`.
