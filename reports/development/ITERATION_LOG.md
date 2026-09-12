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
