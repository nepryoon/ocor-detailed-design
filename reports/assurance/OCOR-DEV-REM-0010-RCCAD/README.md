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
