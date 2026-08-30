# FASE 7 — Validazione meccanica

## Oggetto e harness

Oggetto: `reports/OCOR_Architectural_Design_Document_v1.2_Candidate.md`.

Comandi riproducibili:

```bash
./.venv/bin/python3 scripts/verify.py --add reports/OCOR_Architectural_Design_Document_v1.2_Candidate.md --json
./.venv/bin/python3 reports/tests/test_v12_candidate.py
./.venv/bin/python3 reports/tests/test_v12_semantics.py
./.venv/bin/python3 reports/tests/test_v12_release_gate.py
```

## Risultati aggregati

| Suite | PASS | FAIL | `NOT_EXECUTED` | Artefatto |
|---|---:|---:|---:|---|
| verifier tool-backed candidata | 12 | 0 | 2 | `reports/tests/v12_verify_report.json` |
| conformance JSON Schema/OpenAPI | 105 | 0 | 0 | `reports/tests/v12_conformance_results.json` |
| semantica/FSM/adversarial | 29 | 0 | 0 | `reports/tests/v12_semantic_results.json` |
| release gate/patch/integrità | 12 | 0 | 0 | `reports/tests/v12_release_gate_results.json` |
| Totale di asserzioni/controlli | **158** | **0** | **2 nel verifier** | — |

Il primo `NOT_EXECUTED` del verifier («SHA256SUMS assente accanto alla candidata») è coperto dal release gate: digest baseline e tutti gli entry dei due manifest sorgente coincidono, il patch è leggibile e il checksum finale viene generato in FASE 10. Non viene riclassificato retroattivamente come `PASS` del verifier. Il secondo resta effettivamente `NOT_EXECUTED`: validator semantico OpenAPI 3.1 ufficiale non disponibile. Il controllo alternativo eseguito comprende YAML parse, OpenAPI 3.1.0/version check, 26 `$ref` risolti, 25 component schema referenziati e conformance Draft 2020-12 sulle request/response fixture.

## Copertura contratti

- cinque JSON Schema estratti e meta-validi Draft 2020-12;
- 31 rami condizionali JSON (`4+11+11+2`) con almeno un positivo e un negativo; schema Signed IR con smoke positivo/negativo;
- tre rami OpenAPI con positivi/negativi, più sei request, `Problem`, oneOf e `ObjectSnapshot`;
- canonical commit R1/NONE, senza Decision, Authority o Evidence: respinti;
- `R2_CONTROLLED` con quorum/ruoli vuoti: respinto;
- target/effect incompatibili: respinti dallo schema;
- replay senza bounded window: respinto;
- `ObjectSnapshot` senza relazioni, uncertainty o explanation: respinto;
- Protobuf compilato tramite tooling Python già presente; Turtle: 17 triple parsate.

## Copertura semantica e FSM

- Principal coerente accettato; body mismatch e transport binding non verificato respinti;
- dispatch valido emesso; state/policy/stop drift, lease scaduta e audit indisponibile portano a `INVALIDATED`;
- restriction join = union, permission join = intersection; operator mismatch e unknown label negati;
- 44 tuple FSM diagramma/tabella identiche; 31 numeri `ACT-T` contigui; ID univoci; tutti gli stati raggiungibili; source/destination non vuoti;
- ID inesistente e claim `Verified` con `E1=0/E2=0` respinti per la ragione prevista.

## Release gate

Sessanta hunk del patch sono mappati a un ID `V12-AM-*` mediante il primo heading precedente. Digest v1.1 esatto; 8/8 digest normativi e 2/2 digest prior coincidono; nessun file protetto è modificato. Rimandi risolti, ID definiti univoci, zero dialect/backend nei blocchi di contratto pubblico, evidence e scope fence verdi.

## Esito

`PASS WITH DECLARED NOT_EXECUTED`. Nessun fallimento. Il validator OpenAPI ufficiale mancante non impedisce la conclusione strutturale perché tutti i controlli essenziali utilizzati dalla candidata hanno un'alternativa locale eseguita; non viene però dichiarata conformità a tale validator.
