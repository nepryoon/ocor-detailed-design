# OCOR ADD v1.2 Candidate — Final Review

## 1. Review Control

- Oggetto: `reports/OCOR_Architectural_Design_Document_v1.2_Candidate.md`.
- Derivazione: ADD v1.1, SHA-256 `3e7532c7101e80c74b511cedc56a0563ca0938a3fe259911a91245cb19dedc7f`.
- Branch locale: `codex/add-v1.2-remediation`.
- Review basis: sorgenti normative/supporting complete, review pregresse, registri, prompt, harness e test candidati.
- Stato documento: `PROPOSED — AWAITING CHANGE CONTROL`.
- Approval-readiness remediation: branch `codex/add-v1.2-approval-readiness`; candidate SHA-256 `4f84249b86150a0aa0ef5bf7fcc1a5c99388651e8aae132720dd784883b0426f`.
- Evidence fence: `E1=0`, `E2=0`, zero requisiti `Verified`; tecnologie `Candidate Implementation`, capability `Design Target`.

## 2. Executive Verdict

**`READY FOR DDD AFTER CHANGE-CONTROL APPROVAL`.**

La candidata non presenta difetti interni `BLOCKER` o `CRITICAL` correggibili noti. Tutte le correzioni tecniche sono coerenti, i contratti sono soddisfacibili e le suite sono verdi. Undici finding diretti del ledger restano `PENDING_CHANGE_CONTROL` perché la soluzione candidata modifica authority, contratti o allocazione normativa. Non sono difetti tecnici irrisolti: il testo sceglie una sola postura conservativa e fail-closed, ma non può renderla baseline senza l'Authority.

## 3. Source Integrity

- Manifest normativo: 8/8 digest corrispondenti.
- Materiale prior: 2/2 digest corrispondenti.
- Baseline v1.1: digest esatto.
- `git diff -- inputs prompts docs/detailed_design`: vuoto.
- Nessun file sorgente rinominato, cancellato o modificato.
- Patch v1.1→v1.2: 60 hunk, 1177 righe al checkpoint di generazione, 60/60 mappati.

## 4. Findings Closure

| Insieme | Riconciliati | `CLOSED_IN_CANDIDATE` / governed | `PENDING_CHANGE_CONTROL` |
|---|---:|---:|---:|
| `DRF-001`–`DRF-015` | 15 | 4 | 11 |
| `V12-RF-001`–`V12-RF-002` | 2 | 2 | 0 |
| `ARF-001`–`ARF-027` / `AM-01`–`AM-28` | 27/28 | tutti riconciliati; la disposizione eredita il `DRF-*` causale | nessuna voce separata non mappata |
| `RV-01`, `RV-02` | 2 | `ALREADY_GOVERNED` | 0 |

I sei finding diretti chiusi nella candidata sono `DRF-006`, `DRF-010`, `DRF-013`, `DRF-014`, `V12-RF-001`, `V12-RF-002`. Gli undici authority-pending sono `DRF-001`–`005`, `DRF-007`–`009`, `DRF-011`, `DRF-012`, `DRF-015`.

## 5. New Findings

La prima passata sulla candidata ha rilevato:

- `V12-RF-001`: replay ammesso senza finestra bounded;
- `V12-RF-002`: evidence/quorum strutturalmente vuoti.

Entrambi sono corretti, coperti da casi positivi e negativi e `CLOSED_IN_CANDIDATE`. La successiva passata indipendente end-to-end e adversarial non ha prodotto nuovi finding ADD-level validi.

## 6. Invariant Audit

`PASS IN CANDIDATE`:

- Principal effettivo soltanto da binding verificato;
- GCS unico e digest-equivalent su tutte le superfici;
- unica mutazione canonica tramite Action governata;
- single writer e local state+outbox; relay main-only;
- no prompt, agent memory o backend credential come Authority;
- no effect estimate in `ABSTAIN`; causal identify-or-abstain preservato;
- emission/retry/compensation bloccati su drift o controllo indisponibile;
- indeterminate effect non equivale a successo/failure e non sblocca per silenzio;
- marking unknown/incomparable e operator mismatch fail-closed;
- scope/evidence fence invariati.

## 7. Contract Verification

- 5 JSON Schema Draft 2020-12 meta-validi.
- 31 rami condizionali JSON e 3 OpenAPI coperti positivamente e negativamente.
- 105/105 casi conformance verdi.
- OpenAPI 3.1.0 v1.2.0: 6 path, 25 schema, 26 `$ref`, zero irrisolti.
- Protobuf compilato; Turtle parsato (17 triple).
- Canonical R1/NONE/missing Decision/Authority/Evidence respinti.
- ObjectSnapshot incompleto, replay unbounded e quorum/ruoli vuoti respinti.
- Validator semantico OpenAPI ufficiale: `NOT_EXECUTED`, tool non disponibile; non dichiarato `PASS`.

