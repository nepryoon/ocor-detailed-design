# FASE 8–10 — Red Team, finalizzazione e Final Gate

## Red-team conclusion

Passata indipendente completata su authority ambiguity, confused deputy, prompt-derived authority, stale context, race, duplicate effect, retry/ACK, recovery, compartments/branch/watermark, causal overclaim, ABSTAIN, capability escalation, break-glass, stop bypass, backend fallback, scope e evidence claims.

Nuovi finding validi iniziali: `V12-RF-001`, `V12-RF-002`; corretti e ritestati. Passata successiva: zero nuovi finding validi. Rilievi generici, DDD-only o già governati non sono stati registrati.

## Final mechanical gate

| Gate | Esito |
|---|---|
| schema/OpenAPI/Protobuf/Turtle | `PASS`, salvo validator OpenAPI ufficiale `NOT_EXECUTED` |
| conformance branches | 105/105 `PASS` |
| semantic/FSM/adversarial | 29/29 `PASS` |
| release/integrity/patch | 12/12 `PASS`; 60/60 hunk mappati |
| failure totali | 0 |
| input immutability | `PASS` |
| blocker/critical interni | 0 |
| authority-pending diretti | 11 |
| evidence fence | `PASS`: E1=0, E2=0, zero Verified |

## Gate decision

**`READY FOR DDD AFTER CHANGE-CONTROL APPROVAL`**

Motivo: il lavoro tecnico correggibile localmente è completo; la candidata è determinata e fail-closed. La baseline necessaria non è ancora approvata e la contraddizione `FR-095`/`ELM-070` richiede una modifica atomica dei registri. Pertanto `READY FOR DDD` sarebbe una falsa approvazione.

## Release contents

- ADD v1.2 Candidate;
- Remediation Ledger;
- Change-Control Package;
- Validation Report;
- Final Review;
- patch v1.1→v1.2;
- SHA256SUMS finale;
- checkpoint FASE 0–6;
- test e risultati machine-readable.

Il branch locale deve essere pubblicato solo dall'utente. Nessun push è stato eseguito.
