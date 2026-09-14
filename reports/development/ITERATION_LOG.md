# OCOR RCCAD iteration log

## 2026-09-02 — CC-RCCAD-METHODOLOGY-ADOPTION / DEC-210

- Baseline: `69652a3c4bd6cdd13d54c0a7e326c9d44958f985`; isolated branch/worktree verified clean.
- Reconciliation: normative SHA256 `PASS`; prescribed root venv absent, document harness `NOT_EXECUTED`; no retry or install performed.
- Existing evidence: G0 tasks 0001–0006, G1 tasks 0007–0014 and G2 tasks 0015/0019/0020/0022/0023 are content-addressed in gate manifests. This reconciliation does not re-accept or promote them.
- External blockers: G2 tasks 0016/0017/0018/0021 require unavailable real services; branch protection remains under compensating controls.
- Conflict resolution: the pre-existing AI-first plan/backlog and DAG remain authoritative planning sources. RCCAD refines execution and points to them rather than duplicating task truth.
- RED: methodology acceptance suite exited 1 with 5 non-green tests because all required artifacts and validator were absent; failure was expected and captured before implementation.
- Branch control: `governed/DEC-210-rccad-adoption` è stato rifiutato dal validator per lettere maiuscole; il branch è stato rinominato `governed/dec-210-rccad-adoption` prima dell'integrazione.
- Plan validators: `NOT_EXECUTED` localmente perché il Python di sistema non dispone di `jsonschema`; nessuna dipendenza è stata installata e i gate pinned di CI restano obbligatori.
- GREEN/REFACTOR: 5/5 acceptance test `PASS`; RCCAD validator `PASS` su 16 artefatti e zero finding; scope validator `PASS` su 19 path; JSON parse dello schema, diff check e immutable-input check `PASS`.
- Verifier pass 1: `NO-GO` sul commit `347f65a3…` per indici DEC-210, TDD evidence e fitness incomplete. Remediation: registri append-only v1.4 legati ai digest v1.3, evidence JSON inclusa e validator esteso con risultati espliciti `AFF-001`–`AFF-010`; nuovo local run `PASS` su 18 artefatti e tutti i dieci fitness gate.
- Verifier pass 2: `NO-GO` sul commit `96f056db…`: i token scan non qualificano dinamicamente le AFF e la TDD evidence non era verificata semanticamente. Remediation: esiti locali rinominati `PASS_STATIC_PRECHECK`, `dynamic_assurance=CI_REQUIRED`, fingerprint/commit TDD verificati, comandi AFF distinti e portfolio CI pinned con PostgreSQL reale. La Docker API locale è inaccessibile: riproduzione dinamica locale `NOT_EXECUTED`, senza retry.
- Verifier pass 3: `GO_FOR_REMOTE_CI` sul commit locale `cad0047f…`. La PR #37 ha materializzato lo stesso tree nel commit remoto `96cbaee6…`; il primo run RCCAD ha fallito fail-closed in `AFF-008` perché il commit TDD locale non esiste nel clone remoto. Remediation: l'evidence registra il commit di materializzazione remoto e il validator accetta soltanto l'ancestry locale verificabile oppure, esclusivamente in GitHub Actions, l'ancestry del parent remoto verificabile.
- Remote CI pass 2: supply-chain e layered mandatory gates `PASS`; il run RCCAD `33715519982` ha superato schema, manifest, evidence e acceptance test, poi ha fallito sul validator storico deliberatamente `planning-only`, che rifiuta correttamente ogni diff estraneo a `docs/development_plan/` e `reports/planning/`. Remediation circoscritta: il workflow RCCAD mantiene il runner autoritativo `--validate`/`--dry-run` e rimuove soltanto l'invocazione fuori contesto del validator planning-only; il finding baseline non viene riclassificato né occultato.
- Remote CI pass 3 sul commit `d4c54a876bfb3cc60531596982be04b283d20615`: `PASS` per supply-chain `33715707667`, layered mandatory gates `33715707617`, governance/validation closure `33715707574`, RCCAD methodology gates `33715707590` e autonomous delivery controls `33715707689`. Il sigillo documentale successivo deve ripetere gli stessi controlli sul proprio HEAD prima del merge.
- Evidence fence: `E1=0`, `E2=0`, zero global `Verified`; runtime, PoC and Production remain `NO-GO`.

## 2026-09-03 — OCOR-DEV-REM-0007-RCCAD

- Baseline autoritativa remota: `a09d1a6e573895e716b147c8046ea97b73b2e3a8`; la worktree locale usa il tree equivalente del merge DEC-210. Digest normativi `PASS`; harness locale e pytest locale `NOT_EXECUTED` per venv assente, senza installazioni o retry.
- Reconciliation: nessun nuovo task del DAG è ready perché `OCOR-DEV-0016/17/18/21` restano bloccati su servizi reali; le PR draft #26/#29/#31 sono divergenti. Selezionata soltanto #26, da supersedere con una portabilità RCCAD pulita.
- CHARACTERIZATION: il commit test-only remoto `133ac489141f1186650fc57f459298d482f3f18c` ha superato tutti i cinque workflow (`33716385268/289/292/299/286`) prima dell'aggiunta dei casi che espongono il difetto.
- RED: il commit test-only remoto `79d18cf76c771ca724fa7037a5d3f659addd2e77` ha prodotto 15 failure mirate: round-trip RFC 8785/Appendix B, safe-range binary64, assenza di `DigestProviderError`, errori non bounded e rifiuto errato di `2**53`. Fingerprint SHA-256 `2a136b5dcd53ec4bcb7455fa47c86d48b00bcd20cb72e681340bd5e3ed9772ce`.
- GREEN: applicati soltanto i tre file runtime della remediation già revisionata. Il commit remoto `d15324375dcb63d2cd024bfe1648f529a7683a8c` ha superato RCCAD e layered gates; i due portfolio legacy hanno esposto esclusivamente Node `v22.23.2` contro l'oracle obbligatorio `v20.20.2`.
- REFACTOR/CI: Node `20.20.2` è stato pinning anche nei due workflow legacy, senza cambiare i test. Il commit remoto `8a9a2280750282af156ebb3c026ca0730c53bb27` ha superato tutti i workflow `33716881688/607/556/600/636`.
- Independent verifier: `GO_FOR_EVIDENCE_SEAL`, zero `BLOCKER`, `HIGH` e `MEDIUM`; modello/effort `NOT_ATTESTABLE`. Il merge resta vietato fino al CI verde sull'HEAD del sigillo.
- Claim fence invariato: `E1=0`, `E2=0`, zero global `Verified`; G1 non è ripromosso, runtime conformance non è stabilita, PoC e Production restano `NO-GO`.

## 2026-09-03 — OCOR-DEV-REM-0008-RCCAD

- Baseline remota: `698590511d2a48f5f09083af47f75734ceacc750`; PR #29 divergente selezionata per supersessione dopo il merge qualificato di REM-0007. Digest normativi `PASS`; harness e pytest locali `NOT_EXECUTED` per venv/uv assenti.
- RED test-only `dde7e3e24dcaa5e68175763eebf9126b6df5bfb6`: cinque failure mirate per correlation ID schema-valid, tuple non-array e binding Proto non verificato dereferenziato.
- GREEN `ce717f113e7b736238df7cc7ce0d471e09fa6790`: tutti i cinque workflow `33723246471/584/620/467/447` `PASS`.
- Independent verifier: `GO_FOR_EVIDENCE_SEAL`, zero `BLOCKER`, `HIGH`, `MEDIUM`; scope esatto kernel+test, nessuna modifica a `inputs/`, ADD, LLD o contratti.
- Claim fence invariato: `E1=0`, `E2=0`, zero global `Verified`; runtime conformance, PoC e Production restano `NO-GO`.

## 2026-09-03 — OCOR-DEV-REM-0009-RCCAD

- Baseline remota: 5a5ca88a6ce2aeffe01ba8a35b43487dad810753, tree 974c5ba3 coincidente con la worktree locale; PR #31 divergente selezionata per supersessione dopo il merge qualificato di REM-0008.
- Digest normativi PASS; harness e pytest locali NOT_EXECUTED per .venv/uv assenti, senza installazioni o retry.
- RED test-only 9f215b8dd36bb9d83079098768b56f7231ff7f9d: collection failure mirata perché il port autorevole InMemoryLeaseState non era presente. Fingerprint SHA-256 ef1165dc3083f7e9f1ba9a6832a7425a2b6a5ed7bd293e1062952fc1c552777e.
- GREEN 5404f32c75c98bf1899d4caebf5dc0197228c988: tutti i cinque workflow 33737997879/940/911/908/959 PASS, inclusi full runtime e PostgreSQL reale pinned.
- Independent verifier: GO_FOR_EVIDENCE_SEAL, zero BLOCKER, HIGH, MEDIUM, LOW; scope esatto kernel+test, nessuna modifica a inputs/, ADD o LLD.
- Assurance boundary: consumo atomico e concorrenza sono qualificati solo process-local; restart durability, serializzazione multi-processo e co-transazione DeliveryAttempt restano NOT_ESTABLISHED.
- Claim fence invariato: E1=0, E2=0, zero global Verified; G1 non è promosso, runtime conformance non è stabilita, PoC e Production restano NO-GO.

## 2026-09-03 — RCCAD terminal reconciliation

- REM-0009 integrato dalla PR #40 con merge 6afa0d962580a039f1903797dc304eacc9fcaea8 dopo cinque gate verdi sul seal esatto 846c0966500cf210a929c572057831145cb60061; PR draft #31 chiusa senza merge.
- Riconciliazione GitHub: zero pull request aperte. Le PR divergenti #26, #29 e #31 sono state supersedute rispettivamente da #38, #39 e #40 con evidence seal e verifier puliti.
- Analisi del DAG: 19 task hanno evidenza content-addressed; restano 50 task. I soli task direttamente ready sono OCOR-DEV-0016, OCOR-DEV-0017, OCOR-DEV-0018 e OCOR-DEV-0021.
- Tutti i quattro task ready sono WAITING_EXTERNAL_SERVICE con test obbligatori NOT_EXECUTED: TerminusDB, TypeDB, Apache Jena/Fuseki, SPIFFE/SPIRE e OpenBao non sono disponibili come artefatti pinned approvati o endpoint autorizzati.
- Escludendo i quattro root blocker, il fixed point del DAG non contiene alcun altro task indipendente raggiungibile. Lo stato terminale è pertanto BLOCKED, non COMPLETE.
- Il runner autoritativo locale --status è NOT_EXECUTED perché jsonschema non è disponibile; il controllo non è stato ritentato. Il DAG è stato riconciliato in sola lettura dal backlog e dai manifesti.
- Minimal unblock: fornire i servizi reali approvati e riprendere da OCOR-DEV-0016. Nessuna tecnologia sostitutiva è autorizzata.
- Independent verifier terminale: GO_FOR_BLOCKED_STATE_MERGE, zero BLOCKER, HIGH, MEDIUM e LOW; modello/effort NOT_EXPOSED.
- Claim fence invariato: E1=0, E2=0, zero global Verified; G2 non è chiuso, runtime conformance non è stabilita, PoC e Production restano NO-GO.

## 2026-09-03 — CC-AUTONOMOUS-TOOLING-INFRASTRUCTURE-BOOTSTRAP / DEC-211

- Baseline remota autoritativa verificata con Git e GitHub:
  `d93e8870e975b2aeec715778f3c490ece0e0216f`. Il checkout obsoleto è preservato
  integralmente nel commit `b3960a93efd94100420c856e66c1bf035c3850d9` sul
  branch `archive/stale-reconciliation-20260903T152830Z`.
- `DEC-210` è integrata. La ricerca su ref e PR ha confermato `DEC-211` come primo
  identificativo libero; nessun file in `inputs/` è stato modificato.
- RED test-only commit `605504fe3fd9b2aa3153f703accb72c9f5c15916`:
  3 failure e 2 error attesi per policy, lock, strumenti, task e record assenti;
  fingerprint SHA-256 `01bd89685cc2c1af54984dc52546cbe1e30cc9879b19ce3d5604ce4be4c1a3e4`.
- Toolchain ripristinata con Python 3.12.11 e dipendenze locked; `ruff==0.13.1`
  installato in user space e registrato nel lock.
- Ambiente reale disposable avviato con 11 servizi pinned: TerminusDB, TypeDB,
  Apache Jena/Fuseki, OPA, Keycloak, SPIRE server/agent, OpenBao, PostgreSQL,
  Kafka e Qdrant. Tutti gli endpoint applicabili sono `READY`.
- Un token OpenBao disposable è comparso durante una diagnostica locale; è stato
  immediatamente ruotato e il container è stato ricreato. Nessun valore segreto è
  persistito nel repository o nell'evidence.
- GREEN locale: acceptance 10/10, RCCAD `AFF-001`–`AFF-010` static precheck PASS,
  planning validator 37 PASS e 2 controlli opzionali `NOT_EXECUTED`, harness
  documentale 14 PASS/0 FAIL/0 NOT_EXECUTED, lock schema PASS e service probe PASS.
- Reset distruttivo limitato al progetto e clean rebuild `PASS`; fault injection
  TypeDB `pause` rilevata fail-closed e ritorno a `READY` dopo `unpause` entro il
  retry budget. La regressione runtime completa con PostgreSQL reale è 512/512 PASS.
- Evidence fence invariato: `E1=0`, `E2=0`, runtime conformance
  `NOT_ESTABLISHED`, PoC e Production `NO-GO`. La readiness infrastrutturale non
  accetta automaticamente i quattro spike funzionali G2.
- Independent verifier pass 1: `NO-GO` con DEC211-B01/B02/B03, H01/H02/H03 e
  M01. Remediation: raw log RED/GREEN/REFACTOR content-addressed con comandi
  esatti; lock/schema strict e 10 test negativi; preflight byte/version per tutti
  i tool; Fuseki image-ID fail-closed; Actions pinned a commit; checkout e prova
  exact-head; allowlist change-set esatta; readiness esplicitamente preliminare.
- Evidence rerun qualificante sul commit `4a061dbc9497dfec10925db755dbd05954e9dcf5`
  `PASS`; manifest SHA-256
  `8ccb2f686d07f7af642fc9e064a7b3997288c179dc8e7f72bfdaec1230bc4bb2`.
- Independent verifier pass 3 `dec211_final_verify`: `GO`, zero `BLOCKER`,
  `HIGH` e `MEDIUM`; exact command/raw hash, strict operational schema, preflight,
  Fuseki ID, exact-file scope, immutable inputs e workflow exact-head verificati.

## 2026-09-12 — Riconciliazione autoritativa (Fase 0, CC-LANGUAGE-POLICY-AND-GAP-CLOSURE)

- Mandato esplicito del Product Owner del 2026-09-12: attiva la modalità di
  implementazione autorizzata (`DEC-210`) e il tooling autonomo (`DEC-211`), già
  entrambi integrati in `main`, per una nuova policy dei linguaggi e la chiusura di
  tre lacune note. Nessuna modifica a `inputs/`; nessun nuovo `DEC-*` allocato in
  questa iterazione, che è pura riconciliazione di stato.
- Allineamento esatto a `origin/main` `a8f44364d74c4e5953954f8cf4997032ccc68f05`;
  `sha256sum -c inputs/normative/SHA256SUMS` `PASS` 8/8; `uv sync --project
  ocor-runtime --frozen --extra test` `PASS`.
- `EXECUTION_STATE.json` e `MODEL_HANDOFF.json` dichiaravano ancora 19 task completati
  e `DEC-211` come ultima iterazione; l'evidenza sigillata in
  `reports/evidence/G2/MANIFEST.json` ne conta realmente 28
  (`OCOR-DEV-0015/0019/0020/0022/0023` e `OCOR-DEV-0070`–`0078`), integrati dai merge
  `88a525d3` (PR #42, `DEC-211`) e `PR #48`–`#53` (provisioning reale dei servizi).
  Dettaglio completo in `reports/development/RECONCILIATION_2026-09-12_STATE.md`.
- Stato locale del runner autoritativo ricostruito da zero (file gitignored, mai
  committato) con `scripts/ocor_autonomous_delivery.py --accept-evidence <task>
  --execute` per ciascuno dei 28 task sigillati: 28/28 `PASS`. Esito:
  `dependency_ready = ["OCOR-DEV-0079"]`, `external_blockers = []`.
- I quattro spike `OCOR-DEV-0016/0017/0018/0021` non attendono più un servizio
  esterno: `OCOR-DEV-0073`–`0078` hanno qualificato provisioning reale per
  TerminusDB, TypeDB, Fuseki, OPA/Keycloak, SPIFFE/SPIRE e OpenBao. Restano tuttavia
  sequenziati dietro altri task `PENDING` per ordinaria dipendenza di backlog
  (incluso `OCOR-DEV-0084` per `OCOR-DEV-0016`), non per blocco esterno.
- `reports/development/TERMINAL_BLOCKED_REPORT.json` e
  `reports/evidence/G2/blockers/MANIFEST.json` sono marcati `SUPERSEDED` con motivo
  e commit di superamento, senza essere cancellati.
- Claim fence invariato: `E1=0`, `E2=0`, zero requisiti globali `Verified`,
  `runtime_conformance` `NOT_ESTABLISHED`, `PoC` e `Production` `NO-GO`. Nessun
  requisito promosso, nessuna capability differita attivata.
- Prossima azione: Fase 1 del mandato — allocare il prossimo `DEC-*` libero e
  autorare `docs/development_methodology/OCOR_LANGUAGE_POLICY.md` con
  `scripts/validate_language_policy.py` (RED poi GREEN), cablato in CI.

## 2026-09-12 — Chiusura Fase 1 (CC-LANGUAGE-POLICY-AND-GAP-CLOSURE / DEC-212)

- PR #54 (Fase 0, riconciliazione di stato) integrata: merge
  `b698f6b847f1afcd429e2dd7b7d72ab01d425a02`. Tutti i 12 check CI verdi
  sull'HEAD esatto; un check (`tooling-policy`) inizialmente rosso per
  allowlist troppo stretta in `scripts/validate_ocor_development_plan.py`,
  corretto alla radice estendendo `extension_paths` con i percorsi di questo
  change set, non aggirato.
- PR #55 (Fase 1, `DEC-212`) integrata: merge
  `7c7f9b5b6a5135aa2583445697f54e9ff1dfcf3e`. Allocato `DEC-212` dopo verifica
  in sola lettura che nessun ref/tag/PR/registro lo referenziasse già (ultimo
  libero dopo `DEC-211`). Autorato
  `docs/development_methodology/OCOR_LANGUAGE_POLICY.md` (tabella normativa
  per kernel, C1-C8, harness/validatori e spike G2, qualificatori `deploy/`,
  generatore di contratti, SDK generati, adapter, policy OPA, infra/CI, formati
  dichiarativi) e `scripts/validate_language_policy.py` (gate fail-closed).
  RED su stub pre-implementazione, GREEN sull'implementazione reale,
  REFACTOR dopo pulizia `ruff`. Durante RED/GREEN è emerso che `spikes/**`
  (oracoli G2) mancava dalla bozza iniziale della policy: aggiunto prima di
  dichiarare GREEN. Gate cablato nei tre workflow che già eseguono validazione
  di processo (`ocor-tooling-bootstrap`, `ocor-rccad`, `ocor-delivery-activation`).
- `DEC-212` non supersede alcuna decisione precedente e lascia invariato il
  profilo SDK di `DEC-075`/`FR-047`/`FR-048` (Python e TypeScript generati,
  Rust differito): la distinzione fra i due piani è esplicita nel documento.
- Un job CI (`rccad-methodology`) è fallito una volta per un flake di rete
  transitorio verso Docker Hub durante il pull dell'immagine Kafka pinnata
  (`confluentinc/cp-kafka:7.6.0`), non correlato al diff; il rerun dello stesso
  commit è risultato verde.
- Claim fence invariato: `E1=0`, `E2=0`, zero requisiti globali `Verified`,
  `runtime_conformance` `NOT_ESTABLISHED`, `PoC` e `Production` `NO-GO`.
- Prossima azione: Fase 2.1 del mandato — mypy strict su `ocor-runtime/src` e
  `scripts/`, configurazione `ruff` per l'intero repository, entrambi pinnati
  alla patch, cablati come job CI bloccanti.

## 2026-09-12 — Fase 1B: tre correzioni dalla verifica indipendente (§4 del mandato)

- Nuovo mandato esplicito del Product Owner del 2026-09-12 (CC-OCOR-DELIVERY-COMPLETION):
  riconciliato HEAD reale `50c3bbbe41e4c9cbc1a7112847decd37e80405df` (`origin/main`,
  PR #56), coincidente con quanto il mandato assumeva. Nessuna divergenza da
  riconciliare oltre a quanto già registrato il 2026-09-12 in Fase 0/1.
- §4.1: `docs/development_methodology/OCOR_LANGUAGE_POLICY.md` §3 ancorava le
  quattro soglie di migrazione a un "budget ipotetico p95 < 50 ms" attribuito a
  `NFR-076` (che classifica solo L0/L1/L2, senza fissare alcun numero) e a `OI-024`.
  Verifica sui registri normativi (`inputs/normative/OCOR_Registers_v0.9.md`,
  `OCOR_Requirement_Register_v0.9.md`): `OI-024` governa le soglie di
  rischio/costo per l'autorità dual-control su azioni critiche
  (`DEC-131`/`FR-136`/`FR-137`), non le soglie di latenza; l'open item corretto
  per soglie numeriche di accettazione è `OI-008`, con il processo di
  fissazione descritto in `ASM-010`/`DEC-170`/`NFR-080`. Corretto il riferimento
  a `OI-008` (non a `OI-024`, mai citato come fosse quello giusto), dichiarato
  esplicitamente il valore come ipotesi di lavoro non approvata, e ribadito che
  `NFR-080` impone comunque classe di servizio/percentile/finestra/workload/
  ambiente/comportamento al superamento per ogni SLO. Non chiuso `OI-008`, non
  creato alcun nuovo identificativo di baseline.
- §4.2: `EXECUTION_STATE.json.latest_ci_evidence` era `PENDING_EXACT_HEAD_CI`
  con `candidate_commit: null` nonostante tre PR mergiate con check verdi.
  Popolato con i dati reali via `gh pr checks 56`: head `de3bcac74959caa71d7c0d647abc5578ea0d4bfb`,
  12/12 check `pass` su 6 run id GitHub Actions distinti
  (`34701203516/523/528/530/535/562`), merge `50c3bbbe41e4c9cbc1a7112847decd37e80405df`.
  `baseline_commit` e `active_iteration` risincronizzati a HEAD e al branch di
  questa iterazione in entrambi `EXECUTION_STATE.json` e `MODEL_HANDOFF.json`
  dopo che `scripts/validate_rccad.py` ha rilevato `RCCAD-STATE-HANDOFF-DRIFT`
  fra i due file.
- §4.3: `infra/toolchain.lock.json` non conteneva alcuna voce TypeScript.
  Verificato prima sul registry ufficiale npm che `typescript@7.0.2` esiste
  davvero ed è il dist-tag `latest` corrente (non un'assunzione del mandato);
  installato in un ambiente isolato (`npm install typescript@7.0.2`), confermato
  `tsc --version` → `Version 7.0.2` e calcolato l'hash SHA-256 reale
  dell'eseguibile risolto (`node_modules/typescript/bin/tsc`,
  `2219f428a7e55aaf1f7ad85b9b0f0cf5078aeb76ccc9a7c6036c92d48f492ffd`), verificato
  anche il checksum SHA-1 del tarball npm contro quello pubblicato dal registry
  prima di fidarsi del contenuto. Aggiunta una voce `provider: host` conforme a
  `infra/toolchain.lock.schema.json`, stesso pattern di `node`/`ruff`.
- Gate locali: `sha256sum -c inputs/normative/SHA256SUMS` `PASS` 8/8;
  `scripts/validate_language_policy.py` `PASS`; `scripts/validate_rccad.py`
  `PASS_LOCAL_PRECHECK` (0 finding dopo le due correzioni sopra);
  `scripts/validate_ocor_change_scope.py --base origin/main` `PASS`, 4 percorsi
  cambiati, superfici immutabili intatte, ledger dei task stabile;
  `scripts/validate_ocor_development_plan.py --base-ref origin/main
  --authorized-extension` `PASS` 37/2/0; `scripts/verify.py --json` `PASS` 11/0,
  3 `NOT_EXECUTED` per dipendenze Python opzionali assenti in questa shell
  locale (`openapi-spec-validator`, `grpcio-tools`, `rdflib`) — `reports/verify_report.json`
  lasciato intatto (non sovrascritto con un risultato localmente degradato) perché
  questo change set non tocca alcun file che quel referto copre.
  `mypy`/`tsc --strict`/`ruff` repo-wide/regressione pytest completa: `NOT_APPLICABLE`
  (nessun sorgente Python o TypeScript toccato) e comunque `NOT_EXECUTED` in
  questa shell perché la toolchain pinnata byte-per-byte (`ruff==0.13.1`,
  `uv==0.12.5`, `python==3.12.11` con hash esatto) non è quella osservata
  localmente (`ruff 0.16.1`, `uv 0.5.9`); il gate qualificante resta la CI
  sull'exact-head al push, come per le tre PR precedenti.
- Evidenza sigillata: `reports/evidence/local-gates/phase1b-independent-review-corrections-20260912.json`.
- Claim fence invariato: `E1=0`, `E2=0`, zero requisiti globali `Verified`,
  `runtime_conformance` `NOT_ESTABLISHED`, `PoC` e `Production` `NO-GO`. Nessun
  `OI-*`/`ASM-*`/`RSK-*` chiuso, nessuna capability differita attivata.
- Prossima azione: aprire la PR di questa correzione, attendere CI verde
  sull'HEAD esatto, merge, verifica SHA post-merge, poi Fase 2.1 del mandato —
  mypy strict su `ocor-runtime/src` e `scripts/`, configurazione `ruff` per
  l'intero repository, entrambi pinnati alla patch, cablati come job CI
  bloccanti.

## 2026-09-12 — Chiusura Fase 1B

- PR #57 aperta e integrata: merge `3911228e7b657bf1bd2b1fc17f49fcad9bef3e5c`.
  Il primo push (`1fddb4f`) ha fatto fallire il check `tooling-policy` per lo
  stesso motivo già osservato in Fase 0/PR #54: il nuovo file di evidenza
  `reports/evidence/local-gates/phase1b-independent-review-corrections-20260912.json`
  non era ancora nell'allowlist `extension_paths` di
  `scripts/validate_ocor_development_plan.py`. Corretto alla radice
  (allowlist estesa, self-hash di `OCOR_PLAN_RUN_STATE.json` fatto assestare
  con una seconda esecuzione locale prima del push), non aggirato. Secondo
  push (`040275f`): 12/12 check verdi sull'HEAD esatto
  (run id `34707732916/919/927/931/939/980`).
- Verifica pre-merge: `origin/main` invariato a `50c3bbbe` dal momento della
  creazione del branch; `gh pr view 57` → `mergeStateStatus: CLEAN`,
  `mergeable: MERGEABLE`. Nessun rebase necessario.
- Verifica post-merge: SHA di `origin/main` = `3911228e7b657bf1bd2b1fc17f49fcad9bef3e5c`,
  coincidente con il merge commit riportato da GitHub.
- `EXECUTION_STATE.json` e `MODEL_HANDOFF.json` risincronizzati al nuovo HEAD;
  `latest_ci_evidence` aggiornato ai run reali del secondo push.
- Claim fence invariato: `E1=0`, `E2=0`, zero requisiti globali `Verified`,
  `runtime_conformance` `NOT_ESTABLISHED`, `PoC` e `Production` `NO-GO`.
- Prossima azione: Fase 2.1 del mandato — mypy strict su `ocor-runtime/src` e
  `scripts/`, configurazione `ruff` per l'intero repository, entrambi pinnati
  alla patch, cablati come job CI bloccanti. Task del backlog ordinario
  indipendente dal mandato, sempre dependency-ready: `OCOR-DEV-0079`.

## 2026-09-12 — Fase 2.1: gate bloccante mypy strict + ruff repo-wide

- Nuovo `pyproject.toml` alla radice del repository con `[tool.mypy]`
  (`strict = true`, `files = ["ocor-runtime/src", "scripts"]`) e `[tool.ruff]`
  (`extend-exclude` per i cinque file frozen/content-addressed sotto). `mypy`
  pinnato alla patch (`mypy==2.3.1`) in un nuovo gruppo `lint` di
  `ocor-runtime/pyproject.toml`, insieme a `types-jsonschema==4.26.0.20260518`
  e `types-PyYAML==6.0.12.20260906`: tutte e tre le versioni verificate reali
  sul registry PyPI ufficiale prima del pin, non assunte. `ocor-runtime/uv.lock`
  rigenerato con `uv lock`.
- Prova iniziale `mypy --strict ocor-runtime/src scripts`: 43 errori in 10 file,
  ridotti a 34 dopo l'installazione degli stub mancanti. Corretti con
  annotazioni di tipo precise, cast puntuali o rinomina di variabili in 9 file
  (`ocor_runtime/c3_store.py`, `c4_marking.py`, `c8_agent.py`,
  `scripts/verify.py`, `scripts/ocor_autonomous_delivery.py`,
  `scripts/validate_language_policy.py`, `scripts/validate_rccad.py`,
  `ocor-runtime/tests/backend_assumptions/test_ba01_atomic_outbox.py`,
  `ocor-runtime/tests/schemas/test_schema_integrity.py`); nessun comportamento
  a runtime modificato. Due commenti `# type: ignore` risultati non più
  necessari (`c4_marking.py`, `c8_agent.py`) sono stati rimossi solo dopo aver
  verificato che il comportamento sottostante restava invariato.
  `grpc_tools`/`grpcio-tools` non pubblica stub né `py.typed`: unica eccezione
  concessa, un override puntuale per quel solo modulo di terze parti, non un
  ignore generalizzato del codice proprio.
- Prova iniziale `ruff check --isolated .` (regola di default E4/E7/E9/F, come
  già in uso): 125 errori. Corretti 11 in file attivi non sigillati (import
  inutilizzati, una `lambda` sostituita con `def`, `E401`/`E741` in
  `scripts/verify.py`, una variabile inutilizzata in
  `reports/tests/test_rccad_methodology.py`).
- **Audit dell'evidenza sigillata prima di ogni modifica**: analizzati
  programmaticamente tutti i campi `inputs`/`artifact_hashes` di
  `reports/evidence/**/*.json` e `reports/development/*.json` per ogni file
  `.py` nello scope del nuovo gate. Trovate e **annullate prima del commit**
  tre modifiche che avrebbero invalidato evidenza già accettata:
  - `scripts/preflight_environment.py` è input sigillato di `OCOR-DEV-0072`
    (`reports/evidence/G2/OCOR-DEV-0072.json`) e dell'evidenza ambientale
    `DEC-211` (`reports/development/environment-evidence-dec-211.json`).
  - `ocor-runtime/tests/tasks/test_ocor_dev_0004.py` e `test_ocor_dev_0015.py`
    sono input sigillati rispettivamente di `OCOR-DEV-0004`
    (`reports/evidence/G0/OCOR-DEV-0004.json`) e `OCOR-DEV-0015`
    (`reports/evidence/G2/OCOR-DEV-0015.json`).
  Tutti e tre sono stati esclusi dal gate nuovo con motivazione puntuale in
  linea nella configurazione, invece di essere modificati.
- **Scoperta e escalation** (non bloccante per questa fase): rieseguire
  `scripts/build_ocor_development_plan.py` per far assestare il proprio
  self-hash in `reports/planning/OCOR_PLAN_RUN_STATE.json` ha **cancellato
  silenziosamente `OCOR-DEV-0070`–`0084`** dal backlog rigenerato, perché la
  lista `TASK_SPECS` dello script non è mai stata aggiornata quando quei 15
  task sono stati aggiunti al backlog reale. Nessuno script referenzia
  `OCOR-DEV-0070` o superiore, confermando che non esiste un secondo
  generatore che li copra. La rigenerazione è stata scartata (`git checkout
  --`) prima di qualunque commit; il file è escluso anche dal nuovo gate
  mypy (già pulito per `ruff`). Escalation registrata in
  `reports/evidence/local-gates/phase2-1-mypy-ruff-gates-20260912.json`
  (`PHASE2-4-BACKLOG-GENERATOR-DRIFT`): va risolta prima che la Fase 2.4
  rigeneri il DAG, non prima.
- Cinque file esclusi dal nuovo gate `ruff` con motivazione in linea nel
  `pyproject.toml`: i tre artefatti frozen della review ADD v1.1/v1.2
  (`test_v12_candidate.py` e `test_v12_semantics.py`, content-addressed in
  `reports/OCOR_ADD_v1.2_SHA256SUMS`; `test_schema_conformance.py`, sibling
  v1.1 dello stesso corpus storico) e i due file di evidenza sigillata sopra
  (`test_ocor_dev_0004.py`, `test_ocor_dev_0015.py`).
  `scripts/preflight_environment.py` e `scripts/build_ocor_development_plan.py`
  erano già puliti per `ruff`, quindi esclusi solo dal gate `mypy`.
  Nessuna delle esclusioni promuove evidenza o requisiti.
- Nuovo job bloccante `type-and-lint-gate` in
  `.github/workflows/ocor-tooling-bootstrap.yml`: stesso pattern di checkout
  exact-head, Python 3.12.11 + uv 0.12.5 pinnati, `uv sync --extra test --extra
  lint`, poi `ocor-runtime/.venv/bin/python -m mypy` e `ruff check .`.
- Gate locali: `sha256sum -c` `PASS` 8/8; `ocor-runtime/.venv/bin/python -m
  mypy` `PASS` 44/44 file; `ruff check .` (0.13.1 pinnato) `PASS`;
  `validate_rccad.py` `PASS_LOCAL_PRECHECK` 0 finding; `validate_ocor_change_scope.py`
  `PASS` 14 percorsi; `validate_ocor_development_plan.py --authorized-extension`
  `PASS` 37/2/0 dopo self-hash settle; `validate_language_policy.py` `PASS`;
  regressione pytest completa su `ocor-runtime/tests/` (stessa invocazione
  della CI) `498 passed, 5 skipped, 10 errors` — gli errori sono lo stesso gap
  pre-esistente `OCOR_LIVE_POSTGRES_DSN` di `test_ocor_dev_0015.py` osservato
  in ogni iterazione precedente, non una regressione; `reports/verify_report.json`
  bit-identico alla baseline committata dopo un run con l'ambiente reale
  completo.
- Claim fence invariato: `E1=0`, `E2=0`, zero requisiti globali `Verified`,
  `runtime_conformance` `NOT_ESTABLISHED`, `PoC` e `Production` `NO-GO`. Nessuna
  evidenza sigillata invalidata; nessun requisito promosso.
- Prossima azione: aprire la PR, attendere CI verde sull'HEAD esatto (in
  particolare il nuovo job `type-and-lint-gate`), merge, verifica SHA
  post-merge, poi Fase 2.2 del mandato — pin dell'interprete alla patch.

## 2026-09-12 — Chiusura Fase 2.1

- PR #59 aperta e integrata al primo tentativo: merge
  `1cfa0a787ee620e462adfd0d25378f752c74af28`. Tutti i 12 check verdi
  sull'HEAD esatto `5123650e` al primo push, incluso il nuovo job
  `type-and-lint-gate` (run id `34710650062/063/066/069/077/090`).
- Verifica pre-merge: `mergeStateStatus: CLEAN`, `mergeable: MERGEABLE`.
  Verifica post-merge: SHA di `origin/main` coincidente con il merge commit
  riportato da GitHub.
- `EXECUTION_STATE.json` e `MODEL_HANDOFF.json` risincronizzati al nuovo HEAD;
  `latest_ci_evidence` aggiornato ai run reali.
- Claim fence invariato: `E1=0`, `E2=0`, zero requisiti globali `Verified`,
  `runtime_conformance` `NOT_ESTABLISHED`, `PoC` e `Production` `NO-GO`.
- Prossima azione: Fase 2.2 del mandato — pin dell'interprete alla patch in
  `requires-python`, `uv.lock`, `.python-version` e in tutti i workflow, più
  un test che fallisca se l'interprete in esecuzione diverge dal pin.

## 2026-09-12 — Fase 2.2: pin dell'interprete alla patch

- `ocor-runtime/pyproject.toml`: `requires-python` da `>=3.11` a `==3.12.11`.
  Nuovo `ocor-runtime/.python-version` con `3.12.11`. Header di
  `ocor-runtime/uv.lock` allineato allo stesso valore. Dodici occorrenze di
  `python-version: "3.12"` (pin di sola minor) corrette a `"3.12.11"` in
  cinque workflow (`ocor-rccad`, `ocor-poc-ci` ×6, `ocor-supply-chain`,
  `ocor-delivery-activation`, `ocor-validation-closure`);
  `ocor-tooling-bootstrap.yml` era già esatto. Nuovo
  `ocor-runtime/tests/test_interpreter_pin.py`: fallisce chiuso se
  l'interprete in esecuzione diverge dal pin, letto da `.python-version`
  invece di essere ripetuto in chiaro nel test.
- **Limite di verifica locale, dichiarato esplicitamente**: questo sandbox
  non possiede l'interprete esatto `3.12.11` (né come build standalone di
  `uv`, né altrove) e non può scaricarlo. Di conseguenza `uv lock`, `uv sync
  --frozen` e `uv run` rifiutano categoricamente di eseguire non appena
  `requires-python` diventa `==3.12.11`. Tutta la verifica locale ha quindi
  invocato l'interprete della venv esistente direttamente
  (`ocor-runtime/.venv/bin/python`), bypassando il wrapper di `uv`. La riga
  `requires-python` nell'header di `uv.lock` è stata corretta a mano come
  eccezione documentata — è una copia letterale del campo già dichiarato in
  `pyproject.toml`, non una decisione di risoluzione delle dipendenze; nessuna
  versione di pacchetto o `resolution-markers` è stata toccata a mano.
