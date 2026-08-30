# OCOR ADD v1.2 Candidate — Validation Report

> **Governance supersession — 2026-08-30:** this validation report remains the pre-approval mechanical evidence. ADD v1.2 is now **APPROVED** under `DEC-197`–`DEC-206`. The full post-remediation harness rerun and the governed external-interface validator/waiver are tracked as non-blocking `VAL-ACT-001` and `VAL-ACT-002`; this report does not claim their closure.

## Validation Control

- Oggetto: `reports/OCOR_Architectural_Design_Document_v1.2_Candidate.md`, SHA-256 post-remediation `4f84249b86150a0aa0ef5bf7fcc1a5c99388651e8aae132720dd784883b0426f`.
- Baseline: ADD v1.1 SHA-256 `3e7532c7101e80c74b511cedc56a0563ca0938a3fe259911a91245cb19dedc7f`.
- Data: 2026-08-30, Europe/Rome.
- Natura: verifica documentale e di contratto; non produce Evidence di sistema.
- Evidence fence: `E1=0`, `E2=0`, zero requisiti `Verified`.

## Executive Result

`PASS WITH DECLARED NOT_EXECUTED`: 158 asserzioni/controlli passati, zero falliti. Due controlli del verifier sono marcati `NOT_EXECUTED`; l'integrità senza manifest locale è stata soddisfatta da un controllo alternativo e dal checksum finale, mentre il validator semantico OpenAPI 3.1 ufficiale resta non disponibile e non è dichiarato superato.

## Tool-backed verification

| Area | Esito | Evidenza documentale |
|---|---|---|
| JSON Schema | `PASS` | 5 schemi Draft 2020-12; nessun conditional-required non dichiarato |
| Conditional conformance | `PASS` | 31 rami JSON + 3 OpenAPI; positivi e negativi; 105/105 casi complessivi |
| OpenAPI | `PASS` strutturale | 3.1.0/1.2.0; 6 path; 25 component schema; 26 `$ref` risolti |
| OpenAPI official semantic validator | `NOT_EXECUTED` | tool non presente; nessuna installazione/rete tentata |
| Protobuf | `PASS` | compilazione tramite tooling già disponibile |
| Turtle | `PASS` | parse di 17 triple |
| FSM | `PASS` | 44 tuple esatte; T01–T31 contigue; reachable/unique/source/destination |
| Universo/traceability | `PASS` | core 693; globale DEC 196/196 per disposition; CAP-026 `OUT_OF_SCOPE` |
| Reference integrity | `PASS` | zero rimandi § irrisolti |
| Evidence/authority fence | `PASS` | zero claim unsupported; nessun nuovo ID decisionale o approvazione |
| Patch/Amendment Log | `PASS` | 60/60 hunk mappati |
| Source immutability | `PASS` alternativo | 8/8 normative + 2/2 prior digest; git diff protetto vuoto |

## Required negative tests

Tutti verdi per la ragione attesa: canonical R0/R1 con `NONE`; canonical senza Decision/Authority/Evidence; Principal mismatch; freshness drift; lease scaduta; quorum/ruoli vuoti; target/effect incompatibili; permission con operatore restriction; unknown marking; replay senza window; `ObjectSnapshot` incompleto; transizione senza source/destination; ID inesistente; `Verified` con evidence fence a zero.

Ogni gruppo conserva almeno un caso positivo: canonical R2/Human Gate completo, Principal coerente, emission fence immutata, marking restriction/permission noto, replay bounded, snapshot completo, FSM completa, ID valido e stato `Confirmed` senza promozione.

## Residual validation limitations

1. Il validator semantico OpenAPI 3.1 ufficiale è `NOT_EXECUTED`; la limitazione deve restare visibile al prossimo gate.
2. I test sono documentali/schema-level e non conformance di un'implementazione; non incrementano E1/E2.
3. Backend, performance, security controls, portability e production readiness restano non verificati e soggetti alle Evidence future §7.2.

## Approval-readiness remediation verification

`PASS`: 18/18 controlli mirati, zero failure. Sono stati verificati i dodici mapping `V12-AM-*`→finding corretti, la presenza di dieci change set, il percorso decisionale completo per `DRAFT-C`, le dipendenze DAG, la disposizione deterministica `BA-01`, la chiusura nel ledger e la preservazione dell'authority fence.

Le sezioni contenenti JSON Schema, OpenAPI, Protobuf, FSM e matrici di tracciabilità normativa non sono state modificate dalla remediation. I risultati meccanici precedenti restano riferibili a tali blocchi invariati; prima della firma dell'ADD deve comunque essere rieseguito il full harness sul digest post-remediation e deve essere eseguito il validator OpenAPI 3.1 approvato oppure registrata una waiver formale.

## Verdict

La candidata è internamente verificabile, priva di failure meccaniche note e completa per la review finale dell'Architecture Review Authority. Il risultato non costituisce approvazione automatica: i dieci change set devono essere decisi, i registri aggiornati atomicamente, il full harness rieseguito sul digest post-remediation e la decisione incorporata in una baseline firmata.
