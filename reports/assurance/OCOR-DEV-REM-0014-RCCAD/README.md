# OCOR-DEV-REM-0014-RCCAD — TypeDB commit_id/watermark injection

- **Status**: `REGISTERED_OPEN_FOR_IMPLEMENTATION` (aperta da R2 il 2026-10-01)
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

Da eseguire con TDD RED→GREEN→REFACTOR su backend reale TypeDB, gate verdi e verifica
indipendente prima del sigillo. Il record di evidenza `evidence.json` sarà prodotto al
momento dell'implementazione.