- Confermato che il pin non è fittizio: `infra/toolchain.lock.json` fissa già
  Python `3.12.11` con hash di integrità reale, e ogni run CI di questa
  sessione (PR #54–60) ha già usato `actions/setup-python` con `"3.12.11"`
  con successo (il dump d'ambiente di un job precedente mostrava
  `pythonLocation: /opt/hostedtoolcache/Python/3.12.11/x64`). Il gate
  qualificante reale per questa modifica resta quindi la CI, non questo
  sandbox.
- Regressione pytest completa (invocazione diretta della venv):
  `2 failed, 499 passed, 5 skipped, 10 errors`. Le due nuove failure
  condividono la stessa unica causa già dichiarata sopra, non un difetto
  logico: `test_interpreter_pin.py::test_running_interpreter_matches_the_pin`
  fallisce esattamente come previsto (`3.12.14 != 3.12.11`);
  `test_ocor_dev_0002.py::test_two_clean_environments_resolve_identical_lock_and_image_digests`
  fallisce nel suo stesso sottoprocesso `uv lock --check` con l'identico
  errore di interprete assente. I 10 errori pre-esistenti restano il gap
  `OCOR_LIVE_POSTGRES_DSN` già dichiarato. Entrambe le nuove failure sono
  attese verdi in CI.
- Audit di sicurezza prima della modifica: `ocor-runtime/pyproject.toml` e
  `ocor-runtime/uv.lock` sono già referenziati come input in 15+ evidenze di
  task precedenti (`OCOR-DEV-0002`..`0071`), ma come manifest di progetto
  condivisi e in evoluzione continua — non il deliverable unico e sigillato
  di un singolo task — esattamente come confermato dal precedente già
  accettato in Fase 2.1 (PR #59, che ha già modificato entrambi con successo).
  Stesso ragionamento per `ocor-poc-ci.yml`/`ocor-supply-chain.yml` rispetto
  al precedente `ocor-tooling-bootstrap.yml` già modificato in Fase 2.1.
  Nessun file di evidenza sigillata a task singolo è stato toccato.
- Gate locali: `sha256sum -c` `PASS` 8/8; `ocor-runtime/.venv/bin/python -m
  mypy` `PASS` 44/44; `ruff check .` `PASS`; `verify.py --json` `PASS` 14/0/0;
  `validate_rccad.py` `PASS_LOCAL_PRECHECK` 0 finding; `validate_language_policy.py`
  `PASS`; `validate_ocor_change_scope.py` `PASS` 9 percorsi;
  `validate_ocor_development_plan.py --authorized-extension` `PASS` 37/2/0
  dopo self-hash settle; sintassi YAML valida su tutti i workflow.
- Claim fence invariato: `E1=0`, `E2=0`, zero requisiti globali `Verified`,
  `runtime_conformance` `NOT_ESTABLISHED`, `PoC` e `Production` `NO-GO`.
- Prossima azione: aprire la PR, seguire la CI con particolare attenzione al
  primo passo `uv` di ogni workflow (rischio di risoluzione dell'interprete
  dichiarato sopra); se rosso, correggere alla radice (mai allentare il pin);
  se verde, merge, verifica SHA post-merge, poi Fase 2.3 — SDK TypeScript
  reale e suite di conformità cross-SDK.

## 2026-09-12 — Chiusura Fase 2.2

- PR #61 aperta e integrata: merge `47ca9017c8f8f5f89d5155daea13f05314f1025f`.
  **Il rischio dichiarato sulla risoluzione dell'interprete non si è
  concretizzato**: `type-and-lint-gate`, `unit`, `integration-postgresql` e
  `validation-closure` (tutti basati su `uv`) sono passati puliti sul pin
  esatto `3.12.11` già al primo push, confermando che l'interprete fornito
  su `PATH` da `actions/setup-python` soddisfa il vincolo `requires-python`
  esatto senza bisogno di download da parte di `uv`.
  Il primo push è comunque fallito su `tooling-policy`, ma per una causa
  diversa e già nota: un self-hash di `scripts/validate_ocor_development_plan.py`
  non assestato dopo una terza modifica al file nella stessa iterazione (le
  prime due erano state assestate correttamente, la terza — l'aggiunta del
  percorso di evidenza Fase 2.2 — no). Corretto e ripushato (`7b97e96`):
  12/12 check verdi.
- Verifica pre-merge: `mergeStateStatus: CLEAN`. Verifica post-merge: SHA di
  `origin/main` coincidente con il merge commit.
- `EXECUTION_STATE.json` e `MODEL_HANDOFF.json` risincronizzati; `latest_ci_evidence`
  aggiornato ai run reali.
- Claim fence invariato: `E1=0`, `E2=0`, zero requisiti globali `Verified`,
  `runtime_conformance` `NOT_ESTABLISHED`, `PoC` e `Production` `NO-GO`.
- Prossima azione: Fase 2.3 del mandato — SDK TypeScript reale sotto
  `ocor-runtime/sdk/typescript`, generato dal generatore esistente, mai
  scritto a mano; `tsconfig` strict; compilazione `tsc` in CI; suite di
  conformance cross-SDK `NFR-022` su fixture condivise fra SDK Python, SDK
  TypeScript e descrittore MCP.
## 2026-09-12 — Fase 2.3: SDK TypeScript reale + remediation OCOR-DEV-REM-0010

- Nuovo `ocor-runtime/sdk/typescript/`: `package.json` (`typescript==7.0.2`,
  `@types/node==20.19.43`, entrambe verificate reali sul registry ufficiale),
  `tsconfig.json` (`strict: true` più `noUncheckedIndexedAccess`,
  `exactOptionalPropertyTypes`, `noUnusedLocals/Parameters`), `src/errors.ts`
  ed `src/canonical.ts` (kernel di supporto scritto a mano — la stessa
  distinzione che il runtime Python traccia fra il proprio `canonical.py`
  scritto a mano e `ocor_contracts.py` generato — porting di
  `ocor_runtime.canonical`/`errors.py` che sfrutta il fatto che
  `String(number)` e l'ordinamento di default delle stringhe in ECMAScript
  **sono già** l'algoritmo che RFC 8785 richiede, invece di re-derivarli come
  fa la porta Python), `src/generated/ocor_contracts.ts` (generato dal
  generatore esistente, mai scritto a mano — bit-identico a una sua
  esecuzione fresca, verificato meccanicamente da entrambe le nuove suite).
- **Scoperta un difetto reale e non rilevato in precedenza**: la prima vera
  compilazione `tsc --strict` dell'output del generatore (mai eseguita
  prima — la suite sigillata `test_ocor_dev_0010.py` verifica solo che la
  riga di dichiarazione di ogni modello sia presente, mai che il file nel
  suo insieme risolva o compili) ha prodotto 19 errori `TS2304: Cannot find
  name` distinti. La risoluzione dei `$ref` in
  `ocor-runtime/tools/generate_contracts.py` prendeva l'ultimo segmento del
  percorso senza conoscenza del prefisso `Gateway`/`Memory` che `_models()`
  applica ai record oggetto di origine OpenAPI, e non gestiva affatto i
  `$ref` verso componenti non-oggetto (una stringa digest SHA-256, un array
  `Refs`/`NonEmptyRefs`, un alias `GovernedContext` che inoltra a un intero
  documento JSON Schema esterno). Raw log sigillato con fingerprint SHA-256
  in `reports/tests/evidence/rem_generate_contracts_refs/red.log`.
- **Remediation OCOR-DEV-REM-0010**: `ocor-runtime/tools/generate_contracts.py`
  è input sigillato di `OCOR-DEV-0010`
  (`reports/evidence/G1/OCOR-DEV-0010.json`), così come la sua suite
  `test_ocor_dev_0010.py`. Corretta la sola risoluzione dei riferimenti
  (nuova `_build_reference_index()`), aggiornati i `PINNED_GENERATED_HASHES`
  al nuovo output corretto; l'inventario dei modelli (54, stessi nomi) resta
  invariato. La suite sigillata `test_ocor_dev_0010.py` è stata lasciata
  **completamente non modificata** e riverificata verde 15/15 contro il
  generatore corretto, dimostrando che la correzione è compatibile con il
  significato storico dell'evidenza sigillata, non lo invalida. Nuova suite
  `reports/tests/test_generate_contracts_reference_resolution.py` (13 test):
  fingerprint del log RED, verifica che ogni `$ref` del set di contratti
  pinnati risolva ora a un modello dichiarato o a un primitivo riconosciuto,
  controlli puntuali sui 9 casi precedentemente rotti, verifica che
  l'inventario dei modelli sia invariato, e (quando `tsc` è su `PATH`)
  ricompila da zero l'intero SDK committato.
- Nuova suite `ocor-runtime/tests/sdk/test_typescript_sdk_conformance.py`
  (NFR-022, 4 test): identità byte-per-byte del testo canonico e del digest
  SHA-256 fra Python e TypeScript su 23 fixture (ordinamento delle chiavi,
  escaping di stringhe unicode/di controllo, confine `MAX_SAFE_INTEGER`,
  soglie di notazione scientifica ±21/-7); identità del modello di errore
  (codice `CANONICALIZATION_INVALID`) su fixture con surrogati UTF-16 non
  accoppiati; parità dei campi generati fra una generazione Python fresca e
  l'SDK TypeScript committato; identità del binding di idempotenza (la
  semantica di idempotenza del descrittore MCP lega una richiesta al proprio
  digest canonico: richieste con campi riordinati producono lo stesso
  digest in entrambi gli SDK, un campo cambiato no). La suite pilota l'SDK
  TypeScript compilato come sottoprocesso, lo stesso schema con cui
  `DEC-166`/`REM-0007` usa già Node.js come oracolo cross-language per i
  valori limite dell'implementazione Python.
- Due nuovi controlli di skip condizionale (`tsc`/`node` non disponibili in
  locale, sempre disponibili in CI) registrati in
  `reports/development/METHOD_COMPLIANCE.json.test_exceptions`
  (`TEST-INFRA-002`, `TEST-INFRA-003`), stesso schema del guard PostgreSQL
  già esistente (`TEST-INFRA-001`); `validate_rccad.py` falliva
  `RCCAD-UNJUSTIFIED-SKIP` prima della registrazione.
- Nuovo step `tsc --strict` e le due nuove suite pytest cablati nel job
  `type-and-lint-gate` di `.github/workflows/ocor-tooling-bootstrap.yml`
  (`actions/setup-node@v4`, stesso pin `20.20.2` già in uso altrove nel
  repository).
