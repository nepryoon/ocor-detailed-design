# OCOR-DEV-REM-0015-RCCAD — validate_rccad Unicode/tab/newline path handling

- **Status**: `QUALIFIED_CANDIDATE_PENDING_SEAL_CI_AND_INTEGRATION`
  (implementata con TDD RED→GREEN il 2026-10-01; verifica indipendente
  `GO_FOR_EVIDENCE_SEAL` ricevuta il 2026-10-01; in attesa di CI verde sull'HEAD
  esatto e integrazione per il sigillo)
- **Fonte**: verifica indipendente `REMEDIATION`
  (`request_id` `OCOR-DEV-REM-0010-0011-0012-1aaef13885ed-0`, finding `VF-002`)

## Finding (VF-002, severity medium)

In `scripts/validate_rccad.py:68` la lettura dei path da `git diff --name-only` è
`line.split("\n")`, che perde/interpreta erroneamente nomi con tab, newline o caratteri
Unicode, indebolendo il controllo `RCCAD-IMMUTABLE-INPUT`.

## Fix richiesto

Usare `git diff --name-only -z` (delimitato da NUL) per working tree, index e
`base..HEAD`, e separare su NUL senza perdere nomi o escape. Aggiungere regressioni per
staged modify/add/delete/rename, Unicode, tab e newline che asseriscano
`RCCAD-IMMUTABLE-INPUT`.

## Claims

`E1=0`, `E2=0`, nessun requisito `Verified`, runtime conformance/PoC/Production non
promossi. Nessuna modifica a `inputs/`, ADD o LLD.

## Implementazione

`git_changed()` ora usa `git diff --name-only -z --no-renames` per working tree e index,
e `git diff --name-only -z --no-renames <base> HEAD`, separando su NUL con `os.fsdecode`
per nome. Regressioni hermetic in `reports/tests/test_rccad_methodology.py`:
`test_git_changed_returns_unquoted_paths_for_special_filenames` (unit) più quattro
regressioni end-to-end che attraversano l'intero validatore e asseriscono `exit != 0` /
`status = FAIL` / il path esatto `RCCAD-IMMUTABLE-INPUT` per add/modify/delete/rename
sulle superfici working tree, index e `base..HEAD`, su entrambi i lati di un rename che
attraversa il confine `inputs/`, con controlli positivi.

TDD RED→GREEN (repair cycle 1, VF-001/VF-002) registrato in `evidence.json` (candidato)
e nel record content-addressed `OCOR-DEV-REM-0015.json` + `.log` + `MANIFEST.json`
(validabile con `validate_runtime_evidence.py --non-skipped`). Il log raw registra 10
comandi con `exit_code`, incluso il RED `EXPECTED_FAILURE` (5 failed / 7 passed).
Verifica indipendente completata con `GO_FOR_EVIDENCE_SEAL` (vedi sotto). Nessuna modifica a `inputs/`, ADD o LLD.

## Verifica indipendente (GO_FOR_EVIDENCE_SEAL)

Verdetto ricevuto il 2026-10-01 per `request_id`
`OCOR-DEV-REM-0015-16fa3f423dae-3` (`review_type` `REMEDIATION`, repair cycle 3):

- **Verdict**: `GO_FOR_EVIDENCE_SEAL` — nessun finding (`blocker=0`, `high=0`,
  `medium=0`, `low=0`). Il record content-addressed, il manifest e la tracciabilità
  `supersedes` sono coerenti con l'HEAD verificato
  `16fa3f423dae94b5155e11d4dea820fac98cefca`.
- **Verifier**: processo `codex exec --ephemeral` a contesto pulito su un clone
  separato, modello non esposto dal runtime (`NOT_EXPOSED_BY_RUNTIME`), limite di
  indipendenza dichiarato: processo e contesto separati, stesso fornitore di modello
  dell'implementatore.
- **Sigillo**: identità/configurazione del verifier e verdetto registrati in
  `evidence.json` (`independent_verifier` + `independent_verification_result`) e nel
  record content-addressed `OCOR-DEV-REM-0015.json` (campo `verification`); hash del
  record riallineato in `MANIFEST.json`. Il raw log `OCOR-DEV-REM-0015.log` e il suo
  `raw_output_sha256` restano invariati. Il sigillo si completa con la CI verde
  sull'HEAD esatto e il merge.
