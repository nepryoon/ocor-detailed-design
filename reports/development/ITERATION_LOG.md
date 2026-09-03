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
