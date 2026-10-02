# OCOR-DEV-REM-0010 — C4 projection adapter identifier/literal hardening

Remediation del finding `RVW-01`/`RVW-02` della revisione
`reports/review/OCOR_FULL_CODE_REVIEW_2026-09-15.md`.

## Difetto

Gli adapter C4 reali interpolano identificatori/literali in query TypeQL/SPARQL:

- `c4/typedb_adapter.py` inseriva `fact_id`/`commit_id`/`payload` in literal
  TypeQL senza escape di `\` e `"`.
- `c4/jena_adapter.py` inseriva `resource_id` in posizione IRI (`<...>`) senza
  validazione dei caratteri vietati in un IRIREF SPARQL. (I valori delle
  proprietà erano già correttamente escapati da `_literal`.)

## Correzione

- TypeDB: aggiunto l'helper `_literal()` (escape di `\` e `"`) e usato in
  `apply_commit` e `_lookup_fact`. Per URN/digest canonici l'output è
  byte-identico a prima.
- Jena: aggiunto `_require_iri()` (fail-closed `RESOURCE_ID_INVALID`) invocato in
  `publish` e `to_json_ld` **prima** di qualunque contatto col backend. Gli URN
  passano invariati.

## Non-regressione

Le suite di accettazione reali C4 usano solo URN/digest (nessun `"`/`\`/carattere
vietato), quindi le query generate restano identiche: nessuna regressione attesa.
La validazione contro TypeDB/Fuseki reali avviene in CI (vedi `local_not_executed`).

## Stato

Candidato qualificato con TDD RED→GREEN e gate locali verdi. **Non** è un sigillo:
richiede verifica indipendente e CI verde sull'HEAD esatto prima del seal e del
merge governato. Nessuna modifica a `inputs/`, ADD o LLD; `E1=0`, `E2=0`, nessun
requisito `Verified`, runtime conformance/PoC/Production non promossi.

## Erratum — collisione di ID (2026-10-01)

`OCOR-DEV-REM-0010` è doppiamente assegnato: indica sia la correzione `$ref` del
generatore di contratti (2026-09-12, PR #63) sia l'hardening degli adapter C4
registrato in questa directory (2026-09-15, PR #128). Al secondo è assegnato il
primo `OCOR-DEV-REM-*` libero — `OCOR-DEV-REM-0013` — come **alias canonico**,
senza rinominare la storia (la directory resta `OCOR-DEV-REM-0010-RCCAD/`). Il
record `evidence.json` espone il campo `id_alias`.

## Verifica indipendente (2026-10-01)

La verifica indipendente richiesta da R2 (`request_id`
`OCOR-DEV-REM-0010-0011-0012-1aaef13885ed-0`, `head_sha`
`1aaef13885ed142646d0ed35c995078c30d9f174`) ha restituito **`NO_GO`** con quattro
finding bloccanti (`VF-001`…`VF-004`). Il risultato completo è appeso in append al
record `evidence.json` (campo `independent_verification_result`) senza riscrivere i
campi storici. Questo candidato resta **non sigillato**.

## Requalificazione content-addressed (2026-10-01)

A fronte di `VF-003` (`OCOR-DEV-REM-0016`) è prodotto il record candidato
content-addressed `OCOR-DEV-REM-0010.json` (con `.log` e `MANIFEST.json`),
riqualificato all'HEAD `3135517` e accettato da
`validate_runtime_evidence.py --non-skipped`. Supersede questo `evidence.json`
(immutabile) tramite il campo `supersedes`.
