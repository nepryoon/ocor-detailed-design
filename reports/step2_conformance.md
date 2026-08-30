# STEP 2 — Conformance test degli schemi

Suite: `reports/tests/test_schema_conformance.py`. Risultato machine-readable: `reports/tests/conformance_results.json`. La suite estrae i contratti direttamente dall'ADD, usa JSON Schema Draft 2020-12 con format checking e avvolge i component schema OpenAPI per risolverne i `$ref` locali. Esito complessivo: **98 casi, 97 conformi all'oracolo, 1 fallito**.

Il conteggio `Rami condizionali` mantiene la metrica del harness (`if/then`); la suite copre inoltre tutte le alternative `oneOf` presenti nei punti esercitati e smoke test positivi/negativi per le sei request OpenAPI. Un medesimo fixture può esercitare più vincoli dello stesso ramo, ma ogni ramo dispone di almeno un positivo valido e di un negativo mirato.

| Schema | Rami condizionali | Casi positivi | Casi negativi | Rami insoddisfacibili | Esito |
|---|---:|---:|---:|---:|---|
| `signed-canonical-ir:1.0` | 0 | 1 | 1 | 0 | `PASS` strutturale |
| `canonical-ingestion-envelope:1.1` | 4 | 11 | 9 | 0 | `PASS` |
| `mcp-tool-contract:1.1` | 11 | 11 | 13 | 0 | `PASS` sui rami codificati |
| `action-type-contract:1.0` | 9 | 9 | 11 | 0 | `FAIL` semantico: 1 negativo safety accettato |
| `event-subscription-contract:1.0` | 0 | 1 | 4 | 0 | `PASS` strutturale |
| OpenAPI 1.1.0 | 3 | 15 | 11 | 0 | `PASS` sui component schema; validazione semantica ufficiale `NOT_EXECUTED` |

## Caso fallito

### `action-type-contract:1.0` — commit canonico senza Human Gate

Un'istanza con:

- `target=CANONICAL_COMMIT`;
- `effect_class=CANONICAL_COMMIT`;
- `canonical_commit_binding` completo, con `CanonicalAssertion` e i due flag a `true`;
- `risk_class=R1_ANALYZE`;
- `approval.mode=NONE`;

è **accettata** dal validator. L'oracolo architetturale richiede invece il rigetto: §4.1 afferma che le mutazioni canoniche attraversano «la stessa FSM, le stesse guardie e lo stesso Human Gate» delle azioni esterne e §5.4 classifica una mutazione interna reversibile come almeno `R2_CONTROLLED`, con un approvatore umano indipendente. Il ramo `target=CANONICAL_COMMIT` di §3.7 vincola `effect_class` e reversibilità, ma non impone né `risk_class ∈ {R2_CONTROLLED,R3_HIGH_IMPACT}` né un Approval umano.

Questo non è un ramo insoddisfacibile: è il difetto opposto, un ramo soddisfacibile con un'istanza che viola un invariante di safety. La suite conserva il caso come `FAIL`, senza correggere lo schema normativo.

## Copertura aggiuntiva

- Ingestion: positivi batch/stream/CDC; mismatch mode/transport/class; alternative nullable di `effective_time.to`, `causation_id`, `before_digest`, `after_digest`.
- MCP: retry non safe, High/Critical, execute-approved, dual control, Human Gate, compensation e corrispondenza di tutti gli effect/tier.
- Action: target interno/esterno, CanonicalAssertion, R2/R3, compensation, irreversibilità e retry non safe.
- Event: at-least-once, cursor opaco, filtro nominato e marking propagation.
- OpenAPI: tutte le request, `Consistency`, i due rami condizionali `Problem` e le alternative nullable di `TemporalInterval` ed `EpistemicStatus`.

## Limitazioni

La suite verifica conformance documentale degli schema embedded. Non costituisce evidenza d'implementazione e non modifica `E1=0` o `E2=0`. La validazione semantica dell'intero documento OpenAPI con un validator OpenAPI 3.1 ufficiale resta `NOT_EXECUTED`, coerentemente con il referto del harness; i component schema esercitati non sostituiscono quel controllo.
