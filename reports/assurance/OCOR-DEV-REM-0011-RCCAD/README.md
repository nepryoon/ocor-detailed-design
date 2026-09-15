# OCOR-DEV-REM-0011 — C1 fail-closed handling of `execution_owner`

Remediation del finding `RVW-04` della revisione
`reports/review/OCOR_FULL_CODE_REVIEW_2026-09-15.md`.

## Difetto

`FrontendTypeAndSemanticValidator.validate` calcolava
`{owners} if isinstance(owners, str) else set(owners)`. Un `execution_owner`
malformato (non stringa, non lista — es. `42`) provocava un `TypeError` e il
crash del compilatore invece di un `C1Error` deterministico; una lista con
owner non-stringa (o una mappa) veniva accettata silenziosamente.

## Correzione

`execution_owner` è validato come stringa oppure lista di stringhe; qualsiasi
altro tipo produce un `C1Diagnostic(TYPE_ERROR, ...)` bounded, coerente con il
contratto fail-closed del frontend. I casi validi (stringa singola, lista con
owner ripetuto, lista di owner distinti → `MULTIPLE_EXECUTION_OWNERS`) restano
invariati.

## Stato

Candidato qualificato con TDD RED→GREEN, suite C1 esistente verde (nessuna
regressione) e gate locali verdi. **Non** è un sigillo: richiede verifica
indipendente e CI verde sull'HEAD esatto. Nessuna modifica a `inputs/`, ADD o
LLD; `E1=0`, `E2=0`, nessun requisito `Verified`, nessun claim promosso.
