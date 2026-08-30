# FASE 0 — Preflight, integrità e freeze della baseline

## Execution control

| Campo | Valore |
|---|---|
| Timestamp locale | 2026-08-30 (Europe/Rome) |
| Repository root | `/home/luca/projects/ocor-detailed-design` |
| Branch iniziale | `main` (`main...origin/main`) |
| Branch di lavoro | `codex/add-v1.2-remediation` |
| HEAD congelato | `746132aa289958ff7f9f907a58e4243d6a7da61c` |
| Worktree iniziale | pulito |
| Modifiche preesistenti da preservare | nessuna rilevata |
| Baseline ADD | `inputs/normative/OCOR_Architectural_Design_Document_v1.1.md` |
| SHA-256 baseline ADD | `3e7532c7101e80c74b511cedc56a0563ca0938a3fe259911a91245cb19dedc7f` |

La baseline v1.1 e tutte le sorgenti sotto `inputs/` sono congelate in sola lettura. Tutti gli output di questa esecuzione restano sotto `reports/`. `docs/detailed_design/` è fuori perimetro.

## Source integrity

`sha256sum -c inputs/normative/SHA256SUMS` ha restituito exit code `0`: tutti gli otto file normativi elencati hanno digest coincidente.

| Sorgente | SHA-256 |
|---|---|
| `OCOR_Architectural_Design_Document_v1.1.md` | `3e7532c7101e80c74b511cedc56a0563ca0938a3fe259911a91245cb19dedc7f` |
| `OCOR_CAP_ELM_Requirement_Crosswalk_v0.9.md` | `cc1af191625b8267ac588dcdba1941dc316c75cdcc84efd312e8e32a4a0aef3b` |
| `OCOR_DEC_197_plus_Draft_v0.1.md` | `3336c0948df62564ffecef9c5872bcea2b68a4ec55fc6e08531797d060469bf0` |
| `OCOR_Decision_Register_v1.0.md` | `1a1adfb4a7a83b7f1aae85fd07d6349302bc7d5d0e805908ab5ec157a2a0da32` |
| `OCOR_Decision_Traceability_Index_v1.0.md` | `f7f45763621d68df62f6e2e1ad3ac8f0554c65478d91e6dbf3cfd084f50a3123` |
| `OCOR_Registers_v0.9.md` | `3810de19c25b5fc3179cbcf2189bb663c684180424337790f1ae3583f2ab9f42` |
| `OCOR_Requirement_Register_v0.9.md` | `f8a25dd050caaa468001149abc92fa9e7713cc3ba17d61aab31bfee6af4008cd` |
| `OCOR_Requirement_Traceability_Index_v0.9.md` | `a01400054e9f4871eb22062be7ede92064526a53232cf37e3eb3f4a5c95c08d1` |
| `SHA256SUMS` | `b95406cacedf605c8f1db534551654967802b6c8da26accc1926b41fc0d1024d` |
| `DELTA_MANIFEST.json` | `c45e011fc49cbb4828acc8cb4c7a0579c78a74a973d69dd1069b97db34a704af` |
| `DIFF_v1.0_to_v1.1.patch` | `290fcf9ad98afb3e72f94c422cfaf6e1722ba1283affd7e9a17d650c2c50b70c` |

## Toolchain disponibile

| Strumento | Versione/esito |
|---|---|
| Python | `3.14.4` (`./.venv/bin/python3`) |
| Git | `2.53.0` |
| sha256sum | uutils coreutils `0.8.0` |
| GNU diff | `3.12` |
| jsonschema | `4.26.0` |
| PyYAML | `6.0.3` |
| rdflib | `7.6.0` |
| protobuf Python | `7.36.0` |
| `protoc` standalone | `NOT_EXECUTED`: binario non presente; il verifier usa il compilatore già disponibile tramite ambiente Python |

Non sono stati installati pacchetti e non è stata usata la rete.

## Baseline verifier

Comando: `./.venv/bin/python3 scripts/verify.py --json` — exit code `0`.

| Esito | Conteggio |
|---|---:|
| `PASS` | 13 |
| `FAIL` | 0 |
| `NOT_EXECUTED` | 1 |

Il controllo `NOT_EXECUTED` è la validazione semantica OpenAPI 3.1 con validator ufficiale, assente nell'ambiente. Non è dichiarato superato. La risoluzione interna dei 26 `$ref` OpenAPI è `PASS`; la compilazione Protobuf tramite harness è `PASS`; il binario standalone `protoc` non è disponibile.

Il verifier baseline ha inoltre rilevato 24 rami condizionali da coprire con casi positivi (`canonical-ingestion-envelope=4`, `mcp-tool-contract=11`, `action-type-contract=9`). Questa copertura non è ancora provata per la candidata e costituisce lavoro obbligatorio delle fasi successive.

## Inventario repository congelato

L'inventario completo dei file versionati è stato ottenuto con `git ls-files` e comprende 49 path: `AGENTS.md`, `.gitignore`, 14 path sotto `inputs/`, 5 sotto `prompts/`, 24 sotto `reports/`, 2 sotto `scripts/` e 1 placeholder sotto `docs/detailed_design/`. I file presenti nella virtual environment non sono sorgenti repository e non fanno parte della baseline normativa.

## Gate FASE 0

`PASS WITH NOT_EXECUTED`: integrità e ambiente sono sufficienti per proseguire. Il `NOT_EXECUTED` OpenAPI ufficiale resta esplicitamente aperto come limite strumentale e non sarà trasformato in `PASS`.
