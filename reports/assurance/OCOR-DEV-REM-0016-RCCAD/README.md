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
