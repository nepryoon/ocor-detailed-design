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

## Copertura del candidato TEST-INFRA-006 — 2026-10-07

Il job `conditional-infrastructure-0049` acquisisce in una checkout separata il
commit immutabile `d0ac80a9d1d603ca19ddbb2d5291e252b3d6ae2b` e avvia lo stack
completo mediante il bootstrap del change set REM. Esegue l'intera suite del
candidato, senza selezioni o esclusioni. Il supervisore verifica l'HEAD e
l'assenza di modifiche tracciate prima e dopo il run, oltre a richiedere nel
JUnit entrambi i moduli `test_ocor_dev_0048` e `test_ocor_dev_0049`. Un verde
senza uno dei due moduli viene rifiutato anche se altri test passano.

Il job obbligatorio `validation-closure` dipende da tale campagna e usa
`if: always()` con un controllo esplicito del risultato della dipendenza:
fallimento, cancellazione o mancata esecuzione non diventano un check verde
per effetto di uno skip del job. La successiva campagna del branch REM esegue
nuovamente tutti i test di main e le guardie dei report. TEST-INFRA-001/003/005
sono nella suite runtime, TEST-INFRA-002/004 nei report; TEST-INFRA-006 è
esercitato nella checkout candidata. Nessuna nuova guardia è registrata.

Helm 3.14.4, kind 0.29.0 e kubectl 1.33.1 sono acquisiti da release ufficiali
con confronto del checksum pubblicato, digest del download e del binario
installato. Versioni, oggetti misurati, licenze, architettura e data sono in
`infra/qualification_tools.lock.json`, supplemento per la qualificazione
non-production sotto DEC-211: il lock della toolchain esistente è invariato.
L'acquisizione scrive solo `.ocor/tools/bin/` del worktree e richiede
`--execute`; il controllo non mutativo valida i pin e le fonti senza installare.

Il teardown tenta sia kind sia bootstrap anche se una delle rimozioni
fallisce, preserva l'errore e verifica i residui. Timeout della suite 45 minuti,
zero skip, nessuna tolleranza a restart/OOM di bootstrap. I positivi e negativi
del supervisore e dei pin sono registrati nell'evidenza con fingerprint RED.

Questa campagna dimostra l'esecuzione delle guardie infrastrutturali, **non**
l'accettazione di OCOR-DEV-0049: il suo NO_GO ciclo 6 e i finding restano
invariati; nessun ciclo 7, riparazione, sigillo o merge di 0049. Implementatore
REM: Codex (OpenAI). Verifier REM: Claude Code (Anthropic), processo e contesto
separati; l'esito va acquisito dal loop prima di sigillare o integrare il REM.

### Igiene e memoria della JVM bootstrap

Il primo full del candidato in questa unità è stato interrotto dal supervisore
al minuto 27: `ocor-bootstrap-fuseki-1` OOMKilled=true, exit 137, cgroup 2 GiB.
I 1309 casi conclusi positivamente sono un risultato **parziale e non
qualificante**; il secondo stack non è stato avviato. Diagnostica e run fallito
sono preservati fuori Git e nel raw record. L'entrypoint dell'immagine pinned
imposta `JVM_ARGS=-Xmx4G`, superiore al suo cgroup; sul medesimo runtime la heap
non esplicitamente limitata può dipendere anche dalla memoria dell'host.

Il bootstrap REM genera un override worktree-local del solo ambiente Fuseki:
`JVM_ARGS=-Xms128m -Xmx1G`. Compose governato, limite 2 GiB, Dockerfile, immagine
e lock sono invariati. Il controllo legge il processo Java effettivo mediante
`docker top` (PID 1 è Docker init), rifiuta argomenti di heap contraddittori e
usa una flag probe della JRE pinned con gli stessi argomenti. La misura reale
è 1073741824 byte di heap entro 2147483648 byte di cgroup. `jcmd` assente e
`docker top` senza colonna PID sono stati tentativi falliti, non PASS; i metodi
sono stati corretti dopo diagnosi. Nessun pacchetto o runtime Java sostituito.

La nuova suite parte soltanto dopo teardown, bootstrap completo e salute dei
servizi. Positivi/negativi del controllo e della supervisione sono separati dai
run real-backend; nessun mock prova la disponibilità del servizio e nessuna
interruzione diventa un PASS. Se il retry o la CI non qualificano lo stack,
il REM resta aperto e si applica REM-0017-PRIORITY, senza escludere test.
