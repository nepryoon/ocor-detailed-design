# OCOR architecture fitness functions

Tutte le regole sono bloccanti e dichiarate nel manifest. Il validator locale esegue
solo guardrail statici e restituisce `PASS_LOCAL_PRECHECK` con
`dynamic_assurance=CI_REQUIRED`; non può dichiarare le AFF qualificate. Il job
`rccad-methodology` esegue il validator, i validator di piano/evidenza e il portfolio
dinamico pinned. Solo il successo dell'intero job qualifica `AFF-001`–`AFF-010` per il
change set.

| Rule | Executable outcome |
|---|---|
| `AFF-001` | component/dependency boundaries reject forbidden imports |
| `AFF-002` | ports/adapters isolation rejects infrastructure leakage |
| `AFF-003` | canonical contracts reject backend identifiers |
| `AFF-004` | schema and public-contract parsing/compatibility pass |
| `AFF-005` | canonical serialization and hashing are deterministic |
| `AFF-006` | direct database/broker access outside adapters is rejected |
| `AFF-007` | idempotency/dedup obligations remain traced and tested |
| `AFF-008` | provenance and evidence records are complete/content-addressed |
| `AFF-009` | authorization defaults fail closed; silent fallbacks are rejected |
| `AFF-010` | every normative requirement maps to implementation and test plan |

Una regola non applicabile deve avere una disposition espressa nel task; una regola
non eseguita non passa. Le scansioni statiche sono guardrail e non sostituiscono i test
dinamici o real-backend.
