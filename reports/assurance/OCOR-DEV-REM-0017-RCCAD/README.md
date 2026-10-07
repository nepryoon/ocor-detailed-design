# OCOR-DEV-REM-0017-RCCAD — CI provisioning of the full ocor-bootstrap stack for test_ocor_dev_0048.py

- **Status**: `OPEN` (task aperto il 2026-10-05; implementazione, verifica indipendente e
  sigillo da eseguire)
- **Fonte**: decisione del Product Owner `CI-0048-REAL-BACKEND` (2026-10-05)
- **Deviazione registrata**: `reports/development/METHOD_COMPLIANCE.json` → `deviations`
  (id `CI-0048-REAL-BACKEND`, PR #164)

## Contesto / deviazione

La PR #164 ha escluso `ocor-runtime/tests/tasks/test_ocor_dev_0048.py` dal job
`validation-closure` con `--ignore` (guard `CONDITIONAL_INFRASTRUCTURE_GUARD`
`TEST-INFRA-005`): il CI di validation-closure ADD v1.2 non provisiona lo stack
`ocor-bootstrap` completo (SPIRE server/agent con workload identity SPIFFE e credenziali
di bootstrap). La restrizione è accettata dal Product Owner SOLO come misura temporanea.

## Ambito del task (fix richiesto)

Eseguire in CI lo stack `ocor-bootstrap` completo:

- SPIRE server e agent (workload identity SPIFFE) con credenziali di bootstrap;
- immagini digest-pinned da `infra/services.lock.json`;
- far girare `ocor-runtime/tests/tasks/test_ocor_dev_0048.py` con **zero skip**;
- rimuovere l'`--ignore=tests/tasks/test_ocor_dev_0048.py` dal job `validation-closure`
  di `.github/workflows/ocor-validation-closure.yml`.

## Criteri di accettazione

- Il job `validation-closure` in CI esegue `test_ocor_dev_0048.py` senza `--ignore` e con
  zero `skipped`.
- I 196 casi real-backend di `OCOR-DEV-0048` (OPA, Keycloak, SPIFFE/SPIRE, OpenBao, mTLS)
  sono eseguiti in CI sullo stack `ocor-bootstrap` completo, non solo sullo stack locale.
- Nessun indebolimento di test, gate o soglie; nessun `--ignore`, deselezione o
  marcatura di test; i conteggi `skipped` restano zero e non vengono rimossi dai report.
- I gate locali e CI restano verdi sull'HEAD esatto: `validate_rccad.py`,
  `validate_language_policy.py`, `validate_ocor_change_scope.py`,
  `validate_ocor_development_plan.py`, `validate_runtime_evidence.py --non-skipped`,
  `validate_evidence_input_drift.py`, `sha256sum -c inputs/normative/SHA256SUMS`.

## Criteri negativi (rigetto)

- Il REM non è chiuso se `test_ocor_dev_0048.py` risulta `skipped`, escluso o non eseguito
  in CI sullo stack completo.
- Il REM non è chiuso se il `--ignore` viene lasciato o se un controllo di CI viene
  fatto passare escludendo/deselezionando/marcando test.
- Il REM non è chiuso se le immagini SPIRE/OpenBao/OPA/Keycloak usate non corrispondono
  ai digest di `infra/services.lock.json`.

## Dipendenza G6

Questo REM è **dipendenza obbligatoria di ogni task G6** (`OCOR-DEV-0060` … `OCOR-DEV-0066`):
nessun task G6 parte prima della sua chiusura verificata. Non blocca `OCOR-DEV-0049` né i
task G5. Il vincolo è registrato in `reports/development/EXECUTION_STATE.json` (`blockers`,
id `OCOR-DEV-REM-0017`, `blocked_tasks` = task G6).

## Claims

`E1=0`, `E2=0`, nessun requisito `Verified`, runtime conformance/PoC/Production non
promossi. Nessuna modifica a `inputs/`, ADD o LLD. Nessun indebolimento di test, validator,
workflow, ruleset o soglie.

## Ripresa Codex — 2026-10-07 (WIP, nessuna chiusura)

Mandato `REM-0017-PRIORITY`: il perimetro comprende tutti i
`CONDITIONAL_INFRASTRUCTURE_GUARD`, inclusi TEST-INFRA-005/006. Implementatore
della ripresa: **Codex (OpenAI)**; verifier previsto: **Claude Code (Anthropic)**,
processo e contesto separati. La verifica indipendente non è ancora richiesta:
il requisito TEST-INFRA-006 non è soddisfatto da questa unità.

La PR #169 era inattiva dal 2026-10-05; nessun processo concorrente ne possedeva
il worktree. Il branch è stato riallineato mediante merge di origin/main senza
riscrittura. Il log originale del job 111900253107 è stato acquisito via API:
SPIRE server esce con codice 1, ma il job non aveva raccolto i suoi log. Un
probe sullo stesso digest, con UID diverso dal proprietario della chiave CA
0600, riproduce `permission denied`. È una causa riprodotta compatibile col
crash CI, non una diagnosi ricavata da log SPIRE che il vecchio job non contiene.

Il nuovo `bootstrap_ci_environment.py` avvia l'intero Compose, usa i digest del
lock, genera credenziali locali e assegna soltanto la CA generata all'UID/GID
1000 dell'immagine SPIRE verificata. Registra il workload control-plane e verifica
un SVID reale prima delle qualificazioni tipizzate. La build CI Fuseki usa la
ricetta esistente (base digest e archivio SHA-512), registra l'ID effettivo della
build, ed è qualificata dal validator tipizzato esistente. Il confronto di
identità macchina nel bootstrap locale, il Dockerfile e i lock sono invariati.
Questa procedura non dichiara che una build CI coincida con l'ID della macchina
registrato nel lock.

Il workflow raccoglie tutti i test runtime, compila SDK/oracolo TypeScript con i
pin, esegue anche i due guard nei report, rifiuta immediatamente JUnit con skip,
e rimuove il progetto nel teardown always(). Il supervisore limita la suite a
45 minuti e interrompe su servizio perso, sostituito, riavviato o OOM; conserva
statistiche e log sanitizzati limitati al progetto. Le Actions sono commit-pinned.
Le sole aggiunte al validator di piano sono percorsi puntuali nell'allowlist.

Il primo run completo locale è fallito (913 PASS, 2 FAIL, 186 ERROR, 0 skip)
per assenza dell'entry SPIRE del control plane. Il bootstrap è stato corretto,
poi sono stati eseguiti reset e nuova acquisizione dello stack; i risultati del
run successivo sono registrati nel record WIP, senza cancellare il fallimento.

TEST-INFRA-006 punta a `ocor-runtime/tests/tasks/test_ocor_dev_0049.py`, assente
su origin/main 33821f3. Il candidato d0ac80a contiene il file, ma conserva il
NO_GO ciclo 6: non è stato copiato né promosso. Il run su main non ne prova
l'esecuzione. Il REM resta OPEN/WIP, dipendenza obbligatoria G6, fino a una
campagna CI esplicita di quel guard e alla verifica indipendente dell'intero
change set. Non considerare una CI verde sul solo contenuto di main come
chiusura del REM. La prossima unità deve completare questa copertura in un
checkout CI separato dell'HEAD candidato esatto, senza riparare né accettare
0049; se la capacità del runner non basta, raccogliere misure, aprire la
richiesta prevista dal PO e proseguire con 0050.

Rollback: nuovo revert del change set governato; nessuna migrazione dei dati.
L'eventuale rollback della rimozione dell'ignore è solo ripristino della misura
storica PR #164, soggetto alla sua disposition PO, mai un mezzo per sigillare
questo REM. Il candidato non è stato integrato; main conserva la misura.
