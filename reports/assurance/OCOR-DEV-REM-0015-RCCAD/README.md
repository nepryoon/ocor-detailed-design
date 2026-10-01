# OCOR-DEV-REM-0015-RCCAD — validate_rccad Unicode/tab/newline path handling

- **Status**: `CANDIDATE_PENDING_INDEPENDENT_VERIFICATION_CI_AND_INTEGRATION` (implementata il 2026-10-01)
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
per nome. Regressione hermetic in `reports/tests/test_rccad_methodology.py`
(`test_git_changed_returns_unquoted_paths_for_special_filenames`) per staged
add/modify/delete/rename con Unicode, tab e newline, che asserisce path raw non quotati
e `RCCAD-IMMUTABLE-INPUT`.

TDD RED→GREEN registrato in `evidence.json` (candidato) e nel record content-addressed
`OCOR-DEV-REM-0015.json` + `.log` + `MANIFEST.json` (validabile con
`validate_runtime_evidence.py --non-skipped`). Verifica indipendente richiesta prima del
sigillo. Nessuna modifica a `inputs/`, ADD o LLD.
