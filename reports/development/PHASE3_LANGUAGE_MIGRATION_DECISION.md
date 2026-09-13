# Fase 3 — Harness di benchmark per la migrazione di linguaggio (CC-OCOR-DELIVERY-COMPLETION)

Autorità: `DEC-210`/`DEC-211`. Ancoraggio normativo:
`docs/development_methodology/OCOR_LANGUAGE_POLICY.md` §3 (soglie fissate
**prima** di qualunque misura). Evidenza sigillata:
`reports/benchmarks/phase3_language_migration_benchmark_20260912.json`
(harness: `scripts/run_language_migration_benchmark.py`; oracolo Node:
`ocor-runtime/sdk/typescript/src/cli/benchmark_canonicalize.ts`; corpus
sigillato: `reports/benchmarks/fixtures/phase3_canonical_corpus.json`,
`sha256=2ce8879bc8e5697a4f51e37a3ae1262da4995c2fdba7f2ba23e6e3e775da80b7`).

**Questo documento non è una decisione approvata.** Non promuove alcun
requisito, non chiude alcun `OI-*`/`ASM-*`/`RSK-*`, non autorizza una
migrazione. Prepara il pacchetto di decisione per il Product Owner, come
richiesto esplicitamente per le capability riservate (`NFR-081`/`DEC-174`).

## 1. Esito per componente

| # | Componente | Stato | Esito |
|---|---|---|---|
| 1 | Kernel di canonicalizzazione RFC 8785 e digest | `MEASURED` | **`MIGRATION_THRESHOLD_EXCEEDED`** |
| 2 | Percorso di commit di C3 | `NOT_YET_MEASURABLE` | — |
| 3 | Backbone eventi di C5 | `NOT_YET_MEASURABLE` | — |
| 4 | Proiezione di C4 | `NOT_YET_MEASURABLE` | — |

## 2. Componente 1 — misura reale

- Corpus: 200 documenti deterministici (seed `20260912`, LCG proprio non
  dipendente da `random.Random`), ciascuno ~10 KB serializzato
  (min 10000, max 10121, media 10054 byte) — il payload di riferimento
  esatto di §3.
- Ripetizioni per documento: 25 (mediana per documento su 25 chiamate
  back-to-back, esclusi I/O e `JSON.parse`/parsing di ingresso).
- Motore Python: `ocor_runtime.canonical.canonicalize_json` +
  `canonical_sha256` (stesso kernel sigillato di `OCOR-DEV-0007`).
- Oracolo Node: SDK TypeScript compilato reale (`tsc --strict`, Fase 2.3),
  stesso algoritmo (`canonicalizeJson`+`canonicalSha256` da
  `ocor-runtime/sdk/typescript/src/canonical.ts`), timing interno con
  `process.hrtime.bigint()` per isolare il costo di calcolo dall'overhead
  di sottoprocesso/IPC.
- Ambiente di misura (da disclosure, non hardware di riferimento
  dedicato): Linux, Python 3.12.14, Node v20.20.2, 14 CPU logiche. Questa è
  una limitazione dichiarata: la soglia richiede "lo stesso corpus/hardware"
  fra le due misure, soddisfatto (stesso processo host, stesso momento),
  ma non è un hardware di riferimento certificato — il segno e l'ordine di
  grandezza del risultato sono comunque significativi.

### Numeri (run sigillata)

| Metrica | Valore | Soglia | Esito |
|---|---:|---:|---|
| Mediana Python / mediana Node | **4.24×** (range osservato su 3 run: 4.24×–4.77×) | > 3× | **SUPERATA** |
| p95 assoluto Python (ms/documento) | 1.77 ms (range osservato: 1.77–1.96 ms) | > 2 ms | non superata |

La clausola di soglia è un OR: basta una delle due condizioni. Il rapporto
mediano supera stabilmente 3× su tre run consecutive con lo stesso corpus
sigillato — non è rumore di misura isolato.

## 3. Componenti 2–4 — non ancora misurabili (esito onesto, non un difetto)

- **Componente 2 (percorso di commit C3):** richiede un backend PostgreSQL
  reale, esattamente come la suite live di
  `ocor-runtime/tests/tasks/test_ocor_dev_0015.py`, `NOT_EXECUTED` in
  questo sandbox per lo stesso motivo già documentato (nessun PostgreSQL
  locale). Misurabile una volta cablato in un job CI con lo stesso servizio
  Postgres del job `integration-postgresql`.
- **Componente 3 (backbone eventi C5):** nessuna implementazione reale
  esiste ancora — `ocor_runtime.c5_actions` è l'FSM obsoleta a 32
  transizioni, non il backbone Kafka approvato (`OCOR-DEV-0040`/`0041`,
  WS-06, non ancora eseguiti), per
  `docs/planning/OCOR_CURRENT_STATE_BASELINE.json`.