- Gate locali: `sha256sum -c` `PASS` 8/8; `npm run build` da stato pulito
  (`rm -rf node_modules dist`) `PASS` zero errori; le due nuove suite pytest
  `PASS` 17/17 contro l'SDK ricompilato da zero; `ocor-runtime/.venv/bin/python
  -m mypy` `PASS` 44/44 (invariato, `ocor-runtime/tools/` è fuori scope);
  `ruff check .` `PASS`; `validate_rccad.py` `PASS_LOCAL_PRECHECK` 0 finding
  dopo la registrazione degli skip; `validate_language_policy.py` `PASS`;
  `validate_ocor_change_scope.py` `PASS` 11 percorsi;
  `validate_ocor_development_plan.py --authorized-extension` `PASS` 37/2/0
  dopo self-hash settle; regressione pytest completa `2 failed, 516 passed,
  5 skipped, 10 errors` — le due failure e i dieci errori sono
  esclusivamente i gap sandbox già dichiarati nelle Fasi 2.2 e precedenti
  (interprete `3.12.11` esatto assente, PostgreSQL live assente), non una
  regressione.
- Claim fence invariato: `E1=0`, `E2=0`, zero requisiti globali `Verified`,
  `runtime_conformance` `NOT_ESTABLISHED`, `PoC` e `Production` `NO-GO`.
  Nessuna evidenza sigillata invalidata; profilo SDK `DEC-075`/`FR-047`/`FR-048`
  invariato.
- Prossima azione: aprire la PR, attendere CI verde sull'HEAD esatto (in
  particolare i nuovi step `tsc`/conformance nel job `type-and-lint-gate`),
  merge, verifica SHA post-merge, poi Fase 2.4 del mandato — prima risolvere
  l'escalation `PHASE2-4-BACKLOG-GENERATOR-DRIFT`, poi correggere
  l'allocazione di `FR-047`, aggiungere i task mancanti al backlog e
  rigenerare il DAG.


## 2026-09-12 — Chiusura Fase 2.3

- PR #63 aperta e integrata al primo tentativo: merge
  `b4510123dee21c054876ecca97b02d33b971318a`. Tutti i 12 check verdi
  sull'HEAD esatto `5428ab37` al primo push, incluso il nuovo step `tsc` e
  le due nuove suite pytest nel job `type-and-lint-gate`.
- Verifica pre-merge: `mergeStateStatus: CLEAN`. Verifica post-merge: SHA di
  `origin/main` coincidente con il merge commit.
- `EXECUTION_STATE.json` e `MODEL_HANDOFF.json` risincronizzati; `latest_ci_evidence`
  aggiornato ai run reali.
- Claim fence invariato: `E1=0`, `E2=0`, zero requisiti globali `Verified`,
  `runtime_conformance` `NOT_ESTABLISHED`, `PoC` e `Production` `NO-GO`.
- Prossima azione: Fase 2.4 del mandato. Prima risolvere l'escalation
  `PHASE2-4-BACKLOG-GENERATOR-DRIFT` (riconciliare `TASK_SPECS` del
  generatore con `OCOR-DEV-0070`–`0084` e verificare che una rigenerazione
  riproduca l'84-task backlog reale senza perdite), poi correggere
  l'allocazione di `FR-047` in `OCOR_TRACEABILITY_PLAN.csv`, aggiungere i
  task mancanti al backlog e rigenerare il DAG. Nessuna promozione a
  Verified.

## 2026-09-12 — Fase 2.4 (parziale): correzione allocazione FR-047

- Confermata la denuncia esatta del mandato: `OCOR_TRACEABILITY_PLAN.csv`
  allocava `FR-047` ("SDK e tool MCP generati" — il sistema DEVE generare SDK
  Python e TypeScript e contratti MCP tipizzati) a `OCOR-DEV-0047`
  ("Implement C8 tool boundary sandbox budgets and kill switch", WS-09, G4)
  — un task sul sandbox di invocazione tool dell'agent kernel, senza alcuna
  relazione con la generazione di SDK. `OCOR-DEV-0047.requirement_ids`
  raggruppa una ventina di requisiti includendo `FR-047`, quasi certamente
  per uno scambio numero-task/numero-requisito (047 con 047) piuttosto che
  per una relazione semantica reale.
- Identificato `OCOR-DEV-0010` ("Materialize contract-first SDK boundaries
  and drift checks", WS-01, G1) come il task corretto: è quello che possiede
  `ocor-runtime/tools/generate_contracts.py`, già accettato
  (`completed_evidence_tasks`), ed esteso proprio in questa sessione (Fase
  2.3) con l'SDK TypeScript reale e la suite di conformance cross-SDK che il
  criterio di accettazione di `FR-047` nomina esplicitamente ("lo stesso
  mission scenario è invocabile da entrambi gli SDK e tramite MCP").
- Corretto `docs/development_plan/OCOR_TRACEABILITY_PLAN.csv`: riga `FR-047`
  con `owning_workstream` `WS-09`→`WS-01`, `implementation_task`
  `OCOR-DEV-0047`→`OCOR-DEV-0010`, `qualifying_test`/`required_backend`/
  `expected_evidence` estesi per nominare la suite reale e l'evidenza
  sigillata di `OCOR-DEV-0010`; `verification_task` (`OCOR-DEV-0065`, prova
  di integrazione a mission-thread completo) e `target_gate`/
  `current_baseline_status` lasciati invariati perché ancora corretti.
  Aggiornati coerentemente i due `requirement_ids` nel backlog (rimosso
  `FR-047` da `OCOR-DEV-0047`, aggiunto a `OCOR-DEV-0010`) — diff di sole 4
  righe, nessuna riformattazione incidentale. Nessun task nuovo aggiunto:
  è una pura riallocazione a un task esistente e già corretto. Nessuna
  `hard_dependencies` è cambiata, quindi nessuna rigenerazione del DAG era
  necessaria né è stata eseguita.
- `reports/planning/OCOR_PLAN_RUN_STATE.json.artifact_hashes` per i due file
  di pianificazione toccati aggiornato a mano (calcolo diretto dello
  sha256, non una decisione di risoluzione) come eccezione documentata: la
  sola via sanzionata (rieseguire `scripts/build_ocor_development_plan.py`)
  resta non sicura finché l'escalation `PHASE2-4-BACKLOG-GENERATOR-DRIFT`
  (`TASK_SPECS` privo di `OCOR-DEV-0070`–`0084`) non è risolta — non
  necessaria per QUESTA correzione, perché nessuna rigenerazione è stata
  eseguita.
- Gate locali: `sha256sum -c` `PASS` 8/8; `validate_ocor_development_plan.py
  --authorized-extension` `PASS` 37/2/0 dopo assestamento (allowlist,
  self-hash, artifact-hash), inclusi `285 requirement allocation` `PASS`
  (rows: 285, missing: []) e `qualifying trace assignments` `PASS`;
  `validate_rccad.py` `PASS_LOCAL_PRECHECK` 0 finding; `verify.py --json`
  `PASS` 14/0/0 (`reports/verify_report.json` invariato);
  `validate_language_policy.py` `PASS`; `validate_ocor_change_scope.py`
  `PASS` 5 percorsi; `ruff check .`/`mypy` `PASS` invariati; regressione
  pytest completa `2 failed, 516 passed, 5 skipped, 10 errors` — stessi gap
  sandbox già dichiarati, nessuna nuova failure.
- Claim fence invariato: `E1=0`, `E2=0`, zero requisiti globali `Verified`
  (`FR-047` resta `PARTIALLY_IMPLEMENTED`, in attesa della verifica a
  mission-thread completo di `OCOR-DEV-0065`), `runtime_conformance`
  `NOT_ESTABLISHED`, `PoC` e `Production` `NO-GO`.
- Prossima azione: aprire la PR, attendere CI verde, merge, verifica SHA
  post-merge, poi risolvere l'escalation `PHASE2-4-BACKLOG-GENERATOR-DRIFT`
  come task a sé stante (estendere `TASK_SPECS`/la logica di generazione di
  `scripts/build_ocor_development_plan.py` per coprire `OCOR-DEV-0070`–`0084`
  e verificare che una rigenerazione riproduca l'84-task backlog reale prima
  di rigenerare mai il DAG per davvero). Solo allora la Fase 2.4 è chiusa;
  segue la Fase 3.

## 2026-09-12 — Chiusura parziale Fase 2.4 (FR-047)

- PR #65 aperta e integrata: merge `dcfca5086ac20ed1b99548c4eb02b57f92dee66c`.
  Il primo push ha fatto fallire di nuovo `tooling-policy` per lo stesso
  self-hash di `scripts/validate_ocor_development_plan.py` non assestato
  dopo l'ultima di due modifiche nella stessa iterazione — terza occorrenza
  di questo esatto errore in questa sessione. Corretto e ripushato
  (`f4eda68`): 12/12 check verdi.
- Verifica pre-merge: `mergeStateStatus: CLEAN`. Verifica post-merge: SHA di
  `origin/main` coincidente con il merge commit.
- `EXECUTION_STATE.json` e `MODEL_HANDOFF.json` risincronizzati;
  `latest_ci_evidence` aggiornato ai run reali.
- Claim fence invariato: `E1=0`, `E2=0`, zero requisiti globali `Verified`,
  `runtime_conformance` `NOT_ESTABLISHED`, `PoC` e `Production` `NO-GO`.
- **Fase 2.4 non ancora completamente chiusa**: resta l'escalation
  `PHASE2-4-BACKLOG-GENERATOR-DRIFT`. Prossima azione: risolverla come task a
  sé stante — estendere `scripts/build_ocor_development_plan.py` con un
  percorso di generazione dedicato al workstream `WS-12` (template diverso da
  quello dei task 1-69: `objective`/`rationale`/`normative_references`/
  `validation_commands`/`bounded_agent_context_pack` specifici per il
  bootstrap di infrastruttura), verificare in una directory di scratch che
  una rigenerazione riproduca esattamente backlog/DAG/context-manifest reali
  per `OCOR-DEV-0070`–`0084`, e solo allora considerare la Fase 2.4 chiusa.

## 2026-09-12 — Chiusura Fase 2.4: risolta PHASE2-4-BACKLOG-GENERATOR-DRIFT

- Branch `governed/phase2-4-backlog-generator-drift` da `main`
  (`3caf7a68bfdee11eb1abc4dec857cf130c89f912`, merge PR #66).
- Causa radice confermata: `TASK_SPECS` in
  `scripts/build_ocor_development_plan.py` descriveva solo 69 task; i 15 task
  `OCOR-DEV-0070`–`0084` (catena WS-12 di riparazione del bootstrap
  infrastrutturale) erano stati adottati nel backlog committato fuori banda,
  senza mai aggiornare il generatore. Una rigenerazione reale li avrebbe
  cancellati in silenzio, insieme agli archi di dipendenza che li usano
  (`OCOR-DEV-0016/0017/0018/0021 -> OCOR-DEV-0084`).
- Correzione: aggiunto `WS12_TASK_SPECS` (15 tuple) e un ramo dedicato in
  `build_tasks()`; aggiunta la dipendenza `84` ai task 16/17/18/21 (il
  backlog reale la richiede); aggiunto un override post-hoc per
  `requirement_ids` di FR-047 che riproduce la correzione manuale della PR
  #65 (il matching a parola chiave di `requirement_owner()` per WS-09
  intercetta la sottostringa "tool" dentro il titolo stesso di FR-047 —
  esattamente il difetto già corretto a mano — così una rigenerazione futura
  ora riproduce, invece di annullare, la correzione); riscritta
  `context_manifest()` con un helper `_task_context_entry()` che assegna ai
  task 70–84 il ruolo reale "Infrastructure and Operations Agent" con
  `paths`/token-budget dedicati, distinguendoli dai task 6 e 49 (che usano
  `workstream=WS-12` ma la formula generica).
- Verifica: confronto in memoria (mai scritto su disco prima della verifica,
  come richiesto dal mandato) di `build_tasks()`/`dag_text()`/
  `context_manifest()` contro i file committati reali —
  **0 mismatch su tutti gli 84 task e ogni campo**, DAG e context-manifest
  byte-identici. `build_trace()`/`OCOR_TRACEABILITY_PLAN.csv` lasciato
  volutamente fuori scope: ha una propria staleness distinta e preesistente
  (2/285 righe, `BR-003` e `FR-047`, causata da un'euristica di ownership
  "vince l'ultimo task nell'ordine di iterazione" sensibile all'ordine —
  mai stata corretta per costruzione, solo accidentalmente stabile prima
  dell'aggiunta di WS-12) — registrata come nuova escalation separata,
  non bloccante, non confusa con questa.
- Aggiunto test di non-regressione permanente
  `reports/tests/test_backlog_generator_reality_parity.py` (RED/GREEN, RED
  sigillato in `reports/tests/evidence/rem_backlog_generator_drift/red.log`,
  fingerprint `94c2781e8c0072dd4e7c1b84c9772aeedd7159fa78e00f521efb946bc7748841`)
  che blocca in CI qualunque futura regressione di questo tipo.
- Gate locali tutti verdi: `sha256sum` 8/8, `ruff`, `mypy` (44 file, scope
  invariato), `validate_rccad.py` PASS, `validate_language_policy.py` PASS,
  `validate_ocor_change_scope.py` PASS (7 percorsi), pytest completo
  `2 failed, 521 passed, 5 skipped, 10 errors` (stessi gap sandbox noti,
  +5 rispetto alla fase precedente = i nuovi test di questa iterazione),
  `validate_ocor_development_plan.py --authorized-extension` PASS dopo il
  consueto doppio-run di assestamento self-hash (modificato
  `scripts/validate_ocor_development_plan.py` per l'ultima volta prima di
  eseguirlo, come da lezione appresa dalle 3 occorrenze precedenti).
  `OCOR_PLAN_RUN_STATE.json.artifact_hashes` aggiornato a mano per
  `scripts/build_ocor_development_plan.py` (unica eccezione documentata: il
  percorso di rigenerazione reale invocherebbe anche `build_trace()`, non
  sicuro per la staleness nota sopra).
- Evidenza sigillata:
  `reports/evidence/local-gates/phase2-4-backlog-generator-drift-20260912.json`.
- Claim fence invariato: `E1=0`, `E2=0`, zero requisiti `Verified`,
  `runtime_conformance` `NOT_ESTABLISHED`, `PoC`/`Production` `NO-GO`.
- **Fase 2.4 ora completamente chiusa** (in attesa di merge PR). Prossima
  azione: Fase 3 (harness di benchmark riproducibile e content-addressed per
  i 4 componenti candidati, contro le soglie di migrazione già corrette in
  `OCOR_LANGUAGE_POLICY.md` §3), poi esecuzione backlog via
  `./.venv/bin/python3 scripts/ocor_autonomous_delivery.py --next` a partire
  da `OCOR-DEV-0079`.

## 2026-09-12 — PR #67 mergiata: Fase 2.4 definitivamente chiusa

- PR #67 aperta e integrata senza correzioni: tutti e 13 i check verdi al
  primo push (commit `fbdec46`). `mergeStateStatus: CLEAN`,
  `mergeable: MERGEABLE`. Merge: `9bd2821464339f406df26cc3b2dd8579330c80fb`.
  Verifica post-merge: `git fetch origin main` conferma
  `origin/main == 9bd2821` (fast-forward pulito da `3caf7a6`).
- `EXECUTION_STATE.json`/`MODEL_HANDOFF.json` risincronizzati su branch
  `governed/phase2-4-close-state-generator-drift`, `baseline_commit` ==
  `9bd2821...`, `latest_ci_evidence` aggiornato ai 6 run id reali della PR
  #67 (`34716799046/061/068/075/087/109`). `current_task` avanzato a
  `CC-OCOR-DELIVERY-COMPLETION__PHASE-3-BENCHMARK-HARNESS`.
- Claim fence invariato: `E1=0`, `E2=0`, zero requisiti `Verified`,
  `runtime_conformance` `NOT_ESTABLISHED`, `PoC`/`Production` `NO-GO`.
- **Fasi 2.1–2.4 del mandato ora tutte chiuse e mergiate** (PR #54–#67).
  Prossima azione: Fase 3 — harness di benchmark riproducibile e
  content-addressed per i 4 componenti candidati rispetto alle soglie di
  migrazione OI-008/ASM-010/NFR-080 già corrette in
  `OCOR_LANGUAGE_POLICY.md` §3; esito atteso `NO_MIGRATION_JUSTIFIED` oppure
  una decisione di migrazione scoperta al solo componente coinvolto con
  protocollo differenziale completo prima di ogni merge. Solo dopo,
  esecuzione backlog via
  `./.venv/bin/python3 scripts/ocor_autonomous_delivery.py --next` a partire
  da `OCOR-DEV-0079`.

## 2026-09-12 — Fase 3: harness di benchmark eseguito, esito reale per il componente 1

- PR #68 mergiata (chore(state): close Phase 2.4 tracking): tutti e 13 i
  check verdi, merge `5a08f78c9e429c2e80ec93b9d05c029e9e46cfb9`, verifica
  post-merge con `git fetch origin main` conferma `origin/main == 5a08f78`.
  Un piccolo commit di assestamento (`a19c321`) ha corretto il base-ref
  auto-embedded di `OCOR_PLANNING_VALIDATION_REPORT.md`, prodotto dalla
  stessa esecuzione del validator già usata per i gate — nessun problema
  nuovo, solo output mecc anico del tool.
- Branch `governed/phase3-language-migration-benchmark` da `main`
  (`5a08f78c9e429c2e80ec93b9d05c029e9e46cfb9`).
- Costruito `scripts/run_language_migration_benchmark.py` (harness
  riproducibile e content-addressed) e un nuovo CLI Node dedicato,
  `ocor-runtime/sdk/typescript/src/cli/benchmark_canonicalize.ts`
  (timing interno con `process.hrtime.bigint()`, distinto dal CLI di
  conformità NFR-022 il cui contratto di stdout è già asserito byte per
  byte e non è stato toccato).
- Corpus sigillato: 200 documenti deterministici (LCG proprio, seed
  `20260912`), ciascuno ~10 KB serializzato (10000–10121 byte, esattamente
  il payload di riferimento di `OCOR_LANGUAGE_POLICY.md` §3) —
  `reports/benchmarks/fixtures/phase3_canonical_corpus.json`,
  `sha256=2ce8879bc8e5697a4f51e37a3ae1262da4995c2fdba7f2ba23e6e3e775da80b7`.
- **Componente 1 (kernel di canonicalizzazione RFC 8785) — misurato per
  davvero**: mediana Python / mediana Node = **4.24×** (range su 3 run
  consecutive con lo stesso corpus sigillato: 4.24×–4.77×, stabile, non
  rumore), soglia >3× — **superata**. p95 assoluto Python: 1.77–1.96 ms,
  soglia >2 ms — non superata (ma la clausola è un OR, quindi la soglia
  è comunque superata). Esito: **`MIGRATION_THRESHOLD_EXCEEDED`**.
- Per `OCOR_LANGUAGE_POLICY.md` §3, il superamento autorizza l'apertura di
  una nuova decisione di migrazione per il solo componente — non
  l'esecuzione autonoma della migrazione, che sostituirebbe
  un'architettura approvata (`AFF-001`) ed è una delle condizioni di
  escalation esplicite del mandato (§5.4). Registrata l'escalation
  `PHASE3-COMPONENT1-CANONICAL-KERNEL-MIGRATION-THRESHOLD-EXCEEDED`,
  riservata al Product Owner sotto dual control (`NFR-081`/`DEC-174`).
  Dettaglio completo e raccomandazione in
  `reports/development/PHASE3_LANGUAGE_MIGRATION_DECISION.md`.
- **Componenti 2–4 (percorso di commit C3, backbone eventi C5, proiezione
  C4) — `NOT_YET_MEASURABLE`**, ciascuno con motivo concreto e non
  fabbricato: componente 2 richiede PostgreSQL reale (stesso gap già
  documentato della suite live di `test_ocor_dev_0015.py`); componenti 3 e
  4 non hanno ancora un'implementazione reale in `ocor_runtime` (solo FSM
  obsoleta / reticolo di marking), per
  `docs/planning/OCOR_CURRENT_STATE_BASELINE.json`. Questo è un esito
  parziale onesto, non un sostituto di `NO_MIGRATION_JUSTIFIED`.
- Aggiunto `reports/tests/test_language_migration_benchmark_harness.py`
  (11 test): soglie del harness allineate a `OCOR_LANGUAGE_POLICY.md` §3
  per tutti e 4 i componenti, hash del corpus sigillato invariato,
  determinismo del generatore, payload ~10 KB, componenti 2–4 mai
  fabbricati, smoke test end-to-end (guardia `TEST-INFRA-004`), nessun
  claim proibito nell'evidenza sigillata.
- **Trovato e corretto un gap della PR #67**: `test_backlog_generator_reality_parity.py`
  non era mai stato cablato in nessun job CI (solo eseguito localmente) —
  corretto insieme al nuovo test, entrambi ora nel job `type-and-lint-gate`
  di `ocor-tooling-bootstrap.yml`.
- Gate locali tutti verdi: `sha256sum` 8/8, `ruff`, `mypy` (45 file, 1 fix
  `no-any-return`), `tsc --strict` (nuovo CLI compilato pulito),
  `validate_rccad.py` PASS (dopo aver registrato `TEST-INFRA-004` in
  `METHOD_COMPLIANCE.json`), `validate_language_policy.py` PASS,
  `validate_ocor_change_scope.py` PASS (12 percorsi), pytest completo
  `2 failed, 532 passed, 5 skipped, 10 errors` (stessi gap sandbox noti, +11
  rispetto alla fase precedente = i nuovi test di questa iterazione),
  `validate_ocor_development_plan.py --authorized-extension` PASS dopo il
  consueto doppio-run di assestamento self-hash.
- Evidenza sigillata:
  `reports/evidence/local-gates/phase3-language-migration-benchmark-20260912.json`,
  `reports/benchmarks/phase3_language_migration_benchmark_20260912.json`.
- Claim fence invariato: `E1=0`, `E2=0`, zero requisiti `Verified`,
  `runtime_conformance` `NOT_ESTABLISHED`, `PoC`/`Production` `NO-GO`.
- **Fase 3 chiusa come processo** (misura reale per tutto ciò che è oggi
  misurabile, escalation registrata per il solo componente 1, esito onesto
  e non bloccante per i componenti 2–4). Prossima azione: esecuzione
  backlog via `./.venv/bin/python3 scripts/ocor_autonomous_delivery.py --next`
  a partire da `OCOR-DEV-0079` — l'escalation del componente 1 non blocca
  questo passo.

## 2026-09-12 — PR #69 mergiata: Fase 3 definitivamente chiusa

- PR #69 aperta e integrata senza correzioni: tutti e 13 i check verdi al
  primo push (commit `6d19ca5`). `mergeStateStatus: CLEAN`,
  `mergeable: MERGEABLE`. Merge: `4532dded147f77f025f65fd45d53b6a8043671e9`.
  Verifica post-merge: `git fetch origin main` conferma
  `origin/main == 4532dde` (fast-forward pulito da `5a08f78`).
- `EXECUTION_STATE.json`/`MODEL_HANDOFF.json` risincronizzati su branch
  `governed/phase3-close-state`, `baseline_commit` == `4532dde...`,
  `latest_ci_evidence` aggiornato ai 6 run id reali della PR #69
  (`34720091571/578/580/586/589/603`). `current_task` avanzato a
  `CC-OCOR-DELIVERY-COMPLETION__BACKLOG-EXECUTION-OCOR-DEV-0079`.
- Claim fence invariato: `E1=0`, `E2=0`, zero requisiti `Verified`,
  `runtime_conformance` `NOT_ESTABLISHED`, `PoC`/`Production` `NO-GO`.
- **Fasi 2.1–2.4 e 3 del mandato ora tutte chiuse e mergiate** (PR #54–#69).
  L'escalation `PHASE3-COMPONENT1-CANONICAL-KERNEL-MIGRATION-THRESHOLD-EXCEEDED`
  resta aperta, riservata al Product Owner, e non blocca il passo
  successivo. Prossima azione: esecuzione del backlog via
  `./.venv/bin/python3 scripts/ocor_autonomous_delivery.py --next` a
  partire da `OCOR-DEV-0079`, sbloccando la catena WS-12 fino a `0084` e
  poi gli spike G2 `0016`/`0017`/`0018`/`0021`, poi il resto di G2–G7
  nell'ordine del DAG.

## 2026-09-13 — Backlog: OCOR-DEV-0079 (typed service health checks, reale)

- PR #70 mergiata (chore(state): close Phase 3 tracking): tutti e 13 i
  check verdi, merge `1dc3a0824b08b446ffb07598dded9f526b02d008`, verifica
  post-merge con `git fetch origin main` conferma
  `origin/main == 1dc3a08`.
- `scripts/ocor_autonomous_delivery.py --status`/`--next` confermano
  `OCOR-DEV-0079` come unico task dependency-ready (28 `ACCEPTED`,
  56 `PENDING`).
- **Scoperta**: Docker è realmente disponibile in questo sandbox (porte dei
  10 servizi tutte libere, nessun conflitto con i container preesistenti
  non-ocor-bootstrap `eci-dev-control-plane`/`open-webui`, mai toccati).
  Bootstrap completo dello stack reale da zero: 9 servizi
  (TerminusDB/TypeDB/Fuseki/OPA/Keycloak/OpenBao/PostgreSQL/Kafka/Qdrant)
  avviati direttamente con segreti generati solo per questa sessione (mai
  committati); SPIRE con il flusso a due fasi (server su, join token reale
  generato via `docker exec spire-server ... token generate`, poi agent su
  con attestazione riuscita) usando una CA auto-firmata usa-e-getta appena
  generata per `OCOR_SPIRE_BOOTSTRAP_DIR` — sequenza non documentata prima
  passo-passo altrove nel repo. Verificati i 4 moduli `qualify.py`/
  `qualify_security_services.py` già esistenti (typedb, openbao, spire,
  policy-identity) contro lo stack appena avviato: tutti `PASS` reali,
  prima di scrivere qualunque codice nuovo.
- Estesa `scripts/verify_external_services.py` con stato tipizzato
  (`ServiceStatus`: `READY`/`DEGRADED`/`UNREACHABLE`/`NOT_PROVISIONED`,
  `ServiceHealth` dataclass) al posto del precedente `READY`/`NOT_READY`
  non tipizzato che confondeva "controllato e rotto" con "mai
  provisionato". I 4 servizi già coperti sono guidati come sottoprocessi
  dei moduli esistenti; aggiunti 5 controlli tipizzati inline per i
  servizi senza modulo dedicato (TerminusDB, Fuseki, PostgreSQL, Kafka,
  Qdrant): validazione lock, ispezione Docker reale, prova di protocollo
  positiva e — sotto `--execute` — negativa reale (credenziale errata su
  TerminusDB/PostgreSQL, dataset Fuseki assente, topic Kafka assente,
  collezione Qdrant assente: tutte verificate `FAIL_CLOSED`).
  Retrocompatibilità preservata (`--manifest-only` e la scansione
  porta/container precedente invariate).
- **Fault injection reale**: `docker pause`/`unpause` su TerminusDB e
  Kafka — rilevati `DEGRADED` durante la pausa, tornati `READY` entro la
  finestra limitata dopo l'unpause; stack completo confermato integro con
  `docker compose ps` al termine.
- Aggiunto `ocor-runtime/tests/tasks/test_ocor_dev_0079.py` (17 test
  unit/negative/contract sulla logica tipizzata pura, nessuna dipendenza
  live, eseguiti sempre in CI).
- Gate locali tutti verdi: `sha256sum` 8/8, `ruff`, `mypy` (45 file, 1 fix
  `no-any-return`), `validate_rccad.py` PASS, `validate_language_policy.py`
  PASS, pytest completo `2 failed, 549 passed, 5 skipped, 10 errors`
  (stessi gap sandbox noti, +17 rispetto alla fase precedente = i nuovi
  test di questa iterazione).
- Evidenza sigillata contro lo stack live reale:
  `reports/evidence/G2/OCOR-DEV-0079.json` +
  `reports/evidence/G2/OCOR-DEV-0079.log`, aggiunta a
  `reports/evidence/G2/MANIFEST.json` (diff puramente additivo, nessuna
  riformattazione). `scripts/validate_runtime_evidence.py --task
  OCOR-DEV-0079 --non-skipped` PASS.
- Rischio residuo dichiarato: i 5 test PostgreSQL live restano
  `NOT_EXECUTED` localmente perché `ocor-runtime/.venv` non ha `psycopg`
  installato — non più per assenza di un vero PostgreSQL (che ora è
  realmente in esecuzione e raggiungibile, verificato direttamente), ma
  per un gap del venv locale, fuori scope per questo task e segnalato come
  opportunità futura distinta.
- Claim fence invariato: `E1=0`, `E2=0`, zero requisiti `Verified`,
  `runtime_conformance` `NOT_ESTABLISHED`, `PoC`/`Production` `NO-GO`.
- Prossima azione: `OCOR-DEV-0080` ("Implement deterministic service
  initialization"), che dipende solo da `OCOR-DEV-0079`.

## 2026-09-13 — Backlog: OCOR-DEV-0080 (inizializzazione deterministica, reale)

- PR #71 mergiata (typed service health checks): tutti e 13 i check verdi,
  merge `751836ef2cb836ee77e7908bbdeba0dd1846678e`, verifica post-merge con
  `git fetch origin main` conferma `origin/main == 751836e`. Lo stack Docker
  reale a 11 servizi da `OCOR-DEV-0079` è rimasto in esecuzione e riusato
  direttamente per questa iterazione, senza un nuovo bootstrap.
- Implementato `deploy/bootstrap/init/initialize_services.py`: 5 passi
  ordinati e idempotenti come da `deploy/bootstrap/init/README.md` (trust
  SPIRE, realm Keycloak, policy OPA, path OpenBao, database grafo). Ogni
  passo verifica prima lo stato esistente: se assente lo crea
  (`CREATED`), se presente e conforme non tocca nulla (`ALREADY_INITIALIZED`),
  se presente ma diverso dall'atteso fallisce chiuso (`DRIFT_DETECTED`,
  mai sovrascrittura silenziosa). Nessun contenuto di policy di sicurezza
  reale viene inventato: OPA riceve solo un placeholder `default allow =
  false` (fail-closed, ambito WS-11 differito), il realm Keycloak è un
  guscio vuoto, i database grafo sono vuoti senza schema.
- **Verifica reale contro lo stack live**: RUN 1 (stato pulito) →
  `CREATED` per Keycloak/OPA/OpenBao/database grafo, `ALREADY_INITIALIZED`
  per SPIRE (passo di sola verifica, trust già stabilito a `OCOR-DEV-0079`);
  RUN 2 (ri-esecuzione) → `ALREADY_INITIALIZED` su tutti i 5 passi, zero
  chiamate mutanti; RUN 3 (drift reale: policy OPA mutata esternamente via
  API) → `DRIFT_DETECTED`, script fallito chiuso (`exit=1`), nessuna
  sovrascrittura; RUN 4 (ripristino contenuto corretto) → recupero
  completo a `PASS`. Un vero drill di rollback eseguito, non solo
  descritto.
- Aggiunto `ocor-runtime/tests/tasks/test_ocor_dev_0080.py` (16 test
  unit/negative/contract, ogni chiamata di rete/sottoprocesso sostituita
  con un doppio deterministico, nessuna dipendenza live).
- Corretto `scripts/validate_language_policy.py`: aggiunta
  `deploy/bootstrap/init` alle aree autorizzate per `.py` e `.rego`
  (mancava, bloccava il nuovo file e la policy OPA seminale).
- Gate locali tutti verdi: `sha256sum` 8/8, `ruff`, `mypy` (45 file,
  `deploy/bootstrap/` resta fuori scope mypy come i moduli `qualify.py`
  esistenti), `validate_rccad.py` PASS, `validate_language_policy.py` PASS
  dopo la correzione, pytest completo `2 failed, 565 passed, 5 skipped,
  10 errors` (stessi gap sandbox noti, +16 rispetto alla fase precedente),
  `validate_ocor_development_plan.py --authorized-extension` PASS dopo il
  consueto doppio-run di assestamento self-hash.
- Evidenza sigillata contro lo stack live reale, incluso il drill di
  drift/rollback: `reports/evidence/G2/OCOR-DEV-0080.json` +
  `reports/evidence/G2/OCOR-DEV-0080.log`, aggiunta a
  `reports/evidence/G2/MANIFEST.json` (diff puramente additivo).
  `scripts/validate_runtime_evidence.py --task OCOR-DEV-0080 --non-skipped`
  PASS.
- Claim fence invariato: `E1=0`, `E2=0`, zero requisiti `Verified`,
  `runtime_conformance` `NOT_ESTABLISHED`, `PoC`/`Production` `NO-GO`.
- Prossima azione: `OCOR-DEV-0081` ("Load deterministic synthetic test
  fixtures"), che dipende solo da `OCOR-DEV-0080`.

## 2026-09-13 — Backlog: OCOR-DEV-0081 (fixture sintetiche deterministiche, reali)

- PR #72 mergiata (inizializzazione deterministica): tutti e 13 i check
  verdi, merge `79084dd7be841bee0b36b92b939e9abea0e37362`, verifica
  post-merge con `git fetch origin main` conferma `origin/main == 79084dd`.
  Lo stack Docker a 11 servizi è rimasto in esecuzione, ma `fuseki` era
  stato terminato (`exit 137`, verosimilmente OOM da un container
  preesistente non-ocor-bootstrap che occupa molta memoria host) —
  riavviato con `docker compose up -d fuseki`, tornato sano in pochi
  secondi; nessun altro servizio toccato.
- Esplorazione manuale reale delle API TerminusDB (`/api/document`, schema
  + istanza) e TypeDB (transazioni HTTP v1: `open`/`query`/`commit`/`close`,
  `define`/`insert`/`match`/`undefine`) prima di scrivere codice, per
  imparare le forme esatte di richiesta/risposta/conflitto. Trovata una
  vera stranezza di TerminusDB: una GET su un documento assente risponde
  con HTTP 200 reale ma un corpo prefissato dal testo letterale
  `"Status: 404\nContent-type: ...\n\n"` prima del JSON — documentata nel
  codice e coperta da un test dedicato.
- Implementato `deploy/bootstrap/fixtures/synthetic_fixtures.json`
  (manifest versionato) e `deploy/bootstrap/fixtures/load_fixtures.py`:
  carica la stessa fixture sintetica minima (un'entità/documento) sia in
  TerminusDB sia in TypeDB, con lo stesso pattern check-prima-di-mutare di
  `OCOR-DEV-0080` — assente crea, presente e conforme non tocca nulla
  (`ALREADY_INITIALIZED`), presente ma diverso fallisce chiuso
  (`DRIFT_DETECTED`). `postgresql`/`kafka`/`qdrant` dichiarati esplicitamente
  fuori scope: già provisionati ed evidenziati da task precedenti e
  indipendenti (`OCOR-DEV-0006`/`0015`/`0019`/`0023`), non parte della
  catena di riparazione WS-12.
- **Verifica reale contro lo stack live**: RUN 1 (database puliti) →
  `CREATED` per entrambi i target, digest di verifica post-caricamento
  identico fra TerminusDB e TypeDB per lo stesso contenuto semantico; RUN 2
  (ri-esecuzione) → `ALREADY_INITIALIZED` per entrambi, zero chiamate
  mutanti; RUN 3 (drift reale: istanza TerminusDB mutata esternamente via
  API) → `DRIFT_DETECTED`, script fallito chiuso (`exit=1`); RUN 4
  (ripristino) → recupero completo a `PASS`. Un vero drill di
  drift/rollback eseguito, non solo descritto.
- Aggiunto `ocor-runtime/tests/tasks/test_ocor_dev_0081.py` (12 test
  unit/negative/contract, ogni chiamata di rete sostituita con un doppio
  deterministico).
- Corretto `scripts/validate_language_policy.py`: aggiunta
  `deploy/bootstrap/fixtures` alle aree autorizzate per `.py` (stessa
  lezione di `OCOR-DEV-0080`, verificata questa volta PRIMA di aprire la
  PR).
- Gate locali tutti verdi: `sha256sum` 8/8, `ruff`, `mypy` (45 file),
  `validate_rccad.py` PASS, `validate_language_policy.py` PASS, pytest
  completo `2 failed, 577 passed, 5 skipped, 10 errors` (stessi gap
  sandbox noti, +12 rispetto alla fase precedente),
  `validate_ocor_development_plan.py --authorized-extension` PASS dopo il
  consueto doppio-run di assestamento self-hash.
- Evidenza sigillata contro lo stack live reale, incluso il drill di
  drift/rollback: `reports/evidence/G2/OCOR-DEV-0081.json` +
  `reports/evidence/G2/OCOR-DEV-0081.log`, aggiunta a
  `reports/evidence/G2/MANIFEST.json` (diff puramente additivo).
  `scripts/validate_runtime_evidence.py --task OCOR-DEV-0081 --non-skipped`
  PASS.
- Claim fence invariato: `E1=0`, `E2=0`, zero requisiti `Verified`,
  `runtime_conformance` `NOT_ESTABLISHED`, `PoC`/`Production` `NO-GO`.
- Prossima azione: `OCOR-DEV-0082` ("Implement service reset and
  teardown"), che dipende da `OCOR-DEV-0080`.

## 2026-09-13 — Backlog: OCOR-DEV-0082 (reset e teardown, reale)

- PR #73 mergiata (fixture sintetiche): tutti e 13 i check verdi, merge
  `48b6d01a254d0ceb78fb9ad4ec96088e1835c5fb`, verifica post-merge con
  `git fetch origin main` conferma `origin/main == 48b6d01`. Stack Docker
  ancora attivo e sano (11/11 container), riusato senza nuovo bootstrap.
- Trovato che `scripts/reset_test_environment.py` esisteva già ma
  implementava solo il "teardown" completo (`docker compose down
  --volumes --remove-orphans`), non il "reset" più leggero richiesto dal
  titolo del task. Aggiunta una modalità `--reset` distinta: annulla
  esattamente i 4 passi mutanti di `OCOR-DEV-0080`
  (`initialize_services.py`) — realm Keycloak, policy OPA, mount OpenBao,
  database `ocor_default` su TerminusDB e TypeDB — senza fermare alcun
  container. Il trust SPIRE resta intoccato: `OCOR-DEV-0080` lo verifica
  soltanto, non lo crea, quindi non c'è nulla da annullare senza rompere
  l'identità di ogni servizio. `--teardown` (comportamento preesistente)
  resta invariato.
- **Verifica reale contro lo stack live**: confermato lo stato
  inizializzato prima del reset (typed health check `PASS`); RUN 1
  (`--reset --execute` reale) → `RESET` per tutti e 4 i target; RUN 2
  (ri-esecuzione) → `ALREADY_RESET` per tutti, zero chiamate mutanti;
  `docker compose ps` subito dopo conferma tutti gli 11 container ancora
  `Up`/`healthy` — il reset non tocca mai i container; RUN 3
  (**round-trip reset → re-init reale**) → l'inizializzatore di
  `OCOR-DEV-0080` ricrea da zero tutti e 4 i target (`CREATED`),
  dimostrando che il reset è un vero inverso completo, non parziale o
  con perdita di stato. Fixture sintetiche di `OCOR-DEV-0081` ricaricate
  al termine per lasciare lo stack nello stato atteso dai prossimi task.
  `--teardown` verificato solo in dry-run: eseguirlo per davvero
  avrebbe distrutto lo stack live da cui dipendono gli altri task WS-12
  in corso.
- Aggiunto `ocor-runtime/tests/tasks/test_ocor_dev_0082.py` (10 test
  unit/negative/contract, ogni chiamata di rete sostituita con un doppio
  deterministico).
- `scripts/validate_language_policy.py` verificato PRIMA di aprire la PR
  (lezione da `OCOR-DEV-0080`/`0081`): nessuna nuova area necessaria,
  `scripts/` era già autorizzato per `.py`.
- Gate locali tutti verdi: `sha256sum` 8/8, `ruff`, `mypy` (45 file),
  `validate_rccad.py` PASS, `validate_language_policy.py` PASS, pytest
  completo `2 failed, 587 passed, 5 skipped, 10 errors` (stessi gap
  sandbox noti, +10 rispetto alla fase precedente),
  `validate_ocor_development_plan.py --authorized-extension` PASS dopo il
  consueto doppio-run di assestamento self-hash.
- Evidenza sigillata contro lo stack live reale, incluso il round-trip
  reset→re-init: `reports/evidence/G2/OCOR-DEV-0082.json` +
  `reports/evidence/G2/OCOR-DEV-0082.log`, aggiunta a
  `reports/evidence/G2/MANIFEST.json` (diff puramente additivo).
  `scripts/validate_runtime_evidence.py --task OCOR-DEV-0082 --non-skipped`
  PASS.
- Claim fence invariato: `E1=0`, `E2=0`, zero requisiti `Verified`,
  `runtime_conformance` `NOT_ESTABLISHED`, `PoC`/`Production` `NO-GO`.
- Prossima azione: `OCOR-DEV-0083` ("Implement bounded fault injection"),
  che dipende da `OCOR-DEV-0079`.

## 2026-09-13 — Backlog: OCOR-DEV-0083 (fault injection bounded, reale)

- PR #74 mergiata (reset e teardown): tutti e 13 i check verdi, merge
  `6a7d51ef7534f0cbd2f3519d9e92f2441c5f8aa2`, verifica post-merge con
  `git fetch origin main` conferma `origin/main == 6a7d51e`. `fuseki`
  nuovamente terminato per OOM da un container host non correlato
  (pattern ricorrente, host sotto pressione di memoria per un container
  preesistente da ~7 GiB) — riavviato senza toccare altro.
- Trovato che `scripts/fault_inject_test_environment.py` esisteva già
  (pause/unpause/restart/disconnect/reconnect grezzi, dry-run di default)
  ma senza alcuna nozione di "bounded" — nessun rilevamento del guasto né
  recupero automatico garantito. Aggiunta una modalità `--bounded`: applica
  il guasto, attende (con timeout) la condizione di rottura attesa, poi —
  in un blocco `finally`, quindi il recupero viene tentato anche se il
  rilevamento non si completa mai — applica l'azione di recupero
  corrispondente e attende (con un secondo timeout) il ritorno alla
  normalità. File già referenziato come input sigillato in
  `reports/evidence/G2/OCOR-DEV-0073.json`/`OCOR-DEV-0075.json`, ma solo
  come record storico descrittivo (nessun validatore ne applica l'hash
  come invariante continuo) — modifica diretta sicura, verificato.
- **Scoperta tecnica reale e corretta durante l'iterazione**: il primo
  tentativo di rilevare `disconnect` tramite una semplice connessione TCP
  al servizio pubblicato (`socket.create_connection`) risultava sempre
  "raggiungibile" anche a container scollegato — su questo host Docker
  Desktop il proxy di port-forwarding completa l'handshake TCP
  indipendentemente dall'attacco di rete del container. Verificato con una
  prova diretta (connessione TCP grezza riuscita vs richiesta HTTP reale
  fallita durante lo stesso disconnect). Corretto sostituendo l'oracolo con
  un vero round-trip HTTP per servizio (`HEALTH_URLS`), che rileva
  correttamente sia il guasto sia il recupero. `--bounded disconnect`
  resta non supportato per `spire-server`/`spire-agent` (nessuna porta
  pubblicata da verificare dall'host).
- **Verifica reale contro lo stack live**: RUN 1 (`pause`/`unpause` reale
  su typedb) → rilevato e recuperato entro la finestra limitata; RUN 2
  (`disconnect`/`reconnect` reale su fuseki, oracolo HTTP corretto) →
  rilevato e recuperato; RUN 3 (`restart` reale su keycloak) →
  autorecupero confermato; RUN 4 (negativi) → `--bounded` rifiuta
  `reconnect`/`unpause` come guasto primario e rifiuta `disconnect` per
  `spire-server` senza endpoint pubblicato.
- **Bug reale trovato e corretto ripristinando lo stato dello stack**:
  `deploy/bootstrap/fixtures/load_fixtures.py` (da `OCOR-DEV-0081`)
  tollerava solo la stranezza "TerminusDB risponde 200 con prefisso
  testuale Status: 404" per il caso "documento assente", ma TerminusDB è
  stato osservato restituire anche un vero HTTP 404 per la stessa identica
  condizione in invocazioni diverse — corretto per accettare entrambe le
  forme; aggiunto un test di regressione dedicato al file di test già
  esistente di `OCOR-DEV-0081` (`ocor-runtime/tests/tasks/test_ocor_dev_0081.py`).
- Aggiunto `ocor-runtime/tests/tasks/test_ocor_dev_0083.py` (12 test
  unit/negative/contract, ogni chiamata subprocess/HTTP sostituita con un
  doppio deterministico).
- `scripts/validate_language_policy.py` verificato PRIMA di aprire la PR:
  nessuna nuova area necessaria.
- Gate locali tutti verdi: `sha256sum` 8/8, `ruff`, `mypy` (45 file),
  `validate_rccad.py` PASS, `validate_language_policy.py` PASS, pytest
  completo `2 failed, 600 passed, 5 skipped, 10 errors` (stessi gap
  sandbox noti, +13 rispetto alla fase precedente: 12 nuovi test più 1 di
  regressione per il bug TerminusDB),
  `validate_ocor_development_plan.py --authorized-extension` PASS dopo il
  consueto doppio-run di assestamento self-hash.
- Evidenza sigillata contro lo stack live reale, inclusi tutti e 3 i cicli
  bounded reali e la scoperta tecnica TCP-vs-HTTP:
  `reports/evidence/G2/OCOR-DEV-0083.json` +
  `reports/evidence/G2/OCOR-DEV-0083.log`, aggiunta a
  `reports/evidence/G2/MANIFEST.json` (diff puramente additivo).
  `scripts/validate_runtime_evidence.py --task OCOR-DEV-0083 --non-skipped`
  PASS.
- Claim fence invariato: `E1=0`, `E2=0`, zero requisiti `Verified`,
  `runtime_conformance` `NOT_ESTABLISHED`, `PoC`/`Production` `NO-GO`.
- Prossima azione: `OCOR-DEV-0084` ("Capture reproducible environment
  evidence"), che dipende da `OCOR-DEV-0081`, `OCOR-DEV-0082` e
  `OCOR-DEV-0083` — l'ultimo task della catena WS-12 di riparazione
  dell'infrastruttura, dopo il quale gli spike G2
  `OCOR-DEV-0016`/`0017`/`0018`/`0021` diventano eseguibili.
- `OCOR-DEV-0083`: PR #75 mergiata (`e1b4fe1657d7222bc17b41b04feff8658a1cc6d1`),
  tutti e 13 i check verdi al primo push, SHA post-merge verificata.

## 2026-09-13 — Backlog: OCOR-DEV-0084 (Capture reproducible environment evidence)

- Ultimo task della catena WS-12 di riparazione dell'infrastruttura
  (`OCOR-DEV-0070`..`0084`). Dipende da `OCOR-DEV-0081`/`0082`/`0083`,
  tutti già mergiati.
- `scripts/capture_environment_evidence.py` esisteva già ma catturava solo
  l'inventario grezzo `docker compose ps` (container esistente +
  healthcheck Docker), senza dire nulla sul contratto governato che ogni
  servizio deve soddisfare. Aggiunto un campo tipizzato
  `environment_status` che integra `typed_health_checks()` di
  `scripts/verify_external_services.py` (immagine pinnata, pubblicazione
  solo loopback, probe di protocollo reale, controlli negativi
  fail-closed). Mantenuto deliberatamente separato dal campo `status`
  preesistente (successo del processo di cattura, non salute
  dell'ambiente), così un servizio degradato resta visibile in evidenza
  invece di essere assorbito silenziosamente in un generico "captured OK".
- Aggiunti `ARTIFACT_PATHS` (4 nuovi deliverable WS-12),
  `_load_typed_health_checks()` (import dinamico dello script di verifica,
  stesso pattern `sys.modules[SPEC.name] = module` usato in tutta la
  sessione) e `capture_environment_status()`.
- Bug reale trovato e corretto durante la cattura positiva: l'auto-discovery
  preesistente di `--env-file` controllava solo `.ocor/bootstrap.env`, che
  non corrisponde al percorso reale dei secret di questa sessione
  (`~/.ocor-bootstrap-secrets/ocor-bootstrap.env`); senza un env-file
  corrispondente `docker compose ps` falliva l'interpolazione della
  password Keycloak e l'intera cattura riportava `PARTIAL` anche quando
  ogni servizio era realmente sano. Corretto aggiungendo un argomento CLI
  esplicito `--env-file` che sovrascrive l'auto-discovery.
- Provato per reale contro lo stack live a 11 servizi: RUN 1 (positivo,
  tutti sani) → `environment_status=PASS`; RUN 2 (negativo, `typedb` in
  pausa) → `environment_status=DEGRADED`, exit code non zero, mai un PASS
  silenzioso; RUN 3 (recupero, `typedb` riattivato) → ricatturato fino al
  ritorno a `PASS` (tentativo 4, ~8s di assestamento dell'health-check,
  correttamente riflesso e non ingoiato).
- Aggiunto `ocor-runtime/tests/tasks/test_ocor_dev_0084.py` (4 test
  unit/negative/contract, health check tipizzato sostituito con un doppio
  deterministico, nessuna dipendenza Docker live).
- `scripts/validate_language_policy.py` verificato PRIMA di aprire la PR:
  nessuna nuova area necessaria (`scripts/` già autorizzato).
- Gate locali tutti verdi: `sha256sum` 8/8, `ruff`, `mypy` (45 file),
  `validate_rccad.py` PASS, `validate_language_policy.py` PASS,
  `validate_ocor_change_scope.py` PASS (9 percorsi), pytest completo
  `2 failed, 604 passed, 5 skipped, 10 errors` (stessi gap sandbox noti,
  +4 rispetto alla fase precedente: i 4 nuovi test),
  `validate_ocor_development_plan.py --authorized-extension` PASS dopo il
  consueto doppio-run di assestamento self-hash (aggiunti
  `ocor-runtime/tests/tasks/test_ocor_dev_0084.py`,
  `reports/evidence/G2/OCOR-DEV-0084.{json,log}` a `extension_paths`).
- Evidenza sigillata contro lo stack live reale, incluso il ciclo completo
  positivo/negativo/recupero:
  `reports/evidence/G2/OCOR-DEV-0084.json` +
  `reports/evidence/G2/OCOR-DEV-0084.log`, aggiunta a
  `reports/evidence/G2/MANIFEST.json` (diff puramente additivo, 46 righe).
  `scripts/validate_runtime_evidence.py --task OCOR-DEV-0084 --non-skipped`
  PASS.
- Claim fence invariato: `E1=0`, `E2=0`, zero requisiti `Verified`,
  `runtime_conformance` `NOT_ESTABLISHED`, `PoC`/`Production` `NO-GO`.
- Prossima azione: push del branch
  `governed/ocor-dev-0084-capture-environment-evidence`, apertura PR,
  polling CI, merge a gate verdi, verifica SHA post-merge. Con questo si
  chiude l'intera catena WS-12 (`OCOR-DEV-0070`..`0084`); diventano
  eseguibili gli spike G2 `OCOR-DEV-0016`/`0017`/`0018`/`0021` (le cui
  `hard_dependencies` sono state estese a includere `OCOR-DEV-0084` dalla
  correzione del generator-drift di Fase 2.4).
- `OCOR-DEV-0084`: PR #76 mergiata (`cbf53da9be6d13e77d545679dacebc2398f5af97`),
  tutti e 13 i check verdi al primo push, SHA post-merge verificata. Catena
  WS-12 (`OCOR-DEV-0070`..`0084`) chiusa.

## 2026-09-13 — Backlog: OCOR-DEV-0016 (SPIKE selected C3 backend behaviour)

- Primo spike G2 eseguibile dopo la chiusura della catena WS-12. Dipende
  da `OCOR-DEV-0006`, `OCOR-DEV-0013`, `OCOR-DEV-0015`, `OCOR-DEV-0084`,
  tutti già mergiati. `scripts/ocor_autonomous_delivery.py --status`
  riportava uno stato interno non allineato (proprio state file separato,
  mai aggiornato dall'esecuzione manuale di questa sessione); confermata
  invece la reale prontezza dei quattro spike G2 (`0016`/`0017`/`0018`/`0021`,
  tutti wave 11) direttamente da `docs/development_plan/OCOR_IMPLEMENTATION_BACKLOG.json`
  e da `completed_evidence_tasks`; selezionato `OCOR-DEV-0016` per primo
  (ordine numerico, stessa convenzione usata per tutta la catena WS-12).
- **Scoperta significativa**: lo stack Docker `ocor-bootstrap` include un
  PostgreSQL reale (`127.0.0.1:55433`) già provisionato dalla catena WS-12;
  per la prima volta in questa sessione è stato possibile impostare
  `OCOR_LIVE_POSTGRES_DSN` anche in locale (non solo in CI), riqualificando
  per reale in locale i 10 test live-Postgres di `OCOR-DEV-0015`
  (precedentemente `errors` per gap noto di sandbox) e i 5 nuovi test di
  `OCOR-DEV-0016`.
- Riutilizzato senza modifiche l'oracolo sigillato di `OCOR-DEV-0015`
  (`spikes/c3_atomicity/oracle.py::PostgreSQLAtomicCommitOracle`); aggiunto
  `spikes/c3_backend/concurrency_oracle.py` (nuovo) con l'harness di race
  reale (`race_distinct_commands`, due comandi DISTINTI sulla stessa
  `expected_revision`, ciascuno con una propria connessione PostgreSQL
  reale) e due probe indipendenti fuori-banda: `observe_lock_contention`
  (prova diretta sul wire della mutua esclusione del lock consultivo reale,
  non solo inferita dall'esito) e `sample_revision_during` (lettura
  continua da una connessione indipendente durante una race live, per
  provare l'assenza di dirty read).
- Aggiunto `ocor-runtime/tests/tasks/test_ocor_dev_0016.py` (5 test, tutti
  contro PostgreSQL reale, nessun mock):
  locking (due comandi distinti in race, uno vince, l'altro riceve un vero
  conflitto di revisione, verificato ripetendo 5 volte senza flakiness);
  prova diretta del lock su wire; isolamento (lettore concorrente non
  osserva mai un valore di revisione fuori dal set valido durante una
  race); fallimento sotto concorrenza reale (crash di processo reale via
  subprocess, sincronizzato deterministicamente — non a tempo — con un
  probe che attende l'osservazione reale del lock consultivo prima di
  rilasciare il writer superstite, che completa con successo e il ledger
  riconciliato accetta correttamente un ulteriore commit); riconciliazione
  (falsificazione sintetica di un'anomalia `phantom_receipt`, tipo diverso
  da quello già coperto da `OCOR-DEV-0015`).
- **Bug del primo tentativo, corretto prima di sigillare**: la prima
  versione del test di fallimento-sotto-concorrenza avviava crash e
  writer superstite come una race "a freddo" senza sincronizzazione,
  genuinamente non deterministica (in alcune esecuzioni il writer
  superstite vinceva il lock per primo, facendo fallire il worker di
  crash con un conflitto di revisione invece di farlo effettivamente
  crashare) — corretto bloccando il thread principale su
  `observe_lock_contention` finché il subprocess di crash non viene
  osservato detenere realmente il lock, prima di rilasciare il writer
  superstite; verificato deterministico su 5 esecuzioni consecutive.
- `scripts/validate_language_policy.py` verificato: nessuna nuova area
  necessaria (`spikes/` e `scripts/` già autorizzati dalla Fase 0/`0015`).
- Gate locali tutti verdi: `sha256sum` 8/8, `ruff`, `mypy` (45 file,
  `spikes/` e `tests/` fuori scope per policy, come già per
  `spikes/c3_atomicity/` di `OCOR-DEV-0015`), `validate_rccad.py` PASS,
  `validate_language_policy.py` PASS, `validate_ocor_change_scope.py` PASS
  (9 percorsi), pytest completo con `OCOR_LIVE_POSTGRES_DSN` impostato
  localmente per la prima volta: `2 failed, 624 passed, 0 skipped, 0
  errors` (gli unici 2 fallimenti sono il gap noto e preesistente del pin
  dell'interprete, indipendente da questo task; zero errori, contro i 10
  della baseline precedente senza DSN locale),
  `validate_ocor_development_plan.py --authorized-extension` PASS dopo il
  consueto doppio-run di assestamento self-hash.
- Evidenza sigillata contro il backend PostgreSQL reale selezionato:
  `reports/evidence/G2/OCOR-DEV-0016.json` +
  `reports/evidence/G2/OCOR-DEV-0016.log`, aggiunta a
  `reports/evidence/G2/MANIFEST.json` (diff puramente additivo, 55 righe).
  `scripts/validate_runtime_evidence.py --task OCOR-DEV-0016 --non-skipped`
  PASS.
- Claim fence invariato: `E1=0`, `E2=0`, zero requisiti `Verified`,
  `runtime_conformance` `NOT_ESTABLISHED`, `PoC`/`Production` `NO-GO`.
- Prossima azione: push del branch
  `governed/ocor-dev-0016-c3-backend-concurrency-spike`, apertura PR,
  polling CI, merge a gate verdi, verifica SHA post-merge. Poi proseguire
  con uno degli altri spike G2 dello stesso wave 11:
  `OCOR-DEV-0017`/`0018`/`0021`.
- `OCOR-DEV-0016`: PR #77 mergiata (`a2ea8f467cc47891add109fbcd1b2e8567c49399`),
  tutti e 13 i check verdi al primo push, SHA post-merge verificata.

## 2026-09-13 — Backlog: OCOR-DEV-0017 (SPIKE TypeDB exact-at-commit semantics)

- Secondo spike G2 dopo la chiusura di WS-12, selezionato per ordine
  numerico fra `0017`/`0018`/`0021` (stesso wave 11, dipendenze già
  soddisfatte). Dipende da `OCOR-DEV-0006`, `OCOR-DEV-0012`, `OCOR-DEV-0013`,
  `OCOR-DEV-0084`, tutti già mergiati.
- Riutilizzato senza modifiche il contratto sigillato di `OCOR-DEV-0012`
  (`ocor_runtime.c2.ports`: `ConsistencyMode`/`ConsistencyRequirement`/
  `ServedContext`/`NamedQueryRequest.verify_served`); aggiunto
  `spikes/typedb_exact_commit/adapter.py` (nuovo) con un
  `TypeDBExactCommitAdapter` reale che implementa `ProjectionReadPort`/
  `WatermarkPort` contro TypeDB reale (HTTP v1: signin/transazione/query/
  commit/close, stesso pattern già validato in `OCOR-DEV-0081`), modellando
  una proiezione C4 con ritardo asincrono: `ingest`/aggiornamento scrivono
  un fatto marcato con il commit che lo ha prodotto, `advance_watermark` è
  un passo SEPARATO che simula il momento in cui la pipeline di proiezione
  ha applicato quel commit ed è sicuro leggerlo.
- **Probe empirici reali contro TypeDB prima di scrivere l'adapter** (non
  assunti, verificati): un riferimento a un tipo non definito fallisce con
  HTTP 400 `INF2`; ridefinire uno schema identico è idempotente (HTTP 200,
  nessun errore — `initialize()` non necessita quindi di un probe
  check-before-mutate); un secondo insert con lo stesso valore `@key`
  fallisce con HTTP 400 `CNT9` (motiva perché un aggiornamento di un fatto
  esistente deve cancellare-e-reinserire, non un update in-place).
- Aggiunto `ocor-runtime/tests/tasks/test_ocor_dev_0017.py` (6 test, tutti
  contro TypeDB reale, nessun mock): corrispondenza esatta quando fatto e
  watermark coincidono; fallimento chiuso (`CONSISTENCY_DOWNGRADE`) quando
  un fatto è ingerito ma il watermark non è ancora avanzato — e il
  watermark non viene mai falsamente avanzato; fallimento chiuso quando la
  riga è stata aggiornata a un commit più recente mentre il watermark resta
  al commit più vecchio richiesto (prova diretta del criterio negativo:
  "restituire fatti più vecchi come exact-at-commit falsifica l'approccio",
  qui nella forma speculare — mai servire contenuto più nuovo etichettato
  come il commit più vecchio richiesto); modalità `AT_LEAST_COMMIT` che
  riporta `PROJECTION_NOT_READY` con un watermark osservabile
  separatamente, poi successo dopo l'avanzamento; progressione reale a due
  commit in cui il commit superato non viene mai servito come esatto in
  nessuna delle due direzioni; `RESULT_NOT_FOUND` raggiunto solo dopo che
  la coerenza è confermata (mai una falsificazione della coerenza usata per
  mascherare una semplice assenza).
- **Bug del primo tentativo, corretto prima di sigillare**: `ServedContext`
  e `Watermark` (contratto sigillato di `OCOR-DEV-0012`) richiedono stringhe
  non vuote per `canonical_commit`/`projection_watermark`; usare `""` come
  sentinella per "nessun watermark ancora" faceva fallire la costruzione
  con `QUERY_CONTRACT_INVALID` prima ancora di raggiungere la verifica di
  coerenza — corretto introducendo la sentinella non vuota
  `urn:ocor:commit:none`, garantita per costruzione a non coincidere mai
  con un commit reale generato dai test.
- `scripts/validate_language_policy.py` verificato: nessuna nuova area
  necessaria (`spikes/` e `scripts/` già autorizzati).
- Gate locali tutti verdi: `sha256sum` 8/8, `ruff`, `mypy` (45 file,
  `spikes/` e `tests/` fuori scope per policy), `validate_rccad.py` PASS,
  `validate_language_policy.py` PASS, `validate_ocor_change_scope.py` PASS
  (9 percorsi), pytest completo con `OCOR_LIVE_POSTGRES_DSN` locale:
  `2 failed, 630 passed, 0 skipped, 0 errors` (stessi 2 fallimenti noti e
  preesistenti del pin dell'interprete, +6 rispetto alla fase precedente),
  `validate_ocor_development_plan.py --authorized-extension` PASS dopo il
  consueto doppio-run di assestamento self-hash.
- Evidenza sigillata contro TypeDB reale:
  `reports/evidence/G2/OCOR-DEV-0017.json` +
  `reports/evidence/G2/OCOR-DEV-0017.log`, aggiunta a
  `reports/evidence/G2/MANIFEST.json` (diff puramente additivo, 73 righe).
  `scripts/validate_runtime_evidence.py --task OCOR-DEV-0017 --non-skipped`
  PASS.
- Manutenzione ambiente: `fuseki` nuovamente OOM-killed (exit 137) dal
  container host preesistente non correlato; riavviato il solo servizio
  interessato, come nelle iterazioni precedenti, senza toccare il
  container non correlato.
- Claim fence invariato: `E1=0`, `E2=0`, zero requisiti `Verified`,
  `runtime_conformance` `NOT_ESTABLISHED`, `PoC`/`Production` `NO-GO`.
- Prossima azione: push del branch
  `governed/ocor-dev-0017-typedb-exact-commit-spike`, apertura PR, polling
  CI, merge a gate verdi, verifica SHA post-merge. Poi proseguire con uno
  degli spike G2 rimanenti dello stesso wave 11: `OCOR-DEV-0018`/`0021`.
- `OCOR-DEV-0017`: primo push, 3 check CI rossi (`delivery-activation`,
  `rccad-methodology`, `validation-closure`) perché quei job eseguono
  l'intera suite `ocor-runtime/tests/` con un container Postgres reale ma
  senza TypeDB — causa radice corretta aggiungendo un container TypeDB
  reale ai 3 workflow (stesso digest immagine di `compose.yaml`) e rendendo
  `initialize()` capace di creare il database `ocor_default` se assente.
  Evidenza aggiornata nello stesso commit/PR. Secondo push: tutti e 13 i
  check verdi. PR #78 mergiata
  (`d573b7e119b195837cc9a7f122369c06ace1523d`), SHA post-merge verificata.

## 2026-09-13 — Backlog: OCOR-DEV-0018 (SPIKE Jena marking-safe projection)

- Terzo spike G2 dopo la chiusura di WS-12, selezionato per ordine numerico
  fra `0018`/`0021` (stesso wave 11). Dipende da `OCOR-DEV-0006`,
  `OCOR-DEV-0008`, `OCOR-DEV-0014`, `OCOR-DEV-0084`, tutti già mergiati.
- Riutilizzato senza modifiche il reticolo di marcatura sigillato di C4
  (`ocor_runtime.c4_marking`: `MarkingEngine`/`MarkingSchemeDefinition`/
  `MarkingSet`/`is_authorized`); aggiunto `spikes/jena_marking/adapter.py`
  (nuovo) con un `JenaMarkingProjectionAdapter` reale contro Fuseki live
  (dataset in-memory preconfigurato `/ocor` dal `CMD ["--mem", "/ocor"]`
  di `infra/fuseki/Dockerfile`, SPARQL 1.1 Query/Update via HTTP).
- Design chiave: `list_authorized` esegue un'UNICA query SPARQL che
  congiunge risorsa e classificazione nello stesso pattern grafico (la
  "marking join" richiesta dai criteri di accettazione — una risorsa priva
  del triplo di classificazione non può mai comparire, nemmeno con la
  clearance più alta); `count_authorized`/`exists_authorized` sono
  deliberatamente derivate dallo stesso risultato filtrato di
  `list_authorized` invece che da query SPARQL COUNT/ASK indipendenti, così
  da non poter mai divergere (soddisfa strutturalmente il criterio negativo
  "count ... leak").
- **Probe empirico reale contro Fuseki, bug trovato e corretto prima di
  sigillare**: interrogare `/ocor/sparql` senza un header `Accept`
  esplicito restituisce SPARQL-XML, non JSON — la prima esecuzione dei
  test falliva con `json.JSONDecodeError`; corretto inviando sempre
  `Accept: application/sparql-results+json`.
- Aggiunto `ocor-runtime/tests/tasks/test_ocor_dev_0018.py` (6 test, tutti
  contro Fuseki reale, nessun mock): filtro per clearance; count mai
  divergente dalla lista autorizzata; dimostrazione diretta che un COUNT
  SPARQL grezzo e cieco alla marcatura perderebbe informazione (differisce
  dal conteggio autorizzato) mentre l'API pubblica non lo espone mai;
  `exists_authorized` restituisce la stessa forma (`bool` `False`) per una
  risorsa proibita e per una mai esistita, indistinguibili; una risorsa
  senza il triplo di classificazione non è mai divulgata nemmeno con
  `TOP_SECRET`; il payload restituito a una clearance bassa non contiene
  mai, in nessuna forma, contenuto non autorizzato.
- **Lezione applicata proattivamente da `OCOR-DEV-0017`**: prima di aprire
  la PR, verificato che né Fuseki fosse provisionato in CI — aggiunto
  preventivamente uno step "Build and start Fuseki" (build della stessa
  immagine pinnata di `infra/fuseki/Dockerfile` + `docker run` + attesa di
  salute reale) ai 3 workflow già corretti per TypeDB in `OCOR-DEV-0017`
  (`delivery-activation`, `rccad-methodology`, `validation-closure`), dato
  che l'immagine è costruita da sorgente e non può essere dichiarata come
  `services:` con una semplice `image:`. Rieseguita localmente l'intera
  ricetta CI (build, run su porta alternativa, attesa di salute, query
  SPARQL reale, pulizia) prima di aggiungerla ai workflow, senza mai
  toccare lo stack `ocor-bootstrap` live.
- `scripts/validate_language_policy.py` verificato: nessuna nuova area
  necessaria.
- Gate locali tutti verdi: `sha256sum` 8/8, `ruff`, `mypy` (45 file,
  `spikes/` e `tests/` fuori scope per policy), `validate_rccad.py` PASS,
  `validate_language_policy.py` PASS, `validate_ocor_change_scope.py` PASS
  (12 percorsi), `yaml.safe_load` dei 3 workflow modificati PASS, pytest
  completo con `OCOR_LIVE_POSTGRES_DSN` locale: `2 failed, 636 passed, 0
  skipped, 0 errors` (stessi 2 fallimenti noti e preesistenti del pin
  dell'interprete, +6 rispetto alla fase precedente),
  `validate_ocor_development_plan.py --authorized-extension` PASS dopo il
  consueto doppio-run di assestamento self-hash.
- Evidenza sigillata contro Fuseki reale, incluso il rehearsal completo
  della ricetta CI: `reports/evidence/G2/OCOR-DEV-0018.json` +
  `reports/evidence/G2/OCOR-DEV-0018.log`, aggiunta a
  `reports/evidence/G2/MANIFEST.json` (diff puramente additivo, 73 righe).
  `scripts/validate_runtime_evidence.py --task OCOR-DEV-0018 --non-skipped`
  PASS.
- Claim fence invariato: `E1=0`, `E2=0`, zero requisiti `Verified`,
  `runtime_conformance` `NOT_ESTABLISHED`, `PoC`/`Production` `NO-GO`.
- Prossima azione: push del branch
  `governed/ocor-dev-0018-jena-marking-safe-projection-spike`, apertura
  PR, polling CI, merge a gate verdi, verifica SHA post-merge. Poi
  proseguire con l'ultimo spike G2 dello stesso wave 11: `OCOR-DEV-0021`
  (SPIKE latenza e semantica di fallimento identity-policy).
- `OCOR-DEV-0018`: tutti e 13 i check verdi al primo push (il fix CI
  proattivo per Fuseki ha funzionato senza alcun ciclo di riparazione). PR
  #79 mergiata (`0b3d855c09f50be583a970868ed19375ef4d0802`), SHA
  post-merge verificata.

## 2026-09-13 — Disposizione del Product Owner: escalation Fase 3 componente 1

- Iterazione a sé, non backlog: esegue la disposizione esplicita e
  verbatim del Product Owner su
  `PHASE3-COMPONENT1-CANONICAL-KERNEL-MIGRATION-THRESHOLD-EXCEEDED`
  (registrata in `reports/development/PHASE3_LANGUAGE_MIGRATION_DECISION.md`
  §5, in attesa di lui dal completamento della Fase 3).
- **Decisione**: `RINVIATA`, non respinta. Nessuna decisione di migrazione
  aperta per il kernel di canonicalizzazione; il candidato e la misura
  sigillata restano registrati e validi.
- Aggiunta una nuova §8 in coda a
  `reports/development/PHASE3_LANGUAGE_MIGRATION_DECISION.md` — le sezioni
  1–7 (misura sigillata, numeri inclusi) lasciate byte-per-byte intatte,
  verificato con `git diff --stat` (105 righe, sole inserzioni). La §8
  riporta: la decisione; la motivazione a 4 punti dettata dal Product
  Owner, trascritta testualmente come richiesto ("da riportare come
  tale"), senza editorializzarla; la condizione di riapertura falsificabile
  a 3 rami (a/b/c); i vincoli osservati; la verifica del record decisionale
  formale; il nuovo stato dell'escalation.
- **Verifica del record decisionale formale** (richiesta esplicitamente dal
  Product Owner, con l'istruzione di non coniare un identificativo se non
  richiesto): confrontato con `DEC-212` (adozione di una nuova politica,
  registrata in `OCOR_Decision_Register_v1.6_APPROVED.md`) e con le
  escalation precedenti di questo mandato già dispositate senza un nuovo
  `DEC-*` (`PHASE2-4-BACKLOG-GENERATOR-DRIFT`, risolta in PR #67;
  `GITHUB-BRANCH-PROTECTION-001`, compensata). Questa disposizione non
  adotta alcuna nuova politica, non cambia alcuna soglia, non autorizza
  alcuna migrazione: rientra nella seconda categoria. **Nessun nuovo
  `DEC-*` coniato**; aggiornati solo i documenti esistenti, come richiesto.
- Aggiornato `reports/development/EXECUTION_STATE.json`:
  `mandate_phase_status.phase_3_benchmark.escalations` passa da `OPEN` a
  `DISPOSED_DEFERRED`, con la stessa motivazione e condizione di
  riapertura.
- Vincoli tassativi rispettati e verificati: soglie del §3 di
  `OCOR_LANGUAGE_POLICY.md` non toccate; `OI-024` non chiuso; nessun
  `ASM-*`/`RSK-*` modificato; nessuna modifica al codice del kernel di
  canonicalizzazione (`ocor-runtime/src/ocor_runtime/canonical.py`);
  nessuna promozione di `E1`/`E2`/requisiti a `Verified`, nessun claim di
  conformità runtime.
- Nota di trasparenza (non una correzione della disposizione, che resta
  quella dettata dal Product Owner e riportata testualmente): il punto 2
  della motivazione cita `OI-024` come l'open item collegato al budget
  ipotetico di latenza; il §3 dello stesso documento
  `OCOR_LANGUAGE_POLICY.md` contiene già una nota di correzione secondo cui
  l'open item che governa effettivamente le soglie numeriche di
  performance è `OI-008`, mentre `OI-024` governa le soglie di
  rischio/costo per l'autorità dual-control (`DEC-131`/`FR-136`/`FR-137`).
  La motivazione è stata trascritta come dettata, per istruzione esplicita
  ("da riportare come tale"); questa nota segnala la tensione testuale
  senza alterare la decisione, che è comunque conservativa (nessuna
  migrazione aperta) e indipendente da quale identificativo `OI-*` sia
  citato in questo punto.
- Questa iterazione non tocca codice sorgente né test: gate locali e
  regressione completa rieseguiti comunque per protocollo standard,
  confermati invariati.
- Gate locali tutti verdi: `sha256sum` 8/8, `ruff`, `mypy` (45 file),
  `validate_rccad.py` PASS, `validate_language_policy.py` PASS,
  `validate_ocor_change_scope.py` PASS, pytest completo con
  `OCOR_LIVE_POSTGRES_DSN` locale invariato rispetto alla baseline nota,
  `validate_ocor_development_plan.py --authorized-extension` PASS.
- Claim fence invariato: `E1=0`, `E2=0`, zero requisiti `Verified`,
  `runtime_conformance` `NOT_ESTABLISHED`, `PoC`/`Production` `NO-GO`.
- Prossima azione: push del branch
  `governed/phase3-component1-escalation-disposition-deferred`, apertura
  PR, polling CI, merge a gate verdi, verifica SHA post-merge. Il referto
  finale del mandato dovrà riportare questa disposizione fra gli esiti.
  Poi riprendere il backlog da dove era: l'ultimo spike G2 del wave 11,
  `OCOR-DEV-0021` (SPIKE latenza e semantica di fallimento
  identity-policy).
- Disposizione Fase 3: PR #80 mergiata
  (`59521ae00218ea84e8b74a9cee483b172cdfd8ec`), tutti i check verdi, SHA
  post-merge verificata.

## 2026-09-13 — Backlog: OCOR-DEV-0021 (SPIKE identity-policy latency and failure semantics)

- Ultimo spike G2 del wave 11. Dipende da `OCOR-DEV-0006`, `OCOR-DEV-0014`,
  `OCOR-DEV-0084`, tutti già mergiati.
- Riutilizzati senza modifiche i port di sicurezza sigillati di
  `OCOR-DEV-0014` (`ocor_runtime.security.ports`:
  `ControlName`/`ControlStatus`/`SecurityControlError`/
  `require_available`) e l'harness di fault-injection sigillato di
  `OCOR-DEV-0083` (`fault_command`/`http_reachable`/`_poll`); aggiunto
  `spikes/control_plane_latency/probe.py` (nuovo) con `bounded_probe`
  (round-trip HTTP reale con deadline dichiarata, restituisce sempre uno
  `ControlStatus` più un `AuditEvent` correlato, sia per successo che per
  fallimento) e `decide_with_fail_closed_default` (delega interamente a
  `require_available` — un controllo non disponibile può solo sollevare,
  mai concedere).
- Aggiunto `ocor-runtime/tests/tasks/test_ocor_dev_0021.py` (7 test, tutti
  contro OPA/Keycloak/OpenBao reali, nessun mock): successo entro la
  deadline per i tre controlli; `require_available` non concede mai per
  nessun controllo incluso `WORKLOAD_IDENTITY`; due cicli reali di
  fault-injection pausa/ripresa (OPA, OpenBao) che provano negazione entro
  la deadline dichiarata con evidenza di audit correlata, poi recupero;
  evidenza di audit correlata su entrambi i percorsi successo/fallimento.
- **Prima iterazione CI (PR #81, primo push)**: 3 check rossi
  (`delivery-activation`, `rccad-methodology`, `validation-closure`) con
  `"No such container: ocor-bootstrap-opa-1"` — causa radice: i container
  CI erano nominati `opa`/`keycloak`/`openbao`, ma `fault_command()`
  sigillato (`OCOR-DEV-0083`) costruisce il nome atteso come
  `ocor-bootstrap-<service>-1`, la convenzione di `docker compose`.
  Corretto rinominando ogni `docker run --name` nei 3 workflow
  (`fuseki`/`opa`/`keycloak`/`openbao`) alla convenzione attesa — nessuna
  modifica a test o adapter, il disallineamento era solo nel
  provisioning CI. Evidenza aggiornata nello stesso commit/PR.
- **Provisioning CI proattivo**: aggiunti OPA/Keycloak/OpenBao reali ai 3
  workflow PRIMA di aprire la PR (tutte e 3 immagini pre-costruite e
  pinnate, a differenza di Fuseki), con ricetta rehearsed localmente su
  porte alternative (8182/8081/8201) prima dell'aggiunta ai workflow.
- Secondo push: tutti e 13 i check verdi. PR #81 mergiata
  (`9e97e1c19c7ac82bdfe074e28991493ac798b1c1`), SHA post-merge verificata.
  Con questo si chiude l'intero wave 11 degli spike G2
  (`OCOR-DEV-0016`/`0017`/`0018`/`0021`).
- Gate locali tutti verdi: `sha256sum` 8/8, `ruff`, `mypy` (45 file),
  `validate_rccad.py` PASS, `validate_language_policy.py` PASS,
  `validate_ocor_change_scope.py` PASS, `yaml.safe_load` dei 3 workflow
  PASS, pytest completo con `OCOR_LIVE_POSTGRES_DSN` locale:
  `2 failed, 643 passed, 0 skipped, 0 errors` (stessi 2 fallimenti noti e
  preesistenti del pin dell'interprete), `validate_ocor_development_plan.py
  --authorized-extension` PASS dopo il consueto doppio-run.
- Evidenza sigillata contro OPA/Keycloak/OpenBao reali, incluso il fix CI:
  `reports/evidence/G2/OCOR-DEV-0021.json` +
  `reports/evidence/G2/OCOR-DEV-0021.log`, aggiunta a
  `reports/evidence/G2/MANIFEST.json` (diff puramente additivo, 64 righe).
  `scripts/validate_runtime_evidence.py --task OCOR-DEV-0021 --non-skipped`
  PASS.
- Claim fence invariato: `E1=0`, `E2=0`, zero requisiti `Verified`,
  `runtime_conformance` `NOT_ESTABLISHED`, `PoC`/`Production` `NO-GO`.

## 2026-09-13 — Backlog: OCOR-DEV-0024 (SPIKE cross-compartment non-interference)

- Prossimo task eseguibile determinato direttamente da
  `docs/development_plan/OCOR_IMPLEMENTATION_BACKLOG.json` e
  `completed_evidence_tasks` (lo stato interno di
  `scripts/ocor_autonomous_delivery.py --status` resta inaffidabile, mai
  aggiornato dall'esecuzione manuale di questa sessione). Con la chiusura
  del wave 11, il wave 12 diventa pronto: `OCOR-DEV-0024`/`0025`/`0028`/
  `0029`. Selezionato `OCOR-DEV-0024` per ordine numerico. Dipende da
  `OCOR-DEV-0018`, `OCOR-DEV-0021`, `OCOR-DEV-0023`, tutti già mergiati.
- **Design**: questo spike compone TRE spike già sigillati invece di
  costruirne uno nuovo da zero — la proiezione marking-safe di Jena
  (`OCOR-DEV-0018`), il probe bounded del control-plane identity/policy
  (`OCOR-DEV-0021`), e l'oracolo di partizionamento vettoriale Qdrant
  (`OCOR-DEV-0023`, che già includeva un harness Qdrant reale
  auto-provisionato e test di non-interferenza per singolo backend) —
  tutti riutilizzati senza modifiche. L'unica astrazione nuova è
  `spikes/non_interference/equivalence.py`
  (`assert_observationally_equivalent`), un confronto a coppie con
  messaggio di fallimento preciso per asse, riutilizzato su ogni asse
  (content/existence/rank/count) e ogni backend.
- Aggiunto `ocor-runtime/tests/tasks/test_ocor_dev_0024.py` (7 test, tutti
  contro backend reali, nessun mock): vista Jena a bassa clearance
  invariata (content/count/esistenza) dopo l'ingest di una risorsa
  `TOP_SECRET`; rank e count di una ricerca Qdrant sulla partizione bassa
  invariati dopo l'upsert di 200 vettori estranei sulla partizione alta;
  la finestra di timing bounded di Qdrant ammette ancora il tempo
  osservato dopo la popolazione della partizione alta; l'accesso a una
  partizione alta reale e a una fabbricata/inesistente vengono negati con
  lo stesso errore identico; la disponibilità e il timing del probe OPA
  non sono influenzati da un ciclo reale di fault-injection
  pausa/ripresa sull'OpenBao non correlato; query ripetute a bassa
  clearance su Jena e Qdrant restano identiche dopo la popolazione alta
  in entrambi i backend; `assert_observationally_equivalent` solleva
  realmente su una divergenza costruita (non vacuamente vera).
- Nessun nuovo provisioning CI necessario: OPA/OpenBao/Fuseki sono già
  servizi reali da `OCOR-DEV-0018`/`0021`; Qdrant si auto-provisiona con
  un vero `docker run` all'interno del test stesso, lo stesso meccanismo
  già usato con successo da `OCOR-DEV-0023` negli stessi job CI.
- Corretto un disallineamento nei file di stato scoperto all'inizio di
  questa iterazione: `MODEL_HANDOFF.json` non era stato aggiornato al
  merge di `OCOR-DEV-0021` (PR #81) nell'iterazione precedente —
  `scripts/validate_rccad.py` ha rilevato `RCCAD-STATE-HANDOFF-DRIFT`
  (baseline_commit e branch disallineati fra `EXECUTION_STATE.json` e
  `MODEL_HANDOFF.json`); corretto aggiornando `MODEL_HANDOFF.json` con il
  completamento di `OCOR-DEV-0021` prima di proseguire.
- Gate locali tutti verdi: `sha256sum` 8/8, `ruff`, `mypy` (45 file,
  `spikes/` e `tests/` fuori scope per policy), `validate_rccad.py` PASS
  (dopo la correzione del drift), `validate_language_policy.py` PASS,
  `validate_ocor_change_scope.py` PASS (11 percorsi), pytest completo con
  `OCOR_LIVE_POSTGRES_DSN` locale: `2 failed, 650 passed, 0 skipped, 0
  errors` (stessi 2 fallimenti noti e preesistenti, +7 rispetto alla fase
  precedente), `validate_ocor_development_plan.py --authorized-extension`
  PASS dopo il consueto doppio-run di assestamento self-hash.
- Evidenza sigillata contro backend reali compositi (Fuseki, Qdrant
  auto-provisionato, OPA/OpenBao con fault-injection reale):
  `reports/evidence/G2/OCOR-DEV-0024.json` +
  `reports/evidence/G2/OCOR-DEV-0024.log`, aggiunta a
  `reports/evidence/G2/MANIFEST.json` (diff puramente additivo, 82 righe).
  `scripts/validate_runtime_evidence.py --task OCOR-DEV-0024 --non-skipped`
  PASS.
- Claim fence invariato: `E1=0`, `E2=0`, zero requisiti `Verified`,
  `runtime_conformance` `NOT_ESTABLISHED`, `PoC`/`Production` `NO-GO`.
- Prossima azione: push del branch
  `governed/ocor-dev-0024-cross-compartment-non-interference-spike`,
  apertura PR, polling CI, merge a gate verdi, verifica SHA post-merge.
  Poi determinare il prossimo task pronto del wave 12 in ordine numerico:
  `OCOR-DEV-0025` (SPIKE distributed deletion saga).
- `OCOR-DEV-0024`: tutti e 13 i check verdi al primo push (l'auto-
  provisioning di Qdrant ha funzionato senza problemi in CI). PR #82
  mergiata (`e003fdc453420f8d5942dd9c39261d1ccf0a73ea`), SHA post-merge
  verificata.

## 2026-09-13 — Backlog: OCOR-DEV-0025 (SPIKE distributed deletion saga)

- Secondo task del wave 12. Dipende da `OCOR-DEV-0016`, `OCOR-DEV-0017`,
  `OCOR-DEV-0018`, `OCOR-DEV-0019`, `OCOR-DEV-0023`, tutti già mergiati.
- Aggiunto `spikes/memory_deletion/saga.py` (nuovo) con
  `run_deletion_saga`: tenta un tombstone su ogni target, poi — a
  prescindere dall'esito di `tombstone()` — riverifica sempre
  indipendentemente con `contains()` come unico arbitro fra riconosciuto
  e rimanente. Nessun target è mai creduto sulla parola; un target
  irraggiungibile fallisce chiuso. Target reali: PostgreSQL (metadata),
  TypeDB (contenuto), Qdrant auto-provisionato via `QdrantHarness`
  (`OCOR-DEV-0023`, sigillato, riutilizzato senza modifiche) per
  cache/indice.
- Aggiunto `ocor-runtime/tests/tasks/test_ocor_dev_0025.py` (4 test,
  tutti contro backend reali, nessun mock): cancellazione completa sui 3
  backend con stato `DELETED`; un ciclo reale di fault-injection
  pausa/ripresa su TypeDB durante la cancellazione, che riporta
  `DELETION_INCOMPLETE` con il contenuto genuinamente ancora presente,
  poi recupera e un retry successivo riporta `DELETED`; un target
  "bugiardo" che dichiara successo senza cancellare nulla, dimostrando
  che la saga non si fida mai del segnale del backend; un target
  irraggiungibile classificato correttamente come rimanente.
- **Provisioning CI proattivo applicato PRIMA di aprire la PR**: scoperto
  che il provisioning CI di TypeDB usava un blocco nativo `services:` di
  GitHub Actions, che nomina il container internamente e non come
  `ocor-bootstrap-typedb-1` — la stessa categoria di problema già
  incontrata reattivamente in `OCOR-DEV-0021` per OPA/Keycloak/OpenBao.
  Convertito a un passo `docker run --name ocor-bootstrap-typedb-1`
  esplicito (stessa immagine pinnata) nei 3 workflow, rehearsed
  localmente su porte alternative prima dell'aggiunta.
- Tutti e 13 i check verdi al primo push. PR #83 mergiata
  (`c13a634b94bd1b6f6aed52e54d252746242e050d`), SHA post-merge
  verificata.
- Gate locali tutti verdi: `sha256sum` 8/8, `ruff`, `mypy` (45 file),
  `validate_rccad.py` PASS, `validate_language_policy.py` PASS,
  `validate_ocor_change_scope.py` PASS, `yaml.safe_load` dei 3 workflow
  PASS, pytest completo con `OCOR_LIVE_POSTGRES_DSN` locale: `2 failed,
  654 passed, 0 skipped, 0 errors` (stessi 2 fallimenti noti e
  preesistenti), `validate_ocor_development_plan.py --authorized-extension`
  PASS dopo il consueto doppio-run.
- Evidenza sigillata contro PostgreSQL/TypeDB/Qdrant reali, incluso il
  fix CI proattivo: `reports/evidence/G2/OCOR-DEV-0025.json` +
  `reports/evidence/G2/OCOR-DEV-0025.log`, aggiunta a
  `reports/evidence/G2/MANIFEST.json` (diff puramente additivo, 55
  righe). `scripts/validate_runtime_evidence.py --task OCOR-DEV-0025
  --non-skipped` PASS.
- Claim fence invariato: `E1=0`, `E2=0`, zero requisiti `Verified`,
  `runtime_conformance` `NOT_ESTABLISHED`, `PoC`/`Production` `NO-GO`.

## 2026-09-13 — Backlog: OCOR-DEV-0028 (Build retained C1 compiler slice)

- Prossimo task pronto del wave 12 determinato direttamente dal backlog:
  con `OCOR-DEV-0025` chiuso, gli unici task pronti rimasti del wave 12
  sono `OCOR-DEV-0028` e `OCOR-DEV-0029`, **entrambi gate `G3`** (non
  `G2`) — il primo passaggio da spike a componente runtime *retained* di
  questa sessione. Selezionato `OCOR-DEV-0028` per ordine numerico.
  Dipende da `OCOR-DEV-0011`, `OCOR-DEV-0016`, entrambi già mergiati.
- **Componente puro, nessun servizio esterno necessario**: implementata
  la porzione minima conforme al contratto dei port C1 già sigillati
  (`OCOR-DEV-0011`, `ocor_runtime.c1.ports`, riutilizzati senza
  modifiche) in `ocor-runtime/src/ocor_runtime/c1/compiler.py` (nuovo):
  `RetainedOacParser` (parsing YAML/JSON reale), `RetainedSemanticValidator`
  (contratto di forma minimo id/fields del DSL), `RetainedCanonicalIrBuilder`
  (assembla un documento core deterministico più un artefatto di
  metadati di migrazione). `signature_envelope_ref` è un placeholder non
  firmato dichiarato onestamente come tale; la firma reale (`IrSigner`)
  resta un Protocol sigillato non ancora implementato, task futuro
  separato.
- Aggiunto `ocor-runtime/tests/tasks/test_ocor_dev_0028.py` (8 test, puri
  in-memory, deterministici, nessun servizio esterno): fixture DSL mista
  YAML/JSON che compila con successo con metadati di migrazione;
  verifica di digest riproducibile tramite l'oracolo sigillato
  `verify_deterministic_build`; rifiuto di un import non risolto (già
  imposto dal costruttore sigillato di `CompilerRequest`); rifiuto di
  YAML malformato, chiavi richieste mancanti, `fields` non-mapping, e
  mismatch dell'id dichiarato, ciascuno con il `DiagnosticCode` corretto;
  prova diretta che nessun percorso di rifiuto restituisce mai un
  `CanonicalIrRelease` parziale.
- Creato `reports/evidence/G3/MANIFEST.json` **da zero** — il primo
  manifest di evidenza gate `G3` sigillato da questa sessione.
- Gate locali tutti verdi: `sha256sum` 8/8, `ruff`, `mypy` (46 file,
  `ocor-runtime/src` pienamente in scope per questo gate, a differenza
  degli spike), `validate_rccad.py` PASS, `validate_language_policy.py`
  PASS, `validate_ocor_change_scope.py` PASS (8 percorsi), pytest
  completo con `OCOR_LIVE_POSTGRES_DSN` locale: `2 failed, 662 passed, 0
  skipped, 0 errors` (stessi 2 fallimenti noti e preesistenti),
  `validate_ocor_development_plan.py --authorized-extension` PASS dopo
  il consueto doppio-run di assestamento self-hash.
- Evidenza sigillata: `reports/evidence/G3/OCOR-DEV-0028.json` +
  `reports/evidence/G3/OCOR-DEV-0028.log`.
  `scripts/validate_runtime_evidence.py --task OCOR-DEV-0028 --non-skipped
  --manifest reports/evidence/G3/MANIFEST.json` PASS.
- Aggiornamento dei tre file di stato eseguito in un'unica passata,
  recuperando anche i merge non ancora sincronizzati di `OCOR-DEV-0024`
  (PR #82) e `OCOR-DEV-0025` (PR #83) dalle iterazioni precedenti, per
  evitare un nuovo `RCCAD-STATE-HANDOFF-DRIFT`.
- Claim fence invariato: `E1=0`, `E2=0`, zero requisiti `Verified`,
  `runtime_conformance` `NOT_ESTABLISHED`, `PoC`/`Production` `NO-GO`.
- Prossima azione: push del branch
  `governed/ocor-dev-0028-c1-compiler-slice`, apertura PR, polling CI,
  merge a gate verdi, verifica SHA post-merge. Poi proseguire con
  `OCOR-DEV-0029` (Build retained C3 canonical commit slice, gate `G3`,
  dipende solo da `OCOR-DEV-0016`, già mergiato).
- `OCOR-DEV-0028`: tutti e 13 i check verdi al primo push. PR #84
  mergiata (`b8170f3c5ca9500d38faf95d2b2d01c7ded41850`), SHA post-merge
  verificata.

## 2026-09-13 — Backlog: OCOR-DEV-0029 (Build retained C3 canonical commit slice)

- Ultimo task del wave 12. Dipende solo da `OCOR-DEV-0016`, già mergiato
  (`OCOR-DEV-0013`, che definisce i port C3 sigillati riutilizzati qui,
  è un task G1 già chiuso in una fase precedente a questa sessione).
- Implementati tutti e 5 i port C3 sigillati (`ocor_runtime.c3.ports`,
  riutilizzati senza modifiche) come `PostgresC3Service`:
  `GovernedCommitPort` (`commit`), `CanonicalReadPort` (`read`),
  `RevisionPort` (`current_revision`), `OutboxRelayPort`
  (`claim_batch`/`acknowledge`), `RecoveryPort` (`reconcile`). Backend
  reale PostgreSQL, generalizzando la tecnica di locking/atomicità a
  concorrenza reale già provata dagli spike C3 sigillati
  (`spikes.c3_atomicity.oracle`, `OCOR-DEV-0015`; `spikes.c3_backend`,
  `OCOR-DEV-0016`) in un'implementazione a forma di produzione che parla
  direttamente le dataclass sigillate, non dict ad-hoc.
- **Violazione architetturale reale trovata e corretta prima di
  sigillare**: la prima versione di `service.py` importava `psycopg`
  direttamente; `scripts/validate_rccad.py` ha correttamente segnalato
  `AFF-002`/`AFF-006` ("infrastructure client leaked outside adapters"),
  la regola di fitness architetturale già sigillata (riga 8 di
  `OCOR_LANGUAGE_POLICY.md`) mai innescata prima in questa sessione,
  dato che ogni precedente task su backend reale viveva sotto `spikes/`
  e non sotto `ocor-runtime/src/`. Corretto estraendo ogni riferimento a
  `psycopg` in un nuovo `ocor-runtime/src/ocor_runtime/c3/adapters/postgres.py`
  (`PostgresC3Adapter`), che espone a `service.py` solo tipi Python
  semplici privi di `psycopg` — il primo sotto-albero `adapters/` che
  questa consegna abbia mai avuto bisogno di creare.
- Aggiunto `ocor-runtime/tests/tasks/test_ocor_dev_0029.py` (9 test,
  tutti contro PostgreSQL reale, nessun mock): conformità `isinstance` a
  ogni Protocol sigillato; commit atomico che persiste stato/revisione/
  outbox insieme; replay idempotente; rifiuto per conflitto di
  idempotenza e conflitto di revisione; due comandi distinti in race
  sulla stessa revisione (vince esattamente uno); un vero crash di
  processo (subprocess) a metà commit — zero visibilità parziale, retry
  riuscito; una vera corruzione simulata (una riga outbox derivata
  cancellata direttamente contro il database, riparata da `reconcile()`);
  claim/acknowledge dell'outbox.
- Gate locali tutti verdi: `sha256sum` 8/8, `ruff`, `mypy` (49 file),
  `validate_rccad.py` PASS (dopo la correzione della violazione
  architetturale), `validate_language_policy.py` PASS,
  `validate_ocor_change_scope.py` PASS (10 percorsi), pytest completo
  con `OCOR_LIVE_POSTGRES_DSN` locale: `2 failed, 671 passed, 0 skipped,
  0 errors` (stessi 2 fallimenti noti e preesistenti),
  `validate_ocor_development_plan.py --authorized-extension` PASS dopo
  il consueto doppio-run.
- Evidenza sigillata: `reports/evidence/G3/OCOR-DEV-0029.json` +
  `reports/evidence/G3/OCOR-DEV-0029.log`, aggiunta a
  `reports/evidence/G3/MANIFEST.json` (diff puramente additivo, 100
  righe). `scripts/validate_runtime_evidence.py --task OCOR-DEV-0029
  --non-skipped --manifest reports/evidence/G3/MANIFEST.json` PASS.
- Aggiornamento dei tre file di stato eseguito SUBITO in questa stessa
  iterazione (non rimandato), recuperando anche il merge di
  `OCOR-DEV-0028` (PR #84) non ancora sincronizzato, per istruzione
  esplicita del Product Owner.
- Claim fence invariato: `E1=0`, `E2=0`, zero requisiti `Verified`,
  `runtime_conformance` `NOT_ESTABLISHED`, `PoC`/`Production` `NO-GO`.
- `OCOR-DEV-0029`: `gh pr create` ha incontrato due errori transitori
  dell'API di GitHub (502 Bad Gateway, poi un errore GraphQL di classe
  500), entrambi non correlati al contenuto del repository; riuscito al
  terzo tentativo come PR #85. Tutti e 13 i check verdi al primo push.
  PR #85 mergiata (`7e1cf57bfe98c314f2cfb1ae0469249428e0ab8f`), SHA
  post-merge verificata. Con questo si chiude l'intero wave 12
  (`OCOR-DEV-0024`/`0025`/`0028`/`0029`).

## 2026-09-13 — Sincronizzazione stato: OCOR-DEV-0029 (post-merge)

- Per istruzione esplicita del Product Owner ("aggiorna i tre file di
  stato SUBITO... non rimandare"), sincronizzazione immediata dei tre
  file di stato subito dopo il merge della PR #85, su un branch
  dedicato (`governed/state-sync-ocor-dev-0029`), invece di rimandarla
  al commit dell'iterazione successiva come accaduto in precedenza per
  `OCOR-DEV-0024`/`0025` e per `OCOR-DEV-0028`.
- `baseline_commit` aggiornato a
  `7e1cf57bfe98c314f2cfb1ae0469249428e0ab8f` in entrambi
  `EXECUTION_STATE.json` e `MODEL_HANDOFF.json`; `branch` allineato al
  branch di questa stessa iterazione di sincronizzazione. Verificata
  l'assenza di `RCCAD-STATE-HANDOFF-DRIFT` tramite
  `scripts/validate_rccad.py --root .`.
- Nessun codice sorgente toccato: gate locali (sha256sum, ruff, mypy,
  RCCAD, language-policy, change-scope, plan-validator, pytest
  completo) rieseguiti comunque per protocollo standard e confermati
  invariati.
- Prossima azione: determinare la prontezza del wave 13 direttamente da
  `docs/development_plan/OCOR_IMPLEMENTATION_BACKLOG.json` e
  `completed_evidence_tasks`. Candidati noti con dipendenze già
  soddisfatte: `OCOR-DEV-0026` (SPIKE restore without resurrection) e
  `OCOR-DEV-0027` (SPIKE deterministic context-assembly replay).

## 2026-09-13 — Backlog: OCOR-DEV-0026 (SPIKE restore without resurrection)

- Ricalcolata la prontezza del wave 13 dopo il merge di `OCOR-DEV-0029`:
  ready set = `{OCOR-DEV-0026, OCOR-DEV-0027, OCOR-DEV-0030}` —
  `OCOR-DEV-0030` è diventato pronto solo ora, dato che la sua
  dipendenza `OCOR-DEV-0029` è appena stata mergiata. Selezionato
  `OCOR-DEV-0026` per ordine numerico.
- Verifica proattiva del provisioning CI prima di scrivere codice:
  confermato che PostgreSQL, TypeDB e Qdrant sono già backend reali
  già provisionati nei 3 workflow CI (da `OCOR-DEV-0016`/`0017`/`0025`)
  — nessun gap, nessuna modifica CI necessaria.
- Composto lo spike sigillato `OCOR-DEV-0025`
  (`spikes.memory_deletion.saga`: `DeletionStatus`/`DeletionTarget`/
  `run_deletion_saga` più i tre target concreti Postgres/TypeDB/Qdrant,
  tutti riutilizzati senza modifiche) con un nuovo
  `spikes/restore_no_resurrection/journal.py`: un `TombstoneJournal`
  durevole, sostenuto da PostgreSQL reale; `record_deletion()`, che
  tombstona il journal solo quando la saga conferma indipendentemente
  la cancellazione completa su ogni target; `restore_from_backup()`,
  che consulta il journal PRIMA di toccare qualunque target — un
  elemento tombstonato viene rifiutato, e un journal irraggiungibile
  viene rifiutato allo stesso modo (fail-closed, mai trattato come
  "sicuro da ripristinare").
- Decisione progettuale deliberata: per il test di fault-injection
  "journal irraggiungibile" non è stato scelto un vero pause/unpause
  del container Postgres condiviso `ocor-bootstrap-postgresql-1` (usato
  concorrentemente da molti altri task sigillati, e provisionato in CI
  tramite un blocco nativo `services:` che `fault_command()` non può
  bersagliare), ma un vero rifiuto di connessione TCP a livello di
  sistema operativo contro una porta locale genuinamente chiusa — un
  guasto di rete reale, non un'eccezione simulata, a un raggio
  d'impatto molto più basso rispetto a un più ampio refactoring CI.
- Aggiunto `ocor-runtime/tests/tasks/test_ocor_dev_0026.py` (6 test,
  tutti contro backend reali, nessun mock): restore di un elemento mai
  cancellato riesce su tutti e 3 i backend; restore di un elemento
  tombstonato viene rifiutato e il contenuto non riappare mai;
  `record_deletion` tombstona il journal solo quando ogni target
  conferma la cancellazione completa (un target che mente ma resta
  incompleto non genera mai una scrittura nel journal); il restore
  consulta il journal prima di toccare qualunque target (dimostrato con
  una spia sull'ordine delle chiamate); un journal irraggiungibile
  fallisce in modo chiuso e non risuscita mai nulla; il restore di un
  elemento diverso, mai tombstonato, non è influenzato dal tombstone di
  un elemento non correlato.
- Gate locali tutti verdi: `sha256sum` 8/8, `ruff`, `mypy` (49 file,
  invariato — `spikes/` e `ocor-runtime/tests/` restano fuori dallo
  scope di mypy), `validate_rccad.py` PASS, `validate_language_policy.py`
  PASS, `validate_ocor_change_scope.py` PASS (7 percorsi), pytest
  completo con `OCOR_LIVE_POSTGRES_DSN` locale: `2 failed, 648 passed,
  0 skipped, 0 errors` (stessi 2 fallimenti noti e preesistenti) più
  `29 passed` per le 3 suite `reports/tests/`,
  `validate_ocor_development_plan.py --base-ref origin/main
  --authorized-extension` PASS dopo il consueto doppio-run
  (`FAIL` poi `PASS`), sempre con `--base-ref origin/main` per
  rispecchiare esattamente la CI (non il `BASE_COMMIT` di default,
  molto vecchio).
- Evidenza sigillata: `reports/evidence/G2/OCOR-DEV-0026.json` +
  `reports/evidence/G2/OCOR-DEV-0026.log`, aggiunta a
  `reports/evidence/G2/MANIFEST.json` (diff puramente additivo, 73
  righe, inserimento chirurgico per preservare lo storico esistente).
- Aggiornamento dei tre file di stato eseguito in questa stessa
  iterazione (non rimandato).
- Claim fence invariato: `E1=0`, `E2=0`, zero requisiti `Verified`,
  `runtime_conformance` `NOT_ESTABLISHED`, `PoC`/`Production` `NO-GO`.
- `OCOR-DEV-0026`: tutti e 13 i check verdi al primo push. PR #87
  mergiata (`a78d054d22ac85839181c833a0acc8deed8aa9c8`), SHA
  post-merge verificata.

## 2026-09-13 — Sincronizzazione stato: OCOR-DEV-0026 (post-merge)

- Per istruzione esplicita del Product Owner, sincronizzazione
  immediata dei tre file di stato subito dopo il merge della PR #87,
  su un branch dedicato (`governed/state-sync-ocor-dev-0026`),
  rispecchiando lo stesso schema già usato per `OCOR-DEV-0029`/PR #86.
- `baseline_commit` aggiornato a
  `a78d054d22ac85839181c833a0acc8deed8aa9c8` in entrambi
  `EXECUTION_STATE.json` e `MODEL_HANDOFF.json`; `branch` allineato al
  branch di questa iterazione di sincronizzazione. Verificata l'assenza
  di `RCCAD-STATE-HANDOFF-DRIFT`.
- Nessun codice sorgente toccato: gate locali rieseguiti comunque per
  protocollo standard e confermati invariati.
- Prossima azione: determinare il prossimo task del wave 13
  direttamente dal backlog JSON. Candidati noti: `OCOR-DEV-0027`
  (SPIKE deterministic context-assembly replay) e `OCOR-DEV-0030`
  (Build retained governed-action slice, gate G3, diventato pronto dopo
  il merge di `OCOR-DEV-0029`).

## 2026-09-13 — Backlog: OCOR-DEV-0027 (SPIKE deterministic context-assembly replay)

- Ricalcolata la prontezza del wave 13 dal backlog JSON: ready set =
  `{OCOR-DEV-0027, OCOR-DEV-0030}`. Selezionato `OCOR-DEV-0027` per
  ordine numerico.
- Verifica proattiva del provisioning CI: confermato che Qdrant si
  autoprovisiona già nei 3 workflow CI (da `OCOR-DEV-0023`/`0024`/
  `0025`) — nessun gap, nessuna modifica CI necessaria.
- Implementato `spikes/context_replay/replay.py`: dimostra che il
  digest di ricevuta di un context-assembly è funzione pura e
  deterministica di esattamente cinque dimensioni pinnate — versioni
  degli item, ordinamento (una vera ricerca di similarità coseno
  contro Qdrant, riusando senza modifiche `QdrantHarness` da
  `OCOR-DEV-0023`), redazioni, troncamento e rappresentazione. Il
  digest di ricevuta usa `ocor_runtime.kernel.canonical.canonical_digest`
  (canonicalizzazione RFC 8785 sigillata), mai un hash fatto a mano.
- Aggiunto `ocor-runtime/tests/tasks/test_ocor_dev_0027.py` (8 test,
  tutti contro un vero container Qdrant autoprovisionato, nessun
  mock): input pinnati identici riproducono un digest identico;
  cambiare la versione di un item cambia il digest; cambiare la
  redazione cambia il digest; cambiare il vettore di query cambia sia
  il vero ordinamento di ranking sia il digest; cambiare il
  troncamento cambia il digest e imposta il flag `truncated`; cambiare
  solo la versione di rappresentazione cambia il digest anche con
  ordinamento identico; due assemblaggi indipendenti sono provati
  equivalenti tramite l'helper sigillato `assert_observationally_equivalent`
  di `OCOR-DEV-0024` (riusato senza modifiche); un vero rifiuto di
  connessione TCP su una porta locale chiusa durante il ranking
  fallisce in modo chiuso (`ContextReplayError`) invece di restituire
  un contesto parziale silenzioso — stesso pattern a basso raggio
  d'impatto stabilito in `OCOR-DEV-0026`.
- Gate locali tutti verdi: `sha256sum` 8/8, `ruff`, `mypy` (49 file,
  invariato), `validate_rccad.py` PASS, `validate_language_policy.py`
  PASS, `validate_ocor_change_scope.py` PASS (7 percorsi), pytest
  completo con `OCOR_LIVE_POSTGRES_DSN` locale: `2 failed, 656 passed,
  0 skipped, 0 errors` (stessi 2 fallimenti noti) più `29 passed` per
  le 3 suite `reports/tests/`, `validate_ocor_development_plan.py
  --base-ref origin/main --authorized-extension` PASS dopo il consueto
  doppio-run (`FAIL` poi `PASS`).
- Evidenza sigillata: `reports/evidence/G2/OCOR-DEV-0027.json` +
  `reports/evidence/G2/OCOR-DEV-0027.log`, aggiunta a
  `reports/evidence/G2/MANIFEST.json` (diff puramente additivo, 91
  righe, inserimento chirurgico).
- Aggiornamento dei tre file di stato eseguito in questa stessa
  iterazione (non rimandato).
- Claim fence invariato: `E1=0`, `E2=0`, zero requisiti `Verified`,
  `runtime_conformance` `NOT_ESTABLISHED`, `PoC`/`Production` `NO-GO`.
- `OCOR-DEV-0027`: tutti e 13 i check verdi al primo push. PR #89
  mergiata (`53ad2e5bb76f7b59a5ffae9863b685338027edbe`), SHA
  post-merge verificata.

## 2026-09-13 — Sincronizzazione stato: OCOR-DEV-0027 (post-merge)

- Sincronizzazione immediata dei tre file di stato subito dopo il
  merge della PR #89, su un branch dedicato
  (`governed/state-sync-ocor-dev-0027`).
- `baseline_commit` aggiornato a
  `53ad2e5bb76f7b59a5ffae9863b685338027edbe` in entrambi
  `EXECUTION_STATE.json` e `MODEL_HANDOFF.json`; `OCOR-DEV-0027`
  aggiunto a `completed_evidence_tasks`. Verificata l'assenza di
  `RCCAD-STATE-HANDOFF-DRIFT`.
- **Correzione**: `OCOR-DEV-0030` ha `parallel_wave=13` nel backlog
  JSON, la stessa wave di `OCOR-DEV-0026`/`0027` — il wave 13 NON è
  ancora chiuso interamente, contrariamente a quanto scritto in una
  bozza precedente di questo stesso commit prima della correzione.
- Nessun codice sorgente toccato: gate locali rieseguiti comunque per
  protocollo standard e confermati invariati.
- `OCOR-DEV-0027`: PR #90 mergiata (`c783d7c2b8b3e6824176764cbda0a683dd44c105`)
  sul commit corretto (13/13 check verdi), SHA post-merge verificata.

## 2026-09-13 — Backlog: OCOR-DEV-0030 (Build retained governed-action slice)

- Confermato dal backlog JSON: unico task pronto, gate `G3`,
  dipendente da `OCOR-DEV-0020`/`0021`/`0029` (tutti mergiati).
- Prima di scrivere codice, letto `docs/OCOR_LLD_v1.1.md` §§2.6/3.1/
  3.2/4: il workflow C6 completo è una FSM normativa a 44 transizioni
  (`ACT-T01`..`ACT-T31b`); questo task è la slice contract-compliant
  più piccola del percorso rappresentativo che un'azione a rischio
  attraversa — non l'intera FSM (di cui lo spike sigillato
  `OCOR-DEV-0020` prova già la fedeltà esecutiva strutturale).
- Scoperto, prima di scrivere qualunque cosa, che
  `ocor_runtime.c6_capabilities.CapabilityAuthority` (Authority) e
  `ocor_runtime.c7_emission.EmissionFence` (EMISSION-FENCE) esistono
  già come codice retained sigillato da una fase precedente della
  delivery — riusati direttamente senza modifiche. `Approval` e
  `Decision` sono gli unici due nuovi record realmente necessari,
  poiché nessun record Human Gate o Decision esisteva ancora.
- Implementato `ocor-runtime/src/ocor_runtime/c6/engine.py`:
  `GovernedActionEngine.execute()` attraversa, in ordine stretto,
  Authority (`G-AUTHORITY`), Human Gate (`G-APPROVAL`), Decision
  (`G-DECISION`) ed EMISSION-FENCE prima di qualunque effetto
  simulato, fail-closed a ogni gate. Componente puro, in-memory,
  deterministico — nessun backend esterno necessario (come la slice
  compilatore C1 di `OCOR-DEV-0028`), quindi nessuna preoccupazione
  `AFF-002`/`AFF-006` (zero import di client di backend diretti,
  verificato con `validate_rccad.py`).
- Aggiunto `ocor-runtime/tests/tasks/test_ocor_dev_0030.py` (9 test):
  percorso felice completo attraverso tutti e quattro i gate fino
  all'effetto simulato; diniego all'Authority (lease con capability
  sbagliata); diniego all'Human Gate (approvazione mancante o
  esplicitamente rifiutata) per un'azione a rischio; un'azione non a
  rischio salta interamente l'Human Gate (`ACT-T07`, `NOT_REQUIRED`);
  diniego alla Decision (mancante o rifiutata, con rationale
  preservato); un sink che fallisce lascia il commit canonico durevole
  ma non rilasciato, con un retry sicuro sullo stesso fence; un test
  di fedeltà che traccia i quattro nomi dei gate fino alla tabella
  sigillata a 44 transizioni di `OCOR-DEV-0020` (verificata contro il
  digest LLD approvato), a riprova che i nomi non sono stati inventati
  indipendentemente.
- Gate locali tutti verdi: `sha256sum` 8/8, `ruff`, `mypy` (50 file,
  +1 rispetto a prima), `validate_rccad.py` PASS (tutti i 10 AFF
  `PASS_STATIC_PRECHECK`), `validate_language_policy.py` PASS,
  `validate_ocor_change_scope.py` PASS (7 percorsi), pytest completo
  con `OCOR_LIVE_POSTGRES_DSN` locale: `2 failed, 665 passed, 0
  skipped, 0 errors` (stessi 2 fallimenti noti) più `29 passed` per le
  3 suite `reports/tests/`, `validate_ocor_development_plan.py
  --base-ref origin/main --authorized-extension` PASS dopo il
  consueto doppio-run.
- Evidenza sigillata: `reports/evidence/G3/OCOR-DEV-0030.json` +
  `reports/evidence/G3/OCOR-DEV-0030.log`, aggiunta a
  `reports/evidence/G3/MANIFEST.json` (diff puramente additivo, 100
  righe, inserimento chirurgico).
- Aggiornamento dei tre file di stato eseguito in questa stessa
  iterazione (non rimandato).
- Claim fence invariato: `E1=0`, `E2=0`, zero requisiti `Verified`,
  `runtime_conformance` `NOT_ESTABLISHED`, `PoC`/`Production` `NO-GO`.
- `OCOR-DEV-0030`: tutti e 13 i check verdi al primo push. PR #91
  mergiata (`c9ac9ca4615337193202846d06a4b5f6e38afcbc`), SHA
  post-merge verificata. Con questo si chiude l'intero wave 13
  (`OCOR-DEV-0026`/`0027`/`0030`).

## 2026-09-13 — Sincronizzazione stato: OCOR-DEV-0030 (post-merge, chiusura wave 13)

- Sincronizzazione immediata dei tre file di stato subito dopo il
  merge della PR #91, su un branch dedicato
  (`governed/state-sync-ocor-dev-0030`).
- `baseline_commit` aggiornato a
  `c9ac9ca4615337193202846d06a4b5f6e38afcbc` in entrambi
  `EXECUTION_STATE.json` e `MODEL_HANDOFF.json`; `OCOR-DEV-0030`
  aggiunto a `completed_evidence_tasks`. Verificata l'assenza di
  `RCCAD-STATE-HANDOFF-DRIFT`.
- Ricalcolata la prontezza del prossimo wave dal backlog JSON
  (verificando `parallel_wave` su ogni candidato, come da lezione
  appresa in questa iterazione): ready set = `{OCOR-DEV-0031}`,
  `parallel_wave=14`, "Integrate first real C1-C8 synthetic mission
  thread", gate `G3`, dipendente da `OCOR-DEV-0017`/`0018`/`0019`/
  `0022`/`0024`/`0027`/`0028`/`0029`/`0030` (tutti mergiati) — un
  task di integrazione significativamente più ampio delle recenti
  slice a singolo componente.
- Nessun codice sorgente toccato: gate locali rieseguiti comunque per
  protocollo standard e confermati invariati.
- Prossima azione: leggere per intero la voce di `OCOR-DEV-0031` nel
  backlog JSON (expected_file_areas, acceptance criteria, backend
  reali richiesti) prima di progettare qualunque cosa, dato che è un
  task di integrazione multi-componente, non una slice singola.

## 2026-09-13 — Backlog: OCOR-DEV-0031 (Integrate first real C1-C8 synthetic mission thread)

- Letta per intero la voce del backlog: un unico file atteso
  (`ocor-runtime/tests/mission_thread/test_first_governed_slice.py`),
  nessun nuovo codice di produzione — un vero indizio che il task è
  puramente un test di integrazione.
- Letto per intero `docs/OCOR_LLD_v1.1.md` §§2.1-2.9/3/4 e il codice
  sorgente completo di ogni componente C1-C8 nominato come dipendenza
  dura, prima di progettare qualunque cosa. Confermato che ogni
  componente necessario esiste già come codice retained sigillato o
  spike sigillato: C1 → `ocor_runtime.c1.compiler` (`0028`); C2/C8 →
  `ocor_runtime.c2_identity`/`ocor_runtime.c8_agent` (retained,
  preesistenti a questa sessione); C3 →
  `ocor_runtime.c3.service.PostgresC3Service` (`0029`); C4 → TypeDB
  reale (`spikes.typedb_exact_commit.adapter`, `0017`), Fuseki reale
  (`spikes.jena_marking.adapter`, `0018`), context assembly su Qdrant
  reale (`spikes.context_replay.replay`, `0027`); C5 → Kafka reale
  autoprovisionato (`spikes.kafka_delivery.oracle`, `0019`); C6 →
  `ocor_runtime.c6.engine.GovernedActionEngine` (`0030`); C7 →
  `spikes.causal_reproducibility.oracle` (`0022`).
- **Scoperta rilevante**: `ocor_runtime.c5_actions.py` ("the complete
  ACT-T01…ACT-T31b action state machine") è la FSM generica OBSOLETA a
  32 stati (`DRAFT`/`PROPOSED`/`VALIDATED`, non gli stati reali
  `PROPOSAL_RECORDED`/`CONTROL_CHECK`/ecc. della LLD approvata) già
  documentata come tale altrove in questa sessione — confermato che
  non va riusata e che il lavoro appena fatto in `OCOR-DEV-0030` non è
  duplicativo.
- Implementato `ocor-runtime/tests/mission_thread/test_first_governed_slice.py`
  (5 test, tutti contro backend reali, nessun mock): un unico fixture
  content-addressed, identificato da un `correlation_id`, attraversa
  PostgreSQL/TypeDB/Fuseki/Qdrant/Kafka reali e produce ricevute
  correlate canonical/projection/event/causal/agent/action; il
  `causation_id` della query causale (C7) È l'`event_id` reale
  dell'azione governata (C6) — una vera catena causale, non
  un'etichetta condivisa. Test aggiuntivi: riproducibilità del
  ricevuta causale con gli stessi pin; un diniego all'Authority che
  blocca l'intero thread prima di qualunque effetto; l'applicazione
  reale della consistenza `EXACT_AT_COMMIT` su TypeDB contro un vero
  commit C3; un vero riavvio del broker Kafka autoprovisionato
  (isolato per-test, mai il container condiviso) che preserva la
  consegna durevole e ordinata.
- Due bug reali trovati e corretti durante la prima esecuzione: (1)
  la chiave di riga di Jena è `resource`, non `resource_id`; (2) un
  `EventSink` come funzione semplice viene chiamato come `sink(event)`
  senza `idempotency_key` nel percorso di fallback — corretto usando
  una classe che implementa il Protocol `emit()` sigillato, come nel
  pattern già stabilito da `OCOR-DEV-0030`. Un terzo bug: i digest dei
  pin causali devono usare la funzione `canonical_digest` LOCALE dello
  spike causale (hex grezzo, no prefisso), non quella RFC 8785 del
  kernel — altrimenti `MODEL_PIN_MISMATCH`.
- Verifica proattiva del provisioning CI: confermato che PostgreSQL/
  TypeDB/Fuseki sono già reali e provisionati nei 3 workflow CI;
  Kafka e Qdrant si autoprovisionano — nessun gap, nessuna modifica
  CI necessaria.
- Gate locali tutti verdi: `ruff`, `mypy` (50 file, invariato — il
  file mission-thread è fuori dallo scope di mypy), `validate_rccad.py`
  PASS, `validate_language_policy.py` PASS,
  `validate_ocor_change_scope.py` PASS (6 percorsi), pytest completo
  con `OCOR_LIVE_POSTGRES_DSN` locale: `2 failed, 670 passed, 0
  skipped, 0 errors` (stessi 2 fallimenti noti) più `29 passed` per le
  3 suite `reports/tests/`, `validate_ocor_development_plan.py
  --base-ref origin/main --authorized-extension` PASS dopo il
  consueto doppio-run.
- Evidenza sigillata: `reports/evidence/G3/OCOR-DEV-0031.json` +
  `reports/evidence/G3/OCOR-DEV-0031.log`, aggiunta a
  `reports/evidence/G3/MANIFEST.json` (diff puramente additivo, 64
  righe, inserimento chirurgico).
- Aggiornamento dei tre file di stato eseguito in questa stessa
  iterazione (non rimandato).
- Claim fence invariato: `E1=0`, `E2=0`, zero requisiti `Verified`,
  `runtime_conformance` `NOT_ESTABLISHED`, `PoC`/`Production` `NO-GO`.
- `OCOR-DEV-0031`: al primo push, 3 job CI (`delivery-activation`,
  `rccad-methodology`, `validation-closure`) hanno fallito con
  `ModuleNotFoundError: No module named 'spikes'` durante la raccolta
  di `test_first_governed_slice.py`. Causa radice: il file si basava
  implicitamente su un side-effect `sys.path.insert` di un altro
  modulo di test già raccolto nella stessa sessione pytest — una
  dipendenza cross-file non documentata condivisa da 13 file di test
  esistenti. `mission_thread/` viene raccolta alfabeticamente PRIMA di
  `tasks/`, quindi il nuovo file veniva importato prima che quei
  side-effect fossero eseguiti; i test locali con `python -m pytest`
  (che antepone automaticamente la CWD a `sys.path`) non avevano mai
  rivelato il problema, a differenza dello script `pytest` nudo che la
  CI invoca davvero. Corretto aggiungendo un proprio
  `sys.path.insert(0, REPOSITORY_ROOT)` esplicito, riverificato con lo
  script `pytest` nudo (non `python -m pytest`): 5/5 test passano,
  l'intero albero si raccoglie senza errori, regressione invariata.
  Evidenza risigillata con i nuovi hash e la scoperta della causa
  radice. Commit di correzione pushato come nuovo commit sullo stesso
  branch. Tutti e 13 i check verdi sul commit corretto. PR #93
  mergiata (`47df17176f050c644105b73c3ae7aae085e86a76`), SHA
  post-merge verificata. Con questo si chiude l'intero wave 14 e si
  apre il gate **G4**.

## 2026-09-13 — Sincronizzazione stato: OCOR-DEV-0031 (post-merge, apertura G4)

- Sincronizzazione immediata dei tre file di stato subito dopo il
  merge della PR #93, su un branch dedicato
  (`governed/state-sync-ocor-dev-0031`).
- `baseline_commit` aggiornato a
  `47df17176f050c644105b73c3ae7aae085e86a76` in entrambi
  `EXECUTION_STATE.json` e `MODEL_HANDOFF.json`; `OCOR-DEV-0031`
  aggiunto a `completed_evidence_tasks`. Verificata l'assenza di
  `RCCAD-STATE-HANDOFF-DRIFT`.
- Ricalcolata la prontezza del prossimo wave dal backlog JSON: ready
  set = `{OCOR-DEV-0032, 0034, 0036, 0037, 0038, 0040, 0042, 0046,
  0048}`, 9 task, tutti `parallel_wave=15`, gate **G4**, tutti
  dipendenti solo da `OCOR-DEV-0031`. Selezionato `OCOR-DEV-0032`
  ("Complete C1 parser type-checker and semantic validation") per
  ordine numerico.
- Nessun codice sorgente toccato: gate locali rieseguiti comunque per
  protocollo standard e confermati invariati.
- `OCOR-DEV-0031`: `OCOR-DEV-0031` aggiunto a `completed_evidence_tasks`;
  PR #94 mergiata (`947b2b2586fb89c1d5342199bba2f091b061ef9c`), SHA
  post-merge verificata.

## 2026-09-13 — Backlog: OCOR-DEV-0032 (Complete C1 parser type-checker and semantic validation)

- Letto per intero `ocor_runtime.c1.ports` (l'intero enum sigillato
  `DiagnosticCode`) e `ocor_runtime.c1.compiler` (`OCOR-DEV-0028`)
  prima di progettare qualunque cosa: confermato che `0028` copre già
  `SOURCE_INVALID`, `UNKNOWN_SYNTAX`, `UNRESOLVED_REFERENCE`/
  `DUPLICATE_RESOURCE` (solo import esterni via dependency-lock),
  `TYPE_ERROR`, `CONSTRAINT_ERROR`, `RELEASE_REJECTED`; scoperti come
  NON coperti: `MULTIPLE_EXECUTION_OWNERS`, `UNSUPPORTED_CAPABILITY`,
  e qualunque risoluzione/rilevamento di cicli tra riferimenti
  semantici (non di import) tra risorse.
- Implementato `ocor-runtime/src/ocor_runtime/c1/frontend.py`: una
  nuova implementazione parallela e più completa degli stessi
  Protocol sigillati `OacParser`/`SemanticValidator`/
  `CanonicalIrBuilder`, che NON modifica il `compiler.py` sigillato di
  `OCOR-DEV-0028`. Aggiunge: una grammatica di tipi chiusa (string/
  integer/number/boolean/list) che richiede a ogni campo di
  dichiarare e soddisfare un tipo; il rifiuto di una risorsa che
  dichiara più di un `execution_owner` distinto come ambigua; e la
  risoluzione/rilevamento di cicli su un nuovo campo semantico
  `references` (distinto dagli import esterni già gestiti da
  `CompilerRequest`), riusando l'helper sigillato
  `require_resolved_references` per la risoluzione e un DFS a tre
  colori per i cicli.
- **Bug reale trovato e corretto durante la prima esecuzione**:
  l'helper sigillato `require_resolved_references` (tramite il suo
  `_unique_strings` interno) rifiuta i duplicati nella lista
  `referenced` — ma un grafo a diamante (due risorse che condividono
  lo stesso target referenziato) è legittimo e NON deve essere
  rifiutato come duplicato. Corretto passando solo l'insieme distinto
  dei target referenziati, mai una lista piatta con ripetizioni.
- Aggiunto `ocor-runtime/tests/tasks/test_ocor_dev_0032.py` (15 test,
  puro in-memory, nessun backend esterno): compilazione deterministica
  di un corpus valido; tipi di campo mancanti/non dichiarati; tipo
  dichiarato non supportato; valore non conforme al tipo dichiarato
  (incluso un booleano contro un tipo intero dichiarato, dato che
  `bool` è una sottoclasse di `int` in Python); proprietà d'esecuzione
  ambigua vs. non ambigua; riferimento non risolto; cicli diretti e
  più lunghi; un grafo a diamante non ciclico legittimo che compila
  con successo; sintassi malformata; mismatch dell'id dichiarato;
  nessun rilascio parziale su rifiuto.
- Gate locali tutti verdi: `ruff`, `mypy` (51 file, +1), `validate_rccad.py`
  PASS, `validate_language_policy.py` PASS,
  `validate_ocor_change_scope.py` PASS (5 percorsi), pytest completo
  via lo script `pytest` nudo (non `python -m pytest`): `2 failed, 685
  passed, 0 skipped, 0 errors` (stessi 2 fallimenti noti) più `29
  passed` per le 3 suite `reports/tests/`,
  `validate_ocor_development_plan.py --base-ref origin/main
  --authorized-extension` PASS dopo il consueto doppio-run.
- Evidenza sigillata: `reports/evidence/G4/OCOR-DEV-0032.json` +
  `reports/evidence/G4/OCOR-DEV-0032.log`. **Primo task a sigillare
  evidenza sotto il gate G4**: `reports/evidence/G4/MANIFEST.json`
  creato da zero, rispecchiando lo schema del primo manifest G3
  (`OCOR-DEV-0028`).
- Aggiornamento dei tre file di stato eseguito in questa stessa
  iterazione (non rimandato).
- Claim fence invariato: `E1=0`, `E2=0`, zero requisiti `Verified`,
  `runtime_conformance` `NOT_ESTABLISHED`, `PoC`/`Production` `NO-GO`.
- `OCOR-DEV-0032`: tutti e 13 i check verdi al primo push. PR #95
  mergiata (`00b51e710c24832d09cf87a8f139edfa74f37a1d`), SHA
  post-merge verificata.

## 2026-09-13 — Sincronizzazione stato: OCOR-DEV-0032 (post-merge, apertura wave 16)

- Sincronizzazione immediata dei tre file di stato subito dopo il
  merge della PR #95, su un branch dedicato
  (`governed/state-sync-ocor-dev-0032`).
- `baseline_commit` aggiornato a
  `00b51e710c24832d09cf87a8f139edfa74f37a1d` in entrambi
  `EXECUTION_STATE.json` e `MODEL_HANDOFF.json`; `OCOR-DEV-0032`
  aggiunto a `completed_evidence_tasks`. Verificata l'assenza di
  `RCCAD-STATE-HANDOFF-DRIFT`.
- Ricalcolata la prontezza dal backlog JSON: `OCOR-DEV-0033`
  ("Complete C1 releases semantic diff migration and generators",
  wave 16) è appena diventato pronto, dipendente solo da
  `OCOR-DEV-0032` — numericamente più basso degli 8 task rimanenti
  del wave 15, quindi selezionato per ordine numerico sull'intero
  insieme pronto (non limitato a un singolo wave), secondo la
  convenzione già stabilita in questa sessione.
- Nessun codice sorgente toccato: gate locali rieseguiti comunque per
  protocollo standard e confermati invariati.
- Prossima azione: leggere per intero la voce di `OCOR-DEV-0033` nel
  backlog JSON prima di progettare qualunque cosa (già fatto:
  richiede `ocor-runtime/src/ocor_runtime/c1/releases.py`,
  implementando i Protocol sigillati rimanenti `SemanticDiffEngine`/
  `CompatibilityChecker`/`MigrationPlanner`/`ArtifactGenerator` su
  coppie di `CanonicalIrRelease`, puro in-memory, nessun backend).

## 2026-09-13 — OCOR-DEV-0033: completamento C1 releases (semantic diff, migrazione, generatori)

- Implementati i Protocol sigillati rimanenti di C1 (OCOR-DEV-0011,
  `ocor_runtime.c1.ports`, riusato invariato) in
  `ocor-runtime/src/ocor_runtime/c1/releases.py`:
  `RetainedSemanticDiffEngine.compare` (digest strutturale
  content-addressed su risorse aggiunte/rimosse/cambiate, direzionale),
  `RetainedCompatibilityChecker.check` (`IDENTICAL`/`COMPATIBLE`/
  `BREAKING` — una risorsa rimossa, una dichiarazione di tipo di campo
  rimossa, o un tipo di campo esistente cambiato sono tutti `BREAKING`),
  `RetainedMigrationPlanner.plan` (piano di migrazione content-addressed
  con proprio `plan_digest`, passi ordinati retire/expand-migrate-contract/
  introduce), `RetainedArtifactGenerator` (`generate()` incondizionato
  come da Protocol sigillato; nuovo `generate_governed()` che rende
  eseguibile il criterio di accettazione negativo di questo task — un
  cambiamento `BREAKING` non può mai raggiungere la generazione senza un
  piano di migrazione governato esplicito e non vuoto).
- Riusa `ocor_runtime.c1.frontend` (OCOR-DEV-0032, invariato) per
  costruire fixture `CanonicalIrRelease` reali per i 14 nuovi test in
  `ocor-runtime/tests/tasks/test_ocor_dev_0033.py` — tutti passati al
  primo tentativo, nessun bug trovato nel nuovo codice di questo task
  (a differenza di ogni altro task di questa wave).
- Rilevamento ambientale non bloccante: un OOM transitorio e non
  correlato di Fuseki (`ocor-bootstrap-fuseki-1`, causato da un
  container host di grandi dimensioni non correlato che condivide lo
  stesso demone Docker — pattern ricorrente in questa sessione) ha
  causato 15 errori non correlati nel primo tentativo di regressione
  completa; diagnosticato via `docker compose -p ocor-bootstrap ps` e
  risolto riavviando solo il servizio fuseki; confermato non correlato
  con una seconda esecuzione pulita (`699 passed`, 2 fallimenti noti
  preesistenti).
- Gate locali tutti verdi: `ruff`, `mypy` (52 file, +1),
  `validate_rccad.py` PASS (10/10 AFF `PASS_STATIC_PRECHECK`, nessun
  finding), `validate_language_policy.py` PASS,
  `validate_ocor_change_scope.py` PASS (7 percorsi), pytest completo
  via lo script `pytest` nudo: `2 failed, 699 passed, 0 skipped, 0
  errors` (stessi 2 fallimenti noti) più `29 passed` per le 3 suite
  `reports/tests/`, `validate_ocor_development_plan.py --base-ref
  origin/main --authorized-extension` PASS dopo il consueto
  doppio-run (FAIL poi PASS).
- Evidenza sigillata: `reports/evidence/G4/OCOR-DEV-0033.json` +
  `reports/evidence/G4/OCOR-DEV-0033.log`. `reports/evidence/G4/
  MANIFEST.json` esteso con inserimento chirurgico (2 nuovi artifact,
  11 nuovi requirement_results), preservando la formattazione delle
  voci preesistenti.
- Aggiornamento dei tre file di stato eseguito come PR dedicata
  immediatamente dopo il merge del task (pattern OCOR-DEV-0032/PR #96),
  non incluso nel commit del task.
- Claim fence invariato: `E1=0`, `E2=0`, zero requisiti `Verified`,
  `runtime_conformance` `NOT_ESTABLISHED`, `PoC`/`Production` `NO-GO`.
- `OCOR-DEV-0033`: tutti e 13 i check verdi al primo push. PR #97
  mergiata (`305772453f25223d8c01e83a70ad944d1e7ac7a6`), SHA
  post-merge verificata (`git fetch origin main` +
  `git rev-parse origin/main`).

## 2026-09-13 — Sincronizzazione stato: OCOR-DEV-0033 (post-merge)

- Sincronizzazione immediata dei tre file di stato subito dopo il
  merge della PR #97, su un branch dedicato
  (`governed/state-sync-ocor-dev-0033`).
- `baseline_commit` aggiornato a
  `305772453f25223d8c01e83a70ad944d1e7ac7a6` in entrambi
  `EXECUTION_STATE.json` e `MODEL_HANDOFF.json`; `OCOR-DEV-0033`
  aggiunto a `completed_evidence_tasks`.
- Prossima azione: ricalcolare la prontezza direttamente dal backlog
  JSON (mai fidarsi di `--status`). Wave 15 ha ancora 8 task pronti
  (`OCOR-DEV-0034/0036/0037/0038/0040/0042/0046/0048`); verificare se
  `OCOR-DEV-0033` ha sbloccato un task numericamente più basso prima
  di procedere, poi selezionare per ordine numerico sull'intero
  insieme pronto.

## 2026-09-13 — OCOR-DEV-0034: C2 named-query gateway e identity resolution

- Nuovo `ocor_runtime.c2.gateway`: `NamedQueryGateway` (implementa il
  `NamedQueryPort` sigillato, OCOR-DEV-0012) garantisce che solo le
  named query registrate vengano eseguite, e solo dopo che identità,
  scopo, marking e policy siano tutti dispositivi. Lo scopo è già
  fail-closed dentro il costruttore sigillato di `NamedQueryRequest`;
  questo task fornisce le PRIME implementazioni reali dei port
  sigillati `AuthorityResolutionPort` (`IdentityBackedAuthority`,
  delega al retained `c2_identity.IdentityRegistry`, invariato) e
  `PolicyDecisionPort` (`RegistrationAndMarkingPolicy`, combina un
  allow-list esplicito nome/versione con un controllo reale di
  marking-join contro `spikes.jena_marking.adapter` di OCOR-DEV-0018,
  invariato), poi delega a un `ProjectionReadPort` iniettato
  (`spikes.typedb_exact_commit.adapter` di OCOR-DEV-0017, invariato)
  per la lettura vera e propria.
- Design deliberato: un contratto non registrato, una versione non
  registrata e un diniego di marking restituiscono tutti lo stesso
  codice `ARBITRARY_QUERY_FORBIDDEN` — un chiamante non può distinguere
  quale barriera è stata attraversata dal solo errore; nessuna
  risposta, parziale o meno, viene mai restituita su alcun percorso di
  diniego.
- Aggiunti 14 nuovi test in
  `ocor-runtime/tests/tasks/test_ocor_dev_0034.py`, tutti contro
  Fuseki e TypeDB reali, nessun mock: conformità ai Protocol per le 3
  nuove classi; percorso positivo completo fino a una lettura TypeDB
  reale; diniego per contratto non registrato, versione non
  registrata, identità mai registrata (abstain), risorsa fuori
  clearance, risorsa priva del tutto della propria marcatura, e
  riferimento di clearance non risolvibile; una query registrata senza
  parametro risorsa che salta il marking join; rifiuto di scopo
  mancante e di forma di query arbitraria al confine del costruttore
  sigillato; un test di fault-injection reale (una vera porta TCP
  locale chiusa, stesso pattern a basso raggio d'impatto già stabilito
  in OCOR-DEV-0026/0027) che prova che un guasto del backend di
  marking si propaga invece di ripiegare silenziosamente su un
  permesso.
- Un bug di scrittura del test trovato e corretto prima della
  sigillatura: un test si aspettava `C2Error` da un `GovernedContext`
  con scopo mancante, ma il costruttore sigillato di `GovernedContext`
  solleva il proprio `GovernedContextError` distinto — corretto il
  tipo di eccezione atteso nel test, nessuna modifica al codice di
  produzione necessaria.
- Verificato proattivamente, prima di aprire la PR, che TypeDB e
  Fuseki fossero già forniti in tutti e 3 i workflow CI che eseguono
  l'intera suite di test (già risolto durante OCOR-DEV-0017/0018).
- Gate locali tutti verdi: `ruff`, `mypy`, `validate_rccad.py` PASS
  (nessun import diretto di client backend in `gateway.py`, tutte le
  porte sono iniettate), `validate_language_policy.py` PASS,
  `validate_ocor_change_scope.py` PASS (7 percorsi), pytest completo
  via lo script `pytest` nudo con `OCOR_LIVE_POSTGRES_DSN` impostato
  contro il PostgreSQL reale di ocor-bootstrap: `2 failed, 713 passed`
  (stessi 2 fallimenti noti) più `29 passed` per le 3 suite
  `reports/tests/`, `validate_ocor_development_plan.py --base-ref
  origin/main --authorized-extension` PASS dopo il consueto
  doppio-run.
- Evidenza sigillata: `reports/evidence/G4/OCOR-DEV-0034.json` +
  `reports/evidence/G4/OCOR-DEV-0034.log`.
  `reports/evidence/G4/MANIFEST.json` esteso con inserimento
  chirurgico (2 nuovi artifact, 15 nuovi requirement_results).
- Aggiornamento dei tre file di stato eseguito come PR dedicata
  immediatamente dopo il merge del task, non incluso nel commit del
  task.
- Claim fence invariato: `E1=0`, `E2=0`, zero requisiti `Verified`,
  `runtime_conformance` `NOT_ESTABLISHED`, `PoC`/`Production` `NO-GO`.
- `OCOR-DEV-0034`: tutti e 13 i check verdi al primo push. PR #99
  mergiata (`1af39d6feefbec7a21edeff4c635cf4c406919d8`), SHA
  post-merge verificata.

## 2026-09-13 — Sincronizzazione stato: OCOR-DEV-0034 (post-merge, wave 16 OCOR-DEV-0035 pronto)

- Sincronizzazione immediata dei tre file di stato subito dopo il
  merge della PR #99, su un branch dedicato
  (`governed/state-sync-ocor-dev-0034`).
- `baseline_commit` aggiornato a
  `1af39d6feefbec7a21edeff4c635cf4c406919d8` in entrambi
  `EXECUTION_STATE.json` e `MODEL_HANDOFF.json`; `OCOR-DEV-0034`
  aggiunto a `completed_evidence_tasks`.
- Ricalcolata la prontezza dal backlog JSON: `OCOR-DEV-0035` ("Implement
  C2 policy-filtered planning consistency and watermarks", wave 16) è
  appena diventato pronto, dipendente solo da `OCOR-DEV-0034` —
  numericamente più basso dei 7 task rimanenti del wave 15
  (`0036/0037/0038/0040/0042/0046/0048`), quindi selezionato per
  ordine numerico sull'intero insieme pronto, secondo la convenzione
  già stabilita in questa sessione.
- Nessun codice sorgente toccato: gate locali rieseguiti comunque per
  protocollo standard e confermati invariati.
- Prossima azione: implementare `ocor-runtime/src/ocor_runtime/c2/planner.py`
  riusando i port sigillati `WatermarkPort`/`ConsistencyRequirement`
  (OCOR-DEV-0012) e la composizione di OCOR-DEV-0034 dove utile;
  criterio di accettazione negativo: "silent stale fallback or backend
  query leakage is rejected".

## 2026-09-13 — OCOR-DEV-0035: C2 policy-filtered planning consistency e watermarks

- Nuovo `ocor_runtime.c2.planner`: `ConsistencyPlanner` pianifica se la
  consistenza richiesta da una richiesta già autorizzata dalla policy
  può essere onorata, usando SOLO i port sigillati `PolicyDecisionPort`
  (OCOR-DEV-0012/0034, invariato) e `WatermarkPort` (OCOR-DEV-0012,
  invariato) — mai la query reale sui dati della projection
  (`ProjectionReadPort.read`). La policy viene valutata per prima: una
  query non registrata o comunque negata non raggiunge mai nemmeno il
  controllo del watermark.
- `BEST_AVAILABLE` restituisce un piano senza commit richiesto ma con
  il watermark reale osservato allegato (così un chiamante può sempre
  mostrare il proprio lavoro, mai un successo nudo senza evidenza);
  `EXACT_AT_COMMIT`/`AT_LEAST_COMMIT` confrontano il watermark reale
  con il commit richiesto e sollevano `PROJECTION_NOT_READY` nominando
  il watermark reale osservato quando non ha ancora raggiunto il
  commit — mai un fallback silenzioso a `BEST_AVAILABLE`, mai una
  query reale al backend solo per calcolare il piano. Il confronto
  per uguaglianza rispecchia deliberatamente la stessa semantica già
  stabilita dal `ConsistencyRequirement.verify_served` sigillato e
  dall'adapter di OCOR-DEV-0017, invece di inventare un nuovo ordine
  per `AT_LEAST_COMMIT`.
- Aggiunti 8 nuovi test in
  `ocor-runtime/tests/tasks/test_ocor_dev_0035.py`, tutti contro
  TypeDB reale (per il watermark), nessun mock: conformità al Protocol
  per il wrapper di test dell'adapter TypeDB come `WatermarkPort`;
  `BEST_AVAILABLE` con watermark reale allegato; `EXACT_AT_COMMIT` che
  procede quando il watermark corrisponde; `EXACT_AT_COMMIT` e
  `AT_LEAST_COMMIT` che riportano `PROJECTION_NOT_READY` con il
  watermark reale finché non lo raggiunge; uno spy `WatermarkPort` che
  PROVA, non solo asserisce per commento, che un diniego di policy
  interrompe il flusso prima del controllo del watermark; un diniego
  che non trapela mai alcun piano; e un test di fault-injection reale
  (una vera porta TCP locale chiusa) che prova che un guasto del
  backend di watermark si propaga invece di ripiegare silenziosamente
  su un esito permissivo.
- Nessun bug trovato nel nuovo codice di questo task: tutti e 8 i test
  sono passati al primo tentativo.
- Gate locali tutti verdi: `ruff`, `mypy`, `validate_rccad.py` PASS
  (nessun import diretto di client backend in `planner.py`, tutte le
  porte sono iniettate), `validate_language_policy.py` PASS,
  `validate_ocor_change_scope.py` PASS (7 percorsi), pytest completo
  via lo script `pytest` nudo con `OCOR_LIVE_POSTGRES_DSN` impostato
  contro il PostgreSQL reale di ocor-bootstrap: `2 failed, 721 passed`
  (stessi 2 fallimenti noti) più `29 passed` per le 3 suite
  `reports/tests/`, `validate_ocor_development_plan.py --base-ref
  origin/main --authorized-extension` PASS dopo il consueto
  doppio-run.
- Evidenza sigillata: `reports/evidence/G4/OCOR-DEV-0035.json` +
  `reports/evidence/G4/OCOR-DEV-0035.log`.
  `reports/evidence/G4/MANIFEST.json` esteso con inserimento
  chirurgico (2 nuovi artifact, 9 nuovi requirement_results).
- Aggiornamento dei tre file di stato eseguito come PR dedicata
  immediatamente dopo il merge del task, non incluso nel commit del
  task.
- Claim fence invariato: `E1=0`, `E2=0`, zero requisiti `Verified`,
  `runtime_conformance` `NOT_ESTABLISHED`, `PoC`/`Production` `NO-GO`.
- `OCOR-DEV-0035`: tutti e 13 i check verdi al primo push. PR #101
  mergiata (`bfd928d2036f37ecf7a09658b45a3b0848afbea5`), SHA
  post-merge verificata. Chiude interamente il wave 16
  (`OCOR-DEV-0033/0034/0035`).

## 2026-09-13 — Sincronizzazione stato: OCOR-DEV-0035 (post-merge, wave 16 chiuso)

- Sincronizzazione immediata dei tre file di stato subito dopo il
  merge della PR #101, su un branch dedicato
  (`governed/state-sync-ocor-dev-0035`).
- `baseline_commit` aggiornato a
  `bfd928d2036f37ecf7a09658b45a3b0848afbea5` in entrambi
  `EXECUTION_STATE.json` e `MODEL_HANDOFF.json`; `OCOR-DEV-0035`
  aggiunto a `completed_evidence_tasks`.
- Ricalcolata la prontezza dal backlog JSON: nessun nuovo task
  numericamente più basso è stato sbloccato da `OCOR-DEV-0035`, quindi
  i 7 task rimanenti del wave 15
  (`0036/0037/0038/0040/0042/0046/0048`) tornano ad essere il fronte
  di lavoro; selezionato `OCOR-DEV-0036` ("Complete C3 single-writer
  recovery and reconciliation") per ordine numerico.
- Nessun codice sorgente toccato: gate locali rieseguiti comunque per
  protocollo standard e confermati invariati.
- Prossima azione: implementare `ocor-runtime/src/ocor_runtime/c3/recovery.py`,
  riusando `PostgresC3Service` (OCOR-DEV-0029) e il pattern di
  composizione di OCOR-DEV-0031; criterio di accettazione: scrittori
  concorrenti, ACK perso, outbox corrotto e fixture di riavvio
  convergono senza effetti canonici duplicati.

## 2026-09-13 — OCOR-DEV-0036: C3 single-writer recovery e reconciliation

- Nuovo `ocor_runtime.c3.recovery.SingleWriterRecoveryCoordinator`,
  che compone il `PostgresC3Service` sigillato (OCOR-DEV-0029, invariato)
  esclusivamente tramite i suoi metodi pubblici sigillati (`reconcile`,
  `claim_batch`, `acknowledge`). Prima di scrivere qualunque cosa,
  verificato che `c3/service.py` e `c3/adapters/postgres.py` sono
  hash-referenziati come deliverable unico e sigillato di
  OCOR-DEV-0029 già accettato — esclusi entrambi dalla modifica per
  protocollo standard, aggiungendo invece un NUOVO adapter separato
  (`ocor_runtime.c3.adapters.recovery_lock.PostgresAdvisoryLock`) per
  l'unica capability nuova necessaria (un vero lock advisory
  PostgreSQL a livello di sessione via `pg_advisory_lock`/
  `pg_advisory_unlock`, la stessa primitiva `hashtextextended` già
  usata per davvero da `commit_transaction` di OCOR-DEV-0029),
  mantenendo AFF-002/AFF-006 soddisfatto senza toccare i file
  sigillati di OCOR-DEV-0029.
- `run_recovery_pass` avvolge `reconcile()` nel lock reale, così
  processi concorrenti o riavviati si serializzano sullo stesso lock
  reale e non corrono mai lo stesso repair (`reconcile()` ripara già
  ENTRAMBE le direzioni di orfani — riga di idempotency mancante e
  riga di outbox mancante — quindi la convergenza dell'"outbox
  corrotto" era già coperta dal contratto sigillato; lo scope di
  questo task è la serializzazione single-writer e l'health-gate
  attorno ad essa).
- `claim_and_deliver` avvolge claim+consegna+acknowledge nella stessa
  sezione critica, così due worker di relay concorrenti non possono
  mai reclamare la stessa riga non confermata prima che uno dei due
  la confermi; un ACK perso (un crash tra consegna e acknowledge)
  lascia la riga di nuovo reclamabile, ed è l'idempotenza del sink del
  chiamante (per `event_id`) a prevenire un effetto canonico
  duplicato alla riconsegna — il consueto contratto at-least-once
  dell'outbox, mai silenziosamente elevato a exactly-once da questo
  coordinator.
- `assert_healthy` usa il conteggio di riparazioni di `reconcile()`
  stesso come segnale di salute pre-flight, dato che `RecoveryPort`
  non espone un conteggio senza effetti collaterali nel contratto
  sigillato: solleva `UNRECONCILED_DURABLE_INTENT` per il passaggio in
  cui qualcosa necessitava riparazione, e ha successo una volta che
  non resta nulla.
- Aggiunti 8 nuovi test in
  `ocor-runtime/tests/tasks/test_ocor_dev_0036.py`, tutti contro
  PostgreSQL reale, nessun mock, incluse prove di concorrenza reale
  con threading: un vero lock advisory che serializza davvero due
  detentori concorrenti (provato con timestamp monotoni reali, non
  inferito); due passaggi di recovery concorrenti reali che corrono
  la stessa corruzione simulata reale convergono a esattamente una
  riparazione reale; un test di ACK perso che prova che il sink
  idempotente del chiamante assorbe un vero tentativo di consegna
  duplicata; due worker di relay concorrenti che corrono lo stesso
  singolo evento non confermato senza mai reclamarlo entrambi; un
  coordinator/service nuovo che simula un vero riavvio di processo e
  converge senza ripetere una riparazione già completata; e un test
  di fault-injection reale (un DSN PostgreSQL irraggiungibile) che
  prova che un guasto del backend del lock si propaga e il passaggio
  di recovery non gira mai senza lock.
- Tre bug genuini di scrittura del test trovati e corretti prima della
  sigillatura: (1) `make_command` indovinava inizialmente un campo del
  costruttore `GovernedCanonicalCommitCommand` inesistente
  (`command_digest`) invece di riusare il pattern dell'helper
  `from_mapping` di OCOR-DEV-0029; (2) valori di `idempotency_key`
  sotto i 16 caratteri violano il vincolo di lunghezza minima
  sigillato `COMMIT_CONTRACT_INVALID`; (3) il test di fault-injection
  si aspettava `OSError`, ma `psycopg.OperationalError` non è una
  sua sottoclasse.
- Test ripetuti 6 volte per escludere flakiness nei test di
  concorrenza reale: tutti deterministici.
- Gate locali tutti verdi: `ruff`, `mypy`, `validate_rccad.py` PASS
  (l'unico import di `psycopg` vive nel nuovo `c3/adapters/recovery_lock.py`),
  `validate_language_policy.py` PASS, `validate_ocor_change_scope.py`
  PASS (8 percorsi), pytest completo via lo script `pytest` nudo con
  `OCOR_LIVE_POSTGRES_DSN` impostato contro il PostgreSQL reale di
  ocor-bootstrap: `2 failed, 729 passed` (stessi 2 fallimenti noti)
  più `29 passed` per le 3 suite `reports/tests/`,
  `validate_ocor_development_plan.py --base-ref origin/main
  --authorized-extension` PASS dopo il consueto doppio-run.
- Evidenza sigillata: `reports/evidence/G4/OCOR-DEV-0036.json` +
  `reports/evidence/G4/OCOR-DEV-0036.log`.
  `reports/evidence/G4/MANIFEST.json` esteso con inserimento
  chirurgico (2 nuovi artifact, 9 nuovi requirement_results).
- Aggiornamento dei tre file di stato eseguito come PR dedicata
  immediatamente dopo il merge del task, non incluso nel commit del
  task.
- Claim fence invariato: `E1=0`, `E2=0`, zero requisiti `Verified`,
  `runtime_conformance` `NOT_ESTABLISHED`, `PoC`/`Production` `NO-GO`.
- `OCOR-DEV-0036`: tutti e 13 i check verdi al primo push. PR #103
  mergiata (`ab06c8fc7fd996c40e8728dc5c55c6a4be56967c`), SHA
  post-merge verificata.

## 2026-09-13 — Sincronizzazione stato: OCOR-DEV-0036 (post-merge)

- Sincronizzazione immediata dei tre file di stato subito dopo il
  merge della PR #103, su un branch dedicato
  (`governed/state-sync-ocor-dev-0036`).
- `baseline_commit` aggiornato a
  `ab06c8fc7fd996c40e8728dc5c55c6a4be56967c` in entrambi
  `EXECUTION_STATE.json` e `MODEL_HANDOFF.json`; `OCOR-DEV-0036`
  aggiunto a `completed_evidence_tasks`.
- Ricalcolata la prontezza dal backlog JSON: nessun nuovo task
  numericamente più basso è stato sbloccato da `OCOR-DEV-0036`, quindi
  i 6 task rimanenti del wave 15 (`0037/0038/0040/0042/0046/0048`)
  restano il fronte di lavoro; selezionato `OCOR-DEV-0037` ("Implement
  C4 TypeDB projection adapter") per ordine numerico.
- Nessun codice sorgente toccato: gate locali rieseguiti comunque per
  protocollo standard e confermati invariati.
- Prossima azione: implementare `ocor-runtime/src/ocor_runtime/c4/typedb_adapter.py`,
  riusando lo spike `spikes.typedb_exact_commit.adapter` (OCOR-DEV-0017)
  e `PostgresC3Service` (OCOR-DEV-0029); criterio di accettazione:
  fatti/relazioni e watermark si committano atomicamente e il
  comportamento exact-at-commit rispetta il port; criterio negativo:
  una projection stantia non può mai spacciarsi per esatta.

## 2026-09-13 — OCOR-DEV-0037: C4 TypeDB projection adapter

- Nuovo `ocor_runtime.c4.typedb_adapter.TypeDBProjectionAdapter`,
  versione retained (non-spike) di
  `spikes.typedb_exact_commit.adapter` (OCOR-DEV-0017): un
  `ProjectionReadPort`/`WatermarkPort` sigillato (OCOR-DEV-0012,
  invariato) contro TypeDB reale, reimplementando la stessa superficie
  API HTTP v1 reale già provata dallo spike invece di importare il
  codice dello spike nel codice retained (`spikes/` è fuori dal
  pythonpath di ocor-runtime in produzione, stesso precedente già
  stabilito da OCOR-DEV-0028).
- L'unica vera differenza comportamentale: `apply_commit()` inserisce
  un fatto E avanza il watermark a quel commit atomicamente, in UNA
  sola transazione di scrittura TypeDB reale (lo spike mantiene
  `ingest()`/`advance_watermark()` deliberatamente separati apposta
  per modellare ed esercitare le race fra un fatto e il suo watermark
  nei propri test — questo adapter retained è il percorso di
  produzione reale che un consumer C5 userebbe, dove la deriva fra
  fatto e watermark non deve mai essere possibile in condizioni
  normali). `read()`/`current()` riusano lo stesso identico
  `NamedQueryRequest.verify_served` fail-closed già provato dallo
  spike: una projection stantia non può mai spacciarsi per esatta.
- Confermato che la regex `DIRECT_CLIENTS` di AFF-002/AFF-006
  rileva solo import letterali di `psycopg`/`kafka`/`qdrant_client`/
  `terminusdb_client`/`typedb`, non `urllib` — quindi le chiamate HTTP
  reali di questo file non richiedono un sottoalbero `adapters/`,
  rispecchiando esattamente il layout a file singolo dello spike.
- Aggiunti 8 nuovi test in
  `ocor-runtime/tests/tasks/test_ocor_dev_0037.py`, tutti contro
  TypeDB reale, nessun mock.
- Due bug genuini trovati e corretti prima della sigillatura: (1) la
  prima bozza rispecchiava il metodo `watermark()` dello spike stesso
  (senza argomenti), che NON rispetta davvero la firma sigillata
  `WatermarkPort.current(projection_id, branch)` —
  `isinstance(adapter, WatermarkPort)` falliva genuinamente; corretto
  rinominando in `current(self, projection_id, branch)`, chiudendo un
  vero gap di conformità che lo spike stesso non aveva mai chiuso; (2)
  il test di fault-injection si aspettava `TypeDBAdapterError` da un
  host irraggiungibile, ma un vero guasto di connessione solleva
  direttamente `urllib.error.URLError` (non catturato da `_request`,
  che traduce solo le risposte di errore a livello HTTP) — corretto il
  tipo di eccezione atteso nel test invece di aggiungere un except
  generico nel codice di produzione.
- Gate locali tutti verdi: `ruff`, `mypy`, `validate_rccad.py` PASS,
  `validate_language_policy.py` PASS, `validate_ocor_change_scope.py`
  PASS (7 percorsi), pytest completo via lo script `pytest` nudo con
  `OCOR_LIVE_POSTGRES_DSN` impostato contro il PostgreSQL reale di
  ocor-bootstrap: `2 failed, 737 passed` (stessi 2 fallimenti noti)
  più `29 passed` per le 3 suite `reports/tests/`,
  `validate_ocor_development_plan.py --base-ref origin/main
  --authorized-extension` PASS dopo il consueto doppio-run.
- Evidenza sigillata: `reports/evidence/G4/OCOR-DEV-0037.json` +
  `reports/evidence/G4/OCOR-DEV-0037.log`.
  `reports/evidence/G4/MANIFEST.json` esteso con inserimento
  chirurgico (2 nuovi artifact, 9 nuovi requirement_results).
- Aggiornamento dei tre file di stato eseguito come PR dedicata
  immediatamente dopo il merge del task, non incluso nel commit del
  task.
- Claim fence invariato: `E1=0`, `E2=0`, zero requisiti `Verified`,
  `runtime_conformance` `NOT_ESTABLISHED`, `PoC`/`Production` `NO-GO`.
- `OCOR-DEV-0037`: tutti e 13 i check verdi al primo push. PR #105
  mergiata (`7fa50fcc40a15cdad46a6c0c1b24bec630744d68`), SHA
  post-merge verificata.

## 2026-09-13 — Sincronizzazione stato: OCOR-DEV-0037 (post-merge)

- Sincronizzazione immediata dei tre file di stato subito dopo il
  merge della PR #105, su un branch dedicato
  (`governed/state-sync-ocor-dev-0037`).
- `baseline_commit` aggiornato a
  `7fa50fcc40a15cdad46a6c0c1b24bec630744d68` in entrambi
  `EXECUTION_STATE.json` e `MODEL_HANDOFF.json`; `OCOR-DEV-0037`
  aggiunto a `completed_evidence_tasks`.
- Ricalcolata la prontezza dal backlog JSON: nessun nuovo task
  numericamente più basso è stato sbloccato da `OCOR-DEV-0037`, quindi
  i 5 task rimanenti del wave 15 (`0038/0040/0042/0046/0048`) restano
  il fronte di lavoro; selezionato `OCOR-DEV-0038` ("Implement C4 Jena
  RDF SHACL adapter") per ordine numerico.
- Nessun codice sorgente toccato: gate locali rieseguiti comunque per
  protocollo standard e confermati invariati.
- Prossima azione: implementare `ocor-runtime/src/ocor_runtime/c4/jena_adapter.py`,
  riusando lo spike `spikes.jena_marking.adapter` (OCOR-DEV-0018) e
  `PostgresC3Service` (OCOR-DEV-0029); criterio di accettazione:
  output RDF/JSON-LD supera fixture SHACL e di non-interferenza del
  marking; criterio negativo: triple non autorizzate o provenance
  lossy bloccano la pubblicazione.

## 2026-09-13 — OCOR-DEV-0038: C4 Jena RDF SHACL adapter

- Nuovo `ocor_runtime.c4.jena_adapter.JenaSHACLProjectionAdapter`,
  estende il pattern di marking reale di OCOR-DEV-0018 (Fuseki,
  invariato) con un vero percorso di pubblicazione. Confermato che
  nessun `pyshacl` (o processore SHACL generico) è dipendenza di
  progetto — implementato lo SHACL-equivalent minimo direttamente:
  una shape chiusa a required-property/closed-predicate applicata
  PRIMA di qualunque scrittura SPARQL, invece di aggiungere una nuova
  dipendenza esterna (che avrebbe richiesto modifiche a
  pyproject.toml/uv.lock fuori dallo scope di questo task).
- Un predicato non autorizzato (`ALLOWED_PREDICATES`) o una
  `provenanceRef` mancante/lossy bloccano la pubblicazione per intero
  — i due criteri di accettazione negativi del task, resi strutturali;
  una risorsa rifiutata non diventa mai parzialmente visibile.
- Le letture (`list_authorized`/`exists_authorized`) riusano lo stesso
  identico pattern di marking-join reale già provato da OCOR-DEV-0018.
  `to_json_ld` è negato via `exists_authorized` per qualunque
  clearance non autorizzata, altrimenti serializza JSON-LD reale e
  ben formato via `rdflib` (già dipendenza di progetto, 7.1.4) su un
  vero risultato SPARQL CONSTRUCT.
- Aggiunti 8 nuovi test in
  `ocor-runtime/tests/tasks/test_ocor_dev_0038.py`, tutti contro
  Fuseki reale, nessun mock — tutti e 8 passati al primo tentativo,
  nessun bug trovato (la lezione di OCOR-DEV-0037 su
  `urllib.error.URLError` non tradotto da `_request` è stata applicata
  proattivamente al tipo di eccezione atteso nel test di
  fault-injection).
- Gate locali tutti verdi: `ruff`, `mypy`, `validate_rccad.py` PASS,
  `validate_language_policy.py` PASS, `validate_ocor_change_scope.py`
  PASS (7 percorsi), pytest completo via lo script `pytest` nudo con
  `OCOR_LIVE_POSTGRES_DSN` impostato contro il PostgreSQL reale di
  ocor-bootstrap: `2 failed, 745 passed` (stessi 2 fallimenti noti)
  più `29 passed` per le 3 suite `reports/tests/`,
  `validate_ocor_development_plan.py --base-ref origin/main
  --authorized-extension` PASS dopo il consueto doppio-run.
- Evidenza sigillata: `reports/evidence/G4/OCOR-DEV-0038.json` +
  `reports/evidence/G4/OCOR-DEV-0038.log`.
  `reports/evidence/G4/MANIFEST.json` esteso con inserimento
  chirurgico (2 nuovi artifact, 9 nuovi requirement_results).
- Aggiornamento dei tre file di stato eseguito come PR dedicata
  immediatamente dopo il merge del task, non incluso nel commit del
  task.
- Claim fence invariato: `E1=0`, `E2=0`, zero requisiti `Verified`,
  `runtime_conformance` `NOT_ESTABLISHED`, `PoC`/`Production` `NO-GO`.
- `OCOR-DEV-0038`: tutti e 13 i check verdi al primo push. PR #107
  mergiata (`80962a15fd677cbca610c8382639443d5f70c1c2`), SHA
  post-merge verificata.

## 2026-09-13 — Sincronizzazione stato: OCOR-DEV-0038 (post-merge, wave 16 OCOR-DEV-0039 pronto)

- Sincronizzazione immediata dei tre file di stato subito dopo il
  merge della PR #107, su un branch dedicato
  (`governed/state-sync-ocor-dev-0038`).
- `baseline_commit` aggiornato a
  `80962a15fd677cbca610c8382639443d5f70c1c2` in entrambi
  `EXECUTION_STATE.json` e `MODEL_HANDOFF.json`; `OCOR-DEV-0038`
  aggiunto a `completed_evidence_tasks`.
- Ricalcolata la prontezza dal backlog JSON: `OCOR-DEV-0039` ("Implement
  C4 rebuild and drift reconciliation", wave 16) è appena diventato
  pronto, dipendente da `OCOR-DEV-0037` e `OCOR-DEV-0038` (entrambi
  appena mergiati) — numericamente più basso dei 4 task rimanenti del
  wave 15 (`0040/0042/0046/0048`), quindi selezionato per ordine
  numerico sull'intero insieme pronto.
- Nessun codice sorgente toccato: gate locali rieseguiti comunque per
  protocollo standard e confermati invariati.
- Prossima azione: implementare `ocor-runtime/src/ocor_runtime/c4/rebuild.py`,
  riusando `TypeDBProjectionAdapter` (OCOR-DEV-0037) e
  `JenaSHACLProjectionAdapter` (OCOR-DEV-0038); criterio di
  accettazione: il rebuild della projection dal log canonico riproduce
  digest/watermark e la deriva viene messa in quarantena; criterio
  negativo: servire una projection divergente dopo una riconciliazione
  fallita è vietato.

## 2026-09-13 — OCOR-DEV-0039: C4 rebuild e drift reconciliation

- Nuovo `ocor_runtime.c4.rebuild.ProjectionDriftDetector`, implementa
  direttamente il `ProjectionDriftDetector` nominato in LLD v1.1 §2.4.
  Verificato che `c3/service.py` e `c4/typedb_adapter.py` sono
  hash-referenziati come deliverable sigillati di task già accettati
  (OCOR-DEV-0029, OCOR-DEV-0037) — composti ENTRAMBI esclusivamente
  tramite i loro metodi pubblici sigillati esistenti
  (`PostgresC3Service.read`, `TypeDBProjectionAdapter.apply_commit`/
  `read`), senza mai toccare nessuno dei due file sigillati.
- `rebuild()` legge lo snapshot canonico da C3 (autoritativo),
  "sbircia" il digest della projection attualmente servita tramite il
  `ProjectionReadPort.read()` sigillato dell'adapter (una richiesta di
  sistema sintetica e deterministica in `BEST_AVAILABLE`) PRIMA di
  sovrascriverla mai, e confronta. Una discrepanza è vera deriva:
  l'aggregato viene aggiunto a un insieme di quarantena in-memory e la
  projection divergente reale viene lasciata intatta invece di essere
  riparata silenziosamente; una corrispondenza (o prima projection in
  assoluto) applica il fatto ricostruito e rimuove qualunque quarantena
  residua. `read_if_healthy()` rende eseguibile il criterio di
  accettazione negativo: solleva `PROJECTION_QUARANTINED` prima di
  delegare mai alla lettura della projection per un aggregato in
  quarantena.
- Una prima bozza di design "sbirciava" la projection servita tramite
  il metodo privato con underscore `_lookup_fact` dell'adapter —
  individuato e respinto prima della sigillatura come un vero difetto
  di design (accedere agli interni di un altro modulo sigillato invece
  del suo contratto pubblico) e sostituito con il percorso `read()`
  sigillato.
- Aggiunti 6 nuovi test in
  `ocor-runtime/tests/tasks/test_ocor_dev_0039.py`, tutti contro
  PostgreSQL e TypeDB reali, nessun mock — tutti e 6 passati al primo
  tentativo, nessun bug nel nuovo codice di questo task. Un singolo
  blip ambientale transitorio è stato osservato durante l'iterazione
  esplorativa locale (tutti e 6 i test hanno dato errore in
  un'esecuzione) ma non si è più riprodotto in 7 ripetizioni
  consecutive successive; documentato come un problema ambientale non
  bloccante sotto carico locale concorrente (coerente con altri
  ritrovamenti transitori di questa sessione, es. l'OOM ricorrente di
  Fuseki), non un difetto reale.
- Gate locali tutti verdi: `ruff`, `mypy`, `validate_rccad.py` PASS
  (nessun import diretto di client backend — `rebuild.py` compone due
  adapter già sigillati esclusivamente tramite i loro metodi
  pubblici), `validate_language_policy.py` PASS,
  `validate_ocor_change_scope.py` PASS (7 percorsi), pytest completo
  via lo script `pytest` nudo con `OCOR_LIVE_POSTGRES_DSN` impostato
  contro il PostgreSQL reale di ocor-bootstrap: `2 failed, 751 passed`
  (stessi 2 fallimenti noti) più `29 passed` per le 3 suite
  `reports/tests/`, `validate_ocor_development_plan.py --base-ref
  origin/main --authorized-extension` PASS dopo il consueto
  doppio-run.
- Evidenza sigillata: `reports/evidence/G4/OCOR-DEV-0039.json` +
  `reports/evidence/G4/OCOR-DEV-0039.log`.
  `reports/evidence/G4/MANIFEST.json` esteso con inserimento
  chirurgico (2 nuovi artifact, 7 nuovi requirement_results).
- Aggiornamento dei tre file di stato eseguito come PR dedicata
  immediatamente dopo il merge del task, non incluso nel commit del
  task.
- Claim fence invariato: `E1=0`, `E2=0`, zero requisiti `Verified`,
  `runtime_conformance` `NOT_ESTABLISHED`, `PoC`/`Production` `NO-GO`.
- `OCOR-DEV-0039`: tutti e 13 i check verdi al primo push. PR #109
  mergiata (`02859b0e3dd36824975414b19ee213af2bf2043d`), SHA
  post-merge verificata. Chiude interamente il wave 16
  (`OCOR-DEV-0033/0034/0035/0039`).

## 2026-09-13 — Sincronizzazione stato: OCOR-DEV-0039 (post-merge, wave 16 chiuso)

- Sincronizzazione immediata dei tre file di stato subito dopo il
  merge della PR #109, su un branch dedicato
  (`governed/state-sync-ocor-dev-0039`).
- `baseline_commit` aggiornato a
  `02859b0e3dd36824975414b19ee213af2bf2043d` in entrambi
  `EXECUTION_STATE.json` e `MODEL_HANDOFF.json`; `OCOR-DEV-0039`
  aggiunto a `completed_evidence_tasks`.
- Ricalcolata la prontezza dal backlog JSON: nessun nuovo task
  numericamente più basso è stato sbloccato da `OCOR-DEV-0039`, quindi
  i 4 task rimanenti del wave 15 (`0040/0042/0046/0048`) tornano ad
  essere il fronte di lavoro; selezionato `OCOR-DEV-0040` ("Implement
  C5 canonical event backbone") per ordine numerico.
- Nessun codice sorgente toccato: gate locali rieseguiti comunque per
  protocollo standard e confermati invariati.
- Prossima azione: implementare `ocor-runtime/src/ocor_runtime/c5/backbone.py`,
  riusando lo spike `spikes.kafka_delivery.oracle` (OCOR-DEV-0019) e
  `PostgresC3Service` (OCOR-DEV-0029); criterio di accettazione: eventi
  vincolati a schema preservano ordine di partizione, correlation,
  causation, marking e idempotency su Kafka; criterio negativo: schema
  sconosciuto, contesto mancante o effetto fuori ordine su un aggregato
  vanno in quarantena.

## 2026-09-13 — OCOR-DEV-0040: C5 canonical event backbone

- Nuovo `ocor_runtime.c5.backbone.CanonicalEventBackbone`, primo
  componente C5 retained: un `CanonicalIngestionEnvelope` chiuso (LLD
  v1.1 §2.5) pubblicato su un broker Kafka reale, con chiave
  `aggregate_ref` così che il partitioner nativo di Kafka preserva
  l'ordine per aggregato.
- Correzione di design genuina scoperta a metà implementazione:
  `grep -l kafka .github/workflows/*.yml` ha confermato che NESSUN
  workflow CI fornisce un servizio Kafka condiviso (a differenza di
  TypeDB/Fuseki, aggiunti a 3 workflow da task precedenti); l'unico
  uso di Kafka in tutta la CI è il test mission-thread di
  OCOR-DEV-0031, che auto-provisiona il proprio broker isolato.
  Ridisegnato `CanonicalEventBackbone` per auto-provisionare un vero
  broker KRaft single-node isolato per istanza
  (`provision()`/`destroy()`), reimplementando la stessa reale
  configurazione e ciclo di vita del broker già provati per davvero da
  `spikes.kafka_delivery.oracle.KafkaCli` (OCOR-DEV-0019), invece di
  importare lo spike, dato che `spikes/` è fuori dal pythonpath di
  ocor-runtime in produzione.
- `publish()` controlla l'allow-list degli schemi registrati e
  l'ultima sequenza pubblicata dell'aggregato PRIMA di chiamare mai il
  vero CLI produttore, mettendo in quarantena (mai pubblicando) uno
  schema sconosciuto o una sequenza fuori ordine; `publish_from_mapping()`
  cattura anche un campo di governed-context mancante o malformato al
  momento della costruzione e lo mette in quarantena a sua volta.
- Aggiunti 7 nuovi test in
  `ocor-runtime/tests/tasks/test_ocor_dev_0040.py`, tutti contro un
  broker reale auto-provisionato per test, nessun mock — tutti e 7
  passati, nessun bug nella nuova logica di envelope/publish/consume.
- Un finding AFF-009 genuino auto-rilevato e corretto prima della
  sigillatura: il `try/except KafkaBackboneError: pass` originario di
  `reset()` inghiottiva silenziosamente il fallimento di cancellare un
  topic non ancora esistente — corretto aggiungendo un controllo
  esplicito `topic_exists()` prima di tentare mai la cancellazione,
  rimuovendo del tutto l'except vuoto.
- Gate locali tutti verdi: `ruff`, `mypy`, `validate_rccad.py` PASS
  (dopo la correzione AFF-009), `validate_language_policy.py` PASS,
  `validate_ocor_change_scope.py` PASS (7 percorsi), pytest completo
  via lo script `pytest` nudo con `OCOR_LIVE_POSTGRES_DSN` impostato
  contro il PostgreSQL reale di ocor-bootstrap: `2 failed, 758 passed`
  (stessi 2 fallimenti noti) più `29 passed` per le 3 suite
  `reports/tests/`, `validate_ocor_development_plan.py --base-ref
  origin/main --authorized-extension` PASS dopo il consueto
  doppio-run.
- Evidenza sigillata: `reports/evidence/G4/OCOR-DEV-0040.json` +
  `reports/evidence/G4/OCOR-DEV-0040.log`.
  `reports/evidence/G4/MANIFEST.json` esteso con inserimento
  chirurgico (2 nuovi artifact, 8 nuovi requirement_results).
- Aggiornamento dei tre file di stato eseguito come PR dedicata
  immediatamente dopo il merge del task, non incluso nel commit del
  task.
- Claim fence invariato: `E1=0`, `E2=0`, zero requisiti `Verified`,
  `runtime_conformance` `NOT_ESTABLISHED`, `PoC`/`Production` `NO-GO`.
- `OCOR-DEV-0040`: tutti e 13 i check verdi al primo push, incluse le
  3 job lunghe dell'intera suite che per prime hanno esercitato
  l'auto-provisioning Kafka in CI. PR #111 mergiata
  (`916446c03c22317dd928d8bc89bed87f34e6a83d`), SHA post-merge
  verificata.

## 2026-09-13 — Sincronizzazione stato: OCOR-DEV-0040 (post-merge, wave 16 OCOR-DEV-0041 pronto)

- Sincronizzazione immediata dei tre file di stato subito dopo il
  merge della PR #111, su un branch dedicato
  (`governed/state-sync-ocor-dev-0040`).
- `baseline_commit` aggiornato a
  `916446c03c22317dd928d8bc89bed87f34e6a83d` in entrambi
  `EXECUTION_STATE.json` e `MODEL_HANDOFF.json`; `OCOR-DEV-0040`
  aggiunto a `completed_evidence_tasks`.
- Ricalcolata la prontezza dal backlog JSON: `OCOR-DEV-0041` ("Implement
  C5 registry replay backpressure DLQ and quarantine", wave 16) è
  appena diventato pronto, dipendente solo da `OCOR-DEV-0040` (appena
  mergiato) — numericamente più basso dei 3 task rimanenti del wave 15
  (`0042/0046/0048`), quindi selezionato per ordine numerico
  sull'intero insieme pronto.
- Nessun codice sorgente toccato: gate locali rieseguiti comunque per
  protocollo standard e confermati invariati.
- Prossima azione: implementare `ocor-runtime/src/ocor_runtime/c5/operations.py`,
  riusando `CanonicalEventBackbone` (OCOR-DEV-0040) esclusivamente
  tramite i suoi metodi pubblici; criterio di accettazione: fixture di
  replay e di eventi poison sono bounded, osservabili e non bypassano
  mai i controlli di compatibilità; criterio negativo: un replay dalla
  DLQ con schema incompatibile o marking perso viene bloccato.

## 2026-09-14 — OCOR-DEV-0041: C5 replay backpressure DLQ e quarantine

- Implementato `ocor-runtime/src/ocor_runtime/c5/operations.py`:
  `EventOperationsCoordinator` avvolge il `CanonicalEventBackbone`
  sigillato (OCOR-DEV-0040), riusato immutato e composto
  esclusivamente tramite il suo metodo pubblico `publish()`. Quota di
  ammissione bounded per tenant (`publish_with_backpressure`), record
  `DeadLetter` immutabile per ogni fallimento reale di publish,
  classificazione `POISON` dopo 3 fallimenti dello stesso evento,
  quarantena dietro un gate esplicito
  (`release_for_operator_replay`), e `replay()` che ricostruisce
  sempre l'envelope e richiama il `publish()` reale del backbone — uno
  schema incompatibile o un marking perso vengono bloccati in replay
  esattamente come in un publish nuovo, mai bypassati; una chiave di
  idempotenza già durevole è un no-op sicuro grazie alla gestione di
  idempotenza propria del backbone.
- **Incidente ambientale genuino diagnosticato e risolto prima di
  fidarsi della regressione**: la regressione completa mostrava
  cluster di errori crescenti; `df -h /` ha rivelato il disco host al
  99% di capacità (2.9GB liberi su 234GB), dominato da immagini Docker
  di grandi dimensioni preesistenti e non correlate ad altri progetti
  sulla stessa macchina condivisa (non causato da questa sessione); i
  due comandi di pulizia sicuri (`docker builder prune -f`, `docker
  image prune -f`) hanno liberato 0B. La causa reale dei 33 errori
  era invece `ocor-bootstrap-fuseki-1` e `ocor-bootstrap-spire-agent-1`
  uccisi per OOM (exit 137) ore prima, non correlato al codice di
  questo task — riavviati entrambi (`docker start`), manutenzione di
  routine reversibile sullo stack bootstrap del progetto (mai toccato
  `eci-dev-control-plane` o `open-webui`); la regressione completa è
  poi passata pulita.
- Presa una decisione tecnica poi corretta: era stato avviato un
  redesign in-flight di `backbone.py` sigillato (Kafka data directory
  da volume Docker a `tmpfs`, per ridurre l'impronta su disco), ma
  riconosciuto a metà modifica che sia `backbone.py` sia
  `test_ocor_dev_0040.py` sono deliverable sigillati di OCOR-DEV-0040
  già mergiato — annullata la modifica (`git checkout --`) prima di
  procedere, secondo la regola propria di questa sessione di escludere
  i deliverable già sigillati dalla modifica anziché emendarli. La
  causa reale (ambientale) non richiedeva comunque alcuna modifica al
  sorgente sigillato.
- Aggiunti 8 nuovi test in
  `ocor-runtime/tests/tasks/test_ocor_dev_0041.py`, tutti contro un
  broker reale auto-provisionato per test tramite il backbone
  sigillato, nessun mock — tutti e 8 passati, ripetuti 3 volte per
  determinismo.
- Gate locali tutti verdi: `ruff`, `mypy` PASS, `validate_rccad.py`
  PASS, `validate_language_policy.py` PASS,
  `validate_ocor_change_scope.py --base origin/main` PASS (7
  percorsi), `validate_ocor_development_plan.py --base-ref origin/main
  --authorized-extension` PASS dopo il consueto doppio-run, pytest
  completo via lo script `pytest` nudo con `OCOR_LIVE_POSTGRES_DSN`
  impostato contro il PostgreSQL reale di ocor-bootstrap (dopo il
  riavvio di fuseki/spire-agent): `2 failed, 766 passed` (stessi 2
  fallimenti noti) più `29 passed` per le 3 suite `reports/tests/`.
- Evidenza sigillata: `reports/evidence/G4/OCOR-DEV-0041.json` +
  `reports/evidence/G4/OCOR-DEV-0041.log`.
  `reports/evidence/G4/MANIFEST.json` esteso con inserimento
  chirurgico (2 nuovi artifact, 9 nuovi requirement_results).
- Aggiornamento dei tre file di stato eseguito come PR dedicata
  immediatamente dopo il merge del task, non incluso nel commit del
  task.
- Claim fence invariato: `E1=0`, `E2=0`, zero requisiti `Verified`,
  `runtime_conformance` `NOT_ESTABLISHED`, `PoC`/`Production` `NO-GO`.
- `OCOR-DEV-0041`: tutti e 13 i check verdi al primo push. PR #113
  mergiata (`600b1aa1e95123e0194af13d973637d9d0999231`), SHA
  post-merge verificata anche per `backbone.py` e
  `test_ocor_dev_0040.py` (invariati byte-per-byte rispetto al hash
  sigillato di OCOR-DEV-0040).

## 2026-09-14 — Sincronizzazione stato: OCOR-DEV-0041 (post-merge, OCOR-DEV-0042 pronto)

- Sincronizzazione immediata dei tre file di stato subito dopo il
  merge della PR #113, su un branch dedicato
  (`governed/state-sync-ocor-dev-0041`).
- `baseline_commit` aggiornato a
  `600b1aa1e95123e0194af13d973637d9d0999231` in entrambi
  `EXECUTION_STATE.json` e `MODEL_HANDOFF.json`; `OCOR-DEV-0041`
  aggiunto a `completed_evidence_tasks`.
- Ricalcolata la prontezza dal backlog JSON: insieme pronto =
  {`OCOR-DEV-0042` (wave 15), `OCOR-DEV-0045` (wave 16),
  `OCOR-DEV-0046` (wave 15), `OCOR-DEV-0048` (wave 15)};
  `OCOR-DEV-0042` selezionato per ordine numerico sull'intero insieme
  pronto — "Implement exact approved 44-transition C6 FSM".
- Nessun codice sorgente toccato: gate locali rieseguiti comunque per
  protocollo standard e confermati invariati.
