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
