# OCOR-DEV-REM-0012 — RCCAD precheck must detect staged input changes

Remediation del finding `RVW-05` della revisione
`reports/review/OCOR_FULL_CODE_REVIEW_2026-09-15.md`.

## Difetto

`scripts/validate_rccad.py` `git_changed()` derivava l'insieme dei path
modificati solo da `git diff --name-only` (working tree vs index) e, con base
ref, `git diff --name-only <base> HEAD`. Nessuno dei due mostra una modifica
**staged** ma non ancora committata, quindi un edit staged-only sotto `inputs/`
poteva sfuggire al precheck locale `RCCAD-IMMUTABLE-INPUT`.

## Correzione

`git_changed()` esegue anche `git diff --cached --name-only`. È difesa in
profondità: la CI ri-verifica comunque l'immutabilità con
`git diff --exit-code <base> -- inputs/` e `validate_ocor_change_scope.py`
(che già unisce `git status --porcelain`).

## Stato

Candidato qualificato con TDD RED→GREEN (test hermetici su repo git temporaneo)
e gate locali verdi. **Non** è un sigillo: richiede verifica indipendente e CI
verde sull'HEAD esatto. Nessuna modifica a `inputs/`, ADD o LLD; nessun claim
probatorio promosso.
