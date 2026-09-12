# OCOR Decision Register v1.6 — append-only continuation

## Configuration control

Incorpora senza modifica `OCOR_Decision_Register_v1.5_APPROVED.md` con SHA-256
`9d4a4cc5214ee93fd08585ce11e2ac2fa1da298d978d103beb038a4f0207fafb` e aggiunge
esclusivamente `DEC-212`.

| Decisione | Sorgente / gate | Decisione/esito | Approval | Scope | Evidenza |
|---|---|---|---|---|---|
| `DEC-212` | `CC-OCOR-LANGUAGE-POLICY` | Adotta la politica normativa dei linguaggi di implementazione interna per ogni area del progetto e il gate eseguibile `scripts/validate_language_policy.py`; non tocca il profilo SDK di `DEC-075`/`FR-047`/`FR-048` | explicit Product Owner authorization; 2026-09-12; effective on exact-green merge | development-process policy and CI gate only; `E1=0`, `E2=0`, runtime/Production `NO-GO` | ARA Decision Record v1.6; `OCOR_LANGUAGE_POLICY.md`; RED/GREEN; CI |
