# STEP 0 — Ambiente e integrità

Data di esecuzione: 2026-08-30 (Europe/Rome)

| Controllo | Comando | Esito |
|---|---|---|
| Integrità sorgenti normative | `sha256sum -c inputs/normative/SHA256SUMS` | `PASS`: 8 file verificati, tutti i digest coincidono. Il digest dell'ADD v1.1 è `3e7532c7101e80c74b511cedc56a0563ca0938a3fe259911a91245cb19dedc7f`, uguale al valore atteso. |
| Harness tool-backed | `./.venv/bin/python3 scripts/verify.py --json \|\| true` | 13 `PASS`, 0 `FAIL`, 1 `NOT_EXECUTED`. Referto JSON: `reports/verify_report.json`. |
| Branch corrente | `git rev-parse --abbrev-ref HEAD` | `fase-1`; applicabile il percorso STEP 0–7. |

## Dettaglio harness

Risultano superati: integrità sorgenti; parsing e meta-validazione di 5 JSON Schema; risoluzione dei `$ref` OpenAPI; compilazione Protobuf; parsing Turtle/RDF; controllo strutturale dei rami condizionali insoddisfacibili della classe RV-01; bijezione FSM diagramma/tabella; contiguità della famiglia `ACT-T`; allocazione di tracciabilità; universo normativo; rimandi di sezione; evidence fence; assenza di assegnazione di `DEC-197`.

`NOT_EXECUTED`: validazione semantica OpenAPI 3.1 con validator ufficiale, perché il validator non è disponibile nel harness. Questo controllo non è dichiarato superato.

Il conteggio informativo dei rami condizionali da coprire con casi positivi è: `signed-canonical-ir=0`; `canonical-ingestion-envelope=4`; `mcp-tool-contract=11`; `action-type-contract=9`; `event-subscription-contract=0`.

Stato probatorio invariato: `E1=0`, `E2=0`, zero requisiti `Verified`.
