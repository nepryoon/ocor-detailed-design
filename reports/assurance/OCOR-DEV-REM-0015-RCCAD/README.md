# OCOR-DEV-REM-0015-RCCAD — validate_rccad Unicode/tab/newline path handling

- **Status**: `REGISTERED_OPEN_FOR_IMPLEMENTATION` (aperta da R2 il 2026-10-01)
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

Da eseguire con TDD RED→GREEN→REFACTOR, gate verdi e verifica indipendente prima del
sigillo. Il record di evidenza `evidence.json` sarà prodotto al momento
dell'implementazione.