## 8. FSM Verification

`PASS`: 44 tuple `(transition_id, source, destination)` identiche tra diagramma e tabella; `ACT-T01`–`ACT-T31` contigui con varianti; ID univoci; tutti gli stati raggiungibili; source/destination completi. `ACT-T22` è OutcomeAssessment da `OUTCOME_PENDING`; `ACT-T27` apre la window da `EXECUTION_CONFIRMED`. Drift, lease expiry, retry e compensation sono testati al gate semantico.

## 9. Traceability

Universo core: 693. Coverage: BR 18/18, FR 174/174, NFR 93/93, ARC 23/23, ELM 103/103, RSK 60/60. CAP 25/26 nei subsystem più `CAP-026` esplicitamente `OUT_OF_SCOPE`. Decisioni: 183/196 allocate a subsystem/programme e 13/196 con disposition document/programme; globale 196/196. `DEC-173/175` hanno allocazione candidata, sottoposta a change control.

## 10. Scope Fence

- `ELM-070` resta differita.
- `FR-095` resta formalmente P0/PoC nella baseline; la candidata propone P0/MVP ed elenca le cinque modifiche di registro atomiche. Stato: `PENDING_CHANGE_CONTROL`.
- `NFR-078` resta `Confermato`, P0/MVP e fuori dal profilo PoC, non `Differito`.
- `CAP-024` distingue slice PoC e hardening esteso.
- `CAP-026` resta fuori perimetro.
- Nessuna capability differita è attivata.

## 11. Change-Control Status

Il Change-Control Package contiene dieci slug provvisori senza ID decisionale, testo esatto, alternative, selezione candidata, impatti, registri, dipendenze, rischi, rollback e criteri. `CC-SINGLE-WRITER-BRANCH-SCOPE` fornisce il percorso decisionale esplicito prima mancante per `DRAFT-C`; `CC-BA01-ALTERNATIVE` approva soltanto l'invariante atomico e la semantica `NO-GO`, senza fallback impliciti. Il DAG impedisce approvazioni parziali incoerenti. `DRAFT-A`–`DRAFT-I` restano non approvate; nessun `OI-*`, `ASM-*` o `RSK-*` è chiuso.

## 12. Evidence Fence

`PASS`: `E1=0`, `E2=0`, zero `Verified`; 158 controlli documentali non sono Evidence di implementazione. Nessun claim di parità, superiorità, performance, sicurezza, portabilità o production readiness è introdotto. Le acceptance evidence §7.2 restano `NOT RUN`.

## 13. Residual Risks

1. Authority: dieci change set devono essere approvati/modificati/rigettati; undici finding diretti ereditano questo blocco.
2. OpenAPI official semantic validator: `NOT_EXECUTED`; alternativa strutturale verde ma nessun claim di conformità allo strumento assente.
3. Backend assumptions, inclusa `BA-01`, restano non verificate; i gate `NO-GO` persistono.
4. Nessuna Evidence di runtime, performance, fault injection, security o portability è stata prodotta.
5. Tassonomia nazionale marking (`OI-021`) e altri open issue restano aperti.

## 13.1 Approval-readiness remediation

La verifica mirata successiva alla Final Review ha corretto dodici mapping `V12-AM-*`→finding, aggiunto il change set mancante per `DRAFT-C`, reso deterministica la disposizione `BA-01` e aggiornato il DAG. Il controllo machine-readable `v12_approval_readiness_results.json` riporta 18/18 `PASS`. Le sezioni contenenti schemi, OpenAPI, Protobuf, FSM e matrici normative non sono state modificate; i relativi risultati precedenti restano evidenza del contenuto invariato, ma il full harness deve essere rieseguito sul nuovo digest prima della firma.

## 14. Final Gate

`READY FOR DDD AFTER CHANGE-CONTROL APPROVAL`.

Condizioni per avanzare:

1. l'Authority decide i change set nel rispetto del DAG;
2. i registri vengono aggiornati atomicamente, in particolare `FR-095`/`ELM-070`;
3. la decisione approvata viene incorporata in una baseline firmata senza alterare l'evidence fence;
4. il DDD implementa e prova i contratti approvati, producendo Evidence separata.

Fino ad allora la candidata è pronta per la review di change control, non è una baseline approvata e non autorizza produzione o deployment.
