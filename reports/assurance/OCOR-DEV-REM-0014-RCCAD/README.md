# OCOR-DEV-REM-0014-RCCAD — TypeDB commit_id/watermark injection

- **Status**: `CANDIDATE_PENDING_INDEPENDENT_VERIFICATION_CI_AND_INTEGRATION`
  (implementata con TDD RED→GREEN il 2026-10-01; in attesa di verifica indipendente,
  CI verde e integrazione prima del sigillo)
- **Fonte**: verifica indipendente `REMEDIATION`
  (`request_id` `OCOR-DEV-REM-0010-0011-0012-1aaef13885ed-0`, finding `VF-001`)
- **Supersede/relaziona**: hardening degli adapter C4 (alias canonico `OCOR-DEV-REM-0013`,
  directory storica `OCOR-DEV-REM-0010-RCCAD/`)

## Finding (VF-001, severity high)

In `ocor-runtime/src/ocor_runtime/c4/typedb_adapter.py:211` la query di watermark
inserisce `commit_id` senza il safe literal rendering già applicato ad altri campi; il
contratto dell'identificatore non è validato prima delle query.

## Fix richiesto

Applicare il safe literal rendering anche all'insert del watermark (`commit_id`) e
validare il contratto dell'identificatore prima delle query. Aggiungere test live
positivi/negativi per `fact_id`, `payload` e `commit_id` (fact/watermark pre-esistente,
assenza di injection, identità del watermark, atomicità).

## Claims

`E1=0`, `E2=0`, nessun requisito `Verified`, runtime conformance/PoC/Production non
promossi. Nessuna modifica a `inputs/`, ADD o LLD.

## Implementazione

Eseguita con TDD RED→GREEN su backend reale TypeDB (stack `ocor-bootstrap`):

- **RED** (`bb893ef`): 15 failed, 2 passed — l'insert del watermark usava un
  `"{commit_id}"` nudo, quindi un `commit_id` iniettato spezzava il literal (watermark
  memorizzato come `x`) e creava un fatto iniettato; `apply_commit` sollevava
  `AttributeError` invece di `C2Error` per `fact_id`/`commit_id`/`payload` malformati.
- **GREEN** (`5b6b027`): 17 passed — `apply_commit` ora usa `_literal(commit_id)` per il
  watermark e `_require_value` valida il contratto degli identificatori (`fact_id`,
  `commit_id`, `payload` non vuoti e stringa) prima di costruire qualunque query, con
  rigetto fail-closed `C2Error`. Il `commit_id` iniettato è memorizzato verbatim come
  singolo literal: nessun fatto iniettato, identità del watermark e atomicità
  fact+watermark preservate.
- **Regressione**: 35 passed sulle suite live di `OCOR-DEV-0037/0038/0039` e
  `OCOR-DEV-REM-0010/0011/0012` (con `OCOR_LIVE_POSTGRES_DSN` sullo stack reale per 0039).
- **Gate locali verdi**: `verify.py --json` PASS 14/0/0, `sha256sum -c
  inputs/normative/SHA256SUMS` 8/8, `ruff check .` PASS, `mypy --strict` PASS (67 file),
  `validate_language_policy.py`, `validate_ocor_change_scope.py`,
  `validate_rccad.py` PASS.

Il record di evidenza `evidence.json` è prodotto con stato
`CANDIDATE_PENDING_INDEPENDENT_VERIFICATION_CI_AND_INTEGRATION`; verifica indipendente
e CI verde sull'HEAD esatto sono prerequisiti per il sigillo.
