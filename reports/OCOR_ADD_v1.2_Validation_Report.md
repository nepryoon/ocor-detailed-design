# OCOR ADD v1.2 Candidate — Validation Report

## Validation Control

- Oggetto: `reports/OCOR_Architectural_Design_Document_v1.2_Candidate.md`.
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

## Verdict

La candidata è internamente verificabile e priva di failure meccaniche note. Il risultato abilita la Final Review e la review di change control, non l'approvazione automatica della baseline né il DDD in assenza delle decisioni elencate nel Change-Control Package.
