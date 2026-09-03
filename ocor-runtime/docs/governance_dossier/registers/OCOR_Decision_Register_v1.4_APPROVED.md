# OCOR Decision Register v1.4 — append-only continuation

## Configuration control

Questo registro incorpora senza modifica tutte le righe di
`OCOR_Decision_Register_v1.3_APPROVED.md` con SHA-256
`467bc77b582041c3b10cbdf4d111da21cb92e035a04ee0ae02936b0a44c68ef6` e aggiunge
esclusivamente `DEC-210`. In caso di digest diverso il registro è invalido.

| Decisione | Sorgente / gate | Decisione/esito e condizioni | Approval / authorization | Requisiti / capability | Evidenza autoritativa |
|---|---|---|---|---|---|
| `DEC-210` | `CC-RCCAD-METHODOLOGY-ADOPTION` | Adotta `OCOR-RCCAD v1.0` come raffinamento esecutivo G0–G7; nessuna semantica IRB/ADD/LLD modificata; `E1=0`, `E2=0`, runtime e Production `NO-GO` | explicit Product Owner authorization; 2026-09-02; effective on exact green merge | development process only; CAP-001–CAP-026 e 285 requisiti invariati | ARA Decision Record v1.4; methodology manifest/schema; RCCAD CI and TDD evidence |