- **Componente 4 (proiezione C4):** nessun adapter reale esiste ancora —
  `ocor_runtime.c4_marking` implementa solo il reticolo di marking, non un
  adapter TypeDB/Jena (`OCOR-DEV-0037`/`0038`, WS-05, non ancora eseguiti).

Riportare questi tre componenti come `NOT_YET_MEASURABLE`, con la ragione
precisa, è un esito parziale onesto e completo per questa iterazione — non
un sostituto di `NO_MIGRATION_JUSTIFIED`, che richiederebbe una misura
reale che qui non esiste ancora.

## 4. Perché nessuna migrazione viene eseguita ora

Il superamento della soglia per il componente 1 autorizza — per costruzione
di `OCOR_LANGUAGE_POLICY.md` §3 — **l'apertura di una nuova decisione di
migrazione per il solo componente interessato**, non l'esecuzione autonoma
della migrazione stessa. Una riscrittura del kernel di canonicalizzazione in
un altro linguaggio sostituirebbe un'architettura approvata (`AFF-001`:
"Unico linguaggio di C1–C8"; riga 1 e 2 della tabella normativa in
`OCOR_LANGUAGE_POLICY.md` §2) — una delle condizioni di escalation esplicite
del mandato (§5.4: "un cambiamento che sostituirebbe un'architettura
approvata"). Questa è quindi registrata come **escalation**, non esito
chiuso, ed è riservata alla decisione umana del Product Owner sotto dual
control (`NFR-081`/`DEC-174`), esattamente come promozione E1/E2, requisiti
`Verified` e `PoC-GO`/`Production readiness` restano riservati altrove in
questo mandato.

## 5. Escalation registrata

`PHASE3-COMPONENT1-CANONICAL-KERNEL-MIGRATION-THRESHOLD-EXCEEDED`
— non bloccante per la chiusura della Fase 3 come processo (il processo di
misura è stato eseguito correttamente per tutto ciò che è oggi misurabile);
bloccante per qualunque migrazione reale del kernel di canonicalizzazione,
che resta sospesa in attesa di:

1. Decisione esplicita del Product Owner se aprire o meno una nuova
   decisione di migrazione per questo solo componente.
2. Se aperta: applicazione del protocollo differenziale del mandato prima
   di qualunque merge — suite di conformità byte-identica (già esistente:
   `ocor-runtime/tests/sdk/test_typescript_sdk_conformance.py`, `NFR-022`),
   test property-based/fuzz sui confini RFC 8785 (oltre ai vettori
   `Appendix B` già coperti da `OCOR-DEV-0007`), doppia implementazione
   presente in albero durante la transizione, e ripetizione del benchmark
   su hardware di riferimento dichiarato.
3. Nessuna promozione di requisito, nessuna chiusura `OI-*`/`ASM-*`, nessun
   claim di conformità runtime deriva da questo esito.

## 6. Prossimi passi (non riservati)

- Cablare il componente 2 (percorso di commit C3) in un job CI con
  PostgreSQL reale per ottenere una misura effettiva (non fabbricata) non
  appena pianificato come propria iterazione.
- Rieseguire i componenti 3 e 4 non appena i relativi task di backlog
  (`OCOR-DEV-0037`/`0038` per C4, `OCOR-DEV-0040`/`0041` per C5) producono
  un'implementazione reale da misurare.
- Procedere con l'esecuzione del backlog via
  `./.venv/bin/python3 scripts/ocor_autonomous_delivery.py --next` a
  partire da `OCOR-DEV-0079`, come da sequenza del mandato — l'escalation
  del componente 1 non blocca questo passo.

## 7. Evidence fence

`E1=0`, `E2=0`, zero requisiti globali `Verified`, `runtime_conformance`
`NOT_ESTABLISHED`, `PoC` e `Production` `NO-GO`. Nessuna voce di questo
documento promuove un requisito, chiude un `OI-*`/`ASM-*`/`RSK-*`, attiva
una capability differita, o approva una migrazione.

## 8. Disposizione del Product Owner sull'escalation (2026-09-13)

Il Product Owner ha letto questo documento e registra qui la propria
decisione su `PHASE3-COMPONENT1-CANONICAL-KERNEL-MIGRATION-THRESHOLD-EXCEEDED`
(§5), che il paragrafo restava in attesa di lui. Questa sezione è un'aggiunta
in coda: nessun numero delle sezioni 1–7 è stato riscritto.

### 8.1 Decisione

**Non si apre una decisione di migrazione per il kernel di canonicalizzazione.**
La disposizione è **RINVIATA**, non respinta: il candidato di §4 resta
registrato e la misura di §2 resta valida.

### 8.2 Motivazione

1. Il 4,24× è un rapporto relativo. La seconda condizione della stessa
   clausola, il p95 assoluto, non è stata superata: 1,77 ms per documento da
   10 KB contro una soglia di 2 ms.
2. Il budget di 50 ms da cui l'intera scala delle soglie è derivata è
   un'ipotesi di lavoro, non un requisito approvato. NFR-076 classifica i
   workload in L0, L1 e L2 e non fissa alcun budget di latenza, e OI-024 è
   aperto.
3. NFR-080 richiede che ogni SLO sia definito per classe di servizio,
   percentile, finestra, workload, ambiente e comportamento al superamento.
   Nessuno SLO pre-registrato in questa forma esiste oggi per il fast path
   L0.
4. Migrare ora sostituirebbe architettura approvata, AFF-001 e le righe 1 e 2
   della tabella normativa di `OCOR_LANGUAGE_POLICY.md`, per un guadagno che
   nessun requisito approvato richiede.

### 8.3 Condizione di riapertura (falsificabile)

La disposizione si riapre automaticamente al verificarsi di una qualsiasi di
queste:

a. viene registrato uno SLO reale per il fast path L0 nella forma richiesta
   da `NFR-080`, che superseda o chiuda `OI-024` per via governata, e la
   misura sigillata lo viola;
b. il p95 assoluto sul corpus sigillato supera i 2 ms in una run
   riproducibile;
c. i componenti 2, 3 o 4 diventano misurabili e superano le rispettive
   soglie.

### 8.4 Vincoli osservati da questa disposizione

- Le soglie del §3 di `OCOR_LANGUAGE_POLICY.md` non sono state toccate: sono
  state fissate prima della misura, e la loro immutabilità è ciò che rende il
  risultato credibile. Questa disposizione cambia l'esito applicato al
  candidato, non il metro con cui è stato misurato.
- `OI-024` non è chiuso da questa disposizione. Nessun `ASM-*`/`RSK-*` è
  modificato.
- Nessuna modifica al codice del kernel di canonicalizzazione
  (`ocor-runtime/src/ocor_runtime/canonical.py`), che resta quello sigillato
  e misurato in §2.
- Nessuna promozione di `E1`, `E2` o requisiti a `Verified`, nessun claim di
  conformità runtime deriva da questa disposizione.

### 8.5 Verifica del record decisionale formale

Il Product Owner ha chiesto di verificare se la metodologia del repository
richiede un record decisionale formale (un nuovo identificativo `DEC-*`, un
ARA Decision Record, una voce nel Decision Register) per una disposizione di
questo tipo, e di allocare il prossimo identificativo effettivamente libero
solo se richiesto.

**Verificato: non è richiesto.** Il repository distingue due categorie
distinte:

- L'**adozione di una nuova decisione di governance** (es. `DEC-210`,
  `DEC-211`, `DEC-212`) riceve un identificativo `DEC-*`, un ARA Decision
  Record e una voce nel Decision Register — così è stato per `DEC-212`
  (`OCOR_Decision_Register_v1.6_APPROVED.md`, riga `DEC-212`), che ha
  adottato una nuova politica normativa vincolante.
