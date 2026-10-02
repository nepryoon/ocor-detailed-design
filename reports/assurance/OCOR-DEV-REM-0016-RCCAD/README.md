# OCOR-DEV-REM-0016-RCCAD — content-addressed evidence records per REM-0010/0011/0012

- **Status**: `REGISTERED_OPEN_FOR_IMPLEMENTATION` (aperta da R2 il 2026-10-01)
- **Fonte**: verifica indipendente `REMEDIATION`
  (`request_id` `OCOR-DEV-REM-0010-0011-0012-1aaef13885ed-0`, finding `VF-003`)

## Finding (VF-003, severity high)

I record candidati di `OCOR-DEV-REM-0010/0011/0012` non sono content-addressed come
richiesto: mancano `commit`, `environment`, `commands` con exit/status,
`raw_output_sha256`, `created_at`, raw log e un manifest accettato da
`validate_runtime_evidence.py --non-skipped`.

## Fix richiesto

Produrre nuovi record candidati content-addressed per ciascuna remediation, collegati ai
record originali (immutabili) con supersession esplicita. Rieseguire i test sullo stack
reale con nuovi raw log e hash.

## Claims

`E1=0`, `E2=0`, nessun requisito `Verified`, runtime conformance/PoC/Production non
promossi. Nessuna modifica a `inputs/`, ADD o LLD.

## Implementazione (2026-10-01)

Prodotti i record candidati content-addressed per ciascuna remediation,
riqualificati all'HEAD `3135517`:

- `reports/assurance/OCOR-DEV-REM-0010-RCCAD/OCOR-DEV-REM-0010.json` + `.log` + `MANIFEST.json`
- `reports/assurance/OCOR-DEV-REM-0011-RCCAD/OCOR-DEV-REM-0011.json` + `.log` + `MANIFEST.json`
- `reports/assurance/OCOR-DEV-REM-0012-RCCAD/OCOR-DEV-REM-0012.json` + `.log` + `MANIFEST.json`

Ogni record è accettato da `validate_runtime_evidence.py --non-skipped` e supersede il
record storico `evidence.json` (immutabile) tramite il campo `supersedes`. Il record di
evidenza RCCAD di questo task è `evidence.json` in questa directory. Verifica
indipendente e CI verde sull'HEAD esatto restano prerequisiti del sigillo.

## Repair cycle 2 — VF-001 (validator fail-closed) + VF-002 (record commit/inputs) (2026-10-02)

La prima verifica indipendente ha aggiunto due finding a VF-003:

- **VF-001 (high)** — `scripts/validate_runtime_evidence.py` accettava evidenza non
  qualificante: una label `PASS` con `result` vuoto (`{}`), oppure `result.xfailed = 1`,
  qualificava comunque il record. Riparazione: il validator ora fallisce chiuso — una
  command deve portare un `exit_code` intero `0` oppure un oggetto `result`/counters con
  almeno un counter di fallimento, tutti a zero; un `result` vuoto, o un `xfailed` non
  zero, è rifiutato. `xfailed` è stato aggiunto sia ai counter riconosciuti sia allo
  stato non qualificante `NON_QUALIFYING`.
- **VF-002 (high)** — il record candidato dichiarava il commit base `3135517` e di non
  aver modificato codice, mentre il branch modifica `scripts/validate_runtime_evidence.py`,
  `reports/tests/test_runtime_evidence_validator.py`,
  `scripts/validate_ocor_development_plan.py` (allowlist) e
  `.github/workflows/ocor-tooling-bootstrap.yml` (CI). Riparazione: il record ora punta al
  commit del fix definitivo `15958fe` e i campi `inputs`/`changed_file_sha256`/`rollback`
  riflettono i file di codice modificati.

La suite di regressione verifica inoltre la **ragione** del rigetto: ogni caso negativo
asserisce il predicato fail-closed esatto che deve respingerlo (exit_code/failed/skipped/
not_executed non-zero, tipo `exit_code` invalido, label `PASS` nuda, `result` vuoto,
`result.xfailed` non-zero), non soltanto un exit code non-zero.

Regressione TDD (RED → GREEN) documentata nel raw log:

- **RED @ b93dab8**: `empty_result_dict` e `xfailed_in_result_1` accettati (rc=0).
- **GREEN @ HEAD**: entrambi rifiutati (rc=1), `full_valid` ancora accettato (rc=0).

Il validator continua ad accettare i tre record content-addressed (0010/0011/0012) e
tutta l'evidenza qualificante G0, quindi nessuna evidenza valida viene rigettata.
