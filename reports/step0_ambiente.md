# STEP 0 — Ambiente e integrità

- Data esecuzione: `2026-08-30T16:26:00+02:00`
- Branch: `fase-1`
- Interprete: `.venv/bin/python`
- Dipendenze (`jsonschema`, `pyyaml`, `rdflib`, `grpcio-tools`): `OK`
- Working tree iniziale: pulita (`fase-1...origin/fase-1`)

## Integrità

`sha256sum -c inputs/normative/SHA256SUMS`: `PASS`. Tutti gli otto file elencati
nel manifest hanno digest coincidente.

Digest ADD v1.1 osservato:
`3e7532c7101e80c74b511cedc56a0563ca0938a3fe259911a91245cb19dedc7f`.
Coincide con il digest atteso dal mandato.

## Harness tool-backed

Comando: `.venv/bin/python scripts/verify.py --json`

Esito complessivo: `PASS 13`, `FAIL 0`, `NOT_EXECUTED 1`.

| Controllo | Esito | Nota |
|---|---:|---|
| Integrità sorgenti | PASS | 8 file, digest coincidenti |
| JSON Schema — parsing e meta-validazione | PASS | 5 schemi Draft 2020-12 |
| OpenAPI — risoluzione `$ref` | PASS | OpenAPI 3.1.0; 6 path, 25 schemi, 26 `$ref`; nessuno schema non referenziato |
| OpenAPI — validazione semantica con validator ufficiale | NOT EXECUTED | Validator OpenAPI 3.1 assente dal harness; il controllo non è dichiarato superato |
| Protobuf — compilazione | PASS | Compilazione senza errori |
| Turtle/RDF — parsing | PASS | 17 triple |
| Rami condizionali insoddisfacibili, classe RV-01 | PASS | Nessun campo condizionalmente richiesto ma non dichiarato |
| FSM — bijezione diagramma/tabella | PASS | 29 stati in corrispondenza |
| FSM — famiglia `ACT-T` | PASS | `ACT-T01`–`ACT-T31` contigui, incluse varianti a/b/c |
| FSM — stati terminali | INFO | Nessun terminale inatteso; nessuno stato di indeterminatezza senza uscita |
| Tracciabilità — allocazione in §7 | PASS | DEC 181/196; BR 18/18; FR 174/174; NFR 93/93; ARC 23/23; CAP 25/26; ELM 103/103; RSK 60/60 |
| Universo normativo | PASS | 693/693 |
| Rimandi di sezione | PASS | 44 rimandi distinti; nessuno non risolto |
| Evidence fence | PASS | `E1=0` presente; nessun claim probatorio non supportato rilevato dal harness |
| Nessun `DEC-197` assegnato | PASS | Occorrenze soltanto negative o nel nome del file |

Il JSON integrale prodotto dal harness è conservato in
`reports/verify_report.json`. Il controllo OpenAPI con validator ufficiale resta
esplicitamente `NOT EXECUTED` e non sarà presentato come superato.