- La **disposizione di un'escalation** sollevata durante l'esecuzione
  autonoma non riceve un identificativo `DEC-*`: le escalation precedenti di
  questo stesso mandato (`PHASE2-4-BACKLOG-GENERATOR-DRIFT`, risolta in
  PR #67; `GITHUB-BRANCH-PROTECTION-001`, tracciata come compensata) sono
  state chiuse o dispositate aggiornando i documenti e i file di stato
  esistenti, senza mai coniare un nuovo `DEC-*`.

Questa disposizione rientra nella seconda categoria: non adotta alcuna nuova
politica, non modifica alcuna soglia, non autorizza alcuna migrazione — resta
lo status quo, con la sola differenza che l'escalation è ora dispositata
anziché aperta. Per costruzione (§8.4) non c'è nulla da registrare come nuova
decisione di governance. Coerentemente con l'istruzione del Product Owner,
non è stato coniato alcun identificativo: sono stati aggiornati
esclusivamente i documenti esistenti (questa sezione,
`reports/development/EXECUTION_STATE.json`,
`reports/development/MODEL_HANDOFF.json`).

### 8.6 Stato dell'escalation

`PHASE3-COMPONENT1-CANONICAL-KERNEL-MIGRATION-THRESHOLD-EXCEEDED`:
`OPEN` → **`DISPOSED_DEFERRED`**. Non bloccante per l'esecuzione del backlog,
come già era; resta riservata al Product Owner l'eventuale riapertura secondo
la condizione falsificabile di §8.3.

### 8.7 Evidence fence (invariato)

`E1=0`, `E2=0`, zero requisiti globali `Verified`, `runtime_conformance`
`NOT_ESTABLISHED`, `PoC` e `Production` `NO-GO`. Questa sezione non promuove
alcun requisito, non chiude `OI-024` né alcun `ASM-*`/`RSK-*`, non attiva
alcuna capability differita, non approva alcuna migrazione, non modifica il
codice del kernel sigillato.
